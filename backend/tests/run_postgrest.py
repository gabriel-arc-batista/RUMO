"""Actual isolated PostgreSQL 17/PostgREST HTTP checks; synthetic JWT/Auth only."""

import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import hmac
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid

from postgres_harness import PostgresHarness

JWT_SECRET = "rumo-disposable-postgrest-test-secret-32-bytes"


def jwt(user):
    def encode(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")

    body = ".".join(
        (
            encode({"alg": "HS256", "typ": "JWT"}),
            encode(
                {"sub": user, "role": "authenticated", "exp": int(time.time()) + 600}
            ),
        )
    )
    signature = (
        base64.urlsafe_b64encode(
            hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest()
        )
        .decode()
        .rstrip("=")
    )
    return f"{body}.{signature}"


def main():
    with PostgresHarness("postgres:17.6", publish_http=True) as pg:
        users = [str(uuid.uuid4()), str(uuid.uuid4())]
        pg.sql(
            "INSERT INTO auth.users VALUES "
            + ",".join(f"('{user}')" for user in users)
            + ";"
        )
        pg.sql(
            "INSERT INTO public.rumo_lessons(id,version,pages,title,example) VALUES('example.http','1.0.0',2,'EXEMPLO HTTP',true);"
        )
        pg.sql(
            "INSERT INTO rumo_private.questions(id,version,prompt,options,answer,example) VALUES('example.http','1.0.0','EXEMPLO HTTP','{\"a\":\"A\",\"b\":\"B\"}','a',true);"
        )
        pg.sql((pg.root / "tests/integration.sql").read_text())
        port = (
            subprocess.run(
                ["docker", "port", pg.name, "3000/tcp"],
                check=True,
                capture_output=True,
                text=True,
            )
            .stdout.strip()
            .rsplit(":", 1)[1]
        )
        rest = f"rumo-postgrest-{uuid.uuid4().hex}"
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                rest,
                "--network",
                f"container:{pg.name}",
                "-e",
                "PGRST_DB_URI=postgres://postgres:temporary-test-only@127.0.0.1:5432/postgres",
                "-e",
                "PGRST_DB_SCHEMAS=public",
                "-e",
                "PGRST_DB_ANON_ROLE=anon",
                "-e",
                f"PGRST_JWT_SECRET={JWT_SECRET}",
                "postgrest/postgrest:v14.2",
            ],
            check=True,
            capture_output=True,
        )
        try:
            base = f"http://127.0.0.1:{port}"

            def request(path, payload=None, user=users[0]):
                headers = {"Content-Type": "application/json"}
                if user:
                    headers["Authorization"] = f"Bearer {jwt(user)}"
                data = json.dumps(payload).encode() if payload is not None else None
                req = urllib.request.Request(base + path, data=data, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=5) as response:
                        return response.status, json.loads(response.read())
                except urllib.error.HTTPError as error:
                    return error.code, json.loads(error.read())

            for _ in range(60):
                try:
                    if request("/rpc/pull_events", {})[0] == 200:
                        break
                except (urllib.error.URLError, ConnectionResetError):
                    pass
                time.sleep(0.5)
            else:
                raise RuntimeError("PostgREST startup timed out")
            event = dict(
                id=str(uuid.uuid4()),
                device_id=str(uuid.uuid4()),
                kind="reading.page",
                entity_id="example.http:1.0.0:page:1",
                base_revision=0,
                payload=dict(
                    lesson_id="example.http",
                    version="1.0.0",
                    page=1,
                    pages=2,
                    read=True,
                ),
            )
            status, receipt = request("/rpc/push_events", {"events": [event]})
            assert status == 200 and receipt[0]["id"] == event["id"], (status, receipt)
            assert request("/rpc/push_events", {"events": [event]}) == (200, receipt)
            mismatch = {**event, "payload": {**event["payload"], "read": False}}
            assert (
                request("/rpc/push_events", {"events": [mismatch]})[1]["message"]
                == "event_mismatch"
            )
            malformed = {**event, "kind": None}
            assert (
                request("/rpc/push_events", {"events": [malformed]})[1]["message"]
                == "invalid_event"
            )
            competitors = [
                {
                    **event,
                    "id": str(uuid.uuid4()),
                    "entity_id": "example.http:1.0.0:page:2",
                    "payload": {**event["payload"], "page": 2},
                }
                for _ in range(2)
            ]
            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(
                    pool.map(
                        lambda candidate: request(
                            "/rpc/push_events", {"events": [candidate]}
                        ),
                        competitors,
                    )
                )
            assert sum(status == 200 for status, _ in outcomes) == 1
            assert (
                sum(
                    isinstance(body, dict)
                    and body.get("message") == "revision_conflict"
                    for _, body in outcomes
                )
                == 1
            )
            original_digest = pg.sql(
                "SELECT sha256 FROM test_migrations.applied WHERE name='001_sync.sql';"
            ).strip()
            pg.sql(
                "UPDATE test_migrations.applied SET sha256='changed' WHERE name='001_sync.sql';"
            )
            try:
                pg.apply_migrations()
                raise AssertionError("Changed migration was silently skipped")
            except RuntimeError as error:
                assert "Applied migration changed" in str(error)
            finally:
                pg.sql(
                    f"UPDATE test_migrations.applied SET sha256='{original_digest}' WHERE name='001_sync.sql';"
                )
            assert request("/rpc/pull_events", {}, users[1]) == (200, [])
            assert request("/rpc/pull_events", {}, None)[0] in (401, 403)
            assert request("/events")[0] == 404
            status, catalog = request("/rumo_questions")
            assert status == 200 and all(
                "answer" not in row and "comment" not in row for row in catalog
            )
            assert request("/rpc/progress_summary", {})[1]["look"] is None
            print(
                "PostgreSQL 17.6 + PostgREST 14.2 HTTP/RLS/replay/CAS/catalog checks passed; Auth uses synthetic test JWTs."
            )
        finally:
            subprocess.run(["docker", "rm", "-f", rest], capture_output=True)


if __name__ == "__main__":
    main()
