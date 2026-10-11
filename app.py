import csv
import ctypes
import json
import logging
import os
import sys
import tkinter as tk
import webbrowser
from security import web_url, directory_path
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import ttk, filedialog
from tkinter import font as tkfont
from contextlib import contextmanager

from core import (
    Store,
    Clock,
    COLORS,
    data_dir,
    duration,
    parse_duration,
    ratio,
    percentage,
    uid,
)
from ui import (
    Motion,
    MotionButton,
    MetricCard,
    FocusDial,
    Panel,
    ClockButton,
    load_fonts,
    blend,
)
from syllabus import expand_bacen
from components import SearchSelect

ASSETS = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets"
SECTIONS = [
    "Início",
    "Ciclo de estudos",
    "Edital e assuntos",
    "Revisões",
    "Estatísticas",
    "Histórico",
    "Simulados",
    "Metas e conquistas",
    "Configurações e ajuda",
]


class Dialogs:
    """App-colored accessible confirmations, independent of Windows' theme."""

    bg = "#090909"
    surface = "#151515"
    fg = "#F5F1E8"

    def show(self, title, text, choices, parent=None):
        parent = parent or tk._default_root
        win = tk.Toplevel(parent)
        win.title(title)
        win.configure(bg=self.bg)
        win.transient(parent)
        win.geometry("640x420")
        win.minsize(400, 250)
        result = [None]
        ttk.Label(win, text=title, style="Heading.TLabel").pack(
            anchor="w", padx=20, pady=(20, 10)
        )
        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=20, pady=8)
        body = tk.Text(
            frame,
            wrap="word",
            relief="flat",
            bg=self.surface,
            fg=self.fg,
            font=("Inter", 11),
            padx=14,
            pady=14,
            takefocus=True,
        )
        bar = ttk.Scrollbar(frame, command=body.yview)
        body.configure(yscrollcommand=bar.set)
        body.insert("1.0", str(text))
        body.configure(state="disabled")
        body.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        buttons = ttk.Frame(win)
        buttons.pack(fill="x", padx=20, pady=18)

        def finish(value):
            result[0] = value
            win.destroy()

        first = None
        for label, value in choices:
            button = MotionButton(
                buttons, text=label, command=lambda v=value: finish(v)
            )
            button.pack(side="right", padx=5)
            first = button
        cancel = next((v for label, v in choices if label in ["Cancelar", "Não"]), None)
        win.protocol("WM_DELETE_WINDOW", lambda: finish(cancel))
        win.bind("<Escape>", lambda e: finish(cancel))
        win.bind("<Return>", lambda e: first.invoke())
        motion = getattr(parent._root(), "_motion", None)
        if motion:
            motion.reveal(win)
        win.grab_set()
        first.focus_set()
        win.wait_window()
        return result[0]

    def showinfo(self, title, text, parent=None):
        return self.show(title, text, [("OK", True)], parent)

    def showerror(self, title, text, parent=None):
        return self.show(title, text, [("OK", True)], parent)

    def askyesno(self, title, text, parent=None):
        return bool(self.show(title, text, [("Não", False), ("Sim", True)], parent))

    def askokcancel(self, title, text, parent=None):
        return bool(
            self.show(title, text, [("Cancelar", False), ("Confirmar", True)], parent)
        )

    def askyesnocancel(self, title, text, parent=None):
        return self.show(
            title, text, [("Cancelar", None), ("Não", False), ("Sim", True)], parent
        )


messagebox = Dialogs()


class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.pending = None
        self.popup = None
        widget.bind("<Enter>", self.enter, add="+")
        widget.bind("<Leave>", self.leave, add="+")
        widget.bind("<Destroy>", self.leave, add="+")

    def enter(self, event):
        self.pending = self.widget.after(450, self.show)

    def show(self):
        if not self.widget.winfo_exists():
            return
        self.popup = tk.Toplevel(self.widget)
        self.popup.overrideredirect(True)
        self.popup.configure(bg=messagebox.surface)
        self.popup.geometry(
            f"+{self.widget.winfo_rootx()+10}+{self.widget.winfo_rooty()+self.widget.winfo_height()+4}"
        )
        tk.Label(
            self.popup,
            text=self.text,
            bg=messagebox.surface,
            fg=messagebox.fg,
            padx=10,
            pady=6,
            font=("Inter", 10),
        ).pack()

    def leave(self, event=None):
        if self.pending:
            try:
                self.widget.after_cancel(self.pending)
            except tk.TclError:
                pass
            self.pending = None
        if self.popup:
            try:
                self.popup.destroy()
            except tk.TclError:
                pass
            self.popup = None


class Scroll(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.body = ttk.Frame(self.canvas)
        self.window = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.body.bind(
            "<Configure>",
            lambda e=None: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        def resize(event):
            width = event.width
            self.canvas.itemconfigure(self.window, width=width)
            self.canvas.coords(self.window, max(0, (event.width - width) / 2), 0)

        self.canvas.bind("<Configure>", resize)
        self.canvas.bind("<Enter>", self.bind_wheel)
        self.canvas.bind(
            "<Leave>", lambda e=None: self.canvas.unbind_all("<MouseWheel>")
        )

    def bind_wheel(self, e):
        self.canvas.bind_all(
            "<MouseWheel>",
            lambda event: self.canvas.yview_scroll(int(-event.delta / 120), "units"),
        )


class Form:
    def __init__(self, app, title, fields, save, initial=None, width=740):
        self.app = app
        self.save_callback = save
        self.vars = {}
        self.widgets = {}
        self.initial = initial or {}
        self.win = tk.Toplevel(app.root)
        self.win.title(title)
        self.win.geometry(f"{width}x{690 if len(fields)>8 else 640}")
        self.win.minsize(520, 430)
        self.win.configure(bg=app.bg)
        self.win.transient(app.root)
        outer = Scroll(self.win)
        outer.pack(fill="both", expand=True, padx=18, pady=12)
        outer.canvas.configure(bg=app.bg)
        self.body = outer.body
        ttk.Label(self.body, text=title, style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(4, 6)
        )
        ttk.Label(
            self.body,
            text=(
                "Seu foco começa aqui. Escolha o conteúdo e ajuste ao seu ritmo."
                if title == "Iniciar estudo"
                else "Organize os detalhes do seu estudo. Tudo fica salvo neste computador."
            ),
            style="Muted.TLabel",
            wraplength=width - 80,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 20))
        self.body.columnconfigure(0, weight=1)
        self.body.columnconfigure(1, weight=1)
        preferences = title == "Preferências locais"
        session = len(fields) > 15 and not preferences
        self.notebook = None
        groups = {}
        positions = {}
        if session or preferences:
            self.notebook = ttk.Notebook(self.body)
            self.notebook.grid(row=2, column=0, columnspan=2, sticky="ew")
            for name in (
                ["Aparência", "Rotina e foco", "Revisões", "Dados e avisos"]
                if preferences
                else ["Sessão", "Questões", "Materiais e notas", "Revisões"]
            ):
                groups[name] = ttk.Frame(
                    self.notebook, style="Panel.TFrame", padding=18
                )
                self.notebook.add(groups[name], text=name)
                positions[name] = 0
        else:
            panel = Panel(self.body, app)
            panel.grid(row=2, column=0, columnspan=2, sticky="ew")
            groups["Dados"] = panel.body
            positions["Dados"] = 0
        for frame in groups.values():
            frame.columnconfigure(0, weight=1)
        if title == "Iniciar estudo":
            groups["Dados"].columnconfigure(1, weight=1)
        for row, field in enumerate(fields, 1):
            key, label, kind, *rest = field
            value = self.initial.get(key, rest[1] if len(rest) > 1 else "")
            name = (
                (
                    "Questões"
                    if key
                    in [
                        "correct",
                        "wrong",
                        "blank",
                        "total",
                        "results",
                        "mock_name",
                        "mock_format",
                        "score_correct",
                        "score_wrong",
                        "score_blank",
                    ]
                    else (
                        "Materiais e notas"
                        if key
                        in [
                            "material",
                            "url",
                            "pages",
                            "video_text",
                            "next_step",
                            "notes",
                        ]
                        else (
                            "Revisões"
                            if key in ["schedule", "base", "intervals", "apply_block"]
                            else "Sessão"
                        )
                    )
                )
                if session
                else "Dados"
            )
            if preferences:
                name = (
                    "Aparência"
                    if key
                    in [
                        "animations",
                        "theme",
                        "motivation",
                        "profile",
                        "show_main_goal",
                    ]
                    else (
                        "Revisões"
                        if key
                        in [
                            "review_intervals",
                            "streak_min_minutes",
                            "eligible_days",
                            "week_start",
                        ]
                        else (
                            "Dados e avisos"
                            if key
                            in [
                                "retention",
                                "timezone",
                                "time_format",
                                "sound",
                                "notifications",
                                "achievements",
                                "night_achievement",
                            ]
                            else "Rotina e foco"
                        )
                    )
                )
            frame = ttk.Frame(groups[name], style="Panel.TFrame")
            if title == "Iniciar estudo":
                grid_row = {
                    "subject": 0,
                    "topic": 1,
                    "category": 2,
                    "mode": 2,
                    "target": 3,
                }[key]
                frame.grid(
                    row=grid_row,
                    column=1 if key == "mode" else 0,
                    columnspan=1 if key in ["category", "mode"] else 2,
                    sticky="ew",
                    pady=(0, 10),
                    padx=(
                        (0, 10)
                        if key == "category"
                        else (10, 0) if key == "mode" else 0
                    ),
                )
            else:
                frame.grid(row=positions[name], column=0, sticky="ew", pady=(0, 12))
            positions[name] += 1
            ttk.Label(
                frame, text=label, style="PanelMuted.TLabel", wraplength=width - 100
            ).pack(anchor="w", pady=(0, 5))
            if kind == "bool":
                var = tk.BooleanVar(value=bool(value))
                widget = ttk.Checkbutton(
                    frame, text="Ativar", variable=var, style="Panel.TCheckbutton"
                )
            elif kind == "text":
                var = None
                widget = tk.Text(
                    frame,
                    height=4,
                    wrap="word",
                    bg=app.surface,
                    fg=app.fg,
                    insertbackground=app.fg,
                    relief="flat",
                    font=("Inter", 10),
                    padx=12,
                    pady=10,
                    highlightthickness=1,
                    highlightbackground=app.border,
                    highlightcolor=app.motion.palette["accent"],
                )
                widget.insert("1.0", str(value or ""))
            else:
                var = tk.StringVar(value="" if value is None else str(value))
                if kind in ["choice", "editable"]:
                    widget = SearchSelect(
                        frame,
                        textvariable=var,
                        values=rest[0],
                        state="readonly" if kind == "choice" else "normal",
                    )
                else:
                    widget = ttk.Entry(frame, textvariable=var)
            widget.pack(fill="x")
            self.vars[key] = var
            self.widgets[key] = widget
        footer = ttk.Frame(self.win)
        footer.pack(fill="x", padx=18, pady=12)
        self.error = ttk.Label(footer, text="", foreground="#E16F87", wraplength=500)
        self.error.pack(side="left", fill="x", expand=True)
        MotionButton(footer, text="Cancelar", command=self.win.destroy).pack(
            side="right", padx=5
        )
        self.save_button = MotionButton(
            footer,
            text="Começar meu foco" if title == "Iniciar estudo" else "Salvar",
            style="Accent.TButton",
            command=self.submit,
        )
        self.save_button.pack(side="right")
        self.win.bind("<Escape>", lambda e: self.win.destroy())
        self.win.bind("<Control-Return>", lambda e: self.submit())
        app.motion.idle(
            self.win,
            lambda: (
                next(iter(self.widgets.values())).focus_set() if self.widgets else None
            ),
            "initial-focus",
        )
        app.motion.reveal(self.win)

    def values(self):
        return {
            key: (var.get() if var else self.widgets[key].get("1.0", "end-1c"))
            for key, var in self.vars.items()
        }

    def submit(self):
        self.save_button.configure(state="disabled")
        try:
            self.save_callback(self.values())
            self.win.destroy()
            if getattr(self, "refresh_on_submit", True):
                self.app.refresh()
        except Exception as e:
            self.error.configure(text=str(e))
            self.save_button.configure(state="normal")
            if not isinstance(e, ValueError):
                logging.exception("Form submission")


class App:
    def __init__(self, root, store=None):
        self.root = root
        self.store = store or Store()
        self.clock = Clock(self.store)
        self.app_icon = tk.PhotoImage(file=str(ASSETS / "RUMO.png"))
        root.iconphoto(True, self.app_icon)
        if os.name == "nt":
            root.iconbitmap(str(ASSETS / "RUMO.ico"))
        self.font_family = load_fonts(root, ASSETS)
        self.motion = Motion(root)
        root._motion = self.motion
        self.store.set_pref("design_version", "inter-v4")
        self.section = "Início"
        self.filters = {}
        self.history_offset = 0
        self.week_offset = 0
        self.streak_offset = 0
        self.chart_mode = "Tempo"
        self.group = "day"
        self.clock_win = None
        self.sidebar_visible = self.store.pref("sidebar_visible", True)
        self.edital_expanded = set()
        self.edital_selected = None
        self.edital_search = ""
        self.plan = self.store.pref("active_plan")
        if not self.store.one("SELECT id FROM plans WHERE id=?", (self.plan,)):
            p = self.store.one("SELECT id FROM plans WHERE archived=0 LIMIT 1")
            if p:
                self.plan = p["id"]
            else:
                source = json.loads(
                    (ASSETS / "bacen2024.json").read_text(encoding="utf-8")
                )
                for area, rows in source["areas"].items():
                    pid = self.store.save(
                        "plans",
                        {
                            "name": "BACEN 2024 — " + area,
                            "description": "Referência histórica: Edital nº 1 de 15/01/2024, seção 18. Sem data de nova prova. Não consolida retificações.",
                        },
                    )
                    self.store.import_topics(pid, rows)
                    if area == "Tecnologia da Informação":
                        self.plan = pid
                self.store.set_pref("bacen_source", source["source"])
            self.store.set_pref("active_plan", self.plan)
        guide = json.loads(
            (ASSETS / "bacen2024-detalhado.json").read_text(encoding="utf-8")
        )
        for area, outline in guide["areas"].items():
            for plan in self.store.rows(
                "SELECT id FROM plans WHERE name=? AND archived=0",
                ("BACEN 2024 — " + area,),
            ):
                expand_bacen(self.store, plan["id"], outline, guide["version"])
        if self.store.pref("create_guided_cycle", False):
            from learning import create_starter_cycle

            create_starter_cycle(self.store, self.plan)
            self.store.set_pref("create_guided_cycle", False)
        self.root.title("RUMO — Estudos • Estudos locais")
        left = top = 0
        available_width = root.winfo_screenwidth()
        available_height = root.winfo_screenheight()
        if os.name == "nt":
            from ctypes import wintypes

            work = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(work), 0):
                left, top = work.left, work.top
                available_width = work.right - work.left
                available_height = work.bottom - work.top
        self.root.geometry(
            f"{min(1280,available_width-32)}x{min(800,available_height-64)}+{left+16}+{top+16}"
        )
        self.root.minsize(900, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.report_callback_exception = self.callback_error
        self.apply_theme()
        self.build_shell()
        self.refresh()
        self.root.after(500, self.tick)
        self.motion.reveal(self.root)
        try:
            self.store.auto_backup()
        except Exception as e:
            logging.exception("Automatic backup")
            self.root.after(
                200,
                lambda: self.notify(
                    "Não foi possível criar o backup automático. Confira o destino em Configurações."
                ),
            )
        if self.clock.state:
            self.root.after(
                400,
                lambda: self.notify(
                    "Sessão recuperada e pausada. Abra o relógio para retomar, ajustar ou finalizar."
                ),
            )

    def callback_error(self, kind, value, tb):
        logging.error("Callback error", exc_info=(kind, value, tb))
        messagebox.showerror("Não foi possível concluir", str(value), parent=self.root)

    def apply_theme(self):
        theme = self.store.pref("theme", "Escuro")
        if theme == "Sistema":
            try:
                import winreg

                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                ) as key:
                    dark = not winreg.QueryValueEx(key, "AppsUseLightTheme")[0]
            except Exception:
                dark = True
        else:
            dark = theme != "Claro"
        self.bg = "#101113" if dark else "#F3F4F6"
        self.surface = "#191B1F" if dark else "#FFFFFF"
        self.fg = "#F0EEE9" if dark else "#242424"
        self.muted = "#A4A6AD" if dark else "#525866"
        self.border = "#303238" if dark else "#DCE1E8"
        self.motion.enabled = bool(self.store.pref("animations", True))
        self.motion.palette = dict(
            bg=self.bg,
            surface=self.surface,
            fg=self.fg,
            muted=self.muted,
            hover="#2A2D35" if dark else "#EDF1F7",
            selected="#25231D" if dark else "#F5EDDB",
            accent="#D6B467" if dark else "#87651E",
            border=self.border,
            success="#75CFA0" if dark else "#287547",
            error="#DD7979" if dark else "#AC3B47",
        )
        messagebox.bg = self.bg
        messagebox.surface = self.surface
        messagebox.fg = self.fg
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            ".",
            background=self.bg,
            foreground=self.fg,
            font=("Inter", 9),
            bordercolor=self.border,
            lightcolor=self.border,
            darkcolor=self.border,
        )
        style.configure("TFrame", background=self.bg)
        style.configure("Card.TFrame", background=self.surface)
        style.configure("Panel.TFrame", background=self.surface)
        style.configure("Border.TFrame", background=self.border)
        style.configure("Panel.TLabel", background=self.surface, foreground=self.fg)
        style.configure(
            "PanelMuted.TLabel", background=self.surface, foreground=self.muted
        )
        style.configure(
            "PanelHeading.TLabel",
            background=self.surface,
            foreground=self.fg,
            font=("Inter", 10, "bold"),
        )
        style.configure("TLabel", background=self.bg, foreground=self.fg)
        style.configure("Muted.TLabel", foreground=self.muted)
        style.configure("Title.TLabel", font=("Inter", 17, "bold"))
        style.configure("Heading.TLabel", font=("Inter", 11, "bold"))
        style.configure("Card.TLabel", background=self.surface, foreground=self.muted)
        style.configure(
            "Value.TLabel",
            background=self.surface,
            font=("Inter", 22, "bold"),
            foreground=self.fg,
        )
        style.configure(
            "TButton",
            background=self.surface,
            foreground=self.fg,
            padding=(12, 8),
            borderwidth=1,
        )
        style.map(
            "TButton",
            background=[("active", self.border)],
            foreground=[("disabled", self.muted)],
        )
        style.configure("Accent.TButton", background="#D6B467", foreground="#FFFFFF")
        style.map(
            "Accent.TButton",
            background=[("active", "#EACB84"), ("disabled", self.border)],
        )
        style.configure(
            "TEntry",
            fieldbackground="#22252B" if dark else "#F7F8FA",
            foreground=self.fg,
            insertcolor=self.fg,
            padding=(12, 10),
            borderwidth=1,
            lightcolor=self.border,
            darkcolor=self.border,
            bordercolor=self.border,
        )
        style.map(
            "TEntry",
            fieldbackground=[("readonly", "#22252B" if dark else "#F7F8FA")],
            foreground=[("readonly", self.fg)],
            bordercolor=[("focus", self.motion.palette["accent"])],
            lightcolor=[("focus", self.motion.palette["accent"])],
            darkcolor=[("focus", self.motion.palette["accent"])],
        )
        style.configure("TNotebook", background=self.surface, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=self.bg,
            foreground=self.muted,
            padding=(14, 10),
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.surface)],
            foreground=[("selected", self.motion.palette["accent"])],
        )
        style.configure(
            "Panel.TCheckbutton", background=self.surface, foreground=self.fg
        )
        style.map("Panel.TCheckbutton", background=[("active", self.surface)])
        style.configure(
            "TCombobox",
            fieldbackground=self.surface,
            background=self.surface,
            foreground=self.fg,
            padding=6,
            arrowcolor=self.fg,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.surface)],
            foreground=[("readonly", self.fg)],
            selectbackground=[("readonly", self.surface)],
            selectforeground=[("readonly", self.fg)],
        )
        style.configure(
            "Treeview",
            background=self.surface,
            fieldbackground=self.surface,
            foreground=self.fg,
            rowheight=40,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=self.surface,
            foreground=self.muted,
            font=("Inter", 9, "bold"),
            padding=(4, 8),
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", self.motion.palette["selected"])],
            foreground=[("selected", self.fg)],
        )
        style.configure("TCheckbutton", background=self.bg, foreground=self.fg)
        style.map("TCheckbutton", background=[("active", self.bg)])
        style.configure(
            "Horizontal.TProgressbar",
            background="#D6B467",
            troughcolor=self.border,
            borderwidth=0,
            thickness=6,
        )
        for name in ["Vertical.TScrollbar", "Horizontal.TScrollbar"]:
            style.configure(
                name,
                background=self.border,
                troughcolor=self.bg,
                arrowcolor=self.muted,
                borderwidth=0,
                arrowsize=11,
            )
            style.map(name, background=[("pressed", "#D6B467"), ("active", self.muted)])
        self.root.configure(bg=self.bg)
        self.root.option_add("*TCombobox*Listbox.background", self.surface)
        self.root.option_add("*TCombobox*Listbox.foreground", self.fg)
        self.root.option_add(
            "*TCombobox*Listbox.selectBackground", self.motion.palette["selected"]
        )

    def build_shell(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.clock_win = None
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=18, pady=(12, 8))
        top = ttk.Frame(header)
        top.grid(row=0, column=0, sticky="w")
        actions = ttk.Frame(header)
        actions.grid(row=0, column=1, sticky="e")
        header.columnconfigure(1, weight=1)
        menu_button = MotionButton(top, text="☰", width=3, command=self.toggle_sidebar)
        menu_button.pack(side="left")
        Tooltip(menu_button, "Recolher ou abrir o menu lateral")
        self.plan_var = tk.StringVar()
        self.plan_combo = ttk.Combobox(
            top, textvariable=self.plan_var, state="readonly", width=29
        )
        self.plan_combo.pack(side="left", padx=8)
        self.plan_combo.bind("<<ComboboxSelected>>", self.change_plan)
        MotionButton(
            actions,
            text="Adicionar estudo",
            style="Accent.TButton",
            command=self.session_form,
        ).pack(side="right", padx=5)
        MotionButton(actions, text="Tema", command=self.toggle_theme).pack(
            side="right", padx=4
        )
        MotionButton(actions, text="Avisos", command=self.notifications).pack(
            side="right", padx=4
        )
        MotionButton(
            actions,
            text="Ajuda",
            command=lambda: self.navigate("Configurações e ajuda"),
        ).pack(side="right", padx=4)
        layout = [None]

        def reflow_header(event=None):
            narrow = header.winfo_width() < 980
            if narrow == layout[0]:
                return
            layout[0] = narrow
            top.grid(row=0, column=0, columnspan=2 if narrow else 1, sticky="w")
            actions.grid(
                row=1 if narrow else 0,
                column=0 if narrow else 1,
                columnspan=2 if narrow else 1,
                sticky="e",
                pady=(5, 0) if narrow else 0,
            )

        header.bind("<Configure>", reflow_header)
        header.after_idle(reflow_header)
        from inspiration import header as quote_header

        self.quote_day = self.today()
        self.quote_header = (
            quote_header(self, header, ASSETS / "quotes.json")
            if self.store.pref("motivation", True)
            else None
        )
        self.middle = ttk.Frame(self.root)
        self.middle.pack(fill="both", expand=True)
        self.sidebar = ttk.Frame(self.middle, width=230)
        self.sidebar.pack_propagate(False)
        ttk.Label(
            self.sidebar,
            text="rumo",
            font=("Inter", 16, "bold"),
            foreground=self.motion.palette["accent"],
        ).pack(anchor="w", padx=16, pady=(14, 4))
        ttk.Label(
            self.sidebar, text="Seu estudo, no seu ritmo", style="Muted.TLabel"
        ).pack(anchor="w", padx=16, pady=(0, 16))
        ttk.Label(
            self.sidebar,
            text="LOCAL • OFFLINE\nSem conta ou assinatura",
            style="Muted.TLabel",
        ).pack(side="bottom", anchor="w", padx=12, pady=18)
        nav = Scroll(self.sidebar)
        nav.pack(fill="both", expand=True)
        nav.canvas.configure(bg=self.bg)
        self.nav_buttons = {}
        icons = ["⌂", "↻", "▤", "◷", "▥", "≡", "✎", "◇", "⚙"]
        for s, icon in zip(SECTIONS, icons):
            label = "Configurações" if s == "Configurações e ajuda" else s
            button = MotionButton(
                nav.body,
                text=f"{icon}   {label}",
                style="Nav.TButton",
                command=lambda name=s: self.navigate(name),
            )
            button.pack(fill="x", pady=3, padx=4)
            self.nav_buttons[s] = button
            Tooltip(button, s)
        self.scroll = Scroll(self.middle)
        self.scroll.pack(side="left", fill="both", expand=True, padx=20, pady=12)
        self.scroll.canvas.configure(bg=self.bg)
        self.content = self.scroll.body
        if self.sidebar_visible:
            self.sidebar.pack(side="left", fill="y", before=self.scroll)
        bottom = ttk.Frame(self.root)
        bottom.pack(fill="x", padx=18, pady=9)
        self.status = ttk.Label(
            bottom,
            text=f"Hoje, {self.today():%d/%m/%Y} • Dados salvos neste computador",
            style="Muted.TLabel",
        )
        self.status.pack(side="left")
        self.floating = ClockButton(bottom, command=self.open_clock)
        self.floating.pack(side="right")
        self.clock_tip = Tooltip(
            self.floating, "Iniciar estudo ou registrar manualmente (Ctrl+R)"
        )
        self.root.bind("<Control-n>", lambda e: self.session_form())
        self.root.bind("<Control-r>", lambda e: self.open_clock())

    def toggle_sidebar(self):
        self.sidebar_visible = not self.sidebar_visible
        self.store.set_pref("sidebar_visible", self.sidebar_visible)
        if self.sidebar_visible:
            self.sidebar.pack(side="left", fill="y", before=self.scroll)
            for index, button in enumerate(self.nav_buttons.values()):
                self.motion.animate(
                    button,
                    lambda t, b=button: b.paint(blend(self.bg, b.colors()[0], t)),
                    220 + index * 15,
                )
        else:
            self.sidebar.pack_forget()

    def toggle_theme(self):
        self.store.set_pref(
            "theme",
            "Claro" if self.store.pref("theme", "Escuro") != "Claro" else "Escuro",
        )
        self.apply_theme()
        self.build_shell()
        self.refresh()

    def refresh(self):
        plans = self.store.rows("SELECT * FROM plans WHERE archived=0 ORDER BY name")
        self.plan_map = self.readable_mapping(plans)
        self.plan_combo.configure(values=list(self.plan_map))
        self.plan_var.set(
            next(
                (n for n, p in self.plan_map.items() if p == self.plan),
                "Plano arquivado",
            )
        )
        for w in self.content.winfo_children():
            w.destroy()
        for name, button in self.nav_buttons.items():
            button.select(name == self.section)
        subtitles = [
            "Seu progresso, um estudo de cada vez.",
            "Organize o ritmo e saiba qual é o próximo passo.",
            "Transforme o conteúdo do edital em um caminho claro.",
            "Mantenha o que aprendeu por perto.",
            "Veja como seu esforço se transforma em resultado.",
            "Cada sessão faz parte da sua trajetória.",
            "Treine, avalie e ajuste sua preparação.",
            "Pequenos avanços também merecem ser vistos.",
            "Tudo do seu jeito, salvo neste computador.",
        ]
        title_row = ttk.Frame(self.content)
        title_row.pack(fill="x", pady=(2, 3))
        if self.section == "Edital e assuntos":
            MotionButton(
                title_row,
                text="Novo assunto",
                style="Accent.TButton",
                command=self.topic_form,
            ).pack(side="right")
        ttk.Label(title_row, text=self.section, style="Title.TLabel", anchor="w").pack(
            side="left", fill="x", expand=True
        )
        self.note(subtitles[SECTIONS.index(self.section)])
        if self.section == "Início" and self.store.pref("profile", ""):
            self.note("Estudos de " + self.store.pref("profile"))
        getattr(self, "page_" + str(SECTIONS.index(self.section)))()
        self.scroll.canvas.yview_moveto(0)

        def reveal_page(t):
            canvas = self.scroll.canvas
            canvas.coords(
                self.scroll.window,
                canvas.coords(self.scroll.window)[0],
                round(16 * (1 - t)),
            )
            canvas.configure(
                scrollregion=(
                    0,
                    0,
                    self.content.winfo_width(),
                    self.content.winfo_height() + 16,
                )
            )
            if t == 1:
                canvas.configure(scrollregion=canvas.bbox("all"))
                canvas.yview_moveto(0)

        self.motion.animate(self.scroll.canvas, reveal_page, 320)

    def navigate(self, section):
        self.section = section
        self.history_offset = 0
        self.refresh()

    def change_plan(self, event=None):
        self.plan = self.plan_map[self.plan_var.get()]
        self.store.set_pref("active_plan", self.plan)
        self.filters = {}
        self.history_offset = 0
        self.refresh()

    def notify(self, text):
        self.status.configure(text=f"Hoje, {self.today():%d/%m/%Y} • " + text)
        key = (self.status, "clear-notification")
        previous = self.motion.jobs.pop(key, None)
        if previous:
            self.root.after_cancel(previous)
        self.motion.watch(self.status)
        self.motion.jobs[key] = self.root.after(
            6000,
            lambda: (
                self.motion.jobs.pop(key, None),
                self.status.configure(
                    text=f"Hoje, {self.today():%d/%m/%Y} • Dados salvos neste computador"
                ),
            ),
        )

    def today(self):
        return self.store.today()

    def toolbar(self, actions):
        role = "Panel.TFrame" if getattr(self.content, "_panel", False) else "TFrame"
        row = ttk.Frame(self.content, style=role)
        row.pack(fill="x", pady=5)
        buttons = ttk.Frame(row, style=role)
        buttons.pack(side="left", fill="x", expand=True)
        widgets = [
            MotionButton(
                buttons,
                text=label,
                style=(
                    "Accent.TButton"
                    if label in ["Estudar próximo bloco", "Criar ciclo guiado"]
                    else "TButton"
                ),
                command=command,
            )
            for label, command in actions
        ]
        tips = {
            "Criar ciclo guiado": "Monta uma fila de matérias, com os assuntos na ordem de aprendizagem.",
            "Personalizar por pesos": "Escolha o tempo total; distribua mais blocos entre as matérias prioritárias.",
            "Novo ciclo vazio": "Crie uma fila e adicione seus próprios blocos.",
            "↑ Mover": "Move o bloco selecionado uma posição para cima.",
            "↓ Mover": "Move o bloco selecionado uma posição para baixo.",
            "Remover": "Retira o bloco selecionado; os estudos registrados ficam preservados.",
            "Próxima volta": "Começa uma nova passagem pela fila e preserva o histórico da volta anterior.",
            "Histórico de voltas": "Veja o tempo e as decisões das voltas anteriores.",
            "Renomear ciclo": "Muda apenas o nome deste ciclo.",
        }
        for widget in widgets:
            if widget.text in tips:
                Tooltip(widget, tips[widget.text])
        cached = [0]

        def wrap(event=None):
            width = buttons.winfo_width()
            if width < 2 or width == cached[0]:
                return
            cached[0] = width
            used = 0
            line = 0
            col = 0
            for widget in widgets:
                need = widget.winfo_reqwidth() + 7
                if used and used + need > width:
                    line += 1
                    col = 0
                    used = 0
                widget.grid(row=line, column=col, sticky="w", padx=(0, 7), pady=3)
                used += need
                col += 1

        for i, widget in enumerate(widgets):
            widget.grid(row=0, column=i, sticky="w", padx=(0, 7), pady=3)
        buttons.bind("<Configure>", wrap)
        self.motion.idle(buttons, wrap)
        return row

    def cards(self, items):
        row = ttk.Frame(self.content)
        row.pack(fill="x", pady=10)
        cards = []
        for i, (title, value, sub) in enumerate(items):
            row.columnconfigure(i, weight=1)
            card = MetricCard(row, self, title, value, sub, i)
            card.grid(row=0, column=i, sticky="nsew", padx=(0, 8))
            cards.append(card)
        previous = [0]

        def reflow(event=None):
            cols = len(cards) if row.winfo_width() > 850 else 2
            if cols == previous[0]:
                return
            previous[0] = cols
            for i in range(len(cards)):
                row.columnconfigure(i, weight=1 if i < cols else 0)
            for i, card in enumerate(cards):
                card.grid(
                    row=i // cols,
                    column=i % cols,
                    sticky="nsew",
                    padx=(0, 8),
                    pady=(0, 8),
                )

        row.bind("<Configure>", reflow)
        self.motion.idle(row, reflow)

    def heading(self, text):
        ttk.Label(
            self.content,
            text=text,
            style=(
                "PanelHeading.TLabel"
                if getattr(self.content, "_panel", False)
                else "Heading.TLabel"
            ),
        ).pack(anchor="w", pady=(8, 6))

    def note(self, text):
        panel = getattr(self.content, "_panel", False)
        label = ttk.Label(
            self.content,
            text=text,
            style="PanelMuted.TLabel" if panel else "Muted.TLabel",
            wraplength=900,
            justify="left",
            anchor="w",
        )
        label.pack(fill="x", pady=4)
        # Bind to the label's actual width; content can change while building panels.
        label.bind(
            "<Configure>",
            lambda e: (
                label.configure(wraplength=max(100, e.width - 8))
                if int(float(label.cget("wraplength"))) != max(100, e.width - 8)
                else None
            ),
        )

    @contextmanager
    def in_panel(self, panel):
        previous = self.content
        self.content = panel.body
        try:
            yield panel.body
        finally:
            self.content = previous

    def table(self, columns, rows, height=8, parent=None):
        frame = ttk.Frame(parent or self.content, style="Panel.TFrame", padding=8)
        frame.pack(fill="x", pady=8)
        tree = ttk.Treeview(
            frame,
            columns=[c[0] for c in columns],
            show="headings",
            height=min(height, max(1, len(rows))),
        )
        header_font = tkfont.Font(tree, family="Inter", size=9, weight="bold")
        minimums = {}
        for key, title, width in columns:
            minimum = max(50, header_font.measure(title) + 14)
            if key in ["time", "target", "remaining"]:
                minimum = max(minimum, header_font.measure("000:00:00") + 12)
            if key in ["name", "topic", "material", "subject"]:
                minimum = max(110, minimum)
            minimums[key] = minimum
            tree.heading(key, text=title, command=lambda k=key: self.sort_tree(tree, k))
            tree.column(
                key,
                width=max(width, minimum),
                minwidth=minimum,
                stretch=key in ["name", "topic", "material", "subject"],
                anchor=(
                    "w" if key in ["name", "topic", "material", "subject"] else "center"
                ),
            )
        vb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vb.set, xscrollcommand=hb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vb.grid(row=0, column=1, sticky="ns")
        hb.grid(row=1, column=0, sticky="ew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        if len(rows) <= height:
            vb.grid_remove()
        previous = [None]

        def fit(event=None):
            available = (
                frame.winfo_width()
                - (vb.winfo_width() if vb.winfo_ismapped() else 0)
                - 4
            )
            if available < 10 or previous[0] == available:
                return
            previous[0] = available
            required = sum(minimums.values())
            if available < required:
                hb.grid()
                return
            hb.grid_remove()
            extra = available - required
            weights = [max(1, width - minimums[key]) for key, title, width in columns]
            assigned = 0
            for index, (key, title, width) in enumerate(columns):
                allocation = (
                    available - assigned
                    if index == len(columns) - 1
                    else minimums[key] + int(extra * weights[index] / sum(weights))
                )
                tree.column(key, width=allocation, stretch=False)
                assigned += allocation

        frame.bind("<Configure>", fit)
        self.motion.idle(frame, fit)
        tree.tag_configure(
            "stripe", background="#202227" if self.surface != "#FFFFFF" else "#F7F7F6"
        )
        for index, (rid, values) in enumerate(rows):
            tree.insert(
                "",
                "end",
                iid=str(rid),
                values=values,
                tags=("stripe",) if index % 2 else (),
            )
        if not rows:
            ttk.Label(
                frame,
                text="Nenhum registro neste período. Adicione um estudo ou ajuste os filtros.",
                style="PanelMuted.TLabel",
                font=("Inter", 9, "bold"),
                wraplength=600,
            ).grid(row=2, column=0, sticky="w", pady=8)
        return tree

    def sort_tree(self, tree, key):
        values = [(tree.set(i, key), i) for i in tree.get_children("")]
        reverse = getattr(tree, "_sort_key", None) == key and not getattr(
            tree, "_sort_reverse", False
        )
        tree._sort_key = key
        tree._sort_reverse = reverse

        def convert(item):
            value = item[0]
            try:
                return (0, float(value.rstrip("%")))
            except ValueError:
                try:
                    return (0, parse_duration(value))
                except ValueError:
                    return (1, value.casefold())

        for order, (_, i) in enumerate(sorted(values, key=convert, reverse=reverse)):
            tree.move(i, "", order)

    def selected(self, tree):
        if not tree.selection():
            raise ValueError("Selecione uma linha primeiro.")
        return tree.selection()[0]

    def page_0(self):
        from inspiration import render

        s = self.store.stats(self.plan)
        p = self.store.progress(self.plan)
        self.cards(
            [
                (
                    "TEMPO DE ESTUDO",
                    duration(s["elapsed"]),
                    f"{s['days']} dias estudados",
                ),
                (
                    "DESEMPENHO",
                    percentage(s["rate"]),
                    f"{s['correct']} acertos  /  {s['wrong']} erros",
                ),
                (
                    "PROGRESSO NO EDITAL",
                    (
                        f"{p['done']*100/p['total']:.0f}%"
                        if p["total"]
                        else "Sem assuntos"
                    ),
                    f"{p['done']} de {p['total']} assuntos concluídos",
                ),
                ("QUESTÕES RESOLVIDAS", str(s["total"]), f"{s['blank']} em branco"),
            ]
        )
        parent = self.content
        panel = Panel(parent, self)
        panel.pack(fill="x", pady=(2, 12))
        current, best, days = self.store.streak(self.plan)
        with self.in_panel(panel):
            head = ttk.Frame(self.content, style="Panel.TFrame")
            head.pack(fill="x")
            ttk.Label(
                head, text="CONSTÂNCIA NOS ESTUDOS", style="PanelHeading.TLabel"
            ).pack(side="left")
            for label, step in [("›", 28), ("‹", -28)]:
                MotionButton(
                    head,
                    text=label,
                    width=2,
                    height=28,
                    command=lambda n=step: self.move_streak(n),
                ).pack(side="right", padx=2)
            finish = self.today() + timedelta(days=self.streak_offset)
            begin = finish - timedelta(days=27)
            self.note(
                f"Sequência atual: {current} dias  •  Recorde: {best} dias  •  {begin:%d/%m} a {finish:%d/%m}"
            )
            strip = tk.Canvas(
                self.content, height=38, bg=self.surface, highlightthickness=0
            )
            strip.pack(fill="x", pady=(3, 0))

            def draw_streak(event=None):
                strip.delete("all")
                cell = max(10, (strip.winfo_width() - 8) / 28)
                for i in range(28):
                    day = begin + timedelta(days=i)
                    x = 4 + i * cell
                    item = strip.create_rectangle(
                        x,
                        2,
                        x + cell - 4,
                        21,
                        fill="#D6B467" if day in days else self.border,
                        outline=self.border,
                    )
                    strip.create_text(
                        x + cell / 2 - 2,
                        31,
                        text=day.day,
                        fill=self.muted,
                        font=("Inter", 7),
                    )
                    strip.tag_bind(
                        item,
                        "<Button-1>",
                        lambda e, d=day: (
                            self.filters.update(
                                {"from": d.isoformat(), "to": d.isoformat()}
                            ),
                            self.navigate("Histórico"),
                        ),
                    )

            Tooltip(strip, "Clique em um dia para consultar os registros dessa data.")
            strip.bind("<Configure>", draw_streak)
            strip.after_idle(draw_streak)
        columns = ttk.Frame(parent)
        columns.pack(fill="x")
        left = ttk.Frame(columns)
        right = ttk.Frame(columns)
        columns.columnconfigure(0, weight=3)
        columns.columnconfigure(1, weight=2)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right.grid(row=0, column=1, sticky="nsew")
        previous = [None]

        def reflow(event=None):
            narrow = columns.winfo_width() < 940
            if narrow == previous[0]:
                return
            previous[0] = narrow
            left.grid(
                row=0,
                column=0,
                columnspan=2 if narrow else 1,
                sticky="nsew",
                padx=0 if narrow else (0, 12),
            )
            right.grid(
                row=1 if narrow else 0,
                column=0 if narrow else 1,
                columnspan=2 if narrow else 1,
                sticky="nsew",
                pady=(12, 0) if narrow else 0,
            )

        columns.bind("<Configure>", reflow)
        self.motion.idle(columns, reflow)
        subjects = Panel(left, self)
        subjects.pack(fill="x")
        with self.in_panel(subjects):
            self.heading("Suas matérias")
            rows = self.store.subject_stats(self.plan)
            for r in sorted(rows, key=lambda item: (-item["elapsed"], item["name"]))[
                :5
            ]:
                row = ttk.Frame(self.content, style="Panel.TFrame")
                row.pack(fill="x", pady=(4, 8))
                MotionButton(
                    row,
                    text="›",
                    width=3,
                    height=34,
                    command=lambda sid=r["id"]: self.subject_detail(sid),
                ).pack(side="right", padx=(8, 0))
                texts = ttk.Frame(row, style="Panel.TFrame")
                texts.pack(side="left", fill="x", expand=True)
                label = ttk.Label(
                    texts,
                    text=r["name"],
                    style="Panel.TLabel",
                    wraplength=420,
                    justify="left",
                )
                label.pack(fill="x")
                label.bind(
                    "<Configure>",
                    lambda e, w=label: (
                        w.configure(wraplength=max(100, e.width - 8))
                        if int(w.cget("wraplength")) != max(100, e.width - 8)
                        else None
                    ),
                )
                answered = r["correct"] + r["wrong"]
                rate = percentage(ratio(r["correct"], r["wrong"]))
                ttk.Label(
                    texts,
                    text=f"{duration(r['elapsed'])} de foco  •  "
                    + (
                        f"{answered} respondidas  •  {rate} de acertos"
                        if answered
                        else "Comece seu primeiro estudo"
                    ),
                    style="PanelMuted.TLabel",
                    font=("Inter", 8),
                ).pack(anchor="w", pady=(3, 0))
                tk.Frame(self.content, bg=self.border, height=1).pack(fill="x")

            def all_subjects():
                mapping = self.subject_map()
                form = Form(
                    self,
                    "Evolução por matéria",
                    [("subject", "Escolha uma matéria", "choice", list(mapping))],
                    lambda v: self.subject_detail(mapping[v["subject"]]),
                    {"subject": next(iter(mapping), "")},
                )
                form.refresh_on_submit = False
                form.save_button.configure(text="Ver evolução")

            self.toolbar([("Ver todas as matérias", all_subjects)])
        cycle_panel = Panel(left, self)
        cycle_panel.pack(fill="x", pady=(12, 0))
        with self.in_panel(cycle_panel):
            cycle = self.store.current_cycle(self.plan)
            self.heading("SEU PRÓXIMO ESTUDO")
            if cycle:
                blocks = self.store.cycle_blocks(cycle)
                b = (
                    blocks[cycle["position"]]
                    if cycle["position"] < len(blocks)
                    else None
                )
                self.note(f"{cycle['name']} • volta {cycle['lap']}")
                if b:
                    self.note(
                        f"{b['subject']} • {duration(b['elapsed'])} de {duration(b['target'])}"
                    )
                    self.toolbar(
                        [
                            ("Estudar agora", lambda: self.study_block(b, cycle)),
                            ("Ver ciclo", lambda: self.navigate("Ciclo de estudos")),
                        ]
                    )
                    next_blocks = []
                    names = set()
                    for upcoming in blocks[cycle["position"] :]:
                        next_blocks.append(upcoming)
                        names.add(upcoming["subject_id"])
                        if len(names) >= int(self.store.pref("daily_subjects", 3)):
                            break
                    self.note(
                        "Sugestão flexível: "
                        + " → ".join(x["subject"] for x in next_blocks)
                    )
                else:
                    self.note(
                        "Percurso encerrado. Inicie a próxima volta no Ciclo de estudos."
                    )
            else:
                self.note("Organize suas matérias em um ciclo flexível.")
                self.toolbar(
                    [
                        (
                            "Criar ciclo de estudos",
                            lambda: self.navigate("Ciclo de estudos"),
                        )
                    ]
                )
            pending = self.store.one(
                "SELECT COUNT(*) n FROM reviews r JOIN topics t ON t.id=r.topic_id JOIN subjects s ON s.id=t.subject_id WHERE s.plan_id=? AND r.state='Pendente' AND due<=?",
                (self.plan, self.today().isoformat()),
            )["n"]
            self.toolbar(
                [
                    (
                        f"Revisões para hoje / atrasadas: {pending}",
                        lambda: self.navigate("Revisões"),
                    )
                ]
            )
        exam = Panel(right, self)
        exam.pack(fill="x")
        with self.in_panel(exam):
            self.heading("SEU OBJETIVO • BACEN")
            plan = self.store.one("SELECT * FROM plans WHERE id=?", (self.plan,))
            self.note(plan["name"])
            if plan["exam_date"]:
                self.note(
                    f"Prova: {plan['exam_date']} • {(date.fromisoformat(plan['exam_date'])-self.today()).days} dias"
                )
            else:
                self.note(
                    "Referência: edital de 2024.\nData da próxima prova não cadastrada."
                )

        goals = Panel(right, self)
        goals.pack(fill="x", pady=12)
        with self.in_panel(goals):
            self.goal_bars()
        weekly = Panel(right, self)
        weekly.pack(fill="x")
        with self.in_panel(weekly):
            self.heading("ESTUDO SEMANAL")
            self.week_chart()

    def week_bounds(self):
        today = self.today()
        start = (
            today
            - timedelta(
                days=(today.weekday() - int(self.store.pref("week_start", 0))) % 7
            )
            + timedelta(weeks=self.week_offset)
        )
        return start, start + timedelta(days=6)

    def goal_bars(self):
        start, end = self.week_bounds()
        s = self.store.stats(
            self.plan, {"from": start.isoformat(), "to": end.isoformat()}
        )
        self.heading(f"Metas semanais • {start:%d/%m} a {end:%d/%m}")
        goals = self.store.rows(
            "SELECT g.*,s.name subject FROM goals g LEFT JOIN subjects s ON s.id=g.subject_id WHERE g.plan_id=?",
            (self.plan,),
        )
        if not goals:
            self.note(
                "Defina metas flexíveis em Metas e conquistas. Não há dívida por perder um dia."
            )
        for g in goals:
            v = (
                self.store.stats(
                    self.plan,
                    {
                        "from": start.isoformat(),
                        "to": end.isoformat(),
                        "subject_id": g["subject_id"],
                    },
                )
                if g["subject_id"]
                else s
            )
            for name, value, target in [
                ("Horas", v["elapsed"] / 3600, g["hours"]),
                ("Questões", v["total"], g["questions"]),
            ]:
                self.note(
                    f"{g['subject'] or 'Plano'} • {name}: {value:.1f} / {target:g}"
                )
                ttk.Progressbar(
                    self.content, value=min(100, value / target * 100) if target else 0
                ).pack(fill="x", pady=3)

    def week_chart(self):
        self.toolbar(
            [
                ("‹ Semana", lambda: self.move_week(-1)),
                ("Semana ›", lambda: self.move_week(1)),
                ("Tempo / Questões", self.toggle_chart),
            ]
        )
        start, end = self.week_bounds()
        self.note(
            f"{start:%d/%m/%Y} a {end:%d/%m/%Y} • Barras: "
            + (
                "horas líquidas"
                if self.chart_mode == "Tempo"
                else "questões; linha: acertos/respondidas (%)"
            )
        )
        rows = self.store.grouped(
            self.plan, {"from": start.isoformat(), "to": end.isoformat()}
        )
        data = {r["label"]: r for r in rows}
        rows = [
            data.get(
                (start + timedelta(days=i)).isoformat(),
                {
                    "label": (start + timedelta(days=i)).isoformat(),
                    "elapsed": 0,
                    "correct": 0,
                    "wrong": 0,
                    "blank": 0,
                },
            )
            for i in range(7)
        ]
        self.bar_chart(
            rows,
            "elapsed" if self.chart_mode == "Tempo" else "questions",
            performance=self.chart_mode != "Tempo",
        )

    def move_week(self, n):
        self.week_offset += n
        self.refresh()

    def move_streak(self, n):
        self.streak_offset += n
        self.refresh()

    def toggle_chart(self):
        self.chart_mode = "Questões" if self.chart_mode == "Tempo" else "Tempo"
        self.refresh()

    def bar_chart(self, rows, metric="elapsed", performance=False):
        from charts import bars

        return bars(self, rows, metric, performance)

    def horizontal_chart(self, rows):
        from charts import distribution

        return distribution(self, rows)

    def open_subject_name(self, name):
        row = self.store.one(
            "SELECT id FROM subjects WHERE plan_id=? AND name=?", (self.plan, name)
        )
        if row:
            self.subject_detail(row["id"])

    def page_1(self):
        cycle = self.store.current_cycle(self.plan)
        cycles = self.store.rows(
            "SELECT * FROM cycles WHERE plan_id=? ORDER BY name", (self.plan,)
        )
        row = self.toolbar(
            [
                ("Criar ciclo guiado", self.guided_cycle),
                ("Personalizar por pesos", self.generate_cycle),
                ("Novo ciclo vazio", self.new_cycle),
            ]
        )
        self.note(
            "Um ciclo é uma fila que você retoma de onde parou. O guiado intercala suas matérias em blocos curtos e sugere o próximo assunto pendente na sequência de aprendizagem. Personalizar por pesos permite mudar a duração e a prioridade."
        )
        mapping = self.readable_mapping(cycles)
        var = tk.StringVar(value=self.label_for(mapping, cycle["id"]) if cycle else "")
        combo = ttk.Combobox(
            row, values=list(mapping), textvariable=var, state="readonly", width=25
        )
        combo.pack(side="left")

        def activate(e):
            with self.store.db:
                self.store.db.execute(
                    "UPDATE cycles SET active=0 WHERE plan_id=?", (self.plan,)
                )
                self.store.db.execute(
                    "UPDATE cycles SET active=1 WHERE id=?", (mapping[var.get()],)
                )
            self.refresh()

        combo.bind("<<ComboboxSelected>>", activate)
        if not cycle:
            self.note(
                "O ciclo é uma fila contínua. Você retoma de onde parou, sem agenda rígida."
            )
            return
        blocks = self.store.cycle_blocks(cycle)
        self.note(
            f"Volta {cycle['lap']} • {duration(sum(b['target'] for b in blocks))} previstos • {duration(sum(b['elapsed'] for b in blocks))} realizados • Preferência: {self.store.pref('daily_subjects',3)} matérias/dia"
        )
        if cycle["position"] < len(blocks):
            upcoming = blocks[cycle["position"]]
            panel = Panel(self.content, self)
            panel.pack(fill="x", pady=8)
            with self.in_panel(panel):
                self.heading("Próximo bloco: " + upcoming["subject"])
                self.note(
                    f"Estude {duration(max(0,upcoming['target']-upcoming['elapsed']))}. Pausas ficam fora do tempo líquido. Você pode distribuir os blocos ao longo dos dias."
                )
                self.toolbar(
                    [
                        (
                            "Estudar próximo bloco",
                            lambda: self.study_block(upcoming, cycle),
                        )
                    ]
                )
        self.heading("Fila do ciclo")
        self.note(
            "Selecione uma linha para usar as ações abaixo. Concluir avança a fila; adiar registra o motivo; reabrir desfaz a decisão do bloco."
        )
        tree = self.table(
            [
                ("pos", "Posição", 65),
                ("subject", "Matéria / assunto", 330),
                ("target", "Alvo", 100),
                ("time", "Realizado", 100),
                ("remaining", "Restante", 100),
                ("state", "Decisão", 140),
            ],
            [
                (
                    b["id"],
                    [
                        f"{'→ ' if i==cycle['position'] else ''}{i+1}",
                        b["subject"] + (f" / {b['topic']}" if b["topic"] else ""),
                        duration(b["target"]),
                        duration(b["elapsed"]),
                        duration(max(0, b["target"] - b["elapsed"])),
                        b["state"]
                        or (
                            "Alvo atingido"
                            if b["elapsed"] >= b["target"]
                            else "Pendente"
                        ),
                    ],
                )
                for i, b in enumerate(blocks)
            ],
            height=10,
        )
        mapping = {b["id"]: b for b in blocks}
        if cycle["position"] < len(blocks):
            tree.selection_set(blocks[cycle["position"]]["id"])

        def chosen():
            return mapping[self.selected(tree)]

        def decide(state):
            b = chosen()
            if state == "Adiado":
                form = Form(
                    self,
                    "Adiar bloco",
                    [("reason", "Motivo", "entry")],
                    lambda v: self.store.decide(cycle, b["id"], state, v["reason"]),
                )
            else:
                self.store.decide(cycle, b["id"], state)
                self.refresh()

        self.toolbar(
            [
                ("Adicionar bloco", lambda: self.block_form(cycle)),
                ("Editar selecionado", lambda: self.block_form(cycle, chosen())),
                ("Estudar selecionado", lambda: self.study_block(chosen(), cycle)),
                ("Concluir selecionado", lambda: decide("Concluído")),
                ("Adiar selecionado", lambda: decide("Adiado")),
                ("Reabrir selecionado", lambda: decide("Retomar")),
            ]
        )
        self.toolbar(
            [
                ("↑ Mover", lambda: self.reorder_block(cycle, chosen(), -1)),
                ("↓ Mover", lambda: self.reorder_block(cycle, chosen(), 1)),
                ("Remover", lambda: self.archive_block(chosen())),
                ("Próxima volta", lambda: self.next_lap(cycle)),
                ("Histórico de voltas", lambda: self.cycle_history(cycle)),
                (
                    "Renomear ciclo",
                    lambda: Form(
                        self,
                        "Nome do ciclo",
                        [("name", "Nome", "entry")],
                        lambda v: self.store.save(
                            "cycles",
                            {
                                "id": cycle["id"],
                                "name": v["name"].strip() or cycle["name"],
                            },
                        ),
                        cycle,
                    ),
                ),
            ]
        )

        def drag_start(e):
            tree._drag = tree.identify_row(e.y)

        def drag_end(e):
            src = getattr(tree, "_drag", "")
            dst = tree.identify_row(e.y)
            if src and dst and src != dst:
                ids = list(tree.get_children())
                ids.remove(src)
                ids.insert(ids.index(dst), src)
                self.store.reorder_cycle(cycle, ids)
                self.refresh()

        tree.bind("<ButtonPress-1>", drag_start, add="+")
        tree.bind("<ButtonRelease-1>", drag_end, add="+")
        self.note(
            "O excesso permanece no bloco de origem. Concluir ou adiar é uma decisão explícita; não marca a teoria. Arraste linhas ou use ↑ / ↓."
        )

    def new_cycle(self):
        def save(v):
            if not v["name"].strip():
                raise ValueError("Digite um nome.")
            with self.store.db:
                self.store.db.execute(
                    "UPDATE cycles SET active=0 WHERE plan_id=?", (self.plan,)
                )
                self.store.put("cycles", {"plan_id": self.plan, "name": v["name"]})

        Form(
            self,
            "Novo ciclo",
            [("name", "Nome", "entry")],
            save,
            {"name": "Ciclo BACEN"},
        )

    def generate_cycle(self):
        def preview(v):
            blocks = self.store.generate_cycle(
                self.plan, int(v["minutes"]), int(v["total"])
            )
            text = (
                "Critério: peso × dificuldade, distribuição proporcional e intercalada.\n\n"
                + "\n".join(
                    f"{i+1}. {b['subject']} — {duration(b['target'])}"
                    for i, b in enumerate(blocks)
                )
            )
            if not messagebox.askokcancel(
                "Prévia do ciclo",
                text + "\n\nCriar este ciclo? Você poderá editar cada bloco.",
                parent=self.root,
            ):
                return
            with self.store.db:
                self.store.db.execute(
                    "UPDATE cycles SET active=0 WHERE plan_id=?", (self.plan,)
                )
                cid = self.store.put(
                    "cycles",
                    {"plan_id": self.plan, "name": v["name"] or "Ciclo por pesos"},
                )
                for i, b in enumerate(blocks):
                    self.store.put(
                        "blocks",
                        {
                            "cycle_id": cid,
                            "subject_id": b["subject_id"],
                            "target": b["target"],
                            "category": b["category"],
                            "sort": i,
                        },
                    )

        Form(
            self,
            "Gerar ciclo por pesos",
            [
                ("name", "Nome", "entry"),
                ("minutes", "Minutos por bloco", "entry"),
                ("total", "Minutos por volta (aproximado)", "entry"),
            ],
            preview,
            {
                "name": "BACEN — ciclo por pesos",
                "minutes": str(self.store.pref("block_minutes", 45)),
                "total": "360",
            },
        )

    def subject_map(self, include_archived=False, plan=None):
        return self.readable_mapping(
            self.store.rows(
                "SELECT * FROM subjects WHERE plan_id=? "
                + ("" if include_archived else "AND archived=0")
                + " ORDER BY name",
                (plan or self.plan,),
            )
        )

    def topic_map(self, subject=None, include_archived=False):
        if not subject:
            return {}
        from learning import ordered

        rows = self.store.rows(
            "SELECT * FROM topics WHERE subject_id=? "
            + ("" if include_archived else "AND archived=0")
            + " ORDER BY rowid",
            (subject,),
        )
        name = self.store.one("SELECT name FROM subjects WHERE id=?", (subject,))
        return self.readable_mapping(
            (
                ordered(rows, {subject: name["name"]})
                if self.store.pref("syllabus_order", "Aprendizagem") == "Aprendizagem"
                else rows
            ),
            hierarchy=True,
        )

    @staticmethod
    def readable_mapping(rows, hierarchy=False):
        import re

        by_id = {r["id"]: r for r in rows}
        result = {}

        def title(row):
            return re.sub(r"^\d+(?:\.\d+)*\s+", "", row["name"])

        for row in rows:
            label = title(row)
            parent = by_id.get(row.get("parent_id"))
            if hierarchy and parent:
                label += " — " + title(parent)
            candidate = label
            number = 2
            while candidate in result:
                candidate = f"{label} (opção {number})"
                number += 1
            result[candidate] = row["id"]
        return result

    @staticmethod
    def label_for(mapping, value):
        return next((name for name, rid in mapping.items() if rid == value), "")

    def block_form(self, cycle, b=None):
        mapping = self.subject_map()
        b = b or {}
        initial = {
            "subject": self.label_for(mapping, b.get("subject_id")),
            "topic": "",
            "target": duration(
                b.get("target", int(self.store.pref("block_minutes", 45)) * 60)
            ),
            "category": b.get("category", "Teoria"),
        }
        topics = self.topic_map(b.get("subject_id"))
        initial["topic"] = self.label_for(topics, b.get("topic_id"))

        def save(v):
            sid = mapping.get(v["subject"])
            tid = topic_mapping.get(v["topic"])
            if not sid:
                raise ValueError("Escolha uma matéria.")
            if (
                b
                and (sid != b["subject_id"] or tid != b["topic_id"])
                and self.store.one(
                    "SELECT id FROM sessions WHERE block_id=? LIMIT 1", (b["id"],)
                )
            ):
                raise ValueError(
                    "Este bloco tem histórico. Para trocar matéria ou assunto, crie outro bloco e remova este da fila."
                )
            target = parse_duration(v["target"])
            if not target:
                raise ValueError("O alvo precisa ser positivo.")
            self.store.save(
                "blocks",
                dict(
                    {
                        "cycle_id": cycle["id"],
                        "subject_id": sid,
                        "topic_id": tid,
                        "target": target,
                        "category": v["category"],
                        "sort": b.get("sort", len(self.store.cycle_blocks(cycle))),
                    },
                    **({"id": b["id"]} if b else {}),
                ),
            )

        form = Form(
            self,
            "Bloco do ciclo",
            [
                ("subject", "Matéria", "choice", list(mapping)),
                ("topic", "Assunto opcional", "choice", [""] + list(topics)),
                ("target", "Duração alvo (HH:MM:SS)", "entry"),
                ("category", "Categoria", "choice", ["Teoria", "Questões", "Revisão"]),
            ],
            save,
            initial,
        )
        topic_mapping = topics

        def update(e):
            nonlocal topic_mapping
            topic_mapping = self.topic_map(mapping.get(form.vars["subject"].get()))
            form.widgets["topic"].configure(values=[""] + list(topic_mapping))
            form.vars["topic"].set("")

        form.widgets["subject"].bind("<<ComboboxSelected>>", update)

    def reorder_block(self, cycle, b, direction):
        blocks = self.store.cycle_blocks(cycle)
        ids = [x["id"] for x in blocks]
        pos = ids.index(b["id"])
        other = pos + direction
        if 0 <= other < len(ids):
            ids[pos], ids[other] = ids[other], ids[pos]
            self.store.reorder_cycle(cycle, ids)
            self.refresh()

    def archive_block(self, b):
        if messagebox.askyesno(
            "Remover bloco",
            "Remover da fila e preservar sessões e decisões históricas?",
            parent=self.root,
        ):
            cycle = self.store.one("SELECT * FROM cycles WHERE id=?", (b["cycle_id"],))
            blocks = self.store.cycle_blocks(cycle)
            current = (
                blocks[cycle["position"]]["id"]
                if cycle["position"] < len(blocks)
                else None
            )
            self.store.save("blocks", {"id": b["id"], "archived": 1})
            remaining = self.store.cycle_blocks(cycle)
            ids = [x["id"] for x in remaining]
            if current in ids:
                position = ids.index(current)
            else:
                position = next(
                    (i for i, x in enumerate(remaining) if not x["state"]),
                    len(remaining),
                )
            self.store.save("cycles", {"id": cycle["id"], "position": position})
            self.refresh()

    def next_lap(self, cycle):
        blocks = self.store.cycle_blocks(cycle)
        if any(not b["state"] for b in blocks):
            raise ValueError(
                "Conclua ou adie todos os blocos antes de iniciar outra volta."
            )
        if any(b["state"] == "Adiado" for b in blocks) and not messagebox.askyesno(
            "Blocos adiados",
            "Os adiamentos permanecem no histórico desta volta. Iniciar a próxima?",
            parent=self.root,
        ):
            return
        self.store.save(
            "cycles", {"id": cycle["id"], "lap": cycle["lap"] + 1, "position": 0}
        )
        self.refresh()

    def study_block(self, b, cycle):
        topic = b["topic_id"]
        if self.store.pref("starter_cycle_" + self.plan) == cycle["id"] and not topic:
            from learning import next_topic

            next_item = next_topic(self.store, b["subject_id"])
            topic = next_item["id"] if next_item else None
        self.clock_setup(
            {
                "subject_id": b["subject_id"],
                "topic_id": topic,
                "category": b["category"],
                "target": max(60, b["target"] - b["elapsed"]),
                "block_id": b["id"],
                "lap": cycle["lap"],
            }
        )

    def cycle_history(self, cycle):
        win = tk.Toplevel(self.root)
        win.title("Histórico de voltas • " + cycle["name"])
        win.geometry("950x570")
        win.configure(bg=self.bg)
        rows = self.store.rows(
            """SELECT d.id,d.lap,d.state,d.reason,s.name subject,COALESCE(a.elapsed,0) elapsed FROM decisions d JOIN blocks b ON b.id=d.block_id JOIN subjects s ON s.id=b.subject_id LEFT JOIN (SELECT block_id,lap,SUM(elapsed) elapsed FROM sessions GROUP BY block_id,lap) a ON a.block_id=d.block_id AND a.lap=d.lap WHERE b.cycle_id=? ORDER BY d.lap DESC,b.sort""",
            (cycle["id"],),
        )
        self.table(
            [
                ("lap", "Volta", 65),
                ("subject", "Matéria", 260),
                ("time", "Tempo efetivo", 140),
                ("state", "Decisão", 130),
                ("reason", "Motivo do adiamento", 300),
            ],
            [
                (
                    r["id"],
                    [
                        r["lap"],
                        r["subject"],
                        duration(r["elapsed"]),
                        r["state"],
                        r["reason"],
                    ],
                )
                for r in rows
            ],
            height=12,
            parent=win,
        )
        self.motion.reveal(win)

    def page_2(self):
        from edital import render_edital

        render_edital(self, Tooltip, messagebox)

    def topic_form(self, t=None):
        t = t or {}
        subjects = self.subject_map()
        parents = self.readable_mapping(
            [
                r
                for r in self.store.rows(
                    "SELECT t.* FROM topics t JOIN subjects s ON s.id=t.subject_id WHERE s.plan_id=? AND t.archived=0",
                    (self.plan,),
                )
                if r["id"] != t.get("id")
            ],
            True,
        )

        def save(v):
            sid = subjects.get(v["subject"])
            parent = parents.get(v["parent"])
            if not sid or not v["name"].strip():
                raise ValueError("Escolha matéria e nome do assunto.")
            if parent:
                p = self.store.one("SELECT * FROM topics WHERE id=?", (parent,))
                if p["subject_id"] != sid:
                    raise ValueError("O pai deve pertencer à mesma matéria.")
                seen = {t.get("id")}
                while p:
                    if p["id"] in seen:
                        raise ValueError(
                            "Um assunto não pode ser ancestral de si próprio."
                        )
                    seen.add(p["id"])
                    p = (
                        self.store.one(
                            "SELECT * FROM topics WHERE id=?", (p["parent_id"],)
                        )
                        if p["parent_id"]
                        else None
                    )
            if (
                t
                and sid != t["subject_id"]
                and self.store.one(
                    "SELECT id FROM sessions WHERE topic_id=? LIMIT 1", (t["id"],)
                )
            ):
                raise ValueError(
                    "Assunto com histórico não pode mudar de matéria; crie outro e arquive este."
                )
            values = {
                "subject_id": sid,
                "parent_id": parent,
                "name": v["name"].strip(),
                "notes": v["notes"],
            }
            if t:
                values["id"] = t["id"]
            self.store.save("topics", values)

        return Form(
            self,
            "Assunto / subassunto",
            [
                ("subject", "Matéria", "choice", list(subjects)),
                ("name", "Nome", "entry"),
                ("parent", "Assunto pai (opcional)", "choice", [""] + list(parents)),
                ("notes", "Descrição e observações do estudo", "text"),
            ],
            save,
            {
                "subject": self.label_for(subjects, t.get("subject_id")),
                "name": t.get("name", ""),
                "parent": self.label_for(parents, t.get("parent_id")),
                "notes": t.get("notes", ""),
            },
        )

    def topic_notes(self, topic, on_save=None):
        current = self.store.one("SELECT * FROM topics WHERE id=?", (topic["id"],))

        def save(values):
            self.store.save("topics", {"id": topic["id"], "notes": values["notes"]})
            topic["notes"] = values["notes"]
            if on_save:
                on_save()

        form = Form(
            self,
            "Meu caderno de estudo",
            [("notes", "Descrição, dúvidas, exemplos e observações", "text")],
            save,
            {"notes": current["notes"]},
        )
        form.widgets["notes"].configure(height=12)
        ttk.Label(
            form.body, text=topic["name"], style="Muted.TLabel", wraplength=640
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=12)
        form.refresh_on_submit = False
        return form

    def archive_topic(self, t):
        if messagebox.askyesno(
            "Arquivar assunto",
            "Arquivar este assunto e seus subassuntos? Os estudos e materiais serão preservados.",
            parent=self.root,
        ):
            with self.store.db:
                self.store.db.execute(
                    """WITH RECURSIVE descendants(id) AS (SELECT ? UNION ALL SELECT t.id FROM topics t JOIN descendants d ON t.parent_id=d.id) UPDATE topics SET archived=1 WHERE id IN descendants""",
                    (t["id"],),
                )
            self.refresh()

    def materials(self, t):
        win = tk.Toplevel(self.root)
        win.title("Materiais de " + t["name"])
        win.geometry("850x430")
        win.configure(bg=self.bg)
        rows = self.store.rows("SELECT * FROM materials WHERE topic_id=?", (t["id"],))
        mapping = {r["id"]: r for r in rows}
        tree = self.table(
            [("name", "Material", 300), ("url", "Link", 420)],
            [(r["id"], [r["name"], r["url"]]) for r in rows],
            parent=win,
        )

        def edit(r=None):
            def save(v):
                if not v["name"].strip():
                    raise ValueError("Digite o nome do material.")
                if v["url"] and not v["url"].lower().startswith(
                    ("http://", "https://")
                ):
                    raise ValueError("Use um link http:// ou https://, ou deixe vazio.")
                self.store.save(
                    "materials",
                    dict(v, topic_id=t["id"], **({"id": r["id"]} if r else {})),
                )

            Form(
                self,
                "Material",
                [
                    ("name", "Nome / aula / capítulo", "entry"),
                    ("url", "Link (opcional)", "entry"),
                ],
                save,
                r or {},
            )
            win.destroy()

        bar = ttk.Frame(win)
        bar.pack(pady=10)
        MotionButton(bar, text="Adicionar", command=edit).pack(side="left", padx=5)
        MotionButton(
            bar, text="Editar", command=lambda: edit(mapping[self.selected(tree)])
        ).pack(side="left", padx=5)
        MotionButton(
            bar,
            text="Abrir link",
            command=lambda: self.open_link(mapping[self.selected(tree)]["url"]),
        ).pack(side="left", padx=5)

        def remove():
            if messagebox.askyesno(
                "Excluir material", "Excluir este material?", parent=win
            ):
                with self.store.db:
                    self.store.db.execute(
                        "DELETE FROM materials WHERE id=?", (self.selected(tree),)
                    )
                win.destroy()

        MotionButton(bar, text="Excluir", command=remove).pack(side="left", padx=5)
        self.motion.reveal(win)

    def open_link(self, url):
        webbrowser.open(web_url(url))

    def import_edital(self):
        def preview(v):
            raw = v["text"].strip()
            if raw.startswith("["):
                rows = json.loads(raw)
            elif raw.startswith("materia;"):
                rows = list(csv.DictReader(raw.splitlines(), delimiter=";"))
            else:
                rows = []
                for line in raw.splitlines():
                    parts = line.split("|")
                    if len(parts) not in [2, 3]:
                        raise ValueError(
                            "Use Matéria | Assunto ou Matéria | Pai | Subassunto."
                        )
                    rows.append(
                        {
                            "materia": parts[0].strip(),
                            "assunto": parts[-1].strip(),
                            "pai": parts[1].strip() if len(parts) == 3 else "",
                        }
                    )
            if not rows or any(
                not r.get("materia") or not r.get("assunto") for r in rows
            ):
                raise ValueError("Cada linha precisa de materia e assunto.")
            if messagebox.askokcancel(
                "Confirmar importação",
                f"{len(rows)} assuntos\n\n"
                + "\n".join(
                    f"{r['materia']} → {r.get('pai','')} → {r['assunto']}"
                    for r in rows[:12]
                )
                + "\n\nConfirme para gravar. Assuntos iguais no mesmo pai são preservados sem duplicação.",
                parent=self.root,
            ):
                self.store.import_topics(self.plan, rows)

        form = Form(
            self,
            "Importar edital — revise o texto antes de salvar",
            [("text", "Texto, CSV ou JSON", "text")],
            preview,
            {"text": "Banco de dados | Normalização\nLíngua Portuguesa | Concordância"},
        )
        form.widgets["text"].configure(height=17)

        def read():
            path = filedialog.askopenfilename(
                filetypes=[("Texto estruturado", "*.csv *.json *.txt")], parent=form.win
            )
            if path:
                form.widgets["text"].delete("1.0", "end")
                form.widgets["text"].insert(
                    "1.0", Path(path).read_text(encoding="utf-8-sig")
                )

        MotionButton(form.body, text="Ler arquivo", command=read).grid(
            row=2, column=1, sticky="w", pady=8
        )

    def load_bacen(self):
        data = json.loads((ASSETS / "bacen2024.json").read_text(encoding="utf-8"))

        def save(v):
            area = v["area"]
            rows = data["areas"][area]
            guide = json.loads(
                (ASSETS / "bacen2024-detalhado.json").read_text(encoding="utf-8")
            )["areas"][area]
            count = sum(len(r["items"]) for r in guide)
            if messagebox.askokcancel(
                "BACEN — edital anterior",
                f"Importar {len(rows)} itens oficiais e {count} desdobramentos de estudo de {area}?\n\nReferência: Edital nº 1, 15/01/2024, seção 18. Os desdobramentos são um guia pedagógico separado do texto oficial. Não representa edital novo nem inclui automaticamente retificações. O PDF original fica disponível offline. Não será cadastrada data de prova.",
                parent=self.root,
            ):
                self.store.import_topics(self.plan, rows)
                self.store.set_pref("bacen_source", data["source"])
                # A plan may intentionally contain both BACEN areas.
                key = "bacen_guide_v2_" + self.plan
                previous = self.store.pref(key, False)
                self.store.set_pref(key, False)
                try:
                    expand_bacen(self.store, self.plan, guide, 2)
                except Exception:
                    self.store.set_pref(key, previous)
                    raise

        Form(
            self,
            "BACEN 2024 — área de referência",
            [("area", "Área", "choice", list(data["areas"]))],
            save,
            {"area": "Tecnologia da Informação"},
        )

    def open_bacen(self):
        path = ASSETS / "BACEN-2024-edital-abertura.pdf"
        if os.name == "nt":
            os.startfile(path)
        else:
            webbrowser.open(path.as_uri())

    def syllabus_audit(self):
        guide = json.loads(
            (ASSETS / "bacen2024-detalhado.json").read_text(encoding="utf-8")
        )
        text = (
            f"Revisão: {guide['reviewed_on']}\n\n{guide['evidence_additions']} subassuntos adicionais ligados a provas ou retificação identificadas. "
            "Os 287 itens oficiais originais permanecem preservados.\n\n"
            + guide["review_scope"]
            + "\n\nGuia de estudo: desdobramento pedagógico. Os itens com referência de prova exibem concurso e número das questões. "
            "Não transforme afirmações de questões Certo/Errado em material teórico sem conferir o gabarito definitivo."
        )
        form = Form(
            self,
            "Fontes e cobertura do edital",
            [("summary", "O que foi revisado", "text")],
            lambda v: None,
            {"summary": text},
            width=820,
        )
        form.widgets["summary"].configure(height=9, state="disabled")
        form.save_button.configure(text="Fechar", command=form.win.destroy)
        links = ttk.Frame(form.body)
        links.grid(row=3, column=0, columnspan=2, sticky="ew", pady=12)
        for source in guide["review_sources"].values():
            MotionButton(
                links,
                text=source["exam"],
                command=lambda u=source["url"]: self.open_link(u),
            ).pack(anchor="w", pady=3)
        MotionButton(
            links,
            text="Abrir edital retificado offline",
            command=lambda: os.startfile(ASSETS / "BACEN-2024-edital-retificado.pdf"),
        ).pack(anchor="w", pady=3)
        return form

    def manage_entities(self):
        win = tk.Toplevel(self.root)
        win.title("Planos e matérias")
        win.geometry("950x570")
        win.configure(bg=self.bg)
        self.entity_win = win
        ttk.Label(
            win,
            text="Planos independentes • Arquivar preserva o histórico",
            style="Heading.TLabel",
        ).pack(anchor="w", padx=12, pady=12)
        plans = self.store.rows("SELECT * FROM plans ORDER BY name")
        pm = {p["id"]: p for p in plans}
        pt = self.table(
            [
                ("name", "Plano", 360),
                ("date", "Data prevista", 130),
                ("state", "Estado", 120),
            ],
            [
                (
                    p["id"],
                    [
                        p["name"],
                        p["exam_date"] or "Sem data",
                        "Arquivado" if p["archived"] else "Ativo",
                    ],
                )
                for p in plans
            ],
            height=4,
            parent=win,
        )
        row = ttk.Frame(win)
        row.pack(fill="x", padx=12)
        for label, command in [
            ("Novo plano", lambda: self.plan_form()),
            ("Editar plano", lambda: self.plan_form(pm[self.selected(pt)])),
            (
                "Arquivar / ativar plano",
                lambda: self.archive_entity("plans", pm[self.selected(pt)]),
            ),
        ]:
            MotionButton(
                row, text=label, command=lambda cmd=command: (cmd(), win.destroy())
            ).pack(side="left", padx=5)
        subjects = self.store.rows(
            "SELECT * FROM subjects WHERE plan_id=? ORDER BY name", (self.plan,)
        )
        sm = {s["id"]: s for s in subjects}
        st = self.table(
            [
                ("name", "Matéria do plano atual", 340),
                ("weight", "Peso", 80),
                ("difficulty", "Dificuldade", 90),
                ("state", "Estado", 120),
            ],
            [
                (
                    s["id"],
                    [
                        s["name"],
                        s["weight"],
                        s["difficulty"],
                        "Arquivada" if s["archived"] else "Ativa",
                    ],
                )
                for s in subjects
            ],
            height=5,
            parent=win,
        )
        row = ttk.Frame(win)
        row.pack(fill="x", padx=12, pady=12)
        for label, command in [
            ("Nova matéria", lambda: self.subject_form()),
            ("Editar matéria", lambda: self.subject_form(sm[self.selected(st)])),
            (
                "Arquivar / ativar matéria",
                lambda: self.archive_entity("subjects", sm[self.selected(st)]),
            ),
        ]:
            MotionButton(
                row, text=label, command=lambda cmd=command: (cmd(), win.destroy())
            ).pack(side="left", padx=5)
        self.motion.reveal(win)

    def plan_form(self, p=None):
        p = p or {}

        def save(v):
            if not v["name"].strip():
                raise ValueError("Informe o nome do plano.")
            exam = v["exam_date"].strip() or None
            if exam:
                date.fromisoformat(exam)
            pid = self.store.save(
                "plans",
                dict(
                    name=v["name"].strip(),
                    description=v["description"],
                    exam_date=exam,
                    **({"id": p["id"]} if p else {}),
                ),
            )
            if not p:
                self.plan = pid
                self.store.set_pref("active_plan", pid)
                self.filters = {}

        Form(
            self,
            "Plano / concurso",
            [
                ("name", "Nome", "entry"),
                ("description", "Descrição", "text"),
                ("exam_date", "Data prevista (AAAA-MM-DD, opcional)", "entry"),
            ],
            save,
            p,
        )

    def subject_form(self, s=None):
        s = s or {}

        def save(v):
            if not v["name"].strip():
                raise ValueError("Informe o nome.")
            weight = float(v["weight"])
            difficulty = float(v["difficulty"])
            if not 0 < weight <= 100 or not 0 < difficulty <= 100:
                raise ValueError(
                    "Peso e dificuldade devem ser maiores que zero e até 100."
                )
            self.store.save(
                "subjects",
                dict(
                    plan_id=self.plan,
                    name=v["name"].strip(),
                    color=v["color"],
                    weight=weight,
                    difficulty=difficulty,
                    **({"id": s["id"]} if s else {}),
                ),
            )

        Form(
            self,
            "Matéria",
            [
                ("name", "Nome", "entry"),
                ("color", "Cor de identificação", "choice", COLORS),
                ("weight", "Peso / prioridade", "entry"),
                ("difficulty", "Dificuldade percebida", "entry"),
            ],
            save,
            dict({"color": COLORS[0], "weight": 1, "difficulty": 1}, **s),
        )

    def archive_entity(self, table, row):
        if (
            table == "plans"
            and not row["archived"]
            and len(self.store.rows("SELECT id FROM plans WHERE archived=0")) < 2
        ):
            raise ValueError("Crie outro plano antes de arquivar o único plano ativo.")
        if messagebox.askyesno(
            "Alterar estado",
            "Arquivar ou reativar preservando todo o histórico?",
            parent=self.root,
        ):
            self.store.save(table, {"id": row["id"], "archived": not row["archived"]})
            if table == "plans" and row["id"] == self.plan and not row["archived"]:
                self.plan = self.store.one(
                    "SELECT id FROM plans WHERE archived=0 LIMIT 1"
                )["id"]
                self.store.set_pref("active_plan", self.plan)
            self.refresh()

    def session_form(self, initial=None, editing=None, from_clock=False):
        initial = dict(initial or {})
        editing = editing or {}
        initial = dict(editing, **initial)
        subjects = self.subject_map(
            include_archived=bool(editing) or from_clock,
            plan=initial.get("plan_id", self.plan),
        )
        topics = self.topic_map(initial.get("subject_id"), bool(editing) or from_clock)
        initial.update(
            {
                "subject": self.label_for(subjects, initial.get("subject_id")),
                "topic": self.label_for(topics, initial.get("topic_id")),
            }
        )
        initial.setdefault("day", self.today().isoformat())
        initial.setdefault("category", "Teoria")
        initial.setdefault("target", int(self.store.pref("block_minutes", 45)) * 60)
        initial.setdefault("elapsed", 0)
        initial["target_text"] = duration(initial["target"])
        initial["elapsed_text"] = duration(initial["elapsed"])
        initial.setdefault("correct", 0)
        initial.setdefault("wrong", 0)
        initial.setdefault("blank", 0)
        initial["total"] = initial["correct"] + initial["wrong"] + initial["blank"]
        initial.setdefault(
            "intervals",
            ",".join(
                str(x) for x in self.store.pref("review_intervals", [1, 7, 30, 60, 120])
            ),
        )
        initial.setdefault("base", initial["day"])
        mock = initial["category"] == "Simulado"
        fields = [
            ("day", "Data (AAAA-MM-DD)", "entry"),
            ("start_time", "Horário (HH:MM, opcional)", "entry"),
            (
                "category",
                "Categoria",
                "choice",
                ["Teoria", "Questões", "Revisão", "Simulado"],
            ),
            (
                "subject",
                "Matéria (digite para criar)",
                "editable",
                [""] + list(subjects),
            ),
            (
                "topic",
                "Assunto específico (digite para criar)",
                "editable",
                [""] + list(topics),
            ),
            ("target_text", "Tempo pretendido (HH:MM:SS)", "entry"),
            ("elapsed_text", "Tempo líquido (HH:MM:SS)", "entry"),
            ("correct", "Acertos", "entry"),
            ("wrong", "Erros", "entry"),
            ("blank", "Em branco", "entry"),
            ("total", "Total (automático, editável)", "entry"),
            ("material", "Material / aula / página / capítulo", "entry"),
            ("url", "Link do material", "entry"),
            ("pages", "Páginas lidas (opcional)", "entry"),
            ("video_text", "Videoaula assistida (HH:MM:SS, opcional)", "entry"),
            ("next_step", "Onde parei / próximo passo", "text"),
            ("notes", "Observações", "text"),
            ("theory", "Teoria do assunto finalizada", "bool"),
            ("schedule", "Programar revisões", "bool"),
            ("base", "Data base das revisões", "entry"),
            ("intervals", "Intervalos em dias (separados por vírgula)", "entry"),
            ("apply_block", "Aplicar ao bloco compatível do ciclo", "bool"),
        ]
        initial["video_text"] = (
            duration(initial["video"]) if initial.get("video") is not None else ""
        )
        initial["apply_block"] = bool(initial.get("block_id"))
        if mock:
            fields += [
                ("mock_name", "Nome do simulado", "entry"),
                (
                    "mock_format",
                    "Formato",
                    "choice",
                    ["Certo/Errado", "Múltipla escolha"],
                ),
                ("score_correct", "Valor por acerto", "entry"),
                ("score_wrong", "Desconto por erro", "entry"),
                ("score_blank", "Valor por branco", "entry"),
                ("results", "Resultados por matéria (uma linha por matéria)", "text"),
            ]
            initial.setdefault("mock_name", "Simulado BACEN")
            initial.setdefault("mock_format", "Certo/Errado")
            initial.setdefault("score_correct", 1)
            initial.setdefault("score_wrong", 1)
            initial.setdefault("score_blank", 0)
            if editing:
                rs = self.store.rows(
                    "SELECT r.*,s.name FROM mock_results r JOIN subjects s ON s.id=r.subject_id WHERE session_id=?",
                    (editing["id"],),
                )
                initial["results"] = "\n".join(
                    f"{r['name']} | {r['correct']} | {r['wrong']} | {r['blank']} | {r['weight']}"
                    for r in rs
                )
        topic_mapping = topics
        token = initial.get("id") or uid()

        def save(v):
            plan = initial.get("plan_id", self.plan)
            sid = subjects.get(v["subject"])
            tid = topic_mapping.get(v["topic"])
            # Entity creation and session saving share the same outer transaction.
            self.store.db.execute("SAVEPOINT session_form")
            try:
                if v["subject"].strip() and not sid:
                    sid = self.store.put(
                        "subjects",
                        {
                            "plan_id": plan,
                            "name": v["subject"].strip(),
                            "color": COLORS[0],
                        },
                    )
                if v["topic"].strip() and not tid:
                    if not sid:
                        raise ValueError(
                            "Escolha uma matéria antes de criar o assunto."
                        )
                    tid = self.store.put(
                        "topics", {"subject_id": sid, "name": v["topic"].strip()}
                    )
                values = {
                    "id": token,
                    "plan_id": plan,
                    "subject_id": sid,
                    "topic_id": tid,
                    "day": v["day"],
                    "start_time": v["start_time"],
                    "category": v["category"],
                    "target": parse_duration(v["target_text"]),
                    "elapsed": parse_duration(v["elapsed_text"]),
                    "correct": int(v["correct"] or 0),
                    "wrong": int(v["wrong"] or 0),
                    "blank": int(v["blank"] or 0),
                    "total": int(v["total"] or 0),
                    "material": v["material"],
                    "url": v["url"],
                    "pages": int(v["pages"]) if v["pages"].strip() else None,
                    "video": (
                        parse_duration(v["video_text"])
                        if v["video_text"].strip()
                        else None
                    ),
                    "next_step": v["next_step"],
                    "notes": v["notes"],
                    "block_id": None,
                    "lap": None,
                    "review_id": initial.get("review_id"),
                    "segments": (
                        json.dumps(initial.get("segments", []))
                        if isinstance(initial.get("segments", []), list)
                        else initial["segments"]
                    ),
                }
                if v["apply_block"]:
                    cycle = self.store.current_cycle(plan)
                    blocks = self.store.cycle_blocks(cycle) if cycle else []
                    b = next(
                        (b for b in blocks if b["id"] == initial.get("block_id")), None
                    ) or (
                        blocks[cycle["position"]]
                        if cycle and cycle["position"] < len(blocks)
                        else None
                    )
                    if not b:
                        raise ValueError("Não há bloco atual para receber o tempo.")
                    values.update(
                        block_id=b["id"], lap=initial.get("lap") or cycle["lap"]
                    )
                results = []
                if v["category"] == "Simulado":
                    if not mock:
                        raise ValueError(
                            "Para registrar simulado, use Novo simulado na seção Simulados."
                        )
                    values.update({k: v[k] for k in ["mock_name", "mock_format"]})
                    values.update(
                        {
                            k: float(v[k])
                            for k in ["score_correct", "score_wrong", "score_blank"]
                        }
                    )
                    if not v["mock_name"].strip():
                        raise ValueError("Dê um nome ao simulado.")
                    by_name = {
                        r["name"]: r["id"]
                        for r in self.store.rows(
                            "SELECT * FROM subjects WHERE plan_id=?", (plan,)
                        )
                    }
                    for line in v["results"].splitlines():
                        if not line.strip():
                            continue
                        parts = [x.strip() for x in line.split("|")]
                        if len(parts) not in [4, 5] or parts[0] not in by_name:
                            raise ValueError(
                                "Resultados: Nome exato da matéria | acertos | erros | brancos | peso opcional."
                            )
                        results.append(
                            {
                                "subject_id": by_name[parts[0]],
                                "correct": int(parts[1]),
                                "wrong": int(parts[2]),
                                "blank": int(parts[3]),
                                "weight": float(parts[4]) if len(parts) == 5 else 1,
                            }
                        )
                intervals = (
                    [int(x.strip()) for x in v["intervals"].split(",") if x.strip()]
                    if v["schedule"]
                    else []
                )
                values["pauses"] = (
                    json.dumps(initial.get("pauses", []))
                    if isinstance(initial.get("pauses", []), list)
                    else initial["pauses"]
                )
                # Domain operation commits entity creation and finalization atomically.
                values = self.store.validate_session(values)
                shift = True
                if (
                    editing
                    and editing["day"] != values["day"]
                    and self.store.one(
                        "SELECT id FROM reviews WHERE origin_id=? AND state='Pendente' LIMIT 1",
                        (token,),
                    )
                ):
                    decision = messagebox.askyesnocancel(
                        "Datas de revisões",
                        "Deslocar as revisões pendentes pela alteração da data do estudo?\nSim: ajustar datas pendentes. Não: preservar datas. Cancelar: voltar ao registro. Revisões concluídas permanecem iguais.",
                        parent=form.win,
                    )
                    if decision is None:
                        raise ValueError(
                            "Alteração cancelada. Confira a data antes de salvar."
                        )
                    shift = decision
                self.store.save_session(
                    values,
                    intervals,
                    v["theory"],
                    results,
                    from_clock,
                    v["base"],
                    shift,
                )
                if from_clock:
                    self.clock.state = None
                self.notify("Estudo salvo • " + duration(values["elapsed"]))
            except Exception:
                self.store.db.rollback()
                raise

        form = Form(
            self,
            (
                "Editar estudo"
                if editing
                else "Registrar simulado" if mock else "Registro de estudo"
            ),
            fields,
            save,
            initial,
            width=830,
        )

        def update_subject(e):
            nonlocal topic_mapping
            topic_mapping = self.topic_map(subjects.get(form.vars["subject"].get()))
            form.widgets["topic"].configure(values=[""] + list(topic_mapping))
            form.vars["topic"].set("")

        form.widgets["subject"].bind("<<ComboboxSelected>>", update_subject)

        def update_total(*args):
            try:
                form.vars["total"].set(
                    str(
                        sum(
                            int(form.vars[k].get() or 0)
                            for k in ["correct", "wrong", "blank"]
                        )
                    )
                )
            except ValueError:
                pass

        for k in ["correct", "wrong", "blank"]:
            form.vars[k].trace_add("write", update_total)
        row = ttk.Frame(form.body)
        row.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="w", pady=8)
        MotionButton(
            row,
            text="Hoje",
            command=lambda: form.vars["day"].set(self.today().isoformat()),
        ).pack(side="left", padx=4)
        MotionButton(
            row,
            text="Ontem",
            command=lambda: form.vars["day"].set(
                (self.today() - timedelta(days=1)).isoformat()
            ),
        ).pack(side="left", padx=4)
        if mock:
            ttk.Label(
                form.body,
                text="Pontuação = acertos × valor − erros × desconto + brancos × valor.\nDivisão: Matéria | acertos | erros | brancos | peso (opcional).",
                wraplength=650,
            ).grid(row=len(fields) + 2, column=0, columnspan=2, sticky="w", pady=8)
        if editing:
            ttk.Label(
                form.body,
                text="Alterar a data desloca apenas revisões pendentes. Revisões já realizadas preservam a data.",
                wraplength=650,
            ).grid(row=len(fields) + 3, column=0, columnspan=2, sticky="w")
        return form

    def clock_setup(self, initial=None):
        if self.clock.state:
            self.open_clock()
            return
        initial = dict(initial or {})
        subjects = self.subject_map()
        topics = self.topic_map(initial.get("subject_id"))
        topic_mapping = topics

        def start(v):
            sid = subjects.get(v["subject"])
            tid = topic_mapping.get(v["topic"])
            if not sid or not tid:
                raise ValueError(
                    "Escolha matéria e assunto. Cadastre um assunto em Edital se necessário."
                )
            target = parse_duration(v["target"])
            if v["mode"] == "Timer" and target <= 0:
                raise ValueError("O timer precisa de duração positiva.")
            now = self.clock.local_now()
            self.clock.start(
                dict(
                    initial,
                    plan_id=initial.get("plan_id", self.plan),
                    subject_id=sid,
                    topic_id=tid,
                    category=v["category"],
                    target=target,
                    day=now.date().isoformat(),
                    start_time=now.strftime("%H:%M"),
                ),
                v["mode"],
            )
            self.root.after(100, self.open_clock)

        form = Form(
            self,
            "Iniciar estudo",
            [
                ("subject", "Matéria", "choice", list(subjects)),
                ("topic", "Assunto", "choice", list(topics)),
                ("category", "Categoria", "choice", ["Teoria", "Questões", "Revisão"]),
                ("mode", "Modo", "choice", ["Cronômetro", "Timer"]),
                ("target", "Tempo pretendido (HH:MM:SS)", "entry"),
            ],
            start,
            {
                "subject": self.label_for(subjects, initial.get("subject_id")),
                "topic": self.label_for(topics, initial.get("topic_id")),
                "category": initial.get("category", "Teoria"),
                "mode": "Timer",
                "target": duration(
                    initial.get(
                        "target", int(self.store.pref("focus_minutes", 25)) * 60
                    )
                ),
            },
        )

        def change(e):
            nonlocal topic_mapping
            topic_mapping = self.topic_map(subjects.get(form.vars["subject"].get()))
            form.widgets["topic"].configure(values=list(topic_mapping))
            form.vars["topic"].set(next(iter(topic_mapping), ""))

        form.widgets["subject"].bind("<<ComboboxSelected>>", change)
        shortcuts = ttk.Frame(form.body)
        shortcuts.grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 0))
        for minutes in [15, 25, 45, 60]:
            MotionButton(
                shortcuts,
                text=f"{minutes} min",
                command=lambda m=minutes: form.vars["target"].set(duration(m * 60)),
            ).pack(side="left", padx=(0, 8))
        return form

    def main_goal_text(self, plan=None):
        if not self.store.pref("show_main_goal", True):
            return ""
        goal = self.store.pref("main_goal_" + (plan or self.plan))
        return (
            "Sua meta • " + goal["name"] + " — " + str(goal["target"])
            if goal
            else "Escolha sua meta principal em Metas e conquistas."
        )

    def guided_cycle(self):
        from learning import create_starter_cycle

        create_starter_cycle(
            self.store, self.plan, int(self.store.pref("focus_minutes", 25))
        )
        self.refresh()

    def open_clock(self):
        if self.clock_win and self.clock_win.winfo_exists():
            self.clock_win.lift()
            return
        if not self.clock.state:
            return self.clock_setup()
        backdrop = tk.Toplevel(self.root)
        backdrop.overrideredirect(True)
        backdrop.configure(bg="#000000")
        backdrop.attributes("-alpha", 0)

        def position_backdrop(event=None):
            if event is None or event.widget == self.root:
                backdrop.geometry(
                    f"{self.root.winfo_width()}x{self.root.winfo_height()}+{self.root.winfo_rootx()}+{self.root.winfo_rooty()}"
                )

        position_backdrop()
        backdrop.lift()
        self.motion.animate(
            backdrop, lambda t: backdrop.attributes("-alpha", t * 0.65), 320
        )
        tracking = self.root.bind("<Configure>", position_backdrop, add="+")
        win = tk.Toplevel(self.root)
        self.clock_win = win
        win.title("Modo foco • RUMO — Estudos")
        win.geometry("720x680")
        win.minsize(600, 640)
        win.configure(bg=self.bg)
        win.transient(self.root)

        def close_backdrop(event):
            if event.widget != win:
                return
            self.motion.cancel(backdrop)
            self.root.unbind("<Configure>", tracking)
            if backdrop.winfo_exists():
                backdrop.destroy()

        win.bind("<Destroy>", close_backdrop, add="+")
        backdrop.bind("<Button-1>", lambda e: win.destroy())
        state = self.clock.state
        subject = self.store.one(
            "SELECT name FROM subjects WHERE id=?", (state["subject_id"],)
        )
        topic = self.store.one(
            "SELECT name FROM topics WHERE id=?", (state["topic_id"],)
        )
        ttk.Label(win, text=subject["name"], style="Heading.TLabel").pack(pady=(24, 4))
        ttk.Label(
            win,
            text=topic["name"],
            wraplength=620,
            style="Muted.TLabel",
            justify="center",
        ).pack(pady=4)
        self.clock_label = FocusDial(win, self)
        self.clock_label.pack(fill="x", pady=2)
        self.clock_info = ttk.Label(win, text="", style="Muted.TLabel")
        self.clock_info.pack(pady=8)
        self.clock_goal = ttk.Label(
            win,
            text=self.main_goal_text(state["plan_id"]),
            style="Muted.TLabel",
            font=("Inter", 9, "bold"),
            wraplength=620,
            justify="center",
        )
        self.clock_goal.pack(pady=(0, 6))
        row = ttk.Frame(win)
        row.pack(pady=12)
        self.pause_button = MotionButton(row, text="Pausar", command=self.toggle_pause)
        self.pause_button.pack(side="left", padx=8)
        MotionButton(
            row,
            text="Finalizar e registrar",
            style="Accent.TButton",
            command=self.finish_clock,
        ).pack(side="left", padx=8)
        MotionButton(row, text="Recolher", command=win.destroy).pack(
            side="left", padx=8
        )
        row = ttk.Frame(win)
        row.pack(pady=8)
        for n in [1, 5, 15]:
            MotionButton(
                row, text=f"+{n} min", command=lambda m=n: self.clock.add(m)
            ).pack(side="left", padx=7)
        MotionButton(row, text="Descartar", command=self.discard_clock).pack(
            side="left", padx=7
        )
        MotionButton(
            row,
            text="Tela cheia",
            command=lambda: win.attributes(
                "-fullscreen", not win.attributes("-fullscreen")
            ),
        ).pack(side="left", padx=7)
        ttk.Label(
            win,
            text="Uma sessão de cada vez. Pausas não entram no tempo líquido.",
            style="Muted.TLabel",
        ).pack(pady=12)
        win.bind("<Escape>", lambda e: win.attributes("-fullscreen", False))
        self.update_clock_ui()
        self.motion.reveal(win)

    def toggle_pause(self):
        if self.clock.state["running"]:
            self.clock.pause()
        else:
            self.clock.resume()
        self.update_clock_ui()

    def discard_clock(self):
        if messagebox.askyesno(
            "Descartar sessão",
            "Descartar este rascunho sem registrar estudo?",
            parent=self.clock_win or self.root,
        ):
            self.clock.discard()
            if self.clock_win and self.clock_win.winfo_exists():
                self.clock_win.destroy()

    def finish_clock(self):
        self.clock.pause()
        state = dict(self.clock.state)
        state["elapsed"] = int(state["elapsed"])
        state.pop("running", None)
        state.pop("mode", None)
        if self.clock_win and self.clock_win.winfo_exists():
            self.clock_win.destroy()
        if getattr(self, "clock_form", None) and self.clock_form.win.winfo_exists():
            self.clock_form.win.lift()
            return
        self.clock_form = self.session_form(state, from_clock=True)

    def tick(self):
        expired = self.clock.tick()
        self.update_clock_ui()
        if self.quote_day != self.today():
            self.quote_day = self.today()
            if self.quote_header and self.quote_header.winfo_exists():
                parent = self.quote_header.master
                self.quote_header.destroy()
                from inspiration import header as quote_header

                self.quote_header = quote_header(self, parent, ASSETS / "quotes.json")
            self.status.configure(
                text=f"Hoje, {self.today():%d/%m/%Y} • Dados salvos neste computador"
            )
        if expired:
            if self.store.pref("notifications", True):
                self.notify(
                    "Timer concluído e pausado. Finalize ou acrescente tempo para continuar."
                )
            if self.store.pref("sound", False):
                self.root.bell()
        self.root.after(500, self.tick)

    def update_clock_ui(self):
        state = self.clock.state
        if state:
            elapsed = int(state["elapsed"])
            remaining = max(0, state["target"] - elapsed)
            display = remaining if state["mode"] == "Timer" else elapsed
            self.floating.set_session(True, state["running"])
            self.clock_tip.text = f"{duration(display)} · {'Em estudo' if state['running'] else 'Pausado'} — clique para retornar (Ctrl+R)"
            if self.clock_win and self.clock_win.winfo_exists():
                self.clock_label.configure(text=duration(display))
                self.clock_info.configure(
                    text=f"{state['mode']} • líquido {duration(elapsed)} / previsto {duration(state['target'])}"
                    + (f"\n{state['notice']}" if state.get("notice") else "")
                )
                self.clock_goal.configure(text=self.main_goal_text(state["plan_id"]))
                self.pause_button.configure(
                    text="Pausar" if state["running"] else "Retomar"
                )
                self.clock_label.update_progress(
                    min(100, elapsed / state["target"] * 100) if state["target"] else 0,
                    state["running"],
                )
        else:
            self.floating.set_session(False, False)
            self.clock_tip.text = "Iniciar estudo ou registrar manualmente (Ctrl+R)"

    def page_3(self):
        self.toolbar(
            [
                ("Nova tarefa", self.task_form),
                ("Calendário de apoio", self.calendar),
                ("Avisos de hoje", self.notifications),
            ]
        )
        today = self.today().isoformat()
        view = self.store.pref("review_view", "Todas")
        var = tk.StringVar(value=view)
        combo = ttk.Combobox(
            self.content,
            textvariable=var,
            values=["Todas", "Hoje", "Próximas", "Atrasadas", "Concluídas"],
            state="readonly",
        )
        combo.pack(anchor="w", pady=8)
        combo.bind(
            "<<ComboboxSelected>>",
            lambda e: (self.store.set_pref("review_view", var.get()), self.refresh()),
        )
        conditions = {
            "Todas": "",
            "Hoje": " AND r.state='Pendente' AND r.due=?",
            "Próximas": " AND r.state='Pendente' AND r.due>?",
            "Atrasadas": " AND r.state='Pendente' AND r.due<?",
            "Concluídas": " AND r.state='Concluída'",
        }
        rows = self.store.rows(
            """SELECT r.*,t.name topic,t.subject_id,s.name subject,a.material,a.next_step FROM reviews r JOIN topics t ON t.id=r.topic_id JOIN subjects s ON s.id=t.subject_id LEFT JOIN sessions a ON a.id=r.origin_id WHERE s.plan_id=?"""
            + conditions[view]
            + " ORDER BY CASE WHEN r.state='Pendente' THEN 0 ELSE 1 END,r.due LIMIT 500",
            [self.plan]
            + ([today] if view in ["Hoje", "Próximas", "Atrasadas"] else []),
        )
        mapping = {r["id"]: r for r in rows}
        tree = self.table(
            [
                ("due", "Data prevista", 115),
                ("subject", "Matéria", 180),
                ("topic", "Assunto", 280),
                ("state", "Estado", 120),
                ("material", "Material / retomada", 250),
            ],
            [
                (
                    r["id"],
                    [
                        r["due"],
                        r["subject"],
                        r["topic"],
                        (
                            "Atrasada"
                            if r["state"] == "Pendente" and r["due"] < today
                            else (
                                "Hoje"
                                if r["state"] == "Pendente" and r["due"] == today
                                else r["state"]
                            )
                        ),
                        (r["material"] or "") + " / " + (r["next_step"] or ""),
                    ],
                )
                for r in rows
            ],
            height=10,
        )

        def chosen():
            return mapping[self.selected(tree)]

        def study(timer):
            r = chosen()
            if r["state"] != "Pendente":
                raise ValueError("Esta revisão não está pendente.")
            v = {
                "subject_id": r["subject_id"],
                "topic_id": r["topic_id"],
                "category": "Revisão",
                "review_id": r["id"],
                "material": r["material"] or "",
                "next_step": r["next_step"] or "",
            }
            self.clock_setup(v) if timer else self.session_form(v)

        def reschedule():
            r = chosen()
            Form(
                self,
                "Reagendar revisão",
                [("due", "Data (AAAA-MM-DD)", "entry")],
                lambda v: self.update_review_date(r["id"], v["due"]),
                r,
            )

        def change(state):
            r = chosen()
            if messagebox.askyesno(
                "Estado da revisão",
                f"Marcar como {state}? Esta ação não cria tempo de estudo.",
                parent=self.root,
            ):
                self.store.save("reviews", {"id": r["id"], "state": state})
                self.refresh()

        self.toolbar(
            [
                ("Revisar com relógio", lambda: study(True)),
                ("Registrar revisão", lambda: study(False)),
                ("Reagendar", reschedule),
                ("Concluir tarefa", lambda: change("Concluída")),
                ("Cancelar", lambda: change("Cancelada")),
                ("Reabrir", lambda: change("Pendente")),
            ]
        )
        self.heading("Tarefas opcionais")
        tasks = self.store.rows(
            "SELECT * FROM tasks WHERE plan_id=? ORDER BY due,name", (self.plan,)
        )
        tm = {t["id"]: t for t in tasks}
        tt = self.table(
            [("name", "Tarefa", 440), ("due", "Prazo", 120), ("state", "Estado", 150)],
            [
                (t["id"], [t["name"], t["due"] or "Sem prazo", t["state"]])
                for t in tasks
            ],
            height=5,
        )
        self.toolbar(
            [
                ("Editar tarefa", lambda: self.task_form(tm[self.selected(tt)])),
                ("Excluir tarefa", lambda: self.delete_task(self.selected(tt))),
            ]
        )
        self.note(
            "Séries idênticas para o mesmo assunto, intervalo e data não se repetem. Uma nova data base pode criar uma nova série. Avisos funcionam com o aplicativo aberto."
        )

    def update_review_date(self, rid, day):
        date.fromisoformat(day)
        self.store.save("reviews", {"id": rid, "due": day})

    def task_form(self, t=None):
        t = t or {}
        mapping = self.subject_map()

        def save(v):
            if not v["name"].strip():
                raise ValueError("Digite o nome da tarefa.")
            due = v["due"].strip() or None
            if due:
                date.fromisoformat(due)
            self.store.save(
                "tasks",
                dict(
                    plan_id=self.plan,
                    name=v["name"],
                    due=due,
                    state=v["state"],
                    subject_id=mapping.get(v["subject"]),
                    **({"id": t["id"]} if t else {}),
                ),
            )

        Form(
            self,
            "Tarefa",
            [
                ("name", "Nome", "entry"),
                ("due", "Prazo opcional (AAAA-MM-DD)", "entry"),
                (
                    "state",
                    "Estado",
                    "choice",
                    ["Pendente", "Em andamento", "Concluída"],
                ),
                ("subject", "Matéria opcional", "choice", [""] + list(mapping)),
            ],
            save,
            dict(
                {
                    "state": "Pendente",
                    "subject": self.label_for(mapping, t.get("subject_id")),
                },
                **t,
            ),
        )

    def delete_task(self, rid):
        if messagebox.askyesno(
            "Excluir tarefa", "Excluir esta tarefa?", parent=self.root
        ):
            with self.store.db:
                self.store.db.execute("DELETE FROM tasks WHERE id=?", (rid,))
            self.refresh()

    def notifications(self):
        rows = self.store.rows(
            "SELECT r.due,t.name topic,s.name subject FROM reviews r JOIN topics t ON t.id=r.topic_id JOIN subjects s ON s.id=t.subject_id WHERE s.plan_id=? AND state='Pendente' AND due<=? ORDER BY due",
            (self.plan, self.today().isoformat()),
        )
        tasks = self.store.rows(
            "SELECT name,due FROM tasks WHERE plan_id=? AND state!='Concluída' AND due<=? ORDER BY due",
            (self.plan, self.today().isoformat()),
        )
        text = "\n".join(
            f"{r['due']} • {r['subject']} → {r['topic']}" for r in rows[:30]
        ) + (
            "\n\nTarefas:\n"
            + "\n".join(f"{t['due']} • {t['name']}" for t in tasks[:20])
            if tasks
            else ""
        )
        messagebox.showinfo(
            "Avisos locais",
            text or "Nenhuma revisão ou tarefa pendente para hoje.",
            parent=self.root,
        )

    def calendar(self):
        win = tk.Toplevel(self.root)
        win.title("Calendário de apoio • sessões, revisões e tarefas")
        win.geometry("1150x700")
        win.configure(bg=self.bg)
        mode = tk.StringVar(value="Semana")
        offset = [0]
        top = ttk.Frame(win)
        top.pack(fill="x", padx=12, pady=10)
        legend = ttk.Frame(win)
        legend.pack(side="bottom", fill="x", padx=12, pady=8)
        subjects = self.store.rows(
            "SELECT id,name,color FROM subjects WHERE plan_id=?", (self.plan,)
        )
        subject_colors = {s["id"]: s["color"] for s in subjects}
        for i, s in enumerate(subjects):
            ttk.Label(
                legend, text="■ " + s["name"], foreground=s["color"], wraplength=230
            ).grid(row=i // 4, column=i % 4, sticky="w", padx=5, pady=3)
        calendar_scroll = Scroll(win)
        calendar_scroll.pack(fill="both", expand=True, padx=12, pady=8)
        calendar_scroll.canvas.configure(bg=self.bg)
        body = calendar_scroll.body
        title = ttk.Label(top, text="", style="Heading.TLabel")
        title.pack(side="left")
        combo = ttk.Combobox(
            top,
            textvariable=mode,
            values=["Semana", "Mês", "Lista"],
            state="readonly",
            width=10,
        )
        combo.pack(side="right")
        mini = None

        def mini_calendar():
            nonlocal mini
            if mini and mini.winfo_exists():
                mini.destroy()
                mini = None
                return
            import calendar

            mini = tk.Toplevel(win)
            mini.title("Mini calendário")
            mini.configure(bg=self.bg)
            mini.geometry("350x290")
            month_offset = [0]
            label = tk.Label(
                mini,
                text="",
                bg=self.surface,
                fg=self.fg,
                font=("Inter", 13),
                padx=20,
                pady=12,
            )
            label.pack(fill="both", expand=True)

            def update_month(delta=0):
                month_offset[0] += delta
                absolute = (
                    self.today().year * 12 + self.today().month - 1 + month_offset[0]
                )
                year, month = divmod(absolute, 12)
                month += 1
                names = [
                    "Janeiro",
                    "Fevereiro",
                    "Março",
                    "Abril",
                    "Maio",
                    "Junho",
                    "Julho",
                    "Agosto",
                    "Setembro",
                    "Outubro",
                    "Novembro",
                    "Dezembro",
                ]
                lines = [f"{names[month-1]} {year}", "Seg Ter Qua Qui Sex Sáb Dom"] + [
                    " ".join(f"{n:3d}" if n else "   " for n in week)
                    for week in calendar.monthcalendar(year, month)
                ]
                label.configure(text="\n".join(lines))

            buttons = ttk.Frame(mini)
            buttons.pack(pady=8)
            MotionButton(buttons, text="‹ Mês", command=lambda: update_month(-1)).pack(
                side="left", padx=5
            )
            MotionButton(buttons, text="Mês ›", command=lambda: update_month(1)).pack(
                side="left", padx=5
            )
            update_month()

        MotionButton(top, text="Mini calendário", command=mini_calendar).pack(
            side="right", padx=5
        )

        def move(n):
            offset[0] += n
            draw()

        MotionButton(top, text="›", command=lambda: move(1)).pack(side="right", padx=5)
        MotionButton(top, text="‹", command=lambda: move(-1)).pack(side="right", padx=5)

        def draw(event=None):
            for w in body.winfo_children():
                w.destroy()
            if mode.get() == "Mês":
                import calendar

                total = self.today().year * 12 + self.today().month - 1 + offset[0]
                year, month = divmod(total, 12)
                month += 1
                start = date(year, month, 1)
                end = date(year, month, calendar.monthrange(year, month)[1])
                days = [
                    start + timedelta(days=i) for i in range((end - start).days + 1)
                ]
            else:
                start = (
                    self.today()
                    - timedelta(days=self.today().weekday())
                    + timedelta(weeks=offset[0])
                )
                end = start + timedelta(days=6)
                days = [start + timedelta(days=i) for i in range(7)]
            title.configure(text=f"{start:%d/%m/%Y} — {end:%d/%m/%Y}")
            events = {d.isoformat(): [] for d in days}
            event_colors = {}
            for r in self.store.sessions(
                self.plan,
                {"from": start.isoformat(), "to": end.isoformat()},
                limit=10000,
            ):
                events[r["day"]].append(
                    (
                        "Sessão",
                        f"{r['subject'] or r['mock_name']} • {duration(r['elapsed'])}",
                        r["id"],
                    )
                )
                event_colors[r["id"]] = subject_colors.get(r["subject_id"], "#D6B467")
            for r in self.store.rows(
                "SELECT r.*,t.name,s.plan_id,s.color FROM reviews r JOIN topics t ON t.id=r.topic_id JOIN subjects s ON s.id=t.subject_id WHERE s.plan_id=? AND due BETWEEN ? AND ?",
                (self.plan, start.isoformat(), end.isoformat()),
            ):
                events[r["due"]].append(
                    ("Revisão", r["name"] + " • " + r["state"], r["id"])
                )
                event_colors[r["id"]] = r["color"]
            for t in self.store.rows(
                "SELECT * FROM tasks WHERE plan_id=? AND due BETWEEN ? AND ?",
                (self.plan, start.isoformat(), end.isoformat()),
            ):
                events[t["due"]].append(
                    ("Tarefa", t["name"] + " • " + t["state"], t["id"])
                )
                event_colors[t["id"]] = subject_colors.get(t["subject_id"], "#E69757")
            if mode.get() == "Lista":
                self.table(
                    [
                        ("day", "Data", 120),
                        ("type", "Tipo", 120),
                        ("name", "Descrição", 680),
                    ],
                    [
                        (uid(), [day, kind, name])
                        for day, items in events.items()
                        for kind, name, rid in items
                    ],
                    height=14,
                    parent=body,
                )
                return
            import calendar

            for col in range(7):
                body.columnconfigure(col, weight=1)
                ttk.Label(
                    body, text=["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"][col]
                ).grid(row=0, column=col, pady=5)
            first = days[0].weekday() if mode.get() == "Mês" else 0
            drag = [None]
            day_targets = []

            def drop(event, day):
                # Resolve against our own day cards. Global window hit testing
                # can miss Tk children on Windows with scaled displays.
                for target in day_targets:
                    if (
                        target.winfo_ismapped()
                        and target.winfo_rootx()
                        <= event.x_root
                        < target.winfo_rootx() + target.winfo_width()
                        and target.winfo_rooty()
                        <= event.y_root
                        < target.winfo_rooty() + target.winfo_height()
                    ):
                        day = target.calendar_day
                        break
                if drag[0] and drag[0][0] == "Revisão":
                    rid = drag[0][1]
                    if messagebox.askyesno(
                        "Reagendar revisão", f"Mover revisão para {day}?", parent=win
                    ):
                        self.update_review_date(rid, day)
                        draw()
                        self.refresh()
                drag[0] = None

            for i, day in enumerate(days):
                pos = i + first
                card = ttk.Frame(body, style="Card.TFrame", padding=7)
                card.grid(
                    row=pos // 7 + 1, column=pos % 7, sticky="nsew", padx=3, pady=3
                )
                body.rowconfigure(pos // 7 + 1, weight=1)
                card.calendar_day = day.isoformat()
                day_targets.append(card)
                ttk.Label(card, text=f"{day.day:02d}", style="Card.TLabel").pack(
                    anchor="w"
                )
                card.bind("<ButtonRelease-1>", lambda e, d=day.isoformat(): drop(e, d))
                for kind, name, rid in events[day.isoformat()][:7]:
                    label = ttk.Label(
                        card,
                        text=f"{kind}: {name}",
                        wraplength=130,
                        style="Card.TLabel",
                        foreground=event_colors[rid],
                    )
                    label.pack(anchor="w", pady=4)
                    label.calendar_event_id = rid
                    label.bind(
                        "<ButtonPress-1>",
                        lambda e, k=kind, r=rid: drag.__setitem__(0, (k, r)),
                    )
                    label.bind(
                        "<ButtonRelease-1>", lambda e, d=day.isoformat(): drop(e, d)
                    )
                    if kind == "Revisão":
                        label.bind(
                            "<Double-1>",
                            lambda e, r=rid: Form(
                                self,
                                "Reagendar",
                                [("due", "Data (AAAA-MM-DD)", "entry")],
                                lambda v: self.update_review_date(r, v["due"]),
                                {"due": day.isoformat()},
                            ),
                        )
                if len(events[day.isoformat()]) > 7:
                    ttk.Label(
                        card,
                        text="Mais registros na visão Lista",
                        style="Card.TLabel",
                        wraplength=120,
                    ).pack()

        combo.bind("<<ComboboxSelected>>", lambda e: (offset.__setitem__(0, 0), draw()))
        draw()

    def filter_toolbar(self):
        self.toolbar(
            [
                ("Filtros", self.filter_form),
                ("Limpar", self.clear_filters),
                ("Últimos 7 dias", lambda: self.period_filter(7)),
                ("30 dias", lambda: self.period_filter(30)),
                ("Semana", self.filter_week),
                ("Mês", self.filter_month),
                ("Exportar CSV", self.export_csv),
            ]
        )
        self.note(
            "Período / filtros: "
            + (
                "; ".join(f"{k}: {v}" for k, v in self.filters.items())
                or "Tudo — do primeiro registro até hoje"
            )
        )

    def period_filter(self, n):
        self.filters.update(
            {
                "from": (self.today() - timedelta(days=n - 1)).isoformat(),
                "to": self.today().isoformat(),
            }
        )
        self.history_offset = 0
        self.refresh()

    def filter_week(self):
        a, b = self.week_bounds()
        self.filters.update({"from": a.isoformat(), "to": b.isoformat()})
        self.refresh()

    def filter_month(self):
        self.filters.update(
            {
                "from": self.today().replace(day=1).isoformat(),
                "to": self.today().isoformat(),
            }
        )
        self.refresh()

    def clear_filters(self):
        self.filters = {}
        self.history_offset = 0
        self.refresh()

    def filter_form(self):
        subjects = self.subject_map(True)
        topics = self.readable_mapping(
            self.store.rows(
                "SELECT t.* FROM topics t JOIN subjects s ON s.id=t.subject_id WHERE s.plan_id=?",
                (self.plan,),
            ),
            True,
        )
        initial = dict(
            self.filters,
            subject=self.label_for(subjects, self.filters.get("subject_id")),
            topic=self.label_for(topics, self.filters.get("topic_id")),
        )

        def save(v):
            for k in ["from", "to"]:
                if v[k]:
                    date.fromisoformat(v[k])
            if v["from"] and v["to"] and v["from"] > v["to"]:
                raise ValueError("O início deve ser anterior ao fim.")
            self.filters = {
                k: v[k] for k in ["from", "to", "category", "search"] if v[k]
            }
            self.filters.update(
                {
                    k: x
                    for k, x in [
                        ("subject_id", subjects.get(v["subject"])),
                        ("topic_id", topics.get(v["topic"])),
                    ]
                    if x
                }
            )
            self.history_offset = 0

        Form(
            self,
            "Filtros combináveis",
            [
                ("from", "De (AAAA-MM-DD)", "entry"),
                ("to", "Até (AAAA-MM-DD)", "entry"),
                ("subject", "Matéria", "choice", [""] + list(subjects)),
                ("topic", "Assunto", "choice", [""] + list(topics)),
                (
                    "category",
                    "Categoria",
                    "choice",
                    ["", "Teoria", "Questões", "Revisão", "Simulado"],
                ),
                ("search", "Pesquisar fonte / material / observações", "entry"),
            ],
            save,
            initial,
        )

    def export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="estudos.csv",
            filetypes=[("CSV", "*.csv")],
            parent=self.root,
        )
        if path:
            self.store.export_csv(path, self.plan, self.filters)
            self.notify("CSV exportado.")

    def export_stats_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="estatisticas.csv",
            filetypes=[("CSV", "*.csv")],
            parent=self.root,
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream, delimiter=";")
            writer.writerow(
                [
                    "agrupamento",
                    "grupo",
                    "tempo_liquido_segundos",
                    "tempo_previsto_segundos",
                    "acertos",
                    "erros",
                    "brancos",
                    "aproveitamento_respondidas_percentual",
                ]
            )
            for group in [self.group, "subject", "category", "topic"]:
                for r in self.store.grouped(self.plan, self.filters, group):
                    writer.writerow(
                        [
                            group,
                            r["label"],
                            round(r["elapsed"]),
                            r["target"],
                            r["correct"],
                            r["wrong"],
                            r["blank"],
                            ratio(r["correct"], r["wrong"]),
                        ]
                    )
        self.notify("CSV de estatísticas exportado com os filtros atuais.")

    def page_4(self):
        self.filter_toolbar()
        self.toolbar([("Exportar estatísticas CSV", self.export_stats_csv)])
        s = self.store.stats(self.plan, self.filters)
        p = self.store.progress(self.plan)
        self.cards(
            [
                (
                    "TEMPO LÍQUIDO",
                    duration(s["elapsed"]),
                    f"Média: {duration(s['average'])} / dia estudado",
                ),
                (
                    "APROVEITAMENTO",
                    percentage(s["rate"]),
                    f"{s['total']} questões • total apresentado: {percentage(s['presented_rate'])}",
                ),
                (
                    "CONSTÂNCIA",
                    f"{s['days']/s['period_days']*100:.1f}%",
                    f"{s['days']} dias com estudo / {s['period_days']} no período",
                ),
                (
                    "PÁGINAS",
                    str(s["pages"]) if s["pages"] is not None else "Não informado",
                    (
                        f"{s['pages_hour']:.1f} páginas/h"
                        if s["pages_hour"] is not None
                        else "Sem medição de páginas/h"
                    ),
                ),
            ]
        )
        self.note(
            f"Tempo pretendido: {duration(s['target'])} • Videoaulas: {duration(s['video']) if s['video'] is not None else 'não informado'} • Dias sem estudo: {max(0,s['period_days']-s['days'])} • Edital atual: {p['done']}/{p['total']} folhas (não depende do filtro de sessões)."
        )
        from charts import question_summary

        question_summary(self, s)
        self.heading("Evolução de questões e aproveitamento")
        self.toolbar(
            [
                ("Diária", lambda: self.change_group("day")),
                ("Semanal", lambda: self.change_group("week")),
                ("Mensal", lambda: self.change_group("month")),
            ]
        )
        rows = self.store.grouped(self.plan, self.filters, self.group)
        self.bar_chart(rows, "questions", True)
        self.heading("Tempo líquido de estudo")
        self.bar_chart(rows, "elapsed")
        self.heading("Horas por matéria")
        self.horizontal_chart(self.store.grouped(self.plan, self.filters, "subject"))
        strengths = self.store.grouped(self.plan, self.filters, "subject")
        weak = sorted(
            (r for r in strengths if r["correct"] + r["wrong"] >= 10),
            key=lambda r: ratio(r["correct"], r["wrong"]),
        )[:3]
        self.heading("Onde concentrar a próxima revisão")
        if weak:
            for row in weak:
                self.note(
                    f"{row['label']} • {percentage(ratio(row['correct'],row['wrong']))} de acertos em {row['correct']+row['wrong']} respostas • {duration(row['elapsed'])} estudados"
                )
        else:
            self.note(
                "Registre pelo menos 10 respostas por matéria para comparar pontos de atenção com uma amostra mínima."
            )
        self.heading("Distribuição por matéria / categoria / assunto")
        for group, label in [
            ("subject", "Matéria"),
            ("category", "Categoria"),
            ("topic", "Assunto"),
        ]:
            rows = self.store.grouped(self.plan, self.filters, group)
            self.table(
                [
                    ("name", label, 420),
                    ("time", "Tempo líquido", 130),
                    ("target", "Previsto", 130),
                    ("total", "Questões", 100),
                    ("rate", "Acertos (%)", 110),
                ],
                [
                    (
                        uid(),
                        [
                            r["label"],
                            duration(r["elapsed"]),
                            duration(r["target"]),
                            r["correct"] + r["wrong"] + r["blank"],
                            percentage(ratio(r["correct"], r["wrong"])),
                        ],
                    )
                    for r in rows
                ],
                height=min(6, max(2, len(rows))),
            )
        self.toolbar(
            [("Abrir registros deste filtro", lambda: self.navigate("Histórico"))]
        )
        self.note(
            "Médias de aproveitamento são ponderadas pelo número de questões. Dias sem questões não recebem 0%. Os gráficos mostram até 60 grupos recentes; o CSV contém todos os registros do filtro."
        )

    def change_group(self, group):
        self.group = group
        self.refresh()

    def subject_detail(self, sid):
        self.filters = {"subject_id": sid}
        self.navigate("Histórico")

    def page_5(self):
        self.filter_toolbar()
        s = self.store.stats(self.plan, self.filters)
        p = self.store.progress(self.plan)
        self.cards(
            [
                ("TEMPO", duration(s["elapsed"]), f"{s['count']} registros"),
                (
                    "DESEMPENHO",
                    percentage(s["rate"]),
                    f"{s['correct']} acertos / {s['wrong']} erros",
                ),
                (
                    "PÁGINAS",
                    str(s["pages"]) if s["pages"] is not None else "Não informado",
                    "Somente registros do filtro",
                ),
                (
                    "EDITAL ATUAL",
                    f"{p['done']}/{p['total']}",
                    "Conclusão explícita de folhas",
                ),
            ]
        )
        rows = self.store.sessions(
            self.plan, self.filters, limit=100, offset=self.history_offset
        )
        mapping = {r["id"]: r for r in rows}
        tree = self.table(
            [
                ("day", "Data", 110),
                ("subject", "Matéria", 180),
                ("topic", "Assunto / simulado", 280),
                ("time", "Líquido", 100),
                ("total", "Questões", 75),
                ("rate", "Acertos (%)", 110),
                ("category", "Categoria", 100),
            ],
            [
                (
                    r["id"],
                    [
                        r["day"],
                        r["subject"] or "Simulados — sem matéria",
                        r["topic"] or r["mock_name"],
                        duration(r["elapsed"]),
                        r["correct"] + r["wrong"] + r["blank"],
                        percentage(ratio(r["correct"], r["wrong"])),
                        r["category"],
                    ],
                )
                for r in rows
            ],
            height=12,
        )
        tree.configure(
            show="tree headings",
            displaycolumns=["subject", "topic", "time", "total", "rate", "category"],
        )
        tree.heading("#0", text="Dia")
        tree.column("#0", width=135, minwidth=100, stretch=False)
        daily = {
            r["label"]: r["elapsed"]
            for r in self.store.grouped(self.plan, self.filters)
        }
        for r in rows:
            parent = "day:" + r["day"]
            if not tree.exists(parent):
                tree.insert(
                    "",
                    "end",
                    iid=parent,
                    text=r["day"],
                    open=True,
                    values=["", "", "", duration(daily.get(r["day"], 0)), "", "", ""],
                )
            tree.move(r["id"], parent, "end")

        def chosen():
            rid = self.selected(tree)
            if rid not in mapping:
                raise ValueError("Selecione um estudo dentro do grupo do dia.")
            return rid

        self.toolbar(
            [
                (
                    "Detalhes / anotações",
                    lambda: self.session_details(mapping[chosen()]),
                ),
                (
                    "Editar",
                    lambda: self.session_form(
                        editing=self.store.one(
                            "SELECT * FROM sessions WHERE id=?", (chosen(),)
                        )
                    ),
                ),
                ("Excluir", lambda: self.remove_session(chosen())),
                ("‹ Anterior", lambda: self.history_page(-1)),
                ("Próximos ›", lambda: self.history_page(1)),
            ]
        )
        tree.bind(
            "<Double-1>",
            lambda e: (
                self.session_details(mapping[self.selected(tree)])
                if tree.selection() and self.selected(tree) in mapping
                else None
            ),
        )
        self.note(
            f"Registros {self.history_offset+1}–{self.history_offset+len(rows)}. Carregamento em páginas de 100 para limitar RAM."
        )
        self.heading("Totais por dia (filtro atual)")
        self.table(
            [
                ("day", "Dia", 130),
                ("time", "Tempo líquido", 140),
                ("total", "Questões", 100),
            ],
            [
                (
                    r["label"],
                    [
                        r["label"],
                        duration(r["elapsed"]),
                        r["correct"] + r["wrong"] + r["blank"],
                    ],
                )
                for r in self.store.grouped(self.plan, self.filters)[-60:]
            ],
            height=5,
        )

    def history_page(self, n):
        self.history_offset = max(0, self.history_offset + n * 100)
        self.refresh()

    def session_details(self, r):
        hour = r["start_time"]
        if hour and self.store.pref("time_format", "24h") == "12h":
            hour = datetime.strptime(hour, "%H:%M").strftime("%I:%M %p")
        text = f"{r['day']} {hour}\n{r['subject'] or 'Simulado sem matéria'} → {r['topic'] or r['mock_name']}\n{r['category']}\n\nPretendido: {duration(r['target'])}\nLíquido: {duration(r['elapsed'])}\nAcertos: {r['correct']} • Erros: {r['wrong']} • Brancos: {r['blank']}\nAcertos/respondidas: {percentage(ratio(r['correct'],r['wrong']))}\nAcertos/total: {percentage(ratio(r['correct'],r['wrong'],r['blank'],True))}\n\nMaterial: {r['material']}\nLink: {r['url']}\nPáginas: {r['pages'] if r['pages'] is not None else 'Não informado'}\nVideoaula: {duration(r['video']) if r['video'] is not None else 'Não informado'}\n\nOnde parei: {r['next_step']}\n\nObservações: {r['notes']}"
        pauses = json.loads(r.get("pauses", "[]"))
        if pauses:
            text += "\n\nEventos do relógio:\n" + "\n".join(
                f"{p.get('at','')} • {p.get('event','Pausa')} • líquido {duration(p.get('elapsed',0))}"
                for p in pauses
            )
        win = tk.Toplevel(self.root)
        win.title("Detalhes do estudo")
        win.geometry("700x650")
        win.configure(bg=self.bg)
        widget = tk.Text(
            win,
            wrap="word",
            bg=self.surface,
            fg=self.fg,
            font=("Inter", 11),
            relief="flat",
            padx=20,
            pady=20,
        )
        widget.insert("1.0", text)
        widget.configure(state="disabled")
        widget.pack(fill="both", expand=True)
        if r["url"]:
            MotionButton(
                win, text="Abrir link", command=lambda: self.open_link(r["url"])
            ).pack(pady=8)

    def remove_session(self, sid):
        if messagebox.askyesno(
            "Excluir estudo",
            "Excluir este estudo e recalcular tempo, questões, ciclo e revisões pendentes da sessão? A conclusão explícita da teoria será preservada.",
            parent=self.root,
        ):
            self.store.delete_session(sid)
            self.refresh()

    def page_6(self):
        self.toolbar(
            [
                ("Novo simulado", lambda: self.session_form({"category": "Simulado"})),
                ("Filtros", self.filter_form),
            ]
        )
        f = dict(self.filters, category="Simulado")
        rows = self.store.sessions(self.plan, f, limit=500)
        mapping = {r["id"]: r for r in rows}
        last = rows[0] if rows else None
        self.cards(
            [
                ("SIMULADOS", str(len(rows)), "Resultados reais; até 500 recentes"),
                (
                    "ÚLTIMO",
                    (
                        percentage(
                            ratio(last["correct"], last["wrong"], last["blank"], True)
                        )
                        if last
                        else "Sem simulado"
                    ),
                    "Acertos / total apresentado",
                ),
                (
                    "RESPONDIDAS",
                    (
                        percentage(ratio(last["correct"], last["wrong"]))
                        if last
                        else "Sem questões"
                    ),
                    "Acertos / (acertos + erros)",
                ),
            ]
        )
        if last:
            self.note(
                f"Último: {last['correct']} acertos • {last['wrong']} erros • {last['blank']} brancos • Pontuação: {self.mock_score(last):g}"
            )
        graph = []
        for r in reversed(rows):
            graph.append(
                {
                    "label": r["day"],
                    "elapsed": r["elapsed"],
                    "target": r["target"],
                    "correct": r["correct"],
                    "wrong": r["wrong"],
                    "blank": r["blank"],
                    "score": self.mock_score(r),
                    "rate": ratio(r["correct"], r["wrong"], r["blank"], True) or 0,
                }
            )
        mode = tk.StringVar(value=self.store.pref("mock_chart", "Desempenho"))
        row = ttk.Frame(self.content)
        row.pack(fill="x", pady=8)
        combo = ttk.Combobox(
            row, textvariable=mode, values=["Desempenho", "Pontuação"], state="readonly"
        )
        combo.pack(side="left")
        combo.bind(
            "<<ComboboxSelected>>",
            lambda e: (self.store.set_pref("mock_chart", mode.get()), self.refresh()),
        )
        self.bar_chart(graph, "rate" if mode.get() == "Desempenho" else "score")
        self.note(
            "Desempenho: acertos/total (%). Pontuação: valores configurados no registro, com pesos da divisão por matéria quando informados."
        )
        tree = self.table(
            [
                ("day", "Data", 110),
                ("name", "Simulado", 240),
                ("format", "Formato", 130),
                ("time", "Tempo", 95),
                ("c", "Acertos", 65),
                ("w", "Erros", 65),
                ("b", "Brancos", 65),
                ("score", "Pontuação", 95),
            ],
            [
                (
                    r["id"],
                    [
                        r["day"],
                        r["mock_name"],
                        r["mock_format"],
                        duration(r["elapsed"]),
                        r["correct"],
                        r["wrong"],
                        r["blank"],
                        f"{self.mock_score(r):g}",
                    ],
                )
                for r in rows
            ],
            height=9,
        )
        self.toolbar(
            [
                ("Detalhes", lambda: self.mock_details(mapping[self.selected(tree)])),
                (
                    "Editar",
                    lambda: self.session_form(
                        editing=self.store.one(
                            "SELECT * FROM sessions WHERE id=?", (self.selected(tree),)
                        )
                    ),
                ),
                ("Excluir", lambda: self.remove_session(self.selected(tree))),
            ]
        )

    def mock_score(self, r):
        results = self.store.rows(
            "SELECT * FROM mock_results WHERE session_id=?", (r["id"],)
        )
        if results:
            return sum(
                (
                    x["correct"] * r["score_correct"]
                    - x["wrong"] * r["score_wrong"]
                    + x["blank"] * r["score_blank"]
                )
                * x["weight"]
                for x in results
            )
        return (
            r["correct"] * r["score_correct"]
            - r["wrong"] * r["score_wrong"]
            + r["blank"] * r["score_blank"]
        )

    def mock_details(self, r):
        results = self.store.rows(
            "SELECT r.*,s.name FROM mock_results r JOIN subjects s ON s.id=r.subject_id WHERE session_id=?",
            (r["id"],),
        )
        messagebox.showinfo(
            "Matérias incluídas",
            f"Pontuação = acertos × {r['score_correct']} − erros × {r['score_wrong']} + brancos × {r['score_blank']}\nPontuação total: {self.mock_score(r):g}\n\n"
            + (
                "\n".join(
                    f"{x['name']} • {x['correct']} acertos / {x['wrong']} erros / {x['blank']} brancos • peso {x['weight']}"
                    for x in results
                )
                or "Totais gerais sem divisão por matéria."
            ),
            parent=self.root,
        )
        self.session_details(r)

    def page_7(self):
        from challenges import render

        render(self)
        self.toolbar([("Nova meta semanal", self.goal_form)])
        self.goal_bars()
        goals = self.store.rows(
            "SELECT g.*,s.name subject FROM goals g LEFT JOIN subjects s ON s.id=g.subject_id WHERE g.plan_id=?",
            (self.plan,),
        )
        mapping = {g["id"]: g for g in goals}
        tree = self.table(
            [
                ("name", "Plano / matéria", 350),
                ("hours", "Horas / semana", 160),
                ("questions", "Questões / semana", 180),
            ],
            [
                (g["id"], [g["subject"] or "Todo o plano", g["hours"], g["questions"]])
                for g in goals
            ],
            height=4,
        )

        def principal():
            goal = mapping[self.selected(tree)]
            self.store.set_pref(
                "main_goal_" + self.plan,
                {
                    "name": "Minha meta semanal",
                    "target": f"{goal['hours']:g} h e {goal['questions']} questões por semana",
                },
            )
            self.refresh()

        self.toolbar(
            [
                ("Tornar meta principal", principal),
                ("Editar meta", lambda: self.goal_form(mapping[self.selected(tree)])),
                ("Excluir meta", lambda: self.delete_goal(self.selected(tree))),
            ]
        )
        if not self.store.pref("achievements", True):
            self.note(
                "Conquistas desativadas nas preferências. As metas continuam disponíveis."
            )
            return
        current, best, days = self.store.streak(self.plan)
        eligible = self.store.pref("eligible_days", [0, 1, 2, 3, 4, 5, 6])
        start, end = self.week_bounds()
        pool = set(days)
        week_days = [
            start + timedelta(days=i)
            for i in range(7)
            if (start + timedelta(days=i)).weekday() in eligible
        ]
        week_count = sum(d in pool for d in week_days)
        mocks = self.store.stats(self.plan, {"category": "Simulado"})["count"]
        night = self.store.one(
            "SELECT COUNT(*) n FROM sessions WHERE plan_id=? AND elapsed>0 AND start_time>='22:00'",
            (self.plan,),
        )["n"]
        self.heading("Conquistas locais • critérios transparentes")
        achievements = [
            (
                "Primeiros 7 dias sem falhar",
                f"{min(best,7)}/7",
                "7 dias consecutivos com tempo líquido positivo (ou mínimo configurado).",
                best >= 7,
            ),
            (
                "Semana perfeita",
                f"{week_count}/{len(week_days)}",
                "Estudar nos dias elegíveis desta semana. Recalculada ao corrigir registros.",
                bool(week_days) and week_count == len(week_days),
            ),
            (
                "Mestre dos simulados",
                f"{min(mocks,10)}/10",
                "10 simulados registrados no plano.",
                mocks >= 10,
            ),
        ]
        if self.store.pref("night_achievement", False):
            achievements.append(
                (
                    "Corujão",
                    str(night),
                    "Opcional: uma sessão iniciada após 22h. Não exige reduzir seu sono.",
                    night > 0,
                )
            )
        for name, progress, rule, done in achievements:
            self.heading(("✓ " if done else "○ ") + name + " • " + progress)
            self.note(rule)
        self.note(
            f"Sequência atual: {current} dias. Conquistas são derivadas do banco; alterações de registros podem revogar uma conquista. Não há ranking ou punição por interrupções."
        )

    def goal_form(self, g=None):
        g = g or {}
        subjects = self.subject_map()

        def save(v):
            hours = float(v["hours"])
            questions = int(v["questions"])
            if not 0 <= hours <= 168 or questions < 0:
                raise ValueError("Use horas entre 0 e 168 e questões não negativas.")
            self.store.save(
                "goals",
                dict(
                    plan_id=self.plan,
                    subject_id=subjects.get(v["subject"]),
                    hours=hours,
                    questions=questions,
                    **({"id": g["id"]} if g else {}),
                ),
            )

        Form(
            self,
            "Meta semanal",
            [
                ("subject", "Matéria opcional", "choice", [""] + list(subjects)),
                ("hours", "Horas líquidas por semana", "entry"),
                ("questions", "Questões por semana", "entry"),
            ],
            save,
            {
                "subject": self.label_for(subjects, g.get("subject_id")),
                "hours": g.get("hours", 10),
                "questions": g.get("questions", 100),
            },
        )

    def delete_goal(self, rid):
        if messagebox.askyesno("Excluir meta", "Excluir esta meta?", parent=self.root):
            with self.store.db:
                self.store.db.execute("DELETE FROM goals WHERE id=?", (rid,))
            self.refresh()

    def page_8(self):
        groups = [
            (
                "Aparência e conforto",
                "Fonte Inter, tema claro suave e animações que você pode reduzir.",
                [
                    ("Ajustar aparência e preferências", self.preferences),
                    ("Alternar claro / escuro", self.toggle_theme),
                ],
            ),
            (
                "Sua rotina de estudo",
                "Duração inicial do foco, blocos do ciclo, ordem do edital e meta principal.",
                [
                    ("Preferências da rotina", self.preferences),
                    ("Ver metas", lambda: self.navigate("Metas e conquistas")),
                    ("Organizar ciclo", lambda: self.navigate("Ciclo de estudos")),
                ],
            ),
            (
                "Planos, matérias e conteúdo",
                "Seus concursos ficam separados. Arquivar mantém o histórico.",
                [
                    ("Gerenciar planos e matérias", self.manage_entities),
                    ("Fontes do edital", self.syllabus_audit),
                ],
            ),
            (
                "Dados e recuperação",
                "Backups incluem observações, conclusões, ciclos e preferências. Restaurar mostra uma prévia antes de substituir.",
                [
                    ("Exportar backup JSON", self.export_backup),
                    ("Backup SQLite agora", self.manual_backup),
                    ("Restaurar backup", self.restore_backup),
                    ("Destino de backups", self.backup_folder),
                    (
                        "Abrir pasta dos dados",
                        lambda: self.open_folder(self.store.path.parent),
                    ),
                    ("Exportar CSV", self.export_csv),
                ],
            ),
        ]
        for title, description, actions in groups:
            panel = Panel(self.content, self)
            panel.pack(fill="x", pady=(8, 4))
            with self.in_panel(panel):
                self.heading(title)
                self.note(description)
                self.toolbar(actions)
        self.heading("Atalhos e funcionamento")
        self.note(
            "Ctrl+R: iniciar ou retomar o foco. Ctrl+N: registrar estudo. Ctrl+Enter: salvar. Esc: fechar janela. Pausas e tempo com o programa fechado não contam como estudo."
        )
        self.note(
            f'Hoje: {self.today():%d/%m/%Y} • Fuso: {self.store.pref("timezone","Sistema")} • Dados: {self.store.path}'
        )

    def legacy_help(self):
        self.toolbar(
            [
                ("Preferências", self.preferences),
                ("Planos / matérias", self.manage_entities),
                ("Exportar backup JSON", self.export_backup),
                ("Restaurar backup", self.restore_backup),
            ]
        )
        self.toolbar(
            [
                ("Backup SQLite agora", self.manual_backup),
                ("Destino de backups", self.backup_folder),
                (
                    "Abrir pasta dos dados",
                    lambda: self.open_folder(self.store.path.parent),
                ),
                ("Exportar CSV", self.export_csv),
            ]
        )
        self.heading("Seus dados ficam neste computador")
        self.note(str(self.store.path))
        self.note(
            "Backups automáticos: "
            + str(
                self.store.pref(
                    "backup_folder", str(self.store.path.parent / "backups")
                )
            )
        )
        self.heading("Como estudar")
        self.note(
            "1. Em Edital e assuntos, importe a área do BACEN 2024 ou cadastre suas matérias e assuntos. O PDF original está incluído, para consulta offline. A lista histórica não prevê o conteúdo de um futuro edital."
        )
        self.note(
            "2. Em Ciclo de estudos, gere uma fila ou adicione blocos. Sessões curtas acumulam tempo no mesmo bloco. Concluir, adiar e iniciar a próxima volta são ações suas."
        )
        self.note(
            "3. Adicionar estudo registra tempo líquido e questões. Ctrl+N abre o registro. Ctrl+R abre o relógio. O tempo pretendido nunca vira automaticamente tempo estudado."
        )
        self.note(
            "4. O relógio continua durante a navegação. Fechar o aplicativo pausa e preserva o rascunho. Ao recuperar, a ausência não conta como estudo. Checkpoints a cada 5 segundos limitam perda por falha inesperada."
        )
        self.note(
            "5. Finalizar o relógio abre o registro. Cancelar preserva o rascunho pausado; salvar remove o rascunho na mesma transação, evitando duplicação."
        )
        self.note(
            "6. Revisões podem ser concluídas como tarefa ou com um estudo registrado. Teoria concluída, bloco concluído e revisão concluída são estados diferentes."
        )
        self.heading("Backup e restauração")
        self.note(
            "O backup JSON contém planos, assuntos, registros, ciclos, revisões, preferências e rascunho. A restauração valida antes de substituir e cria uma cópia SQLite anterior. Backups automáticos diários usam a API consistente do SQLite e retenção configurável. Guarde uma cópia em outro local."
        )
        self.heading("Medições e desempenho")
        self.note(
            "Gráficos e totais vêm do banco. Aproveitamento = acertos / questões respondidas. Simulados também mostram acertos / total apresentado. Os resultados por matéria não duplicam os totais gerais. Páginas/h usa apenas tempo de sessões com páginas informadas."
        )
        self.note(
            "Aplicativo nativo sem navegador embutido, servidor ou serviço em segundo plano. Histórico paginado, cache SQLite de 2 MB e gráficos de até 60 grupos. Nenhuma conexão de rede durante uso normal; links só abrem por sua ação."
        )
        self.note(
            "Dados manuais usam a data atribuída à sessão. Para relógio atravessando meia-noite, segmentos medidos são preservados; a divisão diária de tempo usa esses segmentos. Questões permanecem na data escolhida no registro."
        )

    def preferences(self):
        defaults = {
            "animations": True,
            "theme": "Escuro",
            "daily_subjects": 3,
            "block_minutes": 45,
            "review_intervals": [1, 7, 30, 60, 120],
            "week_start": 0,
            "streak_min_minutes": 0,
            "retention": 7,
            "sound": False,
            "night_achievement": False,
            "profile": "",
            "motivation": True,
            "achievements": True,
            "notifications": True,
            "time_format": "24h",
            "timezone": "Sistema",
            "focus_minutes": 25,
            "show_main_goal": True,
            "syllabus_order": "Aprendizagem",
            "eligible_days": [0, 1, 2, 3, 4, 5, 6],
        }
        initial = {k: self.store.pref(k, v) for k, v in defaults.items()}
        initial["review_intervals"] = ",".join(map(str, initial["review_intervals"]))
        initial["eligible_days"] = ",".join(map(str, initial["eligible_days"]))

        def save(v):
            for k in [
                "daily_subjects",
                "block_minutes",
                "focus_minutes",
                "week_start",
                "streak_min_minutes",
                "retention",
            ]:
                v[k] = int(v[k])
            if not 1 <= v["focus_minutes"] <= 180:
                raise ValueError("O foco inicial deve durar de 1 a 180 minutos.")
            if (
                v["daily_subjects"] not in [2, 3]
                or not 1 <= v["block_minutes"] <= 600
                or not 0 <= v["week_start"] <= 6
                or not 0 <= v["streak_min_minutes"] <= 1440
                or not 1 <= v["retention"] <= 100
            ):
                raise ValueError("Confira os limites das preferências.")
            v["review_intervals"] = sorted(
                set(int(x) for x in v["review_intervals"].split(",") if x.strip())
            )
            v["eligible_days"] = sorted(
                set(int(x) for x in v["eligible_days"].split(",") if x.strip())
            )
            if (
                any(x <= 0 or x > 36500 for x in v["review_intervals"])
                or not v["eligible_days"]
                or any(x < 0 or x > 6 for x in v["eligible_days"])
            ):
                raise ValueError("Intervalos positivos; dias elegíveis de 0 a 6.")
            if v["timezone"] != "Sistema":
                from zoneinfo import ZoneInfo

                ZoneInfo(v["timezone"])
            for k, value in v.items():
                self.store.set_pref(k, value)
            self.apply_theme()
            self.root.after_idle(lambda: (self.build_shell(), self.refresh()))

        Form(
            self,
            "Preferências locais",
            [
                ("animations", "Animações suaves", "bool"),
                ("show_main_goal", "Lembrar minha meta durante o foco", "bool"),
                ("focus_minutes", "Duração inicial do foco (minutos)", "entry"),
                (
                    "syllabus_order",
                    "Ordem dos assuntos",
                    "choice",
                    ["Aprendizagem", "Edital"],
                ),
                ("theme", "Tema", "choice", ["Escuro", "Claro", "Sistema"]),
                (
                    "daily_subjects",
                    "Matérias sugeridas por dia (2 ou 3)",
                    "choice",
                    ["2", "3"],
                ),
                ("block_minutes", "Minutos por bloco (1–600)", "entry"),
                ("review_intervals", "Intervalos de revisão (dias)", "entry"),
                ("week_start", "Início da semana (0=seg, 6=dom)", "entry"),
                ("eligible_days", "Dias elegíveis (0=seg até 6=dom)", "entry"),
                (
                    "streak_min_minutes",
                    "Mínimo diário para constância (0=positivo)",
                    "entry",
                ),
                ("retention", "Quantidade de backups (1–100)", "entry"),
                ("timezone", "Fuso IANA ou Sistema", "entry"),
                (
                    "time_format",
                    "Horários nos detalhes (durações em HH:MM:SS)",
                    "choice",
                    ["24h", "12h"],
                ),
                ("profile", "Nome local opcional", "entry"),
                ("sound", "Som ao encerrar timer", "bool"),
                ("notifications", "Avisos locais do timer", "bool"),
                ("motivation", "Mensagens de motivação", "bool"),
                ("achievements", "Exibir conquistas", "bool"),
                ("night_achievement", "Ativar conquista Corujão", "bool"),
            ],
            save,
            initial,
        )

    def export_backup(self):
        self.clock.pause()
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=f"RUMO-{self.today()}.json",
            filetypes=[("Backup RUMO — Estudos", "*.json")],
            parent=self.root,
        )
        if path:
            self.store.export(path)
            self.notify("Backup completo exportado.")

    def restore_backup(self):
        if self.clock.state:
            raise ValueError(
                "Finalize ou descarte o rascunho antes de restaurar outro backup."
            )
        path = filedialog.askopenfilename(
            filetypes=[("Backup RUMO — Estudos", "*.json *.sqlite3 *.db")],
            parent=self.root,
        )
        if not path:
            return
        data = self.store.validate_backup(path)
        counts = "\n".join(
            f'{name}: {len(data["tables"][name])}'
            for name in ["plans", "subjects", "topics", "sessions", "cycles", "reviews"]
        )
        if messagebox.askyesno(
            "Prévia da restauração",
            f'Backup de {data.get("created","data desconhecida")}\n{counts}\n\nSubstituir os dados atuais? Será criado um backup anterior.',
            parent=self.root,
        ):
            self.store.restore(path)
            self.clock = Clock(self.store)
            p = self.store.one("SELECT id FROM plans WHERE archived=0 LIMIT 1")
            self.plan = self.store.pref("active_plan", p["id"] if p else None)
            if not self.store.one("SELECT id FROM plans WHERE id=?", (self.plan,)):
                self.plan = (
                    p["id"] if p else self.store.save("plans", {"name": "Meu plano"})
                )
            self.filters = {}
            self.apply_theme()
            self.build_shell()
            self.refresh()
            self.notify("Backup restaurado e rascunho pausado.")

    def manual_backup(self):
        path = self.store.auto_backup(force=True)
        self.notify("Backup consistente criado: " + str(path))

    def backup_folder(self):
        path = filedialog.askdirectory(parent=self.root)
        if path:
            self.store.set_pref("backup_folder", path)
            self.refresh()

    def open_folder(self, path):
        path = directory_path(path)
        if os.name == "nt":
            os.startfile(path)
        else:
            webbrowser.open(Path(path).as_uri())

    def close(self):
        if self.clock.state:
            if not messagebox.askyesno(
                "Sessão em andamento",
                "Pausar e guardar o rascunho para continuar depois?",
                parent=self.root,
            ):
                return
            self.clock.pause()
        self.store.db.close()
        self.root.destroy()


def single_instance(folder):
    folder.mkdir(parents=True, exist_ok=True)
    file = open(folder / "instance.lock", "a+b")
    try:
        if os.name == "nt":
            import msvcrt

            file.seek(0)
            file.write(b"0")
            file.flush()
            file.seek(0)
            msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        file.close()
        return None
    return file


def main():
    try:
        folder = data_dir()
    except (ValueError, OSError) as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("RUMO — Estudos", str(error))
        root.destroy()
        return
    folder.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=folder / "app.log",
        level=logging.ERROR,
        encoding="utf-8",
        format="%(asctime)s %(message)s",
    )
    lock = single_instance(folder)
    if lock is None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "RUMO — Estudos", "O aplicativo já está aberto. Use a janela existente."
        )
        root.destroy()
        return
    if os.name == "nt":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "RUMO.Estudos.Local"
        )
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    App(root)
    root.mainloop()
    lock.close()


if __name__ == "__main__":
    main()
