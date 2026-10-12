"""Campo de Treinamento: library of lessons (catalog, personal and planned).

Reading and organization are the center; the RPG stays out of this screen.
Planned lessons are browsable but never openable, and numbers are objective
counts, never coverage percentages computed from planning.
"""

import tkinter as tk
from tkinter import filedialog, ttk
from urllib.parse import urlsplit

from theme import compact_duration
from ui import MotionButton, Tooltip, trace_owned
from ui_kit import (
    ActionMenu,
    Card,
    Row,
    Section,
    Segmented,
    dot,
    empty,
    label,
    placeholder,
    wrapping,
)

VIEWS = [
    ("disponiveis", "Disponíveis"),
    ("baixadas", "Baixadas"),
    ("andamento", "Em andamento"),
    ("favoritas", "Favoritas"),
    ("planejadas", "Planejadas"),
]
STATUS = {
    "planejada": "Planejada: ainda não produzida",
    "rascunho": "Rascunho",
    "em_revisao": "Em revisão",
    "publicada": "Publicada e revisada",
    "arquivada": "Arquivada",
    "teste": "Material de teste",
    "pessoal": "Material pessoal",
}
AVAILABILITY = {
    "nao_publicada": ("Sem arquivo", "faint"),
    "nao_baixada": ("Precisa baixar", "muted"),
    "baixando": ("Baixando…", "accent"),
    "disponivel": ("Disponível offline", "success"),
    "falha": ("Falha no download", "error"),
    "atualizacao_disponivel": ("Nova versão disponível", "secondary"),
    "arquivo_ausente": ("Arquivo não encontrado neste computador", "error"),
}
PAGE = 120
EXPLORE = "Explorar todo o acervo"


def size_text(value):
    return (
        f"{value / 1024 / 1024:.1f} MB".replace(".", ",")
        if value >= 1024 * 1024
        else f"{max(1, value // 1024)} KB"
    )


def render(app):
    screen = TrainingScreen(app)
    screen.pack(fill="both", expand=True)
    return screen


class TrainingScreen(tk.Frame):
    def __init__(self, app):
        super().__init__(app.content, bg=app.bg)
        self.app = app
        self.service = app.training
        self.content = app.content_manager
        self.view = app.store.pref("training_view", "disponiveis")
        self.exam = app.store.pref("training_exam", "") or None
        if self.exam not in self.service.exams:
            self.exam = None
        self.query = getattr(app, "training_query", "")
        self.selected = getattr(app, "training_selected", None)
        self.limit = PAGE
        self.poll_job = None
        self.lessons = self.service.library()
        self.bind("<Destroy>", self.cleanup, add="+")
        self.header()
        self.status_line()
        self.continue_strip()
        self.body()
        self.populate()
        self.poll()

    # Top ---------------------------------------------------------------

    def header(self):
        bar = tk.Frame(self, bg=self.app.bg)
        bar.pack(fill="x", pady=(0, 10))
        names = [EXPLORE] + [self.exam_name(e) for e in self.service.exams.values()]
        self.exam_var = tk.StringVar(
            value=(
                self.exam_name(self.service.exams[self.exam]) if self.exam else EXPLORE
            )
        )
        combo = ttk.Combobox(
            bar, textvariable=self.exam_var, values=names, state="readonly", width=44
        )
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", self.change_exam)
        Tooltip(
            combo,
            "Edital-alvo: mostra as aulas e o planejamento ligados a esse cargo. O acervo continua acessível.",
        )
        self.search_var = tk.StringVar(value=self.query)
        entry = ttk.Entry(
            bar, textvariable=self.search_var, width=34, style="Field.TEntry"
        )
        entry.pack(side="left", padx=(10, 0))
        placeholder(entry, self.app, "Buscar por aula, matéria ou assunto")
        trace_owned(entry, self.search_var, self.search_changed)
        ActionMenu(
            bar,
            self.app,
            [
                ("Atualizar catálogo", self.refresh_catalog),
                ("Configurar fonte de conteúdo…", self.configure_source),
                None,
                ("Importar PDF próprio…", self.import_pdf),
                ("Gerenciar downloads…", self.manage_downloads),
                None,
                ("Sobre o acervo e o planejamento", self.about),
            ],
            text="Conteúdo",
            icon="library",
        ).pack(side="right")

    def exam_name(self, exam):
        return f"{exam['organization']} {exam['edition_year']} · {exam['role']}"

    def status_line(self):
        p = self.app.motion.palette
        state = self.content.state()
        catalog = self.content.catalog()
        source = self.content.source
        if source["mode"] == "none":
            text = "Nenhuma fonte de conteúdo configurada. Use o menu Conteúdo para apontar uma pasta ou um endereço."
        elif catalog:
            # Where the active catalog came from, which may differ from the current source.
            produced = (state.get("source") or {}).get("mode")
            origin = {
                "local": "obtido da pasta local",
                "remote": "obtido do endereço remoto",
            }.get(produced, "")
            text = f"Catálogo {catalog['catalog_id']} {catalog['catalog_version']}" + (
                f" ({origin})" if origin else ""
            )
            if produced and produced != source["mode"]:
                text += " · a fonte configurada agora é outra"
            if state.get("checked_at"):
                text += f" · conferido em {state['checked_at'][:16].replace('T', ' ')}"
        else:
            text = "Fonte configurada, mas nenhum catálogo válido foi carregado ainda."
        line = tk.Frame(self, bg=self.app.bg)
        line.pack(fill="x", pady=(0, 6))
        label(line, self.app, text, size=9, tone="muted").pack(side="left")
        if state.get("error"):
            strip = tk.Frame(self, bg=p["warning_bg"])
            strip.pack(fill="x", pady=(0, 8))
            message = "A última atualização falhou: " + state["error"]
            if catalog:
                message += " Continuamos usando o último catálogo válido."
            wrapping(label(strip, self.app, message, size=9, bg=p["warning_bg"])).pack(
                fill="x", padx=12, pady=8
            )
        if catalog and catalog["kind"] == "teste":
            strip = tk.Frame(self, bg=p["info_bg"])
            strip.pack(fill="x", pady=(0, 8))
            wrapping(
                label(
                    strip,
                    self.app,
                    "Catálogo de TESTE ativo: serve para validar download e leitor. Não é conteúdo de estudo nem cobertura de edital.",
                    size=9,
                    bg=p["info_bg"],
                )
            ).pack(fill="x", padx=12, pady=8)

    def continue_strip(self):
        lesson = self.service.continue_reading(self.lessons)
        if not lesson:
            return
        card = Card(self, self.app, padding=(20, 14))
        card.pack(fill="x", pady=(4, 12))
        line = tk.Frame(card.body, bg=self.app.surface)
        line.pack(fill="x")
        texts = tk.Frame(line, bg=self.app.surface)
        texts.pack(side="left", fill="x", expand=True)
        label(
            texts, self.app, "Continuar: " + lesson["title"], size=12, weight="bold"
        ).pack(anchor="w")
        position = lesson["position"]
        where = (
            f"página {position['page']}"
            + (f" de {position['pages']}" if position and position["pages"] else "")
            if position
            else "início"
        )
        label(
            texts,
            self.app,
            f"{lesson['subject']} › {lesson['topic']} · {where}",
            size=9,
            tone="muted",
        ).pack(anchor="w")
        MotionButton(
            line,
            text="Estudar esta aula",
            icon="play",
            style="Accent.TButton",
            command=lambda: self.study(lesson),
        ).pack(side="right")
        MotionButton(
            line, text="Abrir", icon="book-open", command=lambda: self.open(lesson)
        ).pack(side="right", padx=8)

    # Body --------------------------------------------------------------

    def body(self):
        counts = {
            key: len(self.service.filtered(self.lessons, key, "", self.exam))
            for key, _ in VIEWS
        }
        bar = tk.Frame(self, bg=self.app.bg)
        bar.pack(fill="x", pady=(0, 10))
        self.segments = Segmented(
            bar,
            self.app,
            [(k, n, counts[k] or "") for k, n in VIEWS],
            self.view,
            self.change_view,
        )
        self.segments.pack(side="left")
        self.summary = label(self, self.app, "", size=9, tone="muted")
        self.summary.pack(fill="x", pady=(0, 8))
        split = tk.Frame(self, bg=self.app.bg)
        split.pack(fill="both", expand=True)
        split.columnconfigure(0, weight=3, uniform="split")
        split.columnconfigure(1, weight=2, uniform="split", minsize=320)
        split.rowconfigure(0, weight=1)
        left = Card(split, self.app, padding=(4, 4), stretch=True)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        from app import Scroll

        self.list_area = Scroll(left.body, style="Panel.TFrame")
        self.list_area.pack(fill="both", expand=True, padx=(6, 4), pady=6)
        right = Card(split, self.app, padding=(24, 22), stretch=True)
        right.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        self.detail = right.body

    def populate(self):
        host = self.list_area.body
        for widget in host.winfo_children():
            widget.destroy()
        shown = self.service.filtered(
            self.lessons, self.view, self.search_var.get(), self.exam
        )
        self.update_summary(shown)
        self.rows = {}
        if not shown:
            self.empty_list(host)
            self.show(None)
            return
        groups = {}
        for lesson in shown:
            groups.setdefault((lesson["area"], lesson["subject"]), {}).setdefault(
                lesson["topic"], []
            ).append(lesson)
        count = 0
        for (area, subject), topics in sorted(
            groups.items(), key=lambda g: (g[0][0] or "~", g[0][1])
        ):
            if count >= self.limit:
                break
            label(host, self.app, subject, size=11, weight="bold").pack(
                anchor="w", padx=10, pady=(14, 0)
            )
            if area and area != subject:
                label(host, self.app, area, size=8, tone="faint").pack(
                    anchor="w", padx=10
                )
            for topic, lessons in topics.items():
                if len(lessons) > 1 or topic != lessons[0]["title"]:
                    label(host, self.app, topic, size=9, tone="muted").pack(
                        anchor="w", padx=22, pady=(6, 0)
                    )
                for lesson in lessons:
                    self.lesson_row(host, lesson)
                    count += 1
        if len(shown) > count:

            def more():
                self.limit += PAGE
                self.populate()

            MotionButton(
                host,
                text=f"Mostrar mais ({len(shown) - count})",
                style="Ghost.TButton",
                command=more,
            ).pack(anchor="w", padx=10, pady=8)
        current = next((l for l in shown if l["id"] == self.selected), None)
        self.show(current)

    def update_summary(self, shown):
        if self.exam:
            numbers = self.service.exam_summary(self.exam, self.lessons)
            self.summary.configure(
                text=f"Edital: {numbers['disciplines']} disciplinas · {numbers['items']} itens extraídos (conferência pendente) · "
                f"{numbers['available']} aulas publicadas · {numbers['planned']} planejadas"
            )
        else:
            self.summary.configure(
                text=f"{len(shown)} {'aula' if len(shown) == 1 else 'aulas'} neste filtro"
            )

    def lesson_row(self, host, lesson):
        status, tone = AVAILABILITY.get(lesson["availability"], ("", "muted"))
        if lesson["origin"] == "planejada":
            # The whole view is planning; repeating it on every row is noise.
            status, tone = "", "faint"
        detail = []
        if lesson["position"] and lesson["openable"]:
            pos = lesson["position"]
            detail.append(
                f"página {pos['page']}"
                + (f" de {pos['pages']}" if pos["pages"] else "")
            )
        if lesson["completed"]:
            detail.append("leitura concluída")
        if lesson.get("test"):
            detail.append("teste")
        if lesson["origin"] == "pessoal":
            detail.append("material pessoal")
        row = Row(
            host,
            self.app,
            lesson["title"],
            " · ".join(part for part in [status] + detail if part),
            on_open=lambda: self.select(lesson),
            pady=7,
        )
        row.pack(fill="x", padx=(12, 4))
        dot(row.lead, self.app, tone, 8).pack(pady=(6, 0), padx=(0, 10))
        if lesson["favorite"]:
            label(row.trail, self.app, "favorita", size=8, tone="accent").pack(
                side="right"
            )
        row.refresh_bindings()
        if lesson["id"] == self.selected:
            row.select(True)
        self.rows[lesson["id"]] = row

    def empty_list(self, host):
        if self.search_var.get().strip():
            empty(
                host,
                self.app,
                "search",
                "Nada encontrado",
                "Tente outro termo, mais curto ou sem acentos.",
                [("Limpar busca", lambda: self.search_var.set(""))],
            ).pack(fill="x", pady=40)
            return
        if self.view == "planejadas":
            empty(
                host,
                self.app,
                "list",
                "Sem planejamento para este edital",
                "Escolha outro edital ou explore todo o acervo.",
            ).pack(fill="x", pady=40)
            return
        if self.view == "disponiveis":
            empty(
                host,
                self.app,
                "library",
                "Nenhuma aula disponível ainda",
                "O acervo revisado está em produção. Quando houver um catálogo publicado, configure a fonte em "
                "Conteúdo. Enquanto isso, importe um PDF seu ou consulte o planejamento.",
                [
                    ("Ver planejamento", lambda: self.change_view("planejadas")),
                    ("Importar PDF próprio", self.import_pdf),
                ],
            ).pack(fill="x", pady=40)
            return
        messages = {
            "baixadas": "Nenhuma aula baixada. As aulas baixadas abrem sem internet.",
            "andamento": "Nenhuma leitura em andamento. A página em que você parar fica salva aqui.",
            "favoritas": "Nenhuma favorita. Use o menu da aula para favoritá-la.",
        }
        empty(
            host, self.app, "bookmark", "Nada por aqui ainda", messages[self.view]
        ).pack(fill="x", pady=40)

    # Detail --------------------------------------------------------------

    def select(self, lesson):
        previous = self.rows.get(self.selected)
        if previous and previous.winfo_exists():
            previous.select(False)
        self.selected = lesson["id"]
        self.app.training_selected = lesson["id"]
        if lesson["id"] in self.rows:
            self.rows[lesson["id"]].select(True)
        self.show(lesson)

    def show(self, lesson):
        for widget in self.detail.winfo_children():
            widget.destroy()
        if lesson is None:
            self.detail_empty()
            return
        p = self.app.motion.palette
        origin = {
            "catalogo": "Catálogo",
            "pessoal": "Material pessoal",
            "planejada": "Planejamento editorial",
        }[lesson["origin"]]
        if lesson.get("test"):
            origin = "Material de teste"
        label(
            self.detail,
            self.app,
            f"{origin} · {lesson['subject']} › {lesson['topic']}",
            size=9,
            tone="muted",
        ).pack(anchor="w")
        wrapping(
            label(self.detail, self.app, lesson["title"], size=15, weight="bold")
        ).pack(fill="x", pady=(6, 0))
        status = STATUS.get(lesson["publication_status"], lesson["publication_status"])
        availability, tone = AVAILABILITY.get(lesson["availability"], ("", "muted"))
        line = tk.Frame(self.detail, bg=p["surface"])
        line.pack(fill="x", pady=(6, 0))
        label(line, self.app, status, size=9, tone="muted").pack(side="left")
        if lesson["origin"] != "planejada":
            label(line, self.app, " · " + availability, size=9, tone=tone).pack(
                side="left"
            )
        from app import Scroll

        area = Scroll(self.detail, style="Panel.TFrame")
        area.pack(fill="both", expand=True, pady=(10, 0))
        body = area.body
        if lesson["origin"] == "planejada":
            self.planned_detail(body, lesson)
        else:
            self.lesson_detail(body, lesson)
        self.actions(lesson)

    def block(self, parent, title, lines, tone="fg"):
        if not lines:
            return
        label(parent, self.app, title, size=10, weight="bold").pack(
            anchor="w", pady=(14, 4)
        )
        for line in lines:
            wrapping(label(parent, self.app, line, size=10, tone=tone)).pack(
                fill="x", pady=1
            )

    def lesson_detail(self, body, lesson):
        if lesson["summary"]:
            wrapping(label(body, self.app, lesson["summary"], size=10)).pack(fill="x")
        self.block(body, "Objetivos", ["• " + o for o in lesson["objectives"]])
        known = {l["id"]: l["title"] for l in self.lessons}
        self.block(
            body,
            "Pré-requisitos sugeridos",
            [known.get(i, i) for i in lesson["prerequisite_lesson_ids"]],
            "muted",
        )
        review = lesson["review"]
        if lesson["origin"] == "catalogo":
            reviewed = (
                f"Aprovada por {review['reviewer']} em {review['reviewed_at']}"
                if review["status"] == "aprovada"
                else "Revisão: " + review["status"]
            )
            resource = lesson["resource"] or {}
            facts = [
                f"Versão {lesson['content_version']}"
                + (f" · PDF {resource.get('version')}" if resource else ""),
                reviewed,
            ]
            if resource:
                facts.append(
                    size_text(resource["bytes"])
                    + (
                        f" · {resource['page_count']} páginas"
                        if resource.get("page_count")
                        else ""
                    )
                    + (
                        f" · licença: {resource['license']}"
                        if resource.get("license")
                        else ""
                    )
                )
            if lesson.get("authors"):
                facts.append("Autoria: " + ", ".join(lesson["authors"]))
            if lesson.get("changes"):
                facts.append("Mudanças nesta versão: " + lesson["changes"])
            self.block(body, "Revisão e versão", facts, "muted")
            self.block(
                body,
                "Fontes",
                [
                    s["title"] + (f" — {s['url']}" if s["url"] else "")
                    for s in lesson["sources"]
                ],
                "muted",
            )
            coverage = [
                f"{self.exam_short(c['exam_id'])}: {c['status']}"
                + (f" ({c['depth']})" if c["depth"] else "")
                for c in lesson["coverage_links"]
            ]
            self.block(
                body,
                "Cobertura de edital",
                coverage or ["Cobertura ainda não auditada."],
                "muted",
            )
        else:
            self.block(
                body,
                "Origem",
                [lesson["summary"], f"Importado em {lesson['imported'][:10]}"],
                "muted",
            )
        self.block(body, "Seu estudo", self.study_facts(lesson), "muted")

    def study_facts(self, lesson):
        facts = []
        position = lesson["position"]
        if position:
            facts.append(
                f"Página {position['page']}"
                + (f" de {position['pages']}" if position["pages"] else "")
                + f" (versão {position['version']})"
            )
        seconds, sessions = self.service.studied_seconds(lesson["id"])
        if sessions:
            facts.append(
                f"{sessions} {'sessão registrada' if sessions == 1 else 'sessões registradas'} · {compact_duration(seconds)}"
            )
        if lesson["completed"]:
            facts.append(
                "Todas as páginas desta versão foram marcadas como lidas (não mede domínio)."
            )
        notes = len(self.service.notes(lesson["id"]))
        if notes:
            facts.append(f"{notes} {'nota' if notes == 1 else 'notas'} nesta aula")
        return facts or ["Ainda não estudada."]

    def planned_detail(self, body, lesson):
        wrapping(
            label(
                body,
                self.app,
                "Esta aula está no planejamento editorial e ainda não existe como PDF. Ela não entra em "
                "“continuar estudando” e não conta como cobertura.",
                size=10,
            )
        ).pack(fill="x")
        candidates = [
            f"{self.exam_short(c['exam_id'])} — {self.discipline_name(c['exam_id'], c['discipline_id'])}"
            for c in lesson.get("candidates", [])
        ]
        self.block(
            body,
            "Editais candidatos (vínculo por disciplina, não auditado)",
            candidates,
            "muted",
        )
        self.block(
            body,
            "Cobertura",
            ["Não auditada: a correspondência item a item ainda será feita."],
            "muted",
        )

    def exam_short(self, exam_id):
        exam = self.service.exams.get(exam_id)
        return f"{exam['organization']} {exam['edition_year']}" if exam else exam_id

    def discipline_name(self, exam_id, discipline_id):
        exam = self.service.exams.get(exam_id) or {}
        return next(
            (
                d["name"]
                for d in exam.get("disciplines", [])
                if d["id"] == discipline_id
            ),
            discipline_id,
        )

    def detail_empty(self):
        if self.exam:
            numbers = self.service.exam_summary(self.exam, self.lessons)
            exam = self.service.exams[self.exam]
            wrapping(
                label(
                    self.detail, self.app, self.exam_name(exam), size=13, weight="bold"
                )
            ).pack(fill="x")
            lines = [
                f"{numbers['disciplines']} disciplinas e {numbers['items']} itens extraídos do edital oficial.",
                "A decomposição é automática e está pendente de conferência humana; nenhuma cobertura é declarada.",
                exam["retifications"],
                f"{numbers['available']} aulas publicadas ligadas a este cargo · {numbers['planned']} planejadas.",
            ]
            for line in lines:
                wrapping(
                    label(self.detail, self.app, line, size=10, tone="muted")
                ).pack(fill="x", pady=(8, 0))
            MotionButton(
                self.detail,
                text="Ver programa extraído",
                icon="list",
                command=lambda: self.program(exam),
            ).pack(anchor="w", pady=(16, 0))
            return
        empty(
            self.detail,
            self.app,
            "book-open",
            "Escolha uma aula",
            "Veja objetivos, versão, revisão, fontes e cobertura, e comece a estudar.",
        ).pack(fill="x", pady=(40, 0))

    def actions(self, lesson):
        p = self.app.motion.palette
        bar = tk.Frame(self.detail, bg=p["surface"])
        bar.pack(fill="x", side="bottom", pady=(14, 0))
        if lesson["origin"] == "planejada":
            label(
                bar,
                self.app,
                "Sem arquivo para abrir: aula planejada.",
                size=9,
                tone="faint",
            ).pack(side="left")
            return
        state = lesson["availability"]
        job = self.content.job(lesson["id"]) if lesson["origin"] == "catalogo" else {}
        if state == "baixando":
            done = job.get("received", 0) / max(1, job.get("total", 1))
            self.progress_label = label(
                bar, self.app, f"Baixando… {round(done * 100)}%", size=10, tone="accent"
            )
            self.progress_label.pack(side="left")
            MotionButton(
                bar,
                text="Cancelar",
                style="Ghost.TButton",
                command=lambda: self.cancel(lesson),
            ).pack(side="right")
            return
        if state == "falha":
            wrapping(
                label(
                    bar,
                    self.app,
                    job.get("error") or "Falha no download.",
                    size=9,
                    tone="error",
                )
            ).pack(fill="x")
        if state in ("nao_baixada", "falha"):
            MotionButton(
                bar,
                text=("Tentar de novo" if state == "falha" else "Baixar")
                + f" ({size_text(lesson['resource']['bytes'])})",
                icon="download",
                style="Accent.TButton",
                command=lambda: self.download(lesson),
            ).pack(side="left")
        if lesson["openable"]:
            MotionButton(
                bar,
                text="Estudar esta aula",
                icon="play",
                style="Accent.TButton",
                command=lambda: self.study(lesson),
            ).pack(side="left")
            path, version = self.service.file_for(lesson)
            text = (
                "Abrir" if version == lesson["version"] else f"Abrir versão {version}"
            )
            MotionButton(
                bar, text=text, icon="book-open", command=lambda: self.open(lesson)
            ).pack(side="left", padx=(8, 0))
        if state == "atualizacao_disponivel":
            MotionButton(
                bar,
                text="Baixar nova versão",
                icon="download",
                style="Ghost.TButton",
                command=lambda: self.download(lesson),
            ).pack(side="left", padx=(8, 0))
        items = [
            (
                "Remover dos favoritos" if lesson["favorite"] else "Favoritar",
                lambda: self.favorite(lesson),
            ),
        ]
        if lesson["origin"] == "catalogo" and self.content.local_versions(lesson["id"]):
            items += [
                None,
                (
                    "Remover download (mantém notas e progresso)",
                    lambda: self.remove(lesson),
                    "danger",
                ),
            ]
        if lesson["origin"] == "pessoal":
            items += [
                None,
                (
                    "Remover material pessoal",
                    lambda: self.remove_personal(lesson),
                    "danger",
                ),
            ]
        ActionMenu(bar, self.app, items).pack(side="right")

    # Actions -----------------------------------------------------------

    def open(self, lesson):
        self.app.open_lesson(lesson)

    def study(self, lesson):
        path, version = self.service.file_for(lesson)
        self.app.study_lesson(lesson, version or lesson["version"])

    def download(self, lesson):
        self.content.start_download(lesson, lambda lesson_id: None)
        self.reload()

    def cancel(self, lesson):
        self.content.cancel(lesson["id"])

    def favorite(self, lesson):
        self.service.toggle_favorite(lesson["id"])
        self.reload()

    def complete(self, lesson):
        path, version = self.service.file_for(lesson)
        self.service.set_completed(
            lesson["id"], version or lesson["version"], not lesson["completed"]
        )
        self.reload()

    def remove(self, lesson):
        from app import messagebox

        if messagebox.askyesno(
            "Remover download",
            "Apagar o PDF desta aula deste computador? Notas, marcadores, página e histórico de estudo continuam salvos.",
            parent=self.app.root,
        ):
            self.content.remove(lesson["id"])
            self.reload()

    def remove_personal(self, lesson):
        from app import messagebox

        if messagebox.askyesno(
            "Remover material pessoal",
            "Remover este PDF do RUMO? Suas notas e o histórico de estudo continuam salvos.",
            parent=self.app.root,
        ):
            self.service.remove_personal(lesson["id"])
            self.selected = None
            self.reload()

    def reload(self):
        self.app.training_query = self.search_var.get()
        self.app.refresh()

    def poll(self):
        """Watch background downloads from the Tk thread (workers never touch Tk)."""
        active = [
            l
            for l in self.lessons
            if l["origin"] == "catalogo" and self.content.job(l["id"]).get("state")
        ]
        if not active:
            return
        changed = False
        for lesson in active:
            job = self.content.job(lesson["id"])
            if job["state"] != "baixando" and lesson["availability"] == "baixando":
                changed = True
            if (
                job["state"] == "baixando"
                and lesson["id"] == self.selected
                and hasattr(self, "progress_label")
            ):
                if self.progress_label.winfo_exists():
                    self.progress_label.configure(
                        text=f"Baixando… {round(job['received'] / max(1, job['total']) * 100)}%"
                    )
        if changed:
            for lesson in active:
                job = self.content.job(lesson["id"])
                if job["state"] == "concluido":
                    self.app.notify(
                        f"Aula baixada: {lesson['title']}. Ela abre sem internet.",
                        "Download concluído",
                        "circle-check",
                        "success",
                    )
                elif job["state"] == "falha":
                    self.app.notify(
                        job["error"],
                        "Download não concluído",
                        "triangle-alert",
                        "error",
                    )
            self.reload()
            return
        if any(self.content.job(l["id"]).get("state") == "baixando" for l in active):
            self.poll_job = self.after(250, self.poll)

    def change_view(self, key):
        self.view = key
        self.app.store.set_pref("training_view", key)
        self.limit = PAGE
        self.segments.value = key
        self.segments.draw()
        self.populate()

    def change_exam(self, event=None):
        value = self.exam_var.get()
        exam = next(
            (
                e["id"]
                for e in self.service.exams.values()
                if self.exam_name(e) == value
            ),
            "",
        )
        self.app.store.set_pref("training_exam", exam)
        self.selected = None
        self.reload()

    def search_changed(self, *args):
        if getattr(self, "search_job", None):
            self.after_cancel(self.search_job)
        self.search_job = self.after(200, self.populate)

    def cleanup(self, event):
        if event.widget is self and self.poll_job:
            self.after_cancel(self.poll_job)

    # Menus ---------------------------------------------------------------

    def refresh_catalog(self):
        from training_content import ContentError

        try:
            catalog, changed = self.content.refresh()
        except ContentError as error:
            self.app.notify(
                str(error), "Catálogo não atualizado", "triangle-alert", "warning"
            )
            self.reload()
            return
        self.app.notify(
            (
                f"Catálogo {catalog['catalog_version']} ativo."
                if changed
                else "O catálogo já estava atualizado."
            ),
            "Catálogo",
            "circle-check",
            "success",
        )
        self.reload()

    def configure_source(self):
        from app import Form
        from training_content import normalize_source, validate_source

        source = self.content.source
        modes = {
            "Nenhuma": "none",
            "Pasta local": "local",
            "Endereço remoto (HTTPS)": "remote",
        }
        labels = {v: k for k, v in modes.items()}

        def save(values):
            raw = dict(
                mode=modes[values["mode"]],
                path=values["path"].strip(),
                url=values["url"].strip(),
                allowed_hosts=[
                    h.strip() for h in values["hosts"].split(",") if h.strip()
                ],
            )
            if values["github"]:
                from training_content import GITHUB_RELEASE_HOSTS

                raw["allowed_hosts"] += list(GITHUB_RELEASE_HOSTS)
            source = validate_source(normalize_source(raw))
            self.app.store.set_pref("training_source", source)
            self.app.reset_content()

        Form(
            self.app,
            "Fonte de conteúdo",
            [
                ("mode", "De onde vêm as aulas", "choice", list(modes)),
                ("path", "Pasta local com catalog.json (modo pasta)", "entry"),
                ("url", "Endereço https:// do catalog.json (modo remoto)", "entry"),
                (
                    "hosts",
                    "Outros hosts permitidos para os PDFs, separados por vírgula",
                    "entry",
                ),
                ("github", "Permitir os hosts de download do GitHub Releases", "bool"),
            ],
            save,
            dict(
                mode=labels[source["mode"]],
                path=source["path"],
                url=source["url"],
                hosts=", ".join(
                    h
                    for h in source["allowed_hosts"]
                    if h != urlsplit(source["url"]).hostname
                ),
                github=False,
            ),
        )

    def import_pdf(self):
        path = filedialog.askopenfilename(
            title="Importar PDF próprio",
            filetypes=[("PDF", "*.pdf")],
            parent=self.app.root,
        )
        if not path:
            return
        from app import Form
        from training_content import ContentError

        def save(values):
            try:
                lesson_id = self.service.import_personal(
                    path, values["title"], values["subject"], values["topic"]
                )
            except ContentError as error:
                raise ValueError(str(error)) from error
            self.selected = lesson_id
            self.app.training_selected = lesson_id
            self.app.store.set_pref("training_view", "disponiveis")

        from pathlib import Path

        Form(
            self.app,
            "Importar material próprio",
            [
                ("title", "Título", "entry"),
                ("subject", "Matéria (opcional)", "entry"),
                ("topic", "Assunto (opcional)", "entry"),
            ],
            save,
            dict(title=Path(path).stem, subject="", topic=""),
        )

    def manage_downloads(self):
        from app import messagebox

        lines = []
        for lesson in self.lessons:
            if lesson["origin"] != "catalogo":
                continue
            for version, path in self.content.local_versions(lesson["id"]).items():
                lines.append(
                    f"{lesson['title']} · versão {version} · {size_text(path.stat().st_size)}"
                )
        text = (
            ("\n".join(lines) if lines else "Nenhuma aula baixada.")
            + f"\n\nEspaço usado pelo Campo de Treinamento: {size_text(self.content.usage())}.\n"
            "Para remover uma aula, use o menu ⋯ no detalhe dela. Notas e progresso não são apagados."
        )
        messagebox.showinfo("Downloads", text, parent=self.app.root)

    def about(self):
        from app import messagebox

        curriculum = self.service.curriculum
        families = len(curriculum.get("families", []))
        planned = sum(len(f["lessons"]) for f in curriculum.get("families", []))
        items = sum(
            len(d["items"])
            for e in curriculum.get("exams", [])
            for d in e["disciplines"]
        )
        messagebox.showinfo(
            "Acervo e planejamento",
            f"Planejamento editorial: {families} famílias e {planned} aulas sugeridas para 9 cargos de TI. "
            "Nenhuma delas existe ainda como PDF revisado.\n\n"
            f"Programas oficiais: {items} itens extraídos automaticamente dos editais, pendentes de conferência humana. "
            "Por isso o RUMO não mostra percentuais de cobertura.\n\n"
            "Aulas publicadas chegam por um catálogo público (pasta local ou endereço HTTPS). "
            "O progresso, as notas e as sessões ficam somente neste computador.",
            parent=self.app.root,
        )

    def program(self, exam):
        win = tk.Toplevel(self.app.root)
        win.title("Programa extraído • " + exam["organization"])
        win.configure(bg=self.app.bg)
        win.geometry("760x620")
        from app import Scroll

        area = Scroll(win)
        area.pack(fill="both", expand=True, padx=16, pady=16)
        area.canvas.configure(bg=self.app.bg)
        body = area.body
        label(body, self.app, self.exam_name(exam), size=13, weight="bold").pack(
            anchor="w"
        )
        wrapping(
            label(
                body,
                self.app,
                "Extração automática do edital oficial; confira na fonte antes de confiar: "
                + exam["source_url"],
                size=9,
                tone="muted",
            )
        ).pack(fill="x", pady=(4, 10))
        for discipline in exam["disciplines"]:
            label(body, self.app, discipline["name"], size=11, weight="bold").pack(
                anchor="w", pady=(12, 2)
            )
            meta = f"páginas {', '.join(map(str, discipline['source_pages']))} · {discipline['decomposition']} · conferência pendente"
            label(body, self.app, meta, size=8, tone="faint").pack(anchor="w")
            for note in discipline["notes"]:
                wrapping(label(body, self.app, note, size=9, tone="warning")).pack(
                    fill="x"
                )
            for item in discipline["items"]:
                wrapping(
                    label(body, self.app, f"{item['number']}  {item['text']}", size=9)
                ).pack(fill="x", padx=(12, 0))
            if discipline["whole_text"]:
                wrapping(label(body, self.app, discipline["whole_text"], size=9)).pack(
                    fill="x", padx=(12, 0)
                )
        win.bind("<Escape>", lambda e: win.destroy())
