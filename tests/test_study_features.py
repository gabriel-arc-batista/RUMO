import json
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Store
from challenges import metrics
from inspiration import daily, corpus

ASSETS = Path(__file__).resolve().parents[1] / "assets"


class StudyFeaturesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "study.sqlite3"
        self.store = Store(self.path)
        self.plan = self.store.save("plans", {"name": "Meu plano"})
        self.subject = self.store.save(
            "subjects", {"plan_id": self.plan, "name": "Java", "color": "#D6B467"}
        )
        self.topic = self.store.save(
            "topics", {"subject_id": self.subject, "name": "Classes"}
        )

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def record(self, **values):
        return self.store.save_session(
            dict(
                plan_id=self.plan,
                subject_id=self.subject,
                topic_id=self.topic,
                day="2026-10-10",
                category="Teoria",
                target=1800,
                elapsed=900,
                correct=8,
                wrong=2,
                blank=3,
                **values,
            )
        )

    def test_schema_two_upgrade_preserves_existing_records(self):
        self.record()
        original = self.store.one("SELECT * FROM sessions")
        self.store.db.execute("ALTER TABLE topics DROP COLUMN notes")
        self.store.db.execute("PRAGMA user_version=2")
        self.store.db.commit()
        self.store.db.close()
        self.store = Store(self.path)
        self.assertEqual(self.store.db.execute("PRAGMA user_version").fetchone()[0], 6)
        self.assertEqual(self.store.one("SELECT * FROM sessions"), original)
        self.assertEqual(self.store.one("SELECT * FROM topics")["notes"], "")

    def test_notes_completion_and_backup_are_independent(self):
        text = "Dúvida: interfaces × classes.\nExemplo: café, ação e 🧠."
        self.store.save("topics", {"id": self.topic, "notes": text})
        self.store.save("topics", {"id": self.topic, "done": 1})
        backup = Path(self.tmp.name) / "backup.json"
        self.store.export(backup)
        self.store.save(
            "topics", {"id": self.topic, "notes": "Outra observação", "done": 0}
        )
        self.store.restore(backup)
        restored = self.store.one("SELECT * FROM topics WHERE id=?", (self.topic,))
        self.assertEqual(restored["notes"], text)
        self.assertEqual(restored["done"], 1)
        legacy = json.loads(backup.read_text(encoding="utf-8"))
        legacy["version"] = 2
        for row in legacy["tables"]["topics"]:
            row.pop("notes")
        backup.write_text(json.dumps(legacy), encoding="utf-8")
        self.assertEqual(
            self.store.validate_backup(backup)["tables"]["topics"][0]["notes"], ""
        )

    def test_weekly_challenges_isolate_plans_and_recalculate_edits(self):
        session = self.record()
        self.store.save("topics", {"id": self.topic, "notes": "Entendi o exemplo"})
        values = metrics(self.store, self.plan, date(2026, 10, 10))
        self.assertEqual(
            (
                values["sessions"],
                values["minutes"],
                values["questions"],
                values["days"],
                values["notes"],
            ),
            (1, 15, 10, 1, 1),
        )
        other = self.store.save("plans", {"name": "Outro plano"})
        self.assertEqual(metrics(self.store, other, date(2026, 10, 10))["questions"], 0)
        self.store.delete_session(session)
        self.assertEqual(
            metrics(self.store, self.plan, date(2026, 10, 10))["questions"], 0
        )
        self.assertEqual(metrics(self.store, self.plan, date(2026, 10, 19))["notes"], 1)

    def test_challenge_liquid_time_respects_midnight_segments(self):
        self.store.save_session(
            dict(
                plan_id=self.plan,
                subject_id=self.subject,
                topic_id=self.topic,
                day="2026-10-04",
                category="Teoria",
                target=1800,
                elapsed=1800,
                correct=0,
                wrong=0,
                blank=0,
                segments=json.dumps(
                    [
                        {"day": "2026-10-04", "seconds": 600},
                        {"day": "2026-10-05", "seconds": 1200},
                    ]
                ),
            )
        )
        values = metrics(self.store, self.plan, date(2026, 10, 10))
        self.assertEqual(values["minutes"], 20)
        self.assertEqual(values["days"], 1)

    def test_150_daily_quotes_are_distinct_sourced_and_stable(self):
        path = ASSETS / "quotes.json"
        quotes = corpus(path)
        self.assertEqual(len({q["text"] for q in quotes}), 150)
        self.assertTrue(
            all(
                q["source"].startswith("https://") and q["reference"] and q["kind"]
                for q in quotes
            )
        )
        begin = date(2026, 10, 10)
        self.assertEqual(
            len({daily(path, begin + timedelta(days=n))[0] for n in range(150)}), 150
        )
        self.assertEqual(daily(path, begin), daily(path, begin + timedelta(days=150)))


if __name__ == "__main__":
    unittest.main()
