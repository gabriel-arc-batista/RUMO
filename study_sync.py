"""Study projections for the opt-in workspace; never migrate the personal Store."""

import json
import math
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone


def schedule_review(previous, rating, reviewed_at):
    """Deterministic SM-2 adaptation; authoritative date comes from the server."""
    if type(rating) is not int or rating not in (1, 2, 3, 4):
        raise ValueError("Avaliação inválida.")
    stamp = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Revisão exige data com fuso horário.")
    previous = previous or {}
    ease = float(previous.get("ease", 2.5))
    repetitions = int(previous.get("repetitions", 0))
    interval = int(previous.get("interval", 0))
    quality = {1: 1, 2: 3, 3: 4, 4: 5}[rating]
    if rating == 1:
        repetitions, interval = 0, 1
    else:
        interval = (
            1
            if repetitions == 0
            else 6 if repetitions == 1 else max(1, math.floor(interval * ease + 0.5))
        )
        repetitions += 1
    ease = max(1.3, ease + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return dict(
        ease=round(ease, 4),
        repetitions=repetitions,
        interval=interval,
        due=(stamp.astimezone(timezone.utc) + timedelta(days=interval)).isoformat(),
    )


class StudyProjection:
    """A replayable, isolated projection of server-accepted events."""

    def __init__(self, connection):
        self.db = connection
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS study_events(id TEXT PRIMARY KEY, sequence INTEGER UNIQUE, body TEXT NOT NULL)"
        )

    def apply_event(self, event):
        existing = self.db.execute(
            "SELECT body FROM study_events WHERE id=?", (event["id"],)
        ).fetchone()
        body = json.dumps(event, sort_keys=True, ensure_ascii=False)
        if existing:
            if existing[0] != body:
                raise ValueError("event_mismatch")
            return False
        self.db.execute(
            "INSERT INTO study_events VALUES(?,?,?)",
            (event["id"], event["sequence"], body),
        )
        return True

    def events(self):
        return [
            json.loads(row[0])
            for row in self.db.execute(
                "SELECT body FROM study_events ORDER BY sequence"
            )
        ]

    def entity(self, kind, entity_id):
        rows = [
            e
            for e in self.events()
            if e["kind"] == kind and e["entity_id"] == entity_id
        ]
        return rows[-1] if rows else None

    def reading(self, lesson_id, version, pages):
        read, position = set(), 1
        for event in self.events():
            p = event["payload"]
            if p.get("lesson_id") != lesson_id or p.get("version") != version:
                continue
            if event["kind"] == "reading.page":
                if p["read"]:
                    read.add(p["page"])
                else:
                    read.discard(p["page"])
            elif event["kind"] == "reading.position":
                position = p["page"]
        return dict(
            pages_read=sorted(read),
            page=position,
            complete=set(range(1, pages + 1)).issubset(read),
        )

    def cards(self, query="", include_suspended=False):
        cards = {}
        for event in self.events():
            if event["kind"] == "card.save":
                cards[event["entity_id"]] = dict(
                    event["payload"],
                    id=event["entity_id"],
                    revision=event.get("revision", 0),
                )
        return [
            c
            for c in cards.values()
            if not c.get("deleted")
            and (include_suspended or not c.get("suspended"))
            and query.casefold() in (c["front"] + " " + c["back"]).casefold()
        ]

    def card_schedule(self, card_id, version):
        states, latest = {}, None
        for event in self.events():
            p = event["payload"]
            if event["kind"] == "card.review" and p["card_id"] == card_id:
                current_version = p["version"]
                state = schedule_review(
                    states.get(current_version, latest),
                    p["rating"],
                    event["received_at"],
                )
                states[current_version] = latest = state
        return states.get(version, latest)

    def session_counts(self, session_id):
        counts = dict(correct=0, wrong=0, blank=0, reviews=0)
        for event in self.events():
            if event["payload"].get("session_id") != session_id:
                continue
            if event["kind"] == "card.review":
                counts["reviews"] += 1
            elif event["kind"] == "arena.attempt":
                result = event.get("result", event["payload"].get("result"))
                if isinstance(result, dict):
                    result = result.get("status", result.get("result"))
                if result in ("correct", "wrong", "incorrect"):
                    counts["wrong" if result == "incorrect" else result] += 1
        return counts


class StudySync:
    """Small local command facade. Queue owns persistence and CAS validation."""

    def __init__(self, workspace, store=None):
        self.workspace, self.store = workspace, store
        self.projection = StudyProjection(workspace.db)
        with workspace.db:
            for event in workspace.events():
                self.projection.apply_event(event)
        if hasattr(workspace, "set_projector"):
            workspace.set_projector(self.projection.apply_event)

    def _enqueue(self, kind, entity_id, payload, base_revision=None):
        if base_revision is None:
            current = self.workspace.entity(kind, entity_id)
            base_revision = current.get("revision", 0) if current else 0
            known = {e["id"] for e in self.workspace.events()}
            for row in self.workspace.db.execute(
                "SELECT envelope FROM outbox WHERE "
                "(? AND status IN ('pending','sent')) OR (NOT ? AND status='local') ORDER BY rowid",
                (bool(self.workspace.account_id), bool(self.workspace.account_id)),
            ):
                queued = json.loads(row[0])
                if (
                    queued["id"] not in known
                    and queued["kind"] == kind
                    and queued["entity_id"] == entity_id
                ):
                    base_revision = max(base_revision, queued["base_revision"] + 1)
        return self.workspace.enqueue(
            kind,
            entity_id,
            payload,
            base_revision=base_revision,
            local_only=(
                str(payload.get("lesson_id", "")).startswith("pessoal.")
                or str(payload.get("target_id", "")).startswith("pessoal.")
            ),
        )

    def visible_events(self):
        events = self.workspace.events()
        known = {e["id"] for e in events}
        for row in self.workspace.db.execute(
            "SELECT envelope FROM outbox WHERE status IN ('local','pending','sent') ORDER BY rowid"
        ):
            event = json.loads(row[0])
            if event["id"] not in known:
                events.append(event)
        return events

    def reading(self, lesson_id, version, pages):
        self._page(1, pages)
        read, position = set(), 1
        events = self.visible_events()
        for event in events:
            p = event["payload"]
            if p.get("lesson_id") != lesson_id or p.get("version") != version:
                continue
            if event["kind"] == "reading.page":
                if p["read"]:
                    read.add(p["page"])
                else:
                    read.discard(p["page"])
            elif event["kind"] == "reading.position":
                position = p["page"]
        return dict(
            read_pages=sorted(read),
            position=position,
            completed=set(range(1, pages + 1)).issubset(read),
        )

    def reading_versions(self, lesson_id):
        """Páginas lidas em cada versão da aula (histórico preservado por versão)."""
        versions = {}
        for event in self.visible_events():
            p = event["payload"]
            if event["kind"] != "reading.page" or p.get("lesson_id") != lesson_id:
                continue
            pages = versions.setdefault(p["version"], set())
            (pages.add if p["read"] else pages.discard)(p["page"])
        return {version: sorted(pages) for version, pages in versions.items() if pages}

    def carry_reading(self, lesson_id, target, pages, chosen):
        """Marca na versão ``target`` só as páginas escolhidas pela pessoa.

        Nunca é automático: a correspondência entre versões é confirmada na tela.
        Marcações da versão anterior continuam como estão (histórico preservado).
        """
        done = set(self.reading(lesson_id, target, pages)["read_pages"])
        marked = []
        for page in sorted(set(chosen)):
            if type(page) is int and 1 <= page <= pages and page not in done:
                self.read_page(lesson_id, target, page, pages, True)
                marked.append(page)
        return marked

    def read_page(self, lesson_id, version, page, pages, read, base_revision=None):
        self._page(page, pages)
        if type(read) is not bool:
            raise ValueError("Marcação inválida.")
        return self._enqueue(
            "reading.page",
            f"{lesson_id}:{version}:page:{page}",
            dict(
                lesson_id=lesson_id, version=version, page=page, pages=pages, read=read
            ),
            base_revision,
        )

    @staticmethod
    def _page(page, pages):
        if type(page) is not int or type(pages) is not int or not 1 <= page <= pages:
            raise ValueError("Página inválida.")

    def resume(self, lesson_id, version, page, pages):
        self._page(page, pages)
        return self._enqueue(
            "reading.position",
            f"{lesson_id}:{version}:position",
            dict(lesson_id=lesson_id, version=version, page=page, pages=pages),
        )

    def save_note(
        self,
        lesson_id,
        version,
        page,
        text,
        note_id=None,
        deleted=False,
        base_revision=None,
        question_id=None,
    ):
        if (lesson_id is None) == (question_id is None):
            raise ValueError("Escolha uma aula ou uma questão para a anotação.")
        if question_id is not None and page is not None:
            raise ValueError("Anotação de questão não possui página.")
        payload = dict(
            lesson_id=lesson_id, version=version, page=page, text=text, deleted=deleted
        )
        if question_id is not None:
            payload["question_id"] = question_id
        return self._enqueue(
            "note.save",
            note_id or str(uuid.uuid4()),
            payload,
            base_revision,
        )

    def favorite(self, target_type, target_id, version, favorite):
        return self._enqueue(
            "favorite.set",
            f"{target_type}:{target_id}:{version}:favorite",
            dict(
                target_type=target_type,
                target_id=target_id,
                version=version,
                favorite=favorite,
            ),
        )

    def cards(self, query="", include_suspended=False):
        cards = {card["id"]: card for card in self.projection.cards("", True)}
        for row in self.workspace.db.execute(
            "SELECT envelope FROM outbox WHERE status IN ('local','pending','sent') ORDER BY rowid"
        ):
            event = json.loads(row[0])
            if event["kind"] == "card.save":
                cards[event["entity_id"]] = dict(
                    event["payload"],
                    id=event["entity_id"],
                    revision=event["base_revision"] + 1,
                )
        return [
            card
            for card in cards.values()
            if not card.get("deleted")
            and (include_suspended or not card.get("suspended"))
            and query.casefold() in (card["front"] + " " + card["back"]).casefold()
        ]

    def export_personal_cards(self):
        return export_cards(self.cards(include_suspended=True))

    def import_personal_cards(self, text):
        """Call only after explicit user confirmation of the imported drafts."""
        cards = import_cards(text)
        return [self.save_card(card) for card in cards]

    def save_card(self, payload, card_id=None, base_revision=None):
        validate_card(payload)
        return self._enqueue(
            "card.save", card_id or str(uuid.uuid4()), payload, base_revision
        )

    def review_card(self, card_id, version, rating, session_id):
        if type(rating) is not int or rating not in (1, 2, 3, 4):
            raise ValueError("Avaliação inválida.")
        return self._enqueue(
            "card.review",
            str(uuid.uuid4()),
            dict(
                card_id=card_id, version=version, rating=rating, session_id=session_id
            ),
            0,
        )

    def attempt(self, question_id, version, answer, session_id):
        return self._enqueue(
            "arena.attempt",
            str(uuid.uuid4()),
            dict(
                question_id=question_id,
                version=version,
                answer=answer,
                session_id=session_id,
            ),
            0,
        )

    def import_session(self, event, mapping):
        """Explicitly map remote IDs to existing local IDs; Store remains canonical.

        Called after a successful pull, never inside the workspace transaction.
        Reapplying updates the same session ID rather than creating another one.
        """
        if self.store is None or event["kind"] != "study.session":
            raise ValueError("Sessão ou Store indisponível.")
        # A remote replay cannot overwrite an unresolved local edit.
        if self.workspace.db.execute(
            "SELECT 1 FROM outbox WHERE json_extract(envelope,'$.kind')='study.session' "
            "AND json_extract(envelope,'$.entity_id')=? "
            "AND (status IN ('local','pending','conflict') OR "
            "(status='sent' AND json_extract(envelope,'$.base_revision')>=?)) LIMIT 1",
            (event["entity_id"], event.get("revision", 2**63 - 1)),
        ).fetchone():
            return event["entity_id"]
        p = event["payload"]
        counts = self.projection.session_counts(event["entity_id"])
        self._ensure_import_schema()
        existing = (
            self.store.one("SELECT * FROM sessions WHERE id=?", (event["entity_id"],))
            or {}
        )
        self._recover_import_counts(event["entity_id"], existing)
        with self.workspace.db:
            self.workspace.db.execute(
                "INSERT OR IGNORE INTO session_import_baselines"
                "(id,correct,wrong,blank,last_correct,last_wrong,last_blank) VALUES(?,?,?,?,0,0,0)",
                (
                    event["entity_id"],
                    existing.get("correct", 0),
                    existing.get("wrong", 0),
                    existing.get("blank", 0),
                ),
            )
        baseline = self.workspace.db.execute(
            "SELECT * FROM session_import_baselines WHERE id=?",
            (event["entity_id"],),
        ).fetchone()
        manual = {}
        for key in ("correct", "wrong", "blank"):
            previous_remote = baseline["last_" + key]
            if previous_remote is None:
                # Upgrade an older sidecar using the totals already integrated locally.
                previous_remote = max(0, existing.get(key, 0) - baseline[key])
            adjustment = existing.get(key, 0) - (baseline[key] + previous_remote)
            manual[key] = max(0, baseline[key] + adjustment)
        values = dict(
            existing,
            id=event["entity_id"],
            plan_id=mapping["plan_id"],
            subject_id=mapping["subject_id"],
            topic_id=mapping["topic_id"],
            day=p["day"],
            category=p["category"],
            elapsed=p["elapsed"],
            target=existing.get("target", 0),
            correct=manual["correct"] + counts["correct"],
            wrong=manual["wrong"] + counts["wrong"],
            blank=manual["blank"] + counts["blank"],
        )
        context = {k: p[k] for k in ("lesson_id", "lesson_version") if p.get(k)}
        results = self.store.rows(
            "SELECT * FROM mock_results WHERE session_id=?", (event["entity_id"],)
        )
        if results and any(counts[key] for key in ("correct", "wrong", "blank")):
            # Preserve the existing subject breakdown until explicitly reconciled.
            return event["entity_id"]
        journal = dict(
            before={key: existing.get(key, 0) for key in ("correct", "wrong", "blank")},
            after={key: values[key] for key in ("correct", "wrong", "blank")},
            manual=manual,
            remote={key: counts[key] for key in ("correct", "wrong", "blank")},
        )
        with self.workspace.db:
            self.workspace.db.execute(
                "INSERT INTO session_import_journal VALUES(?,?)",
                (event["entity_id"], json.dumps(journal)),
            )
        applying = getattr(self.store, "_applying_sync", False)
        self.store._applying_sync = True
        try:
            sid = self.store.save_session(values, context=context, results=results)
        finally:
            self.store._applying_sync = applying
        self._finish_import_counts(sid, manual, counts)
        return sid

    def _ensure_import_schema(self):
        self.workspace.db.execute(
            "CREATE TABLE IF NOT EXISTS session_import_baselines("
            "id TEXT PRIMARY KEY, correct INTEGER NOT NULL, wrong INTEGER NOT NULL, blank INTEGER NOT NULL,"
            "last_correct INTEGER, last_wrong INTEGER, last_blank INTEGER)"
        )
        columns = {
            row[1]
            for row in self.workspace.db.execute(
                "PRAGMA table_info(session_import_baselines)"
            )
        }
        for column in ("last_correct", "last_wrong", "last_blank"):
            if column not in columns:
                self.workspace.db.execute(
                    "ALTER TABLE session_import_baselines ADD COLUMN "
                    + column
                    + " INTEGER"
                )
        self.workspace.db.execute(
            "CREATE TABLE IF NOT EXISTS session_import_journal(id TEXT PRIMARY KEY,body TEXT NOT NULL)"
        )

    def _finish_import_counts(self, sid, manual, counts):
        with self.workspace.db:
            self.workspace.db.execute(
                "UPDATE session_import_baselines SET correct=?,wrong=?,blank=?,"
                "last_correct=?,last_wrong=?,last_blank=? WHERE id=?",
                (
                    manual["correct"],
                    manual["wrong"],
                    manual["blank"],
                    counts["correct"],
                    counts["wrong"],
                    counts["blank"],
                    sid,
                ),
            )
            self.workspace.db.execute(
                "DELETE FROM session_import_journal WHERE id=?", (sid,)
            )

    def _recover_import_counts(self, sid, existing):
        row = self.workspace.db.execute(
            "SELECT body FROM session_import_journal WHERE id=?", (sid,)
        ).fetchone()
        if not row:
            return
        journal = json.loads(row[0])
        current = {key: existing.get(key, 0) for key in ("correct", "wrong", "blank")}
        if current == journal["after"]:
            self._finish_import_counts(sid, journal["manual"], journal["remote"])
        elif current == journal["before"]:
            with self.workspace.db:
                self.workspace.db.execute(
                    "DELETE FROM session_import_journal WHERE id=?", (sid,)
                )
        else:
            raise ValueError(
                "As contagens locais mudaram durante a recuperação. Reconcilie esta sessão explicitamente antes de importar novamente."
            )

    def reconcile_import_counts(self, sid, *, consent=False):
        """Keep current local totals only after an explicit reconciliation choice."""
        if not consent:
            raise ValueError("A reconciliação exige confirmação explícita.")
        self._ensure_import_schema()
        row = self.workspace.db.execute(
            "SELECT body FROM session_import_journal WHERE id=?", (sid,)
        ).fetchone()
        existing = (
            self.store.one("SELECT * FROM sessions WHERE id=?", (sid,))
            if self.store
            else None
        )
        if not row or not existing:
            raise ValueError("Sessão sem recuperação pendente.")
        remote = json.loads(row[0])["remote"]
        if any(existing[key] < remote[key] for key in ("correct", "wrong", "blank")):
            raise ValueError(
                "As contagens devem incluir as tentativas remotas aceitas."
            )
        manual = {
            key: existing[key] - remote[key] for key in ("correct", "wrong", "blank")
        }
        self._finish_import_counts(sid, manual, remote)
        return sid


def validate_card(card):
    fields = {
        "deck_id",
        "front",
        "back",
        "explanation",
        "source",
        "lesson_id",
        "question_id",
        "suspended",
        "deleted",
    }
    if not isinstance(card, dict) or set(card) != fields:
        raise ValueError("Campos do cartão inválidos.")
    for key in ("front", "back", "deck_id"):
        if (
            not isinstance(card[key], str)
            or not card[key].strip()
            or len(card[key]) > 20000
        ):
            raise ValueError("Texto do cartão inválido.")
    for key in ("explanation", "source"):
        if not isinstance(card[key], str) or len(card[key]) > 20000:
            raise ValueError("Texto do cartão inválido.")
    for key in ("lesson_id", "question_id"):
        if card[key] is not None and (
            not isinstance(card[key], str) or len(card[key]) > 20000
        ):
            raise ValueError("Vínculo inválido.")
    if any(type(card[key]) is not bool for key in ("suspended", "deleted")):
        raise ValueError("Estado inválido.")


def card_draft(text, deck_id, lesson_id=None, question_id=None):
    """Return a draft only: the caller must present it for editing before save."""
    return dict(
        deck_id=deck_id,
        front="",
        back=text,
        explanation="",
        source="",
        lesson_id=lesson_id,
        question_id=question_id,
        suspended=False,
        deleted=False,
    )


def export_cards(cards):
    return json.dumps(
        dict(format="RUMO-personal-cards", version=1, cards=cards),
        ensure_ascii=False,
        indent=2,
    )


def import_cards(text):
    if len(text.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("Arquivo de cartões muito grande.")
    data = json.loads(text)
    if (
        data.get("format") != "RUMO-personal-cards"
        or data.get("version") != 1
        or not isinstance(data.get("cards"), list)
        or len(data["cards"]) > 1000
    ):
        raise ValueError("Formato de cartões inválido.")
    cards = []
    for item in data["cards"]:
        card = {k: v for k, v in item.items() if k not in ("id", "revision")}
        validate_card(card)
        cards.append(card)
    return cards
