"""Desktop <-> site contra a pilha local descartável; nenhum dado pessoal."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from sync_client import SupabaseTransport, SyncWorkspace
from study_sync import StudySync


def main():
    with (ROOT / "web" / ".env.servico.local").open(encoding="utf-8") as stream:
        settings = dict(line.strip().split("=", 1) for line in stream if "=" in line)
    assert settings["VITE_SUPABASE_URL"] == "http://localhost:54321"
    email = subprocess.run(
        [
            "docker",
            "exec",
            "rumo-webtest-db",
            "psql",
            "-U",
            "postgres",
            "-At",
            "-c",
            "select email from auth.users where email like 'extras-%' order by created_at desc limit 1",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert email, "Execute e2e/extras.mjs primeiro para criar o usuário sintético."
    transport = SupabaseTransport(
        "https://placeholder.invalid", settings["VITE_SUPABASE_ANON_KEY"]
    )
    transport.url = settings["VITE_SUPABASE_URL"]  # Só neste teste, loopback acima.
    transport.login(email, "senha-exemplo-123")
    with tempfile.TemporaryDirectory(prefix="rumo-web-bridge-") as folder:
        workspace = SyncWorkspace(Path(folder) / "study-sync.sqlite3")
        try:
            workspace.bind_account(transport.account_id, consent=True)
            study = StudySync(workspace)
            assert workspace.sync(transport) == "synced"
            reading = study.reading("exemplo.aula.juncoes", "1.0.0", 12)
            assert (
                1 not in reading["read_pages"]
            ), "A escolha explícita de B deve desmarcar a página 1."
            bookmark = workspace.entity(
                "favorite.set",
                "bookmark:exemplo.aula.juncoes:1.0.0:page:3:1.0.0:favorite",
            )
            assert bookmark and bookmark["payload"]["favorite"] is True
            sessions = [
                event
                for event in workspace.events()
                if event["kind"] == "study.session"
            ]
            session = next(
                event for event in sessions if event["payload"]["elapsed"] == 125
            )
            assert session["payload"]["category"] == "Questões"
            assert session["result"]["xp"] == 2
            assert study.projection.session_counts(session["entity_id"])["correct"] == 1
            notes = [
                event["payload"]
                for event in workspace.events()
                if event["kind"] == "note.save"
            ]
            assert any(
                note.get("question_id") == "exemplo.q.recorrencia"
                and note["text"] == "Teorema mestre, caso 2."
                for note in notes
            )
            study.read_page("exemplo.aula.juncoes", "1.0.0", 2, 12, True)
            study.review_card("exemplo.c.inner", "1.0.0", 3, str(uuid.uuid4()))
            assert workspace.sync(transport) == "synced"
            assert 2 in study.reading("exemplo.aula.juncoes", "1.0.0", 12)["read_pages"]
            assert study.projection.card_schedule("exemplo.c.inner", "1.0.0")
            print(
                "ok desktop recebeu leitura, marcador, sessão, XP, tentativa e nota; devolveu página e revisão"
            )
            print(email)
        finally:
            workspace.close()
            transport.logout()


if __name__ == "__main__":
    main()
