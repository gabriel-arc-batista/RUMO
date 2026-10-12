"""Estatísticas: one period control, one export menu, time first, then questions.

All numbers come from Store.stats/grouped with the active filters (unchanged
aggregations: accuracy is weighted by answered questions, never an average of
percentages). Only the organization, names and empty states changed.
"""

import tkinter as tk
from datetime import timedelta

from core import duration, ratio, uid
from theme import compact_duration, number, percent
from ui import Columns, MotionButton
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
    "Aproveitamento: acertos ÷ (acertos + erros), somando as questões de todos os "
    "registros do filtro. Dias sem questões não entram como 0%.\n\n"
    "Constância: dias com estudo ÷ dias do período. Tempo líquido desconta pausas.\n\n"
    "Os gráficos mostram até 60 grupos recentes; os arquivos CSV trazem tudo o que "
    "está no filtro."
)
GROUPS = [("day", "Dia"), ("week", "Semana"), ("month", "Mês")]


def period_key(app):
    """Which quick period matches the current filters ('' when custom)."""
    f = app.filters
    if not f.get("from") and not f.get("to"):
        return "all"
    today = app.today()
    week = app.week_bounds()
    candidates = {
        "7": (today - timedelta(days=6), today),
        "30": (today - timedelta(days=29), today),
        "week": week,
        "month": (today.replace(day=1), today),
    }
    current = (f.get("from"), f.get("to"))
    for key, (begin, end) in candidates.items():
        if current == (begin.isoformat(), end.isoformat()):
            return key
    return ""


def set_period(app, key):
    if key == "all":
        app.filters.pop("from", None)
        app.filters.pop("to", None)
        app.history_offset = 0
        app.refresh()
    elif key in ("7", "30"):
        app.period_filter(int(key))
    elif key == "week":
        app.filter_week()
    elif key == "month":
        app.filter_month()


def controls(app):
    bar = tk.Frame(app.content, bg=app.bg)
    bar.pack(fill="x", pady=(0, 6))
    Segmented(
        bar,
        app,
        [
            ("7", "7 dias"),
            ("30", "30 dias"),
            ("week", "Esta semana"),
            ("month", "Este mês"),
            ("all", "Tudo"),
        ],
        period_key(app),
        lambda key: set_period(app, key),
    ).pack(side="left")
    ActionMenu(
        bar,
        app,
        [
            ("Registros de estudo, um por linha (CSV)", app.export_csv),
            ("Resumo por matéria, categoria e assunto (CSV)", app.export_stats_csv),
        ],
        text="Exportar",
        icon="download",
    ).pack(side="right")
    extra = {k: v for k, v in app.filters.items() if k not in ("from", "to")}
    ActionMenu(
        bar,
        app,
        [("Período personalizado, matéria, categoria ou texto", app.filter_form)]
        + ([("Limpar todos os filtros", app.clear_filters)] if app.filters else []),
        text="Filtros" + (f" ({len(extra)})" if extra else ""),
        icon="list-filter",
    ).pack(side="right", padx=(0, 8))
    description = describe(app)
    if description:
        label(app.content, app, description, size=9, tone="muted").pack(
            anchor="w", pady=(4, 0)
        )


def describe(app):
    f = app.filters
    parts = []
    if f.get("from") or f.get("to"):
        parts.append(
            "de "
            + fmt(f.get("from"))
            + " a "
            + fmt(f.get("to") or app.today().isoformat())
            if f.get("from")
            else "até " + fmt(f["to"])
        )
    if f.get("subject_id"):
        row = app.store.one("SELECT name FROM subjects WHERE id=?", (f["subject_id"],))
        parts.append("matéria: " + (row["name"] if row else "removida"))
    if f.get("topic_id"):
        row = app.store.one("SELECT name FROM topics WHERE id=?", (f["topic_id"],))
        parts.append("assunto: " + (row["name"] if row else "removido"))
    if f.get("category"):
        parts.append("categoria: " + f["category"])
    if f.get("search"):
        parts.append(f"texto: “{f['search']}”")
    return ("Mostrando " + " · ".join(parts)) if parts else ""


def fmt(day):
    return f"{day[8:10]}/{day[5:7]}/{day[:4]}" if day else ""


def render(app):
    controls(app)
    s = app.store.stats(app.plan, app.filters)
    if not s["count"]:
        card = Card(app.content, app, padding=(24, 40))
        card.pack(fill="x", pady=(18, 0))
        anything = app.store.one(
            "SELECT COUNT(*) n FROM sessions WHERE plan_id=?", (app.plan,)
        )["n"]
        if anything:
            empty(
                card.body,
                app,
                "filter-x",
                "Nenhum registro neste período ou filtro",
                "Seus estudos continuam salvos; amplie o período ou limpe os filtros.",
                [
                    ("Limpar filtros", app.clear_filters),
                    ("Ver tudo", lambda: set_period(app, "all")),
                ],
            ).pack(fill="x")
        else:
            empty(
                card.body,
                app,
                "chart-column",
                "Suas estatísticas começam no primeiro estudo",
                "Registre um estudo com o relógio ou à mão. Tempo, questões e constância aparecem aqui.",
                [("Registrar estudo", app.session_form, "plus")],
            ).pack(fill="x")
        return
    summary(app, s)
    time_chart(app)
    middle = Columns(app.content, app, (1, 1), gap=18, breakpoint=900)
    middle.pack(fill="x", pady=(0, 26))
    by_subject(app, middle.cols[0])
    questions(app, middle.cols[1], s)
    evolution(app)
    attention(app)
    breakdown(app)


def summary(app, s):
    stats = [
        (
            compact_duration(s["elapsed"]),
            f"líquidas · {compact_duration(s['average'])} por dia estudado",
        ),
        (number(s["total"]), "questões feitas"),
    ]
    if s["rate"] is not None:
        stats.append(
            (
                percent(s["rate"], 1),
                "de acertos nas respondidas",
                "Acertos ÷ (acertos + erros).",
            )
        )
    stats.append(
        (
            f"{s['days']} de {s['period_days']}",
            "dias com estudo",
            "Constância: dias com tempo líquido positivo no período.",
        )
    )
    if s["pages"] is not None:
        stats.append(
            (
                number(s["pages"]),
                "páginas"
                + (
                    f" · {s['pages_hour']:.1f} por hora".replace(".", ",")
                    if s["pages_hour"]
                    else ""
                ),
            )
        )
    row = tk.Frame(app.content, bg=app.bg)
    row.pack(fill="x", pady=(18, 4))
    stat_row(row, app, stats).pack(side="left")
    help_button(row, app, "Como as estatísticas são calculadas", HELP).pack(
        side="right", anchor="n"
    )
    progress = app.store.progress(app.plan)
    details = [f"planejado: {compact_duration(s['target'])}"]
    if s["video"] is not None:
        details.append(f"videoaulas: {compact_duration(s['video'])}")
    details.append(
        f"edital: {number(progress['done'])} de {number(progress['total'])} assuntos concluídos (independe do filtro)"
    )
    label(
        app.content, app, " · ".join(details).capitalize(), size=9, tone="muted"
    ).pack(anchor="w", pady=(4, 26))


def group_control(app, parent):
    return Segmented(
        parent,
        app,
        GROUPS,
        app.group,
        lambda key: app.change_group(key),
        height=30,
    )


def time_chart(app):
    head = Section(app.content, app, "Tempo estudado")
    head.pack(fill="x", pady=(0, 8))
    group_control(app, head.actions).pack(side="right")
    card = Card(app.content, app, padding=(14, 6))
    card.pack(fill="x", pady=(0, 26))
    from charts import bars

    rows = app.store.grouped(app.plan, app.filters, app.group)
    bars(
        app,
        rows,
        "elapsed",
        parent=card.body,
        title={
            "day": "Horas líquidas por dia",
            "week": "Horas líquidas por semana",
            "month": "Horas líquidas por mês",
        }[app.group],
        empty=(
            "Nenhum tempo registrado neste filtro.",
            "Estudos com o relógio ou registrados à mão aparecem aqui.",
        ),
    )


def by_subject(app, parent):
    head = Section(parent, app, "Por matéria", size=12)
    head.pack(fill="x", pady=(0, 8))
    card = Card(parent, app, padding=(10, 6))
    card.pack(fill="x")
    from charts import distribution

    distribution(
        app,
        app.store.grouped(app.plan, app.filters, "subject"),
        parent=card.body,
        limit=8,
    )


def questions(app, parent, s):
    head = Section(parent, app, "Questões", size=12)
    head.pack(fill="x", pady=(0, 8))
    card = Card(parent, app, padding=(12, 6))
    card.pack(fill="x")
    from charts import question_summary

    question_summary(app, s, parent=card.body)


def evolution(app):
    head = Section(app.content, app, "Questões e aproveitamento ao longo do tempo")
    head.pack(fill="x", pady=(0, 8))
    group_control(app, head.actions).pack(side="right")
    card = Card(app.content, app, padding=(14, 6))
    card.pack(fill="x", pady=(0, 26))
    from charts import bars

    bars(
        app,
        app.store.grouped(app.plan, app.filters, app.group),
        "questions",
        True,
        parent=card.body,
        title="Questões feitas (barras) e acertos nas respondidas (linha)",
        empty=(
            "Nenhuma questão registrada neste filtro.",
            "Registre acertos e erros ao salvar um estudo.",
        ),
    )


def attention(app):
    rows = app.store.grouped(app.plan, app.filters, "subject")
    weak = sorted(
        (r for r in rows if r["correct"] + r["wrong"] >= 10),
        key=lambda r: ratio(r["correct"], r["wrong"]),
    )[:3]
    head = Section(app.content, app, "Onde concentrar a próxima revisão")
    head.pack(fill="x", pady=(0, 8))
    card = Card(app.content, app, padding=(14, 8))
    card.pack(fill="x", pady=(0, 26))
    if not weak:
        label(
            card.body,
            app,
            "Com pelo menos 10 respostas numa matéria, as de menor aproveitamento aparecem aqui.",
            size=10,
            tone="muted",
        ).pack(anchor="w", padx=10, pady=12)
        return
    for index, row in enumerate(weak):
        answered = row["correct"] + row["wrong"]
        item = Row(
            card.body,
            app,
            row["label"],
            f"{answered} respostas · {compact_duration(row['elapsed'])} estudados",
            on_open=lambda name=row["label"]: app.open_subject_name(name),
            separator=index < len(weak) - 1,
        )
        item.pack(fill="x")
        label(
            item.trail,
            app,
            percent(ratio(row["correct"], row["wrong"]), 1) + " de acertos",
            size=10,
            tone="warning",
        ).pack(side="right")
        item.refresh_bindings()


def breakdown(app):
    mode = app.store.pref("stats_breakdown", "subject")
    names = {"subject": "Matéria", "category": "Categoria", "topic": "Assunto"}
    if mode not in names:
        mode = "subject"
    head = Section(app.content, app, "Tabela detalhada")
    head.pack(fill="x", pady=(0, 8))
    Segmented(
        head.actions,
        app,
        list(names.items()),
        mode,
        lambda key: (app.store.set_pref("stats_breakdown", key), app.refresh()),
        height=30,
    ).pack(side="right")
    rows = app.store.grouped(app.plan, app.filters, mode)
    card = Card(app.content, app, padding=(6, 4))
    card.pack(fill="x")
    previous = app.content
    app.content = card.body
    try:
        app.table(
            [
                ("name", names[mode], 420),
                ("time", "Tempo líquido", 130),
                ("target", "Planejado", 130),
                ("total", "Questões", 100),
                ("rate", "Acertos (%)", 110),
            ],
            [
                (
                    uid(),
                    [
                        r["label"],
                        compact_duration(r["elapsed"]),
                        compact_duration(r["target"]),
                        r["correct"] + r["wrong"] + r["blank"],
                        percent(ratio(r["correct"], r["wrong"]), 1),
                    ],
                )
                for r in rows
            ],
            height=min(10, max(3, len(rows))),
        )
    finally:
        app.content = previous
    MotionButton(
        app.content,
        text="Abrir os registros deste filtro no Histórico",
        icon="history",
        style="Ghost.TButton",
        command=lambda: app.navigate("Histórico"),
    ).pack(anchor="w", pady=(10, 0))
