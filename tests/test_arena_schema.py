import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from arena_schema import ARENA_SCHEMA, ARENA_TABLES
from core import SCHEMA, Store


class ArenaSchemaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / "estudos.sqlite3")
        self.plan = self.store.save("plans", {"name": "Plano"})
        self.subject = self.store.save(
            "subjects", {"plan_id": self.plan, "name": "Dados", "color": "#D6B467"}
        )
        self.topic = self.store.save(
            "topics", {"subject_id": self.subject, "name": "SQL"}
        )
        now = "2026-11-08T10:00:00"
        with self.store.db:
            self.store.db.execute(
                "INSERT INTO arena_questions(id,subject_id,topic_id,kind,statement,answer,origin,fingerprint,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?)",
                ("q1", self.subject, self.topic, "certo-errado", "SQL é declarativa.")
                + ("certo", "pessoal", "f1", now, now),
            )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def round(self, correct=True):
        attempt = dict(
            question_id="q1",
            question_version="1",
            answer="certo",
            correct=correct,
            answered_at="2026-11-08T10:01:00",
        )
        values = dict(
            plan_id=self.plan,
            subject_id=self.subject,
            topic_id=self.topic,
            day="2026-11-08",
            category="Questões",
            elapsed=60,
            correct=int(correct),
            wrong=int(not correct),
        )
        return self.store.save_session(values, context={"arena_attempts": [attempt]})

    def test_attempts_join_the_session_once_and_cascade(self):
        sid = self.round()
        session = self.store.one("SELECT * FROM sessions WHERE id=?", (sid,))
        self.store.save_session(
            session,
            context={
                "arena_attempts": [
                    dict(
                        question_id="q1",
                        question_version="1",
                        answer="certo",
                        correct=True,
                        answered_at="x",
                    )
                ]
            },
        )
        self.assertEqual(
            self.store.one("SELECT COUNT(*) n FROM arena_attempts")["n"], 1
        )
        self.store.delete_session(sid)
        self.assertEqual(
            self.store.one("SELECT COUNT(*) n FROM arena_attempts")["n"], 0
        )

    def test_invalid_attempt_rolls_back_the_session(self):
        bad = dict(
            question_id="q1",
            question_version="1",
            answer="",
            correct=True,
            answered_at="x",
        )
        values = dict(
            plan_id=self.plan,
            subject_id=self.subject,
            topic_id=self.topic,
            day="2026-11-08",
            category="Questões",
            elapsed=60,
        )
        with self.assertRaises(ValueError):
            self.store.save_session(values, context={"arena_attempts": [bad]})
        self.assertEqual(self.store.one("SELECT COUNT(*) n FROM sessions")["n"], 0)

    def test_backup_round_trip_and_v6_restore(self):
        self.round()
        path = self.root / "b.json"
        self.store.export(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 7)
        self.store.restore(path)
        self.assertEqual(
            self.store.one("SELECT COUNT(*) n FROM arena_attempts")["n"], 1
        )
        for name in ARENA_TABLES:
            data["tables"].pop(name)
        data["version"] = 6
        legacy = self.root / "v6.json"
        legacy.write_text(json.dumps(data), encoding="utf-8")
        self.store.restore(legacy)
        self.assertEqual(
            self.store.one("SELECT COUNT(*) n FROM arena_questions")["n"], 0
        )

    def test_v6_database_upgrades_with_copy(self):
        old = self.root / "v6.sqlite3"
        db = sqlite3.connect(old)
        try:
            db.executescript(SCHEMA.replace(ARENA_SCHEMA, ""))
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 6)
        finally:
            db.close()
        upgraded = Store(old)
        try:
            self.assertEqual(
                upgraded.db.execute("PRAGMA user_version").fetchone()[0], 7
            )
            upgraded.db.execute("SELECT * FROM arena_attempts").fetchall()
        finally:
            upgraded.close()
        self.assertTrue(list(self.root.glob("pre-arena-*.sqlite3")))


if __name__ == "__main__":
    unittest.main()
