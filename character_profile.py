"""Atomic appearance/name save using the existing local profile tables."""

import json

import appearance as A
from rpg import text


def save_character(store, plan, look, name):
    name = text(name, "Nome do personagem", True, 60)
    if not A.validate_look(look):
        raise ValueError("Aparência inválida.")
    if not store.one("SELECT id FROM plans WHERE id=?", (plan,)):
        raise ValueError("Selecione um plano para salvar seu personagem.")
    with store.db:
        store.db.execute(
            "INSERT INTO rpg_characters VALUES(?,?) ON CONFLICT(plan_id) DO UPDATE SET name=excluded.name",
            (plan, name),
        )
        store.db.execute(
            "INSERT OR REPLACE INTO preferences VALUES(?,?)",
            (A.PREFERENCE, json.dumps(A.normalize(look), ensure_ascii=False)),
        )
