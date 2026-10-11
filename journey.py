"""Typed contracts between RUMO screens and the journey (RPG) engine.

Screens only read these view models and call the provider. They never query
the database for journey data. ``source`` says where values came from:

- ``real``: derived read-only from existing records (journey_live.py);
- ``demo``: fictitious values for the visual preview (journey_demo.py);
- ``pending``: the field exists in the contract but no engine computes it yet.

Proposed for integration; the engine must validate these shapes against the
real rules before relying on them. Demo values must never be saved.
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol, Sequence

Source = Literal["real", "demo", "pending"]
ChapterState = Literal["done", "current", "locked"]
Slot = Literal[
    "costas",
    "pescoço",
    "peito",
    "cinto",
    "mão",
    "Título",
    "Moldura",
    "Insígnia",
    "roupa",
    "cabeça",
    "pés",
    "arma",
    "escudo",
    "montaria",
]


@dataclass(frozen=True)
class Mission:
    """Next cycle block presented as the task to start now."""

    subject_id: str
    subject: str
    topic_id: str | None
    topic: str | None
    suggested_seconds: int
    block_id: str | None
    cycle_id: str | None
    lap: int | None
    position: int | None
    block_count: int
    block_elapsed: int
    block_target: int
    category: str
    next_step: str
    last_studied: str | None
    reward_xp: int | None
    source: Source = "real"
    completed: bool = False


@dataclass(frozen=True)
class ReducedMission:
    """'Hoje está difícil': a smaller start that keeps the rest of the block."""

    minutes: int = 10
    questions: int = 2


@dataclass(frozen=True)
class ReviewSummary:
    overdue: int
    today: int
    upcoming: int
    source: Source = "real"


@dataclass(frozen=True)
class SubjectSkill:
    """Effort (time recorded) and performance (answers observed) stay separate."""

    subject_id: str
    name: str
    effort_seconds: int
    answered: int
    correct: int
    accuracy: float | None
    sample_ok: bool
    level: int | None
    xp: int | None
    xp_next: int | None
    progress_source: Source


@dataclass(frozen=True)
class Character:
    name: str
    title: str
    level: int | None
    xp: int | None
    xp_next: int | None
    coins: int | None
    equipped: tuple[str, ...]
    streak_days: int
    source: Source


@dataclass(frozen=True)
class Equipment:
    """Visual gear with study shortcuts; never changes observed study metrics."""

    id: str
    name: str
    slot: Slot
    description: str
    unlocked: bool
    equipped: bool
    unlock_hint: str
    source: Source
    kind: str = "Acessórios"
    purpose: str = ""
    acquisition: str = "shop"
    available: bool = False
    action: str = ""


@dataclass(frozen=True)
class StudyPath:
    id: str
    name: str
    rank: str
    value: int
    target: int
    unit: str
    purpose: str
    action: str
    source: Source = "real"


@dataclass(frozen=True)
class Achievement:
    id: str
    name: str
    rule: str
    progress: int
    target: int
    icon: str
    source: Source

    @property
    def done(self):
        return self.progress >= self.target


@dataclass(frozen=True)
class Chapter:
    number: int
    title: str
    summary: str
    state: ChapterState
    requirement: str
    source: Source


@dataclass(frozen=True)
class Challenge:
    """Dungeon (topics already studied) or boss (larger mock exam)."""

    id: str
    kind: Literal["masmorra", "chefe"]
    title: str
    detail: str
    questions: int
    minutes: int
    subjects: tuple[str, ...] = field(default_factory=tuple)
    available: bool = False
    source: Source = "demo"


@dataclass(frozen=True)
class Reward:
    """Shown briefly after a session is saved. XP/coins only from the engine."""

    seconds: int
    questions: int
    subject: str
    xp: int | None
    coins: int | None
    source: Source


class JourneyProvider(Protocol):
    """Read side used by screens plus the few UI actions they trigger."""

    def mission(self, plan: str) -> Mission | None: ...

    def reduced(self, mission: Mission) -> ReducedMission: ...

    def reviews(self, plan: str) -> ReviewSummary: ...

    def character(self, plan: str) -> Character: ...

    def skills(self, plan: str) -> Sequence[SubjectSkill]: ...

    def equipment(self, plan: str) -> Sequence[Equipment]: ...

    def progression(self, plan: str) -> Sequence[StudyPath]: ...

    def achievements(self, plan: str) -> Sequence[Achievement]: ...

    def chapters(self, plan: str) -> Sequence[Chapter]: ...

    def challenges(self, plan: str) -> Sequence[Challenge]: ...

    def reward_for(self, session: dict, subject: str) -> Reward | None: ...

    def toggle_equipment(self, plan: str, item_id: str) -> None: ...
