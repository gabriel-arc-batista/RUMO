# Tarefa arena-ui-fix — layout da Arena (agy)

Leia antes: `AGENTS.md`, `.agents/CONVENTIONS.md`, `.agents/PIPELINE.md`. A tarefa original
(`arena-ui.md`, DeepSeek) parou por cota; você termina só o layout. Capturas do problema em
`validation/arena-2026-11-08/` (08-editor, 06-correcao-mc, 09-banco).

## Arquivos permitidos

`arena_ui.py`, `screen_arena.py`, `tests/test_screen_arena.py`. Nada mais.

## Corrigir

1. `arena_ui.edit_question`: `_column()` empacota `side="left"`; Tipo e Gabarito criados com
   `_column(body, ...)` ficam soltos ao lado dos campos empilhados. Ordem visual desejada, cada
   linha ocupando a largura toda: Matéria | Assunto; Tipo | Gabarito; Enunciado; Alternativas
   (só múltipla escolha); Comentário; Fonte. Use um frame de linha (como `pair`) para cada par.
2. `screen_arena.RoundView._build_header`: com assunto longo o título empurra progresso e relógio
   para fora. Empacote relógio e progresso à direita **antes** do título e encurte o título
   (até ~80 caracteres com "…").
3. `arena_ui.question_bank`: o detalhe repete o nome completo do assunto (3 linhas). Encurte
   matéria e assunto para ~50 caracteres com "…".

Não desfaça: `TYPING` e a guarda em `_on_key`; ausência de `app.notify` de sucesso em `finish()`;
ícones `search`/`chevron-left`; banco com `include_retired=True` e menu por status; testes
`test_typing_in_a_text_field_never_answers` e `app.notes == []`.

## Aceite

```sh
sh validation/arena-2026-11-08/preview.sh   # base temporária; PNGs em validation/arena-2026-11-08/novo
.venv/bin/python -m black --check screen_arena.py arena_ui.py tests/test_screen_arena.py
.venv/bin/python -W error::ResourceWarning -m unittest tests.test_screen_arena -v
```

Abra os PNGs gerados (08-editor, 03/05/06 da rodada, 09-banco) e confirme no relatório que os
três problemas sumiram. Acrescente um teste para o encurtamento do título.
