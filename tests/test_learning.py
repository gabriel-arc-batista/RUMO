import tempfile
import unittest
from pathlib import Path
from core import Store
from learning import ordered, next_topic, create_starter_cycle


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "study.db")
        self.plan = self.store.put("plans", {"name": "BACEN"})
        self.subject = self.store.put(
            "subjects",
            {"plan_id": self.plan, "name": "Bancos De Dados", "color": "#D7B663"},
        )

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def test_foundations_before_sql_without_changing_records(self):
        sql = self.store.put("topics", {"subject_id": self.subject, "name": "3 SQL"})
        models = self.store.put(
            "topics", {"subject_id": self.subject, "name": "2 Modelos relacionais"}
        )
        self.assertEqual(next_topic(self.store, self.subject)["id"], models)
        self.store.save("topics", {"id": models, "done": True})
        self.assertEqual(next_topic(self.store, self.subject)["id"], sql)
        self.assertEqual(
            self.store.one("SELECT name FROM topics WHERE id=?", (sql,))["name"],
            "3 SQL",
        )

    def test_language_prerequisites(self):
        names = [
            "Java: interfaces",
            "Java: classes",
            "Java: condicionais",
            "Java: tipos",
        ]
        topics = [{"name": n, "subject_id": "s"} for n in names]
        self.assertEqual(
            [t["name"] for t in ordered(topics, {"s": "Engenharia De Software"})],
            list(reversed(names)),
        )

    def test_web_architecture_before_tools_and_design(self):
        names = ["12 Python e Java", "11 Git", "6 UX", "1 Arquitetura web", "5 Camadas"]
        topics = [{"name": n, "subject_id": "s"} for n in names]
        self.assertEqual(
            [t["name"] for t in ordered(topics, {"s": "Engenharia De Software"})],
            ["1 Arquitetura web", "5 Camadas", "12 Python e Java", "11 Git", "6 UX"],
        )

    def test_basics_before_consumer_theory(self):
        names = ["Microeconomia — 2.1 Curvas", "Microeconomia — 1.1 Preços"]
        topics = [{"name": n, "subject_id": "s"} for n in names]
        self.assertEqual(
            [t["name"] for t in ordered(topics, {"s": "Fundamentos"})],
            list(reversed(names)),
        )

    def test_cycle_is_idempotent_and_preserves_history(self):
        old = self.store.put("cycles", {"plan_id": self.plan, "name": "Anterior"})
        cycle = create_starter_cycle(self.store, self.plan)
        self.assertEqual(create_starter_cycle(self.store, self.plan), cycle)
        self.assertEqual(
            self.store.one("SELECT active FROM cycles WHERE id=?", (old,))["active"], 0
        )
        self.assertEqual(
            self.store.one("SELECT name FROM cycles WHERE id=?", (old,))["name"],
            "Anterior",
        )
        self.assertEqual(
            self.store.rows("SELECT target FROM blocks WHERE cycle_id=?", (cycle,)),
            [{"target": 1500}],
        )
        self.assertEqual(self.store.one("SELECT COUNT(*) n FROM sessions")["n"], 0)

    def test_invalid_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            create_starter_cycle(self.store, self.plan, 0)
