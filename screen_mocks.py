"""Simulados: first exam as the central action; then evolution and history.

Uses the same session records (category 'Simulado'), score formula and
details/edit/delete flows as before; only names, units and layout changed.
"""

import tkinter as tk
from datetime import date

from core import ratio
from theme import compact_duration, number, percent
from ui import MotionButton, Tooltip
from ui_kit import (
    ActionMenu,
    Card,
    Row,
    Section,
    Segmented,
    empty,
    help_button,
    label,
    stat_row,
)

HELP = (
    "Aproveitamento: acertos ÷ total de questões do simulado (brancos contam no total).\n"
    "Acertos sobre as respondidas: acertos ÷ (acertos + erros).\n\n"
    "Pontuação: acertos × valor do acerto − erros × desconto + brancos × valor do branco, "
    "como configurado no registro. Quando o simulado tem divisão por matéria, cada "
    "matéria é multiplicada pelo seu peso."
)


def render(app):
    filters = dict(app.filters, category="Simulado")
    rows = app.store.sessions(app.plan, filters, limit=500)
    filtered = any(key != "category" for key in app.filters)
    top = tk.Frame(app.content, bg=app.bg)
    top.pack(fill="x", pady=(0, 18))
    if rows:
        last = rows[0]
        best = max(
            rows, key=lambda r: ratio(r["correct"], r["wrong"], r["blank"], True) or 0
        )
        stat_row(
            top,
            app,
            [
                (number(len(rows)), "simulados registrados"),
                (
                    percent(ratio(last["correct"], last["wrong"], last["blank"], True)),
                    "de aproveitamento no último",
                    "Acertos ÷ total de questões do último simulado.",
                ),
                (
                    percent(ratio(last["correct"], last["wrong"])),
                    "de acertos nas respondidas",
                    "Acertos ÷ (acertos + erros) do último simulado.",
                ),
                (
                    percent(ratio(best["correct"], best["wrong"], best["blank"], True)),
                    "melhor aproveitamento",
                ),
            ],
        ).pack(side="left")
    MotionButton(
        top,
        text="Registrar simulado",
        icon="plus",
        style="Accent.TButton",
        command=lambda: app.session_form({"category": "Simulado"}),
    ).pack(side="right", anchor="n")
    ActionMenu(
        top,
        app,
        [("Filtrar por período, matéria ou texto", app.filter_form)]
        + ([("Limpar filtros", app.clear_filters)] if filtered else []),
        text="Filtros" + (" ativos" if filtered else ""),
        icon="list-filter",
    ).pack(side="right", anchor="n", padx=(0, 8))
    if not rows:
        card = Card(app.content, app, padding=(24, 40))
        card.pack(fill="x")
        if filtered:
            empty(
                card.body,
                app,
                "filter-x",
                "Nenhum simulado com estes filtros",
                "Os filtros também valem para Histórico e Estatísticas.",
                [("Limpar filtros", app.clear_filters)],
            ).pack(fill="x")
        else:
            empty(
                card.body,
                app,
                "swords",
                "Registre seu primeiro simulado",
                "Anote acertos, erros e brancos, como a banca pontua e, se quiser, o resultado por matéria. "
                "A evolução e o histórico aparecem aqui a partir do primeiro.",
                [
                    (
                        "Registrar simulado",
                        lambda: app.session_form({"category": "Simulado"}),
                        "plus",
                    )
                ],
            ).pack(fill="x")
        return
    evolution(app, rows)
    history(app, rows)


def evolution(app, rows):
    mode = app.store.pref("mock_chart", "Desempenho")
    head = Section(app.content, app, "Evolução")
    head.pack(fill="x", pady=(0, 8))
    help_button(head, app, "Como os simulados são calculados", HELP).pack(
        side="left", padx=(4, 0)
    )
    Segmented(
        head.actions,
        app,
        [("Desempenho", "Aproveitamento"), ("Pontuação", "Pontuação")],
        mode,
        lambda key: (app.store.set_pref("mock_chart", key), app.refresh()),
        height=30,
    ).pack(side="right")
    graph = [
        {
            "label": r["day"],
            "elapsed": r["elapsed"],
            "target": r["target"],
            "correct": r["correct"],
            "wrong": r["wrong"],
            "blank": r["blank"],
            "score": app.mock_score(r),
            "rate": ratio(r["correct"], r["wrong"], r["blank"], True) or 0,
        }
        for r in reversed(rows)
    ]
    card = Card(app.content, app, padding=(14, 6))
    card.pack(fill="x", pady=(0, 26))
    from charts import bars

    bars(
        app,
        graph,
        "rate" if mode == "Desempenho" else "score",
        parent=card.body,
        title=(
            "Aproveitamento por simulado (% de acertos sobre o total)"
            if mode == "Desempenho"
            else "Pontuação por simulado (pontos)"
        ),
        height=270,
    )


def history(app, rows):
    head = Section(app.content, app, "Histórico", count=len(rows))
    head.pack(fill="x", pady=(0, 8))
    card = Card(app.content, app, padding=(14, 8))
    card.pack(fill="x")
    for index, r in enumerate(rows):
        day = date.fromisoformat(r["day"]).strftime("%d/%m/%Y")
        parts = [day]
        if r["mock_format"]:
            parts.append(r["mock_format"])
        if r["elapsed"]:
            parts.append(compact_duration(r["elapsed"]))
        parts.append(
            f"{r['correct']} acertos · {r['wrong']} erros · {r['blank']} em branco"
        )
        row = Row(
            card.body,
            app,
            r["mock_name"] or "Simulado sem nome",
            " · ".join(parts),
            on_open=lambda r=r: app.mock_details(r),
            separator=index < len(rows) - 1,
        )
        row.pack(fill="x")
        ActionMenu(
            row.trail,
            app,
            [
                ("Ver detalhes e matérias", lambda r=r: app.mock_details(r)),
                (
                    "Editar simulado",
                    lambda r=r: app.session_form(
                        editing=app.store.one(
                            "SELECT * FROM sessions WHERE id=?", (r["id"],)
                        )
                    ),
                ),
                None,
                ("Excluir simulado", lambda r=r: app.remove_session(r["id"]), "danger"),
            ],
        ).pack(side="right", padx=(10, 0))
        score = app.mock_score(r)
        values = tk.Frame(row.trail, bg=row.base)
        values.pack(side="right")
        label(
            values,
            app,
            f"{score:g} pts".replace(".", ","),
            size=11,
            weight="bold",
            anchor="e",
        ).pack(anchor="e")
        label(
            values,
            app,
            percent(ratio(r["correct"], r["wrong"], r["blank"], True))
            + " de aproveitamento",
            size=9,
            tone="muted",
            anchor="e",
        ).pack(anchor="e")
        Tooltip(
            values,
            "Pontuação conforme a regra do registro; aproveitamento sobre o total.",
        )
        row.refresh_bindings()
