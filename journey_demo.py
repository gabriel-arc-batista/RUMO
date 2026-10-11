"""Preview provider: real read-only data where it exists, isolated demo values elsewhere.

Everything with ``source="demo"`` is fictitious, kept in memory only and shown
with a DEMONSTRAÇÃO chip. Nothing here writes to the database. Replace
``PreviewJourney`` with the real engine provider (see docs/RUMO_HANDOFF.md).
"""

import zlib

import journey_live
from journey import (
    Achievement,
    Challenge,
    Chapter,
    Character,
    Equipment,
    ReducedMission,
    SubjectSkill,
)

DEMO_CHARACTER = dict(
    name="Viajante",
    title="Aprendiz de rota",
    level=4,
    xp=340,
    xp_next=600,
    coins=120,
)
DEMO_EQUIPMENT = [
    ("backpack", "Mochila de estudos", "costas", "Leva o essencial de cada matéria."),
    ("compass", "Bússola", "peito", "Aponta para o próximo assunto pendente."),
    ("scarf", "Cachecol de viagem", "pescoço", "Para as noites de revisão."),
    ("spyglass", "Luneta", "cinto", "Enxerga a prova no horizonte."),
    ("lantern", "Lanterna", "mão", "Ilumina os assuntos mais difíceis."),
]
DEMO_UNLOCKED = {"backpack", "compass", "scarf", "spyglass"}
DEMO_ACHIEVEMENTS = [
    (
        "first-step",
        "Primeiro passo",
        "Registrar a primeira sessão.",
        1,
        1,
        "footprints",
    ),
    ("week", "Semana possível", "Estudar em 4 dias de uma semana.", 4, 4, "calendar"),
    ("revenge", "Revanche", "Refazer 10 questões que você errou.", 6, 10, "swords"),
    ("memory", "Memória viva", "Concluir 5 revisões no prazo.", 3, 5, "brain"),
    ("map", "Mapa completo", "Concluir todos os assuntos de uma matéria.", 0, 1, "map"),
    ("boss", "Primeiro chefe", "Registrar um simulado completo.", 0, 1, "crown"),
]
DEMO_CHAPTERS = [
    (
        "O ponto de partida",
        "Você escolhe o destino e prepara a mochila com o edital.",
        "done",
        "Criar o primeiro ciclo",
    ),
    (
        "A primeira trilha",
        "As matérias de base revelam o caminho. Cada bloco é um trecho percorrido.",
        "current",
        "Concluir uma volta do ciclo",
    ),
    (
        "Ecos dos erros",
        "Questões erradas viram missões de revanche. Elas voltam mais fracas.",
        "locked",
        "Registrar 10 dificuldades",
    ),
    (
        "A torre das revisões",
        "Lembrar antes de consultar. O que volta à memória fica mais firme.",
        "locked",
        "Concluir 15 revisões",
    ),
    (
        "O guardião",
        "Um simulado completo, com calma e estratégia.",
        "locked",
        "Registrar um simulado completo",
    ),
]


def _demo_level(name):
    """Stable fictitious level per subject so the preview does not flicker."""
    seed = zlib.crc32(name.encode("utf-8"))
    level = 1 + seed % 5
    xp_next = 100 * (level + 1)
    return level, (seed // 7) % xp_next, xp_next


class PreviewJourney:
    def __init__(self, store):
        self.store = store
        self.equipped = {"backpack", "compass", "scarf"}

    def mission(self, plan):
        return journey_live.mission(self.store, plan)

    def reduced(self, mission):
        return ReducedMission()

    def reviews(self, plan):
        return journey_live.reviews(self.store, plan)

    def character(self, plan):
        current, _, _ = self.store.streak(plan)
        values = dict(DEMO_CHARACTER)
        values["name"] = (self.store.pref("profile", "") or "").strip() or values[
            "name"
        ]
        return Character(
            equipped=tuple(sorted(self.equipped)),
            streak_days=current,
            source="demo",
            **values,
        )

    def skills(self, plan):
        result = []
        for skill in journey_live.skills(self.store, plan):
            level, xp, xp_next = _demo_level(skill.name)
            result.append(
                SubjectSkill(
                    **{
                        **skill.__dict__,
                        "level": level,
                        "xp": xp,
                        "xp_next": xp_next,
                        "progress_source": "demo",
                    }
                )
            )
        return result

    def equipment(self, plan):
        return [
            Equipment(
                id=item,
                name=name,
                slot=slot,
                description=description,
                unlocked=item in DEMO_UNLOCKED,
                equipped=item in self.equipped,
                unlock_hint="" if item in DEMO_UNLOCKED else "Capítulo 3",
                source="demo",
            )
            for item, name, slot, description in DEMO_EQUIPMENT
        ]

    def toggle_equipment(self, plan, item_id):
        if item_id not in DEMO_UNLOCKED:
            return
        self.equipped ^= {item_id}

    def progression(self, plan):
        return []

    def achievements(self, plan):
        return [
            Achievement(*values[:5], icon=values[5], source="demo")
            for values in DEMO_ACHIEVEMENTS
        ]

    def chapters(self, plan):
        return [
            Chapter(index, title, summary, state, requirement, "demo")
            for index, (title, summary, state, requirement) in enumerate(
                DEMO_CHAPTERS, 1
            )
        ]

    def challenges(self, plan):
        studied = [
            s.name for s in journey_live.skills(self.store, plan) if s.effort_seconds
        ][:3]
        return [
            Challenge(
                id="dungeon-demo",
                kind="masmorra",
                title="Masmorra dos assuntos estudados",
                detail="Questões só de assuntos que você já viu. Sem conteúdo novo.",
                questions=15,
                minutes=30,
                subjects=tuple(studied),
            ),
            Challenge(
                id="boss-demo",
                kind="chefe",
                title="O guardião: simulado completo",
                detail="Prova longa no formato da banca. O resultado vira análise.",
                questions=120,
                minutes=240,
            ),
        ]

    def reward_for(self, session, subject):
        # No engine yet: rewards are never invented for real sessions.
        return None
