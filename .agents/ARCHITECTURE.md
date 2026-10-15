# Arquitetura

| Módulo | Responsabilidade |
|---|---|
| `core.py` | Store, persistência, consultas, validação de sessões e relógio |
| `storage.py` | Descoberta por esquema, bloqueio e migração aditiva da base anterior |
| `backups.py` | Leitura e validação de backups em isolamento, sem GUI |
| `security.py` | Políticas pequenas para links, pastas, CSV, preferências e relações |
| `app.py` | Aplicação Tk, navegação, formulários e composição das telas |
| `ui.py` | Componentes Canvas, fonte privada, paleta e animações finitas |
| `components.py` | Seleção pesquisável e caixa de conclusão |
| `edital.py` | Árvore preguiçosa de assuntos, seleção e atualizações locais |
| `learning.py` | Ordem pedagógica, próxima folha pendente e ciclo guiado idempotente |
| `syllabus.py` | Expansão aditiva do edital preservando personalização |
| `charts.py` | Gráficos nativos a partir de registros reais |
| `challenges.py` | Catálogo por nível e cálculo de progresso |
| `inspiration.py` | Corpus em cache e frase por data |
| `appearance.py` | Opções, padrão, validação e camadas da aparência do personagem (sem Tk) |
| `customizer.py` | Janela do criador de personagem com prévia ao vivo |
| `theme.py` | Tokens de cor/tipo/espaço, contraste e formatação pt-BR |
| `icons.py` | Mapa gerado dos ícones Lucide (`assets/fonts/RUMO-Icons.ttf`) |
| `journey.py` | Contratos tipados da Jornada (view models + `JourneyProvider`) |
| `journey_live.py` | Leituras reais somente leitura para missão, revisões e habilidades |
| `journey_demo.py` | `PreviewJourney`: prévia com dados de demonstração identificados, sem gravação |
| `screen_home.py`, `screen_journey.py`, `focus.py` | Telas Início, Jornada e modo foco; recebem só view models |
| `ui_kit.py` | Blocos das telas reformadas: `Card` (superfície sem borda), `Section`, `Row` (lista com divisória), `Segmented`, `ActionMenu`, `stat_row`, `empty`, `placeholder` |
| `training_schema.py`, `training_catalog.py`, `training_content.py`, `training.py` | Campo de Treinamento: esquema v6, contrato do catálogo, provedor/downloads, estado de leitura e biblioteca (sem Tk) |
| `pdf_reader.py`, `screen_training.py` | Leitor PDF (pypdfium2 → PPM → Tk) e tela do Campo |
| `screen_reviews.py`, `screen_mocks.py`, `screen_goals.py`, `screen_stats.py` | Revisões, Simulados, Metas e Estatísticas; mesmas consultas e ações do `App`, só a composição é nova |
| `scripts/` | Preparação de assets, QA, build e instalador |

## Contratos que não devem mudar silenciosamente

Store usa SQLite com chaves estrangeiras, WAL e cache de 2 MB. Valores SQL são parâmetros. Identificadores dinâmicos vêm de listas de tabelas/colunas permitidas. `source()` retorna SQL com placeholder quando há filtro de matéria; `source_args()` coloca esse valor antes dos demais parâmetros. Atualizar os cinco consumidores juntos se alterar esse contrato.

Relógio usa tempo monotônico, checkpoints de cinco segundos e tempo líquido. Recuperação fica pausada; ausência/suspensão não conta. Segmentos repartem tempo entre datas, mas questões permanecem na data atribuída à sessão. Um bloco pode receber estudos parciais; concluir/adicionar tempo não equivale a concluir a teoria.

Esquema 5: backups 1, 2 e 3 migram pausas, observações e tabelas RPG vazias, sem conceder XP retroativo. A atualização de SQLite antigo cria uma cópia pre-rpg antes da migração aditiva. Uma restauração é validada numa base temporária antes da transação e preserva o destino local de backups. Não modificar o arquivo SQLite importado.

Hierarquia tem matéria consistente, ausência de ciclos e profundidade máxima de 128. A ordem visual não altera IDs, numeração ou textos oficiais. `starter_cycle_<plan>` garante geração idempotente; `create_guided_cycle` é uma ação pontual de instalação autorizada, não um padrão para todas as bases.

Eventos Tk ficam na thread principal. Cancelar callbacks ao destruir widgets. Não criar timers repetidos para hover. No edital, seleção e conclusão atualizam widgets existentes; reconstruir a página deslocava a rolagem e causava o antigo bug de piscar.

## RPG local

`rpg_schema.py` define tabelas adicionais; `rpg.py` opera na conexão e nas transações do Store; `rpg_validation.py` valida backups sem GUI. `journey_backend.py` adapta contratos de apresentação e `rpg_ui.py` oferece formulários nativos. Sessões e resultados de simulados continuam canônicos. Contexto de missão, dificuldade, desafio e lembrança fica em `rpg_links`, nunca em uma segunda sessão.

Recompensas são recalculadas a partir de fontes únicas: um XP por minuto líquido completo, uma moeda por dez XP de cada sessão; encontros e desafios concluídos recebem cinco XP de participação, sem moedas ou bônus por aproveitamento. Nível L exige 100 × L XP para o seguinte. Edições/exclusões corrigem o saldo; compras permanecem e eventual déficit é compensado por ganhos futuros, mantendo saldo disponível não negativo. História desbloqueada permanece. Estudos anteriores só entram após prévia e opção explícita.

Esforço, aproveitamento observado (20 respostas em três datas) e autoavaliação de lembrança são separados. Superação de dificuldade é decisão do usuário; evidência espaçada apenas sugere. Missões parciais não decidem blocos nem avançam o ciclo.

Telas leem a Jornada só por `app.journey` (`app.make_journey`). Selos de demonstração dependem do campo `source`. `Columns`/`Panel(stretch)` fazem a responsividade; em `grid`, sempre informe `padx` e `pady` ao re-posicionar e retire colunas vazias do grupo `uniform`. Decisões visuais: `docs/RUMO_DESIGN.md`; integração: `docs/RUMO_HANDOFF.md`.

Equipamentos de evolução e caminhos ficam em `rpg_progression.py`; contam apenas fontes canônicas inscritas no RPG. Caminhos são derivados e independentes, não classes obrigatórias. Inventário grava aquisições e preço real (zero para recompensas), preservando-as após correções. Migração v4→v5 reconstrói apenas a restrição de slots do inventário, copia todas as linhas e recria o índice de um item equipado por slot, numa transação precedida de backup. Não acrescentar XP, tempo ou questões por usar equipamentos. Avisos de novas recompensas são transitórios, consumidos uma vez pela interface.

## Personalização com assets externos (11/10/2026)

`appearance.py` mantém IDs antigos e novos em dados puros; `character_profile.py`
salva nome por plano e aparência global, atomicamente nas tabelas existentes.
Não há migração de esquema, concessão de XP nem alteração do inventário.
O pacote de retratos CC0 de N. Erebus substitui a arte procedural da aparência:
`prepare_avatar.py` chama `prepare_portrait_assets.py`, que apenas multiplica
cores em peças isoladas, redimensiona e compõe PNGs originais. Pillow só no build.
Manifesto/proveniência/licenças: `assets/character/look/catalog.json`,
`assets/character/sources/erebus/` e `THIRD_PARTY_ASSETS.md`.
Portrait e CharacterView usam a mesma família de retratos. O pacote não tem
corpo/equipamentos: overlays corporais antigos não são aplicados, mas todos os
itens e a equipagem continuam nas tabelas/controles existentes.
Customizer mantém rascunho, miniaturas reais apenas da categoria aberta e
cache de 24 PNGs; ao fechar descarta imagens de /look/ não usadas por widgets.

## Reforma visual das telas (11/10/2026, Claude)

`App.refresh` tem páginas fixas (`FIXED_PAGES`): o Edital não usa a rolagem da
página; monta árvore (rolagem própria, `app.edital_scroll`) e detalhe lado a lado.
Contratos dos scripts preservados: `edital_rows[tid] = (row, marker, labels)`,
`labels[-2]` título, `labels[-1]` detalhe, lápis por linha, `CompletionBox`,
`edital_branch_buttons`, `edital_search_entry`. O relógio fica num rodapé da coluna
de conteúdo (`app.footer`: status à esquerda, `ClockButton` à direita), nunca sobre
as linhas. `Panel` não desenha borda; o anel de foco de `MotionButton` só aparece
com foco de teclado. Miniaturas do inventário: `scripts/prepare_item_thumbs.py`
recorta as camadas `eq-*.png` existentes em `assets/character/items/{96,64,44}/`.

## Campo de Treinamento (11/10/2026, Claude)

Esquema **v6** aditivo (`training_*`, cópia `pre-campo-*` antes de migrar): posição por (aula, versão), marcadores, notas, favoritos/conclusão manual, `training_session_links` e metadados de PDFs próprios. Catálogo público e PDFs ficam em `<dados>/conteudo/`, fora do banco; remover download não apaga notas. `Store.save_session` aceita `lesson_id/lesson_version` no `context` e grava o vínculo na mesma transação (idempotente pelo ID da sessão do relógio); essas chaves são retiradas antes do RPG. O relógio carrega a aula no estado `active`. Abrir/baixar/concluir leitura não concede XP. Detalhes: `docs/campo-de-treinamento/IMPLEMENTACAO.md`; contratos futuros: `CONTRATOS_ARENA_FLASHCARDS.md`.

## Conta e serviço opcional (12/10/2026, Codex)

Pedido explícito autoriza expansão web; desktop nativo e modo sem conta continuam.
`backend/migrations/` implementa Supabase Auth/PostgreSQL/RLS e RPCs de eventos;
nenhum deploy foi feito. `docs/integration/CONTRACT.md` é a fonte compartilhada,
`shared/rumo-api.ts` é o cliente do frontend Claude (`web/`).
`sync_client.py` usa stdlib HTTPS e SQLite separado `study-sync.sqlite3` (schema
próprio 1): outbox persistida, identidade/dispositivo, histórico remoto e cursor
aplicado transacionalmente. Tokens somente memória. `study_sync.py` projeta
leitura/questões/cartões/revisões; `desktop_sync.py` associa sessões ao Store
canônico e preserva contagens anteriores. `screen_account.py` integra login,
retry, associação de assuntos e backup separado nas configurações Tk; rede em
worker curto, acesso à GUI/Store somente na thread principal. Timer único 60 s
para sync autenticada; cancelar no fechamento. Nada roda sem a aplicação aberta.

Leitura é por página e versão; posição não comprova conclusão. Checkbox nativo
em `pdf_reader.py`. Antiga conclusão manual permanece como `legacy_completed`,
sem assumir páginas lidas. PDFs pessoais permanecem locais. Inventário, compras,
aparência, ciclos, metas, edital e histórico legado não sincronizam implicitamente.
Backups canônicos v1–v6 permanecem compatíveis; workspace exige exportação separada.

Integração de sessões: journal no workspace registra antes/depois das contagens
antes do Store canônico. Retomada confere o resultado gravado e finaliza o baseline
sem duplicar; mudanças intervenientes exigem confirmação explícita em Resolver
conflitos. Totais manuais são separados das tentativas remotas; pending/conflict e
sent de revisão mais nova impedem replay remoto sobre alteração local. Metas,
notas, vínculos de revisão/aula e divisões de simulado são preservados.

## Site (`web/`, 12/10/2026, Claude)

Vite + React + TypeScript, sem SSR. `src/service/` é a fronteira: `contract.ts`
(tipos de `shared/rumo-api.ts` e identidades canônicas de entidade), `sync.ts`
(fila IndexedDB por conta, gravada antes da rede; lote recusado reenviado um a
um; conflito retém a cadeia da entidade até escolha explícita), `supabase.ts`
(Auth + RPC; catálogo pelas tabelas públicas, versão mais recente por
`catalog_revision`) e `example/` (servidor simulado com as mesmas regras do SQL,
usado só sem `VITE_SUPABASE_*`, sempre com selo EXEMPLO). `src/domain/projection.ts`
reconstrói o estado a partir dos eventos aceitos + fila; correção, agenda, XP e
nível vêm de `result`/`progress_summary`, nunca recalculados no navegador. Leitor
pdf.js com render preguiçoso e camada de texto; "Li esta página" por página e na
barra fixa; posição separada da leitura. Decisões em `docs/site/FRONTEND.md`.

Migração 009 e app (12/10, Claude): `push_events` virou adaptador que valida `profile.character`/`cycle.snapshot` e delega o resto a `push_events_core` na mesma transação; `progress_summary` traz aparência, nome, equipados e vitórias. Desktop: `desktop_sync.capture_profile_and_cycle` envia retratos só quando mudam e só após `note_server_features` confirmar a 009; `screen_account.background_sync` reconecta o login lembrado (`token_store.py`) ao abrir e repete a cada minuto. `StudySync.carry_reading` e o aviso do leitor trazem marcações de outra versão apenas com confirmação. Site: `useCharacter`, contexto do ciclo no Início, `Formula` (KaTeX sob demanda), `CarryDialog`.

## Estrutura pedagógica — 15/10/2026

`pedagogy.py` usa preferências `learning_graph_<plan>` para relações locais
essential/recommended/parallel entre IDs existentes, com validação sem ciclos.
`assets/bacen-pedagogy.json` oferece 64 relações padrão por correspondência exata
única de títulos; não altera o edital ou cria conteúdo. `pedagogy_ui.py` edita
relações pelo menu do assunto. `learning.next_topic` orienta blocos sem assunto
fixado; `screen_training` apresenta a próxima sugestão do ciclo e `edital` mostra
os conhecimentos anteriores. Não bloqueia estudo nem concede XP.

`editorial.py` e `scripts/editorial.py` são preparação administrativa local em
SQLite separado, com rascunhos/edições/auditoria. Manifesto preparado não significa
publicado; retirada local não significa retirada remota. Não há migração canônica.
Web pagina catálogos, protege respostas contra repetição e oferece filtros de
conteúdo com leitura concluída. Sessões `subject_id=misto` permanecem no workspace
sem importação para uma única matéria. Limites, diagnóstico e continuação em
`docs/pedagogia/IMPLEMENTACAO.md` e `CONTRATO_EVOLUCAO.md`; não anunciar integração
nativa de Arena/cartões ou sincronização do grafo como concluída.
