"""Check native animation lifecycle, reduced motion and repeated navigation."""

import json
import sys
import tempfile
import time
import tkinter as tk
from tkinter import font as tkfont
import gc
import psutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App, SECTIONS
from core import Store
from ui import MetricCard


def pump(root, seconds=0.75):
    finish = time.monotonic() + seconds
    while time.monotonic() < finish:
        root.update()
        time.sleep(0.01)


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
    root = tk.Tk()
    app = App(root, Store(Path(folder) / "design.sqlite3"))
    errors = []
    root.report_callback_exception = lambda kind, value, tb: errors.append(str(value))
    pump(root)
    assert float(root.attributes("-alpha")) == 1
    assert tkfont.Font(root, family="Inter").actual("family") == "Inter"
    # Check actual intermediate frames, rather than only final colors.
    app.navigate("Início")
    root.update_idletasks()
    pump(root, 0.08)
    fresh = [
        w
        for frame in app.content.winfo_children()
        for w in frame.winfo_children()
        if isinstance(w, MetricCard)
    ]
    assert all(0 < w.intro < 1 for w in fresh), [w.intro for w in fresh]
    pump(root)
    assert all(w.intro == 1 for w in fresh)
    assert app.sidebar.winfo_ismapped() and app.sidebar.winfo_width() == 230
    assert app.scroll.winfo_x() >= 230
    app.toggle_sidebar()
    pump(root)
    assert not app.sidebar.winfo_ismapped()
    app.toggle_sidebar()
    pump(root)
    assert app.sidebar.winfo_ismapped()
    button = app.floating
    button.event_generate("<Leave>")
    pump(root)
    resting = button.current
    button.event_generate("<Enter>")
    assert button in app.motion.jobs
    pump(root)
    assert button.current != resting and button not in app.motion.jobs
    button.event_generate("<Leave>")
    pump(root)
    assert button.current.lower() == resting.lower()
    card = next(
        w
        for frame in app.content.winfo_children()
        for w in frame.winfo_children()
        if isinstance(w, MetricCard)
    )
    for frame in app.content.winfo_children():
        for metric in frame.winfo_children():
            if not isinstance(metric, MetricCard):
                continue
            value = next(
                i
                for i in metric.find_all()
                if metric.type(i) == "text"
                and metric.itemcget(i, "text") == str(metric.value)
            )
            assert metric.bbox(value)[2] <= metric.winfo_width() - 16, (
                metric.value,
                metric.bbox(value),
            )
    card.event_generate("<Enter>")
    pump(root)
    assert card.hover == 1
    card.event_generate("<Leave>")
    pump(root)
    assert card.hover == 0
    app.open_clock()
    pump(root)
    win = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
    assert float(win.attributes("-alpha")) == 1
    win.destroy()
    subject = app.store.one(
        "SELECT * FROM subjects WHERE plan_id=? LIMIT 1", (app.plan,)
    )
    topic = app.store.one(
        "SELECT * FROM topics WHERE subject_id=? LIMIT 1", (subject["id"],)
    )
    app.clock.start(
        {
            "plan_id": app.plan,
            "subject_id": subject["id"],
            "topic_id": topic["id"],
            "category": "Teoria",
            "target": 1800,
            "day": app.today().isoformat(),
            "start_time": "10:00",
        },
        "Timer",
    )
    app.open_clock()
    clock = app.clock_win
    root.update_idletasks()
    pump(root, 0.08)
    first_y = clock.winfo_y()
    first_alpha = float(clock.attributes("-alpha"))
    assert 0 < first_alpha < 1
    pump(root)
    assert float(clock.attributes("-alpha")) == 1 and first_y > clock.winfo_y()
    app.clock.discard()
    clock.destroy()
    pump(root)
    # Destroy a window during its fade and ensure callbacks are removed.
    app.open_clock()
    win = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
    win.destroy()
    pump(root)
    for section in SECTIONS:
        app.navigate(section)
        root.update()
    gc.collect()
    before = psutil.Process().memory_info().rss
    for _ in range(4):
        for section in SECTIONS:
            app.navigate(section)
            root.update()
    pump(root)
    gc.collect()
    growth = psutil.Process().memory_info().rss - before
    assert growth < 5 * 1024**2, growth
    # Several page changes before processing idle callbacks must be safe too.
    for section in SECTIONS:
        app.navigate(section)
    pump(root)
    app.store.set_pref("animations", False)
    app.apply_theme()
    app.build_shell()
    app.refresh()
    pump(root)
    button = app.floating
    button.event_generate("<Enter>")
    assert (
        button.current.lower() == button.colors()[1].lower()
        and button not in app.motion.jobs
    )
    app.open_clock()
    win = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
    assert float(win.attributes("-alpha")) == 1
    win.destroy()
    pump(root)
    assert not app.motion.jobs and not errors, (app.motion.jobs, errors)
    report = {
        "hover_transitions": True,
        "cards_hover": True,
        "window_fade": True,
        "destroy_during_animation": True,
        "inter_loaded": True,
        "card_entrance_intermediate_frames": True,
        "persistent_collapsible_sidebar": True,
        "clock_slide_and_fade": True,
        "navigation_memory_growth_mb": round(growth / 1024**2, 2),
        "rapid_navigation": True,
        "empty_metric_text_fits": True,
        "reduced_motion": True,
        "idle_animation_callbacks": 0,
        "errors": errors,
    }
    (Path(__file__).resolve().parents[1] / "validation/design-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report))
    app.store.db.close()
    root.destroy()
