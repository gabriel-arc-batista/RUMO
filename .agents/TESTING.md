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
