"""Idempotent, additive expansion of the historical BACEN study plan."""

import json


def expand_bacen(store, plan, outline, version=1):
    key = f"bacen_guide_v{version}_" + plan
    if store.pref(key, False):
        return 0
    # Save the original completion state and links before changing the hierarchy.
    store.auto_backup(force=True)
    added = 0
    provenance = set(store.pref("bacen_guide_ids", []))
    evidence = store.pref("bacen_topic_sources", {})
    with store.db:
        for entry in outline:
            parent = store.one(
                """SELECT t.* FROM topics t JOIN subjects s ON s.id=t.subject_id
                WHERE s.plan_id=? AND s.name=? AND t.name=? AND s.archived=0 AND t.archived=0""",
                (plan, entry["materia"], entry["official"].strip()),
            )
            if not parent:
                continue  # Respect edits, archival and custom subjects.
            for name in entry["items"]:
                existing = store.one(
                    "SELECT id FROM topics WHERE parent_id=? AND name=?",
                    (parent["id"], name),
                )
                if existing:
                    tid = existing[
                        "id"
                    ]  # Never revive archived items or reset completion.
                else:
                    tid = store.put(
                        "topics",
                        dict(
                            subject_id=parent["subject_id"],
                            parent_id=parent["id"],
                            name=name,
                            done=parent["done"],
                        ),
                    )
                    provenance.add(tid)
                    added += 1
                if name in entry.get("evidence", {}):
                    evidence[tid] = entry["evidence"][name]
        for pref, value in [
            (key, True),
            ("bacen_guide_ids", sorted(provenance)),
            ("bacen_topic_sources", evidence),
        ]:
            store.db.execute(
                "INSERT OR REPLACE INTO preferences VALUES(?,?)",
                (pref, json.dumps(value)),
            )
    return added
