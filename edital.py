"""Lazy expandable syllabus sections; one page scrollbar, no wide table."""

import tkinter as tk
from tkinter import ttk
import unicodedata
from ui import MotionButton, Panel, ThinProgress, blend
from core import ratio, percentage
from components import CompletionBox


def normalized(text):
    return "".join(
        c
        for c in unicodedata.normalize("NFD", text.casefold())
        if not unicodedata.combining(c)
    )


def render_edital(app, tooltip, dialogs):
    store = app.store
    parent = app.content
    palette = app.motion.palette
    progress = store.progress(app.plan)
    percent = 100 * progress["done"] / progress["total"] if progress["total"] else 0
    card = Panel(parent, app)
    card.pack(fill="x", pady=(16, 8))
    top = ttk.Frame(card.body, style="Panel.TFrame")
    top.pack(fill="x")
    progress_percent = ttk.Label(
        top, text=f"{percent:.0f}%", font=("Inter", 17, "bold"), style="Panel.TLabel"
    )
    progress_percent.pack(side="left", padx=(0, 14))
    progress_count = ttk.Label(
        top,
        text=f"{progress['done']} de {progress['total']} assuntos concluídos",
        style="Panel.TLabel",
    )
    progress_count.pack(side="left")

    def help_progress():
        dialogs.showinfo(
            "Conteúdo e progresso",
            "Cada assunto final conta uma vez. Matérias e tópicos com filhos mostram o progresso agregado. "
            "O filtro de busca não altera a porcentagem.\n\n"
            "Os itens originais do BACEN mantêm o texto do edital de abertura de 2024. "
            "Os subassuntos identificados como “Guia de estudo” são um desdobramento pedagógico, "
            "não texto oficial nem garantia de exaustividade. O PDF não foi alterado.\n\n"
            "Ao detalhar um item que já estava concluído, seus novos subassuntos herdam essa conclusão. "
            "Seu histórico permanece ligado ao item original e é somado aos filhos. "
            "O total passa a refletir os assuntos menores.\n\n"
            "Referências: edital BACEN, dev.java/learn, docs.python.org/3/tutorial, "
            "postgresql.org/docs/current/tutorial.html, legislação no Planalto e Cosif/BCB.",
            parent=app.root,
        )

    info = MotionButton(top, text="Como é calculado?", command=help_progress)
    info.pack(side="right")
    tooltip(info, "Entenda os assuntos oficiais, o guia de estudo e o progresso")
    progress_bar = ThinProgress(card.body, app, percent)
    progress_bar.pack(fill="x", pady=(10, 2))
    app.toolbar(
        [
            ("Importar", app.import_edital),
            ("Gerenciar matérias", app.manage_entities),
            ("Fontes e cobertura", app.syllabus_audit),
            ("Área BACEN 2024", app.load_bacen),
            ("PDF e referência", app.open_bacen),
        ]
    )
    searchrow = ttk.Frame(parent)
    searchrow.pack(fill="x", pady=(10, 8))
    ttk.Label(searchrow, text="Buscar no edital", style="Muted.TLabel").pack(
        side="left", padx=(0, 12)
    )
    search = tk.StringVar(value=app.edital_search)
    entry = ttk.Entry(searchrow, textvariable=search)
    entry.pack(side="left", fill="x", expand=True)
    app.edital_search_entry = entry
    selection_area = ttk.Frame(parent, height=44)
    selection_area.pack(fill="x", pady=(3, 0))
    selection_area.pack_propagate(False)
    selection = ttk.Label(
        selection_area,
        text="Selecione um assunto para estudar, editar ou acessar materiais.",
        style="Muted.TLabel",
        wraplength=700,
        anchor="w",
    )
    selection.pack(fill="both", expand=True)
    selection_tip = tooltip(selection, "Selecione um assunto na lista abaixo.")

    def wrap_label(label, event):
        width = max(100, event.width - 8)
        if int(float(label.cget("wraplength") or 0)) != width:
            label.configure(wraplength=width)

    selection.bind("<Configure>", lambda e: wrap_label(selection, e))
    topics = store.rows(
        """SELECT t.*,COALESCE(a.correct,0) correct,COALESCE(a.wrong,0) wrong,
        COALESCE(a.blank,0) blank,a.last,COALESCE(a.n,0) n,COALESCE(r.n,0) pending FROM topics t
        JOIN subjects d ON d.id=t.subject_id LEFT JOIN
        (SELECT topic_id,SUM(correct) correct,SUM(wrong) wrong,SUM(blank) blank,MAX(day) last,COUNT(*) n FROM sessions GROUP BY topic_id) a ON a.topic_id=t.id
        LEFT JOIN (SELECT topic_id,COUNT(*) n FROM reviews WHERE state='Pendente' GROUP BY topic_id) r ON r.topic_id=t.id
        WHERE d.plan_id=? AND d.archived=0 AND t.archived=0 ORDER BY t.rowid""",
        (app.plan,),
    )
    from learning import ordered, subject_key

    names = {
        s["id"]: s["name"]
        for s in store.rows("SELECT id,name FROM subjects WHERE plan_id=?", (app.plan,))
    }
    if store.pref("syllabus_order", "Aprendizagem") == "Aprendizagem":
        topics = ordered(topics, names)
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
    subjects = sorted(
        store.rows(
            "SELECT * FROM subjects WHERE plan_id=? AND archived=0", (app.plan,)
        ),
        key=lambda s: subject_key(s["name"]),
    )
    app.note(
        "Sequência sugerida: fundamentos → aplicação → aprofundamento. A numeração original do edital continua preservada; você pode estudar qualquer item."
    )
    rendered = {}
    controls = {}
    subject_metrics = {}
    views = {}
    app.edital_rows = rendered
    app.edital_mapping = mapping
    app.edital_branch_buttons = {}

    def chosen():
        topic = mapping.get(app.edital_selected)
        if not topic:
            raise ValueError("Selecione um assunto na lista abaixo.")
        return topic

    def toggle_done(topic=None):
        topic = topic or chosen()
        if children.get(topic["id"]):
            raise ValueError("Abra o tópico e marque seus subassuntos individualmente.")
        done = not topic["done"]
        store.save("topics", {"id": topic["id"], "done": done})
        topic["done"] = done

        # Update only completion, not already aggregated history. Keep rows alive
        # so the viewport, selection and keyboard focus remain exactly in place.
        def completion(t):
            descendants = children.get(t["id"], [])
            t["completed"] = (
                sum(completion(c) for c in descendants)
                if descendants
                else int(t["done"])
            )
            return t["completed"]

        for t in topics:
            if t["parent_id"] not in mapping:
                completion(t)
        current = store.progress(app.plan)
        percent = 100 * current["done"] / current["total"] if current["total"] else 0
        progress_percent.configure(text=f"{percent:.0f}%")
        progress_count.configure(
            text=f"{current['done']} de {current['total']} assuntos concluídos"
        )
        progress_bar.value = percent
        progress_bar.draw()
        if topic["id"] in controls:
            controls[topic["id"]].configure(text="✓" if topic["done"] else "□")
        for tid, (row, marker, labels) in rendered.items():
            text = detail_text(mapping[tid])
            if labels[-1].cget("text") != text:
                labels[-1].configure(text=text)
        for sid, (metric, bar, roots) in subject_metrics.items():
            total = sum(t["total"] for t in roots)
            done = sum(t["completed"] for t in roots)
            percent = 100 * done / total if total else 0
            metric.configure(text=f"{percent:.0f}%  ·  {done}/{total}")
            if bar:
                bar.value = percent
                bar.draw()

    actions = app.toolbar(
        [
            ("Concluir / reabrir", toggle_done),
            (
                "Registrar estudo",
                lambda: app.session_form(
                    {"subject_id": chosen()["subject_id"], "topic_id": chosen()["id"]}
                ),
            ),
            ("Observações", lambda: app.topic_notes(chosen(), update_notes)),
            ("Editar", lambda: app.topic_form(chosen())),
            ("Materiais", lambda: app.materials(chosen())),
            ("Arquivar", lambda: app.archive_topic(chosen())),
        ]
    )
    action_buttons = actions.winfo_children()[0].winfo_children()

    def update_actions():
        selected = mapping.get(app.edital_selected)
        for index, button in enumerate(action_buttons):
            enabled = bool(selected) and (
                index != 0 or not children.get(selected["id"])
            )
            button.configure(state="normal" if enabled else "disabled")

    update_actions()
    host = ttk.Frame(parent)
    host.pack(fill="x", pady=(6, 16))
    limit = [100]
    pending_reveal = [None]

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
            marker.configure(bg=palette["accent"] if selected or hover else current)
            for label in labels:
                label.configure(bg=current)

        app.motion.animate(row, paint, 240, channel="row-hover")

    def select(topic):
        previous = app.edital_selected
        app.edital_selected = topic["id"]
        paint_selected(previous)
        paint_selected(topic["id"])
        name = topic["name"]
        selection.configure(
            text="Selecionado: " + name[:100] + ("…" if len(name) > 100 else "")
        )
        selection_tip.text = name
        update_actions()

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
        view["bar"].pack(fill="x", pady=(9, 10)) if view["bar"] else None
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
            if view["bar"]:
                view["bar"].pack_forget()
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
            questions = topic["correct"] + topic["wrong"] + topic["blank"]
            answered = topic["correct"] + topic["wrong"]
            details.append(
                f"{questions} questões · {answered} respondidas · {percentage(ratio(topic['correct'],topic['wrong']))} de acertos"
            )
            details.append("Último estudo: " + str(topic["last"]))
        if topic["pending"]:
            details.append(f"{topic['pending']} revisões pendentes")
        if topic.get("notes"):
            details.append("✎ " + topic["notes"].replace("\n", " ")[:160])
        if "11.813/2013" in topic["name"]:
            details.append("Retificação oficial: leia Lei 12.813/2013")
        if tid in evidence:
            details.append(
                evidence[tid]["exam"] + " • itens " + evidence[tid]["questions"]
            )
        return "   ·   ".join(details) or (
            "Teoria concluída" if topic["done"] else "Não iniciado"
        )

    def update_notes():
        for tid, (row, marker, labels) in rendered.items():
            labels[-1].configure(text=detail_text(mapping[tid]))

    def topic_row(container, topic, depth):
        tid = topic["id"]
        branches = children.get(tid, [])
        row = tk.Frame(container, bg=app.surface)
        row.pack(fill="x", pady=1)
        marker = tk.Frame(row, width=3, bg=app.surface)
        marker.pack(side="left", fill="y")
        inner = tk.Frame(row, bg=app.surface)
        inner.pack(fill="x", padx=(8 + min(depth, 4) * 16, 10), pady=7)
        # Controls are fixed width; the actual title wraps to available space.
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
                height=34,
                state="disabled" if filtered_parent else "normal",
                command=lambda: expand(tid),
            )
            if branches
            else CompletionBox(inner, topic["done"], command=lambda: toggle_done(topic))
        )
        button.pack(side="left", anchor="n", padx=(0, 8))
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
            height=34,
            command=lambda: app.topic_notes(topic, update_notes),
        )
        notes_button.pack(side="right", anchor="n", padx=(8, 0))
        tooltip(notes_button, "Escrever descrição e observações deste assunto")
        text_frame = tk.Frame(inner, bg=app.surface)
        text_frame.pack(side="left", fill="x", expand=True)
        label = tk.Label(
            text_frame,
            text=topic["name"],
            font=("Inter", 10),
            fg=app.fg,
            bg=app.surface,
            anchor="w",
            justify="left",
            cursor="hand2",
        )
        label.pack(fill="x")
        label.bind("<Configure>", lambda e: wrap_label(label, e))
        detail = tk.Label(
            text_frame,
            text=detail_text(topic),
            font=("Inter", 9),
            fg=app.muted,
            bg=app.surface,
            anchor="w",
            justify="left",
        )
        detail.pack(fill="x", pady=(3, 0))
        detail.bind("<Configure>", lambda e: wrap_label(detail, e))
        labels = [inner, text_frame, label, detail]
        rendered[tid] = (row, marker, labels)
        for widget in [row, inner, text_frame, label, detail]:
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
        label.configure(takefocus=True)
        label.bind("<Return>", lambda e, t=topic: activate(t))
        label.bind(
            "<Right>",
            lambda e, k=tid: (
                expand(k) if children.get(k) and k not in app.edital_expanded else None
            ),
        )
        label.bind(
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
                bar=None,
                after=row,
                open=tid in app.edital_expanded,
            )
            app.edital_branch_buttons[tid] = button
            if views[tid]["open"]:
                show_branch(tid)

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
            sid = "s" + subject["id"]
            roots = [t for t in relevant if t["parent_id"] not in mapping]
            total = sum(t["total"] for t in roots)
            done = sum(t["completed"] for t in roots)
            card = Panel(host, app)
            card.pack(fill="x", pady=(0, 8))
            head = ttk.Frame(card.body, style="Panel.TFrame")
            head.pack(fill="x")
            arrow = MotionButton(
                head,
                icon=(
                    "chevron-down"
                    if term or sid in app.edital_expanded
                    else "chevron-right"
                ),
                command=lambda k=sid: expand(k),
            )
            arrow.pack(side="left", padx=(0, 8))
            title = ttk.Label(
                head,
                text=subject["name"],
                style="PanelHeading.TLabel",
                justify="left",
                cursor="hand2",
            )
            title.pack(side="left", fill="x", expand=True)
            title.bind("<Configure>", lambda e, w=title: wrap_label(w, e))
            title.bind("<Button-1>", lambda e, k=sid: expand(k))
            metric = ttk.Label(
                head,
                text=f"{100*done/total if total else 0:.0f}%  ·  {done}/{total}",
                style="PanelMuted.TLabel",
            )
            metric.pack(side="right", padx=(12, 0))
            bar = ThinProgress(card.body, app, 100 * done / total if total else 0)
            subject_metrics[subject["id"]] = (metric, bar, roots)
            group = tk.Frame(card.body, bg=app.surface)
            items = roots
            if term:
                items = matching[: max(0, limit[0] - shown)]
                shown += len(items)
                more = len(items) < len(matching)
            views[sid] = dict(
                host=group,
                button=arrow,
                items=items,
                depth=0,
                bar=bar,
                after=bar,
                open=bool(term or sid in app.edital_expanded),
            )
            app.edital_branch_buttons[sid] = arrow
            if views[sid]["open"]:
                show_branch(sid)
                if not items:
                    ttk.Label(
                        group,
                        text="Adicione o primeiro assunto desta matéria.",
                        style="PanelMuted.TLabel",
                    ).pack(anchor="w", pady=8)
            if more:
                break
        if more:

            def show_more():
                limit[0] += 100
                populate()

            MotionButton(host, text="Mostrar mais resultados", command=show_more).pack(
                anchor="w", pady=8
            )
        if not found:
            ttk.Label(
                host,
                text="Nenhum assunto encontrado. Tente outro termo ou adicione um assunto.",
                style="Muted.TLabel",
            ).pack(anchor="w", pady=16)
        if app.edital_selected in mapping:
            select(mapping[app.edital_selected])
        tid = pending_reveal[0]
        pending_reveal[0] = None
        if tid in rendered:
            row = rendered[tid][0]
            app.motion.watch(row)
            key = (row, "reveal")

            def reveal():
                app.motion.jobs.pop(key, None)
                if row.winfo_exists():
                    y = row.winfo_rooty() - app.content.winfo_rooty() - 80
                    app.scroll.canvas.yview_moveto(
                        max(0, y / max(1, app.content.winfo_height()))
                    )

            app.motion.jobs[key] = app.root.after(120, reveal)

    def search_changed(*args):
        limit[0] = 100
        app.edital_selected = None
        selection.configure(
            text="Selecione um assunto para estudar, editar ou acessar materiais."
        )
        update_actions()
        app.scroll.canvas.yview_moveto(0)
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
