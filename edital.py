"""Edital: a lazy subject/topic tree on the left, the selected topic on the right.

Selecting, completing and annotating update existing widgets; the tree is never
rebuilt for those actions, so scroll position, selection and focus stay put.
Official numbering stays in the names; the learning order only sorts siblings.
"""

import tkinter as tk
from tkinter import ttk
import unicodedata

from components import CompletionBox
from core import ratio
from theme import percent
from ui import MotionButton, ProgressBar, blend
from ui_kit import (
    ActionMenu,
    Card,
    empty,
    icon_label,
    label,
    placeholder,
    stat_row,
    wrapping,
)

HELP = (
    "Cada assunto final conta uma vez. Matérias e tópicos com filhos mostram o "
    "progresso somado. A busca não altera a porcentagem.\n\n"
    "Ordem: dentro de cada matéria, os assuntos aparecem na sequência sugerida "
    "(fundamentos, aplicação, aprofundamento). A numeração original do edital "
    "continua no nome de cada item; você pode estudar qualquer um.\n\n"
    "Os itens originais do BACEN mantêm o texto do edital de abertura de 2024. "
    "Subassuntos marcados como “Guia de estudo” são um desdobramento pedagógico, "
    "não texto oficial nem garantia de exaustividade. O PDF não foi alterado.\n\n"
    "Ao detalhar um item já concluído, os novos subassuntos herdam a conclusão. "
    "O histórico continua ligado ao item original e é somado aos filhos.\n\n"
    "Referências: edital BACEN, dev.java/learn, docs.python.org/3/tutorial, "
    "postgresql.org/docs/current/tutorial.html, legislação no Planalto e Cosif/BCB."
)


def normalized(text):
    return "".join(
        c
        for c in unicodedata.normalize("NFD", text.casefold())
        if not unicodedata.combining(c)
    )


def load_topics(app):
    store = app.store
    topics = store.rows(
        """SELECT t.*,COALESCE(a.correct,0) correct,COALESCE(a.wrong,0) wrong,
        COALESCE(a.blank,0) blank,a.last,COALESCE(a.n,0) n,COALESCE(r.n,0) pending FROM topics t
        JOIN subjects d ON d.id=t.subject_id LEFT JOIN
        (SELECT topic_id,SUM(correct) correct,SUM(wrong) wrong,SUM(blank) blank,MAX(day) last,COUNT(*) n FROM sessions GROUP BY topic_id) a ON a.topic_id=t.id
        LEFT JOIN (SELECT topic_id,COUNT(*) n FROM reviews WHERE state='Pendente' GROUP BY topic_id) r ON r.topic_id=t.id
        WHERE d.plan_id=? AND d.archived=0 AND t.archived=0 ORDER BY t.rowid""",
        (app.plan,),
    )
    from learning import ordered

    names = {
        s["id"]: s["name"]
        for s in store.rows("SELECT id,name FROM subjects WHERE plan_id=?", (app.plan,))
    }
    if store.pref("syllabus_order", "Aprendizagem") == "Aprendizagem":
        topics = ordered(topics, names)
    return topics


def render_edital(app, tooltip, dialogs):
    store = app.store
    parent = app.content
    palette = app.motion.palette
    progress = store.progress(app.plan)

    # Top bar: overall progress, the add action and the administrative menu.
    bar = tk.Frame(parent, bg=app.bg)
    bar.pack(fill="x", pady=(0, 14))
    summary = tk.Frame(bar, bg=app.bg)
    summary.pack(side="left")
    progress_percent = label(summary, app, "", size=15, weight="bold")
    progress_percent.pack(side="left")
    progress_count = label(summary, app, "", size=10, tone="muted")
    progress_count.pack(side="left", padx=(10, 14))
    progress_bar = ProgressBar(summary, app, 0, height=4)
    progress_bar.configure(width=180)
    progress_bar.pack(side="left")

    def show_progress(current):
        value = 100 * current["done"] / current["total"] if current["total"] else 0
        progress_percent.configure(text=f"{value:.0f}%")
        progress_count.configure(
            text=f"{current['done']} de {current['total']} assuntos concluídos"
        )
        progress_bar.value = value
        progress_bar.draw()

    show_progress(progress)
    ActionMenu(
        bar,
        app,
        [
            ("Importar edital", app.import_edital),
            ("Gerenciar matérias e planos", app.manage_entities),
            ("Fontes e cobertura", app.syllabus_audit),
            None,
            ("Área BACEN 2024", app.load_bacen),
            ("PDF e referência do edital", app.open_bacen),
            None,
            (
                "Como o progresso e a ordem funcionam",
                lambda: dialogs.showinfo("Conteúdo e progresso", HELP, parent=app.root),
            ),
        ],
        text="Gerenciar",
        icon="sliders-horizontal",
    ).pack(side="right")
    MotionButton(bar, text="Novo assunto", icon="plus", command=app.topic_form).pack(
        side="right", padx=(0, 8)
    )

    split = tk.Frame(parent, bg=app.bg)
    split.pack(fill="both", expand=True)
    split.columnconfigure(0, weight=3, uniform="split")
    split.columnconfigure(1, weight=2, uniform="split", minsize=300)
    split.rowconfigure(0, weight=1)

    # Left: search and the tree, on one quiet surface with its own scroll.
    left_card = Card(split, app, padding=(4, 4), stretch=True)
    left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
    left = left_card.body
    searchrow = tk.Frame(left, bg=app.surface)
    searchrow.pack(fill="x", padx=14, pady=(14, 8))
    icon_label(
        searchrow, app, "search", size=11, tone="faint", bg=palette["raised"]
    ).pack(side="left", ipadx=8, ipady=8)
    search = tk.StringVar(value=app.edital_search)
    entry = ttk.Entry(searchrow, textvariable=search, style="Field.TEntry")
    entry.pack(side="left", fill="x", expand=True)
    app.edital_search_entry = entry
    hint = placeholder(entry, app, "Buscar assunto ou matéria")
    from app import Scroll

    tree_scroll = Scroll(left, style="Panel.TFrame")
    tree_scroll.pack(fill="both", expand=True, padx=(6, 4), pady=(0, 8))
    app.edital_scroll = tree_scroll
    host = tree_scroll.body

    # Right: details of the selected topic.
    detail_card = Card(split, app, padding=(24, 22), stretch=True)
    detail_card.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
    detail = detail_card.body

    topics = load_topics(app)
    mapping = {t["id"]: t for t in topics}
    children = {}
    by_subject = {}
    for topic in topics:
        children.setdefault(topic["parent_id"], []).append(topic)
        by_subject.setdefault(topic["subject_id"], []).append(topic)
    visited = set()

    def aggregate(topic):
        if topic["id"] in visited:
            return
        visited.add(topic["id"])
        descendants = children.get(topic["id"], [])
        for child in descendants:
            aggregate(child)
            for key in ["correct", "wrong", "blank", "n", "pending"]:
                topic[key] += child[key]
            topic["last"] = max(topic["last"] or "", child["last"] or "") or None
        topic["total"] = sum(x["total"] for x in descendants) if descendants else 1
        topic["completed"] = (
            sum(x["completed"] for x in descendants)
            if descendants
            else int(topic["done"])
        )

    for topic in topics:
        aggregate(topic)
    guide_ids = set(store.pref("bacen_guide_ids", []))
    evidence = store.pref("bacen_topic_sources", {})
    from learning import subject_key

    subjects = sorted(
        store.rows(
            "SELECT * FROM subjects WHERE plan_id=? AND archived=0", (app.plan,)
        ),
        key=lambda s: subject_key(s["name"]),
    )
    subject_names = {s["id"]: s["name"] for s in subjects}
    rendered = {}
    controls = {}
    subject_metrics = {}
    views = {}
    app.edital_rows = rendered
    app.edital_mapping = mapping
    app.edital_branch_buttons = {}
    limit = [100]
    pending_reveal = [None]

    def chosen():
        topic = mapping.get(app.edital_selected)
        if not topic:
            raise ValueError("Selecione um assunto na lista.")
        return topic

    def completion(t):
        descendants = children.get(t["id"], [])
        t["completed"] = (
            sum(completion(c) for c in descendants) if descendants else int(t["done"])
        )
        return t["completed"]

    def toggle_done(topic=None):
        topic = topic or chosen()
        if children.get(topic["id"]):
            raise ValueError("Abra o tópico e marque seus subassuntos individualmente.")
        done = not topic["done"]
        store.save("topics", {"id": topic["id"], "done": done})
        topic["done"] = done
        # Update completion only; rows stay alive so the viewport stays in place.
        for t in topics:
            if t["parent_id"] not in mapping:
                completion(t)
        show_progress(store.progress(app.plan))
        if topic["id"] in controls:
            control = controls[topic["id"]]
            if isinstance(control, CompletionBox):
                control.configure(text="✓" if topic["done"] else "□")
        for tid, (row, marker, labels) in rendered.items():
            text = detail_text(mapping[tid])
            if labels[-1].cget("text") != text:
                labels[-1].configure(text=text)
        for sid, (metric, sbar, roots) in subject_metrics.items():
            total = sum(t["total"] for t in roots)
            done_count = sum(t["completed"] for t in roots)
            metric.configure(text=f"{done_count}/{total}")
            if sbar:
                sbar.value = 100 * done_count / total if total else 0
                sbar.draw()
        if app.edital_selected in mapping:
            show_detail(mapping[app.edital_selected])

    def paint_selected(tid, hover=False):
        if tid not in rendered:
            return
        row, marker, labels = rendered[tid]
        selected = tid == app.edital_selected
        if not row.winfo_exists():
            return
        color = (
            palette["selected"]
            if selected
            else palette["hover"] if hover else app.surface
        )
        if getattr(row, "_target_color", None) == color:
            return
        row._target_color = color
        start = row.cget("bg")

        def paint(t):
            current = blend(start, color, t)
            row.configure(bg=current)
            marker.configure(bg=current)
            for item in labels:
                item.configure(bg=current)
            for button in row._buttons:
                button.surround = current
                button.configure(bg=current)
                if button.role == "Ghost.TButton" and not button.hover:
                    button.current = current
                button.draw()

        app.motion.animate(row, paint, 200, channel="row-hover")

    def select(topic):
        previous = app.edital_selected
        app.edital_selected = topic["id"]
        paint_selected(previous)
        paint_selected(topic["id"])
        show_detail(topic)

    def clear_branch(container):
        prefix = str(container) + "."
        for tid in list(rendered):
            if str(rendered[tid][0]).startswith(prefix):
                rendered.pop(tid)
                controls.pop(tid, None)
                views.pop(tid, None)
                app.edital_branch_buttons.pop(tid, None)
        for widget in container.winfo_children():
            widget.destroy()

    def show_branch(key):
        view = views[key]
        view["host"].pack(fill="x", after=view["after"])
        for topic in view["items"]:
            topic_row(view["host"], topic, view["depth"])

    def expand(key):
        view = views.get(key)
        if not view:
            return
        view["open"] = not view["open"]
        if view["open"]:
            app.edital_expanded.add(key)
            show_branch(key)
        else:
            app.edital_expanded.discard(key)
            clear_branch(view["host"])
            view["host"].pack_forget()
        view["button"].configure(
            icon="chevron-down" if view["open"] else "chevron-right"
        )

    def activate(topic):
        select(topic)
        if not children.get(topic["id"]):
            return
        if not search.get().strip():
            expand(topic["id"])
            return
        # Search results are flat. Reveal the original hierarchy when a matched
        # parent is clicked, instead of silently doing nothing or duplicating rows.
        app.edital_expanded.add("s" + topic["subject_id"])
        current = topic
        while current:
            app.edital_expanded.add(current["id"])
            current = mapping.get(current["parent_id"])
        pending_reveal[0] = topic["id"]
        search.set("")
        select(topic)

    def detail_text(topic):
        tid = topic["id"]
        details = []
        if children.get(tid):
            details.append(f"{topic['completed']}/{topic['total']} concluídos")
        elif tid in guide_ids:
            details.append("Guia de estudo")
            if search.get().strip() and topic["parent_id"] in mapping:
                details.append("Item oficial: " + mapping[topic["parent_id"]]["name"])
        if topic["n"]:
            answered = topic["correct"] + topic["wrong"]
            if answered:
                details.append(
                    f"{percent(ratio(topic['correct'], topic['wrong']), 1)} em {answered} questões"
                )
            details.append("estudado em " + str(topic["last"]))
        if topic["pending"]:
            details.append(
                f"{topic['pending']} {'revisão pendente' if topic['pending'] == 1 else 'revisões pendentes'}"
            )
        if topic.get("notes"):
            details.append("✎ " + topic["notes"].replace("\n", " ")[:90])
        return "  ·  ".join(details)

    def update_notes():
        fresh = store.one("SELECT notes FROM topics WHERE id=?", (app.edital_selected,))
        if fresh and app.edital_selected in mapping:
            mapping[app.edital_selected]["notes"] = fresh["notes"]
        for tid, (row, marker, labels) in rendered.items():
            labels[-1].configure(text=detail_text(mapping[tid]))
        if app.edital_selected in mapping:
            show_detail(mapping[app.edital_selected])

    def show_detail(topic):
        for widget in detail.winfo_children():
            widget.destroy()
        if topic is None:
            empty(
                detail,
                app,
                "book-open",
                "Escolha um assunto",
                "Selecione um item da lista para ver o progresso, as observações e os materiais, e para começar a estudá-lo.",
            ).pack(fill="x", pady=(40, 0))
            label(
                detail,
                app,
                "Dica: clique duas vezes num assunto para registrar um estudo.",
                size=9,
                tone="faint",
                anchor="center",
            ).pack(fill="x", pady=(18, 0))
            return
        branch = bool(children.get(topic["id"]))
        trail = [subject_names.get(topic["subject_id"], "")]
        ancestor = mapping.get(topic["parent_id"])
        if ancestor:
            trail.append(ancestor["name"])
        wrapping(label(detail, app, "  ›  ".join(trail), size=9, tone="muted")).pack(
            fill="x"
        )
        wrapping(label(detail, app, topic["name"], size=15, weight="bold")).pack(
            fill="x", pady=(6, 0)
        )
        state = (
            f"{topic['completed']} de {topic['total']} subassuntos concluídos"
            if branch
            else (
                "Teoria concluída"
                if topic["done"]
                else ("Em estudo" if topic["n"] else "Ainda não estudado")
            )
        )
        tags = [state]
        if topic["id"] in guide_ids:
            tags.append("guia de estudo, não texto oficial")
        label(
            detail,
            app,
            "  ·  ".join(tags),
            size=10,
            tone="accent" if topic["done"] and not branch else "muted",
        ).pack(anchor="w", pady=(6, 0))
        if branch:
            ProgressBar(
                detail, app, 100 * topic["completed"] / topic["total"], height=4
            ).pack(fill="x", pady=(10, 0))
        if topic["n"]:
            answered = topic["correct"] + topic["wrong"]
            stats = [(str(topic["n"]), "estudos")]
            if answered:
                stats.append(
                    (
                        percent(ratio(topic["correct"], topic["wrong"]), 1),
                        f"em {answered} questões",
                    )
                )
            stats.append(
                (str(topic["last"])[8:10] + "/" + str(topic["last"])[5:7], "último")
            )
            stat_row(detail, app, stats, gap=22).pack(anchor="w", pady=(18, 0))
        if topic["pending"]:
            label(
                detail,
                app,
                f"{topic['pending']} {'revisão pendente' if topic['pending'] == 1 else 'revisões pendentes'} neste assunto",
                size=9,
                tone="warning",
            ).pack(anchor="w", pady=(12, 0))
        extra = []
        if "11.813/2013" in topic["name"]:
            extra.append("Retificação oficial: leia Lei 12.813/2013.")
        if topic["id"] in evidence:
            source = evidence[topic["id"]]
            extra.append(f"Cobrado em {source['exam']} (itens {source['questions']}).")
        for line in extra:
            wrapping(label(detail, app, line, size=9, tone="muted")).pack(
                fill="x", pady=(8, 0)
            )
        label(detail, app, "Observações", size=10, weight="bold").pack(
            anchor="w", pady=(22, 4)
        )
        notes = (topic.get("notes") or "").strip()
        wrapping(
            label(
                detail,
                app,
                notes or "Sem observações. Anote dúvidas, macetes e onde parou.",
                size=10,
                tone="fg" if notes else "faint",
            )
        ).pack(fill="x")
        MotionButton(
            detail,
            text="Editar observações" if notes else "Escrever observações",
            icon="pencil",
            style="Ghost.TButton",
            height=30,
            command=lambda: app.topic_notes(topic, update_notes),
        ).pack(anchor="w", pady=(6, 0))
        actions = tk.Frame(detail, bg=app.surface)
        actions.pack(side="bottom", fill="x", pady=(18, 0))
        start = {"subject_id": topic["subject_id"], "topic_id": topic["id"]}
        MotionButton(
            actions,
            text="Estudar agora",
            icon="play",
            style="Accent.TButton",
            height=40,
            command=lambda: app.clock_setup(dict(start)),
        ).pack(side="left")
        MotionButton(
            actions,
            text="Registrar estudo",
            icon="plus",
            height=40,
            command=lambda: app.session_form(dict(start)),
        ).pack(side="left", padx=(8, 0))
        menu = [
            ("Materiais e links", lambda: app.materials(topic)),
            ("Editar assunto", lambda: app.topic_form(topic)),
            None,
            ("Arquivar assunto", lambda: app.archive_topic(topic), "danger"),
        ]
        if not branch:
            menu.insert(
                0,
                (
                    (
                        "Reabrir teoria"
                        if topic["done"]
                        else "Marcar teoria como concluída"
                    ),
                    lambda: toggle_done(topic),
                ),
            )
        ActionMenu(actions, app, menu, height=40).pack(side="right")

    def topic_row(container, topic, depth):
        tid = topic["id"]
        branches = children.get(tid, [])
        row = tk.Frame(container, bg=app.surface)
        row.pack(fill="x")
        row._buttons = []
        marker = tk.Frame(row, width=2, bg=app.surface)
        marker.pack(side="left", fill="y")
        inner = tk.Frame(row, bg=app.surface)
        inner.pack(fill="x", padx=(4 + min(depth, 5) * 18, 6), pady=4)
        filtered_parent = bool(branches and search.get().strip())
        button = (
            MotionButton(
                inner,
                icon=(
                    "minus"
                    if filtered_parent
                    else (
                        "chevron-down"
                        if tid in app.edital_expanded
                        else "chevron-right"
                    )
                ),
                style="Ghost.TButton",
                height=30,
                state="disabled" if filtered_parent else "normal",
                command=lambda: expand(tid),
            )
            if branches
            else CompletionBox(inner, topic["done"], command=lambda: toggle_done(topic))
        )
        button.pack(side="left", anchor="n", padx=(0, 6))
        row._buttons.append(button)
        tooltip(
            button,
            (
                "Limpe a busca para expandir este tópico"
                if filtered_parent
                else "Abrir subassuntos" if branches else "Marcar ou desmarcar teoria"
            ),
        )
        controls[tid] = button
        notes_button = MotionButton(
            inner,
            icon="pencil",
            style="Ghost.TButton",
            height=30,
            command=lambda: app.topic_notes(topic, update_notes),
        )
        notes_button.pack(side="right", anchor="n", padx=(6, 0))
        row._buttons.append(notes_button)
        tooltip(notes_button, "Observações deste assunto")
        text_frame = tk.Frame(inner, bg=app.surface)
        text_frame.pack(side="left", fill="x", expand=True, pady=(5, 0))
        title = tk.Label(
            text_frame,
            text=topic["name"],
            font=(app.font_family, 10, "bold" if branches and depth == 0 else "normal"),
            fg=app.fg,
            bg=app.surface,
            anchor="w",
            justify="left",
            cursor="hand2",
        )
        title.pack(fill="x")
        wrapping(title, 8, 100)
        info = tk.Label(
            text_frame,
            text=detail_text(topic),
            font=(app.font_family, 9),
            fg=app.muted,
            bg=app.surface,
            anchor="w",
            justify="left",
        )
        if info.cget("text"):
            info.pack(fill="x", pady=(2, 4))
        wrapping(info, 8, 100)
        labels = [inner, text_frame, title, info]
        rendered[tid] = (row, marker, labels)
        for widget in [row, inner, text_frame, title, info]:
            widget.bind("<Button-1>", lambda e, t=topic: activate(t))
            widget.bind(
                "<Double-1>",
                lambda e, t=topic: (
                    app.session_form(
                        {"subject_id": t["subject_id"], "topic_id": t["id"]}
                    )
                    if not children.get(t["id"])
                    else None
                ),
            )
            widget.bind("<Enter>", lambda e, t=tid: paint_selected(t, True))
            widget.bind("<Leave>", lambda e, t=tid: paint_selected(t))
        title.configure(takefocus=True)
        title.bind("<Return>", lambda e, t=topic: activate(t))
        title.bind(
            "<Right>",
            lambda e, k=tid: (
                expand(k) if children.get(k) and k not in app.edital_expanded else None
            ),
        )
        title.bind(
            "<Left>", lambda e, k=tid: expand(k) if k in app.edital_expanded else None
        )
        paint_selected(tid)
        if branches and not filtered_parent:
            group = tk.Frame(container, bg=app.surface)
            views[tid] = dict(
                host=group,
                button=button,
                items=branches,
                depth=depth + 1,
                after=row,
                open=tid in app.edital_expanded,
            )
            app.edital_branch_buttons[tid] = button
            if views[tid]["open"]:
                show_branch(tid)

    def subject_header(subject, roots, items, term):
        sid = "s" + subject["id"]
        total = sum(t["total"] for t in roots)
        done = sum(t["completed"] for t in roots)
        block = tk.Frame(host, bg=app.surface)
        block.pack(fill="x", pady=(0, 2))
        head = tk.Frame(block, bg=app.surface, cursor="hand2")
        head.pack(fill="x", padx=4, pady=(6, 0))
        arrow = MotionButton(
            head,
            icon=(
                "chevron-down"
                if term or sid in app.edital_expanded
                else "chevron-right"
            ),
            style="Ghost.TButton",
            height=30,
            command=lambda k=sid: expand(k),
        )
        arrow.pack(side="left", padx=(0, 6))
        title = label(
            head, app, subject["name"], size=11, weight="bold", cursor="hand2"
        )
        title.pack(side="left", fill="x", expand=True)
        metric = label(head, app, f"{done}/{total}", size=9, tone="muted")
        metric.pack(side="right", padx=(8, 8))
        for widget in (head, title, metric):
            widget.bind("<Button-1>", lambda e, k=sid: expand(k))
        sbar = ProgressBar(block, app, 100 * done / total if total else 0, height=3)
        sbar.pack(fill="x", padx=(46, 12), pady=(2, 8))
        subject_metrics[subject["id"]] = (metric, sbar, roots)
        group = tk.Frame(block, bg=app.surface)
        views[sid] = dict(
            host=group,
            button=arrow,
            items=items,
            depth=0,
            after=sbar,
            open=bool(term or sid in app.edital_expanded),
        )
        app.edital_branch_buttons[sid] = arrow
        return sid, group

    def populate():
        rendered.clear()
        controls.clear()
        subject_metrics.clear()
        views.clear()
        app.edital_branch_buttons.clear()
        for widget in host.winfo_children():
            widget.destroy()
        term = normalized(search.get().strip())
        app.edital_search = search.get()
        shown = 0
        more = False
        found = False
        for subject in subjects:
            relevant = by_subject.get(subject["id"], [])
            matching = (
                [
                    t
                    for t in relevant
                    if term in normalized(t["name"])
                    or term in normalized(subject["name"])
                ]
                if term
                else relevant
            )
            if term and not matching:
                continue
            found = True
            roots = [t for t in relevant if t["parent_id"] not in mapping]
            items = roots
            if term:
                items = matching[: max(0, limit[0] - shown)]
                shown += len(items)
                more = len(items) < len(matching)
            sid, group = subject_header(subject, roots, items, term)
            if views[sid]["open"]:
                show_branch(sid)
                if not items:
                    label(
                        group,
                        app,
                        "Adicione o primeiro assunto desta matéria.",
                        size=9,
                        tone="muted",
                    ).pack(anchor="w", padx=46, pady=8)
            if more:
                break
        if more:

            def show_more():
                limit[0] += 100
                populate()

            MotionButton(
                host,
                text="Mostrar mais resultados",
                style="Ghost.TButton",
                command=show_more,
            ).pack(anchor="w", padx=10, pady=8)
        if not found:
            empty(
                host,
                app,
                "search",
                "Nada encontrado",
                "Tente outro termo, sem acentos ou mais curto, ou adicione um assunto.",
                [
                    ("Limpar busca", lambda: search.set("")),
                    ("Novo assunto", app.topic_form),
                ],
            ).pack(fill="x", pady=30)
        if app.edital_selected in mapping:
            select(mapping[app.edital_selected])
        else:
            show_detail(None)
        tid = pending_reveal[0]
        pending_reveal[0] = None
        if tid in rendered:
            row = rendered[tid][0]
            app.motion.watch(row)
            key = (row, "reveal")

            def reveal():
                app.motion.jobs.pop(key, None)
                if row.winfo_exists():
                    y = row.winfo_rooty() - host.winfo_rooty() - 80
                    tree_scroll.canvas.yview_moveto(
                        max(0, y / max(1, host.winfo_height()))
                    )

            app.motion.jobs[key] = app.root.after(120, reveal)

    def search_changed(*args):
        hint()
        limit[0] = 100
        app.edital_selected = None
        tree_scroll.canvas.yview_moveto(0)
        # Cancel rapid keystrokes without rebuilding hundreds of rows each time.
        previous = app.motion.jobs.pop((entry, "search"), None)
        if previous:
            app.root.after_cancel(previous)
        app.motion.watch(entry)

        def run():
            app.motion.jobs.pop((entry, "search"), None)
            populate()

        app.motion.jobs[(entry, "search")] = app.root.after(180, run)

    search.trace_add("write", search_changed)
    populate()
