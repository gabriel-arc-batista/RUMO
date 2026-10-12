# Auditoria dos programas — primeira passagem (11/10/2026)

Resultado de `scripts/audit_training_programs.py` sobre os PDFs oficiais baixados das URLs de `programas-9-concursos.json`. Arquivo estruturado: `programas-extraidos.json`. **Estado: extração automática, pendente de conferência humana.** Nada aqui declara cobertura.

## Método

1. Recorte do texto do cargo por âncoras literais conferidas na página renderizada (por exemplo, `PERFIL: 3. DESENVOLVIMENTO DE SOFTWARE` até `PERFIL: 4.` na DATAPREV). Conteúdos de outros cargos da mesma seleção ficam fora.
2. Localização de cada disciplina pelo título registrado no pacote. Cada bloco termina no título seguinte, mesmo que seja de uma disciplina de outro cargo (por exemplo, Direito Constitucional do TSE, "apenas para os cargos 1 e 19").
3. Um número só é aceito como item quando continua a sequência oficial (1 → 2, 2 → 2.1, 2.1 → 2.2 ou 3). Números de leis, datas, versões e normas (Lei nº 9.613/98, Python 3.9, ISO 27001:2013) não viram itens.
4. Cabeçalhos, rodapés, números de página e assinaturas são removidos. Notas como "(Retificado por meio do Edital nº 4…)" ficam num campo próprio.
5. IDs estáveis: `<concurso>:disciplina:NN:item:<numeração oficial>`.

## Números

| Concurso | Cargo/perfil | Disciplinas | Itens | Pendências específicas |
|---|---|---|---|---|
| Banco do Brasil 2022 | Escriturário — Agente de Tecnologia | 7 | 76 | — |
| Caixa 2024 | Técnico Bancário Novo — TI | 7 | 73 | Língua Inglesa sem numeração (bloco integral) |
| UFABC 2023 | Técnico de TI — Edital 35/2023 | 8 | 19 | Português e Matemática sem numeração; demais blocos com marcadores sem número |
| SERPRO 2023 | Analista — Tecnologia | 12 | 161 | — |
| DATAPREV 2024 | Analista de TI — Perfil 3 | 10 | 94 | — |
| TSE/CPNUJE 2024 | Cargo 17 — Analista Judiciário TI | 10 | 188 | PDPJ-Br e Normativos incluídos pelo Edital nº 3 |
| BACEN 2024 | Cargo 2 — Analista TI | 11 | 126 | Lógica e Estatística: o edital numera "10.3.1–10.3.4" dentro do item 1.3 (provável erro; mantido dentro do 1.3) |
| STN 2024 | AFFC — TI / Transformação Digital | 9 | 102 | O próprio edital pula o item 5 (Direito Administrativo) e o item 2 (Direito Constitucional) |
| Senado 2022 | Analista Legislativo — Análise de Sistemas | 6 | 68 | Programa específico em 25 grupos numerados |
| **Total** | | **80** | **907** | |

Conferência cruzada: o BACEN coincide em contagem com o desmembramento já usado pelo aplicativo (`assets/bacen2024.json`) em 10 das 11 disciplinas; a diferença é o caso "10.3.x" acima. O texto extraído agora corrige palavras partidas daquele arquivo ("referencia ção").

## Retificações

- TSE e BACEN: arquivos oficiais consolidados até a 4ª retificação (`…_RET_4.PDF`); notas de inclusão/retificação preservadas.
- Senado: edital retificado nº 2 (01/09/2022).
- BB, Caixa, UFABC, SERPRO, DATAPREV e STN: **retificações posteriores ainda não conferidas**. Antes de produzir uma aula para esses perfis, consulte a página oficial da seleção.

## O que falta para declarar cobertura

1. Conferência humana item a item contra a página renderizada, registrando responsável e data.
2. Decidir a hierarquia dos blocos sem numeração (Caixa Inglês, UFABC) e dos marcadores da UFABC.
3. Matriz editorial `item ↔ aula/versão` com profundidade, versão de norma ou linguagem e lacunas.
4. Só aulas publicadas e revisadas contam; planejamento nunca conta.

Os PDFs oficiais não são versionados no repositório. Para refazer: baixe-os com os nomes `<id>.pdf` numa pasta e rode `python scripts/audit_training_programs.py PASTA` e depois `python scripts/prepare_training_curriculum.py`.
