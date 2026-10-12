"""Capture actual Tk creator windows with synthetic data (Linux/X11 only)."""

import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App
from core import Store
from customizer import AssetChoice, Swatch
from PIL import Image
from Xlib import X, display


def main():
    out = Path("validation/character-examples")
    out.mkdir(parents=True, exist_ok=True)
    dpy = display.Display()
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "synthetic.sqlite3")
        plan = store.save("plans", {"name": "Exemplos do personagem"})
        store.set_pref("active_plan", plan)
        store.set_pref("theme", "Norte Dourado")
        root = tk.Tk()
        app = App(root, store)
        errors = []
        root.report_callback_exception = lambda k, v, b: errors.append(str(v))

        def pump():
            deadline = time.monotonic() + 0.3
            while time.monotonic() < deadline:
                root.update()
                time.sleep(0.01)

        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)

        def choose(win, category, key):
            win.character_categories.current(category)
            win.character_categories.event_generate("<<ComboboxSelected>>")
            pump()
            choices = [w for w in walk(win) if isinstance(w, (AssetChoice, Swatch))]
            choices[key].command()
            pump()

        def capture(win, filename):
            win.lift()
            pump()
            wid = int(win.wm_frame(), 16) if win.wm_frame() else win.winfo_id()
            window = dpy.create_resource_object("window", wid)
            geo = window.get_geometry()
            raw = window.get_image(0, 0, geo.width, geo.height, X.ZPixmap, 0xFFFFFFFF)
            Image.frombytes(
                "RGB", (geo.width, geo.height), raw.data, "raw", "BGRX"
            ).save(out / filename)

        try:
            win = app.customize_character()
            pump()
            choose(win, 11, 1)  # author's moustache
            choose(win, 3, 1)  # wavy short
            win.character_name.set("Davi")
            capture(win, "masculino.png")
            choose(win, 0, 1)
            choose(win, 11, 0)
            choose(win, 3, 6)  # long straight
            choose(win, 4, 4)  # red hair
            choose(win, 2, 1)
            choose(win, 7, 5)
            choose(win, 10, 8)
            choose(win, 3, 6)
            win.character_name.set("Aurora")
            capture(win, "feminino.png")
            win.geometry("900x620")
            capture(win, "feminino-900x620.png")
            win.destroy()
            app.navigate("Jornada")
            pump()
            capture(root, "jornada.png")
            assert not errors, errors
            print("Captured actual Tk windows with temporary data:", out)
        finally:
            root.destroy()
            store.db.close()
            dpy.close()


if __name__ == "__main__":
    main()
