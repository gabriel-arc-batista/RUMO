# Tarefa arena-logic — domínio da Arena (agy)

Leia antes: `AGENTS.md`, `.agents/CONVENTIONS.md`, `.agents/PIPELINE.md`, `arena_schema.py`,
`core.py` (`Store.save_session`, `validate_session`) e `tests/test_arena_schema.py`.

## Objetivo

Criar `arena.py`: banco local de questões e rodadas de treino, sem Tk. Uma rodada é uma
sessão comum de "Questões" de **um** assunto; acertos/erros entram em `sessions` e as
tentativas em `arena_attempts` na mesma transação, via
`store.save_session(values, context={"arena_attempts": [...]})` (já implementado por Claude).
XP vem só da sessão; não chame nada do RPG.

## Arquivos permitidos

- criar `arena.py`
- criar `tests/test_arena.py`

Esquema (`arena_schema.py`), `core.py`, `backups.py` são do Claude: se precisar mudar, use `ask`.

## Contrato público (a tela da Arena já está sendo feita contra ele)

```python
class Arena:
    def __init__(self, store, now=datetime.now): ...  # now injetável nos testes

    # Banco
    def questions(self, plan_id, topic_id=None, query="", include_retired=False) -> list[dict]
    def question(self, question_id) -> dict | None
    def save_question(self, payload, question_id=None) -> str
    def set_status(self, question_id, status) -> None        # "ativa" | "anulada" | "retirada"
    def import_pack(self, text, subject_id, topic_id) -> dict # {"added", "updated", "skipped"}
    def export_personal(self, plan_id) -> str

    # Treino
    def topics(self, plan_id) -> list[dict]
    def start_round(self, plan_id, topic_id, mode="novas", limit=10) -> Round
    def finish_round(self, round, elapsed) -> str | None     # id da sessão; None se nada respondido
    def summary(self, plan_id) -> dict

@dataclass
class Round:
    plan_id: str; subject_id: str; topic_id: str
    questions: tuple[dict, ...]
    def answer(self, question_id, choice) -> dict  # {"correct": bool | None, "expected": str, "comment": str}
    @property
    def done(self) -> bool
    @property
    def counts(self) -> tuple[int, int]             # (acertos, erros); anuladas não contam
```

Formato da questão (dict devolvido): `id, subject_id, topic_id, kind, statement,
options (list[{"id","text"}]), answer, comment, origin, source, external_id, version,
status, created, updated` (`options` já decodificado de JSON).

`payload` de `save_question`: `{subject_id, topic_id, kind, statement, options, answer, comment, source}`.

## Regras

- `kind`: `certo-errado` (sem alternativas; gabarito `certo`/`errado`) ou `multipla-escolha`
  (2–10 alternativas, ids únicos `a`–`j`, textos não vazios; gabarito é um dos ids).
- Textos ≤ 20000 caracteres; enunciado não vazio. Assunto deve pertencer à matéria e ao plano.
- `fingerprint` = sha256 de `kind` + enunciado normalizado (casefold, espaços colapsados).
  Questão pessoal repetida no mesmo assunto → `ValueError("Questão repetida neste assunto.")`.
- Editar uma questão incrementa `version` (texto inteiro "1", "2"…) e atualiza `updated`;
  tentativas antigas mantêm `question_version`.
- `topics(plan_id)`: só assuntos com questões ativas/anuladas; cada item
  `{subject_id, subject, topic_id, topic, total, unanswered, to_redo}`.
  `to_redo` = questões ativas cuja **última** tentativa foi errada.
- `start_round` modos: `novas` (nunca respondidas), `refazer` (última tentativa errada),
  `todas` (menos recentes primeiro). Só questões `ativa`/`anulada`, nunca `retirada`.
  Ordem determinística (sem aleatoriedade). Sem questões → `ValueError` com texto amigável.
- `Round.answer`: uma resposta por questão por rodada (repetir → `ValueError`); anulada →
  `correct=None`. Escolha inválida para o tipo → `ValueError`.
- `finish_round(round, elapsed)`: `elapsed` inteiro ≥ 0 (segundos). Grava sessão com
  `category="Questões"`, `day` de hoje (`now`), `correct`, `wrong`, `blank=0`, mais os campos
  que `save_session` exigir. Uma única chamada a `save_session`; nada de transação própria.
- `summary(plan_id)` → `{questions, answered, correct, wrong, accuracy, to_redo}`;
  `accuracy` é float 0–100 ou `None` sem respostas.
- Pacote (`import_pack`): JSON ≤ 2 MB, `{"format": "RUMO-questions", "version": 1,
  "questions": [...]}`, ≤ 1000 itens, cada um no formato de
  `docs/campo-de-treinamento/CONTRATOS_ARENA_FLASHCARDS.md` (`id`, `type`, `statement`,
  `options`, `answer`, `comment`, `provenance`, `status`, `version`). Só `status` `publicada`
  (vira `ativa`) ou `anulada`; os outros são `skipped`. Mesmo `id` e `version` já existentes →
  `skipped`; mesmo `id` com versão nova → atualiza a linha (`updated`). Duplicata de enunciado
  no assunto → `skipped`. `source` = resumo legível de `provenance` (banca, ano, direitos).
  Arquivo inválido → `ValueError` **sem gravar nada** (tudo numa transação).
- `export_personal`: JSON no mesmo formato, só `origin="pessoal"`, sem tentativas.

## Aceite (rode e cole o resultado no relatório)

```sh
.venv/bin/python -m black --check arena.py tests/test_arena.py
.venv/bin/python -W error::ResourceWarning -m unittest tests.test_arena tests.test_arena_schema -v
.venv/bin/python -W error::ResourceWarning -m unittest discover -s tests
```

Testes mínimos: validação de cada tipo; repetida; edição sobe versão; os três modos;
resposta dupla; anulada não conta; `finish_round` grava 1 sessão com contagens certas e
as tentativas, e rodada vazia retorna `None`; `to_redo` muda após acertar; pacote válido,
reimportação idempotente, versão nova atualiza, pacote inválido não grava nada; export.
Base temporária (`tempfile`), `store.close()` no `tearDown`.
