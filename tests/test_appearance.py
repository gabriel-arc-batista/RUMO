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

    def test_feminine_adds_lashes_and_bald_has_no_hair_layer(self):
        back, front = A.layers(dict(A.DEFAULT, sex="feminino", hair="careca"))
        self.assertEqual(back, [])
        self.assertTrue(any(n.startswith("lashes-") for n in front))
        self.assertFalse(any(n.startswith("hair-") for n in front))

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
