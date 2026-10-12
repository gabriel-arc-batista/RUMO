"""Local real GoTrue email/password + PostgreSQL17 + PostgREST integration.

Uses already available Docker images, loopback-only ports and synthetic users.
No hosted credentials, SMTP, personal databases or persistent containers.
"""

import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid

from postgres_harness import PostgresHarness
from run_postgrest import JWT_SECRET


def request(base, path, payload=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        raw = error.read()
        return error.code, json.loads(raw) if raw else None


def ready(base, path):
    for _ in range(60):
        try:
            if request(base, path)[0] == 200:
                return
        except (urllib.error.URLError, ConnectionResetError):
            pass
        time.sleep(0.5)
    raise RuntimeError("Local test HTTP service did not start")


def port(container, internal):
    result = subprocess.run(
        ["docker", "port", container, f"{internal}/tcp"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().rsplit(":", 1)[1]


def main():
    with PostgresHarness(
        "postgres:17.6", publish_http=True, publish_auth=True, initialize=False
    ) as pg:
        bootstrap = (
            (pg.root / "tests/bootstrap.sql")
            .read_text()
            .replace("create table auth.users(id uuid primary key);", "")
        )
        pg.sql(bootstrap)
        auth = f"rumo-gotrue-{uuid.uuid4().hex}"
        rest = f"rumo-postgrest-{uuid.uuid4().hex}"
        try:
            subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    auth,
                    "--network",
                    f"container:{pg.name}",
                    "-e",
                    "GOTRUE_API_HOST=0.0.0.0",
                    "-e",
                    "GOTRUE_API_PORT=9999",
                    "-e",
                    "API_EXTERNAL_URL=http://localhost:9999",
                    "-e",
                    "GOTRUE_SITE_URL=http://localhost:3000",
                    "-e",
                    "GOTRUE_DB_DRIVER=postgres",
                    "-e",
                    "GOTRUE_DB_DATABASE_URL=postgres://postgres:temporary-test-only@127.0.0.1:5432/postgres?search_path=auth",
                    "-e",
                    "GOTRUE_DB_NAMESPACE=auth",
                    "-e",
                    f"GOTRUE_JWT_SECRET={JWT_SECRET}",
                    "-e",
                    "GOTRUE_JWT_AUD=authenticated",
                    "-e",
                    "GOTRUE_JWT_DEFAULT_GROUP_NAME=authenticated",
                    "-e",
                    "GOTRUE_JWT_ADMIN_ROLES=service_role",
                    "-e",
                    "GOTRUE_EXTERNAL_EMAIL_ENABLED=true",
                    "-e",
                    "GOTRUE_MAILER_AUTOCONFIRM=true",
                    "-e",
                    "GOTRUE_DISABLE_SIGNUP=false",
                    "supabase/gotrue:v2.177.0",
                ],
                check=True,
                capture_output=True,
            )
            auth_base = f"http://127.0.0.1:{port(pg.name,9999)}"
            ready(auth_base, "/health")
            pg.apply_migrations()
            pg.apply_migrations()
            accounts = []
            for _ in range(2):
                credentials = dict(
                    email=f"rumo-{uuid.uuid4().hex}@example.invalid",
                    password="Temporary-test-password-123!",
                )
                status, registered = request(auth_base, "/signup", credentials)
                assert status == 200, (status, registered.get("msg"))
                status, session = request(
                    auth_base, "/token?grant_type=password", credentials
                )
                assert (
                    status == 200
                    and session.get("access_token")
                    and session.get("refresh_token")
                )
                accounts.append(session)
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
            rest_base = f"http://127.0.0.1:{port(pg.name,3000)}"
            ready(rest_base, "/")
            token = accounts[0]["access_token"]
            session_id = str(uuid.uuid4())
            event = dict(
                id=str(uuid.uuid4()),
                device_id=str(uuid.uuid4()),
                kind="study.session",
                entity_id=session_id,
                base_revision=0,
                payload=dict(
                    plan_id="site",
                    subject_id="example",
                    topic_id=None,
                    day="2026-10-12",
                    category="Teoria",
                    elapsed=659,
                    lesson_id=None,
                    lesson_version=None,
                ),
            )
            status, receipt = request(
                rest_base, "/rpc/push_events", {"events": [event]}, token
            )
            assert status == 200 and receipt[0]["id"] == event["id"]
            assert request(
                rest_base, "/rpc/push_events", {"events": [event]}, token
            ) == (200, receipt)
            assert request(
                rest_base, "/rpc/pull_events", {}, accounts[1]["access_token"]
            ) == (200, [])
            assert request(rest_base, "/rpc/study_summary", {}, token)[1]["xp"] == 10
            status, refreshed = request(
                auth_base,
                "/token?grant_type=refresh_token",
                {"refresh_token": accounts[0]["refresh_token"]},
            )
            assert status == 200 and refreshed.get("access_token")
            assert (
                request(rest_base, "/rpc/pull_events", {}, refreshed["access_token"])[0]
                == 200
            )
            status, _ = request(auth_base, "/logout", {}, refreshed["access_token"])
            assert status in (200, 204)
            assert request(
                auth_base,
                "/token?grant_type=refresh_token",
                {"refresh_token": refreshed["refresh_token"]},
            )[0] in (400, 401)
            print(
                "Real local GoTrue signup/password login/refresh/logout + PostgreSQL17/PostgREST two-account RPC checks passed."
            )
            print(
                "Logout revokes refresh session; already issued access JWTs remain valid until expiry. Gateway/SMTP/hosted signing keys are not covered."
            )
        finally:
            subprocess.run(["docker", "rm", "-f", rest, auth], capture_output=True)


if __name__ == "__main__":
    main()
