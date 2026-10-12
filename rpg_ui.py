"""Functional RPG forms using the approved native RUMO components."""

import tkinter as tk
from tkinter import ttk

from core import duration
from journey import ReducedMission
from rpg import CONTEXT_KEYS
from ui import MotionButton, Panel, CharacterView, trace_owned


def form_class():
    from app import Form

    return Form


def context_from(initial):
    return {key: initial[key] for key in CONTEXT_KEYS if initial.get(key) is not None}


def render_tools(app):
    app.heading("Prática e progressão reais")
    app.note(
        "Revisões usam seus registros existentes. Dificuldades são descritas por você; questões vêm do seu material, sem IA ou banco de provas."
    )
    app.toolbar(
        [
            ("Dificuldades e revanche", lambda: difficulty_list(app)),
            ("Criar masmorra ou chefe", lambda: challenge_form(app)),
            ("Desafios em andamento", lambda: challenge_list(app)),
            ("Nome do personagem", lambda: rename_character(app)),
            ("Como ganho XP?", lambda: progression_details(app)),
            ("Importar XP do histórico", lambda: retroactive_preview(app)),
        ]
    )
    profile = app.store.rpg.profile(app.plan)
    if profile["correction_credit"]:
        app.note(
            f"Uma correção de estudos deixou {profile['correction_credit']} moedas a compensar com ganhos futuros. Seu saldo disponível é zero; os itens comprados continuam seus."
        )


def progression_details(app):
    from app import messagebox

    profile = app.store.rpg.profile(app.plan)
    messagebox.showinfo(
        "Esforço e desempenho",
        profile["explanation"]
        + "\n\nNível 1 começa em 0 XP. Para passar do nível L ao próximo, são necessários 100 × L XP. Cada atividade rende uma moeda por 10 XP completos dessa atividade.\n\nTempo não comprova domínio. Aproveitamento só aparece com 20 questões respondidas em pelo menos 3 datas. Autoavaliação de lembrança é sempre identificada como sua percepção.\n\nHistória e itens desbloqueados permanecem após correções; novas moedas primeiro compensam compras que perderam cobertura. Nenhuma ausência ou revisão atrasada retira recompensas.\n\nXP atual deste plano: "
        + str(profile["xp"]),
        parent=app.root,
    )


def difficulty_form(app, difficulty=None, session=None):
    engine = app.store.rpg
    topic_rows = app.store.rows(
        "SELECT t.id,t.name,s.name subject FROM topics t JOIN subjects s ON s.id=t.subject_id WHERE s.plan_id=? "
        + ("" if difficulty or session else "AND t.archived=0 AND s.archived=0 ")
        + "ORDER BY s.name,t.rowid",
        (app.plan,),
    )
    topics = {
        f"{index}. {row['subject']} · {row['name']}": row["id"]
        for index, row in enumerate(topic_rows, 1)
    }
    selected = difficulty or {}
    if session and session.get("topic_id"):
        selected = dict(
            selected, topic_id=session["topic_id"], session_id=session["id"]
        )
    sources = {"Sem vínculo a estudo": None}
    rows = app.store.sessions(app.plan, limit=1000)
    for index, row in enumerate(rows, 1):
        label = f"{index}. {row['day']} · {row['category']} · {row['subject'] or row['mock_name'] or 'Simulado'}"
        sources[label] = row["id"]
    if selected.get("session_id") and selected["session_id"] not in sources.values():
        sources["Estudo de origem preservado"] = selected["session_id"]
    fields = [
        ("topic", "Assunto", "choice", list(topics)),
        ("session", "Estudo ou simulado de origem (opcional)", "choice", list(sources)),
        ("description", "Descrição do erro ou dificuldade", "text"),
        ("why", "Por que errei?", "text"),
        ("remember", "O que preciso lembrar?", "text"),
        ("source", "Fonte ou referência (opcional)", "entry"),
    ]

    def save(values):
        engine.save_difficulty(
            app.plan,
            topics.get(values["topic"]),
            values["description"],
            values["why"],
            values["remember"],
            source=values["source"],
            session_id=sources.get(values["session"]),
            difficulty_id=selected.get("id"),
        )
        app.notify("Dificuldade salva. A prática não gera um estudo duplicado.")

    initial = dict(
        selected,
        topic=app.label_for(topics, selected.get("topic_id")),
        session=next(
            (k for k, v in sources.items() if v == selected.get("session_id")),
            "Sem vínculo a estudo",
        ),
    )
    return form_class()(
        app,
        "Editar dificuldade" if difficulty else "Registrar dificuldade",
        fields,
        save,
        initial,
    )


def difficulty_list(app):
    from app import messagebox

    window = tk.Toplevel(app.root)
    window.title("Dificuldades e revanche · RUMO")
    window.geometry("980x580")
    panel = Panel(window, app)
    panel.pack(fill="both", expand=True, padx=16, pady=16)
    rows = app.store.rpg.difficulties(app.plan)
    mapping = {r["id"]: r for r in rows}
    with app.in_panel(panel):
        app.note(
            "Não inferimos conceitos a partir de totais de erros. Descreva a dificuldade e escolha como praticar."
        )
        tree = app.table(
            [
                ("subject", "Matéria", 160),
                ("topic", "Assunto", 220),
                ("description", "Dificuldade", 320),
                ("state", "Estado", 170),
            ],
            [
                (r["id"], [r["subject"], r["topic"], r["description"], r["state"]])
                for r in rows
            ],
            height=10,
        )

        def selected():
            return mapping[app.selected(tree)]

        def refresh():
            window.destroy()
            difficulty_list(app)

        def details():
            row = selected()
            evidence = app.store.rpg.difficulty_evidence(row["id"])
            suggestion = (
                "\nVocê pode avaliar marcar como superada."
                if evidence["suggest_overcome"]
                else "\nAinda não há encontros separados suficientes para sugerir superação."
            )
            messagebox.showinfo(
                "Dificuldade e evidências",
                f"{row['description']}\n\nPor que errei: {row['why']}\nO que lembrar: {row['remember']}\nFonte: {row['source'] or 'Não informada'}\n\n{evidence['separate_days']} datas de prática.\n{evidence['explanation']}"
                + suggestion,
                parent=window,
            )

        def start():
            mission = app.store.rpg.revenge_mission(selected()["id"])
            app.clock_setup(app.store.rpg.mission_fields(mission["id"]))

        def state(value):
            row = selected()
            if messagebox.askyesno(
                "Avaliação do usuário",
                f"Marcar esta dificuldade como '{value}'? Esta é uma decisão sua, não uma comprovação objetiva de domínio.",
                parent=window,
            ):
                app.store.rpg.set_difficulty_state(row["id"], value)
                refresh()

        app.toolbar(
            [
                ("Nova dificuldade", lambda: difficulty_form(app)),
                ("Editar", lambda: difficulty_form(app, selected())),
                ("Detalhes e evidências", details),
                ("Começar revanche", start),
                ("Em prática", lambda: state("Em prática")),
                ("Superada por mim", lambda: state("Superada pelo usuário")),
                ("Reabrir", lambda: state("Aberta")),
                ("Atualizar lista", refresh),
            ]
        )
    return window


def challenge_form(app, kind="Masmorra"):
    rows = app.store.rows(
        "SELECT DISTINCT t.id,t.name,s.name subject FROM topics t JOIN subjects s ON s.id=t.subject_id JOIN sessions a ON a.topic_id=t.id WHERE s.plan_id=? AND t.archived=0 AND (a.elapsed>0 OR a.correct+a.wrong>0) ORDER BY s.name,t.name",
        (app.plan,),
    )
    mapping = {
        f"{index}. {r['subject']} · {r['name']}": r["id"]
        for index, r in enumerate(rows, 1)
    }
    fields = [
        ("name", "Nome do desafio", "entry"),
        ("kind", "Tipo", "choice", ["Masmorra", "Chefe"]),
        ("topics", "Assuntos estudados (use o seletor abaixo)", "text"),
        ("questions", "Quantidade de questões", "entry"),
        ("minutes", "Tempo sugerido em minutos (opcional)", "entry"),
        ("source", "Origem do material ou plataforma externa", "entry"),
    ]

    def save(values):
        labels = [
            line.strip() for line in values["topics"].splitlines() if line.strip()
        ]
        if any(label not in mapping for label in labels):
            raise ValueError(
                "Escolha os assuntos pelo seletor; cada linha deve conter um assunto listado."
            )
        minutes = int(values["minutes"]) if values["minutes"].strip() else None
        cid = app.store.rpg.create_challenge(
            app.plan,
            values["name"],
            [mapping[label] for label in labels],
            int(values["questions"]),
            time_limit=minutes * 60 if minutes is not None else None,
            source=values["source"],
            kind=values["kind"],
        )
        app.notify("Desafio criado. Registre as questões feitas no seu material.")

    form = form_class()(
        app,
        "Criar masmorra ou chefe",
        fields,
        save,
        {"kind": kind, "questions": "20", "minutes": ""},
    )

    if not mapping:
        form.error.configure(
            text="Registre primeiro um estudo em um assunto. Depois ele aparecerá no seletor de desafios."
        )
        form.save_button.configure(state="disabled")

    def set_topics(value):
        form.widgets["topics"].delete("1.0", "end")
        form.widgets["topics"].insert("1.0", value)

    def select_topics():
        win = tk.Toplevel(form.win)
        win.title("Selecione assuntos já estudados")
        win.geometry("850x480")
        body = ttk.Frame(win, padding=16)
        body.pack(fill="both", expand=True)
        search = tk.StringVar()
        ttk.Label(
            body,
            text="Buscar matéria ou assunto; Ctrl/Cmd e Shift permitem seleção múltipla.",
        ).pack(anchor="w")
        entry = ttk.Entry(body, textvariable=search)
        entry.pack(fill="x", pady=8)
        tree = ttk.Treeview(
            body, columns=("name",), show="headings", selectmode="extended", height=12
        )
        tree.heading("name", text="Matéria · assunto já estudado")
        tree.column("name", width=740)
        tree.pack(fill="both", expand=True)
        selections = {
            line.strip()
            for line in form.widgets["topics"].get("1.0", "end").splitlines()
            if line.strip() in mapping
        }
        visible = {}

        def filter_list(*args):
            selections.difference_update(visible.values())
            selections.update(visible[key] for key in tree.selection())
            tree.delete(*tree.get_children())
            visible.clear()
            for label in mapping:
                if search.get().casefold() not in label.casefold():
                    continue
                key = str(len(visible))
                visible[key] = label
                tree.insert("", "end", iid=key, values=[label])
                if label in selections:
                    tree.selection_add(key)

        def apply():
            selections.difference_update(visible.values())
            selections.update(visible[key] for key in tree.selection())
            set_topics("\n".join(label for label in mapping if label in selections))
            win.destroy()

        trace_owned(win, search, filter_list)
        filter_list()
        MotionButton(body, text="Usar assuntos selecionados", command=apply).pack(
            anchor="e", pady=12
        )
        entry.focus_set()

    MotionButton(
        form.body, text="Escolher assuntos estudados", command=select_topics
    ).grid(row=len(fields) + 2, column=0, columnspan=2, sticky="w", pady=10)
    return form


def challenge_list(app):
    window = tk.Toplevel(app.root)
    window.title("Masmorras e chefes · RUMO")
    window.geometry("950x520")
    panel = Panel(window, app)
    panel.pack(fill="both", expand=True, padx=16, pady=16)
    rows = app.store.rpg.challenges(app.plan)
    mapping = {r["id"]: r for r in rows}
    with app.in_panel(panel):
        app.note(
            "Faça as questões no seu material ou plataforma externa. Sessões e simulados são registrados uma única vez. Exceder o tempo sugerido não reduz recompensas."
        )
        tree = app.table(
            [
                ("name", "Nome", 250),
                ("kind", "Tipo", 100),
                ("progress", "Questões registradas", 150),
                ("time", "Tempo líquido", 150),
                ("source", "Material", 240),
            ],
            [
                (
                    r["id"],
                    [
                        r["name"],
                        r["kind"],
                        f"{r['total']}/{r['questions']}",
                        duration(r["elapsed"]),
                        r["source"],
                    ],
                )
                for r in rows
            ],
            height=9,
        )

        def begin():
            row = mapping[app.selected(tree)]
            fields = app.store.rpg.challenge_fields(row["id"])
            if row["kind"] == "Chefe":
                app.session_form(fields)
            else:
                app.clock_setup(fields)

        app.toolbar(
            [
                ("Novo desafio", lambda: challenge_form(app)),
                ("Registrar ou começar", begin),
                ("Atualizar lista", lambda: (window.destroy(), challenge_list(app))),
            ]
        )
    return window


def start_challenge(app, challenge_id):
    fields = app.store.rpg.challenge_fields(challenge_id)
    if fields["category"] == "Simulado":
        app.session_form(fields)
    else:
        app.clock_setup(fields)


def retroactive_preview(app):
    from app import messagebox

    preview = app.store.rpg.retroactive_preview(app.plan)
    rows = preview["sessions"]
    if not rows:
        messagebox.showinfo(
            "Histórico",
            "Todos os estudos deste plano já estão incluídos. Nenhuma recompensa foi duplicada.",
            parent=app.root,
        )
        return
    win = tk.Toplevel(app.root)
    win.title("Prévia: importar recompensas do histórico")
    win.geometry("920x560")
    panel = Panel(win, app)
    panel.pack(fill="both", expand=True, padx=16, pady=16)
    with app.in_panel(panel):
        app.note(
            f"Optativo: {len(rows)} estudos podem render {preview['xp']} XP e {preview['coins']} moedas de tempo líquido. Revisões e desafios antigos não recebem bônus automaticamente. Revise os registros antes de confirmar."
        )
        subject_names = {
            r["id"]: r["name"]
            for r in app.store.rows(
                "SELECT id,name FROM subjects WHERE plan_id=?", (app.plan,)
            )
        }
        app.table(
            [
                ("day", "Data", 130),
                ("subject", "Matéria", 250),
                ("elapsed", "Tempo líquido", 150),
                ("xp", "XP previsto", 100),
            ],
            [
                (
                    r["id"],
                    [
                        r["day"],
                        subject_names.get(r["subject_id"], "Simulado geral"),
                        duration(r["elapsed"]),
                        r["elapsed"] // 60,
                    ],
                )
                for r in rows
            ],
            height=12,
        )

        def apply():
            if messagebox.askyesno(
                "Confirmar inclusão explícita",
                f"Incluir os {len(rows)} estudos desta prévia? Os registros originais permanecem iguais; esta ação optativa também pode desbloquear marcos decorativos.",
                parent=win,
            ):
                app.store.rpg.enroll_history(app.plan, [r["id"] for r in rows])
                win.destroy()
                app.refresh()
                app.notify(
                    "Histórico incluído, sem duplicar tempo, questões ou recompensas."
                )

        MotionButton(
            panel.body,
            text="Confirmar inclusão dos registros da prévia",
            command=apply,
        ).pack(anchor="e", pady=12)
    return win


def purchase_preview(app, item_id):
    from app import messagebox

    item = next(row for row in app.store.rpg.catalog(app.plan) if row["id"] == item_id)
    win = tk.Toplevel(app.root)
    win.title("Equipamento · " + item["name"])
    win.geometry("520x660")
    win.minsize(480, 560)
    panel = Panel(win, app)
    panel.pack(fill="both", expand=True, padx=16, pady=16)
    ttk.Label(panel.body, text=item["name"], style="PanelHeading.TLabel").pack(
        anchor="w"
    )
    ttk.Label(
        panel.body, text=item["preview"], style="PanelMuted.TLabel", wraplength=420
    ).pack(anchor="w", pady=8)
    equipped = {
        row["id"]
        for row in app.store.rpg.catalog(app.plan)
        if row["equipped"] and row["slot"] != item["slot"]
    }
    equipped.add(item_id)
    if item["slot"] in ("Título", "Moldura", "Insígnia"):
        color = app.motion.palette["accent"] if item_id == "dourada" else app.border
        preview = tk.Frame(
            panel.body, bg=app.surface, highlightthickness=2, highlightbackground=color
        )
        preview.pack(fill="x", pady=16)
        ttk.Label(preview, text=item["name"], style="PanelHeading.TLabel").pack(
            padx=18, pady=20
        )
    else:
        CharacterView(
            panel.body,
            app,
            equipped=equipped,
            backdrop=app.store.pref("rpg_effects", True),
        ).pack(fill="both", expand=True)
    ttk.Label(
        panel.body,
        text=item["requirement"] + ". Sem multiplicadores de XP ou notas.",
        wraplength=420,
    ).pack(anchor="w", pady=8)

    def purchase():
        if not item["owned"]:
            if not messagebox.askyesno(
                "Compra decorativa",
                f"Comprar {item['name']} por {item['price']} moedas virtuais?",
                parent=win,
            ):
                return
            app.store.rpg.buy(app.plan, item_id)
        app.store.rpg.equip(app.plan, item_id)
        win.destroy()
        app.refresh()
        app.notify("Item equipado. Use seu atalho de estudo na prévia do inventário.")

    MotionButton(
        panel.body,
        text=(
            "Equipar"
            if item["owned"]
            else (
                "Recompensa ainda bloqueada"
                if item["acquisition"] == "reward"
                else "Comprar e equipar"
            )
        ),
        state=(
            "normal"
            if item["owned"]
            or (
                item["acquisition"] == "shop"
                and item["available"]
                and item["affordable"]
            )
            else "disabled"
        ),
        command=purchase,
    ).pack(anchor="e", pady=8)
    if item["owned"]:

        def use():
            app.store.rpg.equip(app.plan, item_id)
            action = app.store.rpg.equipment_action(app.plan, item_id)
            win.destroy()
            app.refresh()
            study_action(app, action, item_id=item_id)

        MotionButton(panel.body, text=ACTION_LABELS[item["action"]], command=use).pack(
            anchor="e", pady=(0, 8)
        )
        if item["equipped"]:

            def put_away():
                app.journey.toggle_equipment(app.plan, item_id)
                win.destroy()
                app.refresh()

            MotionButton(panel.body, text="Guardar equipamento", command=put_away).pack(
                anchor="e"
            )
    return win


ACTION_LABELS = {
    "small": "Missão de cinco minutos",
    "focus": "Preparar foco de quinze minutos",
    "resume": "Retomar missão",
    "practice": "Praticar questões",
    "review": "Preparar revisão",
    "recall": "Lembrar antes de ler",
    "revenge": "Preparar revanche",
    "route": "Preparar rota",
    "challenge": "Preparar masmorra",
    "boss": "Preparar chefe",
    "notes": "Escrever no caderno",
}


def study_action(app, action, item_id=None):
    """Gear/class purpose opens existing study flows; nothing is recorded on click."""
    if action not in ACTION_LABELS:
        raise ValueError("Ação de equipamento inválida.")
    if action == "notes":
        rows = app.store.rows(
            "SELECT DISTINCT t.id,t.name,s.name subject FROM topics t JOIN subjects s ON s.id=t.subject_id "
            "JOIN sessions a ON a.topic_id=t.id JOIN rpg_sources e ON e.session_id=a.id "
            "WHERE s.plan_id=? AND t.archived=0 AND s.archived=0 AND (a.elapsed>0 OR a.correct+a.wrong>0) ORDER BY s.name,t.name",
            (app.plan,),
        )
        if not rows:
            app.notify("Registre um estudo para começar o caderno do Erudito.")
            return
        mapping = {
            f"{i}. {row['subject']} · {row['name']}": row
            for i, row in enumerate(rows, 1)
        }

        def open_notebook(values):
            def saved():
                app.store.rpg.sync()
                app.refresh()

            return app.topic_notes(mapping[values["topic"]], on_save=saved)

        form = form_class()(
            app,
            "Caderno do Erudito",
            [("topic", "Assunto estudado", "choice", list(mapping))],
            open_notebook,
            {"topic": next(iter(mapping))},
        )
        form.refresh_on_submit = False
        return form
    if action == "revenge":
        return difficulty_list(app)
    if action in ("challenge", "boss"):
        return challenge_form(app, "Chefe" if action == "boss" else "Masmorra")
    if action == "route":
        win = tk.Toplevel(app.root)
        win.title("Rota de estudo · RUMO")
        win.geometry("640x440")
        win.configure(bg=app.bg)
        panel = Panel(win, app)
        panel.pack(fill="both", expand=True, padx=16, pady=16)
        ttk.Label(
            panel.body, text="Uma atividade de cada vez", style="PanelHeading.TLabel"
        ).pack(anchor="w")
        ttk.Label(
            panel.body,
            text="Sua montaria acompanha a jornada. Escolha o próximo passo; pausas e retomadas continuam no seu ritmo.",
            style="PanelMuted.TLabel",
            wraplength=550,
        ).pack(anchor="w", pady=(8, 16))
        from rpg_schema import CATALOG

        steps = CATALOG.get(item_id, {}).get("route_steps", 4)
        route = [
            ("Próxima missão", "resume"),
            ("Revisão pendente", "review"),
            ("Dificuldade e revanche", "revenge"),
            ("Preparar desafio", "challenge"),
        ]
        for label, next_action in route[:steps]:

            def begin(a=next_action):
                win.destroy()
                study_action(app, a)

            MotionButton(panel.body, text=label, command=begin).pack(fill="x", pady=4)
        app.motion.reveal(win)
        return win
    if action in ("small", "focus", "resume"):
        mission = app.journey.mission(app.plan)
        if mission and not mission.completed:
            minutes = {"small": 5, "focus": 15, "resume": None}[action]
            fields = app.journey.mission_fields(app.plan, mission, minutes)
            return app.clock_setup(fields)
    if action in ("review", "recall"):
        pending = app.store.one(
            "SELECT r.id FROM reviews r JOIN topics t ON t.id=r.topic_id JOIN subjects s ON s.id=t.subject_id WHERE s.plan_id=? AND r.state='Pendente' AND t.archived=0 AND s.archived=0 ORDER BY r.due,r.id LIMIT 1",
            (app.plan,),
        )
        if pending:
            if action == "recall":
                app.notify(
                    "Tente explicar a ideia antes de consultar. Ao salvar, registre sua percepção de lembrança."
                )
            return app.clock_setup(app.store.rpg.review_fields(pending["id"]))
    rows = app.store.rows(
        "SELECT t.id,t.name,s.id subject_id,s.name subject FROM topics t JOIN subjects s ON s.id=t.subject_id WHERE s.plan_id=? AND t.archived=0 AND s.archived=0 AND NOT EXISTS(SELECT 1 FROM topics c WHERE c.parent_id=t.id AND c.archived=0) ORDER BY s.name,t.rowid",
        (app.plan,),
    )
    if not rows:
        app.notify("Cadastre uma matéria e um assunto para preparar seu estudo.")
        return
    mapping = {
        f"{index}. {r['subject']} · {r['name']}": r for index, r in enumerate(rows, 1)
    }

    def prepare(values):
        row = mapping[values["topic"]]
        category = (
            "Questões"
            if action == "practice"
            else "Revisão" if action in ("recall", "review") else "Teoria"
        )
        minutes = 5 if action == "small" else 10 if action == "practice" else 15
        app.clock_setup(
            dict(
                plan_id=app.plan,
                subject_id=row["subject_id"],
                topic_id=row["id"],
                category=category,
                target=minutes * 60,
                mode="Timer",
            )
        )

    form = form_class()(
        app,
        ACTION_LABELS[action],
        [("topic", "Assunto do seu plano", "choice", list(mapping))],
        prepare,
        {"topic": next(iter(mapping))},
    )
    form.refresh_on_submit = False
    if action == "recall":
        form.error.configure(
            text="Tente lembrar antes de consultar; ao salvar a sessão, escolha Lembrei, Parcial ou Não lembrei.",
            foreground=app.motion.palette["muted"],
        )
    return form


def start_mission(app, mission, reduced=False):
    """Adjustable hard-day task, preserving canonical mission and cycle."""

    def begin(minutes=None):
        fields = app.journey.mission_fields(app.plan, mission, minutes)
        app.focus_context = dict(
            subject=mission.subject,
            topic=mission.topic,
            reduced=(ReducedMission(minutes=minutes, questions=0) if minutes else None),
        )
        return app.clock_setup(fields)

    if reduced:

        def save(values):
            minutes = int(values["minutes"])
            if not 1 <= minutes <= 180:
                raise ValueError("Escolha de 1 a 180 minutos.")
            begin(minutes)

        return form_class()(
            app,
            "Hoje está difícil",
            [("minutes", "Tarefa pequena em minutos (1–180)", "entry")],
            save,
            {"minutes": app.journey.reduced(mission).minutes},
        )
    return begin()


def rename_character(app):
    return form_class()(
        app,
        "Nome do personagem",
        [("name", "Nome local (até 60 caracteres)", "entry")],
        lambda values: app.store.rpg.rename_character(app.plan, values["name"]),
        {"name": app.store.rpg.profile(app.plan)["name"]},
    )
