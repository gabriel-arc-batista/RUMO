import json
import tempfile
import unittest
from pathlib import Path

from core import Store
from learning import next_topic
from pedagogy import graph, recommendations, save_graph, validate_graph


class PedagogyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "test.db"
        self.store = Store(self.path)
        self.plan = self.store.put("plans", {"name": "Teste"})
        self.subject = self.store.put(
            "subjects", {"plan_id": self.plan, "name": "Teste", "color": "#D7B663"}
        )
        self.a = self.store.put(
            "topics", {"subject_id": self.subject, "name": "Avançado"}
        )
        self.b = self.store.put(
            "topics", {"subject_id": self.subject, "name": "Fundamentos"}
        )

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def edge(self, a=None, b=None, kind="essential"):
        return dict(before=a or self.b, after=b or self.a, kind=kind)

    def test_prerequisite_recommendation_resume_and_no_access_block(self):
        save_graph(self.store, self.plan, [self.edge()])
        self.assertEqual(next_topic(self.store, self.subject)["id"], self.b)
        advanced = next(
            r
            for r in recommendations(self.store, self.subject)
            if r["topic"]["id"] == self.a
        )
        self.assertIn("livremente", advanced["reason"])
        # Direct completion remains possible in either order.
        self.store.save("topics", {"id": self.b, "done": 1})
        self.store.db.close()
        self.store = Store(self.path)
        self.assertEqual(next_topic(self.store, self.subject)["id"], self.a)
        self.store.save("topics", {"id": self.a, "done": 1})
        self.assertIsNone(next_topic(self.store, self.subject))

    def test_invalid_graph_is_atomic_and_parallel_is_not_prerequisite(self):
        save_graph(self.store, self.plan, [self.edge(kind="parallel")])
        self.assertEqual(next_topic(self.store, self.subject)["id"], self.a)
        for edges in (
            [self.edge(), self.edge(self.a, self.b)],
            [self.edge(), self.edge()],
            [self.edge("unknown")],
        ):
            with self.assertRaises(ValueError):
                save_graph(self.store, self.plan, edges)
        self.assertEqual(graph(self.store, self.plan)[0]["kind"], "parallel")

    def test_cross_subject_and_parent_progress(self):
        other = self.store.put(
            "subjects", {"plan_id": self.plan, "name": "Outra", "color": "#D7B663"}
        )
        parent = self.store.put("topics", {"subject_id": other, "name": "Base"})
        leaf = self.store.put(
            "topics", {"subject_id": other, "parent_id": parent, "name": "Parte"}
        )
        save_graph(self.store, self.plan, [self.edge(parent)])
        self.assertTrue(recommendations(self.store, self.subject)[1]["missing"])
        self.store.save("topics", {"id": leaf, "done": 1})
        self.assertFalse(recommendations(self.store, self.subject)[0]["missing"])

    def test_deep_cycle_validation_is_iterative(self):
        edges = [
            dict(before=str(i), after=str(i + 1), kind="essential") for i in range(2000)
        ]
        validate_graph(edges)
        with self.assertRaises(ValueError):
            validate_graph(edges + [dict(before="2000", after="0", kind="recommended")])

    def test_backup_roundtrip(self):
        save_graph(self.store, self.plan, [self.edge()])
        path = Path(self.tmp.name) / "backup.json"
        self.store.export(path)
        data = self.store.validate_backup(path)
        prefs = {
            r["key"]: json.loads(r["value"]) for r in data["tables"]["preferences"]
        }
        self.assertEqual(prefs["learning_graph_" + self.plan], [self.edge()])

    def test_official_plan_has_all_identified_items_without_invention(self):
        root = Path(__file__).resolve().parents[1]
        source = json.loads((root / "assets/bacen2024.json").read_text())
        self.store.import_topics(self.plan, source["areas"]["Tecnologia da Informação"])
        edges = graph(self.store, self.plan)
        self.assertGreater(len(edges), 30)
        outline = json.loads((root / "assets/bacen2024-detalhado.json").read_text())[
            "areas"
        ]["Tecnologia da Informação"]
        text = json.dumps(outline, ensure_ascii=False).casefold()
        for term in (
            "multiplicador monetário",
            "criação e destruição",
            "contas do sistema monetário",
            "equilíbrio do consumidor",
            "elasticidade da demanda",
            "grpc",
            "websockets",
            "ui design",
            "assíncrona",
            "graphql",
            "dlt",
            "dns",
            "dhcp",
            "radius",
            "autenticação",
            "certificados",
            "ldap",
            "nfs",
            "smb",
            "sdn",
        ):
            self.assertIn(term, text)
