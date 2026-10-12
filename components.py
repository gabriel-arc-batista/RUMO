"""Lightweight study controls, drawn locally without a browser or image assets."""

import tkinter as tk
from tkinter import ttk
from ui import MotionButton, glyph, palette_of, rounded


class SearchSelect(ttk.Frame):
    """A searchable picker. Stable mapping keys remain separate from database IDs."""

    def __init__(self, parent, textvariable, values=(), state="readonly"):
        super().__init__(parent, style="Panel.TFrame")
        self.variable = textvariable
        self.values = list(values)
        self.editable = state == "normal"
        self.popup = None
        p = palette_of(parent)
        # One bordered field: entry and chevron read as a single control.
        self.box = tk.Frame(
            self, bg=p["raised"], highlightthickness=1, highlightbackground=p["border"]
        )
        self.box.pack(fill="x")
        self.entry = ttk.Entry(
            self.box,
            textvariable=textvariable,
            state="normal" if self.editable else "readonly",
            style="Field.TEntry",
        )
        self.entry.pack(side="left", fill="x", expand=True)
        self.button = MotionButton(
            self.box,
            icon="chevron-down",
            text="" if glyph(self, "chevron-down") else "⌄",
            style="Ghost.TButton",
            height=34,
            command=self.open,
        )
        self.button.pack(side="right", padx=(0, 3))
        for widget in (self.entry, self.button):
            widget.bind("<FocusIn>", lambda e: self.highlight(True), add="+")
            widget.bind("<FocusOut>", lambda e: self.highlight(False), add="+")
        if not self.editable:
            self.entry.bind("<Button-1>", lambda e: self.open())
            self.entry.configure(cursor="hand2")
        self.entry.bind("<Down>", lambda e: self.open())
        self.bind("<Destroy>", self.cleanup, add="+")

    def highlight(self, focused):
        p = palette_of(self)
        if self.box.winfo_exists():
            self.box.configure(
                highlightbackground=p["accent"] if focused else p["border"]
            )

    def focus_set(self):
        self.entry.focus_set()

    def get(self):
        return self.variable.get()

    def configure(self, cnf=None, **kwargs):
        if "values" in kwargs:
            self.values = list(kwargs.pop("values"))
        return super().configure(cnf, **kwargs)

    config = configure

    def cleanup(self, event):
        if event.widget == self and self.popup and self.popup.winfo_exists():
            self.popup.destroy()

    def open(self):
        if self.popup and self.popup.winfo_exists():
            self.popup.lift()
            return
        motion = self.winfo_toplevel()._root()._motion
        p = motion.palette
        win = tk.Toplevel(self)
        self.popup = win
        win.title("Escolher assunto" if len(self.values) > 30 else "Escolher opção")
        win.transient(self.winfo_toplevel())
        win.configure(bg=p["surface"])
        win.geometry("720x520")
        win.minsize(520, 400)
        win.columnconfigure(0, weight=1)
        win.rowconfigure(1, weight=1)
        header = ttk.Frame(win, style="Panel.TFrame")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 12))
        ttk.Label(
            header, text="Encontre o que você vai estudar", style="PanelHeading.TLabel"
        ).pack(anchor="w")
        query = tk.StringVar()
        entry = ttk.Entry(header, textvariable=query)
        entry.pack(fill="x", pady=(12, 0))
        area = ttk.Frame(win, style="Panel.TFrame")
        area.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 12))
        items = tk.Listbox(
            area,
            bg=p["surface"],
            fg=p["fg"],
            selectbackground=p["selected"],
            selectforeground=p["accent"],
            font=("Inter", 10),
            relief="flat",
            highlightthickness=0,
            activestyle="none",
            exportselection=False,
        )
        bar = ttk.Scrollbar(area, command=items.yview)
        items.configure(yscrollcommand=bar.set)
        items.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        preview = ttk.Label(
            win, text="", style="PanelMuted.TLabel", wraplength=660, justify="left"
        )
        preview.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 12))
        preview.bind(
            "<Configure>",
            lambda e: (
                preview.configure(wraplength=max(100, e.width - 8))
                if int(preview.cget("wraplength")) != max(100, e.width - 8)
                else None
            ),
        )
        shown = []

        def selected_label(event=None):
            preview.configure(
                text=shown[items.curselection()[0]] if items.curselection() else ""
            )

        items.bind("<<ListboxSelect>>", selected_label)

        def filter_values(*args):
            from edital import normalized

            term = normalized(query.get())
            shown[:] = [v for v in self.values if term in normalized(v)]
            items.delete(0, "end")
            for value in shown:
                items.insert("end", value or "Sem assunto / todo o plano")
            if shown:
                items.selection_set(0)
            selected_label()

        def choose(event=None):
            if not items.curselection():
                return
            self.variable.set(shown[items.curselection()[0]])
            win.destroy()
            self.event_generate("<<ComboboxSelected>>")
            self.focus_set()

        items.bind("<Double-1>", choose)
        items.bind("<Return>", choose)
        entry.bind("<Return>", choose)
        entry.bind("<Down>", lambda e: items.focus_set())
        win.bind("<Escape>", lambda e: win.destroy())
        footer = ttk.Frame(win, style="Panel.TFrame")
        footer.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 16))
        ttk.Label(
            footer,
            text="Digite para filtrar • Enter para escolher",
            style="PanelMuted.TLabel",
        ).pack(side="left")
        MotionButton(
            footer, text="Selecionar", style="Accent.TButton", height=42, command=choose
        ).pack(side="right")
        query.trace_add("write", filter_values)
        filter_values()
        motion.reveal(win)
        from ui import activate_popup

        activate_popup(win, entry)


class CompletionBox(MotionButton):
    """Visible square checkbox. Green means completion, gold remains the identity."""

    def __init__(self, parent, done, **kwargs):
        self.done = bool(done)
        super().__init__(
            parent, text="✓" if done else "□", width=3, height=34, **kwargs
        )

    def configure(self, cnf=None, **kwargs):
        if "text" in kwargs:
            self.done = kwargs["text"] == "✓"
        return super().configure(cnf, **kwargs)

    config = configure

    def draw(self):
        self.delete("all")
        p = self.motion.palette
        w = self.winfo_width()
        h = self.winfo_height()
        x = w / 2 - 11
        y = h / 2 - 11
        rounded(
            self,
            x,
            y,
            22,
            22,
            5,
            fill=p["success_bg"] if self.done else p["surface"],
            outline=(
                p["success"]
                if self.done
                else p["accent"] if self.hover or self.focused else p["muted"]
            ),
            width=1.5,
        )
        if self.done:
            self.create_line(
                x + 5,
                y + 11,
                x + 9,
                y + 15,
                x + 17,
                y + 7,
                fill=p["success"],
                width=2.4,
                capstyle="round",
                joinstyle="round",
            )
