"""Cross-language RPC flow; opt in to disposable Docker with RUMO_POSTGRES_TEST=1."""

import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from backend.tests.postgres_harness import PostgresHarness
from core import Store
from desktop_sync import service_for, workspace_for
from sync_client import SyncWorkspace
from study_sync import StudySync


class RpcTransport:
    def __init__(self, pg, user):
        self.pg, self.account_id = pg, user

    def push_events(self, events):
        return self.pg.rpc(self.account_id, "push_events", dict(events=events))

    def pull_events(self, after_sequence, batch_size=200):
        return self.pg.rpc(
            self.account_id,
            "pull_events",
            dict(after_sequence=after_sequence, batch_size=batch_size),
        )


@unittest.skipUnless(
    os.environ.get("RUMO_POSTGRES_TEST") == "1",
    "Disposable PostgreSQL test requires explicit environment opt-in",
)
class IntegratedSyncTests(unittest.TestCase):
    def test_three_areas_two_devices_replays_and_canonical_rpg(self):
        user = str(uuid.uuid4())
        with PostgresHarness() as pg, tempfile.TemporaryDirectory() as folder:
            pg.sql(
                f"INSERT INTO auth.users VALUES('{user}'); INSERT INTO public.rumo_lessons(id,version,pages,title,example) VALUES('example.lesson','1.0.0',2,'Exemplo',true); INSERT INTO rumo_private.questions(id,version,prompt,options,answer,example) VALUES('example.question','1.0.0','Exemplo','{{\"a\":\"A\",\"b\":\"B\"}}','a',true); INSERT INTO public.rumo_cards(id,version,front,back,example) VALUES('example.card','1.0.0','Frente','Verso',true);"
            )
            desktop = Store(Path(folder) / "desktop.sqlite3")
            browser = SyncWorkspace(Path(folder) / "browser.sqlite3")
            local = workspace_for(desktop)
            try:
                plan = desktop.save("plans", dict(name="Exemplo"))
                subject = desktop.save(
                    "subjects", dict(plan_id=plan, name="Exemplo", color="#D6B467")
                )
                topic = desktop.save("topics", dict(subject_id=subject, name="Exemplo"))
                local.bind_account(user, consent=True)
                browser.bind_account(user, consent=True)
                d, b = service_for(desktop), StudySync(browser)
                transport = RpcTransport(pg, user)
                d.read_page("example.lesson", "1.0.0", 1, 2, True)
                b.read_page("example.lesson", "1.0.0", 2, 2, True)
                local.sync(transport)
                browser.sync(transport)
                local.sync(transport)
                self.assertTrue(d.reading("example.lesson", "1.0.0", 2)["completed"])
                d.read_page("example.lesson", "1.0.0", 1, 2, False)
                local.sync(transport)
                self.assertFalse(d.reading("example.lesson", "1.0.0", 2)["completed"])
                sid = str(uuid.uuid4())
                b._enqueue(
                    "study.session",
                    sid,
                    dict(
                        plan_id="web-plan",
                        subject_id="web-subject",
                        topic_id="web-topic",
                        day="2026-10-12",
                        category="Questões",
                        elapsed=600,
                        lesson_id=None,
                        lesson_version=None,
                    ),
                )
                attempt = b.attempt("example.question", "1.0.0", "a", sid)
                b.review_card("example.card", "1.0.0", 3, sid)
                browser.sync(transport)
                replay = transport.push_events([attempt])
                self.assertEqual(replay[0]["id"], attempt["id"])
                local.sync(transport)
                session = next(
                    e
                    for e in local.events()
                    if e["kind"] == "study.session" and e["entity_id"] == sid
                )
                mapping = dict(plan_id=plan, subject_id=subject, topic_id=topic)
                desktop._applying_sync = True
                d.import_session(session, mapping)
                d.import_session(session, mapping)
                desktop._applying_sync = False
                self.assertEqual(desktop.stats(plan)["count"], 1)
                self.assertEqual(
                    desktop.one(
                        "SELECT correct,wrong FROM sessions WHERE id=?", (sid,)
                    ),
                    dict(correct=1, wrong=0),
                )
                self.assertEqual(desktop.rpg.profile(plan)["xp"], 10)
                self.assertEqual(
                    d.projection.card_schedule("example.card", "1.0.0")["repetitions"],
                    1,
                )
                summary = pg.rpc(user, "study_summary", {})
                self.assertEqual(summary["xp"], 10)
            finally:
                browser.close()
                local.close()
                desktop.db.close()
