"""Metas e conquistas: active goals first, then this week's challenges, then badges.

Rules are unchanged: goals come from the ``goals`` table, challenges from
challenges.metrics (recomputed from records), achievements from the streak and
mock counts. Challenge points are separate from journey XP and say so.
"""

import tkinter as tk
from datetime import timedelta

from challenges import CATALOG, LEVELS, metrics
from theme import compact_duration, number
from ui import MotionButton, ProgressBar, Tooltip, glyph
from ui_kit import (
    ActionMenu,
    Card,
    Row,
    Section,
    Segmented,
    empty,
    help_button,
    icon_label,
    label,
    wrapping,
)

POINTS_HELP = (
    "Cada desafio concluído na semana vale 50 pontos de desafio. Esses pontos são "
    "locais, recalculados a partir dos seus registros, e não se confundem com o XP "
    "nem com as moedas da Jornada.\n\nCorrigir ou excluir um estudo atualiza o "
    "progresso. “Caderno vivo” é acumulado; os outros desafios recomeçam na segunda-feira. "
    "Não há ranking nem punição por interromper."
)


def render(app):
    goals(app)
    weekly_challenges(app)
    if app.store.pref("achievements", True):
        achievements(app)
    else:
        label(
            app.content,
            app,
            "Conquistas desativadas nas preferências. As metas continuam disponíveis.",
            size=9,
            tone="muted",
        ).pack(anchor="w", pady=(20, 0))


def principal(app):
    return app.store.pref("main_goal_" + app.plan, {}) or {}


def goals(app):
    start, end = app.week_bounds()
    rows = app.store.rows(
        "SELECT g.*,s.name subject FROM goals g LEFT JOIN subjects s ON s.id=g.subject_id WHERE g.plan_id=?",
        (app.plan,),
    )
    main = principal(app)
    head = Section(app.content, app, "Metas da semana")
    head.pack(fill="x", pady=(0, 4))
    if rows:
        head.action("Nova meta semanal", app.goal_form, icon="plus", style="TButton")
    label(
        app.content,
        app,
        f"{start:%d/%m} a {end:%d/%m}"
        + (f" · meta principal: {main['name']} ({main['target']})" if main else ""),
        size=9,
        tone="muted",
    ).pack(anchor="w", pady=(0, 10))
    card = Card(app.content, app, padding=(14, 8))
    card.pack(fill="x", pady=(0, 30))
    if not rows:
        empty(
            card.body,
            app,
            "target",
            "Defina quanto quer estudar por semana",
            "Uma meta de horas e questões para o plano ou para uma matéria. Não há dívida por perder um dia.",
            [("Nova meta semanal", app.goal_form, "plus")],
        ).pack(fill="x", pady=20)
        return
    overall = app.store.stats(
        app.plan, {"from": start.isoformat(), "to": end.isoformat()}
    )
    for index, goal in enumerate(rows):
        values = (
            app.store.stats(
                app.plan,
                {
                    "from": start.isoformat(),
                    "to": end.isoformat(),
                    "subject_id": goal["subject_id"],
                },
            )
            if goal["subject_id"]
            else overall
        )
        hours = values["elapsed"] / 3600
        row = Row(
            card.body,
            app,
            goal["subject"] or "Todo o plano",
            f"{compact_duration(values['elapsed'])} de {goal['hours']:g} h · "
            f"{number(values['total'])} de {goal['questions']} questões".replace(
                ".", ","
            ),
            separator=index < len(rows) - 1,
        )
        row.pack(fill="x")
        bars = tk.Frame(row.texts, bg=row.base)
        bars.pack(fill="x", pady=(8, 2))
        bars.columnconfigure(0, weight=1, uniform="goal")
        bars.columnconfigure(1, weight=1, uniform="goal")
        ProgressBar(
            bars,
            app,
            min(100, hours / goal["hours"] * 100) if goal["hours"] else 0,
            height=4,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ProgressBar(
            bars,
            app,
            (
                min(100, values["total"] / goal["questions"] * 100)
                if goal["questions"]
                else 0
            ),
            tone="secondary",
            height=4,
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        target = f"{goal['hours']:g} h e {goal['questions']} questões por semana"

        def make_main(target=target):
            app.store.set_pref(
                "main_goal_" + app.plan,
                {"name": "Minha meta semanal", "target": target},
            )
            app.refresh()

        ActionMenu(
            row.trail,
            app,
            [
                ("Tornar meta principal", make_main),
                ("Editar meta", lambda g=goal: app.goal_form(g)),
                None,
                ("Excluir meta", lambda g=goal: app.delete_goal(g["id"]), "danger"),
            ],
        ).pack(side="right", padx=(12, 0))
        if main.get("target") == target:
            label(row.trail, app, "principal", size=9, tone="accent").pack(side="right")
        row.refresh_bindings()


def weekly_challenges(app):
    pref = "challenge_level_" + app.plan
    level = app.store.pref(pref, "Iniciante")
    if level not in LEVELS:
        level = "Iniciante"
    index = list(LEVELS).index(level)
    values = metrics(app.store, app.plan, app.today())
    completed = sum(values[key] >= targets[index] for _, key, targets, *_ in CATALOG)
    head = Section(app.content, app, "Desafios da semana")
    head.pack(fill="x", pady=(0, 4))
    help_button(head, app, "Pontos de desafio", POINTS_HELP).pack(
        side="left", padx=(4, 0)
    )
    Segmented(
        head.actions,
        app,
        [(name, name) for name in LEVELS],
        level,
        lambda key: (app.store.set_pref(pref, key), app.refresh()),
        height=30,
    ).pack(side="right")
    hours, questions = LEVELS[level]
    line = tk.Frame(app.content, bg=app.bg)
    line.pack(fill="x", pady=(0, 10))
    label(
        line,
        app,
        f"{completed} de {len(CATALOG)} concluídos · {completed * 50} pontos de desafio",
        size=9,
        tone="muted",
    ).pack(side="left")

    def adopt():
        goal = app.store.one(
            "SELECT id FROM goals WHERE plan_id=? AND subject_id IS NULL LIMIT 1",
            (app.plan,),
        )
        app.store.save(
            "goals",
            dict(
                plan_id=app.plan,
                subject_id=None,
                hours=hours,
                questions=questions,
                **({"id": goal["id"]} if goal else {}),
            ),
        )
        app.refresh()

    adopt_button = MotionButton(
        line,
        text=f"Usar a meta do nível: {hours} h e {questions} questões",
        style="Ghost.TButton",
        height=28,
        command=adopt,
    )
    adopt_button.pack(side="right")
    Tooltip(adopt_button, "Cria ou atualiza a meta semanal de todo o plano.")
    card = Card(app.content, app, padding=(14, 8))
    card.pack(fill="x", pady=(0, 30))
    main = principal(app)
    for position, (name, key, targets, unit, rule, tip) in enumerate(CATALOG):
        target = targets[index]
        actual = values[key]
        done = actual >= target
        row = Row(
            card.body,
            app,
            name,
            rule + " " + tip,
            separator=position < len(CATALOG) - 1,
            pady=9,
        )
        row.pack(fill="x")
        icon_label(
            row.lead,
            app,
            "circle-check" if done else "circle",
            size=13,
            tone="success" if done else "faint",
        ).pack(padx=(0, 12), pady=(1, 0))
        ProgressBar(row.texts, app, min(100, actual / target * 100), height=3).pack(
            fill="x", pady=(6, 2)
        )
        is_main = main.get("key") == key and main.get("level") == level

        def choose(n=name, k=key, t=target, u=unit):
            single = {
                "sessões": "sessão",
                "dias": "dia",
                "assuntos": "assunto",
                "questões": "questão",
            }
            app.store.set_pref(
                "main_goal_" + app.plan,
                {
                    "name": n,
                    "key": k,
                    "target": f"{t} {single.get(u, u) if t == 1 else u}",
                    "level": level,
                },
            )
            app.refresh()

        if is_main:
            label(row.trail, app, "meta principal", size=9, tone="accent").pack(
                side="right", padx=(12, 0)
            )
        else:
            MotionButton(
                row.trail,
                text="Tornar principal",
                style="Ghost.TButton",
                height=28,
                command=choose,
            ).pack(side="right", padx=(12, 0))
        label(
            row.trail,
            app,
            f"{min(actual, target)} de {target} "
            + (
                {
                    "sessões": "sessão",
                    "dias": "dia",
                    "assuntos": "assunto",
                    "questões": "questão",
                    "revisões": "revisão",
                    "matérias": "matéria",
                    "minutos": "minuto",
                }.get(unit, unit)
                if target == 1
                else unit
            ),
            size=9,
            tone="success" if done else "muted",
        ).pack(side="right")
        row.refresh_bindings()


def achievements(app):
    current, best, days = app.store.streak(app.plan)
    eligible = app.store.pref("eligible_days", [0, 1, 2, 3, 4, 5, 6])
    start, _ = app.week_bounds()
    pool = set(days)
    week_days = [
        start + timedelta(days=i)
        for i in range(7)
        if (start + timedelta(days=i)).weekday() in eligible
    ]
    week_count = sum(d in pool for d in week_days)
    mocks = app.store.stats(app.plan, {"category": "Simulado"})["count"]
    items = [
        (
            "flame",
            "Primeiros 7 dias seguidos",
            min(best, 7),
            7,
            "Sete dias consecutivos com tempo líquido positivo (ou o mínimo configurado).",
        ),
        (
            "calendar",
            "Semana completa",
            week_count,
            max(1, len(week_days)),
            "Estudar em todos os dias elegíveis desta semana. Recalculada ao corrigir registros.",
        ),
        (
            "swords",
            "Mestre dos simulados",
            min(mocks, 10),
            10,
            "Dez simulados registrados no plano.",
        ),
    ]
    if app.store.pref("night_achievement", False):
        night = app.store.one(
            "SELECT COUNT(*) n FROM sessions WHERE plan_id=? AND elapsed>0 AND start_time>='22:00'",
            (app.plan,),
        )["n"]
        items.append(
            (
                "moon",
                "Corujão",
                min(night, 1),
                1,
                "Opcional: uma sessão iniciada após 22h. Não exige reduzir o sono.",
            )
        )
    head = Section(
        app.content,
        app,
        "Conquistas",
        count=f"{sum(v >= t for _, _, v, t, _ in items)} de {len(items)}",
    )
    head.pack(fill="x", pady=(0, 4))
    label(
        app.content,
        app,
        f"Sequência atual: {current} {'dia' if current == 1 else 'dias'}. Conquistas vêm dos seus registros; corrigir um estudo pode revogá-las.",
        size=9,
        tone="muted",
    ).pack(anchor="w", pady=(0, 10))
    grid = tk.Frame(app.content, bg=app.bg)
    grid.pack(fill="x")
    p = app.motion.palette
    for column, (icon, name, value, target, rule) in enumerate(items):
        grid.columnconfigure(column, weight=1, uniform="badge")
        done = value >= target
        card = Card(grid, app, padding=(18, 18), stretch=True)
        card.grid(
            row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0)
        )
        badge = tk.Canvas(
            card.body, width=46, height=46, bg=p["surface"], highlightthickness=0
        )
        badge.pack(anchor="w")
        badge.create_oval(
            1,
            1,
            45,
            45,
            fill=p["tint"] if done else p["raised"],
            outline=p["accent"] if done else p["border"],
            width=1.5,
        )
        badge.create_text(
            23,
            23,
            text=glyph(badge, icon),
            fill=p["accent"] if done else p["faint"],
            font=("lucide", 16),
        )
        label(card.body, app, name, size=10, weight="bold").pack(
            anchor="w", pady=(12, 2)
        )
        label(
            card.body,
            app,
            "Conquistada" if done else f"{value} de {target}",
            size=9,
            tone="accent" if done else "muted",
        ).pack(anchor="w")
        if not done:
            ProgressBar(card.body, app, value / target * 100, height=3).pack(
                fill="x", pady=(6, 0)
            )
        wrapping(label(card.body, app, rule, size=9, tone="faint"), minimum=100).pack(
            fill="x", pady=(10, 0)
        )
