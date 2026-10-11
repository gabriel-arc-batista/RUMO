"""Discover a prior study database by schema and copy it without deleting data."""

import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

from backups import validate_backup


@contextmanager
def migration_lock(folder):
    lock = open(folder / "instance.lock", "a+b")
    try:
        if os.name == "nt":
            import msvcrt

            lock.seek(0)
            if not lock.read(1):
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        raise ValueError("Feche a instalação anterior antes de atualizar os dados.")
    try:
        yield
    finally:
        lock.close()


def migrate_existing_data(base, target, schema, tables):
    """Only one validated sibling database can be imported; never overwrite one."""
    base, target = Path(base), Path(target)
    destination = target / "estudos.sqlite3"
    if destination.exists() or not base.is_dir():
        return
    candidates = []
    for folder in base.iterdir():
        if folder == target or folder.is_symlink() or not folder.is_dir():
            continue
        source = folder / "estudos.sqlite3"
        if source.is_symlink() or not source.is_file():
            continue
        try:
            reader = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
            try:
                objects = {
                    row[0]
                    for row in reader.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
            finally:
                reader.close()
            if not set(tables) <= objects:
                continue
            validate_backup(source, schema, tables)
        except (ValueError, OSError, sqlite3.Error) as error:
            raise ValueError(
                "A base de estudos anterior não passou na validação. "
                "Nenhuma base foi substituída. Restaure um backup válido "
                "ou defina RUMO_DATA antes de continuar."
            ) from error
        candidates.append(source)
    if len(candidates) > 1:
        raise ValueError(
            "Há mais de uma base de estudos anterior. Defina RUMO_DATA para "
            "a pasta desejada ou restaure o backup escolhido antes de continuar."
        )
    if not candidates:
        return
    source = candidates[0]
    target.mkdir(parents=True, exist_ok=True)
    with migration_lock(source.parent):
        validate_backup(source, schema, tables)
        descriptor, name = tempfile.mkstemp(
            prefix="migration-", suffix=".sqlite3", dir=target
        )
        os.close(descriptor)
        temporary = Path(name)
        try:
            reader = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
            writer = sqlite3.connect(temporary)
            try:
                reader.backup(writer)
                row = writer.execute(
                    "SELECT value FROM preferences WHERE key='backup_folder'"
                ).fetchone()
                if row:
                    previous = Path(json.loads(row[0]))
                    if previous.is_relative_to(source.parent):
                        replacement = target / previous.relative_to(source.parent)
                        replacement.mkdir(parents=True, exist_ok=True)
                        with writer:
                            writer.execute(
                                "UPDATE preferences SET value=? WHERE key='backup_folder'",
                                (json.dumps(str(replacement)),),
                            )
            finally:
                writer.close()
                reader.close()
            validate_backup(temporary, schema, tables)
            # Hard-link publication fails safely if another process created the DB.
            try:
                os.link(temporary, destination)
            except FileExistsError:
                pass
        finally:
            temporary.unlink(missing_ok=True)
