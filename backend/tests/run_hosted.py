"""Explicit hosted smoke test: temporary confirmed Auth users, private events.

Requires RUMO_HOSTED_URL, RUMO_HOSTED_PUBLIC_KEY, RUMO_HOSTED_ADMIN_KEY in
process memory/environment. Never prints keys, passwords, tokens or bodies.
No catalog fixtures or permanent editorial records are created.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Api:
    def __init__(self, url, public_key, admin_key):
        parsed = urllib.parse.urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("HTTPS project URL required")
        self.opener = urllib.request.build_opener(NoRedirect())
        self.url, self.public_key, self.admin_key = (
            url.rstrip("/"),
            public_key,
            admin_key,
        )

    def request(self, path, payload=None, token=None, admin=False, method=None):
        key = self.admin_key if admin else self.public_key
        headers = {"apikey": key, "Content-Type": "application/json"}
        if admin:
            headers["Authorization"] = f"Bearer {key}"
        elif token:
            headers["Authorization"] = f"Bearer {token}"
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            self.url + path, headers=headers, data=data, method=method
        )
        try:
            with self.opener.open(req, timeout=30) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            raw = error.read()
            return error.code, json.loads(raw) if raw else None


def expect(status, expected, operation):
    if status not in expected:
        raise RuntimeError(f"{operation} failed (HTTP {status}); response withheld")


def main():
    values = [
        os.environ.get(name)
        for name in (
            "RUMO_HOSTED_URL",
            "RUMO_HOSTED_PUBLIC_KEY",
            "RUMO_HOSTED_ADMIN_KEY",
        )
    ]
    if not all(values):
        raise RuntimeError(
            "Set the three RUMO_HOSTED_* variables; no credentials are read from files"
        )
    api = Api(*values)
    users = []
    cleanup_failed = False
    try:
        accounts = []
        for _ in range(2):
            credentials = dict(
                email=f"rumo-qa-{uuid.uuid4().hex}@example.invalid",
                password=f"Qa-{uuid.uuid4().hex}-9!",
            )
            status, created = api.request(
                "/auth/v1/admin/users",
                {**credentials, "email_confirm": True},
                admin=True,
            )
            expect(status, (200, 201), "Create temporary confirmed user")
            user_id = str(uuid.UUID(created["id"]))
            users.append(user_id)  # Record before login so failures still clean up.
            status, session = api.request(
                "/auth/v1/token?grant_type=password", credentials
            )
            expect(status, (200,), "Password login")
            accounts.append(session)
        token = accounts[0]["access_token"]
        event = dict(
            id=str(uuid.uuid4()),
            device_id=str(uuid.uuid4()),
            kind="study.session",
            entity_id=str(uuid.uuid4()),
            base_revision=0,
            payload=dict(
                plan_id="site",
                subject_id="qa-temporary-subject",
                topic_id=None,
                day="2026-10-12",
                category="Teoria",
                elapsed=659,
                lesson_id=None,
                lesson_version=None,
            ),
        )
        endpoint = "/rest/v1/rpc/"
        status, receipt = api.request(
            endpoint + "push_events", {"events": [event]}, token
        )
        expect(status, (200,), "Authenticated RPC push")
        assert receipt[0]["id"] == event["id"]
        assert api.request(endpoint + "push_events", {"events": [event]}, token) == (
            200,
            receipt,
        )
        assert api.request(
            endpoint + "pull_events", {}, accounts[1]["access_token"]
        ) == (200, [])
        status, unauthorized = api.request(endpoint + "pull_events", {})
        expect(status, (401, 403), "Anonymous RPC denial")
        status, conflict = api.request(
            endpoint + "push_events",
            {"events": [{**event, "id": str(uuid.uuid4())}]},
            token,
        )
        assert status >= 400 and conflict.get("message") == "revision_conflict"
        status, summary = api.request(endpoint + "study_summary", {}, token)
        expect(status, (200,), "Server XP projection")
        assert summary["xp"] == 10 and summary["coins"] == 1
        status, catalog = api.request("/rest/v1/rumo_questions?select=*", token=token)
        expect(status, (200,), "Safe catalog view")
        assert all("answer" not in row and "comment" not in row for row in catalog)
        status, _ = api.request("/rest/v1/events?select=*", token=token)
        expect(status, (404,), "Private table not exposed")
        status, refreshed = api.request(
            "/auth/v1/token?grant_type=refresh_token",
            {"refresh_token": accounts[0]["refresh_token"]},
        )
        expect(status, (200,), "Session refresh")
        expect(
            api.request(endpoint + "pull_events", {}, refreshed["access_token"])[0],
            (200,),
            "Refreshed JWT RPC",
        )
        expect(
            api.request("/auth/v1/logout", {}, refreshed["access_token"])[0],
            (200, 204),
            "Logout",
        )
        expect(
            api.request(
                "/auth/v1/token?grant_type=refresh_token",
                {"refresh_token": refreshed["refresh_token"]},
            )[0],
            (400, 401),
            "Refresh revoked after logout",
        )
        print(
            "Hosted HTTPS Auth/password/refresh/logout, two-account isolation, replay/CAS, safe view and XP checks passed."
        )
    finally:
        for user_id in reversed(users):
            try:
                status, _ = api.request(
                    f"/auth/v1/admin/users/{user_id}", admin=True, method="DELETE"
                )
                if status not in (200, 204, 404):
                    cleanup_failed = True
                    print(
                        f"Temporary user cleanup failed (HTTP {status}); user ID: {user_id}"
                    )
            except Exception:
                cleanup_failed = True
                print(f"Temporary user cleanup failed; user ID: {user_id}")
        if cleanup_failed:
            raise RuntimeError(
                "Temporary account cleanup requires retry; IDs shown above, credentials withheld"
            )
        if users:
            print(
                "Temporary Auth users deleted; their private event/projection rows cascade on deletion. No editorial fixtures uploaded."
            )


if __name__ == "__main__":
    main()
