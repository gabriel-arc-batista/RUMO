# Escopo e validação

Entrega Windows x64. A implementação usa Tk/SQLite para reduzir RAM. A base pessoal não recebeu sessões de demonstração; screenshots e testes usam pastas temporárias.

## Requisitos do pacote

| Seção do briefing | Implementação | Verificação |
|---|---|---|
| 1. Objetivo | Rumo — Estudos desktop, português, local, foco BACEN | Executável real e GUI |
| 2. Arquitetura | SQLite em dados do usuário, migrações 1→2→3, transações, instância única, pacote sem Python externo | Build, reinício, migração, instância duplicada |
| 3. Referências | Dez imagens lidas; estrutura própria sem ativos da plataforma | Revisão visual das imagens e screenshots |
| 4. Navegação e cores | Nove seções, menu recolhível, relógio inferior direito, temas completo claro/escuro/sistema, preto/dourado, formulários e confirmações com tema | Todas as telas em 1366×768 e 1000×650; formulários reais |
| 5. Planos e assuntos | Planos separados, matérias com pesos/dificuldade, hierarquia, arquivamento, cadastro rápido, importação editável texto/CSV/JSON com confirmação | Cadastro, importação, planos isolados, relações preservadas |
| 6. Registros | Matéria/assunto, categorias, data/horário, previsto/líquido, questões, brancos, páginas/videoaula, material, observações, próximo passo, conclusão e revisões | Criar/editar/excluir; 45 min e 15/5→16/4; rejeição com rollback |
| 7. Relógio | Cronômetro/timer, pausa, alvo +1/+5/+15, foco, checkpoints, recuperação, suspensão, rascunho separado, eventos de pausa, finalização idempotente | Modelo de relógio simulado e interação real com timer; recuperação sem acrescentar ausência |
| 8. Ciclos | Vários ciclos, fila/voltas, blocos estáveis, sessões parciais, conclusão/adiamento explícitos, retomada, histórico, arraste/botões, geração por pesos, preferência 2–3 matérias | 25+20+15, excesso 70 min, adiamento, edição/exclusão, preservação da posição ao ordenar |
| 9. Início | Resumos reais, constância com navegação, ciclo, revisões, prova opcional, metas, estudo semanal, painel por matéria | Agregações e revisão visual |
| 10. Estatísticas | Filtros combináveis, rosca, horas/médias/dias/páginas/videoaula, diário/semanal/mensal, barras/linha, horas por matéria, acertos/erros, categorias/assuntos, CSV de registros e estatísticas | Médias ponderadas, sem 0% fictício, divisão diária, filtros, CSV |
| 11. Edital | Matérias expansíveis, busca, folhas como unidades de progresso, pais agregadores, questões/último estudo, revisão independente, materiais/links | Hierarquia e progresso sem duplicação; cadastro/conclusão |
| 12. Revisões e calendário | 1/7/30/60/120 e intervalos editáveis; hoje/próximas/atrasadas/concluídas; reagendar/cancelar/concluir/registrar; calendário semanal/mensal/lista, mini calendário, legenda por matéria e tarefas | Série sem duplicação, revisão registrada, tarefa, três visões e arraste com confirmação |
| 13. Histórico | Agrupamento por dia, totais, filtros, pesquisa, ordenação, detalhes, edição/exclusão com confirmação, paginação de 100 | GUI e desempenho com 10 mil registros |
| 14. Simulados | Totais/divisão por matéria, formatos, previsto/líquido, acertos/erros/brancos, fórmula/pesos, gráficos de desempenho/pontuação, detalhes/edição/exclusão | 100 questões 70/20/10, +1/−1/0 = 50; contagem única; filtro por matéria usa divisão real |
| 15. Metas/conquistas | Metas por plano/matéria, horas/questões, constância configurável, dias elegíveis, regras/progresso, motivação/conquistas desativáveis e Corujão opcional | Dados derivados; revisão das regras e preferências |
| 16. Configuração/backup | Tema, sons/avisos, fuso, início da semana, horário 12/24h nos detalhes, duração, revisões, perfil local; JSON versionado, SQLite consistente, retenção, destino, prévia e cópia anterior à restauração | JSON e SQLite restaurados; inválidos preservam base; preferências e vínculos voltam |
| 17. Consistência | IDs, chaves estrangeiras, validação, transações, dados como fonte de verdade, tempo/teoria/bloco/revisão separados | Testes de domínio e integração |
| 18. Entrega | Código, scripts, guia, checklist, screenshots, EXE, instalador e portátil | Build nativo e teste do executável; instalação/desinstalação em destino de teste |
| 19. Aceitação | Fluxos principais e casos matemáticos cobertos | 33 testes automatizados; integração com janelas reais |

## Evidências

- `scripts/verify_subtopic_clicks.py`: cliques reais nas setas e nos nomes, manutenção das linhas e do foco ao abrir/fechar, filhos abaixo do pai, seleção sem deslocamento, liberação de widgets ao recolher e busca sem duplicação de descendentes. Relatório em `validation/subtopic-clicks-report.json`.

- `tests/test_core.py`: 29 testes de persistência, validação, agregação, ciclo, revisão, simulado, relógio, migração, fuso, importação e backup.
- `scripts/verify_gui.py`: formulários reais, estado inválido sem cadastros parciais, cronômetro finalizado após trocar plano, revisões e arraste, calendário, preferências, exportação, todas as telas nos dois temas e duas dimensões, restauração e reinício.
- `validation/gui-report.json` e PNGs: resultados e screenshots de base temporária. As imagens têm dados de teste, não dados pessoais.
- `validation/performance-report.json`: 10 mil registros; resumo ~30 ms, página de 100 ~2 ms, consulta diária ~29 ms neste computador.
- `validation/distribution-report.json`: execução do programa empacotado, memória/CPU, reinício, instância única e ausência de sockets de internet observados.
- `validation/installer-report.json`: instalador e desinstalador concluídos com código 0 em pasta de teste, sem abrir/mudar a base pessoal.
- `scripts/verify_design.py` e `validation/design-report.json`: fonte Poppins carregada, quadros intermediários da entrada dos cartões, menu persistente/recolhível e deslizamento do relógio, transições de mouse, fechamento durante animação, navegação rápida, memória após navegação repetida e opção de desativar animações. Nenhum callback de animação permanece em repouso.
- `tests/test_syllabus.py`: cobertura de cada folha oficial, 565 desdobramentos TI/525 Economia, idempotência, preservação de conclusões/histórico/arquivamento e backup validado.
- `scripts/verify_syllabus_ui.py`: nove seções em 1366×768 e 1920×1080 nos dois temas, abertura de matérias/tópicos, seleção/conclusão, busca com/sem acentos e ausência de tabela/rolagem horizontal no edital. `edital-java-*.png` e `edital-redesenhado-*.png` mostram uma cópia consistente dos dados pessoais, sem inserir sessões de exemplo. Alterações de teste ficam na cópia temporária.

## Limites da validação

Windows 11 x64 foi o sistema efetivamente executado. O script prevê pacote portátil Linux, mas **build e execução Linux estão pendentes de validação em Linux**. Não foi realizado teste com leitor de tela externo. Navegação por teclado usa controles nativos e foco; atalhos de formulário foram implementados. Os seletores de arquivo/pasta pertencem ao sistema operacional e seguem o tema do Windows.

Suspensão e falha foram simuladas com relógio controlável; não foi provocado desligamento abrupto deste computador. O aplicativo não fez conexões de internet nos testes; a rede do sistema não foi desativada. Não se promete aviso com o aplicativo encerrado.

O edital incluído é o de abertura de 2024, completo no PDF e verticalizado na seção 18; não inclui uma consolidação automática das retificações e não é previsão de conteúdo/data de novo concurso.

## Revisão 1.3.0

38 testes unitários; observações e migração v2→v3, restauração de backups antigos, desafios isolados por plano e tempo após meia-noite. `verify_modern_ui.py` testa caixas verdes, lápis/observações sem reconstrução da lista, busca de assuntos, presets, pausa/retomada/finalização, abas do registro e três níveis. Suas capturas usam dados sintéticos exclusivamente temporários. Três referências de design e cobertura bibliográfica: [FONTES.md](FONTES.md).

## Revisão 1.4.0

42 testes unitários. Ciclo guiado idempotente, fundamentos antes de SQL e progressão de estruturas básicas para interfaces. Seletor testado a 520 × 400, meta principal no relógio e preferências em quatro abas. Nove telas em dois temas; Inter carregada, animações finitas e opção de reduzir movimento. Testes de carga com 10 mil registros e revisão visual de capturas das janelas nativas. A atualização preserva registros e mantém o ciclo anterior; o novo ciclo solicitado fica ativo.

## Revisão 1.4.1

57 testes unitários, Black, auditoria de dependências e revisão de alertas Bandit. Retenção e restauração de backups protegidas, valores SQL parametrizados, CSV literal, hierarquia validada. Contexto de continuidade em `.agents`; detalhes e limites em `SECURITY_REVIEW.md`.
