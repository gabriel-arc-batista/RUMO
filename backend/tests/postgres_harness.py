"""Disposable PostgreSQL RPC adapter for tests; never connects to a hosted database."""

import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path


class PostgresHarness:
    def __init__(
        self,
        image="postgres:16-alpine",
        publish_http=False,
        publish_auth=False,
        publish_db=False,
        initialize=True,
    ):
        self.image = image
        self.publish_http = publish_http
        self.publish_auth = publish_auth
        self.publish_db = publish_db
        self.initialize = initialize
        self.name = f"rumo-postgres-flow-{uuid.uuid4().hex}"
        self.root = Path(__file__).resolve().parents[1]

    def __enter__(self):
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                self.name,
                "-e",
                "POSTGRES_PASSWORD=temporary-test-only",
                *(["-p", "127.0.0.1::3000"] if self.publish_http else []),
                *(["-p", "127.0.0.1::9999"] if self.publish_auth else []),
                *(["-p", "127.0.0.1::5432"] if self.publish_db else []),
                self.image,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        try:
            for _ in range(60):
                ready = subprocess.run(
                    [
                        "docker",
                        "exec",
                        self.name,
                        "pg_isready",
                        "-h",
                        "127.0.0.1",
                        "-U",
                        "postgres",
                    ],
                    capture_output=True,
                )
                if ready.returncode == 0:
                    break
                time.sleep(1)
            else:
                raise RuntimeError("PostgreSQL test startup timed out")
            if self.initialize:
                self.sql((self.root / "tests/bootstrap.sql").read_text())
                self.apply_migrations()
                self.apply_migrations()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def apply_migrations(self):
        """Test a checksum ledger analogous to the hosted migration history."""
        self.sql(
            "CREATE SCHEMA IF NOT EXISTS test_migrations; CREATE TABLE IF NOT EXISTS test_migrations.applied(name text PRIMARY KEY, sha256 text NOT NULL);"
        )
        for migration in sorted((self.root / "migrations").glob("*.sql")):
            source = migration.read_text()
            digest = hashlib.sha256(source.encode()).hexdigest()
            previous = self.sql(
                f"SELECT sha256 FROM test_migrations.applied WHERE name='{migration.name}';"
            ).strip()
            if previous:
                if previous != digest:
                    raise RuntimeError(f"Applied migration changed: {migration.name}")
                continue
            position = source.lower().rfind("commit;")
            if position < 0:
                raise RuntimeError("Migration must be atomic")
            statement = f"INSERT INTO test_migrations.applied VALUES('{migration.name}','{digest}');\n"
            self.sql(source[:position] + statement + source[position:])

    def __exit__(self, *_):
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)

    def sql(self, statement):
        result = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                self.name,
                "psql",
                "-h",
                "127.0.0.1",
                "-U",
                "postgres",
                "-At",
                "-v",
                "ON_ERROR_STOP=1",
            ],
            input=statement,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def rpc(self, user_id, function, arguments):
        # Only permit the known RPCs; all values use unique dollar-quoted literals.
        user_id = str(uuid.UUID(str(user_id)))
        if function == "push_events":
            tag = f"$payload_{uuid.uuid4().hex}$"
            args = f"{tag}{json.dumps(arguments['events'])}{tag}::jsonb"
        elif function == "pull_events":
            args = f"{int(arguments.get('after_sequence', 0))},{int(arguments.get('batch_size', 200))}"
        elif function in ("study_summary", "progress_summary"):
            args = ""
        else:
            raise ValueError("Unknown RPC")
        output = self.sql(
            "SET ROLE authenticated;\n"
            f"SET request.jwt.claim.sub='{user_id}';\n"
            f"SELECT public.{function}({args});\n"
        )
        return json.loads(output.strip().splitlines()[-1])
