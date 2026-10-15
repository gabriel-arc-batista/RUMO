"""Optional learning graph, stored in existing backup-compatible preferences.

Edges guide recommendations; they never authorize or prohibit opening a topic.
Theory completion remains the canonical topics.done value, separate from practice.
"""

import json
from pathlib import Path

KINDS = {"essential", "recommended", "parallel"}


def validate_graph(edges, nodes=None):
    if not isinstance(edges, list) or len(edges) > 10000:
        raise ValueError("Trilha inválida ou grande demais.")
    adjacency, seen = {}, set()
    for edge in edges:
        if not isinstance(edge, dict) or set(edge) != {"before", "after", "kind"}:
            raise ValueError("Relação pedagógica inválida.")
        a, b, kind = edge["before"], edge["after"], edge["kind"]
        if any(not isinstance(v, str) or not v or len(v) > 200 for v in (a, b, kind)):
            raise ValueError("Identificador pedagógico inválido.")
        if a == b or kind not in KINDS or (a, b) in seen:
            raise ValueError("Relação repetida ou inválida.")
        if nodes is not None and (a not in nodes or b not in nodes):
            raise ValueError("Assunto ausente ou de outro concurso.")
        seen.add((a, b))
        if kind != "parallel":
            adjacency.setdefault(a, []).append(b)
    # Iterative Kahn traversal: arbitrarily deep graphs cannot exhaust recursion.
    degrees = {}
    for a, children in adjacency.items():
        degrees.setdefault(a, 0)
        for b in children:
            degrees[b] = degrees.get(b, 0) + 1
    ready = [a for a, degree in degrees.items() if not degree]
    visited = 0
    while ready:
        a = ready.pop()
        visited += 1
        for b in adjacency.get(a, []):
            degrees[b] -= 1
            if not degrees[b]:
                ready.append(b)
    if visited != len(degrees):
        raise ValueError("A trilha não pode conter dependências circulares.")


def plan_topics(store, plan):
    return store.rows(
        "SELECT t.* FROM topics t JOIN subjects s ON s.id=t.subject_id "
        "WHERE s.plan_id=? AND s.archived=0 AND t.archived=0 ORDER BY t.rowid",
        (plan,),
    )


def save_graph(store, plan, edges):
    nodes = {r["id"] for r in plan_topics(store, plan)}
    validate_graph(edges, nodes)
    store.set_pref("learning_graph_" + plan, edges)


def graph(store, plan):
    rows = plan_topics(store, plan)
    nodes = {r["id"] for r in rows}
    explicit = store.pref("learning_graph_" + plan, None)
    if explicit is not None:
        validate_graph(explicit)
        # Archival must not resurrect a topic or prevent studying its successors.
        return [e for e in explicit if e["before"] in nodes and e["after"] in nodes]
    subjects = {
        r["id"]: r["name"]
        for r in store.rows("SELECT id,name FROM subjects WHERE plan_id=?", (plan,))
    }
    by_name = {}
    for row in rows:
        by_name.setdefault(
            (subjects[row["subject_id"]], row["name"].strip()), []
        ).append(row["id"])
    data = json.loads(
        (Path(__file__).parent / "assets" / "bacen-pedagogy.json").read_text(
            encoding="utf-8"
        )
    )
    edges = []
    for entry in data["relations"]:
        a, b = (by_name.get(tuple(entry[k]), []) for k in ("before", "after"))
        # Exact unique matches only: personal plans/renames are never guessed.
        if len(a) == len(b) == 1:
            edges.append(dict(before=a[0], after=b[0], kind=entry["kind"]))
    validate_graph(edges, nodes)
    return edges


def recommendations(store, subject):
    from learning import ordered

    owner = store.one(
        "SELECT plan_id FROM subjects WHERE id=? AND archived=0", (subject,)
    )
    if not owner:
        return []
    rows = plan_topics(store, owner["plan_id"])
    nodes = {r["id"]: r for r in rows}
    children = {}
    for row in rows:
        children.setdefault(row["parent_id"], []).append(row["id"])
    edges = graph(store, owner["plan_id"])
    names = {r["id"]: r["name"] for r in store.rows("SELECT id,name FROM subjects")}

    def complete(tid):
        pending = [tid]
        while pending:
            current = pending.pop()
            if current in children:
                pending.extend(children[current])
            elif not nodes[current]["done"]:
                return False
        return True

    result = []
    for row in ordered([r for r in rows if r["subject_id"] == subject], names):
        if row["id"] in children or row["done"]:
            continue
        ancestors, current = {row["id"]}, row
        while current["parent_id"] in nodes:
            current = nodes[current["parent_id"]]
            ancestors.add(current["id"])
        relevant = [
            e for e in edges if e["after"] in ancestors and e["kind"] != "parallel"
        ]
        missing = [
            dict(nodes[e["before"]], kind=e["kind"])
            for e in relevant
            if not complete(e["before"])
        ]
        satisfied = [
            nodes[e["before"]]["name"] for e in relevant if complete(e["before"])
        ]
        reason = (
            "Conhecimentos anteriores concluídos: " + "; ".join(satisfied)
            if satisfied
            else "Próximo subassunto pendente na ordem pedagógica."
        )
        if missing:
            reason = (
                "Antes, recomenda-se estudar: "
                + "; ".join(r["name"] for r in missing)
                + ". Você pode continuar livremente."
            )
        result.append(dict(topic=row, missing=missing, reason=reason))
    # Essential precedences influence priority, never block access. Stable ordering
    # preserves the existing pedagogical display for unrelated/parallel branches.
    result.sort(
        key=lambda r: (
            sum(e["kind"] == "essential" for e in r["missing"]),
            len(r["missing"]),
        )
    )
    return result
