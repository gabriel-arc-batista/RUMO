"""App → site: aparência, nome, equipados e ciclo enviados pelo desktop real.

Base temporária do app e conta sintética na pilha local (npm run servico:up).
Imprime o e-mail criado na última linha para o passo no navegador.
"""

import json
import os
import sys
import tempfile
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core import Store  # noqa: E402
from desktop_sync import (  # noqa: E402
    capture_profile_and_cycle,
    note_server_features,
    workspace_for,
)
from learning import create_starter_cycle  # noqa: E402
from sync_client import SupabaseTransport  # noqa: E402

GATEWAY = "http://localhost:54321"
env = dict(
    line.split("=", 1)
    for line in (ROOT / "web" / ".env.servico.local").read_text().split()
    if "=" in line
)
anon = env["VITE_SUPABASE_ANON_KEY"]
email = f"desktop-{uuid.uuid4().hex[:10]}@example.invalid"
password = "senha-exemplo-123"
request = urllib.request.Request(
    GATEWAY + "/auth/v1/signup",
    data=json.dumps({"email": email, "password": password}).encode(),
    headers={"Content-Type": "application/json", "apikey": anon},
)
urllib.request.urlopen(request, timeout=10).read()

with tempfile.TemporaryDirectory() as folder:
    store = Store(Path(folder) / "study.sqlite3")
    plan = store.save("plans", dict(name="Plano de teste"))
    subject = store.save(
        "subjects", dict(plan_id=plan, name="Bancos de dados", color="#D6B467")
    )
    store.save("topics", dict(subject_id=subject, name="Normalização"))
    create_starter_cycle(store, plan, minutes=45)
    with store.db:
        store.db.execute(
            "INSERT OR REPLACE INTO preferences VALUES('character_look',?)",
            (json.dumps({"hair": "longo", "hair_color": "ruivo", "sex": "feminino"}),),
        )
        store.db.execute(
            "INSERT INTO rpg_characters VALUES(?,?) ON CONFLICT(plan_id) DO UPDATE SET name=excluded.name",
            (plan, "Exploradora"),
        )
    transport = SupabaseTransport("https://placeholder.invalid", anon)
    transport.url = GATEWAY  # só no teste: gateway local HTTP
    transport.login(email, password)
    workspace = workspace_for(store)
    workspace.bind_account(transport.account_id, consent=True)
    capture_profile_and_cycle(store, plan)
    assert workspace.pending() == [], "sem confirmar a 009 o app não envia perfil/ciclo"
    workspace.sync(transport)
    assert note_server_features(workspace, transport), "serviço local deveria ter a 009"
    capture_profile_and_cycle(store, plan)
    print("sync:", workspace.sync(transport))
    kinds = sorted({e["kind"] for e in workspace.events()})
    print("eventos no serviço:", kinds)
    assert {"profile.character", "cycle.snapshot"} <= set(kinds), kinds
    capture_profile_and_cycle(store, plan)
    assert workspace.pending() == [], "snapshot sem mudança não deve gerar evento"
    workspace.close()
    store.close()
print(email)
