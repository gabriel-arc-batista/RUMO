# Registro de contexto — Claude

Memória de trabalho do Claude neste projeto. **Leia este arquivo inteiro antes de qualquer tarefa** e atualize-o ao final de cada etapa: seção "Onde paramos", "Histórico" (uma linha por rodada) e "Preferências do usuário" quando ele disser algo novo. Escreva fatos verificados, com data. O usuário não quer reexplicar contexto a cada sessão.

Última atualização: 12/10/2026 02:27.

## 1. O projeto em poucas linhas

- **RUMO — Estudos**: app desktop nativo (Python 3.13 + Tk 8.6 + SQLite), local, offline e em pt-BR, para organizar o estudo de concursos de TI (planos BACEN 2024 inclusos como referência). Produto-alvo: **Windows 11**. O usuário desenvolve e testa no **Linux (Ubuntu 26.04, GNOME/Wayland)**.
- Núcleo: ciclo de estudos (fila contínua, sem agenda rígida), edital/assuntos, relógio de foco (tempo líquido, pausas não contam), revisões espaçadas, simulados, estatísticas, histórico, metas, backups v1–v5.
- Camada de **RPG integrada** (motor do Codex): XP por minuto líquido, níveis, moedas, classes (Paladino, Guerreiro, Mago, Cartógrafo, Ladino, Erudito), missões vindas do ciclo, "Hoje está difícil", dificuldades e revanche, masmorras e chefes (simulados), equipamentos **só decorativos**, história em capítulos. Sem multiplayer, sem servidor, sem dinheiro real, sem punição por faltar.
- Versão publicada: **1.0.0**, tag `v1.0.0`, esquema SQLite 5. Frontend e motor real integrados; 118 testes e CI Windows aprovados. Instalador, ZIP Windows, tar.gz Linux e hashes anexados. Repositório privado `gabriel-arc-batista/RUMO`.
- Regras permanentes em `AGENTS.md` e `.agents/*.md`: baixa RAM, preservar dados/IDs/backups, não usar o banco pessoal em testes, Black, mudanças pequenas e validadas, nada de Electron/web embutido.

## 2. Como o usuário quer as coisas

- Fala português, mensagens curtas e informais. Quer que eu **aja**, não que pergunte o óbvio, e que eu **mostre** o resultado (rodar o app, capturas de tela).
- **Identidade visual:** preto/grafite e **dourado** é a origem (tema "**Norte Dourado**"). Ele gosta de temas nomeados com uma terceira cor que combine. Dourado moderado: uma ação dourada por tela, nada de neon nem excesso.
- **Fonte única: Inter** em tudo. Ele percebeu e reclamou quando partes usaram outra fonte (fontes nomeadas do Tk em Noto Sans).
- **Animações:** quer bastante animação de hover e transição, mas finitas, sem laço e desligáveis nas preferências.
- **Personagem:** nada cartunesco ("parece boneco do Bomba Patch do PS2"). Quer humano e crível, nunca "morto-vivo" (rosto escuro com olhos brilhando foi rejeitado). Progressão no estilo **Bannerlord/Kenshi**: nível 1 = roupa simples de mendigo e **uma** arma tosca; nada de "roupa de assassino top" ou espada bonita no começo. **Armas sempre na mão.**
- Quer **criação de personagem**: sexo, pele, olhos (tipo e cor), cabelo (tipo e cor), sobrancelhas, orelhas. Pedidos prováveis a seguir: barba/pelos faciais, montarias melhores.
- Cuida dos detalhes do sistema: ícone certo no dock do Linux, atalho na área de trabalho.
- Pediu explicitamente que eu crie **minhas próprias referências** de design, sem as antigas (Estudei/Linear/Material 3).
- Skills de design: `frontend-design` (em `.claude/skills`) e **Impeccable** (em `~/.agents/skills/impeccable`, instalada para o Codex; tem `scripts/impeccable context` e `reference/craft-floor.md`). São web; aplicar os princípios ao Tk e dizer isso.
- **Codex em paralelo (11/10 15:58):** não deixar de fazer nenhuma parte por ser "do Codex". Se ele estiver editando o arquivo necessário (mtime recente, aviso em `docs/RUMO_HANDOFF.md` ou `.agents/CHARACTER_WORK.md`), **esperar ele terminar** e então fazer.
- Quer temas de **três cores** (fundo, principal, companheira); o original é preto + ouro + verdete.

## 3. Direção de design (decidida e implementada)

- Conceito: **RUMO = navegação**. Rosa dos ventos, "N" dourado, viajante. Referências próprias em `docs/RUMO_DESIGN.md`.
- Shell: barra lateral de 230 px em grupos (Estudo / Jornada / Análise), cartão do personagem com `Portrait`; cabeçalho fixo com título, subtítulo (no Início, a frase do dia em uma linha), plano, avisos, **paleta de temas**, ajuda, "Registrar" e a **pílula do relógio** sempre visível.
- `theme.py`: (desatualizado, ver seção 3b) 8 temas — Norte Dourado (original), Alto-Mar, Esmeralda Noturna, Rubi Imperial, Ametista, Brasa (escuros); Aurora, Brisa (claros). `derive()` gera papéis e garante contraste AA (há teste). Valores antigos "Escuro"/"Claro"/"Sistema" continuam válidos.
- `ui.py`: `MotionButton` (variantes + ícone), `Chip`, `Panel` (hover, stretch), `Columns` (responsivo), `ProgressBar`, `Ring`, `MetricCard` (números contam), `EmptyState`, `Toast`, `Tooltip` (fade), `Hover`/`hover_card`, `CharacterView`, `Portrait`, `FocusDial`, `load_image` (LRU para camadas de aparência).
- Ícones: subconjunto Lucide em `assets/fonts/RUMO-Icons.ttf` (`scripts/prepare_icons.py` precisa de `lucide-static@0.460.0` baixado fora do repo).
- Telas que eu desenhei: Início (`screen_home.py`), Jornada (`screen_journey.py`, depois ampliada pelo Codex), modo foco (`focus.py`), seletor de temas (`theme_picker.py`), criador (`customizer.py`). As demais telas só herdam os tokens: **a "etapa 2" (recompor Ciclo, Matérias/Edital, Dificuldades, Revisões, Simulados, Estatísticas, Histórico, Configurações) ainda não foi feita.**

## 3b. Reforma das telas (kit `reforma_front/`, 11/10 16:40)

- Kit em `reforma_front/RUMO-kit-reforma-frontend/rumo-design-kit/` (prompt, diagnóstico das 7 telas, referências Linear/Things/Raycast/TickTick/Habitica). Mapa das ações movidas e sistema em `docs/RUMO_DESIGN.md`.
- **13 temas** de três cores; novos: Nórdico, Menta e Coral (escuros), Sálvia, Pergaminho, Cobalto (claros). `derive(..., ink=)` para cor principal escura. Seletor em grupos Escuros/Claros com rolagem.
- `ui_kit.py`: `Card`, `Section`, `Row`, `Segmented`, `ActionMenu`, `stat_row`, `empty`, `placeholder`, `help_button`. `Panel` sem borda; foco visível só por teclado.
- Telas novas: `screen_reviews.py`, `screen_mocks.py`, `screen_goals.py`, `screen_stats.py`; Início, Edital (árvore + detalhe, página fixa `FIXED_PAGES`, rolagem `app.edital_scroll`) e Jornada (inventário com miniaturas `assets/character/items/{96,64,44}` de `scripts/prepare_item_thumbs.py`) recompostos.
- Relógio saiu do cabeçalho para o **rodapé** da coluna de conteúdo (status à esquerda). Frase do dia no fim do Início; subtítulo do Início = data.
- Harness: `scratchpad/harness.py` aceita passos por tela (`inicio edital edital-sel revisoes simulados jornada metas estatisticas ciclo historico config`, `full-<tela>` com `FRACTIONS=`, `empty`, `themes`). `scratchpad/smoke.py` = 36 verificações de fluxo. Venv com psutil.

## 3c. Campo de Treinamento (11/10 18:10)

- Pacote do usuário em `RUMO-campo-de-treinamento-pesquisa-e-prompts/` (copiado para `docs/campo-de-treinamento/`). Implementado: esquema v6, catálogo local/HTTPS, downloads verificados, leitor pypdfium2 embutido (página única, LRU 3), notas/marcadores por versão, "Estudar esta aula" no relógio existente, PDFs próprios, planejamento (60 famílias/267 aulas) e 9 programas extraídos (907 itens, pendentes). Ver `docs/campo-de-treinamento/IMPLEMENTACAO.md`.
- Testar: aponte a fonte local para `tests/fixtures/campo-teste` (material de TESTE). Scripts de captura: `scratchpad/campo_flow.py` (19 verificações ponta a ponta) e `campo_views.py`.
- Editais oficiais baixados ficam fora do repo (`scratchpad/editais/`); a Caixa exige cookie (`curl -c/-b`).
- Pendências: build Windows no workflow; hospedagem real do catálogo (GitHub Pages + Releases, ver PUBLICACAO.md); conferência humana dos itens; retificações de BB/Caixa/UFABC/SERPRO/DATAPREV/STN; primeira trilha real de bancos de dados (PROMPT_CRIACAO_AULAS.md); Arena/flashcards só documentados.

## 4. Personagem (arte por código, Pillow só no build)

- `appearance.py`: opções, padrão (masculino, morena clara, curto clássico, castanho-escuro, amendoado, castanho, naturais, arredondadas), `validate_look`, `normalize`, `layers()`. Preferência `character_look`, validada em `security.py`.
- `scripts/prepare_avatar.py`: 264 camadas × 2 escalas (`assets/character/look/full` 240×304 e `bust` 264×264), splines, luz do alto à esquerda, ~2 min com 8 núcleos. **Âncoras na grade 300×380:** rosto x 126–174 / y 73–137, olhos y 104 (x 140,5 e 159,5), sobrancelhas y ~97, orelhas x ~121/179, pescoço y 124–153, ombros y 148, mãos **(97, 249) e (203, 249)**, pés y 322–350.
- Armas e lanterna ficam **atrás** do corpo, para a mão (na pele escolhida) cobrir o cabo (`HELD` em `ui.py`). Elmo/capuz/cachecol ajustados à cabeça menor. `base.png` = aparência padrão.
- Equipamentos, roupas, armaduras e montarias: arte e catálogo do **Codex** (`scripts/prepare_rpg_equipment.py`, `rpg_progression.py`). A montaria cavalo parece uma lhama; ainda não foi refeita.

## 5. Trabalho em paralelo com o Codex

- O Codex cuida do backend/regras (`core.py`, `rpg*.py`, `journey_backend.py`, `backups.py`, `storage.py`), da integração e das releases. Eu cuido do frontend, design, assets e comportamento visual.
- Coordenação: um aviso no **topo de `docs/RUMO_HANDOFF.md`** ("Em andamento (Claude…)" → "Concluído…"), listando os arquivos que vou mexer. O contrato dele fica em `docs/RUMO_BACKEND_CONTRACT.md`.
- Ele edita ao mesmo tempo e roda Black no repositório: antes de editar, **confira o mtime** dos arquivos e faça edições pequenas e atômicas. **Nunca rode `black .` no repo inteiro**; formate só os arquivos que você tocou.
- Ele já integrou coisas antes da revisão do usuário. Não brigue com isso: registre e informe ao usuário.

## 6. Ambiente e comandos (Linux do usuário)

- O Python do `uv` (`/tmp/rumo-tools/uv`, Python 3.13) tem Tk **sem Xft** e renderiza fontes bitmap: não serve para validação visual.
- Runtime visual estável: `~/.local/share/rumo-runtime/` (Tk 8.6.17 do Ubuntu extraído de `python3-tk`, `libtk8.6`, `libtcl8.6`) + `/usr/bin/python3.14`. O launcher é `~/.local/share/rumo-runtime/rumo.sh` (roda `app.py` da pasta do projeto). **Não passe argumentos achando que é ajuda: ele abre o app de verdade.**
- Atalhos: `~/Área de trabalho/RUMO.desktop` e `~/.local/share/applications/rumo.desktop`, ambos com `StartupWMClass=Rumo` (o Tk normaliza `className="RUMO"` para "Rumo"). Ícone `assets/RUMO.png`.
- **Dados reais do usuário: `~/.local/share/RUMO`** (existe desde 11/10 13:14). Nunca usar em testes: use `RUMO_DATA=$(mktemp -d)`.
- Validação visual: harness próprio (o scratchpad é temporário; recrie se sumir). Ele usa base temporária, semeia sessões sintéticas, navega pelas telas e captura só a janela com python-xlib (`get_image` no `wm_frame()`), salvando PNG com Pillow. Venv com Pillow, python-xlib, black 26.10.1, bandit e fonttools para o Python 3.14 do sistema, mais as variáveis `LD_LIBRARY_PATH`/`TCL_LIBRARY`/`TK_LIBRARY`/`PYTHONPATH` iguais às do `rumo.sh`.
- Checagens: `python -m unittest discover -s tests` (118 na v1), `python -m black --check <arquivos tocados>`, `python scripts/check_repository.py`, Bandit nos módulos alterados. Os scripts `verify_*.py` antigos são só Windows; os novos do Codex (`verify_rpg_gui.py`, `verify_appearance_gui.py`…) rodam no Linux.
- `RUMO_JOURNEY=preview` mostra a Jornada com dados fictícios identificados (o padrão é o motor real).

## 7. Armadilhas já encontradas (não repetir)

- Fontes nomeadas do Tk (`TkDefaultFont`, `TkTextFont`…) precisam ser configuradas para Inter (`apply_theme`).
- fontconfig guarda cache por pasta: carregue as fontes **arquivo por arquivo** (`FcConfigAppFontAddFile`), ou um ícone novo não aparece.
- `grid` mantém opções de chamadas anteriores: ao re-posicionar, sempre passe `padx` **e** `pady`. Em grupo `uniform`, coluna com peso 0 conta como 1: tire colunas vazias do grupo.
- `wraplength` ligado ao `<Configure>` de um rótulo sem `fill` cria laço de encolhimento.
- `Motion.reveal` trava o tamanho da janela: use `max(winfo_*, winfo_req*)`.
- `grab_set` antes de a janela ficar visível falha no Linux: o Codex criou `activate_popup`.
- `Portrait` tem máscara circular "assada" na cor de fundo: o `hover_card` não pode repintá-lo (`static_bg`).
- Hover em tk.Frame com filhos: use `ui.Hover` (checa o ponteiro antes de sair) para não piscar.
- Harness lento depois do motor RPG (cada sessão sintética gera recompensas): use timeouts de 250–300 s ou lotes menores.

## 8. Histórico

- **11/10 ~10:30** — Diagnóstico do visual antigo. Prévia do redesign (Início, relógio, Jornada) com tokens, componentes, ícones, personagem encapuzado e contratos `journey.py` + prévia isolada. Docs `RUMO_DESIGN.md`/`RUMO_HANDOFF.md`. Parei para revisão.
- **~11:30** — O Codex integrou o motor real nas telas antes da revisão. Corrigi o rodapé cortado do modo foco (`reveal`). Capturas em `validation/design-preview-2026-10-11/`.
- **~13:00** — Usuário: "rode pra eu ver" (abri com dados sintéticos) e pediu atalho na área de trabalho (runtime estável + `.desktop`).
- **~13:20** — Pedidos: fonte inconsistente, temas nomeados, mais animações, cosméticos, ícone no dock. Feito: Inter em tudo, 8 temas + seletor, animações, ícones por item, WM_CLASS. Os cosméticos ficaram com o Codex.
- **~13:40** — Usuário: nível 1 parecia assassino/morto-vivo e a espada flutuava. Refiz o nível 1 como humano maltrapilho com lâmina enferrujada na mão.
- **~14:00** — Criador de personagem completo + arte menos cartunesca (retrato 264 px). 117 testes ok.
- **14:18** — O Codex enviou a integração da **1.0.0** ao GitHub (commit + push); a release aguardou a validação Windows.
- **14:30** — Criado este registro.

- **11/10/2026 14:51 (Codex)** — Revisão final: corrigidos fonts no Windows, seletores, cache de imagens e edital Linux. 118 testes, fluxos antigos/novos e instalação aprovados; preparando publicação dos pacotes.

- **11/10/2026 14:52 (Codex)** — Release `v1.0.0` publicada, quatro anexos com SHA-256 conferido no GitHub; contexto do Claude preservado e sincronizado. Nenhum banco pessoal usado.

- **11/10 16:40** — Reforma das 7 telas pelo kit (Início, Edital, Revisões, Simulados, Jornada, Metas, Estatísticas), 13 temas de 3 cores, componentes `ui_kit`, miniaturas reais no inventário. Em paralelo o Codex trocou o personagem por retratos CC0 (Erebus) e tirou equipamentos do corpo. 121 testes, verify_rpg_gui/dialogs/appearance e fumaça de 36 passos ok. Capturas e comparações em `validation/reforma-2026-10-11/`. Nada commitado.

- **11/10 18:10** — Campo de Treinamento completo (pedido do usuário via pacote): v6, leitor, catálogo/downloads, auditoria dos 9 editais, docs de publicação e contratos Arena/flashcards. 133 testes, verify_* e fluxo real 19/19. Capturas em `validation/campo-2026-10-11/`. Nada commitado.

- **12/10 00:50–02:27** — Conectei Vercel e Supabase ao Claude (MCP + CLIs do Codex). Construí o **site** em `web/` a pedido do usuário (Campo/leitor PDF, Arena, Flashcards, conta/sincronização) com o Codex fazendo serviço e contrato. Alinhei ao contrato v1 (versões string, favoritos canônicos, `bookmark`, notas de questão, `progress_summary`). 17 testes, Chrome 40/40 (exemplo e serviço real local), 16/16 extras, ida e volta com o cliente do desktop. Handoff em `.agents/SITE_WORK.md`. Nada publicado.

## 9. Onde paramos / o que falta fazer

Atualizado em 12/10/2026. Release publicada: `v1.0.0` (https://github.com/gabriel-arc-batista/RUMO/releases/tag/v1.0.0).

**Estado:** muitas mudanças **sem commit** desde a v1.0.0: reforma das 7 telas, 13 temas, Campo de Treinamento (esquema v6), retratos do Codex. O Codex costuma integrar e commitar; combinar com ele antes. Nenhum banco pessoal foi usado em testes. A base real do usuário migra para v6 na próxima abertura, com cópia `pre-campo-*`.

**Aguardando o usuário avaliar:** a reforma das telas (`validation/reforma-2026-10-11/`), o Campo de Treinamento (`validation/campo-2026-10-11/`) e os retratos novos do Codex. Peça a opinião ou espere o retorno antes de mudar a direção.

### O que falta, por prioridade

**Campo de Treinamento**
1. Conferir o **build Windows** no workflow (`.github/workflows/rumo-windows.yml`): o leitor com pypdfium2/PDFium no executável. O build Linux já inclui `libpdfium.so` e abre.
2. **Hospedagem real do catálogo:** criar o repositório público de conteúdo, Pages e Releases, seguindo `docs/campo-de-treinamento/PUBLICACAO.md`, e configurar a fonte remota no app. Hoje só o modo local foi testado de verdade; o remoto, com respostas simuladas.
3. **Primeira trilha real de bancos de dados:** produzir aula por aula com `PROMPT_CRIACAO_AULAS.md`, com revisão humana identificada, e validar no leitor. Nunca marcar como revisado sem revisor real.
4. **Conferência humana dos 907 itens** extraídos (`docs/campo-de-treinamento/auditoria/`). Decidir a hierarquia dos blocos sem numeração (Caixa Inglês, UFABC) e o caso BACEN "10.3.x" dentro do 1.3. As lacunas do STN são do próprio edital.
5. Conferir **retificações posteriores** de BB, Caixa, UFABC, SERPRO, DATAPREV e STN. TSE e BACEN estão consolidados até a RET_4; o Senado, até a retificação 2.
6. **Matriz editorial item ↔ aula/versão:** a cobertura só pode ser declarada depois disso e de aulas publicadas.
7. **Arena e flashcards:** só os contratos estão em `CONTRATOS_ARENA_FLASHCARDS.md`; implementar depois da trilha real.

**Interface**
8. Recompor **Ciclo** (tabela ainda com `HH:MM:SS`), **Histórico**, **Configurações** e o **formulário de registro de estudo**; hoje só herdaram tokens e painéis.
9. Validação visual no **Windows** (DPI, ClearType, fontes privadas); escala de sistema acima de 100% não testada.
10. Decisões ainda sem "ok" explícito do usuário: frase do dia no fim do Início, relógio no rodapé e "Registrar estudo" no cabeçalho.

**Personagem (coordenar com o Codex, que trocou a arte por retratos CC0 Erebus)**
11. Barba e pelos faciais e mais opções de rosto (pedido provável).
12. Montarias e equipamento no corpo: o retrato novo não desenha equipamento; os itens aparecem só como miniaturas no inventário. Decidir com o usuário se quer de volta uma figura de corpo inteiro.

**Integrações externas (12/10/2026)**
13. Vercel e Supabase preparados para uso pelo Claude: MCP `vercel` (https://mcp.vercel.com) e `supabase` (https://mcp.supabase.com/mcp) adicionados no escopo do usuário (`~/.claude.json`, fora do repositório). CLIs `vercel` 63.1.2 e `supabase` 2.120.0 vêm da instalação do Codex em `~/.local/share/codex-cloud-tools` (links em `~/.local/bin`); não reinstalar. Vercel CLI logada como `chessrex39-max`; os dois MCP autenticados por OAuth (`claude mcp login <nome>`, que só funciona em TTY). Pendente: `supabase login` do CLI, só necessário para Supabase local. O app continua local e offline; qualquer uso de Vercel/Supabase no RUMO muda `ARCHITECTURE.md`/`SECURITY.md` e precisa de combinação prévia.

## Integração opcional — etapa Codex, 12/10/2026

Implementado serviço local testável Supabase/PostgreSQL em `backend/migrations/001–006`,
RLS/RPC, eventos idempotentes/CAS, gabarito privado, catálogos editoriais e SM-2.
Contratos `docs/integration/CONTRACT.md`, `shared/rumo-api.ts`; execução/publicação
`docs/integration/SETUP.md`. Divisão e respostas ao Claude em `.agents/SITE_WORK.md`
e `.agents/WEB_INTEGRATION.md`. Frontend `web/` continua exclusivo do Claude.

Desktop: fila SQLite separada `study-sync.sqlite3`, opt-in/conta/tokens só memória,
Configurações com login/retry/conflitos/associação de sessões/exportação separada;
checkbox “Li esta página” no leitor. Preservados schema/backups desktop v1–v6 e
conclusão manual antiga como histórico, sem assumir páginas lidas. Conta não é
obrigatória, dados legados não são enviados automaticamente. PDFs pessoais,
inventário, cosméticos/ciclos/edital/metas continuam locais.

Validações: suíte Python (150 descobertos, um teste Docker opt-in separado),
PostgreSQL 16 real/Docker, fluxo de dois dispositivos e três áreas com importação
Store/RPG, GUI nativa temporária, Black/TypeScript compartilhado e revisão Bandit.
O fluxo integrado SQL usa Auth simulado (não PostgREST/login hospedado).
Nenhum banco pessoal, deploy, commit ou push. Frontend ainda em desenvolvimento:
precisa usar versão string, entidade canônica de favorito, `plan_id:"site"` e
`catalog_revision`, conforme respostas em SITE_WORK. Não declarar navegador ou
Auth real integrados antes da verificação conjunta.

## 12/10/2026 — preparação da integração e release 2.0.0
Usuário autorizou concluir/integrar/subir. Latest GitHub conferido v1.0.0;
versão preparada no installer 2.0.0. Sem publicação ainda. Backend auditado com
GoTrue real + PostgREST em Docker local descartável; 007 move RPC privilegiadas
para esquema privado. Notas de questões seguem contrato compartilhado.
Fila agora protege drafts pessoais com shareable persistente, savepoints,
conflitos persistentes e rejeição de chaves privilegiadas. UI filtra drafts,
logout falho remove transporte. Importador preserva notas/meta/resultados e
recusa sobrescrever alterações pendentes/conflitos; revisão adicional de sent e
contagens manuais em andamento. Build Linux isolado + QA temporário em andamento.
Frontend Claude ainda em uso, tipos compilam mas npm test não encontrou testes;
versões numéricas/favoritos/page devem alinhar antes de deploy. Solicitação
explícita da organização Supabase está pendente por exigência create_project;
não criar/modificar projetos existentes de outros produtos.

Complemento: journal durável de contagens concluído e 37 testes específicos
aprovados. Falhas antes/depois Store e na finalização recuperadas sem duplicação.
Resolver conflitos também permite confirmação de totais intervenientes. Backend
HTTP/Auth e CLI Supabase real local aprovados (7 migrações; replay CLI sem DDL).
Build Linux inicial passou, pacote abriu sem env Tk com base temporária íntegra;
rebuild final necessário após journal/UI. Fonte revisada com Black completo.

## Site do RUMO (Claude, 12/10/2026 02:27)

- Código em `web/` (meu); serviço/contrato do Codex em `backend/`, `shared/`, `docs/integration/`. Coordenação em `.agents/SITE_WORK.md` (pedidos, respostas, handoff) e `.agents/WEB_INTEGRATION.md` (Codex).
- Supabase de produção criado pelo Codex no plano gratuito (projeto RUMO, `dfxzxnrttppoonywfzwd`, custo zero exigido pelo usuário; nunca contratar plano pago). Catálogo vazio: não semear exemplos lá. Vercel: conta `chessrex39-max` (Hobby). Publicação conduzida pelo Codex depois do meu handoff.
- Validar: `cd web && npm test && npm run e2e`; com Docker, `npm run servico:up`, `npm run build:servico`, `npm run preview:servico` (4175) e `npm run e2e:servico`. O disco do usuário está quase cheio (~2 GB livres): não usar `supabase start` completo.
- Armadilhas: `new URL(..., import.meta.url).pathname` codifica o "Á" da pasta (usar `fileURLToPath`); `scrollIntoView` no leitor rola a janela (rolar só o contêiner); GoTrue já manda CORS (no gateway, `proxy_hide_header`); checkbox controlado precisa de atualização otimista; motor de sync precisa recomputar a projeção ao abrir.
- Pendências: teste no Supabase hospedado e na Vercel (Codex), Firefox/Safari/Windows/leitor de tela, fórmulas sem LaTeX, aparência/ciclo não sincronizam.

## Revisão integrada e publicação — 12/10/2026
Frontend entregue pelo Claude e congelado após correções: 31 unitários, tipos/build, Chrome serviço real40/40+16/16 e bridge desktop↔site aprovados. GitHub main recebeu caa7302. Site https://rumo-estudos.vercel.app publicado na Vercel Hobby e validado por HTTPS com conta temporária: login, catálogos vazios, cartão remoto em outro contexto, reload/logout; cleanup confirmado users0/events0. Supabase RUMO permanece Free sem plano pago/SMTP externo. CI Windows38266129648 encontrou SQLite aberto no teardownTraining; corrigir e repetir antes de release. Nenhum banco pessoal usado. Estes resultados substituem os status pendentes anteriores relativos ao frontend/deploy.
