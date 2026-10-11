"""Início: the recommended mission first, then character, cycle, reviews and trends.

Reads view models from ``app.journey`` (journey.py contracts) and existing Store
queries. Never writes; actions open the existing flows.
"""

import tkinter as tk
from datetime import timedelta
from tkinter import ttk

from core import duration
from theme import ICON, DISPLAY, compact_duration, number, percent, relative_day
from ui import (
    Chip,
    Columns,
    EmptyState,
    MotionButton,
    Panel,
    Portrait,
    ProgressBar,
    Ring,
    SectionHeader,
    Tooltip,
    blend,
    demo_chip,
    glyph,
    load_image,
    rounded,
)


def render(app):
    plan = app.plan
    top = Columns(
        app.content,
        app,
        (13, 7) if app.store.pref("rpg_show_character", True) else (1,),
        gap=16,
        breakpoint=1000,
    )
    top.pack(fill="x", pady=(0, 16))
    mission_card(app, top.cols[0], app.journey.mission(plan))
    if app.store.pref("rpg_show_character", True):
        character_card(app, top.cols[1], app.journey.character(plan))
    indicators(app)
    middle = Columns(app.content, app, (1, 1), gap=16, breakpoint=900)
    middle.pack(fill="x", pady=(0, 16))
    cycle_panel(app, middle.cols[0])
    reviews_panel(app, middle.cols[1], app.journey.reviews(plan))
    streak_panel(app, middle.cols[1])
    bottom = Columns(app.content, app, (1, 1), gap=16, breakpoint=900)
    bottom.pack(fill="x", pady=(0, 8))
    weekly_panel(app, bottom.cols[0])
    subjects_panel(app, bottom.cols[1], app.journey.skills(plan))


def meta_item(parent, icon, text, color=None, tip=None):
    p = parent.winfo_toplevel()._root()._motion.palette
    row = ttk.Frame(parent, style="Panel.TFrame")
    if glyph(row, icon):
        ttk.Label(
            row,
            text=glyph(row, icon),
            font=(ICON, 11),
            foreground=color or p["faint"],
            style="Panel.TLabel",
        ).pack(side="left", padx=(0, 6))
    label = ttk.Label(row, text=text, style="PanelMuted.TLabel")
    label.pack(side="left")
    if tip:
        Tooltip(row, tip)
    return row


def wrap(label, margin=8):
    """Keep wraplength equal to the label's real width (no clipped text)."""

    def fit(event):
        width = max(120, event.width - margin)
        if int(float(label.cget("wraplength") or 0)) != width:
            label.configure(wraplength=width)

    label.bind("<Configure>", fit)
    return label


def mission_card(app, parent, mission):
    p = app.motion.palette
    panel = Panel(parent, app, padding=(24, 22), tone="hero", stretch=True)
    panel.pack(fill="both", expand=True)
    body = panel.body
    if mission is None:
        cycle = app.store.current_cycle(app.plan)
        if cycle:
            EmptyState(
                body,
                app,
                "flag",
                "Confira o próximo passo do ciclo",
                "O tempo pode ter sido atingido. Confira os blocos e decida continuar, concluir ou iniciar a próxima volta.",
                [("Abrir ciclo", lambda: app.navigate("Ciclo de estudos"), "repeat")],
            ).pack(fill="x", pady=12)
        else:
            EmptyState(
                body,
                app,
                "compass",
                "Monte um ciclo para receber sua missão",
                "O ciclo guiado intercala suas matérias em blocos curtos e indica o próximo assunto.",
                [
                    ("Criar ciclo guiado", app.guided_cycle, "sparkles"),
                    ("Ver opções", lambda: app.navigate("Ciclo de estudos")),
                ],
            ).pack(fill="x", pady=12)
        return
    head = ttk.Frame(body, style="Panel.TFrame")
    head.pack(fill="x")
    Chip(head, "MISSÃO PARA COMEÇAR", tone="accent", icon="compass").pack(side="left")
    if mission.position is not None:
        Chip(
            head,
            f"Bloco {mission.position + 1} de {mission.block_count} • volta {mission.lap}",
            tip="Posição na fila do ciclo. A fila continua de onde você parou.",
        ).pack(side="right")
    else:
        Chip(head, "FORA DO CICLO", tip="Missão que não ocupa um bloco do ciclo.").pack(
            side="right"
        )
    main = ttk.Frame(body, style="Panel.TFrame")
    main.pack(fill="x", pady=(16, 0))
    main.columnconfigure(0, weight=1)
    texts = ttk.Frame(main, style="Panel.TFrame")
    texts.grid(row=0, column=0, sticky="nsew")
    wrap(
        ttk.Label(
            texts, text=mission.subject, style="PanelTitle.TLabel", justify="left"
        )
    ).pack(fill="x")
    wrap(
        ttk.Label(
            texts,
            text=mission.topic or "Escolha o assunto ao iniciar.",
            style="PanelMuted.TLabel",
            font=(app.font_family, 11),
            justify="left",
        )
    ).pack(fill="x", pady=(4, 0))
    minutes = max(1, round(mission.block_target / 60))
    done = min(minutes, round(mission.block_elapsed / 60))
    Ring(
        main,
        app,
        (
            mission.block_elapsed / mission.block_target * 100
            if mission.block_target
            else 0
        ),
        size=96,
        center=f"{done}/{minutes}",
        caption="min do bloco",
    ).grid(row=0, column=1, sticky="ne", padx=(16, 0))
    meta = ttk.Frame(body, style="Panel.TFrame")
    meta.pack(fill="x", pady=(14, 0))
    meta_item(
        meta,
        "timer",
        f"{compact_duration(mission.suggested_seconds)} sugeridos",
        p["accent"],
        "Tempo que falta neste bloco do ciclo.",
    ).pack(side="left", padx=(0, 18))
    meta_item(meta, "book-marked", mission.category).pack(side="left", padx=(0, 18))
    meta_item(
        meta,
        "history",
        (
            "Último estudo " + relative_day(mission.last_studied, app.today())
            if mission.last_studied
            else "Primeiro estudo desta matéria"
        ),
    ).pack(side="left")
    note = tk.Frame(body, bg=p["raised"], highlightthickness=0)
    note.pack(fill="x", pady=(14, 0))
    if glyph(note, "flag"):
        tk.Label(
            note,
            text=glyph(note, "flag"),
            bg=p["raised"],
            fg=p["accent"] if mission.next_step else p["faint"],
            font=(ICON, 11),
        ).pack(side="left", anchor="n", padx=(12, 8), pady=10)
    step = tk.Label(
        note,
        text=(
            "Onde parei: " + mission.next_step
            if mission.next_step
            else "Sem anotação de onde parou. Ao finalizar, registre o próximo passo."
        ),
        bg=p["raised"],
        fg=p["fg"] if mission.next_step else p["muted"],
        font=(app.font_family, 10),
        justify="left",
        anchor="w",
    )
    step.pack(side="left", fill="x", expand=True, pady=10, padx=(0, 12))
    wrap(step, 4)
    actions = ttk.Frame(body, style="Panel.TFrame")
    actions.pack(fill="x", pady=(16, 0))
    start = MotionButton(
        actions,
        text=(
            "Missão cumprida"
            if mission.completed
            else ("Continuar missão" if mission.block_elapsed else "Começar missão")
        ),
        state="disabled" if mission.completed else "normal",
        icon="play",
        style="Accent.TButton",
        height=42,
        command=lambda: app.start_mission(mission),
    )
    start.pack(side="left")
    Tooltip(start, "Abre o relógio com matéria, assunto e tempo já preenchidos.")
    small = app.journey.reduced(mission)
    easy = MotionButton(
        actions,
        text="Hoje está difícil",
        state="disabled" if mission.completed else "normal",
        icon="leaf",
        height=42,
        command=lambda: app.start_mission(mission, reduced=True),
    )
    easy.pack(side="left", padx=(10, 0))
    short = f"{small.minutes} min" + (
        f" • {small.questions} questões" if small.questions else ""
    )
    Tooltip(
        easy,
        f"Versão curta: {short}. O restante do bloco continua guardado.",
    )
    ttk.Label(
        actions,
        text=short,
        style="PanelMuted.TLabel",
        font=(app.font_family, 9),
    ).pack(side="left", padx=(10, 0))


def character_card(app, parent, hero):
    p = app.motion.palette
    panel = Panel(parent, app, padding=(22, 20), stretch=True)
    panel.pack(fill="both", expand=True)
    body = panel.body
    top = ttk.Frame(body, style="Panel.TFrame")
    top.pack(fill="x")
    portrait = Portrait(top, app, 88)
    portrait.pack(side="left", padx=(0, 14))
    portrait.configure(cursor="hand2")
    portrait.bind("<Button-1>", lambda e: app.customize_character())
    Tooltip(portrait, "Personalizar aparência")
    names = ttk.Frame(top, style="Panel.TFrame")
    names.pack(side="left", fill="x", expand=True)
    if hero.source == "demo":
        demo_chip(
            names,
            "Nível, experiência, moedas e título são fictícios nesta prévia. "
            "A sequência de dias vem dos seus registros.",
        ).pack(anchor="w", pady=(2, 6))
    ttk.Label(names, text=hero.name, style="PanelDisplay.TLabel").pack(anchor="w")
    ttk.Label(names, text=hero.title, style="PanelMuted.TLabel").pack(anchor="w")
    level = ttk.Frame(body, style="Panel.TFrame")
    level.pack(fill="x", pady=(18, 6))
    ttk.Label(level, text=f"Nível {hero.level}", style="PanelHeading.TLabel").pack(
        side="left"
    )
    ttk.Label(
        level, text=f"{hero.xp} / {hero.xp_next} XP", style="PanelMuted.TLabel"
    ).pack(side="right")
    ProgressBar(
        body, app, hero.xp / hero.xp_next * 100 if hero.xp_next else 0, height=8
    ).pack(fill="x")
    stats = ttk.Frame(body, style="Panel.TFrame")
    stats.pack(fill="x", pady=(14, 0))
    meta_item(
        stats,
        "flame",
        f"{hero.streak_days} {'dia' if hero.streak_days == 1 else 'dias'} seguidos",
        p["warning"],
        "Dias consecutivos com estudo registrado. Faltar um dia não tira nada.",
    ).pack(side="left", padx=(0, 16))
    meta_item(stats, "coins", f"{hero.coins} moedas", p["accent"]).pack(side="left")
    MotionButton(
        body,
        text="Abrir jornada",
        icon="map",
        height=42,
        command=lambda: app.navigate("Jornada"),
    ).pack(side="bottom", anchor="w", pady=(16, 0))


def indicators(app):
    s = app.store.stats(app.plan)
    progress = app.store.progress(app.plan)
    edital = (
        percent(progress["done"] * 100 / progress["total"])
        if progress["total"]
        else "—"
    )
    app.cards(
        [
            (
                "TEMPO LÍQUIDO",
                compact_duration(s["elapsed"]),
                f"{s['days']} {'dia' if s['days'] == 1 else 'dias'} com estudo",
                "timer",
            ),
            (
                "DESEMPENHO",
                percent(s["rate"], 1),
                f"{number(s['correct'])} acertos • {number(s['wrong'])} erros",
                "target",
            ),
            (
                "EDITAL",
                edital,
                f"{number(progress['done'])} de {number(progress['total'])} assuntos",
                "book-open",
            ),
            (
                "QUESTÕES",
                number(s["total"]),
                f"{number(s['blank'])} em branco",
                "list-checks",
            ),
        ]
    )


def cycle_panel(app, parent):
    p = app.motion.palette
    panel = Panel(parent, app, stretch=True)
    panel.pack(fill="both", expand=True)
    body = panel.body
    SectionHeader(
        body,
        app,
        "Ciclo atual",
        icon="repeat",
        action=("Abrir ciclo", lambda: app.navigate("Ciclo de estudos")),
    ).pack(fill="x")
    cycle = app.store.current_cycle(app.plan)
    if not cycle:
        EmptyState(
            body,
            app,
            "repeat",
            "Nenhum ciclo ativo",
            "Organize suas matérias em uma fila flexível.",
            [("Criar ciclo guiado", app.guided_cycle, "sparkles")],
        ).pack(fill="x", pady=8)
        return
    blocks = app.store.cycle_blocks(cycle)
    decided = sum(bool(b["state"]) for b in blocks)
    ttk.Label(
        body,
        text=f"{cycle['name']} • volta {cycle['lap']} • {decided} de {len(blocks)} blocos decididos",
        style="PanelMuted.TLabel",
    ).pack(anchor="w", pady=(4, 10))
    upcoming = blocks[cycle["position"] : cycle["position"] + 5]
    if not upcoming:
        ttk.Label(
            body,
            text="Volta concluída. Inicie a próxima no Ciclo de estudos.",
            style="PanelMuted.TLabel",
        ).pack(anchor="w")
        return
    for index, block in enumerate(upcoming):
        current = index == 0
        row = ttk.Frame(body, style="Panel.TFrame")
        row.pack(fill="x", pady=(0, 10))
        badge = tk.Canvas(
            row, width=26, height=26, bg=p["surface"], highlightthickness=0
        )
        badge.pack(side="left", padx=(0, 12), anchor="n")
        badge.create_oval(
            1,
            1,
            25,
            25,
            fill=p["tint"] if current else p["raised"],
            outline=p["accent"] if current else p["border"],
        )
        badge.create_text(
            13,
            13,
            text=str(cycle["position"] + index + 1),
            fill=p["accent"] if current else p["muted"],
            font=(app.font_family, 8, "bold"),
        )
        texts = ttk.Frame(row, style="Panel.TFrame")
        texts.pack(side="left", fill="x", expand=True)
        line = ttk.Frame(texts, style="Panel.TFrame")
        line.pack(fill="x")
        ttk.Label(line, text=block["subject"], style="Panel.TLabel").pack(side="left")
        if current:
            Chip(line, "AGORA", tone="accent").pack(side="left", padx=(8, 0))
        remaining = max(0, block["target"] - block["elapsed"])
        ttk.Label(
            line,
            text=(
                f"faltam {compact_duration(remaining)}"
                if remaining
                else "alvo atingido"
            ),
            style="PanelMuted.TLabel",
            font=(app.font_family, 9),
        ).pack(side="right")
        ProgressBar(
            texts,
            app,
            block["elapsed"] / block["target"] * 100 if block["target"] else 0,
            height=4,
        ).pack(fill="x", pady=(6, 0))


def reviews_panel(app, parent, summary):
    p = app.motion.palette
    panel = Panel(parent, app)
    panel.pack(fill="x", pady=(0, 16))
    body = panel.body
    SectionHeader(
        body,
        app,
        "Revisões",
        icon="brain",
        action=("Abrir revisões", lambda: app.navigate("Revisões")),
    ).pack(fill="x")
    tiles = ttk.Frame(body, style="Panel.TFrame")
    tiles.pack(fill="x", pady=(10, 8))
    for column, (value, label, icon, tone) in enumerate(
        [
            (summary.overdue, "atrasadas", "triangle-alert", "error"),
            (summary.today, "para hoje", "calendar", "accent"),
            (summary.upcoming, "próximos 7 dias", "hourglass", "info"),
        ]
    ):
        tiles.columnconfigure(column, weight=1, uniform="tile")
        active = value > 0
        background = p[tone + "_bg"] if active and tone != "accent" else p["raised"]
        if active and tone == "accent":
            background = p["tint"]
        tile = tk.Frame(tiles, bg=background)
        tile.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=(0 if column == 0 else 5, 0 if column == 2 else 5),
        )
        color = p[tone] if active else p["faint"]
        top = tk.Frame(tile, bg=background)
        top.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(
            top,
            text=number(value),
            bg=background,
            fg=p["fg"] if active else p["muted"],
            font=(app.font_family, 17, "bold"),
        ).pack(side="left")
        if glyph(top, icon):
            tk.Label(
                top, text=glyph(top, icon), bg=background, fg=color, font=(ICON, 12)
            ).pack(side="right")
        tk.Label(
            tile,
            text=label,
            bg=background,
            fg=p["muted"],
            font=(app.font_family, 9),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 10))
    hint = ttk.Label(
        body,
        text=(
            "Tente lembrar antes de abrir o material; depois confira."
            if summary.overdue or summary.today
            else "Nada pendente para hoje. As próximas aparecem aqui."
        ),
        style="PanelMuted.TLabel",
        font=(app.font_family, 9),
    )
    hint.pack(anchor="w")


def streak_panel(app, parent):
    p = app.motion.palette
    panel = Panel(parent, app)
    panel.pack(fill="x")
    body = panel.body
    current, best, days = app.store.streak(app.plan)
    head = SectionHeader(body, app, "Constância", icon="flame")
    head.pack(fill="x")
    for icon, step, tip in [
        ("chevron-right", 28, "Próximas 4 semanas"),
        ("chevron-left", -28, "4 semanas anteriores"),
    ]:
        button = MotionButton(
            head,
            icon=icon,
            style="Ghost.TButton",
            height=30,
            command=lambda n=step: app.move_streak(n),
        )
        button.pack(side="right")
        Tooltip(button, tip)
    finish = app.today() + timedelta(days=app.streak_offset)
    begin = finish - timedelta(days=27)
    ttk.Label(
        body,
        text=f"{current} {'dia' if current == 1 else 'dias'} seguidos • recorde {best} • {begin:%d/%m} a {finish:%d/%m}",
        style="PanelMuted.TLabel",
    ).pack(anchor="w", pady=(4, 10))
    strip = tk.Canvas(body, height=40, bg=app.surface, highlightthickness=0)
    strip.pack(fill="x")
    pool = set(days)
    today = app.today()

    def draw(event=None):
        strip.delete("all")
        width = strip.winfo_width()
        cell = max(8, (width + 4) / 28)
        for i in range(28):
            day = begin + timedelta(days=i)
            x = i * cell
            studied = day in pool
            item = rounded(
                strip,
                x,
                2,
                cell - 4,
                20,
                4,
                fill=blend(p["track"], p["primary"], 0.6) if studied else p["track"],
                outline=p["accent"] if day == today else "",
                width=1.5,
            )
            if cell >= 18 or i % 2 == 0:
                strip.create_text(
                    x + (cell - 4) / 2,
                    33,
                    text=day.day,
                    fill=p["accent"] if day == today else p["faint"],
                    font=(app.font_family, 7),
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
        "Preenchido: dia com estudo registrado. Contorno: hoje. Clique para ver os registros do dia.",
    )


def weekly_panel(app, parent):
    panel = Panel(parent, app, stretch=True)
    panel.pack(fill="both", expand=True)
    body = panel.body
    start, end = app.week_bounds()
    head = SectionHeader(body, app, "Estudo semanal", icon="chart-column")
    head.pack(fill="x")
    controls = ttk.Frame(body, style="Panel.TFrame")
    controls.pack(fill="x", pady=(8, 0))
    for label, mode in [("Tempo", "Tempo"), ("Questões", "Questões")]:
        MotionButton(
            controls,
            text=label,
            style="Chip.TButton",
            selected=app.chart_mode == mode,
            command=lambda m=mode: (
                None if app.chart_mode == m else app.toggle_chart()
            ),
        ).pack(side="left", padx=(0, 6))
    for icon, step in [("chevron-right", 1), ("chevron-left", -1)]:
        MotionButton(
            controls,
            icon=icon,
            style="Ghost.TButton",
            height=30,
            command=lambda n=step: app.move_week(n),
        ).pack(side="right")
    ttk.Label(
        controls,
        text=f"{start:%d/%m} a {end:%d/%m}",
        style="PanelMuted.TLabel",
        font=(app.font_family, 9),
    ).pack(side="right", padx=8)
    with app.in_panel(panel):
        app.week_chart(controls=False)
        app.goal_bars()


def subjects_panel(app, parent, skills):
    p = app.motion.palette
    panel = Panel(parent, app, stretch=True)
    panel.pack(fill="both", expand=True)
    body = panel.body
    SectionHeader(
        body,
        app,
        "Suas matérias",
        icon="book-open",
        action=("Ver habilidades", lambda: app.navigate("Jornada")),
    ).pack(fill="x")
    ttk.Label(
        body,
        text="Esforço é o tempo registrado. Desempenho vem das questões respondidas.",
        style="PanelMuted.TLabel",
        font=(app.font_family, 9),
    ).pack(anchor="w", pady=(4, 12))
    shown = sorted(skills, key=lambda s: (-s.effort_seconds, s.name))[:5]
    if not any(s.effort_seconds or s.answered for s in shown):
        EmptyState(
            body,
            app,
            "sprout",
            "Suas matérias aparecem aqui",
            "Registre o primeiro estudo para acompanhar esforço e desempenho.",
            [("Iniciar foco", app.open_clock, "timer")],
        ).pack(fill="x")
        return
    most = max(s.effort_seconds for s in shown) or 1
    for skill in shown:
        row = ttk.Frame(body, style="Panel.TFrame", cursor="hand2")
        row.pack(fill="x", pady=(0, 12))
        line = ttk.Frame(row, style="Panel.TFrame")
        line.pack(fill="x")
        name = ttk.Label(line, text=skill.name, style="Panel.TLabel")
        name.pack(side="left")
        ttk.Label(
            line,
            text=compact_duration(skill.effort_seconds),
            style="PanelMuted.TLabel",
            font=(app.font_family, 9),
        ).pack(side="right")
        bars = ttk.Frame(row, style="Panel.TFrame")
        bars.pack(fill="x", pady=(6, 0))
        bars.columnconfigure(0, weight=1, uniform="bar")
        bars.columnconfigure(1, weight=1, uniform="bar")
        ProgressBar(bars, app, skill.effort_seconds / most * 100, height=4).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ProgressBar(bars, app, skill.accuracy or 0, tone="info", height=4).grid(
            row=0, column=1, sticky="ew", padx=(8, 0)
        )
        ttk.Label(
            bars,
            text="esforço",
            style="PanelMuted.TLabel",
            font=(app.font_family, 8),
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))
        performance = (
            f"{percent(skill.accuracy)} em {number(skill.answered)} questões"
            if skill.sample_ok
            else (
                f"Dados insuficientes ({skill.answered} respostas)"
                if skill.answered
                else "Dados insuficientes"
            )
        )
        ttk.Label(
            bars,
            text="desempenho • " + performance,
            style="PanelMuted.TLabel",
            font=(app.font_family, 8),
        ).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(3, 0))
        for widget in (row, line, name):
            widget.bind(
                "<Button-1>", lambda e, sid=skill.subject_id: app.subject_detail(sid)
            )
