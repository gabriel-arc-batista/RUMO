# Prompt para completar o currículo item a item

No RUMO, queremos ter aulas para cada item dos programas dos nove cargos/perfis selecionados. O pacote já identifica as disciplinas e sugere famílias/aulas, mas ainda não certifica correspondência de cada subitem nem contém PDFs autorais publicados.

Leia `programas-9-concursos.json`, `PESQUISA_9_CONCURSOS.md` e `catalogo-aulas-planejadas.json`. Pesquise na internet e obtenha os editais oficiais pelas URLs registradas e pelas páginas oficiais de cada seleção. Confira as retificações aplicáveis ao programa de TI. Não usar blogs ou memória do modelo como fonte do texto normativo. Se uma URL bloquear acesso, procurar outra cópia na instituição/banca oficial. Se não conseguir, registrar essa fonte como pendente; não inventar o programa.

Selecione exatamente o cargo/perfil registrado, incluindo conhecimentos gerais exigidos dele. Não misturar conteúdos exclusivos de outros cargos. Atenção ao BB Agente de Tecnologia, Caixa TBN-TI, UFABC Técnico de TI, DATAPREV Desenvolvimento de Software, TSE Cargo17, BACEN Cargo2, STN Transformação Digital e Senado Análise de Sistemas. SERPRO é Analista–Tecnologia.

Desmembrar todos os itens e subitens preservando texto de referência, hierarquia, numeração, fonte, edição, cargo e versão. Extração automática de PDF pode quebrar palavras, juntar colunas e atravessar cargos: conferir com a página renderizada quando houver dúvida. Não confiar só em regex ou OCR sem inspeção. IDs devem permanecer estáveis após correções.

Criar a matriz editorial muitos-para-muitos de itens e aulas: cada item tem conteúdo exigido, pré-requisitos, profundidade, normas/tecnologias específicas e aulas necessárias. Uma família do planejamento pode precisar de mais módulos. Se um item não estiver atendido pelas sugestões, criar a lacuna e propor novas aulas; não descartar termos menores, leis, frameworks ou versões por parecerem pouco importantes.

Reutilizar fundamentos entre editais e adicionar complementos identificados quando a profundidade ou a versão mudar. Revisar separadamente ITIL3/4, COBIT5/2019, edições ISO, Java, SDKs, linguagens, normativos CNJ e legislação. Não declarar equivalência histórica sem justificativa.

Entregar dados estruturados, um inventário legível de lacunas e fontes/retificações verificadas. Estado inicial das aulas: planejadas. Estado de cobertura: pendente até o conteúdo autoral ter sido produzido e revisado. Auditar contagens e garantir que todo item do recorte tenha uma associação planejada ou uma lacuna explícita. Uma aula publicada só pode ser contada como cobertura após revisão de seu conteúdo; mera ocorrência de palavra no título não basta.

Este trabalho organiza o acervo; não autoriza gerar todas as aulas sem revisão ou publicar materiais comerciais. Depois da matriz, produzir uma trilha pequena usando `PROMPT_CRIACAO_AULAS.md` e validar no leitor antes de expandir.
