import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Store
from syllabus import expand_bacen

ASSETS = Path(__file__).resolve().parents[1] / "assets"


class SyllabusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "test.sqlite3")
        source = json.loads((ASSETS / "bacen2024.json").read_text(encoding="utf-8"))
        self.area = "Tecnologia da Informação"
        self.plan = self.store.save("plans", {"name": "BACEN 2024 — " + self.area})
        self.store.import_topics(self.plan, source["areas"][self.area])
        self.guide = json.loads(
            (ASSETS / "bacen2024-detalhado.json").read_text(encoding="utf-8")
        )["areas"][self.area]

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def test_every_official_leaf_has_individual_subtopics(self):
        self.assertEqual(len(self.guide), 117)
        self.assertEqual(expand_bacen(self.store, self.plan, self.guide), 565)
        self.assertEqual(self.store.progress(self.plan)["total"], 565)
        java = self.store.one("SELECT id FROM topics WHERE name='12 Python e Java'")
        names = [
            r["name"]
            for r in self.store.rows(
                "SELECT name FROM topics WHERE parent_id=?", (java["id"],)
            )
        ]
        self.assertIn("Java: interfaces e classes abstratas", names)
        self.assertIn("Java: estruturas sequenciais e entrada/saída", names)
        self.assertTrue(
            any(
                "Normalização:" in r["name"]
                for r in self.store.rows("SELECT name FROM topics")
            )
        )

    def test_completed_state_history_and_repeat_open_are_preserved(self):
        parent = self.store.one("SELECT * FROM topics WHERE name='12 Python e Java'")
        self.store.save("topics", {"id": parent["id"], "done": 1})
        session = self.store.save_session(
            dict(
                plan_id=self.plan,
                subject_id=parent["subject_id"],
                topic_id=parent["id"],
                day="2026-10-10",
                category="Teoria",
                target=1800,
                elapsed=1700,
                correct=8,
                wrong=2,
                blank=0,
            )
        )
        original = self.store.one("SELECT * FROM sessions WHERE id=?", (session,))
        expand_bacen(self.store, self.plan, self.guide)
        children = self.store.rows(
            "SELECT * FROM topics WHERE parent_id=?", (parent["id"],)
        )
        self.assertEqual(len(children), 26)
        self.assertTrue(all(r["done"] for r in children))
        self.assertEqual(
            self.store.one("SELECT * FROM sessions WHERE id=?", (session,)), original
        )
        self.store.save("topics", {"id": children[0]["id"], "done": 0})
        self.store.save("topics", {"id": children[1]["id"], "archived": 1})
        self.assertEqual(expand_bacen(self.store, self.plan, self.guide), 0)
        self.assertEqual(
            self.store.one("SELECT done FROM topics WHERE id=?", (children[0]["id"],))[
                "done"
            ],
            0,
        )
        self.assertEqual(
            self.store.one(
                "SELECT archived FROM topics WHERE id=?", (children[1]["id"],)
            )["archived"],
            1,
        )
        self.assertEqual(self.store.stats(self.plan)["elapsed"], 1700)
        backup = list((Path(self.tmp.name) / "backups").glob("*.sqlite3"))
        self.assertTrue(backup)

    def test_archived_original_and_custom_edits_are_respected(self):
        parent = self.store.one("SELECT * FROM topics WHERE name='12 Python e Java'")
        self.store.save("topics", {"id": parent["id"], "archived": 1})
        self.assertEqual(expand_bacen(self.store, self.plan, self.guide), 539)
        self.assertFalse(
            self.store.rows("SELECT id FROM topics WHERE parent_id=?", (parent["id"],))
        )

    def test_economics_and_backup_roundtrip(self):
        source = json.loads((ASSETS / "bacen2024.json").read_text(encoding="utf-8"))
        area = "Economia e Finanças"
        plan = self.store.save("plans", {"name": "BACEN 2024 — " + area})
        self.store.import_topics(plan, source["areas"][area])
        guide = json.loads(
            (ASSETS / "bacen2024-detalhado.json").read_text(encoding="utf-8")
        )["areas"][area]
        self.assertEqual(expand_bacen(self.store, plan, guide), 525)
        self.assertEqual(self.store.progress(plan)["total"], 525)
        path = Path(self.tmp.name) / "backup.json"
        self.store.export(path)
        data = self.store.validate_backup(path)
        self.assertEqual(len(data["tables"]["topics"]), 812)


if __name__ == "__main__":
    unittest.main()
