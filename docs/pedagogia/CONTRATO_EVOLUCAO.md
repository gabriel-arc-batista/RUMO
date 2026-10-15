# Estrutura para as integrações restantes

Este documento descreve a continuação necessária; os contratos abaixo **não são
endpoints implementados**. O contrato em produção continua sendo
`docs/integration/CONTRACT.md` e `shared/rumo-api.ts`.

## Identidade e hierarquia compartilhada

Preservar Concurso → Disciplina → Assunto → Subassunto e os IDs existentes do
catálogo. O SQLite local continua usando seus IDs históricos; associar um ID do
catálogo a um ID local exige vínculo explícito, sem renomear/recriar registros.
Antes de criar nova entidade, verificar `rumo_topics`, `rumo_subjects`,
`rumo_exams`, `topics` e as associações já gravadas no workspace.

A relação pedagógica tem `before`, `after` e `kind` (`essential`, `recommended`,
`parallel`). Ordem sugerida e relações são coisas diferentes. Relações entre
concursos não devem ser inferidas; as que atravessam disciplinas pertencem ao
mesmo concurso. Validação deve considerar também os descendentes de um assunto,
para impedir ciclos indiretos por conclusão de grupos.

## Progresso teórico e conflitos

Uma evolução versionada do serviço precisa aceitar progresso explícito do
assunto/subassunto (`not_started`, `in_progress`, `completed`) e relações
pedagógicas por plano, com IDs de evento estáveis e CAS por entidade. Não inferir
conclusão a partir de notas, posição de leitura, tentativas ou revisão de cartão.
Um evento por subassunto permite estudo parcial sem terminar o assunto inteiro.

O backend deve autenticar o dono pelo mesmo mecanismo atual, validar vínculos e
campos permitidos e preservar histórico. Conflito entre conclusão/reabertura em
dispositivos diferentes exige escolha explícita, sem usar o relógio do cliente
como autoridade. Eventos antigos e fila local não devem ser descartados. A fila
precisa continuar funcionando offline e os backups canônicos antigos continuam
aceitos. A nova informação do workspace requer a exportação separada já existente.

## Sessões mistas e estatísticas por conteúdo

Cada tentativa/revisão deve carregar uma classificação verificável do item e da
versão usada. Essa classificação vem do catálogo/servidor, nunca de matéria da
primeira pergunta, resposta fornecida pelo cliente ou suposição pelo título.
Persistir a classificação no resultado imutável de **novos** eventos evita que
uma reclassificação editorial mude tentativas passadas. Não alterar retroativamente
envelopes já puxados: a projeção atual rejeita eventos cujo corpo foi modificado.

Projetar por questão/cartão, subassunto e disciplina. Eventos repetidos com o
mesmo UUID contam uma vez. Questão com múltiplos subassuntos pode entrar em cada
recorte temático, mas uma única vez no total geral. Anuladas e revisões de cartões
não são acertos de questão. Não inventar divisão de tempo entre disciplinas.

Para importar ao SQLite canônico, reutilizar a divisão `mock_results` quando
adequada e o journal atual para recuperação transacional; evoluir o suporte a
recortes por subassunto se ele ainda não representar a necessidade. Associar
cada classificação remota ao assunto local correspondente. Manter os totais
manuais separados dos remotos e preservar edições posteriores. Enquanto essa
associação não existir, o marcador `misto` fica no workspace e a interface informa
o motivo. Ele não pode ser mapeado silenciosamente a uma matéria.

## Arena e flashcards nativos

As telas futuras devem consumir o mesmo `StudySync`/workspace, fonte central e
classificação do site. Catálogo vazio é um estado explícito. Não preencher
produção com fixtures. Modos: disciplina, assunto/subassunto, conteúdo estudado,
erros, aleatório e simulado. Conteúdo avançado permanece acessível.

Flashcards pessoais precisam de classificação direta opcional em assunto e
subassunto quando não há vínculo de origem. Essa evolução exige atualizar
`validate_card`, importação/exportação, contrato TS, validador SQL e todos os
consumidores juntos. Preservar dados antigos sem inventar tema. Revisão usa o
mesmo SM-2 e a mesma identidade da ação em clique, retry e reinício; não marca
teoria e não cria revisão duplicada.

## Publicação e retirada editorial

O manifesto local é intermediário administrativo, não uma tabela pública ou um
script SQL executável. Adaptador confiável deve validar IDs/vínculos/revisão,
converter nomes para o esquema atual (`statement`/`prompt`, tipos da questão),
separar gabarito/comentário privados e publicar o lote em uma transação.
Ferramenta gráfica deve expor metadados, alternativas, gabarito, procedência,
direitos, duplicatas e histórico antes da aprovação humana.

Retirada deve impedir novas tentativas e ocultar a edição vigente sem fazer
uma edição antiga publicada reaparecer. Hoje a imutabilidade de versões e as
views de visibilidade não bastam para um fluxo de retirada completo: definir
vigência/tombstone no serviço, manter tentativas históricas e testar a última
edição antes de liberar o adaptador. `withdraw` local só prepara a instrução.

Materiais usam o catálogo/recurso já existente: `planejada` não recebe PDF;
`publicada` exige revisão, URL HTTPS autorizada, tamanho e hash. PDFs pessoais
continuam locais. Downloads removíveis não apagam notas/favoritos/posição.

## RPG

Recompensas continuam derivadas de fontes reais canônicas e idempotentes.
Qualquer marco pedagógico futuro precisa de chave única por usuário e marco,
política de correção/reabertura e teste contra repetição artificial. O marco
não impede acesso a conteúdo nem muda a ordem do ciclo. Abrir telas, importar
rascunhos, rever a mesma ação e repetir sincronização não concedem XP extra.

## Critérios de aceite antes de chamar essas integrações de completas

- Desktop → serviço → site → desktop preserva conclusão/reabertura e conflitos.
- Sessão de duas disciplinas atualiza cada recorte correto, sem duplicar tempo,
  tentativas, revisão ou recompensa, inclusive após interrupção e reinício.
- Questão/cartão reclassificado mantém histórico anterior verificável.
- Lote inválido não publica nenhum item; conteúdo retirado não reaparece pela
  versão antiga e não aceita nova tentativa; histórico continua consultável.
- Navegação e criação/revisão nativas funcionam com catálogo vazio, conteúdo
  real revisado e indisponibilidade de rede, sem exigir conta para o app local.
- Carga de mais de 1.000 questões, filtros, paginação e fila são validados em
  serviço local descartável; autenticação hospedada e Windows têm validação
  separada. A coleta dos 1.000 itens permanece uma tarefa editorial real.
