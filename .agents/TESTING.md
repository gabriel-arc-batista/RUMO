# Construir → testar → revisar

```powershell
python -m pip install -r requirements-dev.txt -r requirements-quality.txt
python -m black --check .
python scripts/check_repository.py
python -m unittest discover -s tests -v
python -m bandit app.py core.py backups.py security.py ui.py components.py charts.py challenges.py edital.py inspiration.py learning.py syllabus.py -f json -o validation/bandit.json
python -m pip_audit -r requirements-dev.txt --no-deps --disable-pip
```

Os testes unitários cobrem sessões, tempo e suspensão, fusos, migrações, restauração, metas, edital, aprendizagem e políticas de segurança. O Bandit exige revisão manual: consultas com composição de identificadores permitidos geram avisos; não ocultar alertas em massa ou afirmar que zero alertas prova segurança.

Os scripts históricos de GUI são específicos do Windows; execute os scripts **um de cada vez**: `verify_gui.py`, `verify_modern_ui.py`, `verify_design.py`, `verify_subtopic_clicks.py`, `verify_syllabus_ui.py`. Os quatro primeiros usam dados temporários; o último lê uma cópia do banco pessoal, sem alterá-lo. Capturas de gráficos em `verify_modern_ui.py` contêm dados sintéticos temporários. Não publicar capturas pessoais.

`verify_performance.py` simula 10 mil sessões. Após o build, `verify_distribution.py` executa o EXE numa pasta temporária e verifica memória, conexões, segunda instância e persistência. Use `window_capture.capture_window` para capturar somente a janela alvo; configure DPI awareness antes. PrintWindow pode registrar artefatos de repaint após maximizar: espere a pintura estabilizar.

`verify_upgrade.py prepare` cria um backup real e referência local; `verify` compara registros e hashes dos arquivos instalados. Esses scripts atingem dados pessoais e pertencem ao fluxo de uma instalação explicitamente solicitada, nunca à CI. `verify_installer.py` evita execução quando já existe uma instalação do usuário.

Não declarar ausência absoluta de bugs. Leitor de tela externo, sandbox/VM isolada e assinatura de código não foram validados. A integração RPG e o pacote Linux foram validados conforme `docs/RUMO_RPG_VALIDATION.md`. Registre quais verificações realmente executou.

O workflow manual `.github/workflows/rumo-windows.yml` constrói e verifica os pacotes Windows em dados temporários antes de produzir um artefato. O upload para Releases é feito após conferir o resultado. Não declarar CI remota aprovada antes da conclusão do workflow.

`tests/test_rpg.py` cobre fontes idempotentes, pausas/recuperação, missões parciais, encontros atrasados, evidências separadas, chefes com resultados canônicos, correções de compras, histórico opt-in e migração/restauração v1–v5. Use bases temporárias também na integração Tk; não consulte o banco pessoal.

Prévia visual no Linux: use um Tk com Xft (o Python do `uv` renderiza fontes bitmap), base em `RUMO_DATA` temporária e captura apenas da janela via Xlib (`get_image` no frame do Xwayland). `RUMO_JOURNEY=real` exercita o provedor real nas mesmas telas. Isso não substitui a validação no Windows.

Integração RPG nativa em Linux e Windows: `python scripts/verify_rpg_gui.py`. Usa exclusivamente dados sintéticos temporários e verifica o provedor real, missão reduzida, pausas, revisão, dificuldades, desafios e compra/equipamento pela interface. No Linux/X11 a aplicação desativa XIM externo para evitar bloqueio na conexão com IBus; a abertura animada é assíncrona. Testar métodos de entrada externos separadamente antes de habilitá-los.

`tests/test_rpg_progression.py` verifica início pobre, evolução gratuita, requisitos de nível e prática, caminhos paralelos, datas não consecutivas, ausência de bônus, aquisições após correções e compatibilidade do inventário v4→v5. `scripts/verify_rpg_dialogs.py` cobre a regressão `grab failed: window not viewable`: abre seletores antes do mapeamento do formulário, confirma diálogos reais e cria masmorra pelo seletor de assuntos; também cobre todas as categorias e o atalho da arma inicial. Rodar após `verify_rpg_gui.py`, nunca simultaneamente.

Seis caminhos: Paladino mantém o ID anterior, Ladino conta dificuldades distintas trabalhadas por estudos inscritos; Erudito conta assuntos estudados com observações de sessão/caderno não vazias, ignorando espaços e histórico não inscrito. A ação `notes` reutiliza `App.topic_notes` e sincroniza/atualiza a Jornada após salvar; não concede XP ou cria estudo. `verify_rpg_dialogs.py` inclui este fluxo nativo.


Revisão v1: execute também `python scripts/verify_appearance_gui.py` (todos os temas e controles, salvar/cancelar, persistência, cache e nenhuma alteração nas métricas). A CI Windows inclui os fluxos legados `verify_gui.py`, `verify_modern_ui.py` e a carga `verify_performance.py`. Resultado final em `docs/RUMO_V1_VALIDATION.md`.

Assets externos: `tests/test_appearance.py` valida todos os caminhos/opções,
ordem de camadas, SHA-256 dos originais, IDs legados, fallback, gravação atômica,
backup/restauração e nenhuma mudança nas métricas/inventário. O teste nativo
`verify_appearance_gui.py` percorre as categorias preguiçosas e todos os temas,
seleciona cada opção, verifica imagens vivas, cancelamento/nome/reinício e cache.
`capture_character_examples.py` captura somente janelas Tk com base temporária
no Linux/X11; exemplos ficam em validation/ e não devem ser versionados.
Não gerar assets enquanto verifica a GUI; exportação de PNGs usa troca atômica.

Campo de Treinamento: `tests/test_training.py` (catálogo inválido mantém o anterior, hash/tamanho/cancelamento, rede simulada e hosts aprovados, atualização e remoção preservando notas, sessão vinculada uma vez, backup v6/v5, migração v5→v6). Fixture de **teste** em `tests/fixtures/campo-teste/` (regerar com `scripts/make_test_lesson.py`; nunca apresentar como aula). O leitor precisa de `pypdfium2` (no `requirements-dev.txt` e coletado por `scripts/build.py`). No Linux, o atalho usa `~/.local/share/rumo-runtime/site`.

## Conta/sync opcional (12/10/2026)
`tests/test_sync_client.py`, `test_study_sync.py`, `test_sync_desktop.py` usam
bases temporárias e rede simulada. `backend/tests/run.sh` usa PostgreSQL 16
Docker descartável para RLS, RPC, duplicação, CAS, catálogos e edição de XP.
`RUMO_POSTGRES_TEST=1 python -m unittest discover -s tests -p test_sync_integration.py -v`
valida fila Python → RPC PostgreSQL → segundo dispositivo → Store/RPG nas três
áreas, sem Auth/PostgREST hospedado. `scripts/verify_sync_gui.py` valida login
opcional e marcação/desmarcação/conclusão do leitor Tk com PDF de teste temporário,
sem rede. Executar scripts GUI sequencialmente. Frontend segue responsabilidade
do Claude; não declarar teste do navegador concluído sem sua implementação pronta.

Site (`web/`): `npm test` (Vitest: fila, conflito, conclusão manual, identidades,
correção, SM-2, importação, chave privilegiada), `npm run e2e` (Chrome real, modo
exemplo) e, com Docker, `npm run servico:up` + `build:servico` + `preview:servico`
+ `npm run e2e:servico` (Postgres/GoTrue/PostgREST locais com as migrações de
`backend/`, conteúdo EXEMPLO e usuários sintéticos). `e2e/vazio.mjs` com
`SEED=0` cobre o catálogo vazio; `python3 web/e2e/desktop_check.py` +
`node web/e2e/desktop-para-site.mjs <email>` cobre a ida e volta com o cliente do
desktop. Não substitui teste no Supabase hospedado nem em outros navegadores.

Adições de 12/10 (tarde): `tests/test_sync_extras.py` (snapshots de perfil/ciclo, trava sem 009, transporte explícito entre versões, intervalos de páginas, token_store com DPAPI no Windows/0600 no Linux) e `scripts/verify_version_carry_gui.py` (leitor nativo: aviso, diálogo editável, versão anterior preservada, sem XP; incluído no workflow Windows). Backend: `backend/tests/profile_cycle.sql` roda em `backend/tests/run.sh`. Site: `npm test` (36), `MAIL=1 npm run servico:up` + `node e2e/email.mjs` (confirmação/recuperação com Mailpit), `node e2e/versao.mjs`, `python3 web/e2e/desktop_profile.py` + `node e2e/desktop-perfil-no-site.mjs <email>`, `node e2e/a11y.mjs` (axe-core), `node e2e/carga.mjs` (só pilha local) e `BROWSER=firefox` nos fluxos `flow.mjs`/`extras.mjs`.
