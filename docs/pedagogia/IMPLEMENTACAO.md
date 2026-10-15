# Estrutura pedagógica e preparação editorial — 15/10/2026

Esta entrega prepara a estrutura e corrige comportamentos pontuais. **Não conclui
todas as funcionalidades dos prompts originais.** A matriz abaixo separa código
operacional, estrutura preparada e integrações ainda pendentes. PDFs, aulas,
materiais didáticos e questões reais não foram produzidos, coletados ou publicados.
A meta de 1.000 questões permanece integralmente pendente de curadoria.

## 1. Funcionalidades que já existiam

Consulte [o diagnóstico técnico e pedagógico](DIAGNOSTICO.md). Desktop nativo
Tk/SQLite offline, ciclo, árvore de assuntos, sessões retomáveis, RPG, leitor PDF,
notas/favoritos/downloads, backups, site React, Arena e flashcards web, contas
opcionais, fila de eventos e conflitos CAS já estavam implementados em graus
diferentes. A existência de APIs de prática no desktop não equivalia a ter telas
nativas completas de Arena e flashcards.

## 2. Correções realizadas

- Cliques/teclas repetidos no mesmo cartão ou questão compartilham uma operação
  em andamento. Uma falha permite tentar novamente com o mesmo UUID. A mudança
  de cartão ocorre só depois da gravação local bem-sucedida.
- Catálogos web usam páginas ordenadas e intervalos inclusivos, continuando até
  página vazia. Mesmo limite de servidor menor que o lote solicitado não trunca
  o banco; falha intermediária recusa o catálogo parcial.
- Sessões web de várias disciplinas recebem marcador `misto`, tanto na Arena
  quanto nos flashcards, em vez de tomar a primeira disciplina. Resultados da
  Arena são separados pela disciplina real de cada questão. Estatísticas de
  domínio também agrupam por assunto/subassunto e deduplicam IDs de atividades.
- **Limite explícito:** sessões `misto` ficam no workspace do desktop e aguardam
  integração por conteúdo. Não são importadas para uma disciplina escolhida
  arbitrariamente. Não houve correção retroativa de sessões pessoais antigas.
- O próximo assunto retorna vazio quando todas as folhas estiverem concluídas;
  não recomenda automaticamente repetir a primeira folha.

## 3. Funcionalidades adicionadas

`pedagogy.py` implementa o grafo opcional. `pedagogy_ui.py` permite adicionar,
alterar o tipo e remover relações em **Edital e assuntos → assunto → menu →
Conhecimentos anteriores**. Permite assuntos de outras disciplinas do mesmo
plano e recusa ciclos, duplicatas, IDs desconhecidos e concursos incompatíveis.

A recomendação considera folhas pendentes e os conhecimentos anteriores de
seus ancestrais. Distingue `essential`, `recommended` e `parallel`; ausência de
arestas representa independência. Nada altera a permissão de acesso ao assunto.
A tela explica o motivo da recomendação e os conhecimentos anteriores faltantes.

O ciclo utiliza a recomendação quando um bloco não tem assunto fixado. Blocos
com assunto escolhido continuam respeitados. O Campo apresenta a sugestão do
próximo bloco pendente e um link para a árvore. Conclusões usam `topics.done` e
permanecem após reinício; consultas, cartões e leitura não marcam teoria por conta
própria. Nenhuma dívida de estudo ou agenda foi criada.

Arena web acrescenta conteúdo estudado, aleatórias e simulado. O filtro de assunto
inclui seus descendentes. No modo direcionado, **todos** os assuntos da questão
precisam de evidência de uma aula atual integralmente marcada como lida; questões
sem classificação ficam fora. A interface explica esse critério, que não mede
domínio nem substitui a conclusão teórica. Simulados podem incluir assuntos novos.
Flashcards ganham filtro de leitura concluída e filtragem de descendentes/fontes
(aula/questão/deck). A revisão recebe os filtros ativos, preservando SM-2.

## 4. Assuntos incluídos no BACEN

Nenhum assunto novo foi necessário para as lacunas enumeradas. Todos os itens
listados nos prompts já existem no edital/guia versionado de TI. O novo teste de
cobertura verifica especificamente essa área, não o conjunto de Economia e
Finanças. Nenhuma disciplina ou assunto foi removido e nenhum ID foi recriado.

A comparação com os títulos do Gran não foi repetida: os títulos não foram
anexados. A afirmação de cobertura se limita à lista de lacunas fornecida, não a
uma auditoria editorial completa do curso.

## 5. Organização pedagógica por disciplina

| Disciplina do BACEN TI | Progressão e independência |
|---|---|
| Língua Portuguesa | Classes antes de concordância/regência; regência antes de crase; estruturas de oração apoiam pontuação/reescrita. Interpretação continua acessível independentemente. |
| Noções de Lógica e Estatística | Proposições → tabelas-verdade → equivalências/De Morgan. População/amostra apoia descrição; probabilidade condicional precede distribuições. Ramos lógico e estatístico podem avançar separadamente. |
| Direito Administrativo | Organização administrativa apoia entidades; espécies de poder apoiam abuso; requisitos dos atos apoiam anulação; regime disciplinar apoia PAD. Não obriga percorrer todas as leis em sequência. |
| Fundamentos de Macro e Microeconomia | Preferências e restrição apoiam equilíbrio; equilíbrio apoia efeitos; demanda apoia elasticidade. Moeda apoia multiplicador e contas monetárias. Micro e macro não dependem uma da outra por regra global. |
| Atualidades | Independente, sem pré-requisitos artificiais ou suposta conclusão permanente das notícias. Mantém a estrutura existente. |
| Ciência de Dados | Aprendizado de máquina apoia redes neurais e MLOps; redes neurais apoiam deep learning; deep learning apoia LLM. Estatística fornece recomendação entre disciplinas. |
| Segurança da Informação | Identidade apoia MFA; ataques apoiam incidentes; criptografia apoia proteção de aplicações. Redes e arquitetura web fornecem recomendações entre disciplinas. |
| Engenharia de Software | HTTP apoia gRPC/WebSockets/REST; cliente-servidor e serviços apoiam microsserviços; microsserviços apoiam API gateway; programação apoia assíncrono. |
| Infraestrutura em TI | Redes e sistemas operacionais apoiam administração/virtualização; imagem/container apoia orquestração; pods apoiam services/ingress. Docker é recomendado, não requisito universal do Kubernetes. |
| Bancos de Dados | Entidades e relacionamentos apoiam modelo relacional/chaves; SELECT básico apoia JOIN, agregações e subconsultas; subconsultas apoiam CTE; agregações apoiam janelas. **NoSQL não é pré-requisito do SQL.** |
| Gestão em TI | Mantém ordenação introdutória existente e explicita Kanban/Scrum como conhecimentos paralelos. Não obriga terminar Kanban para iniciar Scrum/ITIL/governança de dados. |

## 6. Dependências entre assuntos

[assets/bacen-pedagogy.json](../../assets/bacen-pedagogy.json) contém 64 relações
curadas, inclusive entre disciplinas e entre folhas. As relações padrão só são
associadas quando disciplina e título correspondem exatamente a um único registro
local; títulos alterados pelo usuário não são adivinhados. O editor salva relações
pelos IDs reais, mantendo as personalizações. Os textos oficiais permanecem
intactos; o grafo representa curadoria pedagógica, não novo conteúdo do edital.

## 7. Estrutura de dados

Sem migração do SQLite canônico e sem novas tabelas de estudo. A preferência
`learning_graph_<plan_id>` contém as relações explícitas, cobertas pelos backups
v6 existentes e pela validação de preferências. Restaurar backup não concede XP.

O workspace editorial é um SQLite separado, escolhido explicitamente: `drafts`,
`editions` e `audit`. Recusa bases de outro domínio, inclusive a base de estudos.
Versões preparadas são preservadas; correções mantêm o ID da questão e exigem
nova versão quando uma edição já foi preparada. Não há mudança no PostgreSQL.

## 8. Integrações

- Grafo → próxima folha → ciclo → Campo → detalhe da árvore.
- Progresso individual → mesma conclusão local existente e retomada persistente.
- Leitura web atual → questões/cartões relacionados; sem confundir com domínio.
- Questão errada → rascunho editável de cartão já existente preservado.
- Respostas/revisões → fila existente e identidades idempotentes, com proteção
  adicional contra repetição de clique.
- RPG continua derivando recompensas de sessões reais, sem bônus novo por abrir
  trilha, preparar lote, clicar, ler ou marcar uma relação.
- Sincronização de grafo/conclusão teórica entre site e desktop **não foi criada**.

## 9. Testes e resultados

Os resultados finais desta rodada são registrados após a execução abaixo.

| Verificação | Resultado |
|---|---|
| Suíte Python completa | 193 testes, sem falhas; 1 integração opcional ignorada por configuração |
| Frontend Vitest | 45 testes aprovados |
| TypeScript e build de produção | Aprovados |
| `backend/tests/run.sh` | Aprovado em PostgreSQL Docker descartável; inclui RLS/RPC/idempotência/CAS/SM-2/perfil/ciclo |
| `verify_pedagogy_gui.py` | Aprovado no Tk nativo Linux: Campo, árvore, acesso avançado, adicionar/remover relação, nenhuma sessão/XP por navegação |
| Chrome E2E, modo exemplo | 40/40 verificações aprovadas nas duas passagens, incluindo a final após as mudanças |
| Black nos Python alterados | Aprovado |
| `scripts/check_repository.py` | Aprovado; verifica arquivos rastreados, não certifica conteúdo não rastreado |

A primeira execução Python falhou por falta de Pillow no ambiente de teste.
Instalei a versão já fixada em requirements-dev.txt no venv e repeti a suíte.
Há ResourceWarnings preexistentes de conexões não fechadas nos testes; não foram
suprimidos nem tratados como aprovação de gestão de recursos. Não houve teste
hospedado, release Windows, teste de carga remoto ou publicação nesta rodada.

## 10. Problemas e funcionalidades ainda parciais

| Exigência dos prompts | Estado honesto após esta etapa |
|---|---|
| PDFs/aulas/materiais e 1.000 questões | Estrutura existente preservada; nenhum conteúdo real acrescentado. Dependem de coleta, direitos e revisão. |
| Ferramentas editoriais | CLI local operacional; falta painel administrativo gráfico e integração transacional com publicação/retirada no serviço. |
| Publicar/retirar lotes remotamente | Manifestações preparadas, sem execução remota. `published:false` / `applied:false` tornam o limite explícito. |
| Arena e flashcards nativos completos | Continuam pendentes; APIs/fila não equivalem a telas completas. |
| Sessões mistas no desktop | Preservadas sem atribuição incorreta; falta projeção por conteúdo e associação individual para importar com estatísticas completas. |
| Estatísticas históricas já gravadas | Nenhuma reparação automática; exigem classificação verificável e revisão antes de qualquer ajuste pessoal. |
| Classificação individual de cartões pessoais | Fontes/deck permitem filtros quando há vínculo; cartão sem origem temática verificável não recebe classificação inventada. |
| Grafo/progresso teórico sincronizado | Local; contrato de evolução em documento separado. |
| Trilha pedagógica completa no site | Ainda não consome o grafo local; filtro de leitura está operacional, mas não representa essa integração completa. |
| Marcos pedagógicos no RPG | Mecânicas atuais preservadas; não foram adicionados marcos/recompensas por subassunto. |
| Auditoria integral de licenças | Documentação existente preservada; não houve inventário jurídico completo nem mudança da licença privada. |

## 11. Próximas etapas

Concluir as integrações descritas em [CONTRATO_EVOLUCAO.md](CONTRATO_EVOLUCAO.md),
começando pela identidade temática entre catálogo e IDs locais. Só depois aplicar
as migrações aditivas necessárias e concluir telas nativas, grafo web e estatísticas
mistas integradas. A curadoria real de PDFs/questões continua uma etapa separada,
conforme pedido do usuário. A ferramenta editorial não deve apresentar o lote
como publicado antes da confirmação do serviço.

## 12. Operação editorial preparada

A interface de linha de comando funciona sem conta, tokens ou serviço:

```sh
python scripts/editorial.py --workspace /caminho/editorial.sqlite3 \
  --taxonomy /caminho/taxonomia.json --actor 'Nome do editor' list
```

`taxonomia.json` é um objeto `{ "id-do-subassunto": "id-da-disciplina" }`.
Subcomandos: `import arquivo.json`, `correct questao.json`, `approve ID`,
`prepare ID... --output manifesto.json`, `withdraw ID --reason 'motivo'`.
O import aceita até 1.000 itens por lote, acusa duplicatas por enunciado normalizado,
exige origem/direitos/gabarito/comentário e não aprova automaticamente. `approve`
é a confirmação humana de revisão; o programa não verifica a veracidade jurídica
da licença informada. Correções invalidam aprovação; preparar lote é atômico;
falha não deixa metade aprovada como publicada. O manifesto contém gabaritos e é
um documento administrativo privado, não o catálogo público da Arena.

## 13. Rastreabilidade das fases

A: diagnóstico registrado. B: cobertura das lacunas conferida sem duplicação.
C/D: grafo local e integração com ciclo/Campo implementados. E/F: paginação,
proteção de repetição, modos/filtros web e prevenção de atribuição mista corrigidos;
a integração nativa permanece parcial. G: preparação editorial local operacional,
publicação e curadoria reais pendentes. H: invariantes RPG preservadas, novos
marcos pendentes. I: testes locais executados; limitações acima permanecem.
