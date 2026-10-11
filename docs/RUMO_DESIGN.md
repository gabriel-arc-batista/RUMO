# RUMO — linguagem visual

Etapa 1 (prévia para revisão): shell, Início, estudo com relógio e Jornada. As demais telas já herdam tokens, campos, botões e tipografia, mas a recomposição delas fica para a etapa 2, após aprovação.

## Diagnóstico da versão anterior

- Faltava uma ação principal. O próximo estudo ficava abaixo da dobra; o topo era ocupado por frase, quatro botões de mesmo peso e indicadores.
- O cabeçalho com frase e a barra de status consumiam cerca de 180 px em todas as telas, e o relógio ocupava um rodapé próprio.
- O dourado aparecia saturado em blocos grandes, como os dias de constância. Os títulos alternavam entre maiúsculas e minúsculas, e a marca aparecia como "rumo".
- Ícones Unicode viravam quadrados vazios em parte das fontes. Tempos em `HH:MM:SS` e números como `1.02472` no gráfico dificultavam a leitura.
- No relógio, "Descartar" ficava ao lado de "+15 min": ação destrutiva misturada com ações comuns.

## Direção e referências próprias

**RUMO é direção.** O motivo da marca é a navegação: rosa dos ventos, marcações de rumo, trilha. O personagem é um viajante, e os equipamentos são objetos de viagem. As referências abaixo orientam princípios; nenhum ativo, marca ou componente foi copiado.

| Referência | O que inspirou |
|---|---|
| Cartas náuticas e rosas dos ventos | Linhas finas e marcações de rumo: palco do personagem, marcas de minuto do relógio e ícone da marca. |
| HUDs contidos de jogos de ação (ex.: Hades, Supergiant Games) | Dourado como fio e sinal, não como preenchimento; personalidade concentrada no personagem. |
| Anéis de atividade (Apple Fitness) | Progresso em anel calmo e metas alcançáveis, sem punição. |
| Things 3 (Cultured Code) | Uma ação principal por tela, respiro, listas sem ruído. |
| Trilhas de aprendizado em linha do tempo | Capítulos da história como trilha vertical com estados claros. |

## Princípios

1. **Uma ação dourada por tela.** No Início, é "Começar missão"; o relógio do topo fica neutro até haver uma sessão ativa.
2. **O dourado sinaliza.** Ele marca seleção, progresso e o principal. As superfícies são grafite em camadas.
3. **Esforço ≠ desempenho.** O tempo usa barra dourada e ícone de relógio; o desempenho usa barra azul e ícone de alvo. Horas nunca afirmam domínio.
4. **Demonstração sempre identificada.** O selo DEMONSTRAÇÃO e a faixa de aviso aparecem apenas quando o dado tem `source="demo"`.
5. **Estado nunca só por cor.** Sempre há ícone ou texto: "EM FOCO"/"PAUSADO", "Equipado"/"Guardado", "concluída", "bloqueado".
6. **Movimento finito.** Há entrada de página, barras e anéis que se preenchem uma vez, transições de hover e toast deslizante. Nada fica em laço; tudo respeita "Animações" nas preferências.
7. **Sem punição.** Faltar um dia não remove nada; nenhuma conquista exige estudar tarde.

## Tokens (`theme.py`)

As telas usam nomes de papel, nunca hex. O contraste é verificado em `tests/test_journey.py` (WCAG AA ≥ 4,5:1 para todo texto sobre `bg`, `surface`, `raised` e `sidebar`, nos dois temas).

| Papel | Escuro | Claro | Uso |
|---|---|---|---|
| `bg` / `sidebar` | `#0E0E11` / `#121215` | `#F4F2ED` / `#ECE9E2` | Fundo da janela e da navegação |
| `surface` / `raised` | `#18181C` / `#1F1F24` | `#FFFFFF` / `#F8F6F1` | Cartões / campos, blocos internos |
| `border` / `strong` | `#2A2A31` / `#3B3B45` | `#E2DDD2` / `#CBC4B6` | Bordas / hover de borda, scrollbar |
| `fg` / `muted` / `faint` | `#ECE8E0` / `#A3A0A8` / `#8A8792` | `#1F1D1A` / `#5F5B54` / `#6B665D` | Texto |
| `accent` | `#D4B26A` | `#7D5E17` | Texto e ícone dourados |
| `primary` / `primary_ink` | `#CBA65A` / `#17130B` | `#C9A24F` / `#1C170C` | Botão principal, barras e anéis |
| `tint` / `selected` | `#2A2418` / `#241F17` | `#F6EFDD` / `#F3EAD4` | Fundo de chip dourado / item selecionado |
| `success`, `error`, `info`, `warning` (+ `_bg`) | tons suaves | tons escuros | Estado com ícone e texto |
| `track` | `#2C2C33` | `#E9E5DC` | Trilho de barras e anéis |

**Tipografia:** Inter para leitura (título 17 bold, h2 12 bold, corpo 10, pequeno 9, legenda 8). Poppins Bold apenas na marca e no nome do personagem. Os dígitos do relógio são desenhados em células fixas (`ui.tabular`) para não "tremerem".

**Espaçamento:** grade de 4 px (4, 8, 12, 16, 24, 32). Margem de página de 28 px, 16 px entre cartões e padding interno de 20×18.

**Raios:** botões 8, cartões 14, chips em pílula.

Formatação pt-BR em `theme.py`: `number(1097)` → `1.097`; `percent(69.04, 1)` → `69,0%`; `compact_duration` → `41h 35min`; `relative_day` → `há 3 dias`.

## Componentes (`ui.py`)

| Componente | Uso |
|---|---|
| `MotionButton(style=…, icon=…)` | Variantes `Accent.TButton` (principal), `TButton` (secundário), `Ghost.TButton`, `Danger.TButton`, `Nav.TButton` e `Chip.TButton` (seleção compacta). Foco visível com contorno dourado de 2 px; Enter e Espaço acionam. |
| `ClockButton` | Pílula do relógio no cabeçalho. Ociosa: "Iniciar foco". Ativa: ícone ▶/⏸ + tempo tabular + matéria. |
| `Chip`, `demo_chip` | Etiquetas de estado com tom e ícone; `demo_chip` traz uma dica explicativa. |
| `Panel(tone="hero", stretch=True)` | Cartão. `hero` adiciona fio dourado; `stretch` iguala a altura de cartões vizinhos e permite ações ancoradas na base. |
| `Columns(weights, breakpoint)` | Colunas que empilham abaixo da largura informada (base da responsividade). |
| `SectionHeader` | Título de seção com ícone, chip opcional e ação "fantasma" à direita. |
| `ProgressBar(tone=…)`, `Ring` | Progresso linear e circular com preenchimento único animado. `ThinProgress` permanece como alias. |
| `MetricCard(icon=…)` | Indicador com ícone, rótulo, valor que se ajusta à largura e legenda. |
| `EmptyState` | Explica o que falta e oferece a próxima ação. |
| `Toast` | Confirmação breve sobre o conteúdo (5 s, fechável). |
| `Tooltip` | Dica com atraso; agora em `ui.py` (antes em `app.py`). |
| `CharacterView` | Composição das camadas PNG do personagem sobre a rosa dos ventos. |
| `FocusDial` | Anel do modo foco com marcas de minuto e estado em texto. |
| `components.SearchSelect` | Campo único com borda (entrada + seta), destaque dourado no foco. |

**Ícones:** subconjunto da Lucide (ISC) em `assets/fonts/RUMO-Icons.ttf`, com 76 glifos, 28 KB, carregado de forma privada. Texto no Tk é suavizado e herda a cor do tema. Para adicionar um ícone, inclua o nome em `scripts/prepare_icons.py` e rode o script com o `lucide.ttf`/`info.json` do pacote `lucide-static@0.460.0` (fora do repositório); ele regenera a fonte e `icons.py`.

## Personagem e equipamentos

A arte é original, desenhada por código em `scripts/prepare_character.py` e `scripts/prepare_rpg_equipment.py` (Pillow em 4× e redução Lanczos). O boneco base é o viajante humano do nível 1 (ver abaixo). As camadas ficam em `assets/character/`: `base`, `eq-backpack-back`, `eq-backpack`, `eq-scarf`, `eq-compass`, `eq-spyglass`, `eq-lantern-glow`, `eq-lantern`, e os avatares de 88 e 44 px.

Os IDs desenhados são `backpack`, `scarf`, `compass`, `spyglass` e `lantern` (os mesmos usados pelo motor do Codex). Itens sem camada (títulos, molduras, selos) aparecem como blocos na grade, e `CharacterView` os ignora. Para criar uma nova camada, desenhe a função no script, registre o ID em `ui.EQUIPMENT_LAYERS` e posicione-o em `FRONT_ORDER`.

## Shell e responsividade

- **Barra lateral (230 px)** com marca, grupos Estudo / Jornada / Análise, cartão do personagem, Configurações e status. Recolhível pelo ícone do cabeçalho.
- **Cabeçalho fixo** com título da página e subtítulo (no Início, a frase do dia em uma linha, com a fonte num ícone). À direita ficam plano, avisos, tema, ajuda, "Registrar" e a pílula do relógio. Abaixo de 1020 px, as ações descem para uma segunda linha.
- **Pontos de quebra:** Missão/Personagem empilham abaixo de 1000 px, as demais colunas abaixo de 900, os indicadores vão de 4 para 2 colunas abaixo de 820, as habilidades vão de 3 → 2 → 1 colunas (1000/620) e os equipamentos usam de 3 a 5 por linha conforme a largura.
- O modo foco abre em 680×660, cabendo em 1366×768 com barra de tarefas.

## Mapa das telas

| Tela | Onde | Estado |
|---|---|---|
| Início | `screen_home.py` | **Prévia.** Missão (ação principal), "Hoje está difícil", personagem, indicadores, ciclo atual, revisões, constância, gráfico semanal e metas, matérias (esforço × desempenho). |
| Estudo com relógio | `app.clock_setup` + `focus.py` | **Prévia.** Formulário com chips de duração; modo foco com matéria, assunto, tempo e controles; descarte separado; toast após salvar. |
| Jornada | `screen_journey.py` | **Prévia.** Personagem, equipamentos, habilidades, conquistas, história e masmorras/chefes. |
| Ciclo, Edital e assuntos, Revisões, Simulados, Metas, Estatísticas, Histórico, Configurações | `app.py` / `edital.py` / `challenges.py` | Herdam o tema; recomposição na etapa 2. |
| Dificuldades / revanche | — | Etapa 2. Contrato de dados a definir com o Codex (ver handoff). |

## Decisões que mudam o que estava aceito (confirmar na revisão)

1. A frase diária saiu do topo de todas as telas: agora é uma linha no cabeçalho do **Início**, com a fonte num ícone e o texto completo na dica.
2. O relógio saiu do rodapé e virou uma **pílula fixa no cabeçalho**, visível em todas as telas principais. A barra de status deu lugar a toasts e a uma linha no pé da barra lateral.
3. A navegação foi reagrupada, com o novo item **Jornada**; "Adicionar estudo" passou a se chamar **"Registrar"** (Ctrl+N).
4. As referências Estudei/Linear/Material Design 3 foram substituídas pelas desta página.

## Extensão de equipamentos 1.6.0

Inventário sai do cartão de perfil para painel próprio com cinco categorias, requisitos legíveis e propósito de cada item. Caminhos de classe aparecem em painel independente com estados em texto e ações por teclado. Camadas novas originais são geradas por `scripts/prepare_rpg_equipment.py`; roupas antecedem armaduras e montarias ficam atrás do personagem. O início mostra trapos/arma velha. A arte base atual de `prepare_character.py` é preservada como origem; preparar as extensões depois dela. No Linux as janelas ficam opacas, com posicionamento único; animações internas continuam respeitando preferências.

## Temas

Oito temas com nome em `theme.THEMES`, escolhidos pelo ícone de paleta no cabeçalho (galeria com miniatura de cada tema nas próprias cores) ou em Configurações. Cada um soma ao dourado uma cor companheira (`secondary`, usada em desempenho, gráficos e destaques). O original é **Norte Dourado**, o "N" dourado da rosa dos ventos.

| Tema | Tipo | Cores |
|---|---|---|
| Norte Dourado | escuro | grafite + ouro + azul-aço (original) |
| Alto-Mar | escuro | azul-marinho + ouro + água-marinha |
| Esmeralda Noturna | escuro | grafite + ouro + esmeralda |
| Rubi Imperial | escuro | vinho + ouro + rubi |
| Ametista | escuro | roxo + ouro + lavanda |
| Brasa | escuro | carvão + ouro + cobre |
| Aurora | claro | papel quente + ouro + azul |
| Brisa | claro | branco frio + ouro + verde-água |

`theme.derive()` calcula bordas, hover, trilhos e fundos de estado a partir de poucas cores e corrige o contraste automaticamente; `tests/test_journey.py` verifica AA em todos. Os valores antigos `Escuro`/`Claro` continuam válidos (`resolve_theme`). As fontes nomeadas do Tk (`TkDefaultFont`, `TkTextFont`…) agora usam Inter: antes, campos e widgets sem fonte explícita caíam em outra família no Linux.

## Movimento

Tudo finito e desativável em Preferências → Animações:

- botões sobem 1 px com sombra no hover e afundam no clique;
- o indicador da navegação cresce ao trocar de seção, e o texto desliza no hover;
- cartões (`Panel`) acendem a borda; cartões de habilidade, equipamento e do personagem animam fundo e borda (`ui.hover_card`), sem piscar quando o ponteiro passa por elementos internos (`ui.Hover`);
- números dos indicadores contam até o valor na entrada; barras e anéis se preenchem uma vez;
- dicas aparecem com fade; linhas de tabela destacam sob o cursor; a troca de tema faz um fade na janela.

## Personagem do nível 1

Humano comum, sem capuz nem dourado: camisa de linho remendada com barra puída, calça surrada, corda na cintura, pés enrolados em trapos e uma lâmina enferrujada e lascada. A ideia é o recomeço de um mendigo em Bannerlord ou Kenshi. Toda arma é empunhada na mão (grade 300×380, mão em (97, 249)); o punho é redesenhado sobre o cabo.

## Criador de personagem

Na Jornada, "Personalizar aparência", ou clique no retrato do Início. Opções:
- corpo masculino ou feminino e 8 tons de pele;
- 11 cabelos e 8 cores de cabelo;
- 6 formatos e 7 cores de olhos;
- 6 sobrancelhas e 3 orelhas.

A prévia (retrato e corpo inteiro) é ao vivo, e a aparência só é salva ao confirmar.

O traço trocou o boneco plano por formas em curvas suaves, com luz do alto à esquerda: volume em cada forma, íris em degradê com pupila e brilho, pálpebra e vinco, nariz por sombra, lábios com volume e mechas no cabelo. A cabeça é menor em relação ao corpo, e o rosto tem um retrato próprio de 264 px. O app só empilha PNGs pré-gerados (o Pillow continua só no build); um cache limitado evita acumular memória ao navegar pelas opções.
