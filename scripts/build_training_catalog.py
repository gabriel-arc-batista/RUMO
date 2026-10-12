"""Build the public catalog.json of a content repository, ready to publish.

Usage:
  python scripts/build_training_catalog.py CONTENT_REPO BASE_URL [HOST ...]

CONTENT_REPO contains ``catalogo-fonte.json`` (subjects, topics and lessons,
without bytes/sha256) and ``pdf/<arquivo>.pdf`` for every lesson that has a
resource. BASE_URL is where those PDFs will be downloadable, e.g. the release
download address https://github.com/<owner>/<repo>/releases/download/<tag>/.
HOST lists extra approved hosts (the catalog host is added by the app itself).

The script computes bytes, SHA-256 and page count, rejects publication without
an approved review and validates the result with the same rules the app uses.
Output: CONTENT_REPO/publicar/catalog.json plus the PDFs to attach to the
release. It never uploads anything.
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training_catalog import validate_catalog  # noqa: E402


def page_count(path):
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return None
    document = pdfium.PdfDocument(str(path))
    try:
        return len(document)
    finally:
        document.close()


def main(repo, base_url, extra_hosts):
    repo = Path(repo)
    source = json.loads((repo / "catalogo-fonte.json").read_text(encoding="utf-8"))
    out = repo / "publicar"
    out.mkdir(exist_ok=True)
    for lesson in source["lessons"]:
        resource = lesson.get("resource")
        if not resource:
            continue
        pdf = repo / "pdf" / resource.pop("file")
        data = pdf.read_bytes()
        name = f"{lesson['id'].replace(':', '_')}-{resource['version']}.pdf"
        shutil.copyfile(pdf, out / name)
        resource.update(
            url=urljoin(base_url, name),
            media_type="application/pdf",
            bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            page_count=page_count(pdf),
        )
    hosts = [urlsplit(base_url).hostname, *extra_hosts]
    validate_catalog(source, allowed_hosts=hosts)
    (out / "catalog.json").write_text(
        json.dumps(source, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(
        f"Catálogo válido em {out / 'catalog.json'}; anexe os PDFs de {out} à release."
    )


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
