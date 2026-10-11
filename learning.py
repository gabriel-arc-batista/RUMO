"""Pedagogical display order. Official text, IDs and study history stay intact."""

import json
import re
import unicodedata


def norm(text):
    return "".join(
        c
        for c in unicodedata.normalize("NFD", text.casefold())
        if not unicodedata.combining(c)
    )


SUBJECTS = [
    "Língua Portuguesa",
    "Noções De Lógica E Estatística",
    "Engenharia De Software",
    "Bancos De Dados",
    "Infraestrutura Em Ti",
    "Segurança Da Informação",
    "Ciência De Dados",
    "Gestão Em Ti",
    "Direito Administrativo",
    "Fundamentos De Macroeconomia E Microeconomia",
    "Microeconomia",
    "Macroeconomia",
    "Estatística E Econometria",
    "Finanças",
    "Contabilidade De Instituições Financeiras Padrão Cosif (Plano Contábil Das Instituições Do Sistema Financeiro Nacional)",
    "Atualidades",
]
ROOTS = {
    "Noções De Lógica E Estatística": [1, 10, 2],
    "Direito Administrativo": [1, 3, 2, 4, 5, 7, 8, 9, 6, 10, 11],
    "Microeconomia": [1, 5, 2, 3, 4, 6, 7],
    "Macroeconomia": [1, 8, 6, 2, 4, 5, 7, 3],
    "Estatística E Econometria": [1, 2, 3, 4, 7, 5, 6],
    "Finanças": [1, 6, 5, 8, 3, 4, 2, 7],
    "Engenharia De Software": [12, 11, 4, 10, 6, 1, 5, 8, 9, 7, 13, 2, 3, 14],
    "Bancos De Dados": [2, 1, 3, 4],
    "Infraestrutura Em Ti": [9, 10, 5, 3, 8, 7, 1, 11, 2, 4, 6],
    "Segurança Da Informação": [2, 9, 1, 5, 3, 6, 4, 7, 8, 10],
    "Ciência De Dados": [5, 4, 6, 1, 8, 2, 3, 7, 9, 10],
    "Gestão Em Ti": [1, 2, 4, 3],
    "Língua Portuguesa": [3, 5, 4, 1, 2, 6],
}
PROGRAMMING = {
    "python": [
        "tipos",
        "estruturas sequenciais",
        "condicionais",
        "listas",
        "len()",
        "funcoes",
        "classes",
        "excecoes",
        "modulos",
        "iteradores",
    ],
    "java": [
        "tipos",
        "estruturas sequenciais",
        "condicionais",
        "lacos",
        "arrays",
        "classes",
        "metodos",
        "rastreamento",
        "encapsulamento",
        "heranca",
        "interfaces",
        "excecoes",
        "generics",
        "lambdas",
        "pacotes",
        "interpretacao",
    ],
}


def subject_key(name):
    ranks = {norm(s): i for i, s in enumerate(SUBJECTS)}
    return ranks.get(norm(name), len(ranks)), norm(name)


def ordered(topics, subject_names):
    ranks = {
        norm(name): {code: i for i, code in enumerate(codes)}
        for name, codes in ROOTS.items()
    }

    def key(pair):
        index, t = pair
        name = norm(t["name"])
        subject = subject_names.get(t["subject_id"], "")
        if name.startswith(("microeconomia", "macroeconomia")):
            number = int(re.search(r"\d+", name)[0])
            rank = 0 if name.startswith("microeconomia") else 1
            return subject_key(subject), (
                0,
                rank,
                (0 if number == 2 else 1) if rank == 0 else number,
                index,
            )
        official = re.match(r"^(\d+)(?:\.(\d+))?", name)
        if official:
            code = int(official[1])
            sub = int(official[2] or 0)
            return subject_key(subject), (
                0,
                ranks.get(norm(subject), {}).get(code, code),
                sub,
                index,
            )
        language = (
            0 if name.startswith("python:") else 1 if name.startswith("java:") else -1
        )
        patterns = (
            PROGRAMMING.get("python" if language == 0 else "java", [])
            if language >= 0
            else []
        )
        content = name.split(":", 1)[-1].strip()
        phase = next((i for i, p in enumerate(patterns) if content.startswith(p)), 99)
        return subject_key(subject), (1, language, phase, index)

    return [t for _, t in sorted(enumerate(topics), key=key)]


def next_topic(store, subject):
    rows = store.rows(
        "SELECT * FROM topics WHERE subject_id=? AND archived=0 ORDER BY rowid",
        (subject,),
    )
    parent_ids = {r["parent_id"] for r in rows}
    names = {
        subject: store.one("SELECT name FROM subjects WHERE id=?", (subject,))["name"]
    }
    leaves = [r for r in ordered(rows, names) if r["id"] not in parent_ids]
    # Respect parent prerequisites: iterate the actual hierarchy, not a flat list.
    children = {}
    for row in ordered(rows, names):
        children.setdefault(row["parent_id"], []).append(row)
    result = []

    def visit(row):
        if row["id"] in parent_ids:
            for child in children.get(row["id"], []):
                visit(child)
        else:
            result.append(row)

    ids = {r["id"] for r in rows}
    for row in ordered(rows, names):
        if row["parent_id"] not in ids:
            visit(row)
    return next((r for r in result if not r["done"]), result[0] if result else None)


def create_starter_cycle(store, plan, minutes=25):
    if not 1 <= minutes <= 180:
        raise ValueError("Use blocos de 1 a 180 minutos.")
    key = "starter_cycle_" + plan
    existing = store.pref(key)
    if existing and store.one(
        "SELECT id FROM cycles WHERE id=? AND plan_id=?", (existing, plan)
    ):
        with store.db:
            store.db.execute("UPDATE cycles SET active=0 WHERE plan_id=?", (plan,))
            store.db.execute("UPDATE cycles SET active=1 WHERE id=?", (existing,))
        return existing
    subjects = sorted(
        store.rows("SELECT * FROM subjects WHERE plan_id=? AND archived=0", (plan,)),
        key=lambda r: subject_key(r["name"]),
    )
    if not subjects:
        raise ValueError("Cadastre matérias para montar o ciclo.")
    with store.db:
        store.db.execute("UPDATE cycles SET active=0 WHERE plan_id=?", (plan,))
        cycle = store.put(
            "cycles", {"plan_id": plan, "name": "BACEN • Fundamentos ao avançado"}
        )
        for index, subject in enumerate(subjects):
            store.put(
                "blocks",
                {
                    "cycle_id": cycle,
                    "subject_id": subject["id"],
                    "topic_id": None,
                    "target": minutes * 60,
                    "category": "Teoria",
                    "sort": index,
                },
            )
        store.db.execute(
            "INSERT OR REPLACE INTO preferences VALUES(?,?)", (key, json.dumps(cycle))
        )
    return cycle
