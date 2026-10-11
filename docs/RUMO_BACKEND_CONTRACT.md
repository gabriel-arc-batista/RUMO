# RPG backend integration

Codex owns `rpg.py`, `rpg_schema.py`, the persistence changes in `core.py` / `backups.py` / `storage.py`, domain tests and this contract. Frontend work can continue in `app.py`, `ui.py`, components and design documents. Do not implement a second RPG persistence store or a demo profile in the production flow.

The entry point is `app.store.rpg`, a local `RPGService` using the existing SQLite connection. Public APIs will be finalized and verified before integration:

- `profile(plan_id)`: real XP, level, coins, earned/spent amounts, correction credit, skill XP and observed performance. Empty history produces zero XP, never a demonstration character.
- `recommended_mission(plan_id, topic_id=None)`, `mission(id)`, `small_mission(id, minutes=5)`, `mission_fields(id)`: suggested study and clock defaults, partial progress without advancing a block. Clock/session context keys: `mission_id`, `difficulty_id`, `challenge_id`, `recall`.
- `save_difficulty(...)`, `difficulties(plan_id)`, `difficulty_evidence(id)`, `set_difficulty_state(id, state)`, `revenge_mission(id)`: manually described errors and evidence from distinct real encounters; no inferred concepts from totals.
- `review_fields(review_id)`: use the existing review IDs and study sessions; recall is a user assessment (`Lembrei`, `Parcial`, `Não lembrei`).
- `create_challenge(...)`, `challenges(plan_id)`, `challenge_fields(id)`: local dungeons/bosses use existing canonical sessions and mock results, never duplicate studies.
- `catalog(plan_id)`, `buy(plan_id, item_id)`, `equip(plan_id, item_id)`, `story(plan_id)`: decorative-only inventory and local milestones.
- `retroactive_preview(plan_id)`, `enroll_history(plan_id, session_ids)`: explicit opt-in with preview. Historical studies remain unrewarded by default.

`Store.save_session` accepts context as a final optional keyword argument, preserving all existing positional arguments. Session edits/deletes recalculate rewards; source IDs make retries idempotent. Display toggles are `rpg_show_character`, `rpg_effects`, `rpg_story`, `rpg_reward_notifications`.

Frontend must preserve these context keys from `clock_setup(initial)` through `session_form(initial=clock.state)` into `save_session(context=...)`. They are not columns of the canonical `sessions` table. Do not pass them to `Store.validate_session` or `Store.put('sessions', ...)`.

## Completed integration

The frontend handoff and design were read before integration. `journey_backend.py` implements the production provider against `Store.rpg`; preview remains explicit and isolated. Canonical equipment IDs are `backpack`, `scarf`, `compass`, `lantern`, `spyglass`. Theory missions never require questions automatically, and smaller mission duration is adjustable.

Schema 4 is additive. Genuine v1/v2/v3 backups receive empty extension tables without retroactive XP. Standalone missions use `position=None`, `lap=None`, `block_count=0`; the UI handles these fields. Difficulty forms select topics across the current plan.

98 tests and native GUI integration pass, including adjustable missions, clock pauses, review, manual difficulty, dungeon creation, canonical boss results and confirmed equipment purchase. See [validation](RUMO_RPG_VALIDATION.md) for platforms and limits.

## Integrated contracts

`Mission.completed` disables starting completed time tasks while the cycle still requires an explicit decision. Slots include `Título`, `Moldura`, `Insígnia` and the five painted equipment positions. Default provider is real; only `RUMO_JOURNEY=preview` loads an in-memory demonstration. Forms carry RPG context separately from canonical study values. Purchases use a real catalog preview; challenge cards call real canonical study/mock flows.

## Equipamentos 1.6.0

`progression(plan)` retorna seis `StudyPath`, sem escolha obrigatória; `Equipment` inclui categoria, propósito, aquisição e ação. `equipment_action(plan,item)` exige aquisição e equipamento, retornando um atalho de estudo. O inventário usa slots independentes para roupa, cabeça, pés, arma, escudo e montaria. Fontes/XP permanecem inalterados; migração e regras em `RUMO_EQUIPMENT.md`. Telas usam view models; ações nativas permanecem em `rpg_ui.py`.
