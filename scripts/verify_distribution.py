"""Launch the actual compiled application, using an isolated data directory."""

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path
import psutil
from PIL import ImageGrab

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Store
from window_capture import capture_window

project = Path(__file__).resolve().parents[1]
executable = Path(sys.argv[1]) if len(sys.argv) > 1 else project / "dist/RUMO/RUMO.exe"
output = project / "validation"
output.mkdir(exist_ok=True)
user32 = ctypes.windll.user32
ctypes.windll.shcore.SetProcessDpiAwareness(1)
user32.PostMessageW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]


def windows(pid):
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, param):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title, 512)
            found.append((hwnd, title.value))
        return True

    user32.EnumWindows(callback, 0)
    return found


def is_main_window(hwnd, title):
    # The integrated shell no longer appends the plan to its title. A native
    # second-instance message box uses the same title, but is not TkTopLevel.
    name = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW(hwnd, name, len(name))
    return title == "RUMO — Estudos" and name.value == "TkTopLevel"


def await_main(process):
    start = time.perf_counter()
    while time.perf_counter() - start < 20:
        if process.poll() is not None:
            raise AssertionError(f"Executable exited with {process.returncode}")
        matches = [(h, t) for h, t in windows(process.pid) if is_main_window(h, t)]
        if matches:
            return matches[0][0], round(time.perf_counter() - start, 2)
        time.sleep(0.15)
    raise AssertionError("Main window did not appear")


def close(process, hwnd):
    user32.PostMessageW(hwnd, 0x0010, 0, 0)
    process.wait(timeout=10)
    assert process.returncode == 0


tmp = tempfile.TemporaryDirectory()
folder = Path(tmp.name) / "data"
env = dict(os.environ, RUMO_DATA=str(folder))
env.pop("PYTHONPATH", None)
processes = []
try:
    first = subprocess.Popen([str(executable)], env=env, cwd=tmp.name)
    processes.append(first)
    hwnd, startup = await_main(first)
    time.sleep(1.5)
    process = psutil.Process(first.pid)
    memory = process.memory_info().rss / 1024**2
    cpu = process.cpu_percent(interval=2)
    connections = process.net_connections(kind="inet")
    assert not connections, connections
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    work = wintypes.RECT()
    assert user32.SystemParametersInfoW(48, 0, ctypes.byref(work), 0)
    assert rect.bottom <= work.bottom and rect.right <= work.right + 8, (
        rect.bottom,
        work.bottom,
        rect.right,
        work.right,
    )
    capture_window(hwnd, output / "executavel-windows.png")
    second = subprocess.Popen([str(executable)], env=env, cwd=tmp.name)
    processes.append(second)
    time.sleep(0.8)
    assert not [
        title for h, title in windows(second.pid) if is_main_window(h, title)
    ], "Second counting instance was opened"
    for h, t in windows(second.pid):
        user32.PostMessageW(h, 0x0010, 0, 0)
    try:
        second.wait(timeout=3)
    except subprocess.TimeoutExpired:
        second.terminate()
        second.wait(timeout=5)
    close(first, hwnd)
    store = Store(folder / "estudos.sqlite3")
    plans = store.rows("SELECT * FROM plans")
    assert len(plans) == 2
    assert store.stats(plans[0]["id"])["count"] == 0
    total_topics = len(store.rows("SELECT * FROM topics"))
    assert total_topics == 1377, total_topics
    assert len(store.pref("bacen_guide_ids", [])) == 1090
    pid = store.pref("active_plan")
    subject = store.one("SELECT * FROM subjects WHERE plan_id=? LIMIT 1", (pid,))
    topic = store.one(
        "SELECT * FROM topics WHERE subject_id=? LIMIT 1", (subject["id"],)
    )
    store.save_session(
        {
            "plan_id": pid,
            "subject_id": subject["id"],
            "topic_id": topic["id"],
            "day": "2026-10-10",
            "category": "Teoria",
            "target": 3600,
            "elapsed": 2700,
            "correct": 15,
            "wrong": 5,
            "blank": 0,
        }
    )
    store.set_pref("theme", "Claro")
    store.db.close()
    restart = subprocess.Popen([str(executable)], env=env, cwd=tmp.name)
    processes.append(restart)
    hwnd, _ = await_main(restart)
    time.sleep(0.3)
    close(restart, hwnd)
    store = Store(folder / "estudos.sqlite3")
    assert (
        store.stats(pid)["rate"] == 75
        and store.stats(pid)["elapsed"] == 2700
        and store.pref("theme") == "Claro"
    )
    store.db.close()
    # Exercise first-run migration with the real packaged executable, in isolation.
    upgrade_base = Path(tmp.name) / "upgrade-data"
    previous = upgrade_base / "previous-installation"
    previous.mkdir(parents=True)
    original = Store(folder / "estudos.sqlite3")
    import sqlite3

    destination = sqlite3.connect(previous / "estudos.sqlite3")
    original.db.backup(destination)
    destination.close()
    expected = original.snapshot()["tables"]
    original.db.close()
    upgrade_env = dict(env, LOCALAPPDATA=str(upgrade_base))
    upgrade_env.pop("RUMO_DATA", None)
    upgraded = subprocess.Popen([str(executable)], env=upgrade_env, cwd=tmp.name)
    processes.append(upgraded)
    hwnd, _ = await_main(upgraded)
    close(upgraded, hwnd)
    migrated = Store(upgrade_base / "RUMO/estudos.sqlite3")
    assert migrated.stats(pid)["elapsed"] == 2700
    assert migrated.stats(pid)["rate"] == 75
    assert migrated.pref("theme") == "Claro"
    assert migrated.pref("active_plan") == pid
    migrated.db.close()
    original = Store(previous / "estudos.sqlite3")
    assert original.snapshot()["tables"] == expected
    original.db.close()
    report = {
        "platform": "Windows 11 x64",
        "exe": str(executable),
        "startup_seconds": startup,
        "resident_memory_mb": round(memory, 1),
        "idle_cpu_percent": cpu,
        "inet_connections": len(connections),
        "second_instance_blocked": True,
        "restart_persistence": True,
        "previous_installation_migrated": True,
        "migration_source_unchanged": True,
        "historical_bacen_plans": 2,
        "historical_topic_entries": 287,
        "guide_topic_entries": 1090,
        "initial_study_sessions": 0,
        "isolated_data": True,
        "external_python_required": False,
        "offline_note": "No internet sockets observed; source has no runtime network dependency. System network was not disabled.",
    }
    (output / "distribution-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))
finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
    tmp.cleanup()
