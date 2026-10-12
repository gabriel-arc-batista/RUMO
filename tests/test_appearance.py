import itertools
import json
import unittest
from pathlib import Path

import appearance as A
from security import validate_preferences

ASSETS = Path(__file__).resolve().parents[1] / "assets/character/look"


class AppearanceTests(unittest.TestCase):
    def test_default_and_unknown_values_normalize(self):
        self.assertEqual(A.normalize(None), A.DEFAULT)
        look = A.normalize({"sex": "feminino", "skin": "inexistente", "x": 1})
        self.assertEqual(look["sex"], "feminino")
        self.assertEqual(look["skin"], A.DEFAULT["skin"])
        self.assertNotIn("x", look)

    def test_validation_rejects_unknown_ids_and_fields(self):
        self.assertTrue(A.validate_look(A.DEFAULT))
        self.assertTrue(A.validate_look({"hair": "careca"}))
        self.assertFalse(A.validate_look({"hair": "moicano"}))
        self.assertFalse(A.validate_look({"script": "x"}))
        self.assertFalse(A.validate_look(["masculino"]))

    def test_backup_preferences_validate_the_look(self):
        good = [{"key": A.PREFERENCE, "value": json.dumps(A.DEFAULT)}]
        validate_preferences(good)
        bad = [{"key": A.PREFERENCE, "value": json.dumps({"eyes": "../x"})}]
        with self.assertRaises(ValueError):
            validate_preferences(bad)

    def test_shared_layers_and_bald_has_no_hair_layer(self):
        back, front = A.layers(dict(A.DEFAULT, sex="feminino", hair="careca"))
        self.assertEqual(back, [])
        self.assertTrue(any(n.startswith("head-") for n in front))
        self.assertFalse(any(n.startswith("hair-") for n in front))
        self.assertEqual(A.normalize({"sex": "feminino"})["face"], "rosto-4")

    def test_order_and_original_provenance(self):
        import hashlib
        from PIL import Image

        catalog = json.loads((ASSETS / "catalog.json").read_text())
        records = {r["id"]: r for r in catalog["pieces"]}
        for record in records.values():
            source = ASSETS.parent / "sources/erebus/example_assets" / record["source"]
            self.assertEqual(
                hashlib.sha256(source.read_bytes()).hexdigest(), record["source_sha256"]
            )
            with Image.open(ASSETS / record["path"]) as image:
                self.assertEqual(image.size, (264, 264))
                self.assertEqual(image.mode, "RGBA")
        for field, _, options in A.FIELDS:
            for key in A.ids(options):
                look = dict(A.DEFAULT, **{field: key})
                names = sum(A.layers(look), [])
                order = [records[n]["layer"] for n in names]
                self.assertEqual(order, sorted(order))
                self.assertTrue(
                    (ASSETS / "thumbnails" / f"{field}-{key}.png").is_file()
                )

    def test_missing_asset_falls_back_without_changing_other_layers(self):
        import tempfile
        from types import SimpleNamespace
        from ui import look_layers

        with tempfile.TemporaryDirectory() as folder:
            assets = Path(folder)
            target = assets / "character/look/bust"
            target.mkdir(parents=True)
            look = dict(A.DEFAULT, face="rosto-6", hair="longo")
            names = sum(A.layers(look), [])
            for name in names:
                if not name.startswith("head-"):
                    (target / f"{name}.png").touch()
            fallback = A.layers(A.DEFAULT)[1][0]
            (target / f"{fallback}.png").touch()
            back, front = look_layers(SimpleNamespace(assets=assets), look, "bust")
            self.assertEqual(Path(front[0]).stem, fallback)
            self.assertIn("character/look/bust/hair-longo-castanho-escuro.png", front)
            self.assertEqual(len(back + front), len(names))

    def test_profile_save_backup_restore_and_no_rewards(self):
        import tempfile
        from core import Store
        from character_profile import save_character

        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "source.sqlite3")
            plan = store.save("plans", {"name": "Temporário"})
            store.rpg.catalog(plan)  # materialize the existing initial equipment
            before = store.stats(plan)
            inventory = store.rows("SELECT * FROM rpg_inventory")
            self.assertTrue(inventory)
            look = dict(
                A.DEFAULT, sex="feminino", face="rosto-4", hair="longo", beard="bigode"
            )
            save_character(store, plan, look, " Aurora ")
            self.assertEqual(store.rpg.profile(plan)["name"], "Aurora")
            self.assertEqual(store.pref(A.PREFERENCE), look)
            with self.assertRaises(ValueError):
                save_character(store, plan, dict(A.DEFAULT), " ")
            self.assertEqual(store.pref(A.PREFERENCE), look)
            self.assertEqual(store.stats(plan), before)
            self.assertEqual(store.rows("SELECT * FROM rpg_inventory"), inventory)
            self.assertEqual(store.rpg.profile(plan)["xp"], 0)
            backup = Path(folder) / "backup.json"
            store.export(backup)
            store.db.close()
            reopened = Store(Path(folder) / "source.sqlite3")
            self.assertEqual(reopened.pref(A.PREFERENCE), look)
            reopened.db.close()
            restored = Store(Path(folder) / "restored.sqlite3")
            restored.restore(backup)
            self.assertEqual(restored.pref(A.PREFERENCE), look)
            self.assertEqual(restored.rpg.profile(plan)["name"], "Aurora")
            restored.db.close()

    def test_every_option_has_rendered_layers(self):
        names = set()
        fields = {field: A.ids(options) for field, _, options in A.FIELDS}
        for field, values in fields.items():
            for value in values:
                for other in (None, "feminino"):
                    look = dict(A.DEFAULT, **{field: value})
                    if other and field != "sex":
                        look["sex"] = other
                    back, front = A.layers(look)
                    names.update(back + front)
        for style, color in itertools.product(fields["hair"], fields["hair_color"]):
            back, front = A.layers(dict(A.DEFAULT, hair=style, hair_color=color))
            names.update(back + front)
        for view in ("full", "bust"):
            missing = [n for n in names if not (ASSETS / view / f"{n}.png").exists()]
            self.assertEqual(missing, [], view)
