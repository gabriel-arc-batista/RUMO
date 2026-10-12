import json
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from core import Store
from desktop_sync import capture_new_sessions, service_for, workspace_for
from training import TrainingService
from sync_client import SyncError


class DesktopSyncTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.folder.name) / "study.sqlite3")
        self.plan = self.store.save("plans", dict(name="Exemplo"))
        self.subject = self.store.save(
            "subjects", dict(plan_id=self.plan, name="Exemplo", color="#D6B467")
        )
        self.topic = self.store.save(
            "topics", dict(subject_id=self.subject, name="Exemplo")
        )
        self.workspace = workspace_for(self.store)
        self.service = service_for(self.store)

    def tearDown(self):
        self.workspace.close()
        self.store.db.close()
        self.folder.cleanup()

    def session(self, sid=None, **changes):
        v = dict(
            id=sid or uuid.uuid4().hex,
            plan_id=self.plan,
            subject_id=self.subject,
            topic_id=self.topic,
            day="2026-10-12",
            category="Questões",
            elapsed=600,
            target=0,
            correct=4,
            wrong=2,
            blank=0,
        )
        v.update(changes)
        return self.store.save_session(v)

    def test_binding_does_not_send_history_or_personal_pdfs(self):
        sid = self.session()
        self.service.read_page("lesson", "1", 1, 2, True)
        self.workspace.bind_account(str(uuid.uuid4()), consent=True)
        self.assertEqual(self.workspace.pending(), [])
        self.service.read_page("pessoal.example", "1", 1, 2, True)
        self.assertEqual(self.workspace.pending(), [])
        self.session(sid, elapsed=660)
        pending = self.workspace.pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["entity_id"], sid)
        self.assertNotIn("correct", pending[0]["payload"])

    def test_remote_import_preserves_manual_counts_and_does_not_rebroadcast_mapping(
        self,
    ):
        self.workspace.bind_account(str(uuid.uuid4()), consent=True)
        sid = self.session()
        envelope = dict(
            id=str(uuid.uuid4()),
            device_id=str(uuid.uuid4()),
            kind="study.session",
            entity_id=sid,
            base_revision=0,
            revision=1,
            sequence=1,
            received_at="2026-10-12T12:00:00+00:00",
            payload=dict(
                plan_id="site",
                subject_id="web-subject",
                topic_id="web-topic",
                day="2026-10-12",
                category="Questões",
                elapsed=600,
                lesson_id=None,
                lesson_version=None,
            ),
        )
        attempt = dict(
            id=str(uuid.uuid4()),
            device_id=str(uuid.uuid4()),
            kind="arena.attempt",
            entity_id=str(uuid.uuid4()),
            base_revision=0,
            revision=1,
            sequence=2,
            received_at="2026-10-12T12:00:01+00:00",
            payload=dict(question_id="q", version="1", answer="a", session_id=sid),
            result=dict(status="correct"),
        )
        self.workspace.apply_pull([envelope, attempt])
        with self.workspace.db:
            self.workspace.db.execute("UPDATE outbox SET status='sent'")
        self.store._applying_sync = True
        for _ in range(2):
            self.service.import_session(
                envelope,
                dict(plan_id=self.plan, subject_id=self.subject, topic_id=self.topic),
            )
        self.store._applying_sync = False
        row = self.store.one("SELECT correct,wrong FROM sessions WHERE id=?", (sid,))
        self.assertEqual(row, dict(correct=5, wrong=2))
        with self.workspace.db:
            self.workspace.db.execute("UPDATE outbox SET status='sent'")
            self.workspace.db.execute(
                "INSERT INTO metadata VALUES('session_baseline','[]')"
            )
        capture_new_sessions(self.store)
        self.assertEqual(self.workspace.pending(), [])
        self.assertEqual(self.store.stats(self.plan)["count"], 1)
        self.assertEqual(self.store.rpg.profile(self.plan)["xp"], 10)

    def test_remote_replay_preserves_pending_edit_and_local_fields(self):
        self.workspace.bind_account(str(uuid.uuid4()), consent=True)
        sid = self.session(target=1200, notes="Observação preservada")
        event = self.workspace.pending()[0]
        event["payload"]["elapsed"] = 60
        mapping = dict(plan_id=self.plan, subject_id=self.subject, topic_id=self.topic)
        self.service.import_session(event, mapping)
        row = self.store.one("SELECT * FROM sessions WHERE id=?", (sid,))
        self.assertEqual(row["elapsed"], 600)
        with self.workspace.db:
            self.workspace.db.execute("UPDATE outbox SET status='sent'")
        self.store._applying_sync = True
        self.service.import_session(event, mapping)
        self.store._applying_sync = False
        row = self.store.one("SELECT * FROM sessions WHERE id=?", (sid,))
        self.assertEqual(row["elapsed"], 60)
        self.assertEqual(row["target"], 1200)
        self.assertEqual(row["notes"], "Observação preservada")

    def remote_session(self, sid, **changes):
        row = self.store.one("SELECT * FROM sessions WHERE id=?", (sid,))
        payload = {
            key: row[key]
            for key in (
                "plan_id",
                "subject_id",
                "topic_id",
                "day",
                "category",
                "elapsed",
            )
        }
        payload.update(lesson_id=None, lesson_version=None)
        payload.update(changes)
        return dict(
            id=str(uuid.uuid4()),
            device_id=str(uuid.uuid4()),
            kind="study.session",
            entity_id=sid,
            base_revision=0,
            revision=1,
            sequence=1,
            received_at="2026-10-12T12:00:00+00:00",
            payload=payload,
        )

    def test_acknowledged_newer_edit_survives_older_replay(self):
        sid = self.session()
        remote = self.remote_session(sid, elapsed=120)
        self.workspace.apply_pull([remote])
        self.workspace.bind_account(str(uuid.uuid4()), consent=True)
        self.session(sid, elapsed=900)
        with self.workspace.db:
            self.workspace.db.execute("UPDATE outbox SET status='sent'")
        self.service.import_session(
            remote,
            dict(plan_id=self.plan, subject_id=self.subject, topic_id=self.topic),
        )
        self.assertEqual(
            self.store.one("SELECT elapsed FROM sessions WHERE id=?", (sid,))[
                "elapsed"
            ],
            900,
        )

    def test_conflicted_edit_survives_replay(self):
        self.workspace.bind_account(str(uuid.uuid4()), consent=True)
        sid = self.session(notes="Minha alteração", target=1200)
        remote = self.remote_session(sid, elapsed=120)
        with self.workspace.db:
            self.workspace.db.execute("UPDATE outbox SET status='conflict'")
        self.service.import_session(
            remote,
            dict(plan_id=self.plan, subject_id=self.subject, topic_id=self.topic),
        )
        row = self.store.one("SELECT * FROM sessions WHERE id=?", (sid,))
        self.assertEqual(
            (row["elapsed"], row["notes"], row["target"]),
            (600, "Minha alteração", 1200),
        )

    def test_review_and_local_lesson_links_survive_replay(self):
        origin = self.session(category="Teoria")
        rid = self.store.save(
            "reviews",
            dict(topic_id=self.topic, origin_id=origin, due="2026-10-13", interval=1),
        )
        sid = self.session(
            category="Revisão", review_id=rid, notes="Lembrança", target=1200
        )
        self.store.link_lesson(
            sid, dict(lesson_id="pessoal.document", lesson_version="1")
        )
        self.store.db.commit()
        before = self.store.one("SELECT * FROM reviews WHERE id=?", (rid,))
        remote = self.remote_session(sid, elapsed=300)
        mapping = dict(plan_id=self.plan, subject_id=self.subject, topic_id=self.topic)
        self.service.import_session(remote, mapping)
        self.service.import_session(remote, mapping)
        after = self.store.one("SELECT * FROM reviews WHERE id=?", (rid,))
        self.assertEqual(before, after)
        row = self.store.one("SELECT * FROM sessions WHERE id=?", (sid,))
        self.assertEqual(
            (row["elapsed"], row["review_id"], row["notes"], row["target"]),
            (300, rid, "Lembrança", 1200),
        )
        link = self.store.one(
            "SELECT * FROM training_session_links WHERE session_id=?", (sid,)
        )
        self.assertEqual(link["lesson_id"], "pessoal.document")

    def test_mock_breakdown_ids_and_scores_survive_replay(self):
        sid = self.session(
            category="Simulado", mock_name="Meu simulado", score_wrong=-1
        )
        values = self.store.one("SELECT * FROM sessions WHERE id=?", (sid,))
        self.store.save_session(
            values,
            results=[
                dict(subject_id=self.subject, correct=4, wrong=2, blank=0, weight=2)
            ],
        )
        before = self.store.rows(
            "SELECT * FROM mock_results WHERE session_id=?", (sid,)
        )
        remote = self.remote_session(sid, elapsed=300)
        mapping = dict(plan_id=self.plan, subject_id=self.subject, topic_id=self.topic)
        self.service.import_session(remote, mapping)
        self.service.import_session(remote, mapping)
        self.assertEqual(
            before,
            self.store.rows("SELECT * FROM mock_results WHERE session_id=?", (sid,)),
        )
        row = self.store.one("SELECT * FROM sessions WHERE id=?", (sid,))
        self.assertEqual(
            (row["elapsed"], row["mock_name"], row["score_wrong"]),
            (300, "Meu simulado", -1),
        )

    def test_manual_count_edit_then_remote_replay_and_new_attempt(self):
        sid = self.session()
        remote = self.remote_session(sid)
        attempt = dict(
            id=str(uuid.uuid4()),
            device_id=str(uuid.uuid4()),
            kind="arena.attempt",
            entity_id=str(uuid.uuid4()),
            base_revision=0,
            revision=1,
            sequence=2,
            received_at="2026-10-12T12:00:01+00:00",
            payload=dict(question_id="q", version="1", answer="a", session_id=sid),
            result=dict(status="correct"),
        )
        self.workspace.apply_pull([remote, attempt])
        mapping = dict(plan_id=self.plan, subject_id=self.subject, topic_id=self.topic)
        self.service.import_session(remote, mapping)
        self.assertEqual(
            self.store.one("SELECT correct FROM sessions WHERE id=?", (sid,))[
                "correct"
            ],
            5,
        )
        self.workspace.bind_account(str(uuid.uuid4()), consent=True)
        self.session(
            sid, correct=8, wrong=4, blank=2, elapsed=900, notes="Contagem corrigida"
        )
        accepted = self.workspace.pending()[0]
        with self.workspace.db:
            self.workspace.db.execute("UPDATE outbox SET status='sent'")
        accepted.update(revision=2, sequence=3, received_at="2026-10-12T12:00:02+00:00")
        self.workspace.apply_pull([accepted])
        for _ in range(2):
            self.service.import_session(accepted, mapping)
        row = self.store.one("SELECT * FROM sessions WHERE id=?", (sid,))
        self.assertEqual(
            (row["correct"], row["wrong"], row["blank"], row["notes"]),
            (8, 4, 2, "Contagem corrigida"),
        )
        next_attempt = dict(
            attempt, id=str(uuid.uuid4()), entity_id=str(uuid.uuid4()), sequence=4
        )
        self.workspace.apply_pull([next_attempt])
        self.service.import_session(accepted, mapping)
        self.assertEqual(
            self.store.one("SELECT correct FROM sessions WHERE id=?", (sid,))[
                "correct"
            ],
            9,
        )
        self.service.import_session(accepted, mapping)
        self.assertEqual(
            self.store.one("SELECT correct FROM sessions WHERE id=?", (sid,))[
                "correct"
            ],
            9,
        )

    def test_old_count_baseline_migrates_without_double_count(self):
        sid = self.session(correct=5)
        remote = self.remote_session(sid)
        attempt = dict(
            id=str(uuid.uuid4()),
            device_id=str(uuid.uuid4()),
            kind="arena.attempt",
            entity_id=str(uuid.uuid4()),
            base_revision=0,
            revision=1,
            sequence=2,
            received_at="2026-10-12T12:00:01+00:00",
            payload=dict(question_id="q", version="1", answer="a", session_id=sid),
            result=dict(status="correct"),
        )
        self.workspace.apply_pull([remote, attempt])
        with self.workspace.db:
            self.workspace.db.execute(
                "CREATE TABLE session_import_baselines(id TEXT PRIMARY KEY,correct INTEGER NOT NULL,wrong INTEGER NOT NULL,blank INTEGER NOT NULL)"
            )
            self.workspace.db.execute(
                "INSERT INTO session_import_baselines VALUES(?,4,2,0)", (sid,)
            )
        mapping = dict(plan_id=self.plan, subject_id=self.subject, topic_id=self.topic)
        self.service.import_session(remote, mapping)
        self.service.import_session(remote, mapping)
        self.assertEqual(
            self.store.one("SELECT correct FROM sessions WHERE id=?", (sid,))[
                "correct"
            ],
            5,
        )
        self.assertEqual(
            self.workspace.db.execute(
                "SELECT last_correct FROM session_import_baselines WHERE id=?", (sid,)
            ).fetchone()[0],
            1,
        )

    def restart(self):
        path = self.store.path
        self.workspace.close()
        self.store.db.close()
        self.store = Store(path)
        self.workspace = workspace_for(self.store)
        self.service = service_for(self.store)

    def counted_remote_session(self):
        sid = self.session()
        remote = self.remote_session(sid)
        attempt = dict(
            id=str(uuid.uuid4()),
            device_id=str(uuid.uuid4()),
            kind="arena.attempt",
            entity_id=str(uuid.uuid4()),
            base_revision=0,
            revision=1,
            sequence=2,
            received_at="2026-10-12T12:00:01+00:00",
            payload=dict(question_id="q", version="1", answer="a", session_id=sid),
            result=dict(status="correct"),
        )
        self.workspace.apply_pull([remote, attempt])
        return (
            sid,
            remote,
            dict(plan_id=self.plan, subject_id=self.subject, topic_id=self.topic),
        )

    def test_crash_after_canonical_save_recovers_without_double_count(self):
        sid, remote, mapping = self.counted_remote_session()
        with patch.object(
            self.service, "_finish_import_counts", side_effect=RuntimeError("crash")
        ):
            with self.assertRaises(RuntimeError):
                self.service.import_session(remote, mapping)
        self.assertEqual(
            self.store.one("SELECT correct FROM sessions WHERE id=?", (sid,))[
                "correct"
            ],
            5,
        )
        self.assertIsNotNone(
            self.workspace.db.execute(
                "SELECT id FROM session_import_journal WHERE id=?", (sid,)
            ).fetchone()
        )
        self.restart()
        for _ in range(3):
            self.service.import_session(remote, mapping)
        self.assertEqual(
            self.store.one("SELECT correct FROM sessions WHERE id=?", (sid,))[
                "correct"
            ],
            5,
        )
        self.assertIsNone(
            self.workspace.db.execute(
                "SELECT id FROM session_import_journal WHERE id=?", (sid,)
            ).fetchone()
        )
        baseline = self.workspace.db.execute(
            "SELECT correct,last_correct FROM session_import_baselines WHERE id=?",
            (sid,),
        ).fetchone()
        self.assertEqual(tuple(baseline), (4, 1))

    def test_finalize_rollback_keeps_journal_and_baseline_atomic(self):
        sid, remote, mapping = self.counted_remote_session()
        self.service._ensure_import_schema()
        self.workspace.db.execute(
            "CREATE TRIGGER fail_finalize BEFORE DELETE ON session_import_journal BEGIN SELECT RAISE(ABORT,'test failure'); END"
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.service.import_session(remote, mapping)
        baseline = self.workspace.db.execute(
            "SELECT correct,last_correct FROM session_import_baselines WHERE id=?",
            (sid,),
        ).fetchone()
        self.assertEqual(tuple(baseline), (4, 0))
        self.assertIsNotNone(
            self.workspace.db.execute(
                "SELECT id FROM session_import_journal WHERE id=?", (sid,)
            ).fetchone()
        )
        self.workspace.db.execute("DROP TRIGGER fail_finalize")
        self.workspace.db.commit()
        self.restart()
        self.service.import_session(remote, mapping)
        self.assertEqual(
            self.store.one("SELECT correct FROM sessions WHERE id=?", (sid,))[
                "correct"
            ],
            5,
        )
        self.assertIsNone(
            self.workspace.db.execute(
                "SELECT id FROM session_import_journal WHERE id=?", (sid,)
            ).fetchone()
        )

    def test_crash_before_canonical_save_retries_after_restart(self):
        sid, remote, mapping = self.counted_remote_session()
        with patch.object(
            self.store, "save_session", side_effect=RuntimeError("crash")
        ):
            with self.assertRaises(RuntimeError):
                self.service.import_session(remote, mapping)
        self.assertEqual(
            self.store.one("SELECT correct FROM sessions WHERE id=?", (sid,))[
                "correct"
            ],
            4,
        )
        self.restart()
        self.service.import_session(remote, mapping)
        self.service.import_session(remote, mapping)
        self.assertEqual(
            self.store.one("SELECT correct FROM sessions WHERE id=?", (sid,))[
                "correct"
            ],
            5,
        )
        self.assertIsNone(
            self.workspace.db.execute(
                "SELECT id FROM session_import_journal WHERE id=?", (sid,)
            ).fetchone()
        )

    def test_recovery_preserves_intervening_edit_and_requires_explicit_choice(self):
        sid, remote, mapping = self.counted_remote_session()
        with patch.object(
            self.service, "_finish_import_counts", side_effect=RuntimeError("crash")
        ):
            with self.assertRaises(RuntimeError):
                self.service.import_session(remote, mapping)
        self.session(sid, correct=8, notes="Minha correção")
        self.restart()
        with self.assertRaises(ValueError):
            self.service.import_session(remote, mapping)
        row = self.store.one("SELECT * FROM sessions WHERE id=?", (sid,))
        self.assertEqual((row["correct"], row["notes"]), (8, "Minha correção"))
        self.assertIsNotNone(
            self.workspace.db.execute(
                "SELECT id FROM session_import_journal WHERE id=?", (sid,)
            ).fetchone()
        )
        with self.assertRaises(ValueError):
            self.service.reconcile_import_counts(sid)
        self.service.reconcile_import_counts(sid, consent=True)
        self.service.import_session(remote, mapping)
        self.service.import_session(remote, mapping)
        self.assertEqual(
            self.store.one("SELECT correct FROM sessions WHERE id=?", (sid,))[
                "correct"
            ],
            8,
        )

    def test_recovery_equal_counts_still_applies_session_fields(self):
        sid = self.session()
        remote = self.remote_session(sid, elapsed=300)
        mapping = dict(plan_id=self.plan, subject_id=self.subject, topic_id=self.topic)
        with patch.object(
            self.store, "save_session", side_effect=RuntimeError("crash")
        ):
            with self.assertRaises(RuntimeError):
                self.service.import_session(remote, mapping)
        self.restart()
        self.service.import_session(remote, mapping)
        row = self.store.one("SELECT * FROM sessions WHERE id=?", (sid,))
        self.assertEqual((row["correct"], row["elapsed"]), (4, 300))

    def test_importer_does_not_echo_remote_session(self):
        sid = self.session()
        remote = self.remote_session(sid, elapsed=300)
        self.workspace.bind_account(str(uuid.uuid4()), consent=True)
        self.service.import_session(
            remote,
            dict(plan_id=self.plan, subject_id=self.subject, topic_id=self.topic),
        )
        self.assertEqual(self.workspace.pending(), [])
        self.assertFalse(self.store._applying_sync)

    def test_ack_before_pull_survives_restart(self):
        self.workspace.bind_account(str(uuid.uuid4()), consent=True)
        event = self.service.read_page("lesson", "1", 1, 2, True)
        with self.workspace.db:
            self.workspace.db.execute(
                "UPDATE outbox SET status='sent' WHERE id=?", (event["id"],)
            )
        self.assertEqual(self.service.reading("lesson", "1", 2)["read_pages"], [1])
        next_event = self.service.read_page("lesson", "1", 1, 2, False)
        self.assertEqual(next_event["base_revision"], 1)
