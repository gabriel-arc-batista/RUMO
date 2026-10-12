"""In-app PDF reader for the Campo de Treinamento.

Pages are rendered by PDFium (pypdfium2, Apache-2.0/BSD-3) into PPM data that
Tk shows natively, so Pillow is not needed at runtime. Only the visible page and
two neighbours stay in memory. Pages keep their own colors (no inversion of
figures or code); the surroundings follow the app theme.
"""

import tkinter as tk
from tkinter import ttk

from theme import ICON
from ui import MotionButton, Tooltip, glyph, ui_font
from ui_kit import ActionMenu, Segmented, label, placeholder, wrapping

try:
    import pypdfium2 as pdfium
except ImportError:  # The screen explains how to enable the reader.
    pdfium = None

CACHE = 3
ZOOMS = (0.5, 0.67, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0)


class PdfFile:
    """Thin wrapper: page count, sizes, rendering, outline and text search."""

    def __init__(self, path):
        if pdfium is None:
            raise RuntimeError("O leitor precisa do pacote pypdfium2.")
        self.document = pdfium.PdfDocument(str(path))
        self.count = len(self.document)
        self.images = {}

    def close(self):
        self.images.clear()
        self.document.close()

    def size(self, index):
        return self.document[index].get_size()

    def render(self, index, scale):
        """PhotoImage of a page; a small LRU keeps memory flat."""
        key = (index, round(scale, 3))
        if key in self.images:
            self.images[key] = self.images.pop(key)
            return self.images[key]
        bitmap = self.document[index].render(
            scale=scale, rev_byteorder=True, prefer_bgrx=False
        )
        width, height = bitmap.width, bitmap.height
        data = bytes(bitmap.buffer)
        if bitmap.stride != width * 3:
            data = b"".join(
                data[r * bitmap.stride : r * bitmap.stride + width * 3]
                for r in range(height)
            )
        image = tk.PhotoImage(
            data=b"P6 %d %d 255\n" % (width, height) + data, format="PPM"
        )
        self.images[key] = image
        while len(self.images) > CACHE:
            self.images.pop(next(iter(self.images)))
        return image

    def outline(self):
        entries = []
        try:
            for bookmark in self.document.get_toc():
                destination = bookmark.get_dest()
                page = destination.get_index() if destination else None
                if page is not None:
                    entries.append((bookmark.get_title(), bookmark.level, page))
        except Exception:  # noqa: BLE001 - a broken outline only hides the index
            return []
        return entries

    def has_text(self, sample=4):
        for index in range(min(sample, self.count)):
            if self.document[index].get_textpage().get_text_bounded().strip():
                return True
        return False

    def search_page(self, index, term):
        """Rectangles (left, top, right, bottom in points from the top) of matches."""
        page = self.document[index]
        height = page.get_size()[1]
        textpage = page.get_textpage()
        searcher = textpage.search(term, match_case=False)
        rects = []
        while True:
            hit = searcher.get_next()
            if not hit:
                break
            start, count = hit
            for i in range(textpage.count_rects(start, count)):
                left, bottom, right, top = textpage.get_rect(i)
                rects.append((left, height - top, right, height - bottom))
        return rects


class Reader(tk.Frame):
    """Reader page. ``lesson`` is a library view; ``path``/``version`` the file."""

    def __init__(self, parent, app, lesson, path, version):
        super().__init__(parent, bg=app.bg)
        self.app = app
        self.lesson = lesson
        self.version = version
        self.service = app.training
        self.page = 0
        self.zoom = None  # None = fit width
        self.fit = "width"
        self.hits = []
        self.hit_index = -1
        self.search_job = None
        self.save_job = None
        self.panel = app.store.pref("reader_panel", "indice")
        self.notes_open = app.store.pref("reader_notes", True)
        self.pdf = PdfFile(path)
        self.bind("<Destroy>", self.cleanup, add="+")
        self.build()
        saved = self.service.position(lesson["id"], version)
        self.service.opened(lesson["id"], version)
        self.go(min(self.pdf.count, saved["page"]) - 1 if saved else 0, save=False)
        self.after_idle(self.canvas.focus_set)

    # Layout --------------------------------------------------------------

    def build(self):
        self.top_bar()
        self.update_banner()
        self.carry_banner()
        self.tool_bar()
        reading_bar = ttk.Frame(self)
        reading_bar.pack(fill="x", pady=(0, 8))
        self.read_var = tk.BooleanVar()
        ttk.Checkbutton(
            reading_bar,
            text="Li esta página",
            variable=self.read_var,
            command=self.mark_read,
        ).pack(side="left")
        self.read_status = ttk.Label(reading_bar, style="Muted.TLabel")
        self.read_status.pack(side="left", padx=12)
        body = tk.Frame(self, bg=self.app.bg)
        body.pack(fill="both", expand=True)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        self.side = tk.Frame(body, bg=self.app.surface, width=250)
        self.side.pack_propagate(False)
        self.view = tk.Frame(body, bg=self.app.bg)
        self.view.grid(row=0, column=1, sticky="nsew")
        self.notes = tk.Frame(body, bg=self.app.surface, width=300)
        self.notes.pack_propagate(False)
        self.page_view()
        self.side_panel()
        self.notes_panel()
        self.layout_panels()

    def top_bar(self):
        p = self.app.motion.palette
        bar = tk.Frame(self, bg=self.app.bg)
        bar.pack(fill="x", pady=(14, 8))
        MotionButton(
            bar,
            text="Campo de Treinamento",
            icon="chevron-left",
            style="Ghost.TButton",
            command=self.leave,
        ).pack(side="left")
        names = tk.Frame(bar, bg=self.app.bg)
        names.pack(side="left", fill="x", expand=True, padx=(12, 12))
        label(names, self.app, self.lesson["title"], size=13, weight="bold").pack(
            anchor="w"
        )
        origin = {"catalogo": "Catálogo", "pessoal": "Material pessoal"}.get(
            self.lesson["origin"], ""
        )
        if self.lesson.get("test"):
            origin = "Material de teste"
        label(
            names,
            self.app,
            f"{self.lesson['subject']} › {self.lesson['topic']} · versão {self.version} · {origin}",
            size=9,
            tone="muted",
        ).pack(anchor="w")
        self.session = tk.Frame(bar, bg=self.app.bg)
        self.session.pack(side="right")
        self.app.clock_listeners.append(self.refresh_session)
        self.refresh_session()

    def carry_banner(self):
        """Oferece trazer marcações de uma versão anterior (nunca automático)."""
        try:
            versions = self.service.reading_versions(self.lesson["id"])
        except (AttributeError, ValueError):
            return
        older = {v: pages for v, pages in versions.items() if v != self.version}
        current = versions.get(self.version, [])
        if not older or current:
            return
        source, pages = max(older.items(), key=lambda item: len(item[1]))
        p = self.app.motion.palette
        strip = tk.Frame(self, bg=p["info_bg"])
        strip.pack(fill="x", pady=(0, 8))
        wrapping(
            label(
                strip,
                self.app,
                f"Você marcou {len(pages)} páginas como lidas na versão {source}. "
                "Esta versão começa sem marcações; você pode trazê-las depois de conferir.",
                size=9,
                bg=p["info_bg"],
            )
        ).pack(side="left", fill="x", expand=True, padx=12, pady=8)
        MotionButton(
            strip,
            text="Trazer marcações",
            command=lambda: self.carry_dialog(source, pages, strip),
        ).pack(side="right", padx=12, pady=6)

    def carry_dialog(self, source, pages, strip):
        from app import messagebox

        dialog = tk.Toplevel(self.app.root)
        dialog.title("Trazer marcações da versão anterior")
        dialog.transient(self.app.root)
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text=(
                f"Páginas lidas na versão {source}. As páginas da versão {self.version} "
                "podem ter mudado: mantenha só as que correspondem ao mesmo conteúdo."
            ),
            wraplength=460,
        ).pack(anchor="w")
        value = tk.StringVar(value=page_ranges(pages))
        ttk.Entry(frame, textvariable=value, width=52).pack(fill="x", pady=10)
        ttk.Label(frame, text="Ex.: 1-8, 10, 12-14", style="Muted.TLabel").pack(
            anchor="w"
        )

        def confirm():
            try:
                chosen = parse_ranges(value.get(), self.pdf.count)
                marked = self.service.carry_reading(
                    self.lesson["id"], self.version, self.pdf.count, chosen
                )
            except (ValueError, OSError) as exc:
                messagebox.showerror("Marcações não trazidas", str(exc), parent=dialog)
                return
            dialog.destroy()
            strip.destroy()
            self.refresh_reading()
            self.app.notify(f"{len(marked)} páginas marcadas nesta versão.")

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Cancelar", command=dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="Marcar estas páginas", command=confirm).pack(
            side="right", padx=8
        )

    def update_banner(self):
        resource = self.lesson.get("resource") or {}
        current = resource.get("version")
        if (
            not current
            or current == self.version
            or self.lesson["origin"] != "catalogo"
        ):
            return
        p = self.app.motion.palette
        strip = tk.Frame(self, bg=p["info_bg"])
        strip.pack(fill="x", pady=(0, 8))
        text = (
            f"Você está lendo a versão {self.version}. A versão {current} está publicada; "
            "as páginas podem ter mudado. Suas notas continuam ligadas à versão em que foram escritas."
        )
        wrapping(label(strip, self.app, text, size=9, bg=p["info_bg"])).pack(
            side="left", fill="x", expand=True, padx=12, pady=8
        )

    def tool_bar(self):
        bar = tk.Frame(self, bg=self.app.bg)
        bar.pack(fill="x", pady=(0, 8))
        self.side_button = self.tool(
            bar, "panel-left", "Índice e marcadores (painel)", self.toggle_side
        )
        self.tool(
            bar,
            "chevron-left",
            "Página anterior (PgUp)",
            lambda: self.go(self.page - 1),
        )
        self.page_var = tk.StringVar()
        entry = ttk.Entry(bar, textvariable=self.page_var, width=5, justify="center")
        entry.pack(side="left", padx=4)
        entry.bind("<Return>", self.jump)
        Tooltip(entry, "Digite a página e pressione Enter")
        self.count_label = label(
            bar, self.app, f"de {self.pdf.count}", size=10, tone="muted"
        )
        self.count_label.pack(side="left", padx=(2, 6))
        self.tool(
            bar,
            "chevron-right",
            "Próxima página (PgDn)",
            lambda: self.go(self.page + 1),
        )
        self.separator(bar)
        self.tool(bar, "zoom-out", "Diminuir (Ctrl −)", lambda: self.step_zoom(-1))
        self.zoom_label = label(
            bar, self.app, "", size=10, tone="muted", width=6, anchor="center"
        )
        self.zoom_label.pack(side="left")
        self.tool(bar, "zoom-in", "Aumentar (Ctrl +)", lambda: self.step_zoom(1))
        self.fit_control = Segmented(
            bar,
            self.app,
            [("width", "Largura"), ("page", "Página")],
            self.fit,
            self.set_fit,
            height=30,
        )
        self.fit_control.pack(side="left", padx=(8, 0))
        self.separator(bar)
        self.star = self.tool(
            bar, "bookmark", "Marcar esta página (Ctrl+D)", self.toggle_bookmark
        )
        self.notes_button = self.tool(
            bar, "notebook-pen", "Notas da aula", self.toggle_notes
        )
        self.tool(
            bar, "maximize", "Modo foco: esconde menus (Esc sai)", self.toggle_focus
        )
        search = tk.Frame(bar, bg=self.app.bg)
        search.pack(side="right")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            search, textvariable=self.search_var, width=22, style="Field.TEntry"
        )
        self.search_entry.pack(side="left")
        placeholder(self.search_entry, self.app, "Buscar no PDF")
        self.search_entry.bind("<Return>", lambda e: self.search(1))
        self.search_entry.bind("<Shift-Return>", lambda e: self.search(-1))
        self.search_info = label(search, self.app, "", size=9, tone="muted")
        self.search_info.pack(side="left", padx=(8, 0))
        self.tool(
            search, "chevron-down", "Próximo resultado (Enter)", lambda: self.search(1)
        )

    def tool(self, parent, icon, tip, command):
        button = MotionButton(
            parent, icon=icon, style="Ghost.TButton", height=32, command=command
        )
        button.pack(side="left", padx=1)
        Tooltip(button, tip)
        return button

    def separator(self, parent):
        tk.Frame(parent, bg=self.app.border, width=1, height=22).pack(
            side="left", padx=8
        )

    def page_view(self):
        p = self.app.motion.palette
        self.canvas = tk.Canvas(
            self.view, bg=p["sidebar"], highlightthickness=0, takefocus=True
        )
        bar = ttk.Scrollbar(
            self.view,
            orient="vertical",
            command=self.canvas.yview,
            style="Slim.Vertical.TScrollbar",
        )
        hbar = ttk.Scrollbar(self.view, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=bar.set, xscrollcommand=hbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        self.hbar = hbar
        self.view.rowconfigure(0, weight=1)
        self.view.columnconfigure(0, weight=1)
        self.canvas.bind("<Configure>", lambda e: self.schedule_draw())
        for sequence, command in [
            ("<Prior>", lambda e: self.go(self.page - 1)),
            ("<Next>", lambda e: self.go(self.page + 1)),
            ("<Left>", lambda e: self.go(self.page - 1)),
            ("<Right>", lambda e: self.go(self.page + 1)),
            ("<Home>", lambda e: self.go(0)),
            ("<End>", lambda e: self.go(self.pdf.count - 1)),
            ("<Up>", lambda e: self.canvas.yview_scroll(-3, "units")),
            ("<Down>", lambda e: self.canvas.yview_scroll(3, "units")),
            ("<Control-plus>", lambda e: self.step_zoom(1)),
            ("<Control-equal>", lambda e: self.step_zoom(1)),
            ("<Control-minus>", lambda e: self.step_zoom(-1)),
            ("<Control-f>", lambda e: self.search_entry.focus_set()),
            ("<Control-d>", lambda e: self.toggle_bookmark()),
            ("<Escape>", lambda e: self.app.reading_focus(False)),
        ]:
            self.canvas.bind(sequence, command)
        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set())
        self.canvas.bind("<MouseWheel>", lambda e: self.wheel(-1 if e.delta > 0 else 1))
        self.canvas.bind("<Button-4>", lambda e: self.wheel(-1))
        self.canvas.bind("<Button-5>", lambda e: self.wheel(1))

    def wheel(self, direction):
        top, bottom = self.canvas.yview()
        if direction > 0 and bottom >= 0.999:
            self.go(self.page + 1, top=True)
        elif direction < 0 and top <= 0.001:
            self.go(self.page - 1, top=False)
        else:
            self.canvas.yview_scroll(direction * 3, "units")

    # Side panels ---------------------------------------------------------

    def side_panel(self):
        for widget in self.side.winfo_children():
            widget.destroy()
        p = self.app.motion.palette
        Segmented(
            self.side,
            self.app,
            [("indice", "Índice"), ("marcadores", "Marcadores")],
            self.panel,
            self.change_panel,
            height=30,
        ).pack(padx=12, pady=12, anchor="w")
        holder = tk.Frame(self.side, bg=p["surface"])
        holder.pack(fill="both", expand=True, padx=6, pady=(0, 10))
        if self.panel == "indice":
            entries = self.pdf.outline()
            if not entries:
                wrapping(
                    label(
                        holder,
                        self.app,
                        "Este PDF não traz índice embutido. Use a busca ou os marcadores.",
                        size=9,
                        tone="muted",
                    )
                ).pack(fill="x", padx=8, pady=6)
            for title, level, page in entries[:400]:
                self.link(holder, title, page, indent=min(level, 4) * 14)
            return
        marks = self.service.bookmarks(self.lesson["id"], self.version)
        if not marks:
            wrapping(
                label(
                    holder,
                    self.app,
                    "Sem marcadores nesta versão. Use o ícone de marcador ou Ctrl+D.",
                    size=9,
                    tone="muted",
                )
            ).pack(fill="x", padx=8, pady=6)
        for mark in marks:
            self.link(
                holder,
                f"Página {mark['page']}"
                + (f" · {mark['label']}" if mark["label"] else ""),
                mark["page"] - 1,
            )

    def link(self, parent, text, page, indent=0):
        p = self.app.motion.palette
        row = tk.Label(
            parent,
            text=text,
            bg=p["surface"],
            fg=p["fg"],
            anchor="w",
            justify="left",
            font=ui_font(parent, size=9),
            cursor="hand2",
            padx=8 + indent,
            pady=5,
            takefocus=True,
        )
        row.pack(fill="x")
        wrapping(row, 12, 80)
        row.bind("<Button-1>", lambda e: self.go(page))
        row.bind("<Return>", lambda e: self.go(page))
        row.bind("<Enter>", lambda e: row.configure(bg=p["hover"]))
        row.bind("<Leave>", lambda e: row.configure(bg=p["surface"]))

    def change_panel(self, key):
        self.panel = key
        self.app.store.set_pref("reader_panel", key)
        self.side_panel()

    def notes_panel(self):
        for widget in self.notes.winfo_children():
            widget.destroy()
        p = self.app.motion.palette
        head = tk.Frame(self.notes, bg=p["surface"])
        head.pack(fill="x", padx=14, pady=(12, 6))
        label(head, self.app, "Notas", size=11, weight="bold").pack(side="left")
        label(head, self.app, "salvas neste computador", size=9, tone="faint").pack(
            side="left", padx=8
        )
        self.note_text = tk.Text(
            self.notes,
            height=5,
            width=30,
            wrap="word",
            bg=p["raised"],
            fg=p["fg"],
            insertbackground=p["fg"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=p["border"],
            highlightcolor=p["accent"],
            font=ui_font(self.notes, size=10),
            padx=8,
            pady=6,
        )
        self.note_text.pack(fill="x", padx=14)
        self.note_page = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.notes,
            text="Ligar à página atual",
            variable=self.note_page,
            style="Panel.TCheckbutton",
        ).pack(anchor="w", padx=12, pady=4)
        MotionButton(
            self.notes,
            text="Salvar nota",
            icon="check",
            command=self.add_note,
            height=32,
        ).pack(anchor="w", padx=14, pady=(0, 10))
        tk.Frame(self.notes, bg=p["border"], height=1).pack(fill="x")
        from app import Scroll

        area = Scroll(self.notes, style="Panel.TFrame")
        area.pack(fill="both", expand=True, pady=(4, 6))
        notes = self.service.notes(self.lesson["id"])
        if not notes:
            wrapping(
                label(
                    area.body,
                    self.app,
                    "Nenhuma nota ainda. Notas não alteram o PDF.",
                    size=9,
                    tone="muted",
                )
            ).pack(fill="x", padx=14, pady=8)
        for note in notes:
            self.note_row(area.body, note)

    def note_row(self, parent, note):
        p = self.app.motion.palette
        box = tk.Frame(parent, bg=p["surface"])
        box.pack(fill="x", padx=14, pady=(6, 2))
        where = f"página {note['page']}" if note["page"] else "aula inteira"
        older = note["version"] != self.version
        meta = f"{where} · versão {note['version']}" + (
            " (outra edição)" if older else ""
        )
        line = tk.Frame(box, bg=p["surface"])
        line.pack(fill="x")
        jump = label(
            line,
            self.app,
            meta,
            size=8,
            tone="warning" if older else "faint",
            cursor="hand2" if note["page"] and not older else "",
        )
        jump.pack(side="left")
        if note["page"] and not older:
            jump.bind("<Button-1>", lambda e: self.go(note["page"] - 1))
        ActionMenu(
            line,
            self.app,
            [
                ("Editar nota", lambda: self.edit_note(note)),
                ("Excluir nota", lambda: self.remove_note(note), "danger"),
            ],
            height=24,
        ).pack(side="right")
        wrapping(label(box, self.app, note["text"], size=10)).pack(
            fill="x", pady=(2, 4)
        )

    def add_note(self):
        text = self.note_text.get("1.0", "end").strip()
        if not text:
            return
        self.service.save_note(
            self.lesson["id"],
            self.version,
            text,
            self.page + 1 if self.note_page.get() else None,
        )
        self.notes_panel()

    def edit_note(self, note):
        from app import Form

        Form(
            self.app,
            "Editar nota",
            [("text", "Nota", "text")],
            lambda v: (
                self.service.save_note(
                    self.lesson["id"],
                    note["version"],
                    v["text"],
                    note["page"],
                    note["id"],
                ),
                self.notes_panel(),
            ),
            dict(text=note["text"]),
        )

    def remove_note(self, note):
        from app import messagebox

        if messagebox.askyesno(
            "Excluir nota", "Excluir esta nota?", parent=self.app.root
        ):
            self.service.delete_note(note["id"])
            self.notes_panel()

    def layout_panels(self):
        side = self.app.store.pref("reader_side", True)
        if side:
            self.side.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        else:
            self.side.grid_remove()
        if self.notes_open:
            self.notes.grid(row=0, column=2, sticky="ns", padx=(10, 0))
        else:
            self.notes.grid_remove()
        self.side_button.select(side)
        self.notes_button.select(self.notes_open)
        self.schedule_draw()

    def toggle_side(self):
        self.app.store.set_pref(
            "reader_side", not self.app.store.pref("reader_side", True)
        )
        self.layout_panels()

    def toggle_notes(self):
        self.notes_open = not self.notes_open
        self.app.store.set_pref("reader_notes", self.notes_open)
        self.layout_panels()

    def toggle_focus(self):
        self.app.reading_focus(not self.app.focus_reading)
        self.canvas.focus_set()

    # Pages ---------------------------------------------------------------

    def scale(self):
        width, height = self.pdf.size(self.page)
        room_w = max(200, self.canvas.winfo_width() - 40)
        room_h = max(200, self.canvas.winfo_height() - 40)
        if self.zoom is not None:
            return self.zoom
        if self.fit == "page":
            return min(room_w / width, room_h / height)
        return room_w / width

    def schedule_draw(self):
        job = getattr(self, "draw_job", None)
        if job:
            self.after_cancel(job)
        self.draw_job = self.after(60, self.draw)

    def draw(self, top=True):
        self.draw_job = None
        if not self.winfo_exists():
            return
        scale = self.scale()
        image = self.pdf.render(self.page, scale)
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        x = max(20, (cw - image.width()) / 2)
        border = self.app.motion.palette["strong"]
        self.canvas.create_rectangle(
            x - 1, 19, x + image.width(), 20 + image.height(), outline=border, width=1
        )
        self.canvas.create_image(x, 20, image=image, anchor="nw")
        self.offset = (x, 20, scale)
        self.highlight()
        self.canvas.configure(
            scrollregion=(0, 0, max(cw, image.width() + 40), image.height() + 40)
        )
        if image.width() + 40 > cw:
            self.hbar.grid()
        else:
            self.hbar.grid_remove()
        self.zoom_label.configure(text=f"{round(scale * 100)}%")
        self.page_var.set(str(self.page + 1))
        marked = any(
            m["page"] == self.page + 1
            for m in self.service.bookmarks(self.lesson["id"], self.version)
        )
        self.star.configure(icon="bookmark-check" if marked else "bookmark")
        self.star.select(marked)
        self.refresh_reading()

    def refresh_reading(self):
        reading = self.service.reading(self.lesson["id"], self.version, self.pdf.count)
        self.read_var.set(self.page + 1 in reading["read_pages"])
        text = f"{len(reading['read_pages'])} de {self.pdf.count} páginas lidas"
        if reading["completed"]:
            text += " · Leitura concluída"
        self.read_status.configure(text=text)

    def mark_read(self):
        try:
            self.service.mark_page(
                self.lesson["id"],
                self.version,
                self.page + 1,
                self.pdf.count,
                self.read_var.get(),
            )
        except (ValueError, OSError) as exc:
            from app import messagebox

            messagebox.showerror(
                "Não foi possível marcar a página", str(exc), parent=self.app.root
            )
        self.refresh_reading()

    def go(self, index, save=True, top=True):
        if not 0 <= index < self.pdf.count:
            return
        self.page = index
        self.draw()
        self.canvas.yview_moveto(0 if top else 1)
        if save:
            self.schedule_save()

    def schedule_save(self):
        if self.save_job:
            self.after_cancel(self.save_job)
        self.save_job = self.after(400, self.save_position)

    def save_position(self):
        self.save_job = None
        self.service.save_position(
            self.lesson["id"], self.version, self.page + 1, self.pdf.count
        )

    def jump(self, event=None):
        try:
            self.go(int(self.page_var.get()) - 1)
        except ValueError:
            self.page_var.set(str(self.page + 1))

    def step_zoom(self, direction):
        current = self.scale()
        options = [
            z
            for z in ZOOMS
            if (z > current + 0.01 if direction > 0 else z < current - 0.01)
        ]
        if options:
            self.zoom = options[0] if direction > 0 else options[-1]
            self.fit_control.value = None
            self.fit_control.draw()
            self.draw()

    def set_fit(self, key):
        self.fit = key
        self.zoom = None
        self.draw()

    def toggle_bookmark(self):
        self.service.toggle_bookmark(self.lesson["id"], self.version, self.page + 1)
        self.draw()
        if self.panel == "marcadores":
            self.side_panel()

    # Search --------------------------------------------------------------

    def search(self, direction):
        term = self.search_var.get().strip()
        if not term:
            return
        if getattr(self, "searched", None) != term:
            self.searched = term
            self.hits = []
            self.hit_index = -1
            if not self.pdf.has_text():
                self.search_info.configure(text="PDF sem texto: busca indisponível")
                Tooltip(
                    self.search_info,
                    "Este arquivo parece digitalizado. OCR não faz parte desta versão.",
                )
                return
            self.search_info.configure(text="Buscando…")
            self.scan(term, 0, direction)
            return
        self.next_hit(direction)

    def scan(self, term, index, direction):
        """Search a few pages per idle slice so long PDFs never freeze the window."""
        end = min(self.pdf.count, index + 8)
        for page in range(index, end):
            for rect in self.pdf.search_page(page, term):
                self.hits.append((page, rect))
        if end < self.pdf.count and self.searched == term:
            self.search_job = self.after(1, lambda: self.scan(term, end, direction))
            return
        self.search_job = None
        if not self.hits:
            self.search_info.configure(text="Nenhum resultado")
            return
        self.next_hit(direction)

    def next_hit(self, direction):
        if not self.hits:
            return
        after = (
            [i for i, (page, _) in enumerate(self.hits) if page >= self.page]
            if self.hit_index < 0
            else None
        )
        if after:
            self.hit_index = after[0]
        else:
            self.hit_index = (self.hit_index + direction) % len(self.hits)
        self.search_info.configure(text=f"{self.hit_index + 1} de {len(self.hits)}")
        page, rect = self.hits[self.hit_index]
        if page != self.page:
            self.go(page)
        else:
            self.highlight()
        x, y, scale = self.offset
        total = max(1, self.canvas.bbox("all")[3])
        self.canvas.yview_moveto(max(0, (y + rect[1] * scale - 120) / total))

    def highlight(self):
        self.canvas.delete("hit")
        x, y, scale = self.offset
        p = self.app.motion.palette
        for index, (page, (left, top, right, bottom)) in enumerate(self.hits):
            if page != self.page:
                continue
            current = index == self.hit_index
            self.canvas.create_rectangle(
                x + left * scale - 2,
                y + top * scale - 2,
                x + right * scale + 2,
                y + bottom * scale + 2,
                outline=p["primary"] if current else p["secondary"],
                width=2 if current else 1,
                tags="hit",
            )

    # Study session ---------------------------------------------------------

    def refresh_session(self):
        if not self.winfo_exists():
            return
        state = self.app.clock.state
        signature = (
            bool(state),
            state.get("lesson_id") if state else None,
            state.get("running") if state else None,
        )
        if signature == getattr(self, "session_signature", None) and state:
            # Same buttons; only the time changes on every clock tick.
            self.session_text.configure(text=self.session_caption(state))
            return
        self.session_signature = signature
        for widget in self.session.winfo_children():
            widget.destroy()
        if not state:
            if self.lesson["origin"] == "planejada":
                return
            button = MotionButton(
                self.session,
                text="Estudar esta aula",
                icon="play",
                style="Accent.TButton",
                command=lambda: self.app.study_lesson(self.lesson, self.version),
            )
            button.pack(side="right")
            Tooltip(
                button,
                "Abre o relógio com matéria, assunto e aula. Você define o tempo.",
            )
            return
        mine = state.get("lesson_id") == self.lesson["id"]
        self.session_text = label(
            self.session,
            self.app,
            self.session_caption(state),
            size=10,
            tone="accent" if mine and state["running"] else "muted",
        )
        self.session_text.pack(side="left", padx=(0, 10))
        if mine:
            MotionButton(
                self.session,
                text="Retomar" if not state["running"] else "Pausar",
                icon="play" if not state["running"] else "pause",
                style="Ghost.TButton",
                height=32,
                command=self.app.toggle_pause,
            ).pack(side="left")
            MotionButton(
                self.session,
                text="Encerrar e registrar",
                icon="check",
                height=32,
                command=self.app.finish_clock,
            ).pack(side="left", padx=(6, 0))
        else:
            MotionButton(
                self.session,
                text="Abrir relógio",
                icon="timer",
                height=32,
                command=self.app.open_clock,
            ).pack(side="left")

    def session_caption(self, state):
        from core import duration

        mine = state.get("lesson_id") == self.lesson["id"]
        return (
            (
                "Estudando esta aula · "
                if mine
                else f"Sessão ativa: {self.app.focus_subject_name()} · "
            )
            + duration(state["elapsed"])
            + ("" if state["running"] else " · pausada")
        )

    def leave(self):
        self.app.reading_focus(False)
        self.app.navigate("Campo de Treinamento")

    def cleanup(self, event):
        if event.widget is not self:
            return
        for job in (getattr(self, "draw_job", None), self.search_job, self.save_job):
            if job:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
        if self.save_job:
            self.save_position()
        if self.refresh_session in self.app.clock_listeners:
            self.app.clock_listeners.remove(self.refresh_session)
        self.pdf.close()


def unavailable(parent, app):
    """Explains the missing PDF engine instead of failing."""
    from ui_kit import empty

    return empty(
        parent,
        app,
        "file-text",
        "Leitor indisponível nesta instalação",
        "O leitor usa o pacote pypdfium2. Instale-o (pip install pypdfium2) ou use o "
        "executável do RUMO, que já o inclui. Suas notas e o progresso continuam salvos.",
    )


def page_ranges(pages):
    """[1,2,3,5] -> "1-3, 5"."""
    parts, start, previous = [], None, None
    for page in sorted(set(pages)):
        if start is None:
            start = previous = page
        elif page == previous + 1:
            previous = page
        else:
            parts.append(f"{start}-{previous}" if start != previous else str(start))
            start = previous = page
    if start is not None:
        parts.append(f"{start}-{previous}" if start != previous else str(start))
    return ", ".join(parts)


def parse_ranges(text, limit):
    """ "1-3, 5" -> [1,2,3,5]; recusa páginas fora de 1..limit."""
    chosen = set()
    for part in (text or "").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        bounds = part.split("-")
        if len(bounds) > 2 or not all(b.strip().isdigit() for b in bounds):
            raise ValueError(f"Intervalo inválido: {part}")
        first, last = int(bounds[0]), int(bounds[-1])
        if not 1 <= first <= last <= limit:
            raise ValueError(f"Páginas fora desta versão (1 a {limit}): {part}")
        chosen.update(range(first, last + 1))
    if not chosen:
        raise ValueError("Informe ao menos uma página.")
    return sorted(chosen)
