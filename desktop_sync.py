"""Optional desktop integration; never uploads the canonical SQLite database."""

from pathlib import Path

from sync_client import SyncWorkspace
from study_sync import StudySync


def workspace_for(store):
    workspace = getattr(store, "study_workspace", None)
    if workspace is None:
        workspace = SyncWorkspace(store.path.with_name("study-sync.sqlite3"))
        store.study_workspace = workspace
    return workspace


def service_for(store):
    service = getattr(store, "study_sync_service", None)
    if service is None:
        service = StudySync(workspace_for(store), store=store)
        store.study_sync_service = service
    return service


def export_workspace(store, destination):
    """Explicit consistent backup of the optional workspace, without credentials."""
    import sqlite3

    source = workspace_for(store)
    path = Path(destination)
    if path.exists():
        raise ValueError("Escolha um arquivo novo para preservar o backup existente.")
    target = sqlite3.connect(path)
    try:
        source.db.backup(target)
    finally:
        target.close()


def capture_session(store, session_id):
    """Capture only sessions recorded through the canonical save flow.

    Retry scanning explicitly repairs a crash between canonical and queue commits.
    Old sessions are never scanned implicitly.
    """
    import json

    if getattr(store, "_applying_sync", False):
        return
    workspace = workspace_for(store)
    if not workspace.account_id:
        return
    row = store.one("SELECT * FROM sessions WHERE id=?", (session_id,))
    if not row:
        return
    link = (
        store.one(
            "SELECT * FROM training_session_links WHERE session_id=?", (session_id,)
        )
        or {}
    )
    payload = {
        key: row.get(key)
        for key in ("plan_id", "subject_id", "topic_id", "day", "category", "elapsed")
    }
    payload.update(lesson_id=link.get("lesson_id"), lesson_version=link.get("version"))
    if str(payload["lesson_id"]).startswith("pessoal."):
        payload.update(lesson_id=None, lesson_version=None)
    previous = workspace.entity("study.session", session_id)
    if (
        previous
        and workspace.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='session_import_baselines'"
        ).fetchone()
        and workspace.db.execute(
            "SELECT 1 FROM session_import_baselines WHERE id=?", (session_id,)
        ).fetchone()
    ):
        # Local topic mapping is presentation/integration, not a remote edit.
        for key in ("plan_id", "subject_id", "topic_id"):
            payload[key] = previous["payload"][key]
    previous_payload = previous["payload"] if previous else None
    for queued in workspace.db.execute(
        "SELECT envelope FROM outbox WHERE status IN ('local','pending') "
        "OR (? AND status='sent') ORDER BY rowid",
        (previous is None,),
    ):
        event = json.loads(queued[0])
        if event["kind"] == "study.session" and event["entity_id"] == session_id:
            previous_payload = event["payload"]
    if previous_payload != payload:
        service_for(store)._enqueue("study.session", session_id, payload)


def capture_new_sessions(store):
    """Recover only IDs absent from the baseline taken at explicit account binding."""
    import json

    workspace = workspace_for(store)
    raw = workspace._meta("session_baseline")
    if raw is None:
        return
    baseline = set(json.loads(raw))
    for row in store.rows("SELECT id FROM sessions"):
        if row["id"] not in baseline:
            capture_session(store, row["id"])


def import_remote_sessions(store):
    """Apply same-ID local sessions; foreign IDs wait for explicit topic mapping."""
    service = service_for(store)
    latest = {}
    for event in service.workspace.events():
        if event["kind"] == "study.session":
            latest[event["entity_id"]] = event
    import json

    waiting = []
    for event in latest.values():
        p = event["payload"]
        key = "session_mapping:" + json.dumps(
            [p["plan_id"], p["subject_id"], p["topic_id"]]
        )
        raw_mapping = service.workspace._meta(key)
        mapping = (
            json.loads(raw_mapping)
            if raw_mapping
            else {k: p[k] for k in ("plan_id", "subject_id", "topic_id")}
        )
        subject = store.one(
            "SELECT plan_id FROM subjects WHERE id=?", (mapping["subject_id"],)
        )
        topic = store.one(
            "SELECT subject_id FROM topics WHERE id=?", (mapping["topic_id"],)
        )
        if (
            not subject
            or not topic
            or subject["plan_id"] != mapping["plan_id"]
            or topic["subject_id"] != mapping["subject_id"]
        ):
            waiting.append(event)
            continue
        store._applying_sync = True
        try:
            service.import_session(event, mapping)
        finally:
            store._applying_sync = False
    return waiting


CATEGORIES = ("Teoria", "Questões", "Revisão", "Simulado")


def _latest_payload(workspace, kind, entity_id):
    """Last payload known for the entity, including actions still queued."""
    import json

    current = workspace.entity(kind, entity_id)
    payload = current["payload"] if current else None
    for row in workspace.db.execute(
        "SELECT envelope FROM outbox WHERE status IN ('local','pending','sent') ORDER BY rowid"
    ):
        event = json.loads(row[0])
        if event["kind"] == kind and event["entity_id"] == entity_id:
            payload = event["payload"]
    return payload


def character_snapshot(store, plan):
    """Appearance, name and equipped item IDs only; no inventory or purchases."""
    from appearance import PREFERENCE, normalize

    look = {
        key: str(value) for key, value in normalize(store.pref(PREFERENCE, {})).items()
    }
    row = store.one("SELECT name FROM rpg_characters WHERE plan_id=?", (plan,))
    name = ((row or {}).get("name") or "Viajante").strip()[:60] or "Viajante"
    equipped = sorted(
        r["item_id"]
        for r in store.rows(
            "SELECT item_id FROM rpg_inventory WHERE plan_id=? AND equipped=1", (plan,)
        )
    )[:20]
    return {"name": name, "look": look, "equipped": equipped}


def cycle_snapshot(store, plan):
    """Read-only picture of the active cycle for the site; never edited remotely."""
    plan_row = store.one("SELECT name FROM plans WHERE id=?", (plan,))
    cycle = store.current_cycle(plan)
    items = []
    if cycle:
        for block in store.cycle_blocks(cycle)[:80]:
            items.append(
                {
                    "subject": str(block["subject"])[:120] or "Matéria",
                    "topic": str(block["topic"])[:200] if block["topic"] else None,
                    "category": (
                        block["category"]
                        if block["category"] in CATEGORIES
                        else "Teoria"
                    ),
                    "target_minutes": max(1, min(600, round(block["target"] / 60))),
                    "done": block["state"] == "Concluído",
                }
            )
    position = min(int(cycle["position"] or 0), len(items)) if cycle else 0
    name = str((plan_row or {}).get("name") or "")[:120]
    return {"plan_name": name, "position": position, "items": items}


FEATURE_KEY = "feature_profile_cycle"


def note_server_features(workspace, transport):
    """Marca se o serviço já aceita perfil/ciclo (migração 009); falha não bloqueia."""
    try:
        summary = transport.progress_summary()
    except Exception:  # noqa: BLE001 - recurso opcional; a sincronização já terminou
        return False
    supported = isinstance(summary, dict) and "victories" in summary
    with workspace.db:
        workspace.db.execute(
            "INSERT OR REPLACE INTO metadata VALUES(?,?)",
            (FEATURE_KEY, "1" if supported else "0"),
        )
    return supported


def capture_profile_and_cycle(store, plan):
    """Queue character/cycle snapshots only when they changed (bound accounts only).

    Só depois de confirmar que o serviço tem a migração 009: um serviço antigo
    recusaria o lote inteiro e travaria a sincronização das outras ações.
    """
    if getattr(store, "_applying_sync", False) or not plan:
        return
    workspace = workspace_for(store)
    if not workspace.account_id or workspace._meta(FEATURE_KEY) != "1":
        return
    service = service_for(store)
    for kind, entity_id, payload in (
        ("profile.character", "profile:character", character_snapshot(store, plan)),
        ("cycle.snapshot", "cycle:current", cycle_snapshot(store, plan)),
    ):
        if _latest_payload(workspace, kind, entity_id) != payload:
            service._enqueue(kind, entity_id, payload)
