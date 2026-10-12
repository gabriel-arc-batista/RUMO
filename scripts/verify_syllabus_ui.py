"""Exercise real syllabus controls against a consistent copy of user data.

Screenshots contain the actual study state; no sample sessions are inserted.
All test clicks and theme changes affect only a temporary database.
"""

import ctypes
import json
import sqlite3
import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path
from PIL import ImageGrab
import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App, SECTIONS
from core import Store, data_dir
from ui import MotionButton
from window_capture import capture_window

ctypes.windll.shcore.SetProcessDpiAwareness(1)
output = Path(__file__).resolve().parents[1] / "validation"


def pump(root, seconds=0.55):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        root.update()
        time.sleep(0.01)


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def snap(root, name):
    pump(root)
    get_parent = ctypes.windll.user32.GetParent
    get_parent.argtypes = [ctypes.c_void_p]
    get_parent.restype = ctypes.c_void_p
    capture_window(get_parent(root.winfo_id()), output / name)


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
    database = Path(folder) / "review.sqlite3"
    actual = data_dir() / "estudos.sqlite3"
    if actual.exists():
        reader = sqlite3.connect(actual.resolve().as_uri() + "?mode=ro", uri=True)
        destination = sqlite3.connect(database)
        reader.backup(destination)
        destination.close()
        reader.close()
    store = Store(database)
    store.set_pref("backup_folder", str(Path(folder) / "backups"))
    root = tk.Tk()
    app = App(root, store)
    errors = []
    root.report_callback_exception = lambda kind, value, tb: errors.append(str(value))
    for size in ["1366x768", "1920x1080"]:
        root.geometry(size + "+0+0")
        for theme in ["Escuro", "Claro"]:
            store.set_pref("theme", theme)
            app.apply_theme()
            app.build_shell()
            for section in SECTIONS:
                app.navigate(section)
                pump(root)
                assert (
                    app.scroll.canvas.bbox("all")[2]
                    <= app.scroll.canvas.winfo_width() + 1
                ), section
                for widget in descendants(root):
                    if isinstance(widget, MotionButton) and widget.winfo_ismapped():
                        assert (
                            widget.winfo_rootx() + widget.winfo_width()
                            <= root.winfo_rootx() + root.winfo_width() + 1
                        ), (size, section, widget.text)
            app.navigate("Edital e assuntos")
            pump(root)
            assert not any(
                isinstance(w, tk.ttk.Treeview) for w in descendants(app.content)
            )
            assert len(app.edital_rows) == 0  # Lazy collapsed sections.
            sid = store.one(
                "SELECT id FROM subjects WHERE plan_id=? AND name='Bancos De Dados'",
                (app.plan,),
            )
            app.edital_expanded.add("s" + sid["id"])
            app.refresh()
            pump(root)
            roots = [
                r
                for r in app.edital_mapping.values()
                if r["subject_id"] == sid["id"] and not r["parent_id"]
            ]
            assert len(app.edital_rows) == 4
            modeling = next(t for t in roots if t["name"].startswith("2 "))
            app.edital_expanded.add(modeling["id"])
            app.refresh()
            pump(root)
            assert len(app.edital_rows) == 4 + len(
                [
                    t
                    for t in app.edital_mapping.values()
                    if t["parent_id"] == modeling["id"]
                ]
            )
            leaf = next(
                t
                for t in app.edital_mapping.values()
                if t["parent_id"] == modeling["id"]
            )
            app.edital_rows[leaf["id"]][2][-2].event_generate("<Button-1>")
            pump(root)
            assert app.edital_selected == leaf["id"]
            original = leaf["done"]
            app.scroll.canvas.yview_moveto(0.3)
            pump(root)
            original_scroll = app.scroll.canvas.yview()[0]
            button = next(
                w
                for w in descendants(app.edital_rows[leaf["id"]][0])
                if isinstance(w, MotionButton)
            )
            button.invoke()
            pump(root)
            assert (
                store.one("SELECT done FROM topics WHERE id=?", (leaf["id"],))["done"]
                != original
            )
            assert abs(app.scroll.canvas.yview()[0] - original_scroll) < 0.02, (
                original_scroll,
                app.scroll.canvas.yview(),
            )
            store.save("topics", {"id": leaf["id"], "done": original})
            app.edital_expanded.clear()
            app.refresh()
            pump(root)
            app.edital_search_entry.insert(0, "Java:")
            pump(root)
            java_matches = [
                t for t in app.edital_mapping.values() if "java:" in t["name"].lower()
            ]
            assert len(app.edital_rows) == len(java_matches)
            if size == "1366x768":
                snap(root, "edital-java-" + theme.lower() + ".png")
            # Accents do not prevent matching, and clearing restores laziness.
            app.edital_search_entry.delete(0, "end")
            app.edital_search_entry.insert(0, "normalizacao")
            pump(root)
            assert any(
                "Normalização:" in app.edital_mapping[tid]["name"]
                for tid in app.edital_rows
            )
            app.edital_search_entry.delete(0, "end")
            pump(root)
            assert len(app.edital_rows) == 0
            if size == "1366x768":
                snap(root, "edital-redesenhado-" + theme.lower() + ".png")
            app.edital_search = ""
            app.edital_selected = None
    assert not errors, errors
    report = {
        "sizes": ["1366x768", "1920x1080"],
        "themes": ["Escuro", "Claro"],
        "sections": 9,
        "actual_data_copy": True,
        "sample_sessions_inserted": 0,
        "lazy_subjects": True,
        "expand_nested_topics": True,
        "individual_completion": True,
        "completion_keeps_scroll_position": True,
        "search_java_details": len(java_matches),
        "accent_insensitive_search": True,
        "syllabus_horizontal_scroll": False,
        "errors": errors,
        "memory_mb": round(psutil.Process().memory_info().rss / 1024**2, 1),
    }
    (output / "syllabus-ui-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report))
    store.close()
    root.destroy()
