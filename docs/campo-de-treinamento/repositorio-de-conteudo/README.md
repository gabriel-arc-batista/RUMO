# Modelo do repositório de conteúdo do RUMO

Copie esta pasta para um repositório próprio (por exemplo, `rumo-conteudo`). Ela contém só modelos; nenhuma aula foi produzida.

- `catalogo-fonte.exemplo.json`: formato do catálogo de origem. Renomeie para `catalogo-fonte.json`.
- `aulas/MODELO/aula.md`: estrutura editorial de uma aula, conforme `PROMPT_CRIACAO_AULAS.md`.
- `pdf/`: coloque aqui o PDF renderizado e inspecionado de cada aula.

Publicação: veja `../PUBLICACAO.md`. O script `scripts/build_training_catalog.py`, no repositório do aplicativo, calcula tamanho e SHA-256 e valida o catálogo com as mesmas regras do RUMO.
