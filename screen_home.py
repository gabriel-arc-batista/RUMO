"""Início: what to study next, first. Then the cycle, today, reviews and journey.

Reads view models from ``app.journey`` (journey.py contracts) and existing Store
queries. Never writes; actions open the existing flows.
"""

import tkinter as tk
from datetime import timedelta

from theme import compact_duration, number, percent, relative_day
from ui import Columns, MotionButton, ProgressBar, Tooltip, blend, glyph, rounded
from ui_kit import (
    Card,
    Row,
    Section,
    dot,
    empty,
    icon_label,
    label,
    stat_row,
    wrapping,
)

# Engine default when no real "where I stopped" note exists; not shown as if it were one.
GENERIC_STEP = "Abra o material e registre onde continuar."


def render(app):
    plan = app.plan
    mission = app.journey.mission(plan)
    top = Columns(app.content, app, (8, 5), gap=18, breakpoint=1000)
    top.pack(fill="x", pady=(0, 22))
    next_study(app, top.cols[0], mission)
    cycle_sequence(app, top.cols[1])
    today_line(app)
    middle = Columns(app.content, app, (1, 1), gap=18, breakpoint=900)
    middle.pack(fill="x", pady=(0, 22))
    reviews_list(app, middle.cols[0])
    if app.store.pref("rpg_show_character", True):
        journey_strip(app, middle.cols[1])
    else:
        goals_card(app, middle.cols[1])
    bottom = Columns(app.content, app, (3, 2), gap=18, breakpoint=900)
    bottom.pack(fill="x", pady=(0, 8))
    weekly_card(app, bottom.cols[0])
    constancy_card(app, bottom.cols[1])
    if app.store.pref("rpg_show_character", True):
        goals_card(app, bottom.cols[1], top_gap=18)
    quote(app)


def next_study(app, parent, mission):
    card = Card(
        app.content if parent is None else parent, app, padding=(28, 26), stretch=True
    )
    card.pack(fill="both", expand=True)
    body = card.body
    if mission is None:
        cycle = app.store.current_cycle(app.plan)
        if cycle:
            empty(
                body,
                app,
                "flag",
                "Decida o próximo passo do ciclo",
                "Os blocos desta volta atingiram o tempo previsto. Confira-os para continuar, concluir ou começar a próxima volta.",
                [("Abrir ciclo", lambda: app.navigate("Ciclo de estudos"), "repeat")],
            ).pack(fill="both", expand=True, pady=12)
        else:
            empty(
                body,
                app,
                "compass",
                "Monte seu ciclo para escolher o próximo estudo",
                "O ciclo guiado intercala suas matérias em blocos de 25 minutos e indica o próximo assunto pendente.",
                [
                    ("Criar ciclo guiado", app.guided_cycle, "sparkles"),
                    ("Montar do meu jeito", lambda: app.navigate("Ciclo de estudos")),
                ],
            ).pack(fill="both", expand=True, pady=12)
        return
    p = app.motion.palette
    wrapping(label(body, app, mission.subject, size=21, weight="bold")).pack(fill="x")
    wrapping(
        label(
            body,
            app,
            mission.topic or "Você escolhe o assunto ao começar.",
            size=12,
            tone="muted" if mission.topic else "faint",
        )
    ).pack(fill="x", pady=(4, 0))
    facts = tk.Frame(body, bg=p["surface"])
    facts.pack(fill="x", pady=(18, 0))
    items = [
        ("timer", f"{compact_duration(mission.suggested_seconds)} neste bloco"),
        ("book-marked", mission.category),
        (
            "history",
            (
                "último estudo " + relative_day(mission.last_studied, app.today())
                if mission.last_studied
                else "primeiro estudo desta matéria"
            ),
        ),
    ]
    for index, (icon, text) in enumerate(items):
        if glyph(facts, icon):
            icon_label(
                facts, app, icon, size=11, tone="accent" if index == 0 else "faint"
            ).pack(side="left", padx=(0 if index == 0 else 18, 6))
        label(facts, app, text, size=10, tone="muted").pack(side="left")
    step = (mission.next_step or "").strip()
    if step and step != GENERIC_STEP:
        resume = tk.Frame(body, bg=p["surface"])
        resume.pack(fill="x", pady=(16, 0))
        icon_label(resume, app, "flag", size=11, tone="accent").pack(
            side="left", anchor="n", padx=(0, 8), pady=(1, 0)
        )
        wrapping(label(resume, app, "Onde parei: " + step, size=10)).pack(
            side="left", fill="x", expand=True
        )
    if mission.block_target:
        done = round(mission.block_elapsed / 60)
        goal = max(1, round(mission.block_target / 60))
        progress = tk.Frame(body, bg=p["surface"])
        progress.pack(fill="x", pady=(18, 0))
        label(
            progress,
            app,
            f"{min(done, goal)} de {goal} min do bloco",
            size=9,
            tone="muted",
        ).pack(anchor="w")
        ProgressBar(
            progress, app, mission.block_elapsed / mission.block_target * 100, height=5
        ).pack(fill="x", pady=(6, 0))
    actions = tk.Frame(body, bg=p["surface"])
    actions.pack(fill="x", side="bottom", pady=(22, 0))
    start = MotionButton(
        actions,
        text=(
            "Bloco concluído"
            if mission.completed
            else ("Continuar estudo" if mission.block_elapsed else "Começar estudo")
        ),
        state="disabled" if mission.completed else "normal",
        icon="play",
        style="Accent.TButton",
        height=44,
        command=lambda: app.start_mission(mission),
    )
    start.pack(side="left")
    Tooltip(start, "Abre o relógio com matéria, assunto e tempo já preenchidos.")
    small = app.journey.reduced(mission)
    short = f"{small.minutes} min" + (
        f" e {small.questions} questões" if small.questions else ""
    )
    easy = MotionButton(
        actions,
        text=f"Hoje está difícil · {short}",
        state="disabled" if mission.completed else "normal",
        icon="leaf",
        style="Ghost.TButton",
        height=44,
        command=lambda: app.start_mission(mission, reduced=True),
    )
    easy.pack(side="left", padx=(10, 0))
    Tooltip(easy, "Uma versão curta. O restante do bloco continua guardado.")


def cycle_sequence(app, parent):
    card = Card(parent, app, padding=(22, 20), stretch=True)
    card.pack(fill="both", expand=True)
    body = card.body
    cycle = app.store.current_cycle(app.plan)
    head = Section(body, app, "Ciclo", size=12)
    head.pack(fill="x", pady=(0, 4))
    head.action("Abrir", lambda: app.navigate("Ciclo de estudos"), icon="chevron-right")
    if not cycle:
        wrapping(
            label(
                body,
                app,
                "Monte seu ciclo para escolher o próximo estudo. Ele aparece aqui como uma fila de matérias que se repete.",
                size=10,
                tone="muted",
            )
        ).pack(fill="x", pady=(6, 14))
        MotionButton(
            body, text="Criar ciclo guiado", icon="sparkles", command=app.guided_cycle
        ).pack(anchor="w")
        MotionButton(
            body,
            text="Montar do meu jeito",
            style="Ghost.TButton",
            command=lambda: app.navigate("Ciclo de estudos"),
        ).pack(anchor="w", pady=(6, 0))
        return
    blocks = app.store.cycle_blocks(cycle)
    label(
        body,
        app,
        f"Volta {cycle['lap']} · bloco {min(cycle['position'] + 1, len(blocks))} de {len(blocks)}",
        size=9,
        tone="muted",
    ).pack(anchor="w", pady=(0, 10))
    upcoming = blocks[cycle["position"] : cycle["position"] + 6]
    if not upcoming:
        label(
            body,
            app,
            "Volta concluída. Comece a próxima no Ciclo.",
            size=10,
            tone="muted",
        ).pack(anchor="w")
        return
    p = app.motion.palette
    for index, block in enumerate(upcoming):
        current = index == 0
        line = tk.Frame(body, bg=p["surface"])
        line.pack(fill="x", pady=(0, 9))
        marker = tk.Canvas(
            line, width=18, height=18, bg=p["surface"], highlightthickness=0
        )
        marker.pack(side="left", padx=(0, 10))
        if current:
            marker.create_oval(3, 3, 15, 15, fill=p["primary"], outline="")
        else:
            marker.create_oval(5, 5, 13, 13, fill="", outline=p["strong"], width=1.5)
        label(
            line,
            app,
            block["subject"],
            size=10,
            weight="bold" if current else "normal",
            tone="fg" if current else "muted",
        ).pack(side="left", fill="x", expand=True)
        remaining = max(0, block["target"] - block["elapsed"])
        label(
            line,
            app,
            compact_duration(remaining) if remaining else "feito",
            size=9,
            tone="accent" if current else "faint",
        ).pack(side="right")


def today_line(app):
    today = app.today()
    start, end = app.week_bounds()
    day = app.store.stats(
        app.plan, {"from": today.isoformat(), "to": today.isoformat()}
    )
    week = app.store.stats(app.plan, {"from": start.isoformat(), "to": end.isoformat()})
    progress = app.store.progress(app.plan)
    if not app.store.one(
        "SELECT COUNT(*) n FROM sessions WHERE plan_id=?", (app.plan,)
    )["n"]:
        paragraph = tk.Frame(app.content, bg=app.bg)
        paragraph.pack(fill="x", pady=(0, 24), padx=4)
        message = label(
            paragraph,
            app,
            "Nenhum estudo registrado ainda. Seu tempo, suas questões e seu aproveitamento aparecem aqui a partir do primeiro.",
            size=10,
            tone="muted",
            wraplength=640,
        )
        message.pack(fill="x")

        def fit_paragraph(event):
            width = max(1, event.width - 8)
            if int(float(message.cget("wraplength"))) != width:
                message.configure(wraplength=width)

        # A dedicated parent owns the callback and supplies the actual available
        # width, avoiding label geometry feedback and callbacks on stale pages.
        paragraph.bind("<Configure>", fit_paragraph)
        return
    stats = [
        (compact_duration(day["elapsed"]), "hoje"),
        (compact_duration(week["elapsed"]), "nesta semana"),
        (number(week["total"]), "questões na semana"),
    ]
    if week["correct"] + week["wrong"]:
        stats.append(
            (
                percent(week["rate"]),
                "de acertos na semana",
                "Acertos ÷ (acertos + erros). Questões em branco ficam de fora.",
            )
        )
    stats.append(
        (
            f"{number(progress['done'])}/{number(progress['total'])}",
            "assuntos do edital concluídos",
        )
    )
    row = stat_row(app.content, app, stats)
    row.pack(fill="x", pady=(0, 24), padx=4)


def reviews_list(app, parent):
    from screen_reviews import counts, fetch, start_review, state_of, when

    today = app.today().isoformat()
    number_of = counts(app, today)
    pending = number_of["overdue"] + number_of["today"]
    head = Section(parent, app, "Revisões de hoje", count=pending or None, size=12)
    head.pack(fill="x", pady=(0, 8))
    head.action("Ver todas", lambda: app.navigate("Revisões"), icon="chevron-right")
    card = Card(parent, app, padding=(12, 8))
    card.pack(fill="x")
    rows = [
        r
        for r in fetch(app, "Todas", today, limit=40)
        if r["state"] == "Pendente" and r["due"] <= today
    ][:4]
    if not rows:
        text = (
            f"Nada pendente hoje. {number_of['upcoming']} chegam nos próximos dias."
            if number_of["upcoming"]
            else "Nada pendente. As revisões aparecem aqui quando você registra estudos com intervalos."
        )
        wrapping(label(card.body, app, text, size=10, tone="muted")).pack(
            fill="x", padx=10, pady=14
        )
        return
    for index, review in enumerate(rows):
        state = state_of(review, today)
        row = Row(
            card.body,
            app,
            review["topic"],
            review["subject"],
            separator=index < len(rows) - 1,
            pady=8,
        )
        row.pack(fill="x")
        dot(row.lead, app, "error" if state == "Atrasada" else "accent").pack(
            pady=(5, 0), padx=(0, 12)
        )
        MotionButton(
            row.trail,
            text="Revisar",
            icon="play",
            height=30,
            command=lambda r=review: start_review(app, r),
        ).pack(side="right", padx=(10, 0))
        label(
            row.trail,
            app,
            when(review, today),
            size=9,
            tone="error" if state == "Atrasada" else "muted",
        ).pack(side="right")
        row.refresh_bindings()
    if pending > len(rows):
        label(
            card.body,
            app,
            f"e mais {pending - len(rows)} em Revisões",
            size=9,
            tone="faint",
        ).pack(anchor="w", padx=10, pady=(4, 6))


def next_unlock(equipment):
    locked = [item for item in equipment if not item.unlocked]
    rewards = [item for item in locked if item.acquisition == "reward"]
    return (rewards or locked or [None])[0]


def journey_strip(app, parent):
    from screen_journey import art

    hero = app.journey.character(app.plan)
    head = Section(parent, app, "Jornada", size=12)
    head.pack(fill="x", pady=(0, 8))
    head.action("Abrir", lambda: app.navigate("Jornada"), icon="chevron-right")
    card = Card(parent, app, padding=(22, 18))
    card.pack(fill="x")
    body = card.body
    p = app.motion.palette
    line = tk.Frame(body, bg=p["surface"])
    line.pack(fill="x")
    label(line, app, f"{hero.name} · nível {hero.level}", size=11, weight="bold").pack(
        side="left"
    )
    if hero.xp_next:
        label(
            line,
            app,
            f"faltam {number(hero.xp_next - hero.xp)} XP",
            size=9,
            tone="muted",
        ).pack(side="right")
    ProgressBar(
        body, app, hero.xp / hero.xp_next * 100 if hero.xp_next else 0, height=5
    ).pack(fill="x", pady=(8, 14))
    item = next_unlock(app.journey.equipment(app.plan))
    if item:
        unlock = tk.Frame(body, bg=p["surface"])
        unlock.pack(fill="x")
        art(app, unlock, item, 44).pack(side="left", padx=(0, 12))
        texts = tk.Frame(unlock, bg=p["surface"])
        texts.pack(side="left", fill="x", expand=True)
        label(texts, app, "Próximo item: " + item.name, size=10).pack(anchor="w")
        wrapping(label(texts, app, item.unlock_hint, size=9, tone="muted")).pack(
            fill="x", pady=(2, 0)
        )
    stats = tk.Frame(body, bg=p["surface"])
    stats.pack(fill="x", pady=(14, 0))
    for icon, text, tone in [
        (
            "flame",
            f"{hero.streak_days} {'dia' if hero.streak_days == 1 else 'dias'} seguidos",
            "warning",
        ),
        ("coins", f"{number(hero.coins or 0)} moedas", "accent"),
    ]:
        icon_label(stats, app, icon, size=11, tone=tone).pack(side="left", padx=(0, 6))
        label(stats, app, text, size=9, tone="muted").pack(side="left", padx=(0, 18))


def weekly_card(app, parent):
    start, end = app.week_bounds()
    head = Section(parent, app, "Estudo da semana", size=12)
    head.pack(fill="x", pady=(0, 8))
    for icon, step, tip in [
        ("chevron-right", 1, "Próxima semana"),
        ("chevron-left", -1, "Semana anterior"),
    ]:
        button = head.action("", lambda n=step: app.move_week(n), icon=icon, height=30)
        Tooltip(button, tip)
    label(head.actions, app, f"{start:%d/%m} a {end:%d/%m}", size=9, tone="muted").pack(
        side="right", padx=8
    )
    from ui_kit import Segmented

    Segmented(
        head.actions,
        app,
        [("Tempo", "Horas"), ("Questões", "Questões")],
        app.chart_mode,
        lambda key: app.toggle_chart(),
        height=30,
    ).pack(side="right", padx=(0, 6))
    card = Card(parent, app, padding=(14, 6))
    card.pack(fill="x")
    rows = app.store.grouped(
        app.plan, {"from": start.isoformat(), "to": end.isoformat()}
    )
    data = {r["label"]: r for r in rows}
    days = []
    for i in range(7):
        key = (start + timedelta(days=i)).isoformat()
        days.append(
            data.get(
                key, dict(label=key, elapsed=0, target=0, correct=0, wrong=0, blank=0)
            )
        )
    from charts import bars

    bars(
        app,
        days,
        "elapsed" if app.chart_mode == "Tempo" else "questions",
        performance=app.chart_mode != "Tempo",
        parent=card.body,
        title=(
            "Horas líquidas por dia"
            if app.chart_mode == "Tempo"
            else "Questões por dia"
        ),
        empty=("Nenhum estudo nesta semana.", "Os dias com estudo aparecem aqui."),
        height=250,
    )


def constancy_card(app, parent):
    p = app.motion.palette
    current, best, days = app.store.streak(app.plan)
    head = Section(parent, app, "Constância", size=12)
    head.pack(fill="x", pady=(0, 8))
    for icon, step, tip in [
        ("chevron-right", 28, "Próximas 4 semanas"),
        ("chevron-left", -28, "4 semanas anteriores"),
    ]:
        Tooltip(
            head.action("", lambda n=step: app.move_streak(n), icon=icon, height=30),
            tip,
        )
    card = Card(parent, app, padding=(20, 16))
    card.pack(fill="x")
    body = card.body
    finish = app.today() + timedelta(days=app.streak_offset)
    begin = finish - timedelta(days=27)
    label(
        body,
        app,
        f"{current} {'dia' if current == 1 else 'dias'} seguidos · recorde de {best}",
        size=10,
    ).pack(anchor="w")
    label(body, app, f"{begin:%d/%m} a {finish:%d/%m}", size=9, tone="muted").pack(
        anchor="w", pady=(2, 10)
    )
    strip = tk.Canvas(body, height=58, bg=p["surface"], highlightthickness=0)
    strip.pack(fill="x")
    pool = set(days)
    today = app.today()

    def draw(event=None):
        strip.delete("all")
        width = strip.winfo_width()
        cell = max(8, (width + 4) / 14)
        for i in range(28):
            day = begin + timedelta(days=i)
            row, column = divmod(i, 14)
            x = column * cell
            y = row * 28
            studied = day in pool
            item = rounded(
                strip,
                x,
                y + 2,
                cell - 4,
                22,
                5,
                fill=blend(p["track"], p["primary"], 0.7) if studied else p["track"],
                outline=p["accent"] if day == today else "",
                width=1.5,
            )
            strip.tag_bind(
                item,
                "<Button-1>",
                lambda e, d=day: (
                    app.filters.update({"from": d.isoformat(), "to": d.isoformat()}),
                    app.navigate("Histórico"),
                ),
            )

    strip.bind("<Configure>", draw)
    Tooltip(
        strip,
        "Cada quadrado é um dia (duas semanas por linha). Preenchido: estudou. "
        "Contorno: hoje. Clique para ver os registros do dia. Faltar um dia não tira nada.",
    )


def goals_card(app, parent, top_gap=0):
    start, end = app.week_bounds()
    goals = app.store.rows(
        "SELECT g.*,s.name subject FROM goals g LEFT JOIN subjects s ON s.id=g.subject_id WHERE g.plan_id=?",
        (app.plan,),
    )
    head = Section(parent, app, "Metas da semana", size=12)
    head.pack(fill="x", pady=(top_gap, 8))
    head.action(
        "Metas", lambda: app.navigate("Metas e conquistas"), icon="chevron-right"
    )
    card = Card(parent, app, padding=(20, 16))
    card.pack(fill="x")
    body = card.body
    if not goals:
        wrapping(
            label(
                body,
                app,
                "Sem meta semanal. Defina horas e questões em Metas; não há dívida por perder um dia.",
                size=9,
                tone="muted",
            )
        ).pack(fill="x")
        return
    for goal in goals[:2]:
        values = app.store.stats(
            app.plan,
            dict(
                {"from": start.isoformat(), "to": end.isoformat()},
                **({"subject_id": goal["subject_id"]} if goal["subject_id"] else {}),
            ),
        )
        for name, value, target, text in [
            (
                "Horas",
                values["elapsed"] / 3600,
                goal["hours"],
                compact_duration(values["elapsed"]),
            ),
            ("Questões", values["total"], goal["questions"], number(values["total"])),
        ]:
            if not target:
                continue
            line = tk.Frame(body, bg=app.motion.palette["surface"])
            line.pack(fill="x", pady=(0, 4))
            label(
                line, app, f"{goal['subject'] or 'Plano'} · {name.lower()}", size=9
            ).pack(side="left")
            label(
                line,
                app,
                f"{text} de {target:g}".replace(".", ","),
                size=9,
                tone="muted",
            ).pack(side="right")
            ProgressBar(body, app, min(100, value / target * 100), height=4).pack(
                fill="x", pady=(0, 10)
            )


def quote(app):
    if not app.store.pref("motivation", True):
        return
    from inspiration import inline
    from app import ASSETS

    holder = tk.Frame(app.content, bg=app.bg)
    holder.pack(fill="x", pady=(18, 0), padx=4)
    app.quote_header = inline(app, holder, ASSETS / "quotes.json")
