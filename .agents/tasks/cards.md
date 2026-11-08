# Tarefa cards — flashcards nativos (GLM)

Leia antes: `AGENTS.md`, `.agents/CONVENTIONS.md`, `.agents/PIPELINE.md`, `study_sync.py`
(`StudySync.cards/save_card/review_card`, `schedule_review`, `validate_card`),
`sync_client.py` (`SyncWorkspace.enqueue`, tabela `outbox`), `desktop_sync.service_for`,
`screen_reviews.py` (padrão de tela), `ui_kit.py`, `ui.py`, `docs/RUMO_DESIGN.md`.

## Objetivo

Flashcards pessoais no app, funcionando **sem conta**. A persistência já existe na área de
trabalho opcional (`study-sync.sqlite3`): sem conta os eventos ficam com status `local`.
Falta: agenda offline, um serviço enxuto e a tela.

## Arquivos permitidos

- criar `cards.py` — domínio, sem Tk
- criar `screen_cards.py` — `render(app)`
- criar `tests/test_cards.py`

Não edite `study_sync.py`, `sync_client.py`, `desktop_sync.py` nem `app.py` (Claude liga a
navegação). Precisa mudar um deles? `ask`.

## Contrato

```python
class Cards:
    def __init__(self, service, now=lambda: datetime.now(timezone.utc)): ...  # service = StudySync
    def list(self, query="", deck_id=None, include_suspended=False) -> list[dict]
    def decks(self) -> list[dict]                 # [{"deck_id", "total", "due"}]
    def save(self, front, back, deck_id="pessoal", explanation="", source="", card_id=None) -> str
    def suspend(self, card_id, suspended=True) -> None
    def delete(self, card_id) -> None
    def schedule(self, card_id) -> dict | None    # {"ease","repetitions","interval","due"}
    def due(self, limit=50) -> list[dict]          # novos (sem agenda) e vencidos, mais antigos primeiro
    def review(self, card_id, rating, round_id) -> None   # rating 1–4
    def stats(self) -> dict                        # {"total", "due", "reviewed_today"}
```

## Regras

- `save` monta o payload completo exigido por `validate_card` e usa `base_revision` da revisão
  atual do cartão ao editar. `delete` e `suspend` regravam o cartão (`deleted`/`suspended`).
- **Agenda offline:** `StudyProjection.card_schedule` só enxerga eventos aceitos pelo servidor.
  A fila não guarda data. Crie em `service.workspace.db` uma tabela própria
  `card_review_log(event_id TEXT PRIMARY KEY, card_id TEXT NOT NULL, version TEXT NOT NULL,
  rating INTEGER NOT NULL, reviewed_at TEXT NOT NULL)` (`CREATE TABLE IF NOT EXISTS`) e grave
  nela, logo após `review_card` devolver o evento, o `id` do evento e a hora (`now`, ISO com fuso).
  `schedule` aplica `schedule_review` em ordem cronológica sobre: revisões do servidor
  (`received_at`) + revisões locais do log cujo `event_id` **não** esteja entre os eventos do
  servidor (sem contar duas vezes depois da sincronização). Versão do cartão = `str(revision)`.
- `round_id`: um id por rodada de revisão (`"cards-" + uuid4().hex`), passado como `session_id`.
  Revisar cartões não cria sessão canônica nem XP nesta etapa.
- Leitura eficiente: não percorra todos os eventos uma vez por cartão; carregue uma vez por
  chamada de `due()`/`stats()`.

## Tela (`screen_cards.py`)

- Topo: `stat_row` (cartões, para hoje, revisados hoje) e ação dourada "Revisar agora (n)".
  `ActionMenu`: "Novo cartão", "Exportar", "Importar" (usa `export_personal_cards` /
  `import_personal_cards` do serviço, com confirmação antes de importar).
- Busca + lista (`Row`, paginada 30): frente, baralho, próxima data; editar, suspender, excluir
  (confirmação). Vazio: `ui_kit.empty` honesto com "Criar cartão".
- Revisão no próprio `app.content`: frente → "Mostrar resposta" (Espaço) → verso e explicação →
  Errei / Difícil / Bom / Fácil (teclas 1–4) com o próximo intervalo previsto em cada botão.
  Fim: resumo e volta ao painel.
- Editor: `Toplevel` com `activate_popup`; frente, verso, explicação, fonte, baralho.
- Serviço vem pronto em `app.cards`. Não construa `Cards`/`StudySync` na tela; sem SQL na tela.

## Vazamentos

Bindings de teclado da revisão removidos ao sair; `after` cancelado no `<Destroy>`;
nenhuma conexão SQLite aberta fora do workspace existente.

## Aceite (rode e cole o resultado no relatório)

```sh
.venv/bin/python -m black --check cards.py screen_cards.py tests/test_cards.py
.venv/bin/python -W error::ResourceWarning -m unittest tests.test_cards -v
.venv/bin/python -W error::ResourceWarning -m unittest discover -s tests
```

`tests/test_cards.py` com `Store` temporário e `desktop_sync.service_for(store)` (sem conta,
`store.close()` no `tearDown`): criar/editar/suspender/excluir; cartão novo aparece em `due`;
revisar "Bom" tira de `due` e agenda 1 dia; "Errei" volta amanhã; agenda não conta duas vezes
quando o mesmo evento também aparece como evento do servidor (simule com
`service.projection.apply_event` usando o mesmo id); `stats`. Tela: fumaça com Tk real
(`skipUnless` display) montando painel vazio, com cartões e a revisão, e destruindo sem `after`
pendente.
