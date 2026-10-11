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

GUI só no Windows, execute os scripts **um de cada vez**: `verify_gui.py`, `verify_modern_ui.py`, `verify_design.py`, `verify_subtopic_clicks.py`, `verify_syllabus_ui.py`. Os quatro primeiros usam dados temporários; o último lê uma cópia do banco pessoal, sem alterá-lo. Capturas de gráficos em `verify_modern_ui.py` contêm dados sintéticos temporários. Não publicar capturas pessoais.

`verify_performance.py` simula 10 mil sessões. Após o build, `verify_distribution.py` executa o EXE numa pasta temporária e verifica memória, conexões, segunda instância e persistência. Use `window_capture.capture_window` para capturar somente a janela alvo; configure DPI awareness antes. PrintWindow pode registrar artefatos de repaint após maximizar: espere a pintura estabilizar.

`verify_upgrade.py prepare` cria um backup real e referência local; `verify` compara registros e hashes dos arquivos instalados. Esses scripts atingem dados pessoais e pertencem ao fluxo de uma instalação explicitamente solicitada, nunca à CI. `verify_installer.py` evita execução quando já existe uma instalação do usuário.

Não declarar ausência absoluta de bugs. Linux, leitor de tela externo, sandbox/VM isolada e assinatura de código não foram validados. Registre quais verificações realmente executou.

O workflow manual `.github/workflows/rumo-windows.yml` constrói e verifica os pacotes Windows em dados temporários antes de produzir um artefato. O upload para Releases é feito após conferir o resultado. Não declarar CI remota aprovada antes da conclusão do workflow.
