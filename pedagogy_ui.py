"""Small native editor for optional prerequisites, reusing the existing forms."""

import tkinter as tk
from tkinter import ttk

from pedagogy import graph, plan_topics, save_graph
from ui import MotionButton

LABELS = {
    "Essencial": "essential",
    "Recomendado": "recommended",
    "Pode estudar em paralelo": "parallel",
}


def edit_dependencies(app, topic):
    from app import Form

    rows = plan_topics(app.store, app.plan)
    nodes = {r["id"]: r for r in rows}
    names = {
        r["id"]: r["name"]
        for r in app.store.rows(
            "SELECT id,name FROM subjects WHERE plan_id=?", (app.plan,)
        )
    }
    choices = {}
    for row in rows:
        if row["id"] == topic["id"]:
            continue
        label = names[row["subject_id"]] + " › " + row["name"]
        while label in choices:
            label += " ·"
        choices[label] = row["id"]
    window = tk.Toplevel(app.root)
    window.title("Conhecimentos anteriores")
    window.configure(bg=app.bg)
    window.geometry("780x450")
    window.transient(app.root)
    ttk.Label(window, text=topic["name"], style="Title.TLabel", wraplength=730).pack(
        anchor="w", padx=18, pady=(18, 8)
    )
    ttk.Label(
        window,
        text="Estas relações orientam a trilha. Você continua livre para estudar qualquer assunto.",
        wraplength=730,
    ).pack(anchor="w", padx=18, pady=(0, 12))
    tree = ttk.Treeview(
        window, columns=("kind", "name"), show="headings", selectmode="browse", height=8
    )
    tree.heading("kind", text="Relação")
    tree.heading("name", text="Conhecimento anterior / paralelo")
    tree.column("kind", width=160, stretch=False)
    tree.column("name", width=540)
    tree.pack(fill="both", expand=True, padx=18)
    listed = {}

    def refresh():
        tree.delete(*tree.get_children())
        listed.clear()
        for edge in graph(app.store, app.plan):
            if edge["after"] == topic["id"]:
                key = tree.insert(
                    "",
                    "end",
                    values=(
                        next(k for k, v in LABELS.items() if v == edge["kind"]),
                        nodes[edge["before"]]["name"],
                    ),
                )
                listed[key] = edge

    def add():
        def save(values):
            before = choices.get(values["before"])
            if not before:
                raise ValueError("Escolha um assunto do concurso atual.")
            edges = graph(app.store, app.plan)
            edges = [
                e for e in edges if (e["before"], e["after"]) != (before, topic["id"])
            ]
            edges.append(
                dict(before=before, after=topic["id"], kind=LABELS[values["kind"]])
            )
            save_graph(app.store, app.plan, edges)
            refresh()

        form = Form(
            app,
            "Adicionar conhecimento anterior",
            [
                (
                    "before",
                    "Assunto (inclui outras disciplinas)",
                    "choice",
                    sorted(choices),
                ),
                ("kind", "Relação pedagógica", "choice", list(LABELS)),
            ],
            save,
            {"kind": "Recomendado"},
        )
        form.refresh_on_submit = False

    def remove():
        selected = tree.selection()
        if not selected:
            return
        edge = listed[selected[0]]
        save_graph(
            app.store, app.plan, [e for e in graph(app.store, app.plan) if e != edge]
        )
        refresh()

    def close():
        window.destroy()
        app.refresh()

    bar = ttk.Frame(window)
    bar.pack(fill="x", padx=18, pady=16)
    MotionButton(bar, text="Adicionar relação", command=add).pack(side="left")
    MotionButton(bar, text="Remover relação selecionada", command=remove).pack(
        side="left", padx=8
    )
    MotionButton(bar, text="Concluir", command=close).pack(side="right")
    window.protocol("WM_DELETE_WINDOW", close)
    refresh()
    app.motion.reveal(window)
    return window
