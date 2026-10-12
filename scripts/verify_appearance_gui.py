"""Exercise all themes and appearance controls using only synthetic study data."""

import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import appearance as A
from app import App
from core import Store
from customizer import Swatch, AssetChoice
from theme import THEME_NAMES
from ui import LOOK_CACHE, MotionButton, Portrait, CharacterView


def main():
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "appearance.sqlite3")
        plan = store.save("plans", {"name": "QA aparência"})
        store.set_pref("active_plan", plan)
        root = tk.Tk()
        app = App(root, store)
        errors = []
        root.report_callback_exception = lambda kind, value, tb: errors.append(
            str(value)
        )

        def pump():
            until = time.monotonic() + 0.12
            while time.monotonic() < until:
                root.update()
                time.sleep(0.005)

        def controls(widget):
            for child in widget.winfo_children():
                if isinstance(child, (MotionButton, Swatch, AssetChoice)):
                    yield child
                yield from controls(child)

        def check_visible_images(widget):
            names = set(root.tk.splitlist(root.tk.call("image", "names")))
            if isinstance(widget, (Portrait, CharacterView)):
                for item in widget.find_all():
                    if widget.type(item) == "image":
                        assert (
                            widget.itemcget(item, "image") in names
                        ), "Visible avatar layer was evicted"
            for child in widget.winfo_children():
                check_visible_images(child)

        def click(win, label):
            next(
                w
                for w in controls(win)
                if (isinstance(w, MotionButton) and w.cget("text") == label)
                or (isinstance(w, AssetChoice) and w.label == label)
            ).command()
            pump()

        try:
            before = store.stats(plan)
            for name in THEME_NAMES:
                store.set_pref("theme", name)
                app.apply_theme()
                app.refresh()
                pump()
                win = app.customize_character()
                pump()
                assert app.customize_character() is win
                for index, (field, _, options) in enumerate(A.FIELDS):
                    win.character_categories.current(index)
                    win.character_categories.event_generate("<<ComboboxSelected>>")
                    pump()
                    choices = [
                        w for w in controls(win) if isinstance(w, (Swatch, AssetChoice))
                    ]
                    assert len(choices) == len(options)
                    for widget in choices:
                        widget.command()
                        pump()
                check_visible_images(root)
                click(win, "Aleatório")
                click(win, "Restaurar padrão")
                click(win, "Salvar aparência")
                assert app.character_look() == A.DEFAULT
                win = app.customize_character()
                pump()
                click(win, "Feminino")
                win.character_name.set("Aurora")
                click(win, "Salvar aparência")
                assert app.character_look()["sex"] == "feminino"
                assert store.rpg.profile(plan)["name"] == "Aurora"
                saved = app.character_look()
                win = app.customize_character()
                pump()
                win.character_name.set("Nome cancelado")
                click(win, "Restaurar padrão")
                click(win, "Cancelar")
                assert store.rpg.profile(plan)["name"] == "Aurora"
                assert app.character_look() == saved
                assert len([k for k in app.images if "/look/" in k]) <= LOOK_CACHE
            assert store.stats(plan) == before
            assert app.journey.character(plan).xp == 0
            assert not errors, errors
            # Exercise many looks and report bounded resident memory/image buffers.
            import psutil
            from unittest.mock import patch

            rss_before = psutil.Process().memory_info().rss
            with (
                patch(
                    "socket.create_connection",
                    side_effect=AssertionError("Network forbidden"),
                ),
                patch(
                    "urllib.request.urlopen",
                    side_effect=AssertionError("Network forbidden"),
                ),
            ):
                win = app.customize_character()
                pump()
                for _ in range(120):
                    click(win, "Aleatório")
                check_visible_images(root)
                click(win, "Cancelar")
            rss_after = psutil.Process().memory_info().rss
            assert len([k for k in app.images if "/look/" in k]) <= LOOK_CACHE
            print(
                f"Memory after browsing: {rss_after/1024**2:.1f} MiB RSS; delta {max(0,rss_after-rss_before)/1024**2:.1f} MiB; LRU <= {LOOK_CACHE} images."
            )
            store.close()
            reopened = Store(Path(folder) / "appearance.sqlite3")
            assert reopened.pref(A.PREFERENCE) == saved
            reopened.db.close()
            print(
                f"Appearance GUI passed: {len(THEME_NAMES)} themes, all options, save/cancel/reset/random, bounded cache, persistence and unchanged study metrics."
            )
        finally:
            app.motion.enabled = False
            root.destroy()


if __name__ == "__main__":
    main()
