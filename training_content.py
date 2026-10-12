"""Content provider and local files of the Campo de Treinamento (no Tk).

Two providers share one interface: a local folder (catalog.json + PDFs) and a
public HTTPS address. No account, key or AI service is involved. Downloads go to
a temporary file, are checked against the declared size and SHA-256 and only
then renamed into place. The last valid catalog stays active when a refresh
fails; personal notes and progress live in SQLite and never in these folders.
"""

import hashlib
import json
import os
import shutil
import threading
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from training_catalog import MAX_PDF_BYTES, CatalogError, validate_catalog

MAX_CATALOG_BYTES = 8 * 1024 * 1024
CHUNK = 64 * 1024
TIMEOUT = 20
DISK_MARGIN = 50 * 1024 * 1024
GITHUB_RELEASE_HOSTS = (
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
)
NO_SOURCE = dict(mode="none", path="", url="", allowed_hosts=[])


class ContentError(Exception):
    """User-facing failure of a catalog or download operation."""


class Cancelled(ContentError):
    pass


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with open(temporary, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def normalize_source(raw):
    """Preference value -> source config. Unknown or malformed -> no source."""
    if not isinstance(raw, dict) or raw.get("mode") not in ("none", "local", "remote"):
        return dict(NO_SOURCE)
    hosts = [
        h.strip().lower()
        for h in raw.get("allowed_hosts", [])
        if isinstance(h, str) and h.strip()
    ]
    source = dict(
        mode=raw["mode"],
        path=str(raw.get("path") or ""),
        url=str(raw.get("url") or ""),
        allowed_hosts=hosts,
    )
    if source["mode"] == "remote":
        host = urlsplit(source["url"]).hostname
        if host and host.lower() not in source["allowed_hosts"]:
            source["allowed_hosts"].insert(0, host.lower())
    return source


def validate_source(source):
    """Raise ValueError when the configuration cannot be used."""
    if source["mode"] == "local" and not Path(source["path"]).is_dir():
        raise ValueError("Escolha uma pasta existente com catalog.json.")
    if source["mode"] == "remote":
        parts = urlsplit(source["url"])
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username
            or parts.password
        ):
            raise ValueError("Use um endereço https:// público, sem usuário e senha.")
    return source


class HostCheck(urllib.request.HTTPRedirectHandler):
    """Follow redirects only to HTTPS hosts listed in the configuration."""

    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = urlsplit(newurl)
        if parts.scheme != "https" or (parts.hostname or "").lower() not in self.hosts:
            raise ContentError(
                f"Redirecionamento para host não aprovado: {parts.hostname}."
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class LocalProvider:
    """A folder with catalog.json; resources are relative paths inside it."""

    label = "Pasta local"
    is_local = True

    def __init__(self, folder):
        self.folder = Path(folder).resolve()

    def fetch_catalog(self, etag=None):
        path = self.folder / "catalog.json"
        if not path.is_file():
            raise ContentError("A pasta não tem catalog.json.")
        if path.stat().st_size > MAX_CATALOG_BYTES:
            raise ContentError("catalog.json grande demais.")
        return path.read_bytes(), None

    def open(self, url):
        target = (self.folder / url).resolve()
        if self.folder not in target.parents or not target.is_file():
            raise ContentError("Arquivo da aula não encontrado na pasta do catálogo.")
        return open(target, "rb")


class RemoteProvider:
    """Public HTTPS catalog; PDFs on approved hosts (e.g. GitHub Releases)."""

    label = "Endereço remoto"
    is_local = False

    def __init__(self, url, hosts, opener=None):
        self.url = url
        self.hosts = set(hosts)
        self.opener = opener or urllib.request.build_opener(HostCheck(self.hosts))

    def request(self, url, headers=None):
        parts = urlsplit(url)
        if parts.scheme != "https" or (parts.hostname or "").lower() not in self.hosts:
            raise ContentError(f"Host não aprovado: {parts.hostname}.")
        request = urllib.request.Request(
            url, headers={"User-Agent": "RUMO-Estudos", **(headers or {})}
        )
        try:
            return self.opener.open(request, timeout=TIMEOUT)
        except urllib.error.HTTPError as error:
            if error.code == 304:
                return None
            raise ContentError(
                f"O servidor respondeu {error.code} para {parts.hostname}."
            ) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise ContentError("Sem conexão com o endereço do conteúdo.") from error

    def fetch_catalog(self, etag=None):
        response = self.request(self.url, {"If-None-Match": etag} if etag else None)
        if response is None:
            return None, etag
        with response:
            data = response.read(MAX_CATALOG_BYTES + 1)
            if len(data) > MAX_CATALOG_BYTES:
                raise ContentError("Catálogo remoto grande demais.")
            return data, response.headers.get("ETag")

    def open(self, url):
        response = self.request(urljoin(self.url, url))
        if response is None:
            raise ContentError("Resposta vazia do servidor.")
        return response


class ContentManager:
    """Catalog cache, downloads and personal imports under one data folder."""

    def __init__(self, root, source=None, opener=None):
        self.root = Path(root)
        self.catalog_dir = self.root / "catalogo"
        self.files_dir = self.root / "arquivos"
        self.personal_dir = self.root / "pessoal"
        self.tmp_dir = self.root / "temp"
        self.source = normalize_source(source)
        self.opener = opener
        self.downloads = {}
        self.lock = threading.Lock()
        for folder in (
            self.catalog_dir,
            self.files_dir,
            self.personal_dir,
            self.tmp_dir,
        ):
            folder.mkdir(parents=True, exist_ok=True)
        for leftover in self.tmp_dir.glob("*.part"):
            leftover.unlink(missing_ok=True)

    # Provider and catalog -------------------------------------------------

    def provider(self):
        if self.source["mode"] == "local":
            return LocalProvider(self.source["path"])
        if self.source["mode"] == "remote":
            return RemoteProvider(
                self.source["url"], self.source["allowed_hosts"], self.opener
            )
        return None

    def state(self):
        path = self.catalog_dir / "estado.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def save_state(self, **changes):
        state = dict(self.state(), **changes)
        write_atomic(
            self.catalog_dir / "estado.json",
            json.dumps(state, ensure_ascii=False).encode(),
        )
        return state

    def catalog(self):
        """The last valid catalog, or None. Re-validated on every load."""
        path = self.catalog_dir / "ativo.json"
        if not path.is_file():
            return None
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
            return validate_catalog(stored["raw"], stored["local"], stored["hosts"])
        except (OSError, ValueError, KeyError):
            return None

    def refresh(self):
        """Fetch, validate and activate a catalog. Returns (catalog, changed)."""
        provider = self.provider()
        if provider is None:
            raise ContentError("Nenhuma fonte de conteúdo configurada.")
        state = self.state()
        same_source = state.get("source") == self.source
        try:
            data, etag = provider.fetch_catalog(
                state.get("etag") if same_source else None
            )
            if data is None:
                self.save_state(checked_at=now(), error=None)
                return self.catalog(), False
            try:
                raw = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as error:
                raise ContentError("O catálogo não é um JSON válido.") from error
            hosts = sorted(set(self.source["allowed_hosts"]))
            catalog = validate_catalog(raw, provider.is_local, hosts)
        except (ContentError, CatalogError) as error:
            self.save_state(checked_at=now(), error=str(error))
            raise ContentError(str(error)) from error
        stored = dict(raw=raw, local=provider.is_local, hosts=hosts)
        write_atomic(
            self.catalog_dir / "ativo.json",
            json.dumps(stored, ensure_ascii=False).encode(),
        )
        self.save_state(
            source=self.source,
            etag=etag,
            checked_at=now(),
            activated_at=now(),
            error=None,
            catalog_id=catalog["catalog_id"],
            catalog_version=catalog["catalog_version"],
        )
        return catalog, True

    # Files --------------------------------------------------------------

    def file_for(self, lesson_id, resource):
        return (
            self.files_dir
            / lesson_id.replace(":", "_")
            / resource["version"]
            / f"{resource['sha256']}.pdf"
        )

    def local_versions(self, lesson_id):
        """Downloaded versions of a lesson: {version: path}, newest names last."""
        folder = self.files_dir / lesson_id.replace(":", "_")
        found = {}
        if folder.is_dir():
            for version in sorted(p for p in folder.iterdir() if p.is_dir()):
                files = sorted(version.glob("*.pdf"))
                if files:
                    found[version.name] = files[0]
        return found

    def availability(self, lesson):
        """nao_publicada, nao_baixada, baixando, disponivel, falha or atualizacao_disponivel."""
        resource = lesson.get("resource")
        if not resource:
            return "nao_publicada"
        with self.lock:
            job = self.downloads.get(lesson["id"])
        if job and job["state"] == "baixando":
            return "baixando"
        current = self.file_for(lesson["id"], resource)
        if current.is_file() and current.stat().st_size == resource["bytes"]:
            return "disponivel"
        if job and job["state"] == "falha":
            return "falha"
        if self.local_versions(lesson["id"]):
            return "atualizacao_disponivel"
        return "nao_baixada"

    def download(self, lesson, progress=None, cancel=None):
        """Blocking download with checks; call from a worker thread."""
        resource = lesson["resource"]
        target = self.file_for(lesson["id"], resource)
        if target.is_file() and target.stat().st_size == resource["bytes"]:
            return target
        if shutil.disk_usage(self.root).free < resource["bytes"] + DISK_MARGIN:
            raise ContentError("Espaço em disco insuficiente para esta aula.")
        provider = self.provider()
        if provider is None:
            raise ContentError("Configure a fonte de conteúdo para baixar esta aula.")
        part = self.tmp_dir / f"{resource['sha256']}.part"
        digest = hashlib.sha256()
        received = 0
        try:
            with provider.open(resource["url"]) as stream, open(part, "wb") as out:
                while True:
                    if cancel is not None and cancel.is_set():
                        raise Cancelled("Download cancelado.")
                    chunk = stream.read(CHUNK)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > resource["bytes"] or received > MAX_PDF_BYTES:
                        raise ContentError(
                            "O arquivo é maior que o declarado no catálogo."
                        )
                    digest.update(chunk)
                    out.write(chunk)
                    if progress:
                        progress(received, resource["bytes"])
                out.flush()
                os.fsync(out.fileno())
            if received != resource["bytes"]:
                raise ContentError("O arquivo recebido está incompleto.")
            if digest.hexdigest() != resource["sha256"]:
                raise ContentError("O arquivo não confere com o hash do catálogo.")
            with open(part, "rb") as check:
                if check.read(5) != b"%PDF-":
                    raise ContentError("O arquivo recebido não é um PDF.")
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(part, target)
            return target
        except OSError as error:
            raise ContentError(
                f"Não foi possível gravar a aula: {error.strerror or error}."
            ) from error
        finally:
            part.unlink(missing_ok=True)

    def start_download(self, lesson, notify):
        """Background download; ``notify(lesson_id)`` runs on every state change."""
        cancel = threading.Event()
        job = dict(
            state="baixando",
            received=0,
            total=lesson["resource"]["bytes"],
            error=None,
            cancel=cancel,
        )
        with self.lock:
            if self.downloads.get(lesson["id"], {}).get("state") == "baixando":
                return
            self.downloads[lesson["id"]] = job

        def progress(received, total):
            job["received"] = received

        def run():
            try:
                self.download(lesson, progress, cancel)
                job["state"] = "concluido"
            except Cancelled:
                job["state"] = "cancelado"
            except ContentError as error:
                job.update(state="falha", error=str(error))
            except Exception as error:  # noqa: BLE001 - never crash the UI thread
                job.update(state="falha", error=f"Falha inesperada: {error}")
            notify(lesson["id"])

        threading.Thread(target=run, daemon=True).start()
        notify(lesson["id"])

    def job(self, lesson_id):
        with self.lock:
            return dict(self.downloads.get(lesson_id) or {})

    def cancel(self, lesson_id):
        with self.lock:
            job = self.downloads.get(lesson_id)
        if job and job["state"] == "baixando":
            job["cancel"].set()

    def remove(self, lesson_id, version=None):
        """Delete downloaded files only; notes and progress stay in the database."""
        folder = self.files_dir / lesson_id.replace(":", "_")
        target = folder / version if version else folder
        if target.is_dir() and folder.resolve() in [
            target.resolve(),
            *target.resolve().parents,
        ]:
            shutil.rmtree(target)
        with self.lock:
            self.downloads.pop(lesson_id, None)

    def usage(self):
        return sum(p.stat().st_size for p in self.root.rglob("*.pdf") if p.is_file())

    # Personal files ------------------------------------------------------

    def import_pdf(self, path):
        """Copy a user's own PDF into the private folder. Returns (sha, bytes, name)."""
        source = Path(path)
        size = source.stat().st_size
        if not 0 < size <= MAX_PDF_BYTES:
            raise ContentError("PDF vazio ou grande demais.")
        with open(source, "rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise ContentError("O arquivo escolhido não é um PDF.")
        if shutil.disk_usage(self.root).free < size + DISK_MARGIN:
            raise ContentError("Espaço em disco insuficiente.")
        digest = hashlib.sha256()
        part = self.tmp_dir / f"import-{os.getpid()}.part"
        try:
            with open(source, "rb") as stream, open(part, "wb") as out:
                for chunk in iter(lambda: stream.read(CHUNK), b""):
                    digest.update(chunk)
                    out.write(chunk)
            name = digest.hexdigest() + ".pdf"
            os.replace(part, self.personal_dir / name)
        finally:
            part.unlink(missing_ok=True)
        return digest.hexdigest(), size, name

    def personal_file(self, filename):
        path = self.personal_dir / filename
        return path if path.is_file() else None
