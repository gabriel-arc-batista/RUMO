"""Preview authentic data in both themes, capturing only our native window."""

import ctypes
import sqlite3
import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App
from core import Store, data_dir
from window_capture import capture_window

ctypes.windll.shcore.SetProcessDpiAwareness(1)
get_parent = ctypes.windll.user32.GetParent
get_parent.argtypes = [ctypes.c_void_p]
get_parent.restype = ctypes.c_void_p
output = Path(__file__).resolve().parents[1] / "validation"


def pump(root):
    until = time.monotonic() + 0.8
    while time.monotonic() < until:
        root.update()
        time.sleep(0.01)


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
    path = Path(folder) / "preview.sqlite3"
    reader = sqlite3.connect(
        (data_dir() / "estudos.sqlite3").resolve().as_uri() + "?mode=ro", uri=True
    )
    writer = sqlite3.connect(path)
    reader.backup(writer)
    writer.close()
    reader.close()
    store = Store(path)
    store.set_pref("backup_folder", str(Path(folder) / "backups"))
    root = tk.Tk()
    app = App(root, store)
    root.geometry("1366x768+16+16")
    root.lower()
    for theme in ["Escuro", "Claro"]:
        store.set_pref("theme", theme)
        app.apply_theme()
        app.build_shell()
        for term, name in [("", "edital-redesenhado-"), ("Java:", "edital-java-")]:
            app.edital_search = term
            app.navigate("Edital e assuntos")
            pump(root)
            capture_window(
                get_parent(root.winfo_id()), output / (name + theme.lower() + ".png")
            )
    store.db.close()
    root.destroy()
print("Four native-window previews saved from a consistent copy of personal data.")
