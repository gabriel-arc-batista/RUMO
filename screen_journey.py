"""Jornada: character, subject skills, decorative equipment, achievements, story.

All RPG values come from ``app.journey`` (journey.py contracts). In the preview,
values marked ``demo`` are fictitious and labelled; effort and performance per
subject are read from real records.
"""

import tkinter as tk
from tkinter import ttk

from theme import ICON, compact_duration, number, percent
from ui import (
    Chip,
    CharacterView,
    Columns,
    EmptyState,
    MotionButton,
    Panel,
    ProgressBar,
    SectionHeader,
    Tooltip,
    blend,
    hover_card,
    demo_chip,
    glyph,
)

DEMO_NOTE = (
    "Prévia visual. Nível, experiência, moedas, equipamentos, conquistas, capítulos "
    "e desafios são fictícios e não são salvos. Esforço e desempenho por matéria vêm "
    "dos seus registros."
)


def render(app):
    plan = app.plan
    hero = app.journey.character(plan)
    if hero.source == "demo":
        banner(app)
    top = Columns(
        app.content,
        app,
        (1, 1) if app.store.pref("rpg_show_character", True) else (1,),
        gap=16,
        breakpoint=980,
    )
    top.pack(fill="x", pady=(0, 16))
    if app.store.pref("rpg_show_character", True):
        stage(app, top.cols[0], hero)
    profile(app, top.cols[-1], hero, app.journey.equipment(plan))
    equipment_panel(app, app.journey.equipment(plan))
    if hero.source == "real":
        study_paths(app, app.journey.progression(plan))
    skills(app, app.journey.skills(plan))
    lower = Columns(app.content, app, (1, 1), gap=16, breakpoint=900)
    lower.pack(fill="x", pady=(0, 16))
    achievements(app, lower.cols[0], app.journey.achievements(plan))
    if app.store.pref("rpg_story", True):
        story(app, lower.cols[1], app.journey.chapters(plan))
    challenges(app, app.journey.challenges(plan))


def banner(app):
    p = app.motion.palette
    strip = tk.Frame(app.content, bg=p["warning_bg"])
    strip.pack(fill="x", pady=(0, 16))
    if glyph(strip, "eye"):
        tk.Label(
            strip,
            text=glyph(strip, "eye"),
            bg=p["warning_bg"],
            fg=p["warning"],
            font=(ICON, 12),
        ).pack(side="left", padx=(14, 10), pady=10, anchor="n")
    label = tk.Label(
        strip,
        text=DEMO_NOTE,
        bg=p["warning_bg"],
        fg=p["fg"],
        font=(app.font_family, 9),
        justify="left",
        anchor="w",
    )
    label.pack(side="left", fill="x", expand=True, pady=10, padx=(0, 14))
    label.bind(
        "<Configure>",
        lambda e: label.configure(wraplength=max(200, e.width - 4)),
    )


def stage(app, parent, hero):
    panel = Panel(parent, app, padding=(12, 12), tone="hero", stretch=True)
    panel.pack(fill="both", expand=True)
    view = CharacterView(
        panel.body, app, hero.equipped, backdrop=app.store.pref("rpg_effects", True)
    )
    view.configure(height=330)
    view.pack(fill="both", expand=True)
    app.character_view = view
    MotionButton(
        panel.body,
        text="Personalizar aparência",
        icon="wand-sparkles",
        command=app.customize_character,
    ).pack(pady=(4, 6))


def profile(app, parent, hero, equipment):
    p = app.motion.palette
    panel = Panel(parent, app, padding=(24, 22), stretch=True)
    panel.pack(fill="both", expand=True)
    body = panel.body
    head = ttk.Frame(body, style="Panel.TFrame")
    head.pack(fill="x")
    if hero.source == "demo":
        demo_chip(head).pack(side="left")
    ttk.Label(
        body,
        text=(
            hero.name
            if app.store.pref("rpg_show_character", True)
            else "Progressão dos estudos"
        ),
        style="PanelDisplay.TLabel",
    ).pack(anchor="w", pady=(12, 0))
    if app.store.pref("rpg_show_character", True):
        ttk.Label(body, text=hero.title, style="PanelMuted.TLabel").pack(anchor="w")
    level = ttk.Frame(body, style="Panel.TFrame")
    level.pack(fill="x", pady=(16, 6))
    ttk.Label(level, text=f"Nível {hero.level}", style="PanelHeading.TLabel").pack(
        side="left"
    )
    ttk.Label(
        level,
        text=f"{hero.xp} / {hero.xp_next} XP • faltam {hero.xp_next - hero.xp}",
        style="PanelMuted.TLabel",
    ).pack(side="right")
    ProgressBar(
        body, app, hero.xp / hero.xp_next * 100 if hero.xp_next else 0, height=8
    ).pack(fill="x")
    stats = ttk.Frame(body, style="Panel.TFrame")
    stats.pack(fill="x", pady=(14, 18))
    for icon, text, color, tip in [
        (
            "flame",
            f"{hero.streak_days} dias seguidos",
            p["warning"],
            "Real: dias consecutivos com estudo registrado.",
        ),
        (
            "coins",
            f"{hero.coins} moedas",
            p["accent"],
            (
                "Demonstração."
                if hero.source == "demo"
                else "Moedas virtuais de atividades reais; acessórios com atalhos de estudo, sem multiplicadores."
            ),
        ),
    ]:
        item = ttk.Frame(stats, style="Panel.TFrame")
        item.pack(side="left", padx=(0, 18))
        if glyph(item, icon):
            ttk.Label(
                item,
                text=glyph(item, icon),
                font=(ICON, 12),
                foreground=color,
                style="Panel.TLabel",
            ).pack(side="left", padx=(0, 6))
        ttk.Label(item, text=text, style="Panel.TLabel").pack(side="left")
        Tooltip(item, tip)


def equipment_panel(app, equipment):
    panel = Panel(app.content, app)
    panel.pack(fill="x", pady=(0, 16))
    body = panel.body
    SectionHeader(body, app, "Inventário e recompensas", icon="backpack").pack(fill="x")
    ttk.Label(
        body,
        text="Comece com trapos e uma arma velha. Ganhe equipamento por nível e marcos de estudo.",
        style="PanelMuted.TLabel",
        wraplength=700,
    ).pack(anchor="w", pady=(4, 10))
    tabs = ttk.Frame(body, style="Panel.TFrame")
    tabs.pack(fill="x", pady=(0, 12))
    grid = ttk.Frame(body, style="Panel.TFrame")
    grid.pack(fill="x")
    kinds = list(dict.fromkeys(item.kind for item in equipment))
    selected = getattr(app, "equipment_category", "Roupas")
    if selected not in kinds:
        selected = kinds[0] if kinds else ""
    tiles = []
    layout = [0]

    def reflow(event=None):
        per_row = max(1, min(5, grid.winfo_width() // 165))
        if per_row == layout[0]:
            return
        layout[0] = per_row
        for col in range(5):
            grid.columnconfigure(
                col,
                weight=1 if col < per_row else 0,
                uniform="gear" if col < per_row else "",
            )
        for index, tile in enumerate(tiles):
            row, col = divmod(index, per_row)
            tile.grid(
                row=row,
                column=col,
                sticky="nsew",
                padx=(0 if col == 0 else 8, 0),
                pady=(0 if row == 0 else 8, 0),
            )

    buttons = {}

    def show(kind):
        app.equipment_category = kind
        for widget in grid.winfo_children():
            widget.destroy()
        tiles[:] = [slot(app, grid, item) for item in equipment if item.kind == kind]
        for key, button in buttons.items():
            button.select(key == kind)
        layout[0] = 0
        app.motion.idle(grid, reflow)

    for kind in kinds:
        buttons[kind] = MotionButton(
            tabs, text=kind, style="Chip.TButton", command=lambda k=kind: show(k)
        )
        buttons[kind].pack(side="left", padx=(0, 6))
    grid.bind("<Configure>", reflow)
    show(selected)


def study_paths(app, rows):
    panel = Panel(app.content, app)
    panel.pack(fill="x", pady=(0, 16))
    body = panel.body
    SectionHeader(body, app, "Caminhos de classe", icon="graduation-cap").pack(fill="x")
    ttk.Label(
        body,
        text="Não precisa escolher uma classe. Os seis caminhos evoluem juntos; nenhuma ausência tira seu equipamento.",
        style="PanelMuted.TLabel",
        wraplength=700,
    ).pack(anchor="w", pady=(4, 12))
    for path in rows:
        row = ttk.Frame(body, style="Panel.TFrame")
        row.pack(fill="x", pady=6)
        text = ttk.Frame(row, style="Panel.TFrame")
        text.pack(side="left", fill="x", expand=True)
        ttk.Label(
            text, text=f"{path.name} · {path.rank}", style="PanelHeading.TLabel"
        ).pack(anchor="w")
        label = ttk.Label(
            text,
            text=f"{path.value}/{path.target} {path.unit} · {path.purpose}",
            style="PanelMuted.TLabel",
            wraplength=600,
        )
        label.pack(anchor="w", pady=(2, 4))
        label.bind(
            "<Configure>",
            lambda e, w=label: (
                w.configure(wraplength=max(160, e.width))
                if int(w.cget("wraplength")) != max(160, e.width)
                else None
            ),
        )
        ProgressBar(text, app, min(100, path.value / path.target * 100), height=5).pack(
            fill="x"
        )

        def practice(action=path.action):
            from rpg_ui import study_action

            study_action(app, action)

        MotionButton(row, text="Praticar", command=practice).pack(
            side="right", padx=(16, 0)
        )


ITEM_ICONS = [
    ("staff", "wand-sparkles"),
    ("bow", "crosshair"),
    ("blade", "sword"),
    ("sword", "sword"),
    ("shield", "shield"),
    ("helm", "crown"),
    ("hood", "venetian-mask"),
    ("boots", "footprints"),
    ("armor", "shield-half"),
    ("robe", "shirt"),
    ("tunic", "shirt"),
    ("coat", "shirt"),
    ("griffin", "bird"),
    ("horse", "paw-print"),
    ("mule", "paw-print"),
]


def item_icon(item):
    named = {
        "backpack": "backpack",
        "compass": "compass",
        "scarf": "feather",
        "spyglass": "telescope",
        "lantern": "lamp",
    }
    if item.id in named:
        return named[item.id]
    for key, icon in ITEM_ICONS:
        if key in item.id:
            return icon
    return {
        "Armas": "swords",
        "Armaduras": "shield-half",
        "Montarias": "paw-print",
        "Roupas": "shirt",
    }.get(getattr(item, "kind", ""), "gem")


def slot(app, parent, item):
    p = app.motion.palette
    equipped = item.equipped
    fill = p["tint"] if equipped else p["raised"]
    frame = tk.Frame(
        parent,
        bg=fill,
        highlightthickness=1,
        highlightbackground=(
            blend(p["border"], p["accent"], 0.5) if equipped else p["border"]
        ),
        cursor="hand2",
        takefocus=True,
    )
    icon = item_icon(item)
    tk.Label(
        frame,
        text=glyph(frame, icon if item.unlocked else "lock"),
        bg=fill,
        fg=p["accent"] if equipped else (p["muted"] if item.unlocked else p["faint"]),
        font=(ICON, 15),
    ).pack(pady=(10, 2))
    name = tk.Label(
        frame,
        text=item.name,
        bg=fill,
        fg=p["fg"] if item.unlocked else p["muted"],
        font=(app.font_family, 9),
        justify="center",
        wraplength=145,
    )
    name.pack(padx=4)
    tk.Label(
        frame,
        text=(
            "Equipado"
            if equipped
            else ("Guardado" if item.unlocked else item.unlock_hint)
        ),
        bg=fill,
        fg=p["accent"] if equipped else p["faint"],
        font=(app.font_family, 8, "bold"),
        wraplength=145,
        justify="center",
    ).pack(pady=(2, 8), padx=4)
    tk.Label(
        frame,
        text=item.purpose or item.description,
        bg=fill,
        fg=p["muted"],
        font=(app.font_family, 8),
        wraplength=145,
        justify="center",
    ).pack(padx=8, pady=(0, 10))
    Tooltip(
        frame,
        f"{item.name} • {item.slot}\n{item.description}"
        + ("" if item.unlocked else f"\nLiberado em: {item.unlock_hint}")
        + (
            "\nDemonstração: a escolha não é salva."
            if item.source == "demo"
            else "\nClique para visualizar, comprar ou equipar."
        ),
    )

    def toggle(event=None):
        if item.source == "real":
            from rpg_ui import purchase_preview

            purchase_preview(app, item.id)
            return
        if not item.unlocked:
            return
        app.journey.toggle_equipment(app.plan, item.id)
        app.refresh()

    frame.bind("<Return>", toggle)
    frame.bind("<space>", toggle)
    for widget in [frame, *frame.winfo_children()]:
        widget.bind("<Button-1>", toggle)
    hover_card(
        app,
        frame,
        fill,
        blend(fill, p["primary"], 0.12) if equipped else p["hover"],
        frame.cget("highlightbackground"),
        p["accent"] if item.unlocked else p["strong"],
    )
    return frame


def skills(app, rows):
    panel = Panel(app.content, app)
    panel.pack(fill="x", pady=(0, 16))
    body = panel.body
    demo = any(skill.progress_source == "demo" for skill in rows)
    SectionHeader(
        body,
        app,
        "Habilidades por matéria",
        icon="graduation-cap",
        chip=(
            (
                lambda parent: Chip(
                    parent,
                    "NÍVEL: DEMONSTRAÇÃO",
                    tone="demo",
                    tip="O nível por matéria é fictício. Esforço e desempenho são reais.",
                )
            )
            if demo
            else None
        ),
    ).pack(fill="x")
    ttk.Label(
        body,
        text="Horas mostram esforço, não domínio. O desempenho só aparece quando há questões suficientes, em dias diferentes.",
        style="PanelMuted.TLabel",
        font=(app.font_family, 9),
    ).pack(anchor="w", pady=(4, 12))
    if not rows:
        EmptyState(
            body,
            app,
            "graduation-cap",
            "Nenhuma matéria neste plano",
            "Cadastre matérias para acompanhar esforço e desempenho.",
        ).pack(fill="x")
        return
    grid = ttk.Frame(body, style="Panel.TFrame")
    grid.pack(fill="x")
    rows = sorted(rows, key=lambda s: (-s.effort_seconds, s.name))
    most = max([s.effort_seconds for s in rows] + [1])
    cards = [skill_card(app, grid, skill, most) for skill in rows]
    layout = [0]

    def reflow(event=None):
        width = grid.winfo_width()
        columns = 3 if width > 1000 else 2 if width > 620 else 1
        if columns == layout[0]:
            return
        layout[0] = columns
        for index in range(3):
            grid.columnconfigure(
                index,
                weight=1 if index < columns else 0,
                uniform="skill" if index < columns else "",
            )
        for index, card in enumerate(cards):
            col = index % columns
            card.grid(
                row=index // columns,
                column=col,
                sticky="nsew",
                padx=(0 if col == 0 else 6, 0 if col == columns - 1 else 6),
                pady=(0, 12),
            )

    grid.bind("<Configure>", reflow)
    app.motion.idle(grid, reflow)


def skill_card(app, parent, skill, most):
    p = app.motion.palette
    card = tk.Frame(
        parent, bg=p["raised"], highlightthickness=1, highlightbackground=p["border"]
    )
    head = tk.Frame(card, bg=p["raised"])
    head.pack(fill="x", padx=14, pady=(12, 0))
    name = tk.Label(
        head,
        text=skill.name,
        bg=p["raised"],
        fg=p["fg"],
        font=(app.font_family, 10, "bold"),
        anchor="w",
        justify="left",
    )
    name.pack(side="left", fill="x", expand=True)
    name.bind("<Configure>", lambda e: name.configure(wraplength=max(80, e.width - 4)))
    if skill.level is not None:
        tk.Label(
            head,
            text=f"Nv {skill.level}",
            bg=p["tint"],
            fg=p["accent"],
            font=(app.font_family, 8, "bold"),
            padx=8,
            pady=2,
        ).pack(side="right", anchor="n", padx=(8, 0))
    if skill.level is not None and skill.progress_source == "real":
        tk.Label(
            card,
            text=f"Experiência de esforço: {skill.xp} / {skill.xp_next} XP",
            bg=p["raised"],
            fg=p["muted"],
            font=(app.font_family, 8),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(8, 0))
        ProgressBar(
            card,
            app,
            skill.xp / skill.xp_next * 100 if skill.xp_next else 0,
            height=3,
            bg=p["raised"],
        ).pack(fill="x", padx=14, pady=(4, 0))
    for label, value, bar, tone, icon in [
        (
            "Esforço registrado",
            compact_duration(skill.effort_seconds) if skill.effort_seconds else "—",
            skill.effort_seconds / most * 100,
            "accent",
            "timer",
        ),
        (
            "Desempenho observado",
            (
                f"{percent(skill.accuracy)} • {number(skill.answered)} questões"
                if skill.sample_ok
                else (
                    f"Dados insuficientes ({skill.answered} respostas)"
                    if skill.answered
                    else "Dados insuficientes"
                )
            ),
            (skill.accuracy or 0) if skill.sample_ok else 0,
            "info",
            "target",
        ),
    ]:
        row = tk.Frame(card, bg=p["raised"])
        row.pack(fill="x", padx=14, pady=(10, 0))
        if glyph(row, icon):
            tk.Label(
                row, text=glyph(row, icon), bg=p["raised"], fg=p[tone], font=(ICON, 10)
            ).pack(side="left", padx=(0, 6))
        tk.Label(
            row, text=label, bg=p["raised"], fg=p["muted"], font=(app.font_family, 8)
        ).pack(side="left")
        tk.Label(
            row, text=value, bg=p["raised"], fg=p["fg"], font=(app.font_family, 9)
        ).pack(side="right")
        ProgressBar(card, app, bar, tone=tone, height=4, bg=p["raised"]).pack(
            fill="x", padx=14, pady=(5, 0)
        )
    tk.Frame(card, bg=p["raised"], height=12).pack()
    hover_card(app, card, p["raised"], p["hover"], p["border"], p["strong"])
    for widget in [card, head, name]:
        widget.bind(
            "<Button-1>", lambda e, sid=skill.subject_id: app.subject_detail(sid)
        )
    card.configure(cursor="hand2")
    return card


def achievements(app, parent, items):
    p = app.motion.palette
    panel = Panel(parent, app, stretch=True)
    panel.pack(fill="both", expand=True)
    body = panel.body
    SectionHeader(
        body,
        app,
        "Conquistas",
        icon="award",
        chip=demo_chip if any(i.source == "demo" for i in items) else None,
    ).pack(fill="x")
    done = sum(item.done for item in items)
    ttk.Label(
        body,
        text=f"{done} de {len(items)} conquistadas. Nenhuma depende de estudar até tarde.",
        style="PanelMuted.TLabel",
        font=(app.font_family, 9),
    ).pack(anchor="w", pady=(4, 12))
    for item in items:
        row = ttk.Frame(body, style="Panel.TFrame")
        row.pack(fill="x", pady=(0, 12))
        badge = tk.Canvas(
            row, width=38, height=38, bg=app.surface, highlightthickness=0
        )
        badge.pack(side="left", padx=(0, 12))
        badge.create_oval(
            1,
            1,
            37,
            37,
            fill=p["tint"] if item.done else p["raised"],
            outline=p["accent"] if item.done else p["border"],
        )
        badge.create_text(
            19,
            19,
            text=glyph(badge, item.icon),
            fill=p["accent"] if item.done else p["faint"],
            font=(ICON, 13),
        )
        texts = ttk.Frame(row, style="Panel.TFrame")
        texts.pack(side="left", fill="x", expand=True)
        line = ttk.Frame(texts, style="Panel.TFrame")
        line.pack(fill="x")
        ttk.Label(line, text=item.name, style="Panel.TLabel").pack(side="left")
        ttk.Label(
            line,
            text="concluída" if item.done else f"{item.progress}/{item.target}",
            style="PanelMuted.TLabel",
            font=(app.font_family, 9),
            foreground=p["success"] if item.done else p["muted"],
        ).pack(side="right")
        ttk.Label(
            texts, text=item.rule, style="PanelMuted.TLabel", font=(app.font_family, 9)
        ).pack(anchor="w")
        if not item.done:
            ProgressBar(texts, app, item.progress / item.target * 100, height=3).pack(
                fill="x", pady=(5, 0)
            )


def story(app, parent, chapters):
    p = app.motion.palette
    panel = Panel(parent, app, stretch=True)
    panel.pack(fill="both", expand=True)
    body = panel.body
    SectionHeader(
        body,
        app,
        "História",
        icon="scroll-text",
        chip=demo_chip if any(c.source == "demo" for c in chapters) else None,
    ).pack(fill="x")
    ttk.Label(
        body,
        text="Capítulos curtos que avançam com a sua rotina, sem prazo.",
        style="PanelMuted.TLabel",
        font=(app.font_family, 9),
    ).pack(anchor="w", pady=(4, 12))
    for index, chapter in enumerate(chapters):
        row = ttk.Frame(body, style="Panel.TFrame")
        row.pack(fill="x")
        rail = tk.Canvas(row, width=32, height=72, bg=app.surface, highlightthickness=0)
        rail.pack(side="left", fill="y")
        color = {
            "done": p["success"],
            "current": p["accent"],
            "locked": p["faint"],
        }[chapter.state]
        if index < len(chapters) - 1:
            rail.create_line(16, 30, 16, 200, fill=p["border"], width=2)
        rail.create_oval(
            4,
            4,
            28,
            28,
            fill=p["tint"] if chapter.state == "current" else p["raised"],
            outline=color,
            width=1.5,
        )
        rail.create_text(
            16,
            16,
            text=glyph(
                rail,
                {"done": "check", "current": "compass", "locked": "lock"}[
                    chapter.state
                ],
            ),
            fill=color,
            font=(ICON, 10),
        )
        texts = ttk.Frame(row, style="Panel.TFrame")
        texts.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=(4, 12))
        line = ttk.Frame(texts, style="Panel.TFrame")
        line.pack(fill="x")
        ttk.Label(
            line,
            text=f"Capítulo {chapter.number} • {chapter.title}",
            style="Panel.TLabel",
            font=(app.font_family, 10, "bold"),
            foreground=p["fg"] if chapter.state != "locked" else p["muted"],
        ).pack(side="left")
        state = {
            "done": "desbloqueado",
            "current": "capítulo atual",
            "locked": "bloqueado",
        }[chapter.state]
        ttk.Label(
            line,
            text=state,
            style="PanelMuted.TLabel",
            font=(app.font_family, 8),
            foreground=color,
        ).pack(side="right")
        summary = ttk.Label(
            texts,
            text=(
                chapter.summary
                if chapter.state != "locked"
                else "Para liberar: " + chapter.requirement
            ),
            style="PanelMuted.TLabel",
            font=(app.font_family, 9),
            justify="left",
        )
        summary.pack(fill="x", anchor="w")
        summary.bind(
            "<Configure>",
            lambda e, w=summary: w.configure(wraplength=max(120, e.width - 4)),
        )


def challenges(app, items):
    p = app.motion.palette
    panel = Panel(app.content, app)
    panel.pack(fill="x", pady=(0, 8))
    body = panel.body
    SectionHeader(
        body,
        app,
        "Masmorras e chefes",
        icon="castle",
        chip=demo_chip if any(i.source == "demo" for i in items) else None,
        action=("Ver simulados", lambda: app.navigate("Simulados")),
    ).pack(fill="x")
    ttk.Label(
        body,
        text="Desafios usam apenas assuntos já estudados. O resultado continua sendo uma análise séria.",
        style="PanelMuted.TLabel",
        font=(app.font_family, 9),
    ).pack(anchor="w", pady=(4, 12))
    grid = ttk.Frame(body, style="Panel.TFrame")
    grid.pack(fill="x")
    if not items:
        EmptyState(
            body,
            app,
            "castle",
            "Nenhum desafio criado",
            "Monte uma masmorra com assuntos já estudados ou registre um simulado como chefe.",
            [("Ver simulados", lambda: app.navigate("Simulados"), "swords")],
        ).pack(fill="x")
        return
    for index, item in enumerate(items):
        grid.columnconfigure(index % 2, weight=1, uniform="challenge")
        boss = item.kind == "chefe"
        fill = p["raised"]
        card = tk.Frame(
            grid,
            bg=fill,
            highlightthickness=1,
            highlightbackground=p["accent"] if boss else p["border"],
        )
        card.grid(
            row=index // 2,
            column=index % 2,
            sticky="nsew",
            padx=(0 if index % 2 == 0 else 6, 6 if index % 2 == 0 else 0),
            pady=(0 if index < 2 else 12, 0),
        )
        head = tk.Frame(card, bg=fill)
        head.pack(fill="x", padx=16, pady=(14, 0))
        tk.Label(
            head,
            text=glyph(head, "crown" if boss else "castle"),
            bg=fill,
            fg=p["accent"] if boss else p["muted"],
            font=(ICON, 16),
        ).pack(side="left", padx=(0, 10))
        tk.Label(
            head,
            text=("CHEFE" if boss else "MASMORRA"),
            bg=fill,
            fg=p["accent"] if boss else p["muted"],
            font=(app.font_family, 8, "bold"),
        ).pack(side="left")
        tk.Label(
            card,
            text=item.title,
            bg=fill,
            fg=p["fg"],
            font=(app.font_family, 11, "bold"),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(8, 0))
        detail = tk.Label(
            card,
            text=item.detail,
            bg=fill,
            fg=p["muted"],
            font=(app.font_family, 9),
            anchor="w",
            justify="left",
        )
        detail.pack(fill="x", padx=16, pady=(2, 0))
        detail.bind(
            "<Configure>",
            lambda e, w=detail: w.configure(wraplength=max(120, e.width - 4)),
        )
        tk.Label(
            card,
            text=f"{item.questions} questões • "
            + (
                compact_duration(item.minutes * 60)
                if item.minutes
                else "sem limite de tempo"
            )
            + (f" • {', '.join(item.subjects)}" if item.subjects else ""),
            bg=fill,
            fg=p["faint"],
            font=(app.font_family, 8),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(8, 0))
        handler = getattr(app, "start_challenge", None)
        ready = item.available and item.source == "real" and handler
        MotionButton(
            card,
            text="Enfrentar" if ready else "Disponível após a integração",
            icon="swords" if ready else "lock",
            style="Accent.TButton" if ready and boss else "TButton",
            height=34,
            state="normal" if ready else "disabled",
            command=(lambda c=item: handler(c)) if ready else None,
        ).pack(anchor="w", padx=16, pady=(12, 14))
