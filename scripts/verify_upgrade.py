"""Verify additive upgrades. prepare/verify require an explicitly authorized install.

self-test uses synthetic temporary databases only and is suitable for CI.
"""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import SCHEMA, TABLES, Store, data_dir
from training_schema import TRAINING_SCHEMA, TRAINING_TABLES

PROJECT = Path(__file__).resolve().parents[1]
EXPECTED_SCHEMA = 6


def release_version():
    text = (PROJECT / "scripts/installer.iss").read_text(encoding="utf-8")
    match = re.search(r"^AppVersion=(\d+\.\d+\.\d+)$", text, re.MULTILINE)
    if not match:
        raise ValueError("Installer has no semantic release version")
    return match.group(1)


def reader(path):
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA trusted_schema=OFF")
    connection.execute("PRAGMA query_only=ON")
    return connection


def table_counts(connection):
    existing = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    return {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in TABLES
        if table in existing
    }


def preserved_records(old, new, counts):
    preserved = {}
    allowed = {"design_version", "bacen_guide_ids", "bacen_topic_sources"}
    for table in counts:
        assert table in TABLES, "Unknown baseline table"
        info = list(old.execute(f"PRAGMA table_info({table})"))
        columns = [row["name"] for row in info]
        primary = [
            row["name"] for row in sorted(info, key=lambda row: row["pk"]) if row["pk"]
        ]
        assert primary, (table, "missing primary key")
        where = " AND ".join(column + "=?" for column in primary)
        count = 0
        for row in old.execute(f"SELECT * FROM {table}"):
            current = new.execute(
                f"SELECT {','.join(columns)} FROM {table} WHERE {where}",
                tuple(row[column] for column in primary),
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
    assert new.execute("PRAGMA user_version").fetchone()[0] == EXPECTED_SCHEMA
    assert new.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not new.execute("PRAGMA foreign_key_check").fetchall()
    return preserved


def self_test():
    with tempfile.TemporaryDirectory(prefix="rumo-upgrade-") as folder:
        root = Path(folder)
        legacy = root / "legacy.sqlite3"
        connection = sqlite3.connect(legacy)
        assert SCHEMA.endswith(TRAINING_SCHEMA)
        connection.executescript(SCHEMA[: -len(TRAINING_SCHEMA)])
        connection.execute("PRAGMA user_version=5")
        connection.execute(
            "INSERT INTO plans(id,name) VALUES('plan','Plano sintético')"
        )
        connection.execute(
            "INSERT INTO subjects(id,plan_id,name,color) VALUES('subject','plan','Matéria','#123456')"
        )
        connection.execute(
            "INSERT INTO topics(id,subject_id,name,notes,done) VALUES('topic','subject','Assunto','Observação sintética',1)"
        )
        connection.execute(
            "INSERT INTO sessions(id,plan_id,subject_id,topic_id,day,category,target,elapsed,correct,wrong,notes) VALUES('session','plan','subject','topic','2026-10-11','Questões',120,120,3,2,'Histórico sintético')"
        )
        connection.execute(
            "INSERT INTO reviews(id,topic_id,origin_id,due,interval) VALUES('review','topic','session','2026-10-12',1)"
        )
        connection.commit()
        before = root / "before.sqlite3"
        dest = sqlite3.connect(before)
        connection.backup(dest)
        dest.close()
        connection.close()
        baseline = reader(before)
        try:
            assert not set(table_counts(baseline)) & set(TRAINING_TABLES)
        finally:
            baseline.close()
        store = Store(legacy)
        store.close()
        old, new = reader(before), reader(legacy)
        try:
            preserved_records(old, new, table_counts(old))
        finally:
            old.close()
            new.close()
    print("Synthetic v5→v6 upgrade preserves existing records.")


def prepare(database, baseline):
    backup = (
        database.parent
        / "backups"
        / (
            f"pre-v{release_version()}-"
            + datetime.now().strftime("%Y%m%d-%H%M%S%f")
            + ".sqlite3"
        )
    )
    backup.parent.mkdir(exist_ok=True)
    source = reader(database)
    dest = sqlite3.connect(backup)
    try:
        source.backup(dest)
        counts = table_counts(source)
    finally:
        dest.close()
        source.close()
    baseline.write_text(
        json.dumps({"backup": str(backup), "counts": counts}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"backup_created": True, "counts": counts}))


def verify(database, baseline):
    before = json.loads(baseline.read_text(encoding="utf-8"))
    old, new = reader(Path(before["backup"])), reader(database)
    try:
        preserved = preserved_records(old, new, before["counts"])
    finally:
        old.close()
        new.close()
    installed = Path(os.environ["LOCALAPPDATA"]) / "Programs/RUMO"
    bundle = PROJECT / "dist/RUMO"
    files = [path for path in bundle.rglob("*") if path.is_file()]
    assert files, "Build missing"
    for path in files:
        target = installed / path.relative_to(bundle)
        assert (
            target.is_file()
            and hashlib.sha256(path.read_bytes()).digest()
            == hashlib.sha256(target.read_bytes()).digest()
        )
    report = dict(
        version=release_version(),
        matches_build=True,
        all_existing_study_records_preserved=True,
        preserved_counts=preserved,
        schema_version=EXPECTED_SCHEMA,
        installed_files_checked=len(files),
        final_build_installed=True,
    )
    (baseline.parent / "installation-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "verify", "self-test"))
    args = parser.parse_args()
    if args.mode == "self-test":
        self_test()
        return
    out = PROJECT / "validation"
    out.mkdir(exist_ok=True)
    database = data_dir() / "estudos.sqlite3"
    {"prepare": prepare, "verify": verify}[args.mode](
        database, out / "upgrade-baseline.json"
    )


if __name__ == "__main__":
    main()
