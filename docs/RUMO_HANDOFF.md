# Passagem frontend → Codex

> **Concluído (Claude, 11/10 14:20) — criador de personagem; pode voltar a editar.** `appearance.py` (opções, padrão, validação, `layers()`), `scripts/prepare_avatar.py` (264 camadas × 2 escalas em `assets/character/look/full|bust`, ~2 min com 8 núcleos), `customizer.py`, `ui.Portrait`, `ui.look_layers`, `app.character_look()`/`customize_character()`, preferência `character_look` validada em `security.py`. **Mudanças nos seus arquivos:** armas e lanterna agora são camadas de trás e não desenham o punho (`HELD` em `ui.py`, `prepare_rpg_equipment.weapon`); elmo/capuz e cachecol ajustados à cabeça menor (`detail`, `prepare_character.scarf`); `base.png` é a aparência padrão. Tronco, mãos (97,249)/(203,249) e pés não mudaram. Novos itens que dependam do rosto devem usar as âncoras do `prepare_avatar` (rosto x 126–174, olhos y 104, sobrancelhas y 97).

> **Concluído (Claude, 11/10 13:50) — pode voltar a editar.** Temas nomeados (`theme.THEMES`, `theme_picker.py`; preferência `theme` aceita os nomes e os valores antigos, validada em `security.py`), fontes nomeadas do Tk em Inter, animações (`ui.Hover`, `ui.hover_card`, `count_text`), WM_CLASS `Rumo` (`tk.Tk(className="RUMO")`), boneco base humano do nível 1 e armas empunhadas (`prepare_character.base`, `prepare_rpg_equipment.rag_base/weapon`, mão em (97, 249)). Ícones novos no subconjunto: palette, shirt, shield-half, axe, hammer, wand-sparkles, rabbit, bird, dog, cat, paw-print e outros. Mantive catálogo, roupas, armaduras e montarias como estavam. **Sugestão:** a montaria `trail_horse` ainda parece uma lhama pequena atrás do personagem — vale redesenhar.


Responsabilidades: o frontend cuida de componentes, navegação, assets e comportamento visual. O Codex cuida de regras, persistência e integração (`rpg.py`, `rpg_schema.py`, `journey_backend.py`, ver `RUMO_BACKEND_CONTRACT.md`). Esta etapa **parou na revisão visual** pedida pelo usuário: nenhuma regra de XP, migração ou conclusão de missão foi implementada aqui.

## Como executar e conferir

```bash
python app.py                        # prévia (padrão desta etapa): dados RPG de demonstração identificados
RUMO_JOURNEY=real python app.py      # mesmas telas com journey_backend.RPGJourney
RUMO_DATA=/tmp/rumo-teste python app.py   # base isolada (nunca use o banco pessoal em testes)
python -m unittest discover -s tests # inclui tests/test_journey.py (contraste, prévia sem gravação)
```

No Linux, o Tk precisa de suporte a Xft para a fonte suavizada. O Python do `uv` (python-build-standalone) não tem Xft e renderiza fontes bitmap; as capturas desta etapa usaram o Tk 8.6.17 do Ubuntu. `ui.load_fonts` registra Inter, Poppins e os ícones de forma privada também no Linux (fontconfig), sem instalar nada.

## Arquivos

| Arquivo | Papel | Integração |
|---|---|---|
| `theme.py` | Tokens, contraste, formatadores pt-BR | Não muda |
| `icons.py`, `assets/fonts/RUMO-Icons.ttf`, `scripts/prepare_icons.py` | Ícones | Não muda |
| `assets/character/*`, `scripts/prepare_character.py` | Personagem em camadas | Novas camadas apenas pelo script |
| `ui.py` | Componentes | Reutilizar; não acessar banco |
| `journey.py` | **Contratos tipados** (dataclasses + `JourneyProvider`) | Validar contra o motor real |
| `journey_live.py` | Leituras reais somente leitura (missão, revisões, esforço/desempenho) | Pode ser substituído pelo motor |
| `journey_demo.py` | **Prévia com dados de demonstração** (`PreviewJourney`) | Manter só como opção explícita |
| `screen_home.py`, `screen_journey.py`, `focus.py` | Telas da prévia | Recebem só view models |
| `app.py` | Shell, `make_journey`, `start_mission`, `session_saved`, `refresh_character_card` | Pontos de integração abaixo |
| `components.py`, `inspiration.py`, `charts.py` | Campo de seleção, frase em linha, rótulos do gráfico | — |

## Contratos e ações (`journey.py`)

As telas chamam somente o provedor (`app.journey`):

- **Leitura:** `mission(plan)`, `reduced(mission)`, `reviews(plan)`, `character(plan)`, `skills(plan)`, `equipment(plan)`, `achievements(plan)`, `chapters(plan)`, `challenges(plan)`, `reward_for(session, subject)`.
- **Ação:** `toggle_equipment(plan, item_id)`.
- **Origem:** cada view model traz `source` (`real` | `demo` | `pending`). O selo DEMONSTRAÇÃO e a faixa de aviso dependem só disso.
- `Mission.position=None` é aceito (missão fora do ciclo: revisão, revanche). `ReducedMission.questions=0` oculta "questões".
- `SubjectSkill.sample_ok` decide se o desempenho é exibido. A interface não fixa limiar numérico no texto.

Ações da interface já ligadas: "Começar missão" e "Hoje está difícil" → `app.start_mission(mission, reduced)` → `clock_setup` preenchido; salvar uma sessão → `app.session_saved(values, subject)` → toast com o que foi registrado e, se `reward_for` devolver `source="real"`, `+XP`.

## Onde estão as demonstrações e como substituí-las

- **Somente** em `journey_demo.py` (`DEMO_*`): nível 4, 340/600 XP, 120 moedas, 5 equipamentos, 6 conquistas, 5 capítulos e 2 desafios. Ficam só em memória; `toggle_equipment` da prévia não grava. Há teste garantindo que nenhuma chamada altera o banco e que `reward_for` devolve `None`.
- A escolha do provedor está em **`app.make_journey`**. **Antes de qualquer release:** troque o padrão para `real` e deixe a prévia apenas com `RUMO_JOURNEY=preview`. O padrão atual é a prévia porque esta é a build de revisão.

## Checklist de integração (Codex)

1. `make_journey`: padrão `real`; prévia só por variável explícita.
2. `start_mission`: usar `RPGJourney.mission_fields(plan, mission, minutes)` para obter os campos do relógio, incluindo `mission_id`. Na versão reduzida, passar `minutes=reduced.minutes`. Hoje o frontend monta o dicionário a partir da `Mission`.
3. Preservar as chaves de contexto (`mission_id`, `difficulty_id`, `challenge_id`, `recall`) de `clock_setup(initial)` → `clock.state` → `session_form(initial=…)` → `save_session(context=…)`. O `save` de `session_form` monta `values` explicitamente; o contexto deve ir **apenas** no argumento `context`, nunca em `validate_session`.
4. `session_saved` já chama `reward_for` **depois** de `save_session`: confirmar que `reward_details(session_id)` está disponível nesse momento.
5. Equipamentos: hoje, clicar alterna apenas itens com `unlocked=True`. Falta a compra (`buy_equipment`) com prévia e confirmação; proposta: clicar em item não adquirido abre confirmação com preço → comprar → `refresh`.
6. Desafios: definir `app.start_challenge(challenge)`. Com ele presente e `available=True`/`source="real"`, o botão "Enfrentar" é ativado sozinho.
7. Preferências `rpg_show_character`, `rpg_effects`, `rpg_story` e `rpg_reward_notifications`: a interface ainda não as lê. Proposta: ocultar o cartão do personagem (Início e barra lateral), a seção História e o `+XP` do toast, respectivamente.
8. `Equipment.slot`: o motor usa também "Título"/"Moldura"/"Selo". Basta ampliar o `Literal`; a grade já mostra qualquer slot e o personagem ignora IDs sem camada.
9. Etapa 2: telas **Dificuldades/Revanche** (proposta de dataclass `Difficulty(id, subject, topic, why, remember, state, evidence, source)`), encontros de revisão com "Lembrei / Parcial / Não lembrei" e chefes em Simulados.

## Pendências e limitações verificadas

- Validação visual feita no **Linux** (Ubuntu 26.04, Tk 8.6.17 com Xft, Python 3.14), em base temporária com dados sintéticos e janelas de 1366×768, 1920×1080 e 1024×700, nos dois temas e com os dois provedores. **Não validado no Windows 11** (plataforma do produto): DPI, ClearType, cores da barra de título via DWM e o carregamento de Poppins e ícones por `AddFontResourceExW`. Os scripts `verify_*.py` dependem do Windows e **não foram executados**. `verify_gui.py` foi ajustado para o novo rótulo "Registrar".
- Formas no Canvas do Tk (cantos, anéis) não têm antialiasing. Texto e PNG são suavizados.
- As telas da etapa 2 mantêm tabelas com rolagem própria dentro da página (rolagem aninhada) e tempos em `HH:MM:SS`.
- Abas (`ttk.Notebook`) no tema claro ainda têm o visual do tema `clam`.
- Não há suporte a leitor de tela. O foco por teclado funciona em botões, campos e chips.
- Durante esta etapa o Black foi executado algumas vezes em todo o repositório, formatando também arquivos do Codex em andamento. Não houve mudança semântica, mas convém conferir se nenhuma escrita simultânea se perdeu.

## Integração concluída pelo Codex

O padrão agora é `real`; `RUMO_JOURNEY=preview` mantém apenas a prévia explícita. Os pontos 1–9 foram conectados, com formulários reais em `rpg_ui.py`. Contexto permanece separado das colunas de sessão. Equipamentos têm prévia, compra confirmada e persistência; desafios abrem relógio ou simulado canônico. As quatro preferências são aplicadas. `Mission.completed` e slots textuais foram acrescentados ao contrato. Consulte o README para regras e uso; a validação final fica em `docs/RUMO_RPG_VALIDATION.md`.
