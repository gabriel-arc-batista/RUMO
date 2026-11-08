"""Flashcards: agenda offline sobre o serviço e fumaça da tela com Tk real."""

import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk

import ui
import screen_cards
from cards import Cards
from core import Store
from desktop_sync import service_for

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)


def round_id():
    return "cards-" + uuid.uuid4().hex


class CardDomainTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.folder.name) / "study.sqlite3")
        self.service = service_for(self.store)
        self.cards = Cards(self.service, now=lambda: NOW)

    def tearDown(self):
        workspace = getattr(self.store, "study_workspace", None)
        if workspace is not None:
            workspace.close()
        self.store.close()
        self.folder.cleanup()

    def test_create_lists_counts_and_deck_report(self):
        card_id = self.cards.save(
            "Frente", "Verso", explanation="Nota", source="Manual"
        )
        self.assertEqual(str(uuid.UUID(card_id)), card_id)
        listed = self.cards.list()
        self.assertEqual(len(listed), 1)
        card = listed[0]
        self.assertEqual(card["front"], "Frente")
        self.assertEqual(card["deck_id"], "pessoal")
        self.assertEqual(card["explanation"], "Nota")
        self.assertEqual(card["source"], "Manual")
        self.assertEqual(card["revision"], 1)
        self.assertIsNone(card["due"])
        self.assertEqual(self.cards.stats(), dict(total=1, due=1, reviewed_today=0))
        self.assertEqual(self.cards.decks(), [dict(deck_id="pessoal", total=1, due=1)])

    def test_edit_keeps_state_and_suspension_toggles(self):
        card_id = self.cards.save("Frente", "Verso")
        self.cards.suspend(card_id)
        self.cards.save("Nova frente", "Verso 2", card_id=card_id)
        card = self.cards.list(include_suspended=True)[0]
        self.assertEqual(card["front"], "Nova frente")
        self.assertEqual(card["back"], "Verso 2")
        self.assertEqual(card["revision"], 3)  # save, suspend, edit
        self.assertEqual(card["suspended"], True)
        self.cards.suspend(card_id, False)
        self.assertEqual(self.cards.list()[0]["suspended"], False)
        self.cards.delete(card_id)
        self.assertEqual(self.cards.list(), [])
        self.assertEqual(self.cards.stats()["total"], 0)
        with self.assertRaises(ValueError):
            self.cards.save("X", "Y", card_id=str(uuid.uuid4()))

    def test_suspended_card_leaves_due_and_returns_after_edit(self):
        card_id = self.cards.save("Frente", "Verso")
        self.cards.suspend(card_id)
        self.assertEqual(self.cards.due(), [])
        self.assertEqual(self.cards.decks()[0], dict(deck_id="pessoal", total=1, due=0))
        suspended = self.cards.list(include_suspended=True)[0]
        self.assertEqual(suspended["suspended"], True)
        self.cards.suspend(card_id, False)
        self.assertEqual([c["id"] for c in self.cards.due()], [card_id])

    def test_new_card_is_due_and_good_review_schedules_one_day(self):
        card_id = self.cards.save("Frente", "Verso")
        self.assertEqual([c["id"] for c in self.cards.due()], [card_id])
        self.cards.review(card_id, 3, round_id())
        self.assertEqual(self.cards.due(), [])
        schedule = self.cards.schedule(card_id)
        self.assertEqual(schedule["interval"], 1)
        self.assertEqual(schedule["repetitions"], 1)
        self.assertGreater(datetime.fromisoformat(schedule["due"]), NOW)
        stats = self.cards.stats()
        self.assertEqual((stats["due"], stats["reviewed_today"]), (0, 1))
        self.assertEqual(self.cards.decks()[0]["due"], 0)

    def test_wrong_review_returns_tomorrow(self):
        card_id = self.cards.save("Frente", "Verso")
        self.cards.review(card_id, 1, round_id())
        schedule = self.cards.schedule(card_id)
        self.assertEqual(schedule["interval"], 1)
        self.assertEqual(schedule["repetitions"], 0)
        self.assertEqual(
            datetime.fromisoformat(schedule["due"]).date(), NOW.date() + timedelta(1)
        )
        self.assertEqual(self.cards.preview(card_id, 3)["interval"], 1)

    def test_schedule_is_not_counted_twice_when_server_replays_the_event(self):
        card_id = self.cards.save("Frente", "Verso")
        self.cards.review(card_id, 3, round_id())
        before = self.cards.schedule(card_id)
        event_id, version, rating = self.service.workspace.db.execute(
            "SELECT event_id,version,rating FROM card_review_log WHERE card_id=?",
            (card_id,),
        ).fetchone()[:3]
        self.service.projection.apply_event(
            dict(
                id=event_id,
                sequence=1,
                revision=1,
                device_id=str(uuid.uuid4()),
                kind="card.review",
                entity_id=event_id,
                received_at=(NOW + timedelta(minutes=5)).isoformat(),
                payload=dict(card_id=card_id, version=version, rating=rating),
            )
        )
        after = self.cards.schedule(card_id)
        # Same review once: the server's time replaces the local one.
        self.assertEqual(before["interval"], after["interval"])
        self.assertEqual(before["repetitions"], after["repetitions"])
        self.assertEqual(self.cards.stats()["reviewed_today"], 1)

    def test_search_deck_filter_and_order(self):
        second = self.cards.save("Alpha", "Sobre alpha", deck_id="segundo")
        first = self.cards.save("Beta", "Sobre beta")
        self.assertEqual([c["id"] for c in self.cards.list(query="alpha")], [second])
        self.assertEqual(
            [c["front"] for c in self.cards.list(deck_id="pessoal")], ["Beta"]
        )
        self.assertEqual(
            [c["deck_id"] for c in self.cards.list()], ["pessoal", "segundo"]
        )
        self.assertIn(first, [c["id"] for c in self.cards.due()])

    def test_due_orders_new_first_then_older_overdue_and_respects_limit(self):
        old = Cards(self.service, now=lambda: NOW - timedelta(days=9))
        mid = Cards(self.service, now=lambda: NOW - timedelta(days=4))
        fresh_front = self.cards.save("Novo cartão", "Verso")
        stale_a = old.save("Antigo A", "Verso")
        old.review(stale_a, 3, round_id())
        stale_b = mid.save("Antigo B", "Verso")
        mid.review(stale_b, 3, round_id())
        due = [c["id"] for c in self.cards.due()]
        self.assertEqual(due.index(fresh_front), 0)
        self.assertEqual(due.index(stale_a), 1)
        self.assertEqual(due.index(stale_b), 2)
        self.assertEqual(len(self.cards.due(limit=2)), 2)

    def test_export_and_import_roundtrip(self):
        self.cards.save("Frente", "Verso")
        text = self.cards.export()
        self.assertEqual(self.cards.import_cards(text), 1)
        self.assertEqual(self.cards.stats()["total"], 2)

    def test_import_rejects_bad_payload_without_touching_data(self):
        self.cards.save("Frente", "Verso")
        with self.assertRaises(ValueError):
            self.cards.import_cards('{"format":"outro","cards":[]}')
        self.assertEqual(self.cards.stats()["total"], 1)


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


class _ScreenCase(unittest.TestCase):
    """Tk real quando houver display, com o serviço real sobre base temporária."""

    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"Tk display unavailable: {error}")
        self.folder = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.folder.name) / "study.sqlite3")
        cards = Cards(service_for(self.store), now=lambda: NOW)
        self.content = tk.Frame(self.root, bg=ui.FALLBACK["bg"])
        self.content.pack(fill="both", expand=True)
        self.root.withdraw()
        self.motion = self.root._motion = ui.Motion(self.root)
        self.motion.palette = dict(ui.FALLBACK)
        self.app = SimpleNamespace(
            root=self.root,
            content=self.content,
            bg=ui.FALLBACK["bg"],
            cards=cards,
            motion=self.motion,
            today=lambda: NOW.astimezone().date(),
            notify=lambda *args, **kwargs: None,
            refresh=lambda: self._refresh(),
        )

    def _refresh(self):
        for child in self.content.winfo_children():
            child.destroy()
        screen_cards.render(self.app)

    def tearDown(self):
        if self.root.winfo_exists():
            self.root.destroy()
        workspace = getattr(self.store, "study_workspace", None)
        if workspace is not None:
            workspace.close()
        self.store.close()
        self.folder.cleanup()

    def labels(self, parent):
        for widget in descendants(parent):
            if isinstance(widget, tk.Label):
                yield widget

    def texts(self, parent=None):
        return [label_["text"] for label_ in self.labels(parent or self.content)]

    def buttons(self, prefix):
        for widget in descendants(self.content):
            if isinstance(widget, ui.MotionButton):
                if widget.text.startswith(prefix):
                    yield widget


class PanelTests(_ScreenCase):
    def test_empty_panel_mounts(self):
        screen_cards.render(self.app)
        self.assertIn("Nenhum cartão ainda", self.texts())

    def test_panel_lists_a_page_and_paginator_works(self):
        for index in range(35):
            self.app.cards.save(f"Frente {index}", "Verso")
        screen_cards.render(self.app)
        rows = [
            widget
            for widget in descendants(self.content)
            if isinstance(widget, tk.Frame) and hasattr(widget, "trail")
        ]
        self.assertEqual(len(rows), 30)
        [more] = list(self.buttons("Mostrar mais"))
        more.invoke()
        rows = [
            widget
            for widget in descendants(self.content)
            if isinstance(widget, tk.Frame) and hasattr(widget, "trail")
        ]
        self.assertEqual(len(rows), 35)
        self.assertIn("para hoje", self.texts())

    def test_search_filters_and_empties_honestly(self):
        self.app.cards.save("Alfa", "Verso")
        self.app.cards.save("Beta", "Verso")
        screen_cards.render(self.app)
        [entry] = [w for w in descendants(self.content) if isinstance(w, ttk.Entry)]
        entry.insert(0, "Alfa")
        rows = [
            w
            for w in descendants(self.content)
            if isinstance(w, tk.Frame) and hasattr(w, "trail")
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(self.app.cards_state.get("query"), "Alfa")
        entry.delete(0, "end")
        entry.insert(0, "Nada haver")
        self.assertIn("Nenhum cartão nesta busca", self.texts())
        entry.delete(0, "end")
        self.assertEqual(len(list(self.buttons("Mostrar mais"))), 0)

    def test_golden_review_button_disabled_without_due(self):
        screen_cards.render(self.app)
        [button] = list(self.buttons("Revisar agora"))
        self.assertEqual(button.cget("state"), "disabled")


class ReviewTests(_ScreenCase):
    def _any_due(self):
        self.app.cards.save("Alpha", "Verso A")
        self.app.cards.save("Beta", "Verso B")

    def test_round_answers_then_finishes_with_summary(self):
        alpha_id = self.app.cards.save("Alpha", "Verso A")
        beta_id = self.app.cards.save("Beta", "Verso B")
        baseline_after = self.root.tk.call("after", "info")
        screen_cards.review_round(self.app)
        state = self.app.cards_state
        self.assertIs(state["frame"].master, self.content)
        self.assertEqual(state["phase"], "front")
        self.assertEqual(state["cards"][0]["id"], alpha_id)
        self.assertTrue(state["keys"])
        self.assertEqual(self.root.tk.call("after", "info"), baseline_after)
        screen_cards.reveal(self.app)
        self.assertEqual(state["phase"], "back")
        self.assertEqual(state["answer"]["text"], "Verso A")
        first_button = state["rates"][3]
        self.assertIn("amanhã", first_button.text)
        screen_cards.rate(self.app, 3)
        self.assertEqual(state["index"], 1)
        self.assertEqual(state["cards"][1]["id"], beta_id)
        self.assertEqual(state["phase"], "front")
        screen_cards.reveal(self.app)
        screen_cards.rate(self.app, 1)
        self.assertIn("Rodada concluída", self.texts())
        self.assertEqual(state["counts"], {1: 1, 2: 0, 3: 1, 4: 0})
        self.assertEqual(state["keys"], [])
        self.assertEqual(self.app.cards.stats()["reviewed_today"], 2)
        self.assertEqual(self.app.cards.due(), [])
        buttons = [
            w.text for w in descendants(self.content) if isinstance(w, ui.MotionButton)
        ]
        self.assertIn("Voltar ao painel", buttons)

    def test_destroying_review_releases_keys_and_leaves_no_after(self):
        self._any_due()
        screen_cards.review_round(self.app)
        state = self.app.cards_state
        screen_cards.reveal(self.app)
        self.content.destroy()
        self.assertEqual(state.get("keys"), [])
        self.assertFalse(self.root.tk.call("after", "info"))

    def test_keys_only_bound_during_round(self):
        self._any_due()
        baseline = str(self.root.tk.call("bind", ".", "<space>"))
        screen_cards.review_round(self.app)
        state = self.app.cards_state
        for seq, funcid in state["keys"]:
            self.assertIn(funcid, str(self.root.tk.call("bind", ".", seq)))
        self.content.destroy()
        self.assertEqual(str(self.root.tk.call("bind", ".", "<space>")), baseline)


class EditorTests(_ScreenCase):
    def test_editor_creates_card_is_mandatory(self):
        screen_cards.render(self.app)
        win = screen_cards.open_editor(self.app)
        self.root.update_idletasks()
        entries = [w for w in descendants(win) if isinstance(w, tk.Entry)]
        bare = [e for e in entries if not e.cget("textvariable")]
        texts = [w for w in descendants(win) if isinstance(w, tk.Text)]
        self.assertEqual(len(bare), 2)
        self.assertEqual(len(texts), 2)
        [save] = [
            w
            for w in descendants(win)
            if isinstance(w, ui.MotionButton) and w.text == "Salvar cartão"
        ]
        save.invoke()
        self.assertIn("Escreva a frente e o verso", self._status_text(win))
        bare[0].insert(0, "Frente do teclado")
        texts[0].insert("1.0", "Verso do teclado")
        save.invoke()
        cards = self.app.cards.list()
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["front"], "Frente do teclado")
        self.assertEqual(cards[0]["back"], "Verso do teclado")
        self.assertEqual(cards[0]["deck_id"], "pessoal")
        self.assertFalse(win.winfo_exists())

    def _status_text(self, win):
        for widget in descendants(win):
            if (
                isinstance(widget, tk.Label)
                and widget.cget("fg") == ui.FALLBACK["error"]
            ):
                return widget.cget("text")
        return ""

    def test_editor_edits_existing_card(self):
        card_id = self.app.cards.save("Antiga", "Verso")
        screen_cards.render(self.app)
        win = screen_cards.open_editor(self.app, self.app.cards.list()[0])
        self.root.update_idletasks()
        entries = [w for w in descendants(win) if isinstance(w, tk.Entry)]
        front = next(e for e in entries if e.get() == "Antiga")
        front.delete(0, "end")
        front.insert(0, "Atualizada")
        [save] = [
            w
            for w in descendants(win)
            if isinstance(w, ui.MotionButton) and w.text == "Salvar cartão"
        ]
        save.invoke()
        card = self.app.cards.list()[0]
        self.assertEqual(card["id"], card_id)
        self.assertEqual(card["revision"], 2)
        self.assertEqual(card["front"], "Atualizada")


if __name__ == "__main__":
    unittest.main()
