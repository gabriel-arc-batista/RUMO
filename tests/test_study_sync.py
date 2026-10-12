import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from study_sync import (
    StudyProjection,
    StudySync,
    card_draft,
    export_cards,
    import_cards,
    schedule_review,
)
from sync_client import SyncWorkspace


class StudyTests(unittest.TestCase):
    def test_question_note_has_one_versioned_origin(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = SyncWorkspace(Path(folder) / "sync.sqlite3")
            study = StudySync(workspace)
            event = study.save_note(
                None, "1.0.0", None, "Minha análise", question_id="q"
            )
            self.assertEqual(event["payload"]["question_id"], "q")
            self.assertIsNone(event["payload"]["lesson_id"])
            self.assertEqual(event["payload"]["version"], "1.0.0")
            with self.assertRaises(ValueError):
                study.save_note("aula", "1", None, "texto", question_id="q")
            with self.assertRaises(ValueError):
                study.save_note(None, "1", 2, "texto", question_id="q")
            workspace.close()

    def test_schedule_and_retry(self):
        db = sqlite3.connect(":memory:")
        projection = StudyProjection(db)
        event = dict(
            id="review-1",
            sequence=1,
            revision=1,
            kind="card.review",
            entity_id="review-1",
            received_at="2026-10-12T12:00:00Z",
            payload=dict(card_id="c", version="1", rating=3, session_id="s"),
        )
        self.assertTrue(projection.apply_event(event))
        self.assertFalse(projection.apply_event(event))
        self.assertEqual(projection.card_schedule("c", "1")["interval"], 1)
        self.assertEqual(projection.session_counts("s")["reviews"], 1)
        second = schedule_review(
            projection.card_schedule("c", "1"), 4, "2026-10-13T12:00:00Z"
        )
        self.assertEqual(second["interval"], 6)
        self.assertEqual(
            schedule_review(second, 1, "2026-10-14T12:00:00Z")["repetitions"], 0
        )

    def test_offline_pages_version_and_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sync.sqlite3"
            workspace = SyncWorkspace(path)
            study = StudySync(workspace)
            study.resume("lesson", "1", 3, 3)
            self.assertFalse(study.reading("lesson", "1", 3)["completed"])
            for page in range(1, 4):
                study.read_page("lesson", "1", page, 3, True)
            self.assertTrue(study.reading("lesson", "1", 3)["completed"])
            self.assertFalse(study.reading("lesson", "2", 3)["completed"])
            study.read_page("lesson", "1", 2, 3, False)
            workspace.db.close()
            reopened = SyncWorkspace(path)
            self.assertEqual(
                StudySync(reopened).reading("lesson", "1", 3)["read_pages"], [1, 3]
            )
            reopened.db.close()

    def test_personal_card_import_is_validated_draft(self):
        draft = card_draft("Resposta", "deck", lesson_id="lesson")
        draft["front"] = "Pergunta"
        exported = export_cards([dict(draft, id="old", revision=4)])
        self.assertEqual(import_cards(exported), [draft])
        malformed = json.loads(exported)
        malformed["cards"][0]["suspended"] = "false"
        with self.assertRaises(ValueError):
            import_cards(json.dumps(malformed))

    def test_local_cas_and_canonical_session_import(self):
        from core import Store

        with tempfile.TemporaryDirectory() as folder:
            workspace = SyncWorkspace(Path(folder) / "sync.sqlite3")
            store = Store(Path(folder) / "study.sqlite3")
            plan = store.save("plans", {"name": "Plano temporário"})
            subject = store.save(
                "subjects", {"plan_id": plan, "name": "Matéria", "color": "#123456"}
            )
            topic = store.save("topics", {"subject_id": subject, "name": "Assunto"})
            study = StudySync(workspace, store)
            first = study.read_page("l", "1", 1, 1, True)
            second = study.read_page("l", "1", 1, 1, False)
            self.assertEqual((first["base_revision"], second["base_revision"]), (0, 1))
            event = dict(
                id="event",
                sequence=1,
                revision=1,
                kind="study.session",
                entity_id="session",
                payload=dict(day="2026-10-12", category="Teoria", elapsed=120),
            )
            mapping = dict(plan_id=plan, subject_id=subject, topic_id=topic)
            study.import_session(event, mapping)
            study.import_session(event, mapping)
            self.assertEqual(store.one("SELECT COUNT(*) n FROM sessions")["n"], 1)
            self.assertEqual(store.one("SELECT SUM(elapsed) n FROM sessions")["n"], 120)
            store.db.close()
            workspace.db.close()

    def test_version_continuity_and_server_result(self):
        projection = StudyProjection(sqlite3.connect(":memory:"))
        for sequence, version in enumerate(("1", "2"), 1):
            projection.apply_event(
                dict(
                    id=f"r{sequence}",
                    sequence=sequence,
                    revision=1,
                    kind="card.review",
                    entity_id=f"r{sequence}",
                    received_at="2026-10-12T12:00:00Z",
                    payload=dict(
                        card_id="c", version=version, rating=3, session_id="s"
                    ),
                )
            )
        self.assertEqual(projection.card_schedule("c", "1")["interval"], 1)
        self.assertEqual(projection.card_schedule("c", "2")["interval"], 6)
        self.assertEqual(
            projection.card_schedule("c", "3"), projection.card_schedule("c", "2")
        )
        self.assertIsNone(projection.card_schedule("unreviewed", "1"))
        self.assertEqual(projection.session_counts("s")["reviews"], 2)
        projection.apply_event(
            dict(
                id="a",
                sequence=3,
                kind="arena.attempt",
                entity_id="a",
                payload=dict(session_id="s"),
                result=dict(status="incorrect"),
            )
        )
        projection.apply_event(
            dict(
                id="b",
                sequence=4,
                kind="arena.attempt",
                entity_id="b",
                payload=dict(session_id="s"),
                result=dict(status="annulled"),
            )
        )
        self.assertEqual(projection.session_counts("s")["wrong"], 1)

    def test_page_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = SyncWorkspace(Path(folder) / "sync.sqlite3")
            with self.assertRaises(ValueError):
                StudySync(workspace).read_page("l", "v", 0, 3, True)
            workspace.db.close()
