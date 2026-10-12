"""Leitor nativo: marcações de outra versão só vêm por ação explícita.

Dados temporários, PDF de teste e nenhuma rede. Também confere a opção
"Manter conectado" desligada por padrão e sem arquivo de login.
"""

import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App
from core import Store
from pdf_reader import Reader
from training_content import ContentManager


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


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
            with patch("screen_account.SupabaseTransport") as transport:
                app.navigate("Configurações e ajuda")
                root.update()
                remember = [
                    w
                    for w in descendants(app.content)
                    if isinstance(w, ttk.Checkbutton)
                    and w.cget("text").startswith("Manter conectado")
                ]
                assert len(remember) == 1, "opção Manter conectado ausente"
                assert not store.path.with_name("study-sync-login.json").exists()
                transport.assert_not_called()

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
            # Leitura antiga, numa versão anterior fictícia do mesmo PDF de teste.
            app.training.mark_page(lesson["id"], "0.9.0", 1, 4, True)
            app.training.mark_page(lesson["id"], "0.9.0", 2, 4, True)

            reader = Reader(app.content, app, lesson, path, version)
            reader.pack(fill="both", expand=True)
            root.update()
            count = reader.pdf.count
            assert (
                app.training.reading(lesson["id"], version, count)["read_pages"] == []
            )
            # MotionButton guarda texto e ação em atributos próprios.
            button = next(
                w
                for w in descendants(reader)
                if getattr(w, "text", None) == "Trazer marcações"
            )
            button.command()
            root.update()
            dialog = next(
                w
                for w in root.winfo_children()
                if isinstance(w, tk.Toplevel)
                and w.title() == "Trazer marcações da versão anterior"
            )
            entry = next(w for w in descendants(dialog) if isinstance(w, ttk.Entry))
            assert entry.get() == "1-2", entry.get()
            entry.delete(0, "end")
            entry.insert(0, "2")
            confirm = next(
                w
                for w in descendants(dialog)
                if isinstance(w, ttk.Button)
                and w.cget("text") == "Marcar estas páginas"
            )
            confirm.invoke()
            root.update()
            assert app.training.reading(lesson["id"], version, count)["read_pages"] == [
                2
            ]
            assert app.training.reading(lesson["id"], "0.9.0", 4)["read_pages"] == [
                1,
                2,
            ]
            assert store.rpg.profile(plan)["xp"] == 0
            reader.destroy()
            root.update()
            assert not errors, errors
            print(
                "Native version carry + remember option: passed, explicit only, old version preserved, no network"
            )
        finally:
            app.close()


if __name__ == "__main__":
    main()
