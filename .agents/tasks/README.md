# Tarefas

| Id | Agente | Estado | Arquivos |
|---|---|---|---|
| [arena-logic](arena-logic.md) | agy (Sonnet 4.6 → Gemini 3.8 Flash) | **auditada e reescrita pelo Claude** | `arena.py`, `tests/test_arena.py` |
| [arena-ui](arena-ui.md) | DeepSeek → agy ([arena-ui-fix](arena-ui-fix.md)) | **aprovada** (layout pelo agy) | `screen_arena.py`, `arena_ui.py`, `tests/test_screen_arena.py` |
| [cards](cards.md) | GLM → Claude | **concluída pelo Claude** | `cards.py`, `screen_cards.py`, `tests/test_cards.py` |

Feito pelo Claude antes do despacho: esquema v7 (`arena_schema.py`, migração com cópia
`pre-arena-*`, backups v1–v7, gancho `arena_attempts` em `save_session`) e
`tests/test_arena_schema.py`.

Depois: Claude audita cada entrega, liga `app.arena`, `app.cards`, `app.after_arena_session`
e a navegação no `app.py`.

## Auditoria arena-logic (08/11)

Entrega do agy: 665 linhas, 46 testes verdes, mas reprovada. Defeitos: `target` recebia o
número de questões; edição sem transação (sem commit); `finish_round` duas vezes = duas
sessões/XP; pacote malformado gerava `AttributeError`/`TypeError`; versão "1.0.0" quebrava
na edição; N+1 em `topics()`; rodada sem checar plano; `%`/`_` como curinga na busca.
Claude reescreveu `arena.py` (421 linhas, contrato igual) e acrescentou
`ArenaAuditRegressionTests` (6 testes que falham na versão original e passam na atual).
Lição para as próximas tarefas: exigir teste para cada invariante citado na tarefa e não
aceitar "corrigido" sem rodar o teste correspondente.

## Auditoria arena-ui (08/11)

Entrega do DeepSeek: lógica de tela e vazamentos aprovados (timer cancelado no `<Destroy>`,
binds com funcid removidos). Claude corrigiu: teclas da raiz respondiam mesmo digitando em
campos de texto; aviso duplicado ao concluir; ícones inexistentes; banco escondia retiradas
(irreversível pela interface). Captura real (`validation/arena-2026-11-08/`, roteiro
`preview.sh`, base temporária) mostrou editor com layout quebrado, título da rodada
empurrando progresso/relógio e detalhes longos no banco: devolvido ao DeepSeek.

## Cota do opencode (08/11)

DeepSeek e GLM atingiram o limite gratuito do opencode ("Free usage limit reached"; no
DeepSeek apareceu como pop-up de assinatura que bloqueou a tela). Dispatches
`ctx_bc91d4cd0bfa` e `ctx_3acac26c00b0` abandonados para não voltarem a editar.

## Auditoria cards (08/11)

GLM deixou `cards.py` correto (passada única, log local, sem contagem dupla), mas os testes de
tela nunca rodaram (`winfo_descendants` não existe, app falso sem `Motion`) e 4 testes de
domínio tinham expectativas erradas. Claude corrigiu os testes (19 ok), a guarda de teclas em
campos de texto, os botões de avaliação cortados (MotionButton guarda a largura do primeiro
texto: recriados ao revelar) e o editor (linhas inteiras). Capturas 12–17 em
`validation/arena-2026-11-08/`. Pendente: extrair campos de texto/estado repetidos em
`arena_ui.py` e `screen_cards.py` para o `ui_kit`.

## Fechamento do ciclo 1 (08/11)

arena-ui-fix (agy) aprovada: minhas correções preservadas, capturas conferidas pelo Claude
(editor em linhas, título encurtado com relógio/progresso visíveis, banco compacto). Os únicos
`after` restantes após os fluxos são o `tick` do relógio do app e o fechamento do aviso
(`motion.later(..., "toast")`), ambos donos conhecidos. Campos e linha de status repetidos
viraram `ui_kit.field` e `ui_kit.status_line`. 278 testes, `-W error::ResourceWarning`.
