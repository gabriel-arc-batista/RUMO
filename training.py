"""Campo de Treinamento: personal reading state and the merged library (no Tk).

The library merges three origins and never confuses them:
- ``catalogo``: lessons of the active public catalog (published or test material);
- ``pessoal``: PDFs imported by the user, identified as personal material;
- ``planejada``: editorial planning shipped with the app (no file, no "Abrir").

Opening, downloading or finishing a lesson grants nothing: study time and
rewards come only from the existing study session flow.
"""

import json
import unicodedata
from datetime import datetime
from pathlib import Path

from core import uid
from training_schema import MAX_TEXT, valid_id, valid_version

CURRICULUM = Path(__file__).parent / "assets" / "training" / "curriculo.json"
FILTERS = ("disponiveis", "baixadas", "andamento", "favoritas", "planejadas")


def fold(text):
    """Accent- and case-insensitive form for local search."""
    return "".join(
        c
        for c in unicodedata.normalize("NFD", (text or "").casefold())
        if not unicodedata.combining(c)
    )


def stamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_curriculum(path=CURRICULUM):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(exams=[], families=[])


class TrainingService:
    def __init__(self, store, content, curriculum=None):
        self.store = store
        self.content = content
        self.curriculum = curriculum if curriculum is not None else load_curriculum()
        self.exams = {e["id"]: e for e in self.curriculum.get("exams", [])}
        self.families = {f["id"]: f for f in self.curriculum.get("families", [])}

    # Personal state -----------------------------------------------------

    def state(self, lesson_id):
        row = self.store.one(
            "SELECT * FROM training_lessons WHERE lesson_id=?", (lesson_id,)
        )

        return row or dict(
            lesson_id=lesson_id,
            favorite=0,
            last_version=None,
            last_opened=None,
            completed_version=None,
            completed_day=None,
        )

    @property
    def sync_service(self):
        from desktop_sync import service_for

        return service_for(self.store)

    def reading(self, lesson_id, version, pages):
        return self.sync_service.reading(lesson_id, version, pages)

    def mark_page(self, lesson_id, version, page, pages, read):
        self.check(lesson_id, version)
        return self.sync_service.read_page(lesson_id, version, page, pages, read)

    def _upsert(self, lesson_id, **values):
        state = dict(self.state(lesson_id), **values)
        with self.store.db:
            self.store.db.execute(
                "INSERT OR REPLACE INTO training_lessons VALUES(?,?,?,?,?,?)",
                (
                    lesson_id,
                    state["favorite"],
                    state["last_version"],
                    state["last_opened"],
                    state["completed_version"],
                    state["completed_day"],
                ),
            )
        return state

    def toggle_favorite(self, lesson_id):
        favorite = bool(self.state(lesson_id)["favorite"])
        for event in self.sync_service.visible_events():
            p = event["payload"]
            if (
                event["kind"] == "favorite.set"
                and p["target_type"] == "lesson"
                and p["target_id"] == lesson_id
            ):
                favorite = p["favorite"]
        self.sync_service.favorite("lesson", lesson_id, "", not favorite)
        state = self._upsert(lesson_id, favorite=0 if favorite else 1)
        return state

    def opened(self, lesson_id, version):
        """Remember the last lesson read; this is not progress nor completion."""
        self.check(lesson_id, version)
        return self._upsert(lesson_id, last_version=version, last_opened=stamp())

    def set_completed(self, lesson_id, version, done=True):
        """Manual 'leitura concluída' for this version; idempotent, no reward."""
        self.check(lesson_id, version)
        return self._upsert(
            lesson_id,
            completed_version=version if done else None,
            completed_day=self.store.today().isoformat() if done else None,
        )

    def position(self, lesson_id, version):
        row = self.store.one(
            "SELECT * FROM training_positions WHERE lesson_id=? AND version=?",
            (lesson_id, version),
        )
        latest = None
        for event in self.sync_service.visible_events():
            if (
                event["kind"] == "reading.position"
                and event["entity_id"] == f"{lesson_id}:{version}:position"
            ):
                latest = event
        if latest:
            return dict(latest["payload"], updated="")
        return row

    def save_position(self, lesson_id, version, page, pages=None):
        self.check(lesson_id, version)
        page = max(1, int(page))
        if pages:
            self.sync_service.resume(lesson_id, version, page, pages)
        with self.store.db:
            self.store.db.execute(
                "INSERT OR REPLACE INTO training_positions VALUES(?,?,?,?,?)",
                (lesson_id, version, page, pages, stamp()),
            )
        # The version being read is remembered so an update can show where you were.
        self._upsert(lesson_id, last_version=version)

    def bookmarks(self, lesson_id, version):
        rows = self.store.rows(
            "SELECT * FROM training_bookmarks WHERE lesson_id=? AND version=? ORDER BY page",
            (lesson_id, version),
        )
        by_page = {row["page"]: row for row in rows}
        prefix = f"{lesson_id}:{version}:page:"
        for event in self.sync_service.visible_events():
            p = event["payload"]
            if (
                event["kind"] != "favorite.set"
                or p.get("target_type") != "bookmark"
                or not p["target_id"].startswith(prefix)
            ):
                continue
            page = int(p["target_id"][len(prefix) :])
            if p["favorite"]:
                by_page[page] = dict(
                    id=event["entity_id"],
                    lesson_id=lesson_id,
                    version=version,
                    page=page,
                    label="",
                    created=event.get("received_at", ""),
                )
            else:
                by_page.pop(page, None)
        return [by_page[page] for page in sorted(by_page)]

    def toggle_bookmark(self, lesson_id, version, page, label=""):
        self.check(lesson_id, version)
        favorite = not any(
            row["page"] == page for row in self.bookmarks(lesson_id, version)
        )
        self.sync_service.favorite(
            "bookmark", f"{lesson_id}:{version}:page:{page}", version, favorite
        )
        with self.store.db:
            self.store.db.execute(
                "DELETE FROM training_bookmarks WHERE lesson_id=? AND version=? AND page=?",
                (lesson_id, version, page),
            )
            if favorite:
                self.store.db.execute(
                    "INSERT INTO training_bookmarks VALUES(?,?,?,?,?,?)",
                    (uid(), lesson_id, version, int(page), label[:200], stamp()),
                )
        return favorite

    def notes(self, lesson_id):
        """All notes of a lesson, every version, newest first."""
        rows = self.store.rows(
            "SELECT * FROM training_notes WHERE lesson_id=? ORDER BY updated DESC",
            (lesson_id,),
        )
        notes = {r["id"]: r for r in rows}
        local_ids = {
            row[0]
            for row in self.sync_service.workspace.db.execute(
                "SELECT id FROM outbox WHERE status='local'"
            )
        }
        for event in self.sync_service.visible_events():
            p = event["payload"]
            if (
                event["id"] in local_ids
                or event["kind"] != "note.save"
                or p["lesson_id"] != lesson_id
            ):
                continue
            if p["deleted"]:
                notes.pop(event["entity_id"], None)
            else:
                notes[event["entity_id"]] = dict(
                    p,
                    id=event["entity_id"],
                    created=event.get("received_at", ""),
                    updated=event.get("received_at", ""),
                )
        return list(notes.values())

    def save_note(self, lesson_id, version, text, page=None, note_id=None):
        self.check(lesson_id, version)
        text = (text or "").strip()
        if not text:
            raise ValueError("Escreva a nota antes de salvar.")
        if len(text) > MAX_TEXT:
            raise ValueError("Nota longa demais.")
        editing = note_id is not None
        note_id = note_id or uid()
        self.sync_service.save_note(lesson_id, version, page, text, note_id=note_id)
        with self.store.db:
            if editing:
                self.store.db.execute(
                    "UPDATE training_notes SET text=?,updated=? WHERE id=? AND lesson_id=?",
                    (text, stamp(), note_id, lesson_id),
                )
            else:
                self.store.db.execute(
                    "INSERT INTO training_notes VALUES(?,?,?,?,?,?,?)",
                    (note_id, lesson_id, version, page, text, stamp(), stamp()),
                )
        return note_id

    def delete_note(self, note_id):
        existing = self.store.one("SELECT * FROM training_notes WHERE id=?", (note_id,))
        if not existing:
            for event in self.sync_service.visible_events():
                if event["kind"] == "note.save" and event["entity_id"] == note_id:
                    existing = event["payload"]
        if existing:
            self.sync_service.save_note(
                existing["lesson_id"],
                existing["version"],
                existing["page"],
                "",
                note_id=note_id,
                deleted=True,
            )
        with self.store.db:
            self.store.db.execute("DELETE FROM training_notes WHERE id=?", (note_id,))

    def studied_seconds(self, lesson_id):
        row = self.store.one(
            "SELECT COALESCE(SUM(s.elapsed),0) n, COUNT(*) c FROM training_session_links l "
            "JOIN sessions s ON s.id=l.session_id WHERE l.lesson_id=?",
            (lesson_id,),
        )
        return row["n"], row["c"]

    def reading_versions(self, lesson_id):
        return self.sync_service.reading_versions(lesson_id)

    def carry_reading(self, lesson_id, version, pages, chosen):
        self.check(lesson_id, version)
        return self.sync_service.carry_reading(lesson_id, version, pages, chosen)

    @staticmethod
    def check(lesson_id, version):
        if not valid_id(lesson_id) or not valid_version(version):
            raise ValueError("Aula ou versão inválida.")

    # Personal imports ------------------------------------------------------

    def import_personal(self, path, title, subject="", topic=""):
        title = (title or "").strip() or Path(path).stem
        sha, size, name = self.content.import_pdf(path)
        lesson_id = "pessoal." + sha[:16]
        with self.store.db:
            self.store.db.execute(
                "INSERT OR REPLACE INTO training_personal VALUES(?,?,?,?,?,?,?,?)",
                (
                    lesson_id,
                    title[:300],
                    subject[:300],
                    topic[:300],
                    sha,
                    size,
                    name,
                    stamp(),
                ),
            )
        return lesson_id

    def remove_personal(self, lesson_id):
        """Forget an imported file; its notes and progress remain unless deleted."""
        row = self.store.one("SELECT * FROM training_personal WHERE id=?", (lesson_id,))
        if not row:
            return
        others = self.store.one(
            "SELECT COUNT(*) n FROM training_personal WHERE filename=? AND id<>?",
            (row["filename"], lesson_id),
        )["n"]
        with self.store.db:
            self.store.db.execute(
                "DELETE FROM training_personal WHERE id=?", (lesson_id,)
            )
        path = self.content.personal_file(row["filename"])
        if path and not others:
            path.unlink(missing_ok=True)

    # Library -------------------------------------------------------------

    def library(self):
        """Every lesson known locally, as plain dicts for the screen."""
        catalog = self.content.catalog()
        lessons = []
        seen = set()
        if catalog:
            subjects = {s["id"]: s for s in catalog["subjects"]}
            topics = {t["id"]: t for t in catalog["topics"]}
            for lesson in catalog["lessons"]:
                topic = topics[lesson["primary_topic_id"]]
                lessons.append(
                    self._catalog_view(
                        lesson, topic, subjects[topic["subject_id"]], catalog
                    )
                )
                seen.add(lesson["id"])
        for row in self.store.rows(
            "SELECT * FROM training_personal ORDER BY imported DESC"
        ):
            lessons.append(self._personal_view(row))
        for family in self.families.values():
            for planned in family["lessons"]:
                if planned["id"] not in seen:
                    lessons.append(self._planned_view(planned, family))
        states = {
            r["lesson_id"]: r for r in self.store.rows("SELECT * FROM training_lessons")
        }
        positions = {}
        for r in self.store.rows("SELECT * FROM training_positions"):
            positions[(r["lesson_id"], r["version"])] = r
        for lesson in lessons:
            self._personalize(lesson, states.get(lesson["id"]), positions)
        return lessons

    def _catalog_view(self, lesson, topic, subject, catalog):
        family = self.families.get(subject["id"])
        return dict(
            lesson,
            origin="catalogo",
            test=catalog["kind"] == "teste",
            catalog_id=catalog["catalog_id"],
            version=(
                lesson["resource"]["version"]
                if lesson["resource"]
                else lesson["content_version"]
            ),
            subject_id=subject["id"],
            subject=subject["name"],
            area=family["area"] if family else "",
            topic_id=topic["id"],
            topic=topic["name"],
            exam_ids=sorted(
                {c["exam_id"] for c in lesson["coverage_links"]}
                | {c["exam_id"] for c in (family or {}).get("candidates", [])}
            ),
            availability=self.content.availability(lesson),
        )

    def _personal_view(self, row):
        path = self.content.personal_file(row["filename"])
        return dict(
            id=row["id"],
            title=row["title"],
            origin="pessoal",
            test=False,
            publication_status="pessoal",
            version="1",
            content_version="1",
            subject_id="pessoal",
            subject=row["subject"] or "Material pessoal",
            area="Material pessoal",
            topic_id="pessoal",
            topic=row["topic"] or "Sem assunto",
            summary="PDF importado por você. Não passou pela revisão do catálogo e não conta como cobertura.",
            objectives=[],
            prerequisite_lesson_ids=[],
            authors=[],
            review=dict(status="pendente", reviewer=None, reviewed_at=None),
            resource=dict(
                bytes=row["bytes"], sha256=row["sha256"], page_count=None, license=""
            ),
            license="",
            sources=[],
            coverage_links=[],
            exam_ids=[],
            availability="disponivel" if path else "arquivo_ausente",
            path=str(path) if path else None,
            imported=row["imported"],
        )

    def _planned_view(self, planned, family):
        return dict(
            id=planned["id"],
            title=planned["title"],
            origin="planejada",
            test=False,
            publication_status="planejada",
            version="0",
            content_version="0",
            subject_id=family["id"],
            subject=family["name"],
            area=family["area"],
            topic_id=planned["topic_id"],
            topic=planned["title"],
            summary="",
            objectives=[],
            prerequisite_lesson_ids=[],
            authors=[],
            review=dict(status="pendente", reviewer=None, reviewed_at=None),
            resource=None,
            license="",
            sources=[],
            coverage_links=[],
            candidates=family["candidates"],
            exam_ids=sorted({c["exam_id"] for c in family["candidates"]}),
            availability="nao_publicada",
        )

    def _personalize(self, lesson, state, positions):
        state = state or {}
        lesson["favorite"] = bool(state.get("favorite"))
        for event in self.sync_service.visible_events():
            p = event["payload"]
            if (
                event["kind"] == "favorite.set"
                and p["target_type"] == "lesson"
                and p["target_id"] == lesson["id"]
            ):
                lesson["favorite"] = p["favorite"]
        lesson["last_opened"] = state.get("last_opened")
        lesson["completed"] = state.get("completed_version") == lesson["version"]
        lesson["completed_version"] = state.get("completed_version")
        position = self.position(lesson["id"], lesson["version"])
        if not position and state.get("last_version"):
            position = positions.get((lesson["id"], state["last_version"]))
        lesson["position"] = position
        pages = (lesson.get("resource") or {}).get("page_count") or (
            position.get("pages") if position else None
        )
        lesson["legacy_completed"] = lesson["completed"]
        reading = self.reading(lesson["id"], lesson["version"], pages) if pages else {}
        lesson["completed"] = bool(reading.get("completed"))
        lesson["read_pages"] = reading.get("read_pages", [])
        lesson["openable"] = lesson["origin"] != "planejada" and lesson[
            "availability"
        ] in (
            "disponivel",
            "atualizacao_disponivel",
        )
        lesson["in_progress"] = bool(position) and not lesson["completed"]

    def filtered(self, lessons, view="disponiveis", query="", exam_id=None):
        """Apply the screen's filter, the edital-alvo and the text search."""
        terms = fold(query).split()
        result = []
        for lesson in lessons:
            if exam_id and exam_id not in lesson["exam_ids"]:
                continue
            if not self._in_view(lesson, view):
                continue
            haystack = fold(
                " ".join(
                    (
                        lesson["title"],
                        lesson["subject"],
                        lesson["topic"],
                        lesson["area"],
                    )
                )
            )
            if all(term in haystack for term in terms):
                result.append(lesson)
        return result

    @staticmethod
    def _in_view(lesson, view):
        if view == "planejadas":
            return lesson["origin"] == "planejada"
        if lesson["origin"] == "planejada":
            return False
        if view == "baixadas":
            return lesson["openable"]
        if view == "andamento":
            return lesson["in_progress"] and lesson["openable"]
        if view == "favoritas":
            return lesson["favorite"]
        return True

    @staticmethod
    def continue_reading(lessons):
        """The last lesson opened that can still be opened (never a planned one)."""
        candidates = [l for l in lessons if l["openable"] and l["last_opened"]]
        return max(candidates, key=lambda l: l["last_opened"], default=None)

    def file_for(self, lesson):
        """Local PDF to open: current version, else the newest one downloaded."""
        if lesson["origin"] == "pessoal":
            return (
                (Path(lesson["path"]), lesson["version"])
                if lesson.get("path")
                else (None, None)
            )
        if not lesson.get("resource"):
            return None, None
        current = self.content.file_for(lesson["id"], lesson["resource"])
        if current.is_file():
            return current, lesson["resource"]["version"]
        versions = self.content.local_versions(lesson["id"])
        if versions:
            version = sorted(versions)[-1]
            return versions[version], version
        return None, None

    def exam_summary(self, exam_id, lessons):
        """Objective numbers for an edital; no coverage percentage is computed."""
        exam = self.exams[exam_id]
        items = sum(len(d["items"]) for d in exam["disciplines"])
        related = [l for l in lessons if exam_id in l["exam_ids"]]
        return dict(
            disciplines=len(exam["disciplines"]),
            items=items,
            available=sum(
                1
                for l in related
                if l["origin"] == "catalogo"
                and not l["test"]
                and l["publication_status"] == "publicada"
            ),
            planned=sum(1 for l in related if l["origin"] == "planejada"),
        )


def subject_match(store, plan, name):
    """Plan subject whose name matches a lesson subject (accent-insensitive)."""
    wanted = fold(name)
    rows = store.rows(
        "SELECT id,name FROM subjects WHERE plan_id=? AND archived=0", (plan,)
    )
    for row in rows:
        if fold(row["name"]) == wanted:
            return row["id"]
    for row in rows:
        if wanted and (wanted in fold(row["name"]) or fold(row["name"]) in wanted):
            return row["id"]
    return None


def topic_match(store, subject_id, name):
    """Leaf topic of that subject with the same name, ignoring numbering and accents."""
    import re

    wanted = re.sub(r"^[\d.\s]+", "", fold(name)).strip()
    if not wanted:
        return None
    rows = store.rows(
        "SELECT id,name FROM topics WHERE subject_id=? AND archived=0", (subject_id,)
    )
    for row in rows:
        if re.sub(r"^[\d.\s]+", "", fold(row["name"])).strip() == wanted:
            return row["id"]
    return None
