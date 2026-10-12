/**
 * Catálogo de EXEMPLO para desenvolver o site enquanto o serviço não está
 * publicado. Tudo leva `example: true` e aparece com o selo EXEMPLO; nada
 * aqui é aula, questão ou deck revisado. IDs de edital vêm de
 * docs/campo-de-treinamento/programas-9-concursos.json.
 */
import { parseStatement } from "../../domain/blocks";
import type { Card, Catalog, Deck, Lesson, Question } from "../../domain/types";

const pending = { status: "pendente" as const, reviewer: null, reviewedAt: null };

const subjects = [
  { id: "subject.bancos-dados", name: "Bancos de dados" },
  { id: "subject.eng-software", name: "Engenharia de software" },
  { id: "subject.estruturas-dados", name: "Estruturas de dados e algoritmos" },
  { id: "subject.seguranca", name: "Segurança da informação" },
];

const topics = [
  { id: "topic.bd.modelo-relacional", subjectId: "subject.bancos-dados", parentId: null, name: "Modelo relacional" },
  { id: "topic.bd.sql", subjectId: "subject.bancos-dados", parentId: null, name: "SQL: consultas e junções" },
  { id: "topic.bd.normalizacao", subjectId: "subject.bancos-dados", parentId: null, name: "Normalização" },
  { id: "topic.bd.transacoes", subjectId: "subject.bancos-dados", parentId: null, name: "Transações e concorrência" },
  { id: "topic.es.ageis", subjectId: "subject.eng-software", parentId: null, name: "Métodos ágeis" },
  { id: "topic.es.testes", subjectId: "subject.eng-software", parentId: null, name: "Testes de software" },
  { id: "topic.ed.complexidade", subjectId: "subject.estruturas-dados", parentId: null, name: "Complexidade assintótica" },
  { id: "topic.ed.arvores", subjectId: "subject.estruturas-dados", parentId: null, name: "Árvores" },
  { id: "topic.si.criptografia", subjectId: "subject.seguranca", parentId: null, name: "Criptografia" },
];

const exams = [
  { id: "bacen-2024-ti", name: "BACEN 2024 — Tecnologia da Informação" },
  { id: "caixa-2024-tbn-ti", name: "Caixa 2024 — Tecnologia da Informação" },
  { id: "serpro-2023-tecnologia", name: "SERPRO 2023 — Tecnologia" },
  { id: "dataprev-2024-desenvolvimento", name: "DATAPREV 2024 — Desenvolvimento" },
  { id: "tse-2024-analista-ti", name: "TSE 2024 — Analista de TI" },
];

function lesson(partial: Partial<Lesson> & Pick<Lesson, "id" | "title" | "subjectId">): Lesson {
  return {
    version: "1.0.0",
    versionLabel: "versão 1.0.0 (exemplo)",
    summary: "",
    topicIds: [],
    examIds: [],
    status: "planejada",
    objectives: [],
    prerequisiteTopicIds: [],
    sources: [],
    review: pending,
    pages: null,
    pdfUrl: null,
    outline: [],
    example: true,
    ...partial,
  };
}

const lessons: Lesson[] = [
  lesson({
    id: "exemplo.aula.modelo-relacional",
    title: "Modelo relacional: tabelas, chaves e relações",
    summary: "PDF de exemplo com 20 páginas para testar o leitor. Não é uma aula revisada.",
    subjectId: "subject.bancos-dados",
    topicIds: ["topic.bd.modelo-relacional"],
    examIds: ["bacen-2024-ti", "caixa-2024-tbn-ti", "serpro-2023-tecnologia"],
    status: "disponivel",
    objectives: [
      "Distinguir relação, tupla, atributo e domínio",
      "Identificar chaves candidatas, primária e estrangeira",
      "Explicar a integridade referencial com um exemplo",
    ],
    sources: [
      { title: "E. F. Codd, “A Relational Model of Data for Large Shared Data Banks”, CACM, 1970", url: "https://doi.org/10.1145/362384.362685" },
    ],
    pages: 20,
    pdfUrl: "/pdf/exemplo-modelo-relacional.pdf",
    outline: [
      { title: "Abertura", page: 1 },
      { title: "Relações, tuplas e atributos", page: 2 },
      { title: "Chaves candidatas e primária", page: 4 },
      { title: "Chaves estrangeiras", page: 5 },
      { title: "Diagrama: duas relações", page: 7 },
      { title: "Álgebra relacional: seleção", page: 9 },
      { title: "Junções", page: 11 },
      { title: "Exemplo em SQL", page: 12 },
      { title: "Dependências funcionais", page: 16 },
      { title: "Resumo", page: 19 },
      { title: "Página final", page: 20 },
    ],
  }),
  lesson({
    id: "exemplo.aula.juncoes",
    title:
      "Consultas SQL com junções internas, externas e autojunções aplicadas a cenários de cadastro, atendimento e hierarquia de funcionários",
    summary: "Exemplo com título longo e 12 páginas. Não é uma aula revisada.",
    subjectId: "subject.bancos-dados",
    topicIds: ["topic.bd.sql"],
    examIds: ["bacen-2024-ti", "dataprev-2024-desenvolvimento", "tse-2024-analista-ti"],
    status: "disponivel",
    objectives: ["Comparar junção interna e externa", "Escrever uma autojunção com apelidos"],
    prerequisiteTopicIds: ["topic.bd.modelo-relacional"],
    sources: [{ title: "ISO/IEC 9075 (SQL), parte 2 — referência da linguagem" }],
    pages: 12,
    pdfUrl: "/pdf/exemplo-juncoes-sql.pdf",
    outline: [
      { title: "Abertura", page: 1 },
      { title: "Junção interna", page: 3 },
      { title: "Junção externa", page: 6 },
      { title: "Autojunção", page: 9 },
      { title: "Página final", page: 12 },
    ],
  }),
  lesson({
    id: "exemplo.aula.normalizacao",
    title: "Normalização até a terceira forma normal",
    subjectId: "subject.bancos-dados",
    topicIds: ["topic.bd.normalizacao"],
    examIds: ["bacen-2024-ti", "serpro-2023-tecnologia"],
    objectives: ["Reconhecer dependências funcionais", "Decompor uma relação até a 3FN"],
    prerequisiteTopicIds: ["topic.bd.modelo-relacional"],
  }),
  lesson({
    id: "exemplo.aula.transacoes",
    title: "Transações, propriedades ACID e níveis de isolamento",
    subjectId: "subject.bancos-dados",
    topicIds: ["topic.bd.transacoes"],
    examIds: ["bacen-2024-ti", "tse-2024-analista-ti"],
    objectives: ["Explicar as propriedades ACID", "Relacionar anomalias e níveis de isolamento"],
  }),
  lesson({
    id: "exemplo.aula.scrum",
    title: "Scrum: papéis, eventos e artefatos",
    subjectId: "subject.eng-software",
    topicIds: ["topic.es.ageis"],
    examIds: ["caixa-2024-tbn-ti", "dataprev-2024-desenvolvimento"],
  }),
  lesson({
    id: "exemplo.aula.complexidade",
    title: "Notação assintótica e recorrências",
    subjectId: "subject.estruturas-dados",
    topicIds: ["topic.ed.complexidade"],
    examIds: ["serpro-2023-tecnologia", "tse-2024-analista-ti"],
  }),
];

const certoErrado = [
  { id: "certo", text: "Certo" },
  { id: "errado", text: "Errado" },
];

function question(
  partial: Omit<Question, "statement" | "version" | "example" | "annulled" | "provenance"> & {
    text: string;
    annulled?: boolean;
  },
): Question {
  const { text, ...rest } = partial;
  return {
    version: "1.0.0",
    example: true,
    annulled: false,
    provenance: { kind: "autoral", label: "Questão autoral de exemplo (sem revisão)" },
    statement: parseStatement(text),
    ...rest,
  };
}

const questions: Question[] = [
  question({
    id: "exemplo.q.left-join",
    type: "multipla_escolha",
    subjectId: "subject.bancos-dados",
    topicIds: ["topic.bd.sql"],
    examIds: ["bacen-2024-ti", "dataprev-2024-desenvolvimento"],
    text:
      "A tabela `cliente` tem 4 linhas e a tabela `pedido` tem 6 linhas. Dois clientes não têm pedidos; os demais têm 3 pedidos cada. Quantas linhas a consulta abaixo devolve?\n\n```sql\nSELECT c.id, p.id\nFROM cliente c\nLEFT JOIN pedido p ON p.cliente_id = c.id;\n```",
    options: [
      { id: "a", text: "4" },
      { id: "b", text: "6" },
      { id: "c", text: "8" },
      { id: "d", text: "10" },
      { id: "e", text: "24" },
    ],
  }),
  question({
    id: "exemplo.q.fk",
    type: "certo_errado",
    subjectId: "subject.bancos-dados",
    topicIds: ["topic.bd.modelo-relacional"],
    examIds: ["bacen-2024-ti", "caixa-2024-tbn-ti"],
    text: "No modelo relacional, uma chave estrangeira deve referenciar uma chave candidata da relação referenciada.",
    options: certoErrado,
  }),
  question({
    id: "exemplo.q.3fn",
    type: "multipla_escolha",
    subjectId: "subject.bancos-dados",
    topicIds: ["topic.bd.normalizacao"],
    examIds: ["serpro-2023-tecnologia"],
    text: "Uma relação está na terceira forma normal (3FN) quando, além de estar na 2FN:",
    options: [
      { id: "a", text: "não possui atributos multivalorados" },
      { id: "b", text: "nenhum atributo não chave depende transitivamente da chave primária" },
      { id: "c", text: "todo determinante é chave candidata" },
      { id: "d", text: "não possui dependências multivaloradas não triviais" },
    ],
  }),
  question({
    id: "exemplo.q.recorrencia",
    type: "multipla_escolha",
    subjectId: "subject.estruturas-dados",
    topicIds: ["topic.ed.complexidade"],
    examIds: ["serpro-2023-tecnologia", "tse-2024-analista-ti"],
    text: "Considere a recorrência do merge sort:\n\n$$T(n) = 2\\,T\\left(\\frac{n}{2}\\right) + \\Theta(n)$$\n\nQual é a sua solução assintótica?",
    options: [
      { id: "a", text: "Θ(n)" },
      { id: "b", text: "Θ(n log n)" },
      { id: "c", text: "Θ(n²)" },
      { id: "d", text: "Θ(log n)" },
    ],
  }),
  question({
    id: "exemplo.q.serializavel",
    type: "certo_errado",
    subjectId: "subject.bancos-dados",
    topicIds: ["topic.bd.transacoes"],
    examIds: ["bacen-2024-ti", "tse-2024-analista-ti"],
    text: "O nível de isolamento SERIALIZABLE, definido no padrão SQL, impede leituras sujas, leituras não repetíveis e leituras fantasmas.",
    options: certoErrado,
  }),
  question({
    id: "exemplo.q.product-owner",
    type: "multipla_escolha",
    subjectId: "subject.eng-software",
    topicIds: ["topic.es.ageis"],
    examIds: ["caixa-2024-tbn-ti", "dataprev-2024-desenvolvimento"],
    text: "No Scrum, quem é responsável por ordenar os itens do Product Backlog?",
    options: [
      { id: "a", text: "Scrum Master" },
      { id: "b", text: "Product Owner" },
      { id: "c", text: "Developers" },
      { id: "d", text: "Stakeholders, por votação" },
    ],
  }),
  question({
    id: "exemplo.q.anulada",
    type: "certo_errado",
    subjectId: "subject.eng-software",
    topicIds: ["topic.es.testes"],
    examIds: ["dataprev-2024-desenvolvimento"],
    annulled: true,
    text: "Exemplo de questão anulada: testes de regressão só devem ser executados ao fim do projeto.",
    options: certoErrado,
  }),
  question({
    id: "exemplo.q.arvore-b",
    type: "multipla_escolha",
    subjectId: "subject.estruturas-dados",
    topicIds: ["topic.ed.arvores"],
    examIds: ["serpro-2023-tecnologia", "bacen-2024-ti"],
    text:
      "Exemplo de enunciado extenso. Um sistema de arquivos precisa indexar milhões de registros armazenados em disco, onde cada acesso a um bloco custa muito mais do que operações em memória principal. A equipe compara estruturas de índice considerando o número de acessos a disco por busca, a manutenção do balanceamento após inserções e remoções frequentes e a possibilidade de percorrer intervalos de chaves em ordem.\n\nCada nó do índice ocupa exatamente um bloco de disco e pode armazenar muitas chaves. A equipe quer manter todas as folhas no mesmo nível e permitir varreduras sequenciais eficientes entre folhas vizinhas.\n\nQual estrutura atende melhor a esses requisitos?",
    options: [
      { id: "a", text: "Árvore binária de busca sem balanceamento" },
      { id: "b", text: "Árvore AVL com um registro por nó" },
      { id: "c", text: "Árvore B+ com folhas encadeadas" },
      { id: "d", text: "Tabela hash com endereçamento aberto" },
      { id: "e", text: "Lista encadeada ordenada" },
    ],
  }),
  question({
    id: "exemplo.q.assimetrica",
    type: "certo_errado",
    subjectId: "subject.seguranca",
    topicIds: ["topic.si.criptografia"],
    examIds: ["bacen-2024-ti", "serpro-2023-tecnologia"],
    text: "Na criptografia assimétrica, para garantir a confidencialidade de uma mensagem, o remetente cifra o conteúdo com a chave pública do destinatário.",
    options: certoErrado,
  }),
];

/** Gabarito e comentário: no serviço real ficam privados; aqui só o servidor de exemplo lê. */
export const EXAMPLE_ANSWERS: Record<string, { answer: string; comment: string }> = {
  "exemplo.q.left-join": {
    answer: "c",
    comment:
      "Os dois clientes com pedidos geram 3 linhas cada (6). A junção externa à esquerda preserva os dois clientes sem pedido, com p.id nulo (+2). Total: 8.",
  },
  "exemplo.q.fk": {
    answer: "certo",
    comment: "A chave estrangeira referencia uma chave candidata (em geral, a primária) da relação referenciada.",
  },
  "exemplo.q.3fn": {
    answer: "b",
    comment: "A 3FN elimina dependências transitivas de atributos não chave. “Todo determinante é chave candidata” define a FNBC.",
  },
  "exemplo.q.recorrencia": {
    answer: "b",
    comment: "Pelo teorema mestre, a = 2, b = 2 e f(n) = Θ(n) = Θ(n^log_b a): caso 2, T(n) = Θ(n log n).",
  },
  "exemplo.q.serializavel": {
    answer: "certo",
    comment: "SERIALIZABLE é o nível mais estrito do padrão e não admite nenhuma das três anomalias.",
  },
  "exemplo.q.product-owner": {
    answer: "b",
    comment: "O Product Owner é responsável pelo Product Backlog, inclusive pela ordenação dos itens.",
  },
  "exemplo.q.anulada": { answer: "errado", comment: "Questão anulada no exemplo: não conta como acerto nem como erro." },
  "exemplo.q.arvore-b": {
    answer: "c",
    comment:
      "A árvore B+ é balanceada, tem nós do tamanho de um bloco com muitas chaves (poucos acessos a disco) e folhas encadeadas, o que favorece varreduras por intervalo.",
  },
  "exemplo.q.assimetrica": {
    answer: "certo",
    comment: "Só a chave privada do destinatário decifra o que foi cifrado com a pública dele.",
  },
};

const decks: Deck[] = [
  {
    id: "exemplo.deck.sql",
    title: "SQL essencial",
    description: "Deck de exemplo sobre junções e agregações.",
    subjectId: "subject.bancos-dados",
    topicId: "topic.bd.sql",
    personal: false,
    example: true,
  },
  {
    id: "exemplo.deck.complexidade",
    title: "Complexidade e recorrências",
    description: "Deck de exemplo com notação assintótica.",
    subjectId: "subject.estruturas-dados",
    topicId: "topic.ed.complexidade",
    personal: false,
    example: true,
  },
  {
    id: "exemplo.deck.vazio",
    title: "Segurança: em preparação",
    description: "Deck de exemplo ainda sem cartões, para conferir o estado vazio.",
    subjectId: "subject.seguranca",
    topicId: "topic.si.criptografia",
    personal: false,
    example: true,
  },
];

function card(id: string, deckId: string, front: string, back: string, explanation = "", source = ""): Card {
  return {
    id,
    version: "1.0.0",
    deckId,
    front,
    back,
    explanation,
    source,
    lessonId: null,
    questionId: null,
    suspended: false,
    deleted: false,
    personal: false,
    example: true,
  };
}

const cards: Card[] = [
  card("exemplo.c.inner", "exemplo.deck.sql", "O que a junção interna (INNER JOIN) devolve?", "Só as combinações de linhas que satisfazem a condição de junção.", "Linhas sem correspondência dos dois lados ficam de fora.", "Exemplo: modelo relacional, p. 11"),
  card("exemplo.c.left", "exemplo.deck.sql", "O que muda no LEFT JOIN em relação ao INNER JOIN?", "Todas as linhas da tabela à esquerda são preservadas.", "Quando não há correspondência, as colunas da direita vêm nulas.", "Exemplo: junções em SQL, p. 6"),
  card("exemplo.c.having", "exemplo.deck.sql", "Qual a diferença entre WHERE e HAVING?", "WHERE filtra linhas antes do agrupamento; HAVING filtra grupos depois dele.", "", ""),
  card("exemplo.c.count", "exemplo.deck.sql", "COUNT(coluna) conta valores nulos?", "Não. COUNT(*) conta linhas; COUNT(coluna) ignora nulos.", "", ""),
  card("exemplo.c.bigo", "exemplo.deck.complexidade", "O que significa f(n) = O(g(n))?", "Existe c > 0 e n₀ tal que f(n) ≤ c·g(n) para todo n ≥ n₀.", "É um limite superior assintótico.", ""),
  card("exemplo.c.mestre", "exemplo.deck.complexidade", "Solução de T(n) = 2T(n/2) + Θ(n)?", "Θ(n log n)", "Caso 2 do teorema mestre.", ""),
  card("exemplo.c.busca-binaria", "exemplo.deck.complexidade", "Complexidade da busca binária num vetor ordenado?", "O(log n)", "A cada passo, metade do intervalo é descartada.", ""),
];

export const EXAMPLE_CATALOG: Catalog = {
  example: true,
  subjects,
  topics,
  exams,
  lessons,
  questions,
  decks,
  cards,
};
