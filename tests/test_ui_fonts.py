"""Platform boundary regression: Windows font loading must reach native GDI."""

import ctypes
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import ui


class PrivateFontTests(unittest.TestCase):
    def test_windows_registers_bundled_fonts_once_without_linux_import_shadow(self):
        root = SimpleNamespace()
        assets = Path(__file__).resolve().parents[1] / "assets"
        add = Mock(return_value=1)
        native = SimpleNamespace(gdi32=SimpleNamespace(AddFontResourceExW=add))
        expected = [
            p for pattern in ui.PRIVATE_FONTS for p in (assets / "fonts").glob(pattern)
        ]
        self.assertTrue(expected)
        with (
            patch.object(ui, "os", SimpleNamespace(name="nt")),
            patch.object(ctypes, "windll", native, create=True),
            patch.object(ui.tkfont, "families", return_value=["Inter", "lucide"]),
        ):
            self.assertEqual(ui.load_fonts(root, assets), "Inter")
            self.assertTrue(root._icons_available)
            self.assertEqual(add.call_count, len(expected))
            for path in expected:
                add.assert_any_call(str(path), 0x10, None)
            ui.load_fonts(root, assets)
            self.assertEqual(add.call_count, len(expected))


if __name__ == "__main__":
    unittest.main()
