# RUMO — Campo de Treinamento, primeira etapa

Pacote preparado em 11/10/2026 para implementar aulas em PDF dentro do RUMO. Arena de questões e flashcards compartilham os assuntos, mas ficam para etapas seguintes.

## Começar no projeto

Extraia esta pasta para `docs/campo-de-treinamento/` no seu projeto. Cole no agente este comando em linguagem natural:

> Leia `docs/campo-de-treinamento/PROMPT_IMPLEMENTACAO_CAMPO.md` e os arquivos que ele referencia. Implemente o Campo de Treinamento integrado ao RUMO, seguindo a stack e as instruções existentes. Comece inspecionando o projeto e mantenha a identidade preto e dourado suave. O catálogo enviado é planejamento; não finja que os PDFs já existem. Entregue o fluxo completo de catálogo, download, leitura offline e sessão de estudo, com validação real. Arena e flashcards ficam para a próxima etapa.

Para autoria de conteúdo, usar `PROMPT_CRIACAO_AULAS.md` **por aula**, com os itens de edital e versões selecionados. Não pedir uma biblioteca inteira em uma única geração.

## O que há neste pacote

- `PESQUISA_9_CONCURSOS.md`: nove edições, cargos, dificuldade relativa, disciplinas, diferenças relevantes e fontes oficiais.
- `programas-9-concursos.json`: inventário rastreável dos blocos de disciplinas dos nove perfis.
- `disciplinas-por-concurso.csv`: mesma relação em formato para consulta/importação.
- `CATALOGO_DE_AULAS.md` e `catalogo-aulas-planejadas.json`: 60 famílias e 267 sugestões iniciais de aulas, com referências candidatas para conferência editorial.
- `ARQUITETURA_E_INTEGRACAO.md`: catálogo público, PDF sob demanda, dados locais e funcionamento offline.
- `PROMPT_IMPLEMENTACAO_CAMPO.md`: especificação para o agente no projeto.
- `PROMPT_CRIACAO_AULAS.md`: didática, autoria, pesquisa, fontes e revisão.
- `PROMPT_AUDITORIA_CURRICULO.md`: decomposição de todos os itens/subitens e conferência da matriz de cobertura.
- `exemplo-manifesto.json`: exemplo de contrato para conteúdo; apenas planejado, sem URLs fictícias.

## Limites importantes da pesquisa

As categorias fácil/intermediário/difícil são editoriais e relativas ao conjunto; não são uma previsão de aprovação. A janela pesquisada é a dos últimos dez anos; as nove seleções escolhidas são de 2022 a 2024. Cada edital foi recortado para **um cargo/perfil de TI**, incluindo as matérias gerais exigidas desse perfil.

Os 80 blocos de disciplinas se repetem entre provas; não significam 80 matérias únicas. As 60 famílias e 267 sugestões são uma organização inicial, não equivalências auditadas nem um total definitivo. Item a item, pode ser necessário criar outras aulas e complementos. Novos editais podem acrescentar assuntos fora desta amostra.

Este pacote não contém aulas PDF autorais prontas, banco de questões ou flashcards. Não existe cobertura pedagógica completa aprovada. A meta é produzir aulas para todos os itens dos perfis selecionados, verificando versões e retificações antes da publicação.

## Sequência recomendada

1. Implementar e validar catálogo, biblioteca, leitor, downloads e sessão usando material de teste claramente identificado.
2. Produzir e revisar uma pequena trilha real de bancos de dados, publicar PDFs e usá-los no ciclo.
3. Priorizar novas aulas pelo seu edital-alvo; auditar cobertura e expandir o acervo.
4. Integrar Arena com questões e gabaritos revisados e acertos/erros automáticos.
5. Integrar flashcards e revisão espaçada aos mesmos assuntos e às evidências de dificuldade.

O projeto pode evoluir sem esperar centenas de aulas. Uma aula útil, revisada e estudada vale mais que um catálogo cheio de PDFs sem validação.
