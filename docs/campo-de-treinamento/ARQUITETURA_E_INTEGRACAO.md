# Como o catálogo online conversa com o RUMO

Proposta para a primeira versão: **catálogo público online, PDFs baixados sob demanda e progresso salvo localmente**. O aplicativo continua executável na sua máquina. Não precisa distribuir toda a biblioteca junto do instalador, criar uma conta ou chamar uma IA para abrir uma aula.

## Fluxo de uso

1. Você escolhe um edital-alvo ou explora matérias livremente.
2. O RUMO consulta um pequeno catálogo JSON por HTTPS. Ele descreve matérias, assuntos, aulas, versões, cobertura e arquivos disponíveis.
3. Ao escolher uma aula publicada, o aplicativo baixa o PDF e verifica o arquivo.
4. O leitor abre a cópia local. Página atual, anotações, favoritos e sessões de estudo ficam no computador.
5. Sem internet, PDFs já baixados continuam abrindo e o último catálogo válido continua visível. Uma aula ainda não baixada explica que precisa de conexão.
6. Ao voltar a ficar online, o RUMO verifica novas versões. Não apaga notas nem substitui silenciosamente o PDF que você estava estudando.

Para o usuário, um site pode ter uma página de apresentação e pesquisa do acervo. Para o aplicativo, basta uma URL estável do catálogo. **Um site completo ou um servidor com banco de dados não é requisito da primeira etapa.**

## Hospedagem inicial

Sugestão: repositório público de conteúdo próprio, com catálogo no GitHub Pages e PDFs ou pacotes versionados nos assets de Releases. O repositório do código e o de conteúdo podem ser separados para que o instalador não cresça junto do acervo. A URL final depende dos repositórios que forem realmente criados; não inventar URLs publicadas.

O Pages está disponível para repositórios públicos no GitHub Free, mas tem limites: site publicado de até 1 GB e limite flexível de banda de 100 GB/mês. Releases aceita arquivos individuais menores que 2 GiB e até 1.000 assets por release, conforme a documentação consultada. Isso torna a proposta viável para começar; não constitui promessa de hospedagem gratuita permanente ou sem qualquer limitação.

Fontes oficiais, consultadas em 11/10/2026:

- [Limites do GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [Arquivos de Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
- [PDF.js, se a tecnologia atual do app for web](https://mozilla.github.io/pdf.js/)
- [R2 como alternativa posterior de armazenamento](https://developers.cloudflare.com/r2/pricing/)

Se o acervo ou o tráfego crescer, trocar o provedor dos arquivos pelo adaptador de conteúdo, mantendo os identificadores das aulas. Armazenamento de objetos tem regras e custos próprios. Não implementar essa migração antecipadamente.

## Quem guarda o quê

O catálogo público guarda currículo, metadados das aulas, referências, versões, licenças e links dos recursos. O computador guarda PDFs baixados, notas, página de leitura, favoritos, estado de conclusão, ciclos e sessões de estudo.

Nesta etapa não enviar estatísticas ou documentos pessoais para o servidor. Não exigir login, API key, telemetria, sincronização de contas ou assinatura. Um eventual serviço remoto de contas será outra decisão de produto.

## Modelo compartilhado com Arena e flashcards

Identidades distintas: concurso/edição/perfil, disciplina oficial, item de edital, matéria canônica, assunto, aula e recurso/versão. Um assunto pode aparecer em várias disciplinas oficiais. Um item pode exigir várias aulas; uma aula pode contribuir para vários itens. Uma aula pode abordar vários assuntos, com um assunto principal e vínculos adicionais.

Use IDs estáveis independentes de título, caminho, posição e número de página. Corrigir o nome de uma aula não pode perder seu progresso. O recurso PDF tem versão, URL, bytes, hash e licença próprios. O `catalog_version` é diferente da versão de cada aula e do `schema_version`.

O inventário de disciplinas e suas fontes está em `programas-9-concursos.json`. `catalogo-aulas-planejadas.json` é planejamento editorial, **não o catálogo de arquivos publicados**. Os vínculos de suas famílias com disciplinas são candidatos a revisão; ainda não são cobertura auditada por item.

Criar uma relação editorial `edital_item ↔ lesson_version`, com profundidade, versão de norma/linguagem, estado de revisão e observações. Para uma cobertura real, desmembrar todos os itens/subitens dos programas originais e conferir a matriz contra os PDFs aprovados. Preservar texto original, numeração e fonte. Não considerar que citar uma palavra cobre o assunto.

Arena e flashcards usarão os mesmos IDs de assunto. Questões terão enunciado, tipo, alternativas quando houver, gabarito, comentário, procedência, direitos de uso, banca, ano, revisões e eventual anulação. Flashcards terão frente, verso, referências e vínculos ao assunto. Estes são contratos futuros, não autorização para implementar agora o motor de batalha ou a repetição espaçada.

## Estados e números honestos

Separar publicação (`planejada`, `rascunho`, `em_revisao`, `publicada`, `arquivada`) de disponibilidade local (`nao_baixada`, `baixando`, `disponivel`, `falha`, `atualizacao_disponivel`). A revisão deve registrar resultado, responsável e data; só um recurso aprovado pode ser publicado.

Separar também: **cobertura editorial do edital**, **progresso de leitura** e **domínio demonstrado em exercícios**. Hoje não existem PDFs aprovados neste pacote. Logo, não existem aulas publicadas nem cobertura comprovada. Abrir um PDF não demonstra domínio. Se a decomposição do edital não estiver auditada, exibir “cobertura ainda não auditada”, não “100%”.

Enquanto o total de aulas estiver em elaboração, mostrar números objetivos, como “3 aulas publicadas nesta matéria”, e lacunas conhecidas. Evitar percentuais calculados sobre um planejamento incompleto. Nunca importar as categorias de dificuldade do concurso como atributo de dificuldade de cada aula.

## Download e catálogo resilientes

Validar esquema, IDs únicos, referências, status e compatibilidade antes de substituir o catálogo ativo. Manter o anterior se o novo for inválido. Usar ETag/Last-Modified quando disponíveis, timeout e cancelamento. Não depender de um check de internet separado: tratar o resultado da operação solicitada.

Baixar para arquivo temporário, impor limites configuráveis, conferir tamanho declarado e SHA-256 e concluir por renomeação atômica. Validar caminhos e URLs e tratar redirects do provedor; permitir apenas hosts previamente aprovados na configuração, incluindo os hosts efetivos usados pelos downloads de Releases. Não executar scripts fornecidos pelo catálogo. SHA-256 verifica integridade; um hash no mesmo catálogo comprometido não autentica o editor. Assinatura do catálogo pode ser uma evolução posterior.

Guardar versões dos arquivos em diretório de dados/cache do sistema operacional. Em apps com backend nativo, priorizar a camada nativa para downloads persistentes, evitando limites de CORS e armazenamento de WebView. Em um app totalmente web, verificar CORS de catálogo e arquivos no ambiente real. Não pedir que o usuário desative segurança do navegador.

Permitir ver e limpar downloads, mostrar uso em disco e remover um PDF sem apagar notas/progresso. Uma atualização não marca a nova edição como lida. Notas ancoradas em uma página antiga continuam vinculadas à versão antiga; migração automática exige prova de correspondência.

## Leitor e registro de estudo

Usar o leitor compatível com a stack existente. Se for web, PDF.js pode ser distribuído localmente para não depender de CDN. Disponibilizar índice quando existir no PDF, páginas, zoom, pesquisa textual quando o arquivo permitir, retorno à última página e favoritos. Para PDF digitalizado sem texto, explicar a limitação; OCR não faz parte desta entrega.

Interface escura e leitura com fundo configurável. Não inverter indiscriminadamente imagens, gráficos e código do PDF. Notas em painel lateral ou recolhível. Edição de conteúdo do PDF e anotações desenhadas na própria página são etapas opcionais futuras, não pré-requisitos.

“Estudar esta aula” reutiliza o registro e o cronômetro existentes: matéria e assunto preenchidos, tempo desejado configurável, pausa e encerramento. O cronômetro flutuante deve refletir a mesma sessão, não criar outra. Registrar minutos uma única vez. Perguntar ou pausar quando o app for suspenso conforme comportamento já existente. Não contar tempo enquanto o usuário só deixa o leitor aberto.

RPG discreto: feedback por sessões reais e marcos de estudo, conforme regras já existentes. Não conceder XP repetidamente por abrir, baixar ou clicar em concluir a mesma aula. Nunca bloquear uma aula porque o personagem não tem nível, roupa ou equipamento.

## Publicação e revisão

Materiais autorais em fonte editável, por exemplo Markdown, com imagens licenciadas e exportação reprodutível para PDF. Decidir separadamente a licença do código e a licença do conteúdo. CC BY ou CC BY-SA podem ser consideradas para conteúdo próprio; não escolher uma licença em nome de autores terceiros.

Pipeline editorial: identificar item e pré-requisitos → escrever aula → testar exemplos → conferir fontes e versões → revisão técnica e didática por pessoa identificada → renderizar/inspecionar PDF → publicar recurso versionado → atualizar catálogo → auditar cobertura.

Um gerador de PDFs não gera conhecimento confiável por si só. Não republicar apostilas comerciais, PDFs de terceiros ou bancos de questões sem autorização. Para IA ajudar na autoria, usar a ferramenta/assinatura já disponível e revisão posterior; o aplicativo não precisa de IA embutida nem de API paga para servir aulas, corrigir questões com gabarito ou mostrar flashcards.

## Etapas seguintes

Primeiro entregar uma trilha pequena real, leitor, download, catálogo, sessões e experiência offline. Depois ampliar os PDFs por prioridade do edital-alvo e revisar cobertura dos nove programas. Só então integrar Arena e flashcards, com questões revisadas e registros automáticos de acertos/erros. Um backend dinâmico passa a fazer sentido para moderação, contas, publicação multiusuário ou sincronização; não para abrir um PDF.
