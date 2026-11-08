"""Smoke tests for the Arena screen with a real Tk and a fake service."""

import os
import tkinter as tk
import unittest
from datetime import date

import screen_arena
import arena_ui
from theme import palette
from ui import Motion, MotionButton


def display_available():
    if os.name != "nt" and not os.environ.get("DISPLAY"):
        return False
    try:
        root = tk.Tk()
        root.destroy()
        return True
    except tk.TclError:
        return False


DISPLAY = display_available()


def question(identifier, kind="certo-errado", answer="certo", status="ativa", **extra):
    data = {
        "id": identifier,
        "subject_id": "s1",
        "topic_id": "t1",
        "kind": kind,
        "statement": "Enunciado " + identifier,
        "options": [],
        "answer": answer,
        "comment": "",
        "origin": "pessoal",
        "source": "",
        "external_id": None,
        "version": "1",
        "status": status,
    }
    data.update(extra)
    return data


def texts(widget):
    found = []
    for child in widget.winfo_children():
        if isinstance(child, tk.Label):
            found.append(str(child.cget("text")))
        found.extend(texts(child))
    return found


def buttons(widget):
    found = []
    for child in widget.winfo_children():
        if isinstance(child, MotionButton) and child.text:
            found.append(child.text)
        found.extend(buttons(child))
    return found


class FakeRound:
    def __init__(self, questions):
        self.questions = tuple(questions)
        self.plan_id = "p1"
        self.subject_id = "s1"
        self.topic_id = "t1"
        self.answered = {}

    def answer(self, question_id, choice):
        if question_id in self.answered:
            raise ValueError("Esta questão já foi respondida nesta rodada.")
        item = next(q for q in self.questions if q["id"] == question_id)
        self.answered[question_id] = choice
        if item["status"] == "anulada":
            correct = None
        else:
            correct = choice == item["answer"]
        return {
            "correct": correct,
            "expected": item["answer"],
            "comment": item.get("comment", ""),
        }

    @property
    def counts(self):
        correct = wrong = 0
        for item in self.questions:
            choice = self.answered.get(item["id"])
            if choice is None or item["status"] == "anulada":
                continue
            if choice == item["answer"]:
                correct += 1
            else:
                wrong += 1
        return correct, wrong

    @property
    def done(self):
        return all(item["id"] in self.answered for item in self.questions)


class FakeArena:
    def __init__(self, summary=None, topics=(), questions=(), session="ses-1"):
        self._summary = dict(
            summary
            or {
                "questions": 0,
                "answered": 0,
                "correct": 0,
                "wrong": 0,
                "accuracy": None,
                "to_redo": 0,
            }
        )
        self._topics = list(topics)
        self._questions = list(questions)
        self.session = session
        self.started = []
        self.finished = []

    def summary(self, plan_id):
        return dict(self._summary)

    def topics(self, plan_id):
        return [dict(topic) for topic in self._topics]

    def start_round(self, plan_id, topic_id, mode="novas", limit=10):
        self.started.append((plan_id, topic_id, mode))
        return FakeRound(self._questions)

    def finish_round(self, round_, elapsed):
        self.finished.append((round_, elapsed))
        return self.session if round_.answered else None

    def questions(self, plan_id, topic_id=None, query="", include_retired=False):
        return [dict(item) for item in self._questions]

    def save_question(self, payload, question_id=None):
        return question_id or "q-new"

    def set_status(self, question_id, status):
        for item in self._questions:
            if item["id"] == question_id:
                item["status"] = status


class FakeApp:
    def __init__(self, arena):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root._motion = Motion(self.root)
        self.root._motion.palette = palette()
        self.motion = self.root._motion
        self.bg = self.motion.palette["bg"]
        self.content = tk.Frame(self.root, bg=self.bg)
        self.content.pack(fill="both", expand=True)
        self.plan = "p1"
        self.arena = arena
        self.notes = []
        self.sessions = []
        self.refreshes = 0
        self._subjects = {"Bancos de Dados": "s1"}
        self._topics = {"s1": {"Arquitetura": "t1"}}

    def subject_map(self):
        return dict(self._subjects)

    def topic_map(self, subject=None):
        return dict(self._topics.get(subject, {}))

    def today(self):
        return date(2026, 11, 8)

    def notify(self, text, title=None, **kwargs):
        self.notes.append((title, text))

    def refresh(self):
        self.refreshes += 1
        for child in self.content.winfo_children():
            child.destroy()

    def after_arena_session(self, session_id):
        self.sessions.append(session_id)


@unittest.skipUnless(DISPLAY, "sem display para o Tk")
class ArenaScreenTest(unittest.TestCase):
    def make_app(self, **kwargs):
        self.arena = FakeArena(**kwargs)
        self.app = FakeApp(self.arena)
        self.addCleanup(self.app.root.destroy)
        return self.app

    def test_empty_panel_teaches_the_next_step(self):
        app = self.make_app()
        screen_arena.render(app)
        self.assertIn("Nenhuma questão ainda", texts(app.content))
        names = buttons(app.content)
        self.assertIn("Criar questão", names)
        self.assertIn("Importar pacote", names)

    def test_panel_lists_topics_with_actions(self):
        app = self.make_app(
            summary={
                "questions": 5,
                "answered": 7,
                "correct": 5,
                "wrong": 2,
                "accuracy": 71.4,
                "to_redo": 2,
            },
            topics=[
                {
                    "subject_id": "s1",
                    "subject": "Bancos de Dados",
                    "topic_id": "t1",
                    "topic": "Arquitetura",
                    "total": 5,
                    "unanswered": 3,
                    "to_redo": 2,
                }
            ],
        )
        screen_arena.render(app)
        self.assertIn("Arquitetura", texts(app.content))
        names = buttons(app.content)
        self.assertIn("Treinar", names)
        self.assertIn("Refazer erros", names)

    def test_round_answers_shows_correction_and_finishes_once(self):
        questions = [
            question("q1", comment="Comentário de apoio"),
            question(
                "q2",
                kind="multipla-escolha",
                answer="b",
                options=[
                    {"id": "a", "text": "Primeira"},
                    {"id": "b", "text": "Segunda"},
                ],
            ),
        ]
        app = self.make_app(questions=questions)
        screen_arena.render(app)
        view = screen_arena.play(app, self.arena.start_round("p1", "t1"))
        self.assertEqual(self.arena.started[-1], ("p1", "t1", "novas"))
        view.answer("certo")
        self.assertTrue(view.answered)
        shown = texts(view.feedback)
        self.assertIn("Certo", shown)
        self.assertIn("Gabarito: Certo", " ".join(shown))
        self.assertIn("Comentário de apoio", shown)
        view.advance()
        view.answer("a")
        self.assertIn("Errado", texts(view.feedback))
        view.advance()
        self.assertEqual(len(self.arena.finished), 1)
        self.assertEqual(self.arena.finished[0][0].counts, (1, 1))
        self.assertEqual(app.sessions, ["ses-1"])
        # The app's own "Sessão registrada" toast is the only confirmation.
        self.assertEqual(app.notes, [])
        self.assertEqual(app.refreshes, 1)
        self.assertTrue(view.finished)

    def test_annulled_question_is_neutral_and_does_not_count(self):
        app = self.make_app(
            questions=[
                question(
                    "q1",
                    kind="multipla-escolha",
                    status="anulada",
                    answer="a",
                    options=[{"id": "a", "text": "Única"}],
                )
            ]
        )
        view = screen_arena.play(app, self.arena.start_round("p1", "t1"))
        view.answer("a")
        shown = texts(view.feedback)
        self.assertIn("Questão anulada", shown)
        self.assertEqual(self.arena.finished, [])
        view.finish()
        self.assertEqual(len(self.arena.finished), 1)
        self.assertEqual(app.sessions, ["ses-1"])

    def test_destroy_mid_round_leaves_no_pending_timer_or_binding(self):
        app = self.make_app(questions=[question("q1")])
        view = screen_arena.play(app, self.arena.start_round("p1", "t1"))
        timer = str(view._timer)
        self.assertIn(timer, set(app.root.tk.call("after", "info")))
        self.assertTrue(view._binds)
        view.destroy()
        self.assertNotIn(timer, set(app.root.tk.call("after", "info")))
        self.assertEqual(view._binds, [])

    def test_leaving_without_answers_records_nothing(self):
        app = self.make_app(questions=[question("q1")])
        view = screen_arena.play(app, self.arena.start_round("p1", "t1"))
        view.finish()
        self.assertEqual(len(self.arena.finished), 1)
        self.assertEqual(app.sessions, [])
        self.assertTrue(app.notes)
        self.assertIn("Nada respondido", " ".join(text for _, text in app.notes))

    def test_editor_opens_and_reports_missing_topic(self):
        app = self.make_app()
        win = arena_ui.edit_question(app)
        self.addCleanup(win.destroy)
        save = _button(win, "Salvar questão")
        self.assertIsNotNone(save)
        save.invoke()
        self.assertIn("Escolha a matéria e o assunto", " ".join(texts(win)))

    def test_bank_opens_with_honest_empty_state(self):
        app = self.make_app()
        win = arena_ui.question_bank(app)
        self.addCleanup(win.destroy)
        self.assertIn("Nenhuma questão encontrada", " ".join(texts(win)))

    def test_round_title_shortens_long_subject_and_topic(self):
        long_subject = "Engenharia de Software e Práticas Ágeis em Ambientes Complexos e Distribuídos"
        long_topic = "Metodologias Ágeis, Scrum, Kanban, XP e Práticas de Integração Contínua em Larga Escala"
        app = self.make_app(questions=[question("q1")])
        app._subjects = {long_subject: "s1"}
        app._topics = {"s1": {long_topic: "t1"}}
        view = screen_arena.play(app, self.arena.start_round("p1", "t1"))
        self.assertLessEqual(len(view.title.cget("text")), 80)
        self.assertTrue(view.title.cget("text").endswith("…"))


def _button(widget, text):
    for child in widget.winfo_children():
        if isinstance(child, MotionButton) and child.text == text:
            return child
        found = _button(child, text)
        if found:
            return found
    return None


if __name__ == "__main__":
    unittest.main()


class ArenaAuditUiTests(unittest.TestCase):
    def test_typing_in_a_text_field_never_answers(self):
        view = screen_arena.RoundView.__new__(screen_arena.RoundView)
        view.finished = view.answered = False
        calls = []
        view.answer = calls.append
        event = type("E", (), {})()
        event.widget = tk.Entry.__new__(tk.Entry)
        event.keysym = "c"
        view._on_key(event)
        self.assertEqual(calls, [])
