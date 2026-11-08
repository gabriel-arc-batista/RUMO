"""Flashcards pessoais: comandos e agenda offline sobre o serviço opcional.

``StudyProjection.card_schedule`` só enxerga eventos aceitos pelo servidor, e a
fila não guarda data. As revisões feitas sem conta ficam no log local
``card_review_log`` e entram na agenda em ordem cronológica até o servidor
devolver os mesmos eventos, que então passam a valer por si.
"""

import uuid
from datetime import datetime, timezone

from study_sync import schedule_review

LOG_SCHEMA = """CREATE TABLE IF NOT EXISTS card_review_log(
    event_id TEXT PRIMARY KEY,card_id TEXT NOT NULL,version TEXT NOT NULL,
    rating INTEGER NOT NULL,reviewed_at TEXT NOT NULL)"""
FIELDS = (
    "deck_id",
    "front",
    "back",
    "explanation",
    "source",
    "lesson_id",
    "question_id",
    "suspended",
    "deleted",
)
PRESERVED = ("lesson_id", "question_id", "suspended", "deleted")


class Cards:
    """Comandos de cartões pessoais e a agenda para revisão sem conta."""

    def __init__(self, service, now=lambda: datetime.now(timezone.utc)):
        self.service = service
        self.now = now
        with service.workspace.db:
            service.workspace.db.execute(LOG_SCHEMA)

    # Agenda -----------------------------------------------------------

    def _entries(self):
        """Revisões por cartão em uma única passada por chamada."""
        entries, server = {}, set()
        for event in self.service.projection.events():
            server.add(event["id"])
            if event["kind"] != "card.review":
                continue
            payload = event["payload"]
            reviews = entries.setdefault(payload["card_id"], [])
            reviews.append(
                (
                    self._stamp(event["received_at"]),
                    int(payload["rating"]),
                    str(payload["version"]),
                )
            )
        rows = self.service.workspace.db.execute(
            "SELECT event_id,card_id,version,rating,reviewed_at FROM card_review_log"
        ).fetchall()
        for event_id, card_id, version, rating, reviewed_at in rows:
            if event_id in server:
                continue
            reviews = entries.setdefault(card_id, [])
            reviews.append((self._stamp(reviewed_at), int(rating), str(version)))
        for reviews in entries.values():
            reviews.sort(key=lambda item: item[0])
        return entries

    @staticmethod
    def _stamp(text):
        stamp = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("Revisão exige data com fuso horário.")
        return stamp.astimezone(timezone.utc)

    @staticmethod
    def _chain(reviews):
        states, latest = {}, None
        for stamp, rating, version in reviews:
            state = schedule_review(
                states.get(version, latest), rating, stamp.isoformat()
            )
            states[version] = latest = state
        return states, latest

    def _state(self, card, entries):
        states, latest = self._chain(entries.get(card["id"], []))
        return states.get(str(card["revision"]), latest)

    @staticmethod
    def _mature(card, state, now):
        if card.get("suspended"):
            return False
        return state is None or datetime.fromisoformat(state["due"]) <= now

    def _cards(self):
        return self.service.cards("", True), self._entries()

    # Consultas --------------------------------------------------------

    def list(self, query="", deck_id=None, include_suspended=False):
        cards = self.service.cards(query, True)
        if deck_id is not None:
            cards = [c for c in cards if c.get("deck_id") == deck_id]
        entries = self._entries()
        for card in cards:
            state = self._state(card, entries)
            card["due"] = state["due"] if state else None
        if not include_suspended:
            cards = [c for c in cards if not c.get("suspended")]
        cards.sort(key=lambda c: (c["deck_id"], c["front"].casefold(), c["id"]))
        return cards

    def decks(self):
        cards, entries = self._cards()
        now = self.now()
        decks = {}
        for card in cards:
            box = decks.setdefault(
                card["deck_id"], dict(deck_id=card["deck_id"], total=0, due=0)
            )
            box["total"] += 1
            if self._mature(card, self._state(card, entries), now):
                box["due"] += 1
        return sorted(decks.values(), key=lambda d: d["deck_id"])

    def due(self, limit=50):
        """Novos (sem agenda) primeiro; vencidos por data, mais antigos antes."""
        cards, entries = self._cards()
        now = self.now()
        picks = []
        for card in cards:
            state = self._state(card, entries)
            if self._mature(card, state, now):
                due_at = datetime.fromisoformat(state["due"]) if state else now
                picks.append((state is not None, due_at, card))
        picks.sort(
            key=lambda item: (
                item[0],
                item[1],
                item[2]["front"].casefold(),
                item[2]["id"],
            )
        )
        return [item[2] for item in picks[: max(0, int(limit))]]

    def stats(self):
        cards, entries = self._cards()
        now = self.now()
        due = sum(
            1 for card in cards if self._mature(card, self._state(card, entries), now)
        )
        today = now.astimezone().date()
        reviewed = {
            card_id
            for card_id, reviews in entries.items()
            if any(stamp.astimezone().date() == today for stamp, _, _ in reviews)
        }
        return dict(total=len(cards), due=due, reviewed_today=len(reviewed))

    def schedule(self, card_id):
        card = self._current(card_id)
        states, latest = self._chain(self._entries().get(card_id, []))
        return states.get(str(card["revision"]), latest)

    def preview(self, card_id, rating):
        """Estado projetado de uma revisão a mais agora; alimenta os botões."""
        return schedule_review(self.schedule(card_id), rating, self.now().isoformat())

    # Comandos ---------------------------------------------------------

    def save(
        self, front, back, deck_id="pessoal", explanation="", source="", card_id=None
    ):
        editing = card_id is not None
        card_id = card_id or str(uuid.uuid4())
        base_revision = None
        payload = {
            "deck_id": deck_id,
            "front": front,
            "back": back,
            "explanation": explanation,
            "source": source,
            "lesson_id": None,
            "question_id": None,
            "suspended": False,
            "deleted": False,
        }
        if editing:
            current = self._current(card_id)
            payload.update({field: current[field] for field in PRESERVED})
            base_revision = int(current["revision"])
        self.service.save_card(payload, card_id=card_id, base_revision=base_revision)
        return card_id

    def suspend(self, card_id, suspended=True):
        self._rewrite(card_id, dict(suspended=bool(suspended)))

    def delete(self, card_id):
        self._rewrite(card_id, dict(deleted=True))

    def review(self, card_id, rating, round_id):
        current = self._current(card_id)
        if current.get("suspended"):
            raise ValueError("Cartão suspenso.")
        version = str(int(current["revision"]))
        event = self.service.review_card(card_id, version, rating, round_id)
        with self.service.workspace.db:
            self.service.workspace.db.execute(
                "INSERT INTO card_review_log(event_id,card_id,version,rating,reviewed_at)"
                " VALUES(?,?,?,?,?)",
                (event["id"], card_id, version, int(rating), self.now().isoformat()),
            )

    def export(self):
        return self.service.export_personal_cards()

    def import_cards(self, text):
        """Chame só com confirmação explícita; devolve quantos foram salvos."""
        return len(self.service.import_personal_cards(text))

    # Internos ---------------------------------------------------------

    def _find(self, card_id):
        for card in self.service.cards("", True):
            if card["id"] == card_id:
                return card
        return None

    def _current(self, card_id):
        card = self._find(card_id)
        if card is None:
            raise ValueError("Cartão não encontrado.")
        return card

    def _rewrite(self, card_id, changes):
        current = self._current(card_id)
        payload = {field: current[field] for field in FIELDS}
        payload.update(changes)
        self.service.save_card(
            payload, card_id=card_id, base_revision=int(current["revision"])
        )
