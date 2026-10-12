"""Jornada: character, subject skills, decorative equipment, achievements, story.

All RPG values come from ``app.journey`` (journey.py contracts). In the preview,
values marked ``demo`` are fictitious and labelled; effort and performance per
subject are read from real records.
"""

import tkinter as tk
from tkinter import ttk

from theme import DISPLAY, ICON, compact_duration, number, percent
from ui_kit import ActionMenu, Card, Row, Section, icon_label, label, wrapping
from ui import (
    background_of,
    load_image,
    rounded,
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
    equipment = app.journey.equipment(plan)
    if hero.source == "demo":
        banner(app)
    head = tk.Frame(app.content, bg=app.bg)
    head.pack(fill="x", pady=(0, 12))
    if hero.source == "real":
        from rpg_ui import progression_details, rename_character, retroactive_preview

        ActionMenu(
            head,
            app,
            [
                ("Nome do personagem", lambda: rename_character(app)),
                ("Personalizar aparência", app.customize_character),
                None,
                ("Como ganho XP e moedas", lambda: progression_details(app)),
                ("Importar XP do histórico", lambda: retroactive_preview(app)),
            ],
            text="Ajustes da jornada",
            icon="settings",
        ).pack(side="right")
        credit = app.store.rpg.profile(plan)["correction_credit"]
        if credit:
            wrapping(
                label(
                    head,
                    app,
                    f"Uma correção de estudos deixou {credit} moedas a compensar com ganhos futuros. "
                    "Os itens comprados continuam seus.",
                    size=9,
                    tone="muted",
                )
            ).pack(side="left", fill="x", expand=True)
    top = Columns(
        app.content,
        app,
        (5, 6) if app.store.pref("rpg_show_character", True) else (1,),
        gap=18,
        breakpoint=980,
    )
    top.pack(fill="x", pady=(0, 26))
    if app.store.pref("rpg_show_character", True):
        stage(app, top.cols[0], hero)
    profile(app, top.cols[-1], hero, equipment)
    inventory(app, equipment)
    if hero.source == "real":
        study_paths(app, app.journey.progression(plan))
    skills(app, app.journey.skills(plan))
    lower = Columns(app.content, app, (1, 1), gap=18, breakpoint=900)
    lower.pack(fill="x", pady=(0, 26))
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
    text = tk.Label(
        strip,
        text=DEMO_NOTE,
        bg=p["warning_bg"],
        fg=p["fg"],
        font=(app.font_family, 9),
        justify="left",
        anchor="w",
    )
    text.pack(side="left", fill="x", expand=True, pady=10, padx=(0, 14))
    wrapping(text, 4, 200)


def item_art(app, canvas, item, size, fill):
    p = app.motion.palette
    canvas.delete("all")
    rounded(canvas, 0, 0, size - 1, size - 1, 12, fill=fill, outline="")
    folder = 96 if size >= 90 else 64 if size >= 60 else 44
    path = f"character/items/{folder}/{item.id}.png"
    if (app.assets / path).is_file():
        canvas.create_image(size / 2, size / 2, image=load_image(app, path))
    else:
        canvas.create_text(
            size / 2,
            size / 2,
            text=glyph(canvas, item_icon(item)),
            fill=p["muted"] if item.unlocked else p["faint"],
            font=(ICON, max(12, size // 3)),
        )
    if not item.unlocked:
        r = max(9, size // 6)
        canvas.create_oval(
            size - 2 * r - 3,
            size - 2 * r - 3,
            size - 3,
            size - 3,
            fill=p["surface"],
            outline=p["border"],
        )
        canvas.create_text(
            size - r - 3,
            size - r - 3,
            text=glyph(canvas, "lock"),
            fill=p["muted"],
            font=(ICON, max(8, r - 1)),
        )
    elif item.equipped:
        canvas.create_oval(size - 15, 4, size - 5, 14, fill=p["primary"], outline="")


def art(app, parent, item, size=56, fill=None):
    p = app.motion.palette
    fill = fill or p["raised"]
    canvas = tk.Canvas(
        parent,
        width=size,
        height=size,
        bg=background_of(parent) or p["surface"],
        highlightthickness=0,
    )
    item_art(app, canvas, item, size, fill)
    return canvas


def stage(app, parent, hero):
    card = Card(parent, app, padding=(14, 14), stretch=True)
    card.pack(fill="both", expand=True)
    view = CharacterView(
        card.body, app, hero.equipped, backdrop=app.store.pref("rpg_effects", True)
    )
    view.configure(height=360)
    view.pack(fill="both", expand=True)
    app.character_view = view
    MotionButton(
        card.body,
        text="Personalizar aparência",
        icon="wand-sparkles",
        style="Ghost.TButton",
        command=app.customize_character,
    ).pack(pady=(2, 2))


def profile(app, parent, hero, equipment):
    p = app.motion.palette
    card = Card(parent, app, padding=(26, 24), stretch=True)
    card.pack(fill="both", expand=True)
    body = card.body
    if hero.source == "demo":
        demo_chip(body).pack(anchor="w", pady=(0, 10))
    show = app.store.pref("rpg_show_character", True)
    tk.Label(
        body,
        text=hero.name if show else "Progressão dos estudos",
        bg=p["surface"],
        fg=p["fg"],
        font=(DISPLAY, 19, "bold"),
        anchor="w",
    ).pack(fill="x")
    if show:
        label(body, app, hero.title, size=10, tone="muted").pack(anchor="w")
    level = tk.Frame(body, bg=p["surface"])
    level.pack(fill="x", pady=(18, 6))
    label(level, app, f"Nível {hero.level}", size=12, weight="bold").pack(side="left")
    label(
        level,
        app,
        f"{number(hero.xp)} de {number(hero.xp_next)} XP · faltam {number(hero.xp_next - hero.xp)}",
        size=9,
        tone="muted",
    ).pack(side="right")
    ProgressBar(
        body, app, hero.xp / hero.xp_next * 100 if hero.xp_next else 0, height=7
    ).pack(fill="x")
    stats = tk.Frame(body, bg=p["surface"])
    stats.pack(fill="x", pady=(12, 0))
    for icon, text, tone, tip in [
        (
            "flame",
            f"{hero.streak_days} {'dia' if hero.streak_days == 1 else 'dias'} seguidos",
            "warning",
            "Dias consecutivos com estudo registrado. Faltar um dia não tira nada.",
        ),
        (
            "coins",
            f"{number(hero.coins or 0)} moedas",
            "accent",
            (
                "Demonstração."
                if hero.source == "demo"
                else "Moedas virtuais de atividades reais; compram acessórios, sem multiplicadores."
            ),
        ),
    ]:
        item = tk.Frame(stats, bg=p["surface"])
        item.pack(side="left", padx=(0, 20))
        icon_label(item, app, icon, size=11, tone=tone).pack(side="left", padx=(0, 6))
        label(item, app, text, size=10).pack(side="left")
        Tooltip(item, tip)
    upcoming = [i for i in equipment if not i.unlocked]
    rewards = [i for i in upcoming if i.acquisition == "reward"] or upcoming
    if rewards:
        nxt = rewards[0]
        label(body, app, "Próximo desbloqueio", size=10, weight="bold").pack(
            anchor="w", pady=(22, 8)
        )
        line = tk.Frame(body, bg=p["surface"], cursor="hand2")
        line.pack(fill="x")
        art(app, line, nxt, 48).pack(side="left", padx=(0, 12))
        texts = tk.Frame(line, bg=p["surface"])
        texts.pack(side="left", fill="x", expand=True)
        label(texts, app, nxt.name, size=10).pack(anchor="w")
        wrapping(label(texts, app, nxt.unlock_hint, size=9, tone="muted")).pack(
            fill="x"
        )
        for widget in (line, texts, *texts.winfo_children()):
            widget.bind("<Button-1>", lambda e, i=nxt: select_item(app, i), add="+")
    worn = [i for i in equipment if i.equipped]
    if worn:
        label(body, app, "Equipado", size=10, weight="bold").pack(
            anchor="w", pady=(20, 8)
        )
        slots = tk.Frame(body, bg=p["surface"])
        slots.pack(fill="x")
        for index, item in enumerate(worn[:8]):
            cell = art(app, slots, item, 44)
            cell.grid(row=index // 8, column=index % 8, padx=(0, 8), pady=(0, 8))
            cell.configure(cursor="hand2")
            cell.bind("<Button-1>", lambda e, i=item: select_item(app, i))
            Tooltip(cell, f"{item.name} · {item.slot}")


def select_item(app, item):
    app.equipment_category = item.kind
    app.equipment_selected = item.id
    app.refresh()


def inventory(app, equipment):
    p = app.motion.palette
    owned = sum(item.unlocked for item in equipment)
    section = Section(
        app.content, app, "Inventário", count=f"{owned} de {len(equipment)}"
    )
    section.pack(fill="x", pady=(0, 10))
    wrapping(
        label(
            app.content,
            app,
            "Você começa com trapos e uma arma velha. Itens chegam por nível e por marcos de estudo; nenhum dá vantagem nas métricas.",
            size=9,
            tone="muted",
        )
    ).pack(fill="x", pady=(0, 12))
    columns = Columns(app.content, app, (3, 2), gap=18, breakpoint=900)
    columns.pack(fill="x", pady=(0, 26))
    grid_card = Card(columns.cols[0], app, padding=(18, 16), stretch=True)
    grid_card.pack(fill="both", expand=True)
    detail_card = Card(columns.cols[1], app, padding=(24, 22), stretch=True)
    detail_card.pack(fill="both", expand=True)
    tabs = tk.Frame(grid_card.body, bg=p["surface"])
    tabs.pack(fill="x", pady=(0, 14))
    grid = tk.Frame(grid_card.body, bg=p["surface"])
    grid.pack(fill="x")
    kinds = list(dict.fromkeys(item.kind for item in equipment))
    selected_kind = getattr(app, "equipment_category", "Roupas")
    if selected_kind not in kinds:
        selected_kind = kinds[0] if kinds else ""
    by_id = {item.id: item for item in equipment}
    tiles = []
    layout = [0]
    buttons = {}
    current = [by_id.get(getattr(app, "equipment_selected", None))]

    def reflow(event=None):
        per_row = max(2, min(6, grid.winfo_width() // 104))
        if per_row == layout[0]:
            return
        layout[0] = per_row
        for col in range(6):
            grid.columnconfigure(
                col,
                weight=1 if col < per_row else 0,
                uniform="gear" if col < per_row else "",
            )
        for index, tile in enumerate(tiles):
            row, col = divmod(index, per_row)
            tile.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)

    def show(kind):
        app.equipment_category = kind
        for widget in grid.winfo_children():
            widget.destroy()
        items = [item for item in equipment if item.kind == kind]
        tiles[:] = [tile(app, grid, item, choose) for item in items]
        for key, button in buttons.items():
            button.select(key == kind)
        layout[0] = 0
        app.motion.idle(grid, reflow)
        if not current[0] or current[0].kind != kind:
            choose(items[0] if items else None)
        else:
            choose(current[0])

    def choose(item):
        current[0] = item
        app.equipment_selected = item.id if item else None
        for widget in tiles:
            widget.mark(widget.item is item)
        item_detail(app, detail_card.body, item)

    for kind in kinds:
        buttons[kind] = MotionButton(
            tabs, text=kind, style="Chip.TButton", command=lambda k=kind: show(k)
        )
        buttons[kind].pack(side="left", padx=(0, 6))
    grid.bind("<Configure>", reflow)
    show(selected_kind)


def tile(app, parent, item, on_choose):
    p = app.motion.palette
    frame = tk.Frame(parent, bg=p["surface"], cursor="hand2", takefocus=True)
    frame.item = item
    picture = art(app, frame, item, 64)
    picture.pack(pady=(8, 4))
    name = tk.Label(
        frame,
        text=item.name,
        bg=p["surface"],
        fg=p["fg"] if item.unlocked else p["muted"],
        font=(app.font_family, 9),
        wraplength=92,
        justify="center",
    )
    name.pack(padx=4, pady=(0, 8))
    selected = [False]

    def paint(color):
        for widget in (frame, name):
            widget.configure(bg=color)
        picture.configure(bg=color)

    def mark(value):
        selected[0] = value
        paint(p["selected"] if value else p["surface"])

    def hover(inside):
        if not selected[0]:
            paint(p["hover"] if inside else p["surface"])

    frame.mark = mark
    for widget in (frame, picture, name):
        widget.bind("<Button-1>", lambda e: on_choose(item))
        widget.bind("<Enter>", lambda e: hover(True))
        widget.bind("<Leave>", lambda e: hover(False))
    frame.bind("<Return>", lambda e: on_choose(item))
    return frame


def item_detail(app, body, item):
    p = app.motion.palette
    for widget in body.winfo_children():
        widget.destroy()
    if item is None:
        label(body, app, "Nenhum item nesta categoria.", size=10, tone="muted").pack(
            anchor="w"
        )
        return
    art(app, body, item, 96, p["raised"]).pack(anchor="w")
    wrapping(label(body, app, item.name, size=14, weight="bold")).pack(
        fill="x", pady=(14, 0)
    )
    state = (
        "Equipado"
        if item.equipped
        else ("Guardado no inventário" if item.unlocked else "Bloqueado")
    )
    kind = (
        item.kind
        if item.slot.lower() in item.kind.lower()
        else f"{item.kind} · {item.slot}"
    )
    label(
        body,
        app,
        f"{kind} · {state}",
        size=9,
        tone="accent" if item.equipped else "muted",
    ).pack(anchor="w", pady=(4, 0))
    wrapping(label(body, app, item.description, size=10)).pack(fill="x", pady=(14, 0))
    if item.purpose and item.purpose.strip() != item.description.strip():
        wrapping(label(body, app, item.purpose, size=9, tone="muted")).pack(
            fill="x", pady=(8, 0)
        )
    if not item.unlocked:
        label(body, app, "Como liberar", size=10, weight="bold").pack(
            anchor="w", pady=(16, 2)
        )
        wrapping(label(body, app, item.unlock_hint, size=10, tone="muted")).pack(
            fill="x"
        )

    def act():
        if item.source == "real":
            from rpg_ui import purchase_preview

            purchase_preview(app, item.id)
            return
        if item.unlocked:
            app.journey.toggle_equipment(app.plan, item.id)
            app.refresh()

    text = (
        ("Desequipar" if item.equipped else "Equipar")
        if item.unlocked
        else (
            "Ver requisitos e preço" if item.acquisition == "shop" else "Ver requisitos"
        )
    )
    if item.source == "real":
        text = "Ver, comprar ou equipar" if not item.unlocked else text
    MotionButton(
        body,
        text=text,
        icon="shirt" if item.unlocked else "lock",
        command=act,
        state="normal" if item.source == "real" or item.unlocked else "disabled",
    ).pack(side="bottom", anchor="w", pady=(16, 0))


def study_paths(app, rows):
    section = Section(app.content, app, "Caminhos de classe")
    section.pack(fill="x", pady=(0, 6))
    wrapping(
        label(
            app.content,
            app,
            "Não precisa escolher uma classe: os seis caminhos evoluem juntos, e nenhuma ausência tira seu equipamento.",
            size=9,
            tone="muted",
        )
    ).pack(fill="x", pady=(0, 12))
    card = Card(app.content, app, padding=(14, 8))
    card.pack(fill="x", pady=(0, 26))
    for index, path in enumerate(rows):
        row = Row(
            card.body,
            app,
            f"{path.name} · {path.rank}",
            f"{path.value} de {path.target} {path.unit} · {path.purpose}",
            separator=index < len(rows) - 1,
        )
        row.pack(fill="x")
        ProgressBar(
            row.texts, app, min(100, path.value / path.target * 100), height=4
        ).pack(fill="x", pady=(6, 2))

        def practice(action=path.action):
            from rpg_ui import study_action

            study_action(app, action)

        MotionButton(row.trail, text="Praticar", height=32, command=practice).pack(
            side="right", padx=(16, 0)
        )
        row.refresh_bindings()


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
    panel.pack(fill="x", pady=(0, 26))
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
                    "Nível de demonstração",
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
    card = tk.Frame(parent, bg=p["raised"], highlightthickness=0)
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
    hover_card(app, card, p["raised"], p["hover"])
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
    section = Section(app.content, app, "Masmorras, chefes e revanche")
    section.pack(fill="x", pady=(0, 6))
    if any(i.source == "demo" for i in items):
        demo_chip(section).pack(side="left", padx=(10, 0))
    if app.journey.character(app.plan).source == "real":
        from rpg_ui import challenge_form, challenge_list, difficulty_list

        section.action(
            "Criar masmorra ou chefe",
            lambda: challenge_form(app),
            icon="plus",
            style="TButton",
        )
        section.menu(
            "",
            [
                ("Desafios em andamento", lambda: challenge_list(app)),
                ("Dificuldades e revanche", lambda: difficulty_list(app)),
                None,
                ("Ver simulados", lambda: app.navigate("Simulados")),
            ],
        )
    wrapping(
        label(
            app.content,
            app,
            "Masmorras usam só assuntos que você já estudou; um simulado registrado pode ser o chefe. "
            "Dificuldades anotadas voltam como revanche.",
            size=9,
            tone="muted",
        )
    ).pack(fill="x", pady=(0, 12))
    panel = Card(app.content, app, padding=(18, 16))
    panel.pack(fill="x", pady=(0, 8))
    body = panel.body
    grid = ttk.Frame(body, style="Panel.TFrame")
    grid.pack(fill="x")
    if not items:
        EmptyState(
            body,
            app,
            "castle",
            "Nenhum desafio criado",
            "Monte uma masmorra com assuntos já estudados ou registre um simulado como chefe.",
            [],
        ).pack(fill="x")
        return
    for index, item in enumerate(items):
        grid.columnconfigure(index % 2, weight=1, uniform="challenge")
        boss = item.kind == "chefe"
        fill = p["raised"]
        card = tk.Frame(grid, bg=fill, highlightthickness=0)
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
            text=("Chefe" if boss else "Masmorra"),
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
