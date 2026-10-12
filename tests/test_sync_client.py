import tempfile
import json
import sqlite3
import base64
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock

from sync_client import SyncError, SyncWorkspace, SupabaseTransport, _NoRedirect


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "workspace.sqlite3"
        self.workspace = SyncWorkspace(self.path)
        self.account = str(uuid.uuid4())

    def tearDown(self):
        self.workspace.close()
        self.temp.cleanup()

    def event(self, sequence=1):
        return dict(
            id=str(uuid.uuid4()),
            device_id=str(uuid.uuid4()),
            kind="reading.page",
            entity_id="lesson:v1:page:1",
            base_revision=0,
            payload=dict(lesson_id="lesson", version="v1", page=1, pages=2, read=True),
            sequence=sequence,
            revision=1,
        )

    def test_explicit_selection_and_account_lock(self):
        event = self.workspace.enqueue("reading.page", "page", {"read": True})
        self.assertEqual(self.workspace.pending(), [])
        with self.assertRaises(SyncError):
            self.workspace.bind_account(self.account)
        self.workspace.bind_account(self.account, consent=True)
        self.assertEqual(self.workspace.pending(), [])
        self.workspace.share_events([event["id"]])
        self.assertEqual(self.workspace.pending()[0]["id"], event["id"])
        with self.assertRaises(SyncError):
            self.workspace.bind_account(str(uuid.uuid4()), consent=True)

    def test_persistence_and_retry_same_id(self):
        self.workspace.bind_account(self.account, consent=True)
        event = self.workspace.enqueue("reading.page", "page", {"read": True})
        device = self.workspace.device_id
        self.workspace.close()
        self.workspace = SyncWorkspace(self.path)
        self.assertEqual(self.workspace.device_id, device)
        transport = Mock(account_id=self.account)
        transport.pull_events.return_value = []
        transport.push_events.side_effect = OSError("offline")
        with self.assertRaises(OSError):
            self.workspace.sync(transport)
        self.assertEqual(self.workspace.pending(), [event])
        transport.push_events.side_effect = None
        transport.push_events.return_value = [{"id": event["id"], "sequence": 1}]
        self.assertEqual(self.workspace.sync(transport), "synced")
        self.assertEqual(transport.push_events.call_args.args[0][0]["id"], event["id"])

    def test_cursor_projection_atomic_on_failure(self):
        first, second = self.event(1), self.event(2)

        def apply(event):
            if event["sequence"] == 2:
                raise SyncError("projection_failed")

        self.workspace.set_projector(apply)
        with self.assertRaises(SyncError):
            self.workspace.apply_pull([first, second])
        self.assertEqual(self.workspace.cursor, 0)
        self.assertEqual(self.workspace.events(), [])
        self.assertIsNone(self.workspace.entity(first["kind"], first["entity_id"]))

    def test_conflict_preserves_both_versions(self):
        self.workspace.bind_account(self.account, consent=True)
        event = self.workspace.enqueue(
            "reading.page", "lesson:v1:page:1", {"read": False}
        )
        remote = self.event()
        transport = Mock(account_id=self.account)
        transport.pull_events.side_effect = [[], [remote]]
        transport.push_events.side_effect = SyncError("revision_conflict")
        self.assertEqual(self.workspace.sync(transport), "conflict")
        self.assertEqual(self.workspace.conflicts(), [event])
        self.assertEqual(self.workspace.events(), [remote])
        resolved = self.workspace.resolve_conflict(event["id"], {"read": False}, 1)
        self.assertNotEqual(resolved["id"], event["id"])
        self.assertEqual(self.workspace.conflicts(), [])

    def test_conflict_isolates_one_event(self):
        self.workspace.bind_account(self.account, consent=True)
        first = self.workspace.enqueue("note.save", "first", {"text": "a"})
        second = self.workspace.enqueue("note.save", "second", {"text": "b"})
        transport = Mock(account_id=self.account)
        transport.pull_events.return_value = []
        transport.push_events.side_effect = SyncError("revision_conflict")
        self.workspace.sync(transport)
        self.assertEqual(self.workspace.conflicts(), [first])
        self.assertEqual(self.workspace.pending(), [second])
        transport.push_events.side_effect = None
        transport.push_events.return_value = [{"id": second["id"], "sequence": 2}]
        self.assertEqual(self.workspace.sync(transport), "conflict")
        self.assertEqual(self.workspace.pending(), [])

    def test_local_only_cannot_be_shared_and_persists(self):
        protected = self.workspace.enqueue(
            "note.save", "private", {"text": "private"}, local_only=True
        )
        personal = self.workspace.enqueue(
            "reading.page",
            "private-page",
            {"lesson_id": "pessoal.document", "read": True},
        )
        ordinary = self.workspace.enqueue("note.save", "ordinary", {"text": "share"})
        self.workspace.bind_account(self.account, consent=True)
        with self.assertRaises(SyncError) as caught:
            self.workspace.share_events([ordinary["id"], protected["id"]])
        self.assertEqual(caught.exception.code, "local_only")
        self.assertEqual(self.workspace.pending(), [])
        self.workspace.close()
        self.workspace = SyncWorkspace(self.path)
        for event in (personal, protected):
            with self.assertRaises(SyncError):
                self.workspace.share_events([event["id"]])
        self.assertEqual(self.workspace.pending(), [])

    def test_legacy_personal_draft_is_protected_by_migration(self):
        path = Path(self.temp.name) / "legacy.sqlite3"
        db = sqlite3.connect(path)
        db.execute(
            "CREATE TABLE outbox(id TEXT PRIMARY KEY,envelope TEXT NOT NULL,status TEXT NOT NULL,error TEXT)"
        )
        personal = self.event()
        personal["payload"]["lesson_id"] = "pessoal.document"
        db.execute(
            "INSERT INTO outbox VALUES(?,?,'pending',NULL)",
            (personal["id"], json.dumps(personal)),
        )
        db.commit()
        db.close()
        workspace = SyncWorkspace(path)
        try:
            workspace.bind_account(self.account, consent=True)
            self.assertEqual(workspace.pending(), [])
            with self.assertRaises(SyncError):
                workspace.share_events([personal["id"]])
        finally:
            workspace.close()

    def test_enqueue_does_not_commit_outer_transaction(self):
        with self.assertRaises(RuntimeError):
            with self.workspace.db:
                self.workspace.db.execute(
                    "INSERT INTO metadata VALUES('outer','temporary')"
                )
                self.workspace.enqueue("note.save", "note", {"text": "temporary"})
                raise RuntimeError("rollback")
        self.assertIsNone(self.workspace._meta("outer"))
        self.assertEqual(
            self.workspace.db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0], 0
        )

    def test_conflict_resolution_is_atomic_on_failure(self):
        self.workspace.bind_account(self.account, consent=True)
        event = self.workspace.enqueue("note.save", "note", {"text": "old"})
        self.workspace.db.execute(
            "UPDATE outbox SET status='conflict' WHERE id=?", (event["id"],)
        )
        self.workspace.db.commit()
        self.workspace.db.execute(
            "CREATE TRIGGER prevent_resolve BEFORE UPDATE ON outbox WHEN NEW.status='resolved' BEGIN SELECT RAISE(ABORT,'test failure'); END"
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.workspace.resolve_conflict(event["id"], {"text": "replacement"}, 1)
        self.assertEqual(self.workspace.conflicts(), [event])
        self.assertEqual(self.workspace.pending(), [])

    def test_conflict_status_survives_restart(self):
        event = self.workspace.enqueue("note.save", "note", {"text": "old"})
        self.workspace.db.execute(
            "UPDATE outbox SET status='conflict' WHERE id=?", (event["id"],)
        )
        self.workspace.db.commit()
        self.workspace.close()
        self.workspace = SyncWorkspace(self.path)
        self.assertEqual(self.workspace.status, "conflict")

    def test_invalid_pull_and_ack_do_not_discard_pending(self):
        self.workspace.bind_account(self.account, consent=True)
        event = self.workspace.enqueue("note.save", "note", {"text": "old"})
        transport = Mock(account_id=self.account)
        transport.pull_events.return_value = []
        transport.push_events.return_value = ["malformed"]
        with self.assertRaises(SyncError):
            self.workspace.sync(transport)
        self.assertEqual(self.workspace.pending(), [event])
        with self.assertRaises(SyncError):
            self.workspace.apply_pull([self.event(), "malformed"])
        self.assertEqual(self.workspace.cursor, 0)
        self.assertEqual(self.workspace.events(), [])

    def test_transport_rejects_privileged_keys(self):
        payload = (
            base64.urlsafe_b64encode(json.dumps({"role": "service_role"}).encode())
            .decode()
            .rstrip("=")
        )
        for key in ("sb_secret_test", "header." + payload + ".signature"):
            with self.assertRaises(ValueError):
                SupabaseTransport("https://example.com", key)

    def test_envelope_id_mismatch_and_limits(self):
        event = self.workspace.enqueue("note.save", "note", {"text": "ok"})
        with self.assertRaises(SyncError):
            self.workspace.enqueue(
                "note.save", "note", {"text": "changed"}, event_id=event["id"]
            )
        with self.assertRaises(SyncError):
            self.workspace.enqueue("note.save", "note", {"text": "x" * 20001})

    def test_transport_https_and_no_redirect(self):
        for url in (
            "http://example.com",
            "https://user:pass@example.com",
            "https://example.com?x=1",
        ):
            with self.assertRaises(ValueError):
                SupabaseTransport(url, "public")
        with self.assertRaises(SyncError):
            _NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.com")
        transport = SupabaseTransport("https://example.com", "public")
        with self.assertRaises(SyncError):
            transport.pull_events(0)
        transport.access_token = "secret"
        transport.refresh_token = "refresh"
        transport._call = Mock(side_effect=OSError())
        with self.assertRaises(OSError):
            transport.logout()
        self.assertIsNone(transport.access_token)
        self.assertIsNone(transport.refresh_token)


if __name__ == "__main__":
    unittest.main()
