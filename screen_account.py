"""Native opt-in account controls; network work never blocks the Tk thread."""

import json
import queue
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from desktop_sync import (
    note_server_features,
    capture_new_sessions,
    capture_profile_and_cycle,
    export_workspace,
    import_remote_sessions,
    service_for,
    workspace_for,
)
import token_store
from sync_client import SupabaseTransport, SyncWorkspace, SyncError
from study_sync import StudySync
from service_config import PUBLIC_KEY, SERVICE_URL

LABELS = {
    "offline": "Offline — suas ações continuam salvas",
    "pending": "Ações aguardando envio",
    "syncing": "Sincronizando…",
    "synced": "Sincronizado",
    "conflict": "Conflito — escolha qual alteração manter",
    "error": "Falha de sincronização — tente novamente",
}


def render(app):
    workspace = workspace_for(app.store)
    panel = ttk.Frame(app.content, padding=16, style="Panel.TFrame")
    panel.pack(fill="x", pady=8)
    ttk.Label(panel, text="Conta e sincronização", style="Heading.TLabel").pack(
        anchor="w"
    )
    ttk.Label(
        panel,
        text="Conectar é opcional. O histórico antigo fica local até você escolher o que compartilhar.",
        wraplength=680,
        style="Muted.TLabel",
    ).pack(anchor="w", pady=(6, 12))
    status = tk.StringVar(value=LABELS.get(workspace.status, workspace.status))
    ttk.Label(panel, textvariable=status, wraplength=680).pack(anchor="w", pady=6)
    fields = {}
    advanced = ttk.Frame(panel)

    def toggle_service():
        if advanced.winfo_manager():
            advanced.pack_forget()
        else:
            advanced.pack(fill="x", before=consent_button, pady=8)

    ttk.Button(panel, text="Configuração do serviço", command=toggle_service).pack(
        anchor="w", pady=4
    )
    for key, label in (
        ("url", "Endereço do serviço"),
        ("key", "Chave pública do serviço"),
        ("email", "E-mail"),
        ("password", "Senha"),
    ):
        parent = advanced if key in ("url", "key") else panel
        ttk.Label(parent, text=label).pack(anchor="w", pady=(8, 3))
        fields[key] = tk.StringVar(
            value=(
                workspace._meta("service_" + key)
                or {"url": SERVICE_URL, "key": PUBLIC_KEY}[key]
                if key in ("url", "key")
                else ""
            )
        )
        ttk.Entry(
            parent, textvariable=fields[key], show="•" if key == "password" else ""
        ).pack(fill="x")
    consent = tk.BooleanVar(value=False)
    consent_button = ttk.Checkbutton(
        panel,
        text="Compartilhar novas ações de estudo com esta conta",
        variable=consent,
    )
    consent_button.pack(anchor="w", pady=(12, 4))
    login_file = app.store.path.with_name("study-sync-login.json")
    remember = tk.BooleanVar(value=login_file.exists())
    ttk.Checkbutton(
        panel,
        text="Manter conectado neste computador (guarda só o token de renovação; Sair apaga)",
        variable=remember,
    ).pack(anchor="w", pady=(0, 12))
    actions = ttk.Frame(panel)
    actions.pack(fill="x", pady=4)
    mailbox = queue.Queue()
    busy = getattr(app, "study_network_busy", None)
    if busy is None:
        busy = [False]
        app.study_network_busy = busy

    def run(action):
        if busy[0]:
            return
        if action == "restore":
            stored = token_store.load(login_file)
            if not stored or not workspace.account_id:
                return
        if action == "login" and not consent.get():
            status.set("Marque a opção de compartilhar novas ações antes de conectar.")
            return
        if action == "logout":
            token_store.clear(login_file)
        if action != "logout":
            if workspace._meta("session_baseline") is None:
                with workspace.db:
                    workspace.db.execute(
                        "INSERT INTO metadata VALUES('session_baseline',?)",
                        (
                            json.dumps(
                                [
                                    r["id"]
                                    for r in app.store.rows("SELECT id FROM sessions")
                                ]
                            ),
                        ),
                    )
            capture_new_sessions(app.store)
            # Aparência/equipados e ciclo vão ao site como retrato somente leitura.
            capture_profile_and_cycle(app.store, getattr(app, "plan", None))
        values = {key: value.get() for key, value in fields.items()}
        fields["password"].set("")
        busy[0] = True
        status.set(
            "Conectando…" if action in ("login", "restore") else LABELS["syncing"]
        )
        path = app.store.path.with_name("study-sync.sqlite3")
        transport = getattr(app, "study_transport", None)

        def work():
            local = None
            try:
                local = SyncWorkspace(path)
                StudySync(local)
                client = transport
                if action == "restore":
                    client = SupabaseTransport(values["url"], values["key"])
                    client.refresh_token = stored
                    client.refresh()
                    if client.account_id != local.account_id:
                        raise ValueError(
                            "O login salvo é de outra conta. Entre novamente."
                        )
                if action == "login":
                    client = SupabaseTransport(values["url"], values["key"])
                    client.login(values["email"], values["password"])
                    local.bind_account(client.account_id, consent=True)
                    with local.db:
                        for key in ("url", "key"):
                            local.db.execute(
                                "INSERT OR REPLACE INTO metadata VALUES(?,?)",
                                ("service_" + key, values[key]),
                            )
                if client is None:
                    raise ValueError("Entre na conta antes de sincronizar.")
                if action == "logout":
                    client.logout()
                    mailbox.put((None, "offline", None))
                else:
                    result = local.sync(client)
                    note_server_features(local, client)
                    mailbox.put((client, result, None))
            except Exception as exc:
                # Do not display response bodies or credentials in errors.
                code = getattr(exc, "code", None)
                message = (
                    str(exc)
                    if isinstance(exc, ValueError)
                    else (code or "Falha de conexão. Tente novamente.")
                )
                mailbox.put(
                    (None if action == "logout" else transport, "error", message)
                )
            finally:
                values.pop("password", None)
                if local:
                    local.close()

        threading.Thread(target=work, daemon=True).start()
        app.root.after(100, poll)

    def poll():
        try:
            client, state, error = mailbox.get_nowait()
        except queue.Empty:
            app.root.after(100, poll)
            return
        busy[0] = False
        app.study_transport = client
        workspace.status = state
        # Guarda o token mais recente (o serviço gira o refresh token a cada uso).
        try:
            if client is not None and remember.get() and client.refresh_token:
                token_store.save(login_file, client.refresh_token)
            elif not remember.get():
                token_store.clear(login_file)
        except (OSError, ValueError):
            status.set("Não foi possível guardar o login neste computador.")
        status.set(error or LABELS[state])
        if not error:
            # Projection sees committed worker changes through its own connection.
            service_for(app.store)
            if client is not None:
                capture_profile_and_cycle(app.store, getattr(app, "plan", None))
            try:
                waiting = import_remote_sessions(app.store)
            except (ValueError, SyncError) as exc:
                status.set(str(exc))
                return
            if waiting:
                status.set(
                    f"Sincronizado. {len(waiting)} sessões aguardam associação a um assunto local."
                )

    def backup():
        path = filedialog.asksaveasfilename(
            parent=app.root,
            title="Exportar dados de sincronização",
            defaultextension=".sqlite3",
        )
        if path:
            try:
                export_workspace(app.store, path)
                status.set("Backup dos dados de sincronização salvo.")
            except (ValueError, OSError) as exc:
                status.set(str(exc))

    def share():
        drafts = [
            json.loads(r[0])
            for r in workspace.db.execute(
                "SELECT envelope FROM outbox WHERE status='local' AND shareable=1"
            )
        ]
        if not workspace.account_id:
            status.set("Entre na conta para escolher ações anteriores.")
            return
        chooser = tk.Toplevel(app.root)
        chooser.title("Escolher ações locais para compartilhar")
        ttk.Label(chooser, text="Selecione apenas as ações que deseja enviar.").pack(
            padx=16, pady=12
        )
        listing = tk.Listbox(
            chooser, selectmode="extended", width=75, height=15, exportselection=False
        )
        listing.pack(fill="both", expand=True, padx=16)
        for event in drafts:
            listing.insert("end", f"{event['kind']} · {event['entity_id']}")

        def selected():
            try:
                workspace.share_events(
                    [drafts[index]["id"] for index in listing.curselection()]
                )
            except SyncError as exc:
                status.set(LABELS.get(exc.code, "Estas ações devem permanecer locais."))
                return
            status.set(LABELS[workspace.status])
            chooser.destroy()

        ttk.Button(chooser, text="Compartilhar selecionadas", command=selected).pack(
            pady=12
        )

    def conflicts():
        if workspace.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='session_import_journal'"
        ).fetchone():
            recovery = workspace.db.execute(
                "SELECT id,body FROM session_import_journal ORDER BY rowid LIMIT 1"
            ).fetchone()
            if recovery:
                recover_counts(recovery)
                return
        events = workspace.conflicts()
        if not events:
            status.set("Nenhum conflito pendente.")
            return
        event = events[0]
        remote = workspace.entity(event["kind"], event["entity_id"])
        chooser = tk.Toplevel(app.root)
        chooser.title("Resolver alteração em conflito")
        ttk.Label(chooser, text="Compare as duas versões antes de escolher.").pack(
            padx=16, pady=12
        )
        text = tk.Text(chooser, width=85, height=18, wrap="word")
        text.pack(padx=16)
        text.insert(
            "end",
            "Sua alteração:\n"
            + json.dumps(event["payload"], ensure_ascii=False, indent=2)
            + "\n\nVersão remota:\n"
            + json.dumps(remote, ensure_ascii=False, indent=2),
        )
        text.configure(state="disabled")

        def keep_local():
            workspace.resolve_conflict(
                event["id"], event["payload"], remote["revision"] if remote else 0
            )
            status.set(LABELS["pending"])
            chooser.destroy()

        ttk.Button(
            chooser,
            text="Manter minha alteração e enviar novamente",
            command=keep_local,
        ).pack(pady=8)

        def keep_remote():
            with workspace.db:
                workspace.db.execute(
                    "UPDATE outbox SET status='resolved' WHERE id=?", (event["id"],)
                )
            status.set(
                "Versão remota mantida; alteração local preservada no histórico."
            )
            chooser.destroy()

        ttk.Button(chooser, text="Manter versão remota", command=keep_remote).pack(
            pady=(0, 12)
        )

    def recover_counts(recovery):
        sid, body = recovery
        row = app.store.one("SELECT * FROM sessions WHERE id=?", (sid,))
        if not row:
            status.set("A sessão ainda não foi integrada. Tente sincronizar novamente.")
            return
        pending = json.loads(body)
        chooser = tk.Toplevel(app.root)
        chooser.title("Conferir resultados da sessão")
        summary = " · ".join(
            f"{label}: {row[key]} (remotos: {pending['remote'][key]})"
            for key, label in (
                ("correct", "Acertos"),
                ("wrong", "Erros"),
                ("blank", "Em branco"),
            )
        )
        ttk.Label(
            chooser,
            text="A integração foi interrompida e os resultados locais mudaram.\n"
            "Confira a sessão no histórico. As quantidades devem incluir os resultados remotos.\n\n"
            + summary,
            wraplength=600,
        ).pack(padx=16, pady=16)

        def keep_counts():
            try:
                service_for(app.store).reconcile_import_counts(sid, consent=True)
            except ValueError as exc:
                status.set(str(exc))
                return
            status.set("Contagens locais preservadas. Tente sincronizar novamente.")
            chooser.destroy()

        ttk.Button(
            chooser,
            text="Confirmar que os totais locais estão corretos",
            command=keep_counts,
        ).pack(padx=16, pady=12)

    def associate():
        try:
            waiting = import_remote_sessions(app.store)
        except (ValueError, SyncError) as exc:
            status.set(str(exc))
            return
        if not waiting:
            status.set("Todas as sessões já estão associadas.")
            return
        event = waiting[0]
        chooser = tk.Toplevel(app.root)
        chooser.title("Associar sessão a um assunto")
        ttk.Label(
            chooser,
            text=f"Estudo de {event['payload']['day']} · {event['payload']['elapsed']} segundos líquidos",
        ).pack(padx=16, pady=12)
        ttk.Label(
            chooser,
            text="Escolha o assunto no plano atual para integrar esta sessão ao histórico.",
            wraplength=520,
        ).pack(padx=16)
        choices = {}
        for row in app.store.rows(
            "SELECT t.id,t.name,s.id subject_id,s.name subject FROM topics t JOIN subjects s ON s.id=t.subject_id WHERE s.plan_id=? ORDER BY s.name,t.rowid",
            (app.plan,),
        ):
            label = f"{row['subject']} › {row['name']}"
            while label in choices:
                label += " ·"
            choices[label] = row
        choice = tk.StringVar()
        ttk.Combobox(
            chooser,
            textvariable=choice,
            values=list(choices),
            state="readonly",
            width=70,
        ).pack(padx=16, pady=12)

        def apply_mapping():
            selected = choices.get(choice.get())
            if not selected:
                return
            p = event["payload"]
            key = "session_mapping:" + json.dumps(
                [p["plan_id"], p["subject_id"], p["topic_id"]]
            )
            mapping = dict(
                plan_id=app.plan,
                subject_id=selected["subject_id"],
                topic_id=selected["id"],
            )
            with workspace.db:
                workspace.db.execute(
                    "INSERT OR REPLACE INTO metadata VALUES(?,?)",
                    (key, json.dumps(mapping)),
                )
            try:
                remaining = import_remote_sessions(app.store)
            except (ValueError, SyncError) as exc:
                status.set(str(exc))
                return
            status.set(f"Sessão integrada. {len(remaining)} aguardam associação.")
            chooser.destroy()

        ttk.Button(
            chooser, text="Associar e integrar ao histórico", command=apply_mapping
        ).pack(pady=12)

    for label, callback in (
        ("Entrar e sincronizar", lambda: run("login")),
        ("Tentar novamente", lambda: run("sync")),
        ("Sair", lambda: run("logout")),
    ):
        ttk.Button(actions, text=label, command=callback).pack(side="left", padx=(0, 8))
    extra = ttk.Frame(panel)
    extra.pack(fill="x", pady=8)
    for label, callback in (
        ("Escolher ações anteriores", share),
        ("Resolver conflitos", conflicts),
        ("Associar sessões", associate),
        ("Exportar dados de sincronização", backup),
    ):
        ttk.Button(extra, text=label, command=callback).pack(side="left", padx=(0, 8))

    def auto_retry():
        app._study_auto_retry = None
        if getattr(app, "study_transport", None) is not None and not busy[0]:
            run("sync")
        app._study_auto_retry = app.root.after(60000, auto_retry)

    if getattr(app, "_study_auto_retry", None):
        app.root.after_cancel(app._study_auto_retry)
    app._study_auto_retry = app.root.after(60000, auto_retry)
    # Login lembrado: reconecta em segundo plano ao abrir a tela, sem pedir senha.
    if (
        getattr(app, "study_transport", None) is None
        and not busy[0]
        and login_file.exists()
    ):
        run("restore")


def background_sync(app, action="sync"):
    """Sincroniza sem a tela de conta: reconexão ao abrir (login lembrado) e
    nova tentativa periódica. Rede numa thread; Store/GUI só na thread principal."""
    busy = getattr(app, "study_network_busy", None)
    if busy is None:
        busy = [False]
        app.study_network_busy = busy
    if busy[0]:
        return
    workspace = workspace_for(app.store)
    login_file = app.store.path.with_name("study-sync-login.json")
    transport = getattr(app, "study_transport", None)
    stored = token_store.load(login_file) if action == "restore" else None
    if (
        action == "restore" and (not stored or not workspace.account_id or transport)
    ) or (action == "sync" and transport is None):
        return
    capture_new_sessions(app.store)
    capture_profile_and_cycle(app.store, getattr(app, "plan", None))
    url = workspace._meta("service_url") or SERVICE_URL
    key = workspace._meta("service_key") or PUBLIC_KEY
    path = app.store.path.with_name("study-sync.sqlite3")
    mailbox = queue.Queue()
    busy[0] = True

    def work():
        local = None
        try:
            local = SyncWorkspace(path)
            StudySync(local)
            client = transport
            if action == "restore":
                client = SupabaseTransport(url, key)
                client.refresh_token = stored
                client.refresh()
                if client.account_id != local.account_id:
                    raise SyncError("account_mismatch")
            result = local.sync(client)
            note_server_features(local, client)
            mailbox.put((client, result, None))
        except Exception as exc:
            mailbox.put((transport, "error", getattr(exc, "code", None) or "error"))
        finally:
            if local:
                local.close()

    def poll():
        try:
            client, state, error = mailbox.get_nowait()
        except queue.Empty:
            app.root.after(200, poll)
            return
        busy[0] = False
        workspace.status = state
        if error == "account_mismatch":
            token_store.clear(login_file)
        if client is None:
            return
        app.study_transport = client
        try:
            if login_file.exists() and client.refresh_token:
                token_store.save(login_file, client.refresh_token)
        except (OSError, ValueError):
            pass
        if not error:
            service_for(app.store)
            try:
                import_remote_sessions(app.store)
            except (ValueError, SyncError):
                pass

    threading.Thread(target=work, daemon=True).start()
    app.root.after(200, poll)


def schedule_background_sync(app):
    """Reconecta o login lembrado ao abrir e tenta de novo a cada minuto."""
    background_sync(app, "restore")

    def again():
        background_sync(app, "sync")
        app._study_background = app.root.after(60000, again)

    app._study_background = app.root.after(60000, again)
