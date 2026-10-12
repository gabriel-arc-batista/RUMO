import hashlib
import io
import json
import shutil
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
from datetime import date
from pathlib import Path

from core import SCHEMA, Store, uid
from rpg_schema import RPG_SCHEMA
from training import TrainingService, load_curriculum, subject_match
from training_catalog import CatalogError, validate_catalog
from training_content import (
    ContentError,
    ContentManager,
    RemoteProvider,
    normalize_source,
)
from training_schema import TRAINING_SCHEMA, TRAINING_TABLES

FIXTURE = Path(__file__).parent / "fixtures" / "campo-teste"
LESSON = "teste.campo:leitor:aula:01"


def published(catalog):
    """A copy of the test catalog shaped as reviewed, published content."""
    data = json.loads(json.dumps(catalog))
    data["kind"] = "publicado"
    lesson = data["lessons"][0]
    lesson["publication_status"] = "publicada"
    lesson["review"] = dict(
        status="aprovada", reviewer="Pessoa revisora", reviewed_at="2026-10-11"
    )
    return data


class FakeResponse(io.BytesIO):
    def __init__(self, data, etag=None):
        super().__init__(data)
        self.headers = {"ETag": etag} if etag else {}


class FakeOpener:
    """Stands in for urllib: maps URLs to bytes or to an exception."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def open(self, request, timeout=None):
        self.calls.append(request.full_url)
        value = self.routes[request.full_url]
        if isinstance(value, Exception):
            raise value
        return FakeResponse(value)


class TrainingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.folder = self.root / "catalogo"
        shutil.copytree(FIXTURE, self.folder)
        self.store = Store(self.root / "estudos.sqlite3")
        self.plan = self.store.save("plans", {"name": "Plano"})
        self.subject = self.store.save(
            "subjects",
            {"plan_id": self.plan, "name": "Material de teste", "color": "#D6B467"},
        )
        self.topic = self.store.save(
            "topics", {"subject_id": self.subject, "name": "Validação do leitor"}
        )
        self.content = ContentManager(
            self.root / "conteudo", dict(mode="local", path=str(self.folder))
        )
        self.service = TrainingService(self.store, self.content)

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def lesson(self):
        return next(l for l in self.service.library() if l["id"] == LESSON)

    def use_catalog(self, name):
        shutil.copy(self.folder / name, self.folder / "catalog.json")
        return self.content.refresh()

    # Catalog --------------------------------------------------------------

    def test_package_counts_and_planning_are_not_content(self):
        curriculum = load_curriculum()
        self.assertEqual(len(curriculum["families"]), 60)
        self.assertEqual(sum(len(f["lessons"]) for f in curriculum["families"]), 267)
        self.assertEqual(sum(len(e["disciplines"]) for e in curriculum["exams"]), 80)
        planned = [l for l in self.service.library() if l["origin"] == "planejada"]
        self.assertEqual(len(planned), 267)
        self.assertTrue(
            all(not l["openable"] and l["resource"] is None for l in planned)
        )
        self.assertFalse(self.service.filtered(planned, "disponiveis"))
        self.assertTrue(
            all(
                d["review_status"] == "pendente"
                for e in curriculum["exams"]
                for d in e["disciplines"]
            )
        )

    def test_invalid_catalogs_are_rejected_with_reasons(self):
        base = json.loads((FIXTURE / "catalog.json").read_text(encoding="utf-8"))
        cases = []
        planned_with_url = json.loads(json.dumps(base))
        planned_with_url["lessons"][0]["publication_status"] = "planejada"
        cases.append(planned_with_url)
        unreviewed = published(base)
        unreviewed["lessons"][0]["review"] = dict(status="pendente")
        cases.append(unreviewed)
        test_in_public = json.loads(json.dumps(base))
        test_in_public["kind"] = "publicado"
        cases.append(test_in_public)
        bad_hash = json.loads(json.dumps(base))
        bad_hash["lessons"][0]["resource"]["sha256"] = "x" * 64
        cases.append(bad_hash)
        duplicate = json.loads(json.dumps(base))
        duplicate["lessons"].append(duplicate["lessons"][0])
        cases.append(duplicate)
        escape = json.loads(json.dumps(base))
        escape["lessons"][0]["resource"]["url"] = "../fora.pdf"
        cases.append(escape)
        for case in cases:
            with self.subTest(case=case["lessons"][0].get("publication_status")):
                with self.assertRaises(CatalogError):
                    validate_catalog(case, base_is_local=True)
        remote = published(base)
        remote["lessons"][0]["resource"]["url"] = "https://exemplo.org/a.pdf"
        with self.assertRaises(CatalogError):
            validate_catalog(remote, allowed_hosts=["github.com"])
        self.assertEqual(
            validate_catalog(remote, allowed_hosts=["exemplo.org"])["lessons"][0][
                "resource"
            ]["url"],
            "https://exemplo.org/a.pdf",
        )

    def test_malformed_refresh_keeps_last_valid_catalog(self):
        catalog, changed = self.content.refresh()
        self.assertTrue(changed)
        (self.folder / "catalog.json").write_text("{quebrado", encoding="utf-8")
        with self.assertRaises(ContentError):
            self.content.refresh()
        self.assertEqual(self.content.catalog()["catalog_version"], "1.0.0")
        self.assertIn("JSON", self.content.state()["error"])

    # Downloads ----------------------------------------------------------

    def test_download_checks_hash_size_and_is_atomic(self):
        self.content.refresh()
        lesson = self.lesson()
        self.assertEqual(lesson["availability"], "nao_baixada")
        good = (self.folder / "arquivos" / "leitor-teste-1.0.0.pdf").read_bytes()
        (self.folder / "arquivos" / "leitor-teste-1.0.0.pdf").write_bytes(
            good[:-1] + b"X"
        )
        with self.assertRaisesRegex(ContentError, "hash"):
            self.content.download(lesson)
        self.assertFalse(self.content.local_versions(LESSON))
        self.assertFalse(list((self.root / "conteudo" / "temp").iterdir()))
        (self.folder / "arquivos" / "leitor-teste-1.0.0.pdf").write_bytes(
            good + b"extra"
        )
        with self.assertRaisesRegex(ContentError, "maior"):
            self.content.download(lesson)
        (self.folder / "arquivos" / "leitor-teste-1.0.0.pdf").write_bytes(good)
        path = self.content.download(lesson)
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(), lesson["resource"]["sha256"]
        )
        self.assertEqual(self.lesson()["availability"], "disponivel")

    def test_cancelled_download_leaves_nothing(self):
        self.content.refresh()
        cancel = threading.Event()
        cancel.set()
        with self.assertRaisesRegex(ContentError, "cancelado"):
            self.content.download(self.lesson(), cancel=cancel)
        self.assertEqual(self.lesson()["availability"], "nao_baixada")

    def test_remote_provider_errors_and_redirect_policy(self):
        base = published(
            json.loads((FIXTURE / "catalog.json").read_text(encoding="utf-8"))
        )
        pdf = (FIXTURE / "arquivos" / "leitor-teste-1.0.0.pdf").read_bytes()
        url = "https://conteudo.exemplo.org/catalog.json"
        base["lessons"][0]["resource"]["url"] = "https://conteudo.exemplo.org/a.pdf"
        opener = FakeOpener(
            {
                url: json.dumps(base).encode(),
                "https://conteudo.exemplo.org/a.pdf": pdf,
            }
        )
        content = ContentManager(
            self.root / "remoto", dict(mode="remote", url=url), opener=opener
        )
        self.assertEqual(content.source["allowed_hosts"], ["conteudo.exemplo.org"])
        catalog, _ = content.refresh()
        lesson = dict(catalog["lessons"][0])
        self.assertTrue(content.download(lesson).is_file())
        opener.routes[url] = urllib.error.URLError("offline")
        with self.assertRaisesRegex(ContentError, "conexão"):
            content.refresh()
        self.assertIsNotNone(content.catalog(), "último catálogo válido continua ativo")
        provider = RemoteProvider(url, {"conteudo.exemplo.org"}, opener)
        with self.assertRaisesRegex(ContentError, "não aprovado"):
            provider.open("https://outro.exemplo.org/a.pdf")
        with self.assertRaises(ValueError):
            from training_content import validate_source

            validate_source(
                normalize_source(dict(mode="remote", url="http://inseguro.org/c.json"))
            )

    # Reading state ------------------------------------------------------------

    def test_update_and_removal_preserve_notes_and_progress(self):
        self.use_catalog("catalog-1.0.0.json")
        self.content.download(self.lesson())
        self.service.save_position(LESSON, "1.0.0", 3, 4)
        self.service.save_note(LESSON, "1.0.0", "Rever a seção 2", page=2)
        self.service.toggle_bookmark(LESSON, "1.0.0", 4)
        self.use_catalog("catalog-2.0.0.json")
        lesson = self.lesson()
        self.assertEqual(lesson["availability"], "atualizacao_disponivel")
        path, version = self.service.file_for(lesson)
        self.assertEqual(version, "1.0.0", "a edição antiga continua abrindo")
        self.content.download(lesson)
        lesson = self.lesson()
        self.assertEqual(self.service.file_for(lesson)[1], "2.0.0")
        self.assertFalse(lesson["completed"], "nova edição não vem marcada como lida")
        self.assertEqual(
            lesson["position"]["page"], 3, "posição da versão anterior permanece"
        )
        notes = self.service.notes(LESSON)
        self.assertEqual((notes[0]["version"], notes[0]["page"]), ("1.0.0", 2))
        self.content.remove(LESSON)
        self.assertEqual(self.lesson()["availability"], "nao_baixada")
        self.assertEqual(len(self.service.notes(LESSON)), 1)
        self.assertEqual(len(self.service.bookmarks(LESSON, "1.0.0")), 1)

    def test_completion_and_favorites_are_idempotent_and_reward_free(self):
        self.content.refresh()
        before = self.store.rpg.profile(self.plan)["xp"]
        for _ in range(5):
            self.service.opened(LESSON, "1.0.0")
            self.service.set_completed(LESSON, "1.0.0")
        self.service.toggle_favorite(LESSON)
        self.assertEqual(self.store.rpg.profile(self.plan)["xp"], before)
        self.assertEqual(self.store.stats(self.plan)["count"], 0)
        lesson = self.lesson()
        self.assertTrue(lesson["legacy_completed"] and lesson["favorite"])
        self.assertFalse(lesson["completed"])
        pages = lesson["resource"]["page_count"]
        for page in range(1, pages + 1):
            self.service.mark_page(LESSON, "1.0.0", page, pages, True)
        self.assertTrue(self.lesson()["completed"])
        self.service.mark_page(LESSON, "1.0.0", 1, pages, False)
        self.assertFalse(self.lesson()["completed"])
        self.assertEqual(self.store.rpg.profile(self.plan)["xp"], before)

    def test_study_session_links_once_and_counts_once(self):
        self.content.refresh()
        self.assertEqual(
            subject_match(self.store, self.plan, "material de TESTE"), self.subject
        )
        values = dict(
            id=uid(),
            plan_id=self.plan,
            subject_id=self.subject,
            topic_id=self.topic,
            day=date.today().isoformat(),
            start_time="19:00",
            category="Teoria",
            target=1800,
            elapsed=1500,
            correct=0,
            wrong=0,
            blank=0,
            material="[TESTE] Validação do leitor (versão 1.0.0)",
        )
        context = dict(lesson_id=LESSON, lesson_version="1.0.0", recall=None)
        for _ in range(2):  # the same closing event delivered twice
            self.store.save_session(
                dict(values), [], False, [], True, None, True, dict(context)
            )
        self.assertEqual(self.store.stats(self.plan)["count"], 1)
        self.assertEqual(self.store.stats(self.plan)["elapsed"], 1500)
        self.assertEqual(
            self.store.stats(self.plan)["total"], 0, "leitura não gera questões"
        )
        self.assertEqual(self.service.studied_seconds(LESSON), (1500, 1))
        self.assertEqual(self.store.rpg.profile(self.plan)["xp"], 25)
        with self.assertRaises(ValueError):
            self.store.save_session(
                dict(values, id=uid()),
                [],
                False,
                [],
                True,
                None,
                True,
                dict(lesson_id="../x", lesson_version="1"),
            )

    # Persistence --------------------------------------------------------------

    def test_backup_v6_round_trip_and_v5_restore(self):
        self.service.save_note(LESSON, "1.0.0", "Nota preservada")
        self.service.save_position(LESSON, "1.0.0", 2, 4)
        path = self.root / "b.json"
        self.store.export(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 6)
        with self.store.db:
            self.store.db.execute("DELETE FROM training_notes")
        self.store.restore(path)
        self.assertEqual(self.service.notes(LESSON)[0]["text"], "Nota preservada")
        for name in TRAINING_TABLES:
            data["tables"].pop(name)
        data["version"] = 5
        legacy = self.root / "v5.json"
        legacy.write_text(json.dumps(data), encoding="utf-8")
        self.store.restore(legacy)
        self.assertEqual(self.service.notes(LESSON), [])
        data["version"] = 6
        data["tables"] = json.loads(path.read_text(encoding="utf-8"))["tables"]
        data["tables"]["training_notes"][0]["text"] = ""
        broken = self.root / "broken.json"
        broken.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.validate_backup(broken)

    def test_v5_database_upgrades_without_losing_data(self):
        old = self.root / "v5.sqlite3"
        connection = sqlite3.connect(old)
        connection.executescript(SCHEMA.replace(TRAINING_SCHEMA, ""))
        connection.execute("INSERT INTO plans(id,name) VALUES('p','Antigo')")
        connection.commit()
        self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 5)
        connection.close()
        upgraded = Store(old)
        try:
            self.assertEqual(
                upgraded.db.execute("PRAGMA user_version").fetchone()[0], 6
            )
            self.assertEqual(upgraded.one("SELECT name FROM plans")["name"], "Antigo")
            upgraded.db.execute("SELECT * FROM training_notes").fetchall()
        finally:
            upgraded.db.close()
        self.assertTrue(
            list(self.root.glob("pre-campo-*.sqlite3")), "cópia antes da migração"
        )
        self.assertTrue(RPG_SCHEMA in SCHEMA)

    def test_personal_import_is_distinct_and_survives_removal_of_notes(self):
        source = self.root / "meu.pdf"
        source.write_bytes(
            (FIXTURE / "arquivos" / "leitor-teste-1.0.0.pdf").read_bytes()
        )
        lesson_id = self.service.import_personal(
            source, "Minha apostila", "Bancos de dados"
        )
        lesson = next(l for l in self.service.library() if l["id"] == lesson_id)
        self.assertEqual(
            (lesson["origin"], lesson["availability"]), ("pessoal", "disponivel")
        )
        self.assertFalse(lesson["coverage_links"])
        self.service.save_note(lesson_id, "1", "Anotação própria")
        self.service.remove_personal(lesson_id)
        self.assertFalse(any(l["id"] == lesson_id for l in self.service.library()))
        self.assertEqual(len(self.service.notes(lesson_id)), 1)
        not_pdf = self.root / "x.pdf"
        not_pdf.write_bytes(b"MZ executable")
        with self.assertRaises(ContentError):
            self.service.import_personal(not_pdf, "x")


if __name__ == "__main__":
    unittest.main()
