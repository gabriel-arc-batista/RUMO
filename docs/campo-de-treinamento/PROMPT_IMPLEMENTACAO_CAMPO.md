# Prompt para implementar a primeira etapa no RUMO

Você está trabalhando no projeto **RUMO**, um aplicativo executável local de organização de estudos com ciclos, cronômetro, estatísticas e elementos de RPG. Quero adicionar um sistema de conteúdo começando pelo **Campo de Treinamento**, o lugar de estudar aulas em PDF. A futura **Arena** será o lugar de responder questões; flashcards serão uma área de revisão. Nesta entrega implemente o Campo de Treinamento e a estrutura compartilhada; Arena e flashcards ficam para entregas posteriores.

Leia antes os arquivos deste pacote, principalmente `ARQUITETURA_E_INTEGRACAO.md`, `programas-9-concursos.json`, `CATALOGO_DE_AULAS.md` e `catalogo-aulas-planejadas.json`. Eles contêm o inventário de matérias gerais e específicas de nove perfis, links dos programas oficiais e um catálogo editorial. Leia os PDFs oficiais para obter e conferir todos os itens/subitens; não presuma que os títulos das famílias substituem esse trabalho. Não confunda planejamento com PDFs publicados. Não use dados de outros cargos da mesma seleção.

## 1. Examine o projeto e preserve suas integrações

Leia as instruções do repositório e identifique stack, persistência, navegação, design system, leitor disponível, sessão de estudo, cronômetro flutuante, ciclos, estatísticas, recompensas e formato do executável. Faça uma inspeção das telas atuais antes de editar. Implemente na tecnologia existente; não converta todo o app para sua stack preferida, não substitua a navegação e não crie uma aplicação paralela. Preserve dados e prepare migrações compatíveis quando necessárias.

Explique sucintamente as decisões derivadas dessa inspeção e avance na implementação. Não pare apenas para entregar um plano. Se uma informação externa indispensável estiver ausente, como endereço real de hospedagem, implemente o adaptador configurável e o modo local; não invente uma URL funcionando ou bloqueie todo o trabalho por isso.

## 2. Estrutura do conteúdo

Modele concurso/edição/perfil, disciplina oficial, item/subitem de edital, matéria canônica, assunto, aula e recurso PDF versionado. Aulas e assuntos têm IDs estáveis. Suporte uma aula atendendo vários editais sem duplicar seu arquivo. Uma aula pode ter assunto principal e vínculos adicionais. Não confunda assunto introdutório com cobertura de um item avançado.

Importe os nove programas como fonte editorial rastreável, com URL, edição, cargo, texto original e estado de revisão. Os dados extraídos precisam de conferência antes de declarar cobertura. Desmembrar itens deve conservar hierarquia e numeração e lidar com formatos diferentes das bancas, não depender de uma regex ingênua. Se não for possível desmembrar com confiança nesta etapa, conservar o bloco integral e registrar a decomposição como pendente, sem percentuais inventados.

Importe as 60 famílias e 267 sugestões como **planejamento inicial**, não como uma biblioteca de PDFs existentes nem um total definitivo de aulas. Verifique os números contra o JSON. Preserve as referências candidatas como pendentes de revisão. Não tratar uma família como uma aula única; editar e expandir o currículo deve ser possível.

Preserve versões cobradas: ITILv3/4, COBIT5/2019, edições ISO, Java, Python, bibliotecas e normativos específicos. Não atualize os programas históricos silenciosamente. Uma aula de fundamentos pode ser reaproveitada; complementos e diferenças de versão devem estar claros.

## 3. Experiência visual do Campo de Treinamento

O RUMO usa **preto e dourado**. Mantenha essa identidade com aplicação suave: fundos escuros com diferenças discretas entre camadas, texto legível, dourado reservado a ações e estados importantes, espaçamento consistente e tipografia bem hierarquizada. Use componentes e tokens existentes e refine o necessário. Preserve tema claro se já existir, com modo escuro como experiência completa. O visual deve ser elegante e contemporâneo e o RPG discreto, sem parecer um jogo infantil ou um painel cheio de enfeites.

Não faça uma grade de dezenas de cards iguais, todos com borda dourada, ícones genéricos, barras inventadas e textos decorativos. O protagonismo é do conteúdo e da próxima ação de estudo.

Tela principal: título Campo de Treinamento, continuar última aula, assuntos do ciclo que já tenham conteúdo disponível e busca global. Mostrar edital-alvo atual com opção de trocar ou explorar tudo. Se não houver edital escolhido, a biblioteca continua acessível. Sem cronograma semanal imposto.

Organizar a biblioteca por matéria → assunto → aulas. A visão por edital reutiliza o mesmo acervo. Prefira lista legível, agrupamento e painel de detalhe quando fizer sentido na stack. Mostrar matéria, assunto, título, versão/revisão, páginas e disponibilidade. Tempo de leitura é opcional, identificado como estimativa real; não inventar números. Não transformar a classificação do concurso em nível da aula.

Filtros úteis: matéria, assunto, edital, disponíveis para leitura, baixadas, em andamento, favoritas. Separar plano editorial do acervo disponível: o usuário pode consultar conteúdos planejados, mas eles não entram em “continuar estudando” nem exibem botão Abrir habilitado. Busca deve cobrir nomes e metadados locais, inclusive offline; pesquisa em todo o texto de todos os PDFs é outra funcionalidade.

Detalhe da aula: objetivos, conteúdo, pré-requisitos sugeridos, itens de edital relacionados com estado da cobertura, autor, revisão, fontes, licença, versão e recurso. Disponibilidade local e novas versões claras. Não exigir nível, item de RPG ou concluir pré-requisitos para abrir uma aula publicada.

## 4. Leitor PDF

Abrir dentro do aplicativo com leitor compatível com a stack, distribuído localmente. Oferecer paginação, zoom, ajustar largura/página, índice se disponível, pesquisa textual quando possível, favoritos e retomada da última página. Para arquivo sem camada de texto, informar a limitação da busca. Não implantar OCR sem necessidade nesta fase.

Modo de foco reduz a navegação e mantém controles de leitura acessíveis. Notas ficam em painel recolhível, vinculadas à aula e versão. Sem editor de PDF complexo neste escopo. O fundo do documento pode ser claro mesmo no tema escuro; evite filtros que prejudiquem figuras e código. Controles por teclado, foco visível, contraste e redução de movimento precisam funcionar.

Atualizar PDF preserva notas e posição da versão antiga e sinaliza que as páginas podem mudar. Remover download não remove anotações. Progresso de página e conclusão manual são distintos de domínio do assunto. Abrir última página não marca aprendizado concluído.

## 5. Integrar estudo, ciclo e RPG

Botão “Estudar esta aula” reaproveita a sessão existente, preenchendo matéria, assunto e identificador da aula; usuário define o tempo desejado. Manter pausa, retomada e encerramento conforme o app. Cronômetro flutuante e leitor mostram **a mesma sessão**. Fechar leitor, mudar aula, suspender o computador e relançar o app devem ter comportamento consistente, sem tempo fantasma nem perda da sessão.

Ao encerrar, os minutos vão uma vez para histórico, gráficos, ciclo e recompensas já existentes. Não inventar questões respondidas durante leitura. Não duplicar XP ao receber o mesmo evento duas vezes. Abrir, baixar ou repetir cliques em concluir não devem ser fonte ilimitada de recompensa. Feedback é pequeno e pode ser desativado; nunca interrompe uma leitura com animação de batalha.

## 6. Catálogo online e funcionamento offline

Criar uma interface de provedor de conteúdo com implementação local e remota configurável. Nenhuma conta ou chave de API é necessária para um catálogo público. Metadados por HTTPS; PDFs apenas sob demanda. Sem dependência de um servidor de IA. Use o contrato de exemplo do pacote como referência, ajustando e documentando decisões para a stack real.

Validar esquema, referências, compatibilidade e estados antes de aceitar catálogo. Manter último catálogo válido. Timeout, cancelamento e retomada/retry razoáveis. Download temporário com limites, tamanho/hash e gravação atômica. Tratar redirects reais dos hosts autorizados. Não executar código remoto. Verificar CORS se aplicável e usar backend nativo quando disponível para downloads persistentes. Não criar proxy público aberto.

Aula publicada precisa de revisão aprovada e PDF válido. Rascunhos e planejadas não têm URL fictícia. Mostrar estados: ainda não publicada, precisa baixar, baixando, disponível offline, falha e atualização disponível. Tratar falta de conexão, disco cheio, PDF inválido, catálogo inválido e arquivo removido do host sem quebrar o app.

Gerenciar downloads: tamanho, abrir local, cancelar, tentar novamente, remover e baixar nova versão. Dados pessoais de estudo permanecem locais. Não construir login, painel de contas ou sincronização agora. Se não houver hospedagem configurada, modo local e importação de material próprio devem funcionar, com procedência claramente distinguida do catálogo revisado.

## 7. Autoria e publicação

Preparar a estrutura de um repositório de conteúdo: metadados versionados, aulas em fonte editável, recursos licenciados, instruções de renderização e validação, cobertura editorial e publicação separada. Não é necessário duplicar todos os PDFs no repositório principal do aplicativo. A publicação real depende de endereço e repositório existentes; prepare o resultado local e instruções concretas sem simular deploy bem-sucedido.

O catálogo público pode começar em GitHub Pages e PDFs em Releases. Documente os limites atuais consultando a documentação oficial no momento da implementação. Nunca prometer gratuidade ilimitada. Arquivos e catálogo devem usar versões imutáveis quando publicados.

Esta tarefa não autoriza gerar centenas de PDFs e marcá-los como revisados. Use fixtures claramente identificadas para validar a infraestrutura e, se precisar de um PDF mínimo, faça uma amostra de teste separada, sem alegar cobertura de concurso. Siga o prompt editorial do pacote para produzir depois uma trilha real, revisada por pessoa responsável.

## 8. Preparar Arena e flashcards

Documentar contratos futuros de questão, tentativa, gabarito, comentário, flashcard e revisão vinculados a assuntos e fontes. Aproveitar o armazenamento e tipos existentes. Evitar migrations especulativas se bastar documentar os contratos. Não adicionar telas vazias que pareçam funcionalidades prontas. Se houver entradas de navegação futuras, usar estado indisponível claro e coerente com o padrão atual.

Questões pré-cadastradas com gabarito podem ser corrigidas sem IA. PDFs podem ser servidos sem IA. Flashcards podem ser revisados sem IA. Integração com geração automática de questões é um projeto posterior e não um requisito escondido desta primeira entrega.

## 9. Verificação e entrega

Verifique um fluxo completo: catálogo válido → aula publicada de teste identificada → download → leitor → sessão de estudo → encerramento único → reinício → leitura offline com notas e página preservadas. Testar falha de conexão, catálogo malformado, hash incompatível, cancelamento, atualização de PDF e download removido sem perder notas. Testar idempotência do encerramento e migrações que afetem dados. Use testes adequados para riscos reais; não criar testes triviais apenas para aumentar quantidade.

Faça revisão visual no aplicativo real, tamanhos de janela compatíveis, teclado e temas existentes. Rode build/lint/testes relevantes do repositório e verifique geração do executável se o ambiente permitir. Não afirmar verificação que não fez.

Entregue código integrado, instruções locais, arquivos alterados, limitações reais, passos de publicação e validações realizadas. Documente o que ficou planejado e o que pode ser usado imediatamente. Prioridade é fazer uma sessão de estudo com uma aula funcionar bem; a Arena vem depois.

## Se Claude Code e Codex dividirem o trabalho

Use este prompt como especificação comum. Primeiro combine modelos, estados, eventos e interfaces. Codex pode cuidar de persistência, provedor, download, catálogo e sessão; Claude Code pode cuidar da experiência visual, biblioteca, leitor e estados de interface. Defina arquivos responsáveis antes de editar. Só trabalhar em paralelo quando os contratos estiverem estáveis e os arquivos separados; mudanças de contrato exigem alinhamento. Finalizar com uma integração única e validação ponta a ponta, não apenas duas tarefas isoladas concluídas.
