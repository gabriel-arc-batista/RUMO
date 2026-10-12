"""Check actual Supabase CLI migration history against disposable local PG17."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from postgres_harness import PostgresHarness


def main():
    executable = shutil.which("supabase")
    if executable is None:
        raise RuntimeError("Existing Supabase CLI required; this test installs nothing")
    with (
        PostgresHarness("postgres:17.6", publish_db=True, initialize=False) as pg,
        tempfile.TemporaryDirectory(prefix="rumo-migrations-") as folder,
    ):
        pg.sql((pg.root / "tests/bootstrap.sql").read_text())
        exposed = (
            subprocess.run(
                ["docker", "port", pg.name, "5432/tcp"],
                check=True,
                capture_output=True,
                text=True,
            )
            .stdout.strip()
            .rsplit(":", 1)[1]
        )
        url = f"postgres://postgres:temporary-test-only@127.0.0.1:{exposed}/postgres?sslmode=disable"
        environment = os.environ.copy()
        environment.pop("SUPABASE_ACCESS_TOKEN", None)

        def cli(*args):
            result = subprocess.run(
                [executable, *args, "--workdir", folder, "--yes"],
                env=environment,
                capture_output=True,
                text=True,
            )
            if result.returncode:
                raise RuntimeError(
                    f"Local migration CLI failed: {result.stdout}\n{result.stderr}"
                )
            return result.stdout + result.stderr

        cli("init")
        migration_dir = Path(folder) / "supabase/migrations"
        migration_dir.mkdir(exist_ok=True)
        for migration in sorted((pg.root / "migrations").glob("*.sql")):
            shutil.copyfile(migration, migration_dir / migration.name)
        cli("db", "push", "--db-url", url, "--skip-vault")
        count = int(
            pg.sql(
                "SELECT count(*) FROM supabase_migrations.schema_migrations;"
            ).strip()
        )
        assert count == len(list(migration_dir.glob("*.sql"))), count
        repeated = cli("db", "push", "--db-url", url, "--skip-vault")
        assert "up to date" in repeated.lower(), repeated
        assert (
            int(
                pg.sql(
                    "SELECT count(*) FROM supabase_migrations.schema_migrations;"
                ).strip()
            )
            == count
        )
        pg.sql((pg.root / "tests/integration.sql").read_text())
        print(
            f"Supabase CLI applied {count} migrations on local PostgreSQL17; repeat skipped via real migration history; SQL assertions passed."
        )


if __name__ == "__main__":
    main()
