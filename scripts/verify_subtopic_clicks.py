"""Regression: real arrow/name clicks must keep the surrounding list alive."""

import ctypes
import os
import gc
import json
import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path
import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App
from core import Store

if os.name == "nt":
    ctypes.windll.shcore.SetProcessDpiAwareness(1)


def pump(root, seconds=0.15):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        root.update()
        time.sleep(0.005)


click_time = 0


def click(widget):
    global click_time
    click_time += 1000
    widget.event_generate("<ButtonPress-1>", x=10, y=10, time=click_time)
    widget.event_generate("<ButtonRelease-1>", x=10, y=10, time=click_time + 50)


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
    root = tk.Tk()
    store = Store(Path(folder) / "clicks.sqlite3")
    app = App(root, store)
    errors = []
    root.report_callback_exception = lambda kind, value, tb: errors.append(str(value))
    timings = []
    for theme in ["Escuro", "Claro"]:
        store.set_pref("theme", theme)
        app.apply_theme()
        app.build_shell()
        app.navigate("Edital e assuntos")
        pump(root, 0.5)
        sid = store.one(
            "SELECT id FROM subjects WHERE plan_id=? AND name='Bancos De Dados'",
            (app.plan,),
        )["id"]
        subject_key = "s" + sid
        subject_button = app.edital_branch_buttons[subject_key]
        other = next(
            b for k, b in app.edital_branch_buttons.items() if k != subject_key
        )
        started = time.perf_counter()
        click(subject_button)
        pump(root)
        timings.append(time.perf_counter() - started)
        assert subject_button.winfo_exists() and other.winfo_exists()
        roots = [
            t
            for t in app.edital_mapping.values()
            if t["subject_id"] == sid and not t["parent_id"]
        ]
        for index, topic in enumerate(roots):
            row = app.edital_rows[topic["id"]][0]
            position = max(
                0,
                (row.winfo_rooty() - app.content.winfo_rooty() - 100)
                / app.content.winfo_height(),
            )
            app.scroll.canvas.yview_moveto(position)
            pump(root)
            before = row.winfo_rooty()
            arrow = app.edital_branch_buttons[topic["id"]]
            started = time.perf_counter()
            click(arrow)
            pump(root)
            timings.append(time.perf_counter() - started)
            assert (
                row.winfo_exists()
                and subject_button.winfo_exists()
                and other.winfo_exists()
            )
            assert abs(row.winfo_rooty() - before) <= 2, (before, row.winfo_rooty())
            descendants = [
                t for t in app.edital_mapping.values() if t["parent_id"] == topic["id"]
            ]
            assert all(t["id"] in app.edital_rows for t in descendants)
            last = app.edital_rows[descendants[-1]["id"]][0]
            if index + 1 < len(roots):
                assert (
                    last.winfo_rooty()
                    < app.edital_rows[roots[index + 1]["id"]][0].winfo_rooty()
                )
            leaf = descendants[0]
            label = app.edital_rows[leaf["id"]][2][-2]
            before = label.winfo_rooty()
            click(label)
            pump(root)
            assert app.edital_selected == leaf["id"]
            assert abs(label.winfo_rooty() - before) <= 2, (
                "Selecting a leaf displaced its row",
                topic["name"],
                leaf["name"],
                before,
                label.winfo_rooty(),
            )
            click(arrow)
            pump(root)
            assert row.winfo_exists()
            assert all(t["id"] not in app.edital_rows for t in descendants)
            parent_label = app.edital_rows[topic["id"]][2][-2]
            click(parent_label)
            pump(root)
            assert all(
                t["id"] in app.edital_rows for t in descendants
            ), "Clicking the topic name did not open its children"
            click(parent_label)
            pump(root)
            assert all(t["id"] not in app.edital_rows for t in descendants)
            assert not errors, errors
        # Repeated opening/collapsing must not keep widgets or callbacks alive.
        arrow = app.edital_branch_buttons[roots[0]["id"]]
        gc.collect()
        before_memory = psutil.Process().memory_info().rss
        for _ in range(20):
            arrow.invoke()
            pump(root, 0.025)
            arrow.invoke()
            pump(root, 0.025)
        pump(root, 0.5)
        gc.collect()
        growth = psutil.Process().memory_info().rss - before_memory
        assert growth < 8 * 1024**2, growth
        # Search shows a flat list, without duplicating expanded descendants.
        app.edital_search_entry.insert(0, "SQL")
        pump(root, 0.4)
        assert len(app.edital_rows) == len(
            {
                t["id"]
                for t in app.edital_mapping.values()
                if "sql" in t["name"].casefold()
            }
        )
        matched_parent = next(t for t in roots if t["name"].startswith("3 "))
        click(app.edital_rows[matched_parent["id"]][2][-2])
        pump(root, 0.5)
        assert not app.edital_search_entry.get()
        assert all(
            t["id"] in app.edital_rows
            for t in app.edital_mapping.values()
            if t["parent_id"] == matched_parent["id"]
        )
        assert not errors, errors
        app.edital_search = ""
        app.edital_selected = None
        app.edital_expanded.clear()
    assert max(timings) < 3, timings
    report = {
        "actual_arrow_and_name_mouse_events": True,
        "surrounding_widgets_preserved": True,
        "selection_keeps_row_position": True,
        "topic_name_opens_and_closes_children": True,
        "search_parent_reveals_hierarchy": True,
        "children_below_their_parent": True,
        "collapse_frees_descendants": True,
        "repeated_expand_collapse": 40,
        "search_does_not_duplicate_descendants": True,
        "max_click_seconds": round(max(timings), 3),
        "errors": errors,
    }
    (
        Path(__file__).resolve().parents[1] / "validation/subtopic-clicks-report.json"
    ).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    store.close()
    root.destroy()
