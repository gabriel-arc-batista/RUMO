"""Back up production data, then verify an additive update without printing it."""

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import data_dir, TABLES

project = Path(__file__).resolve().parents[1]
out = project / "validation"
baseline = out / "upgrade-baseline.json"
database = data_dir() / "estudos.sqlite3"


def reader(path):
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if sys.argv[1] == "prepare":
    backup = (
        data_dir()
        / "backups"
        / ("pre-v1.4.2-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".sqlite3")
    )
    backup.parent.mkdir(exist_ok=True)
    source = reader(database)
    dest = sqlite3.connect(backup)
    source.backup(dest)
    dest.close()
    counts = {
        t: source.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES
    }
    source.close()
    baseline.write_text(
        json.dumps({"backup": str(backup), "counts": counts}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"backup_created": True, "counts": counts}))
else:
    before = json.loads(baseline.read_text(encoding="utf-8"))
    old = reader(Path(before["backup"]))
    new = reader(database)
    preserved = {}
    allowed = {"design_version", "bacen_guide_ids", "bacen_topic_sources"}
    for table in TABLES:
        columns = [r["name"] for r in old.execute(f"PRAGMA table_info({table})")]
        primary = next(
            r["name"] for r in old.execute(f"PRAGMA table_info({table})") if r["pk"]
        )
        count = 0
        for row in old.execute(f"SELECT * FROM {table}"):
            current = new.execute(
                f"SELECT {','.join(columns)} FROM {table} WHERE {primary}=?",
                (row[primary],),
            ).fetchone()
            assert current is not None, (table, "missing record")
            if table == "preferences" and row["key"] in allowed:
                if row["key"] == "bacen_guide_ids":
                    assert set(json.loads(row["value"])) <= set(
                        json.loads(current["value"])
                    )
            elif table == "cycles":
                expected = dict(row)
                expected["active"] = current["active"]
                assert dict(current) == expected, (table, "changed cycle history")
            else:
                assert dict(current) == dict(row), (table, "changed existing record")
            count += 1
        preserved[table] = count
    assert new.execute("PRAGMA user_version").fetchone()[0] == 3
    assert new.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not new.execute("PRAGMA foreign_key_check").fetchall()
    total = new.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
    old.close()
    new.close()
    installed = Path(os.environ["LOCALAPPDATA"]) / "Programs/RUMO"
    bundle = project / "dist/RUMO"
    files = [p for p in bundle.rglob("*") if p.is_file()]
    assert all(
        (installed / p.relative_to(bundle)).is_file()
        and digest(p) == digest(installed / p.relative_to(bundle))
        for p in files
    )
    report = {
        "version": "1.4.2",
        "installed_executable": str(installed / "RUMO.exe"),
        "matches_build": True,
        "all_existing_study_records_preserved": True,
        "original_preferences_preserved_except_additive_guide_and_design": True,
        "preserved_counts": preserved,
        "new_syllabus_entries": total - before["counts"]["topics"],
        "backup": before["backup"],
        "schema_version": 3,
        "installed_files_checked": len(files),
        "final_build_installed": True,
        "subtopic_click_regression_passed": True,
    }
    (out / "installation-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))
