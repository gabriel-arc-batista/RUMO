# Convenções de código

Valem para qualquer agente (Claude, Codex, agy, opencode). Complementam `AGENTS.md`,
`ARCHITECTURE.md`, `SECURITY.md` e `TESTING.md`; em conflito, vale o mais restritivo.

## Camadas e responsabilidade única

| Camada | Arquivos | Pode | Não pode |
|---|---|---|---|
| Esquema | `*_schema.py` | DDL, listas de tabelas, primitivas de gravação sem commit, validação de backup | Regra de negócio, Tk |
| Domínio | `core.py`, `rpg.py`, `learning.py`, `arena.py`, `cards.py`… | Regras, validação, consultas parametrizadas, transações | Importar `tkinter`, `ui*`, `screen_*` |
| Tela | `screen_*.py`, `*_ui.py` | Compor widgets de `ui.py`/`ui_kit.py`, chamar o domínio | SQL, `store.db`, regras, cálculo de XP |
| Shell | `app.py` | Navegação, ligação tela ↔ domínio | Lógica nova; só ligação. Dono: Claude |

- Uma função faz uma coisa. Prefira funções de até ~30 linhas; módulo novo com uma responsabilidade clara.
- **Aberto/fechado:** acrescente módulos e funções; não reescreva contratos existentes. Mudança de contrato só com nota em `ARCHITECTURE.md`.
- **Inversão de dependência:** telas recebem o serviço pronto (`app.arena`, `app.cards`) e nunca o constroem; isso permite testar com um serviço falso.
- **Interfaces pequenas:** o serviço expõe só o que a tela usa. Dicionários simples ou `dataclass(frozen=True)` na fronteira.
- Nada de herança profunda; composição e funções puras.

## Código enxuto

- Sem dependências novas de runtime. Biblioteca padrão + o que já está em `requirements-dev.txt`.
- Sem código morto, sem `print`, sem comentários óbvios. Docstring de uma linha quando o porquê não é evidente.
- Não duplique: procure helper existente (`theme.fmt_*`, `ui_kit.*`, `Store.one/all/save`) antes de escrever outro.
- Consultas: parâmetros `?` sempre; nunca formatar valores em SQL. Identificadores dinâmicos só de listas permitidas.
- Black (formatar **só os arquivos tocados**, nunca `black .`). Nomes em inglês no código, textos visíveis em pt-BR.

## Vazamentos (checklist obrigatório)

- **Tk `after`:** guarde o id e cancele (`after_cancel`) no `<Destroy>` do widget dono. Nenhum laço periódico sem condição de parada. Animações finitas.
- **Bindings:** `bind_all`/`bind` na raiz precisam de `unbind` ao sair da tela. Prefira `bind` no próprio widget.
- **Imagens:** `PhotoImage` mantidas por referência só enquanto o widget vive; caches com limite (LRU). Nada de lista global que só cresce.
- **SQLite:** conexões fora do `Store` são fechadas em `finally`/`with closing`. Em testes, `self.addCleanup(db.close)` ou `store.close()`.
- **Arquivos:** sempre `with open(...)`. Gravação atômica (temporário + `replace`) para dados do usuário.
- **Threads:** só para rede/IO curto, `daemon=True`, sem tocar Tk ou `Store` fora da thread principal; resultado por `queue` + `after`.
- **Listeners:** quem se inscreve em `app.clock_listeners` (ou similar) se remove no `<Destroy>`.
- Rode os testes com `-W error::ResourceWarning` nos módulos tocados.

## Dados do usuário

- Nunca abrir `~/.local/share/RUMO` (ou `%LOCALAPPDATA%/RUMO`). Testes com `tempfile`/`RUMO_DATA` temporário.
- Migração só aditiva, com cópia `pre-*` antes, e backup v1–vN continua aceito. Migrações são do Claude.
- Não inventar conteúdo (questões, aulas, gabaritos). Estado vazio honesto, sem parecer pronto.

## Testes

- Todo comportamento novo tem teste em `tests/test_<módulo>.py` (unittest, base temporária).
- Caso feliz, entrada inválida e o invariante que protege dados (idempotência, transação, não duplicar).
- Telas: teste de fumaça com Tk real quando houver display (`skipUnless`), serviço falso, verificando que montam e destroem sem erro.
