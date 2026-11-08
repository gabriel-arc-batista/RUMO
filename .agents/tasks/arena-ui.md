# Tarefa arena-ui — telas da Arena (DeepSeek)

Leia antes: `AGENTS.md`, `.agents/CONVENTIONS.md`, `.agents/PIPELINE.md`,
`.agents/tasks/arena-logic.md` (contrato do serviço), `screen_reviews.py` e `screen_mocks.py`
(padrão de tela), `ui_kit.py`, `ui.py` (`MotionButton`, `activate_popup`, `Toast`) e
`docs/RUMO_DESIGN.md` (uma ação dourada por tela, Inter, animações finitas).

## Objetivo

A Arena nativa: painel, rodada de questões, editor de questão, importação de pacote e banco.
O serviço `app.arena` (classe `Arena` de `arena.py`) está sendo escrito **ao mesmo tempo**
por outro agente; programe contra o contrato e teste com um serviço falso.

## Arquivos permitidos

- criar `screen_arena.py` — `render(app)`: painel e rodada
- criar `arena_ui.py` — diálogos: editor de questão, importação, banco de questões
- criar `tests/test_screen_arena.py`

Não edite `app.py` (Claude liga a navegação depois). Não acesse `app.store` nem SQL:
use só `app.arena`, `app.plan`, `app.today()`, `app.notify()`, `app.refresh()`,
`app.subject_map()`, `app.topic_map()` e `app.after_arena_session(session_id)`
(este último Claude cria; chame-o depois de `finish_round` devolver um id).

## Telas

1. **Painel** (`render`): `stat_row` com questões, respondidas, aproveitamento e "para refazer"
   (`arena.summary`). Lista de assuntos (`arena.topics`) em `Row`s com total, novas, para refazer
   e ações "Treinar" (modo `novas`, ou `todas` quando não houver novas) e "Refazer erros"
   (só se `to_redo` > 0). `ActionMenu` com "Nova questão", "Importar pacote", "Banco de questões".
   Sem questões: `ui_kit.empty` honesto ("Nenhuma questão ainda…") com "Criar questão" e
   "Importar pacote". Nada de dados de exemplo.
2. **Rodada**: renderizada no próprio `app.content` (sem janela nova). Cabeçalho com assunto e
   progresso `3/10`; tempo decorrido mm:ss (relógio monotônico, atualiza 1×/s com `after`;
   **cancele no `<Destroy>`**). Enunciado com quebra de linha. Certo/Errado ou alternativas como
   botões; teclas `1`–`9`/`c`/`e` respondem. Depois de responder: certo/errado em cor de estado,
   gabarito e comentário, botão "Próxima" (Enter). Anulada: aviso neutro. No fim, ou em
   "Encerrar": `arena.finish_round(round, segundos)`, `app.notify` com acertos/erros e volta ao
   painel. Sair sem responder nada não grava sessão.
3. **Editor** (`arena_ui.edit_question(app, question=None, on_saved=None)`): `Toplevel` com
   `activate_popup`; matéria e assunto, tipo, enunciado (Text), alternativas (adicionar/remover,
   2–10), gabarito, comentário, fonte. Erros do serviço (`ValueError`) aparecem na própria janela.
4. **Importar** (`arena_ui.import_pack(app, on_done=None)`): `filedialog` para `.json`, escolher
   matéria/assunto, chamar `arena.import_pack`, mostrar `added/updated/skipped`.
5. **Banco** (`arena_ui.question_bank(app, topic_id=None)`): lista paginada (30) com busca,
   editar, anular/reativar, retirar (com confirmação).

## Vazamentos

Todo `after` guardado e cancelado no `<Destroy>`; bindings de teclado só no frame da rodada ou
removidos ao sair; janelas `Toplevel` destruídas ao fechar; nenhuma lista global de widgets.

## Aceite (rode e cole o resultado no relatório)

```sh
.venv/bin/python -m black --check screen_arena.py arena_ui.py tests/test_screen_arena.py
.venv/bin/python -W error::ResourceWarning -m unittest tests.test_screen_arena -v
.venv/bin/python -W error::ResourceWarning -m unittest discover -s tests
```

`tests/test_screen_arena.py`: com Tk real (`skipUnless` display), um `App` mínimo falso
(`content`, `bg`, `palette`/o que os componentes exigirem — leia `ui_kit`) e um `FakeArena`
que segue o contrato. Verifique: painel vazio e com dados montam; rodada responde, mostra
correção, encerra chamando `finish_round` uma vez; destruir a tela no meio da rodada não deixa
`after` pendente (`root.tk.call("after", "info")` vazio de ids seus).
