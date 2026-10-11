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
| `scripts/` | Preparação de assets, QA, build e instalador |

## Contratos que não devem mudar silenciosamente

Store usa SQLite com chaves estrangeiras, WAL e cache de 2 MB. Valores SQL são parâmetros. Identificadores dinâmicos vêm de listas de tabelas/colunas permitidas. `source()` retorna SQL com placeholder quando há filtro de matéria; `source_args()` coloca esse valor antes dos demais parâmetros. Atualizar os cinco consumidores juntos se alterar esse contrato.

Relógio usa tempo monotônico, checkpoints de cinco segundos e tempo líquido. Recuperação fica pausada; ausência/suspensão não conta. Segmentos repartem tempo entre datas, mas questões permanecem na data atribuída à sessão. Um bloco pode receber estudos parciais; concluir/adicionar tempo não equivale a concluir a teoria.

Esquema 3: backups 1 e 2 migram pausas e observações. Uma restauração é validada numa base temporária antes da transação e preserva o destino local de backups. Não modificar o arquivo SQLite importado.

Hierarquia tem matéria consistente, ausência de ciclos e profundidade máxima de 128. A ordem visual não altera IDs, numeração ou textos oficiais. `starter_cycle_<plan>` garante geração idempotente; `create_guided_cycle` é uma ação pontual de instalação autorizada, não um padrão para todas as bases.

Eventos Tk ficam na thread principal. Cancelar callbacks ao destruir widgets. Não criar timers repetidos para hover. No edital, seleção e conclusão atualizam widgets existentes; reconstruir a página deslocava a rolagem e causava o antigo bug de piscar.
