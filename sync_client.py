"""Explicit, durable event synchronization; no access to the legacy study database."""

import json
import base64
from contextlib import contextmanager
import sqlite3
import uuid
from urllib import error, parse, request

KINDS = frozenset(
    (
        "reading.page",
        "reading.position",
        "note.save",
        "favorite.set",
        "arena.attempt",
        "card.save",
        "card.review",
        "study.session",
    )
)
MAX_RESPONSE = 16 * 1024 * 1024


class SyncError(Exception):
    def __init__(self, code, message=""):
        self.code = code
        super().__init__(message or code)


def _uuid(value):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError) as exc:
        raise SyncError("invalid_event", "UUID inválido") from exc


def _json(value, max_bytes=65536):
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise SyncError("invalid_event") from exc
    if len(encoded.encode("utf-8")) > max_bytes:
        raise SyncError("invalid_event", "Evento excede 64 KiB")

    def check(item):
        if isinstance(item, str) and len(item) > 20000:
            raise SyncError("invalid_event", "Texto excede o limite")
        if isinstance(item, dict):
            for key, child in item.items():
                check(key)
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)

    check(value)
    return encoded


@contextmanager
def _transaction(connection):
    """Nest safely without committing a caller's transaction."""
    name = "sync_" + uuid.uuid4().hex
    connection.execute("SAVEPOINT " + name)
    try:
        yield
    except BaseException:
        connection.execute("ROLLBACK TO " + name)
        connection.execute("RELEASE " + name)
        raise
    else:
        connection.execute("RELEASE " + name)


def _personal_payload(payload):
    return any(
        isinstance(payload.get(field), str) and payload[field].startswith("pessoal.")
        for field in ("lesson_id", "target_id")
    )


class SyncWorkspace:
    """One explicitly bound account per independent SQLite workspace."""

    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA cache_size=-2048")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS outbox(
                id TEXT PRIMARY KEY,envelope TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',error TEXT);
            CREATE TABLE IF NOT EXISTS remote_events(
                id TEXT PRIMARY KEY,sequence INTEGER UNIQUE NOT NULL,envelope TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS entities(
                kind TEXT NOT NULL,entity_id TEXT NOT NULL,revision INTEGER NOT NULL,
                payload TEXT NOT NULL,PRIMARY KEY(kind,entity_id));
        """)
        with _transaction(self.db):
            columns = {row[1] for row in self.db.execute("PRAGMA table_info(outbox)")}
            if "shareable" not in columns:
                self.db.execute(
                    "ALTER TABLE outbox ADD COLUMN shareable INTEGER NOT NULL DEFAULT 1"
                )
                # Older builds encoded local-only personal progress as ordinary drafts.
                for row in self.db.execute(
                    "SELECT id,envelope FROM outbox WHERE shareable=1"
                ):
                    if _personal_payload(json.loads(row[1])["payload"]):
                        self.db.execute(
                            "UPDATE outbox SET shareable=0,status='local' WHERE id=?",
                            (row[0],),
                        )
            self.db.execute("INSERT OR IGNORE INTO metadata VALUES('version','1')")
            self.db.execute(
                "INSERT OR IGNORE INTO metadata VALUES('device_id',?)",
                (str(uuid.uuid4()),),
            )
            self.db.execute("INSERT OR IGNORE INTO metadata VALUES('cursor','0')")
        if self._meta("version") != "1":
            raise SyncError("unsupported_workspace")
        self.projector = None
        self.status = (
            "conflict"
            if self.conflicts()
            else "pending" if self.pending(1) else "offline"
        )

    def close(self):
        self.db.close()

    def _meta(self, key):
        row = self.db.execute(
            "SELECT value FROM metadata WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else None

    @property
    def account_id(self):
        return self._meta("account_id")

    @property
    def device_id(self):
        return self._meta("device_id")

    @property
    def cursor(self):
        return int(self._meta("cursor"))

    def bind_account(self, account_id, *, consent=False):
        account_id = _uuid(account_id)
        if self.account_id and self.account_id != account_id:
            raise SyncError("account_mismatch", "Crie outro workspace para outra conta")
        if not consent:
            raise SyncError("consent_required")
        with _transaction(self.db):
            self.db.execute(
                "INSERT OR IGNORE INTO metadata VALUES('account_id',?)", (account_id,)
            )
            if self.account_id != account_id:
                raise SyncError("account_mismatch")

    def enqueue(
        self,
        kind,
        entity_id,
        payload,
        base_revision=0,
        event_id=None,
        *,
        local_only=False,
    ):
        if (
            kind not in KINDS
            or not isinstance(entity_id, str)
            or not entity_id
            or len(entity_id) > 512
            or type(base_revision) is not int
            or base_revision < 0
            or not isinstance(payload, dict)
        ):
            raise SyncError("invalid_event")
        event = dict(
            id=_uuid(event_id or uuid.uuid4()),
            device_id=self.device_id,
            kind=kind,
            entity_id=entity_id,
            base_revision=base_revision,
            payload=payload,
        )
        _json(payload)
        encoded = _json(event, 128 * 1024)
        local_only = local_only or _personal_payload(payload)
        old = self.db.execute(
            "SELECT envelope FROM outbox WHERE id=?", (event["id"],)
        ).fetchone()
        if old and json.loads(old[0]) != event:
            raise SyncError("event_mismatch")
        with _transaction(self.db):
            self.db.execute(
                "INSERT OR IGNORE INTO outbox(id,envelope,status,shareable) VALUES(?,?,?,?)",
                (
                    event["id"],
                    encoded,
                    "pending" if self.account_id and not local_only else "local",
                    int(not local_only),
                ),
            )
        self.status = "pending" if self.pending(1) else "offline"
        return event

    def set_projector(self, projector):
        self.projector = projector

    def share_events(self, event_ids):
        if not self.account_id:
            raise SyncError("consent_required")
        with _transaction(self.db):
            for event_id in event_ids:
                row = self.db.execute(
                    "SELECT shareable FROM outbox WHERE id=?", (event_id,)
                ).fetchone()
                if row is None:
                    raise SyncError("invalid_event")
                if not row[0]:
                    raise SyncError(
                        "local_only", "PDFs pessoais permanecem neste dispositivo"
                    )
                self.db.execute(
                    "UPDATE outbox SET status='pending' WHERE id=? AND status='local' AND shareable=1",
                    (event_id,),
                )
        self.status = "pending" if self.pending(1) else "offline"

    def pending(self, limit=-1):
        return [
            json.loads(row[0])
            for row in self.db.execute(
                "SELECT envelope FROM outbox WHERE status='pending' AND shareable=1 ORDER BY rowid LIMIT ?",
                (limit,),
            )
        ]

    def conflicts(self):
        return [
            json.loads(row[0])
            for row in self.db.execute(
                "SELECT envelope FROM outbox WHERE status='conflict' ORDER BY rowid"
            )
        ]

    def events(self):
        return [
            json.loads(row[0])
            for row in self.db.execute(
                "SELECT envelope FROM remote_events ORDER BY sequence"
            )
        ]

    def entity(self, kind, entity_id):
        row = self.db.execute(
            "SELECT revision,payload FROM entities WHERE kind=? AND entity_id=?",
            (kind, entity_id),
        ).fetchone()
        return dict(revision=row[0], payload=json.loads(row[1])) if row else None

    def apply_pull(self, events):
        """Validate and apply the whole page before committing its cursor."""
        with _transaction(self.db):
            cursor = self.cursor
            for event in events:
                if not isinstance(event, dict):
                    raise SyncError("invalid_response")
                sequence = event.get("sequence")
                revision = event.get("revision")
                if (
                    type(sequence) is not int
                    or sequence <= cursor
                    or type(revision) is not int
                    or revision < 1
                    or event.get("kind") not in KINDS
                    or not isinstance(event.get("entity_id"), str)
                    or not isinstance(event.get("payload"), dict)
                ):
                    raise SyncError("invalid_response")
                event_id = _uuid(event.get("id"))
                encoded = _json(event, 128 * 1024)
                self.db.execute(
                    "INSERT INTO remote_events VALUES(?,?,?)",
                    (event_id, sequence, encoded),
                )
                self.db.execute(
                    """INSERT INTO entities VALUES(?,?,?,?)
                    ON CONFLICT(kind,entity_id) DO UPDATE SET revision=excluded.revision,payload=excluded.payload
                    WHERE excluded.revision>entities.revision""",
                    (
                        event["kind"],
                        event["entity_id"],
                        revision,
                        _json(event["payload"]),
                    ),
                )
                if self.projector:
                    self.projector(event)
                cursor = sequence
            self.db.execute(
                "UPDATE metadata SET value=? WHERE key='cursor'", (str(cursor),)
            )

    def _pull(self, transport):
        while True:
            page = transport.pull_events(self.cursor, 200)
            if not isinstance(page, list) or len(page) > 200:
                raise SyncError("invalid_response")
            self.apply_pull(page)
            if len(page) < 200:
                break

    def sync(self, transport):
        if not self.account_id or transport.account_id != self.account_id:
            raise SyncError("account_mismatch")
        self.status = "syncing"
        try:
            self._pull(transport)
            while self.pending(1):
                batch = self.pending(1)
                try:
                    accepted = transport.push_events(batch)
                except SyncError as exc:
                    if exc.code == "revision_conflict":
                        self._pull(transport)
                        with _transaction(self.db):
                            for event in batch:
                                self.db.execute(
                                    "UPDATE outbox SET status='conflict',error=? WHERE id=?",
                                    (exc.code, event["id"]),
                                )
                        self.status = "conflict"
                        return self.status
                    raise
                ids = {event["id"] for event in batch}
                if (
                    not isinstance(accepted, list)
                    or len(accepted) != len(batch)
                    or any(not isinstance(item, dict) for item in accepted)
                    or {item.get("id") for item in accepted} != ids
                    or any(
                        type(item.get("sequence")) is not int or item["sequence"] < 1
                        for item in accepted
                    )
                ):
                    raise SyncError("invalid_response")
                with _transaction(self.db):
                    for event_id in ids:
                        self.db.execute(
                            "UPDATE outbox SET status='sent',error=NULL WHERE id=?",
                            (event_id,),
                        )
            self._pull(transport)
            self.status = "conflict" if self.conflicts() else "synced"
        except (OSError, SyncError, sqlite3.Error, ValueError) as exc:
            self.status = "offline" if isinstance(exc, OSError) else "error"
            raise
        return self.status

    def resolve_conflict(self, event_id, payload, base_revision):
        row = self.db.execute(
            "SELECT envelope FROM outbox WHERE id=? AND status='conflict'", (event_id,)
        ).fetchone()
        if not row:
            raise SyncError("invalid_event")
        old = json.loads(row[0])
        with _transaction(self.db):
            new = self.enqueue(old["kind"], old["entity_id"], payload, base_revision)
            self.db.execute(
                "UPDATE outbox SET status='resolved' WHERE id=?", (event_id,)
            )
        return new


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if fp is not None:
            fp.close()
        raise SyncError("unsafe_redirect")


def _validate_public_key(value):
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise ValueError("Chave pública inválida")
    if value.startswith("sb_secret_"):
        raise ValueError("Use somente a chave pública do serviço")
    parts = value.split(".")
    if len(parts) == 3:
        try:
            payload = json.loads(
                base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4))
            )
        except (ValueError, UnicodeError):
            payload = None
        if isinstance(payload, dict) and payload.get("role") in (
            "service_role",
            "supabase_admin",
        ):
            raise ValueError("Use somente a chave pública do serviço")


class SupabaseTransport:
    """HTTPS only, bounded responses, no redirects; credentials live in memory."""

    def __init__(self, url, public_key, timeout=15):
        parsed = parse.urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise ValueError("Origem HTTPS inválida")
        _validate_public_key(public_key)
        self.url = url.rstrip("/")
        self.public_key = public_key
        self.timeout = timeout
        self.access_token = self.refresh_token = self.account_id = None
        self.opener = request.build_opener(_NoRedirect())

    def _call(self, path, body, *, authenticated=True, retry=True):
        if authenticated and not self.access_token:
            raise SyncError("unauthenticated")
        headers = {"apikey": self.public_key, "Content-Type": "application/json"}
        if authenticated:
            headers["Authorization"] = "Bearer " + self.access_token
        req = request.Request(
            self.url + path,
            data=json.dumps(body, allow_nan=False).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                data = response.read(MAX_RESPONSE + 1)
        except error.HTTPError as exc:
            data = exc.read(65537)
            exc.close()
            code = "unauthenticated" if exc.code in (401, 403) else "remote_error"
            try:
                detail = json.loads(data)
                for field in ("message", "code"):
                    if detail.get(field) in (
                        "revision_conflict",
                        "event_mismatch",
                        "invalid_event",
                        "content_unavailable",
                        "invalid_answer",
                        "card_suspended",
                    ):
                        code = detail[field]
            except (ValueError, AttributeError):
                pass
            if (
                code == "unauthenticated"
                and authenticated
                and retry
                and self.refresh_token
            ):
                self.refresh()
                return self._call(path, body, authenticated=True, retry=False)
            raise SyncError(code) from None
        if len(data) > MAX_RESPONSE:
            raise SyncError("invalid_response")
        try:
            return json.loads(data) if data else None
        except (ValueError, UnicodeError) as exc:
            raise SyncError("invalid_response") from exc

    def _session(self, result):
        try:
            account = _uuid(result["user"]["id"])
            access, refresh = result["access_token"], result["refresh_token"]
            if (
                not isinstance(access, str)
                or not access
                or not isinstance(refresh, str)
                or not refresh
            ):
                raise ValueError()
        except (KeyError, TypeError, ValueError) as exc:
            raise SyncError("invalid_response") from exc
        if self.account_id and self.account_id != account:
            raise SyncError("account_mismatch")
        self.account_id, self.access_token, self.refresh_token = (
            account,
            access,
            refresh,
        )
        return account

    def login(self, email, password):
        return self._session(
            self._call(
                "/auth/v1/token?grant_type=password",
                {"email": email, "password": password},
                authenticated=False,
            )
        )

    def refresh(self):
        if not self.refresh_token:
            raise SyncError("unauthenticated")
        return self._session(
            self._call(
                "/auth/v1/token?grant_type=refresh_token",
                {"refresh_token": self.refresh_token},
                authenticated=False,
            )
        )

    def logout(self):
        try:
            if self.access_token:
                self._call("/auth/v1/logout", {})
        finally:
            self.access_token = self.refresh_token = self.account_id = None

    def push_events(self, events):
        if len(events) > 100:
            raise SyncError("invalid_event")
        return self._call("/rest/v1/rpc/push_events", {"events": events})

    def pull_events(self, after_sequence, batch_size=200):
        return self._call(
            "/rest/v1/rpc/pull_events",
            {"after_sequence": after_sequence, "batch_size": batch_size},
        )
