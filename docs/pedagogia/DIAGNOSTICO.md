# Diagnóstico técnico e pedagógico — 15/10/2026

Leitura dos dois prompts anexados e de AGENTS.md, .agents/README, ARCHITECTURE,
SECURITY, TESTING, SITE_WORK e WEB_INTEGRATION. Escopo: evoluir a estrutura;
produção/obtenção de PDFs, aulas, materiais e questões reais fica para curadoria
posterior. Não preencher o catálogo com exemplos de produção. Nenhuma base
pessoal foi aberta, migrada ou usada em testes. Alterações locais anteriores em
learning.py, tests/test_learning.py e .agents/logs_claude.md foram preservadas.

| Área | Evidência no código | Estado antes desta etapa |
|---|---|---|
| Desktop | app.py, core.py, storage.py | Python/Tk nativo, SQLite v6, offline, backups v1–v6 |
| Site | web/src, package.json | React/TypeScript/Vite, responsivo, PDF.js, modo exemplo explícito |
| Backend | backend/migrations/001–009 | Supabase Auth/Postgres, RLS, eventos com CAS e IDs idempotentes |
| Conta e sincronização | sync_client.py, desktop_sync.py, study_sync.py | Opcionais; fila SQLite separada, conflitos explícitos, importação com journal |
| Conteúdo | syllabus.py, assets/bacen2024*.json | Edital preservado e guia detalhado separado; 11 disciplinas em TI |
| Ciclo | learning.py, core.py | Fila retomável, sem cronograma ou dívida; ordem por numeração/título |
| Dependências pedagógicas | learning.py | Sem grafo de pré-requisitos; ordem visual não prova dependência conceitual |
| Campo | training*.py, pdf_reader.py, screen_training.py | Catálogo, planejadas, PDF pessoal, download, leitura por versão, notas e favoritos |
| Arena web | web/src/pages/arena | Filtros, erros, favoritos, respostas, comentários, sugestão de cartão após erro |
| Flashcards web | web/src/pages/cards | Editor pessoal, importação/exportação, revisão SM-2, filtros por deck |
| Arena/cartões desktop | StudySync, screen_account.py | Domínio/fila e importação de resultados; faltam telas completas de prática |
| Estatísticas mistas | study_sync.py: import_session | Soma tentativas à sessão associada; sem classificação individual, pode atribuir tudo a uma disciplina |
| Clique repetido | ArenaSession.tsx, ReviewSession.tsx | Cada clique criava UUID novo; idempotência do servidor não resolve UUIDs distintos |
| Paginação | web/src/service/supabase.ts | select sem range; risco de truncar questões/cartões no limite da API |
| Editorial | backend/migrations/005 | Publicação exige aprovação, versões imutáveis; falta ferramenta de curadoria |
| RPG | rpg.py, rpg_progression.py, backend summary | Fontes canônicas, recompensas idempotentes por sessão; revisão/leitura não dão XP separado |
| Licenças | THIRD_PARTY.md, THIRD_PARTY_ASSETS.md, FONTES.md | Proveniência de dependências/assets; código próprio privado sem licença definida |

## Referência oficial e lacunas mencionadas

Fonte consultada: [edital retificado BACEN 2024, Cargo 2](https://cdn.cebraspe.org.br/concursos/bcb_24/arquivos/ED_1_BCB_23_ABERTURA_ATUALIZADO_RET_4.PDF),
seção de conhecimentos. Os tópicos apontados nos prompts já constam na estrutura
versionada ou nos desdobramentos. Não é necessário inserir duplicatas de
multiplicador monetário, criação/destruição de moeda, contas monetárias, equilíbrio
do consumidor, elasticidade, gRPC, WebSockets, UX/UI, programação assíncrona,
GraphQL, DLT, DNS, DHCP, RADIUS, autenticação/certificados Windows Server, LDAP,
NFS, SMB ou SDN. Teste de cobertura protege essa lista.

Os títulos do Gran citados no prompt não foram anexados; não é possível declarar
nova comparação item a item com o Gran. Nenhum assunto foi excluído ou
rebaixado por frequência de cobrança. A existência de um título no guia não
significa que uma aula tenha sido produzida ou que o edital tenha cobertura
editorial integral.

## Plano verificável

1. Manter registros e IDs; modelar grafo opcional nas preferências existentes.
2. Curar relações conceituais, inclusive entre disciplinas, sem sequência única.
3. Integrar recomendações ao ciclo, detalhe do assunto e Campo de Treinamento.
4. Corrigir repetição de respostas e paginação com regressões automatizadas.
5. Preparar ferramenta editorial local com validação, aprovação e trilha de auditoria.
6. Documentar exatamente o que ficou preparado, integrado ou pendente e validar
   sem credenciais hospedadas ou dados pessoais.
