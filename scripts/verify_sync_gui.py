"""Native account/reader regression with temporary data and no network."""

import sys
import tempfile
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App
from core import Store
from desktop_sync import workspace_for
from pdf_reader import Reader
from training_content import ContentManager
from service_config import PUBLIC_KEY, SERVICE_URL


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def verify_service_defaults(app, root):
    """Disconnected settings never instantiate a network transport."""
    with patch("screen_account.SupabaseTransport") as transport:
        app.navigate("Configurações e ajuda")
        root.update()
        buttons = [
            widget
            for widget in descendants(app.content)
            if isinstance(widget, ttk.Button)
            and widget.cget("text") == "Configuração do serviço"
        ]
        assert len(buttons) == 1, "Service settings toggle missing"
        toggle = buttons[0]
        entries = [
            widget
            for widget in descendants(toggle.master)
            if isinstance(widget, ttk.Entry)
        ]
        url = next(widget for widget in entries if widget.get() == SERVICE_URL)
        key = next(widget for widget in entries if widget.get() == PUBLIC_KEY)
        advanced = url.master
        assert key.master == advanced
        assert not advanced.winfo_manager(), "Advanced settings should start hidden"
        assert not url.winfo_ismapped() and not key.winfo_ismapped()
        for _ in range(2):
            toggle.invoke()
            root.update()
            assert advanced.winfo_manager() == "pack"
            assert url.get() == SERVICE_URL and key.get() == PUBLIC_KEY
            toggle.invoke()
            root.update()
            assert not advanced.winfo_manager()
        credentials = [entry for entry in entries if entry.master != advanced]
        assert len(credentials) == 2
        assert all(entry.get() == "" for entry in credentials)
        assert sum(bool(entry.cget("show")) for entry in credentials) == 1
        assert workspace_for(app.store).account_id is None
        transport.assert_not_called()


def main():
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "test.sqlite3")
        plan = store.save("plans", dict(name="Exemplo temporário"))
        store.set_pref("active_plan", plan)
        root = tk.Tk()
        errors = []
        root.report_callback_exception = lambda kind, value, trace: errors.append(
            str(value)
        )
        app = App(root, store)
        try:
            verify_service_defaults(app, root)
            assert workspace_for(store).account_id is None
            app._content = ContentManager(
                Path(folder) / "content",
                dict(
                    mode="local", path=str(Path("tests/fixtures/campo-teste").resolve())
                ),
            )
            app._content.refresh()
            app._training = None
            lesson = next(x for x in app.training.library() if x["test"])
            app._content.download(lesson)
            path, version = app.training.file_for(lesson)
            reader = Reader(app.content, app, lesson, path, version)
            reader.pack(fill="both", expand=True)
            root.update()
            assert not reader.read_var.get()
            reader.go(reader.pdf.count - 1)
            assert not app.training.reading(lesson["id"], version, reader.pdf.count)[
                "completed"
            ]
            reader.read_var.set(True)
            reader.mark_read()
            assert (
                reader.pdf.count
                in app.training.reading(lesson["id"], version, reader.pdf.count)[
                    "read_pages"
                ]
            )
            for page in range(reader.pdf.count):
                reader.go(page)
                reader.read_var.set(True)
                reader.mark_read()
            assert app.training.reading(lesson["id"], version, reader.pdf.count)[
                "completed"
            ]
            reader.read_var.set(False)
            reader.mark_read()
            assert not app.training.reading(lesson["id"], version, reader.pdf.count)[
                "completed"
            ]
            assert store.stats(plan)["count"] == 0
            assert store.rpg.profile(plan)["xp"] == 0
            reader.destroy()
            root.update()
            assert not errors, errors
            print(
                "Native account defaults/toggle + manual reading: passed, temporary data only, no network"
            )
        finally:
            app.close()


if __name__ == "__main__":
    main()
