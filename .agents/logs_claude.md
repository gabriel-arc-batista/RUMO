# Registro de contexto — Claude

Memória de trabalho do Claude neste projeto. **Leia este arquivo inteiro antes de qualquer tarefa** e atualize-o ao final de cada etapa: seção "Onde paramos", "Histórico" (uma linha por rodada) e "Preferências do usuário" quando ele disser algo novo. Escreva fatos verificados, com data. O usuário não quer reexplicar contexto a cada sessão.

Última atualização: 11/10/2026 14:52.

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
- Mencionou skills "frontend design" e "figma": **não existem** nesta sessão. Aplicar design direto no código e dizer isso com honestidade.

## 3. Direção de design (decidida e implementada)

- Conceito: **RUMO = navegação**. Rosa dos ventos, "N" dourado, viajante. Referências próprias em `docs/RUMO_DESIGN.md`.
- Shell: barra lateral de 230 px em grupos (Estudo / Jornada / Análise), cartão do personagem com `Portrait`; cabeçalho fixo com título, subtítulo (no Início, a frase do dia em uma linha), plano, avisos, **paleta de temas**, ajuda, "Registrar" e a **pílula do relógio** sempre visível.
- `theme.py`: 8 temas — Norte Dourado (original), Alto-Mar, Esmeralda Noturna, Rubi Imperial, Ametista, Brasa (escuros); Aurora, Brisa (claros). `derive()` gera papéis e garante contraste AA (há teste). Valores antigos "Escuro"/"Claro"/"Sistema" continuam válidos.
- `ui.py`: `MotionButton` (variantes + ícone), `Chip`, `Panel` (hover, stretch), `Columns` (responsivo), `ProgressBar`, `Ring`, `MetricCard` (números contam), `EmptyState`, `Toast`, `Tooltip` (fade), `Hover`/`hover_card`, `CharacterView`, `Portrait`, `FocusDial`, `load_image` (LRU para camadas de aparência).
- Ícones: subconjunto Lucide em `assets/fonts/RUMO-Icons.ttf` (`scripts/prepare_icons.py` precisa de `lucide-static@0.460.0` baixado fora do repo).
- Telas que eu desenhei: Início (`screen_home.py`), Jornada (`screen_journey.py`, depois ampliada pelo Codex), modo foco (`focus.py`), seletor de temas (`theme_picker.py`), criador (`customizer.py`). As demais telas só herdam os tokens: **a "etapa 2" (recompor Ciclo, Matérias/Edital, Dificuldades, Revisões, Simulados, Estatísticas, Histórico, Configurações) ainda não foi feita.**

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

## 9. Onde paramos / próximos passos

- Estado: release `v1.0.0` publicada e hashes dos quatro anexos conferidos via API. Árvore limpa após registrar este contexto. Release: https://github.com/gabriel-arc-batista/RUMO/releases/tag/v1.0.0. CI: https://github.com/gabriel-arc-batista/RUMO/actions/runs/38160132817.
- O usuário ainda não avaliou o criador de personagem nem a arte nova: **peça a opinião dele ou espere o feedback**.
- Pendências conhecidas:
  1. **Etapa 2 do redesign**: recompor as telas antigas (Ciclo, Edital/Matérias, Dificuldades, Revisões, Simulados, Estatísticas, Histórico, Metas, Configurações), tirar rolagens aninhadas e os `HH:MM:SS` em tabelas, ajustar as abas no tema claro.
  2. Barba/pelos faciais e mais opções de rosto (provável próximo pedido).
  3. Redesenhar as montarias (cavalo/mula/grifo) no novo traço; coordenar com o Codex.
  4. Validação visual no Windows (DPI, ClearType, fontes privadas): só o workflow do Codex cobre hoje.
  5. Decisões da prévia ainda sem "ok" explícito do usuário: frase do dia só no Início; relógio em pílula no cabeçalho; "Adicionar estudo" → "Registrar". Ele seguiu usando sem reclamar.
