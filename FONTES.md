# Referências da atualização 1.4.0

Pesquisa e revisão: 10/10/2026. O aplicativo continua nativo em Tk/SQLite; as referências orientam a composição, sem copiar marcas, imagens ou componentes proprietários.

> Reforma visual 2026-10: as referências de design abaixo foram substituídas pelas de `docs/RUMO_DESIGN.md`. A tabela fica como registro histórico da 1.4.0.

| Referência de design | Aplicação no RUMO — Estudos |
|---|---|
| [Estudei — tutoriais oficiais](https://wp.estudei.com.br/tutoriais/) | Indicadores de estudo, constância, progresso por matéria, organização do foco e relógio circular. |
| [Linear — apresentação do novo design](https://linear.app/now/how-we-redesigned-the-linear-ui) | Hierarquia de fundo, superfícies e campos; navegação lateral; alinhamento; redução de ruído e listas com separadores discretos. |
| [Material Design 3 — campos](https://github.com/material-components/material-web/blob/main/docs/components/text-field.md) e [diálogos](https://github.com/material-components/material-web/blob/main/docs/components/dialog.md) | Rótulos externos, estados de foco, busca na seleção, agrupamento de campos e separação da ação principal do cancelamento. |

O dourado identifica ações e progresso; conclusão usa verde como estado. Fundo, painéis e campos têm três tons escuros. Animações de entrada, hover e abertura são finitas e podem ser desativadas. Não existe navegador embutido.

# Edital e provas

Os 287 registros do edital original (130 TI e 157 Economia) foram preservados. O guia pedagógico tem 565 desdobramentos TI e 525 Economia: 1.090 no total. A revisão adiciona 81 itens nas duas áreas, com evidências vinculadas ao assunto. Dois desses acréscimos registram a retificação da lei de conflito de interesses.

- [Edital de abertura BACEN 2024 — BCB](https://bcb.gov.br/content/acessoinformacao/analista_2024/Edital-n-1-de-Abertura-do-concurso.pdf), seção 18.
- [Edital com retificações até o edital nº 4 — Cebraspe](https://cdn.cebraspe.org.br/concursos/bcb_24/arquivos/ED_1_BCB_23_ABERTURA_ATUALIZADO_RET_4.PDF). No item 9 de Direito Administrativo, a referência correta é **Lei 12.813/2013**. O registro original contém 11.813/2013 e exibe aviso de correção; não é apagado, pois pode ter histórico associado. Os dois PDFs ficam disponíveis offline.
- [BACEN 2024 — conhecimentos básicos](https://cdn.cebraspe.org.br/concursos/bcb_24/arquivos/959_BCB_CB1_01.PDF).
- [BACEN 2024 — conhecimentos específicos TI](https://cdn.cebraspe.org.br/concursos/bcb_24/arquivos/959_BCB_002_01.PDF).
- [BACEN 2024 — conhecimentos específicos Economia](https://cdn.cebraspe.org.br/concursos/bcb_24/arquivos/959_BCB_001_01.PDF).
- [BACEN 2024 — padrão definitivo atualizado da discursiva TI](https://cdn.cebraspe.org.br/concursos/bcb_24/arquivos/BCB_24_PADRO_DE_RESPOSTA_DEFINITIVO_CARGO_2_ATUALIZADO.PDF).
- [STJ 2024 — Análise de Sistemas](https://cdn.cebraspe.org.br/concursos/stj_24/arquivos/018_STJ_003_01.PDF) e [Suporte de TI](https://cdn.cebraspe.org.br/concursos/stj_24/arquivos/018_STJ_018_01.PDF), usados como comparação de provas similares, dentro dos tópicos previstos no BACEN.

Exemplos acrescentados: rastreamento de recursão em Java; `len()` em Python; CRI, Pod, Node e manifests Kubernetes; tipos de métricas Prometheus; sharding; dependências funcionais/multivaloradas; HTTP 429 e XXE; distinção entre entrega e implantação contínua. Em Economia, incluem VAR, efeitos fixos/aleatórios, lei de Walras, APT, duration/convexidade e contingências no Cosif.

O guia anterior era predominantemente um desdobramento pedagógico autoral dos tópicos do edital. A revisão acrescenta identificação de prova e questão nos itens com evidência encontrada. **Não foi feito um inventário de todas as provas históricas**, e os termos amplos do edital não permitem prometer uma lista exaustiva. Não se usou edital novo. Questões Certo/Errado identificam temas cobrados; suas afirmações não são automaticamente conteúdo teórico correto. Confira o gabarito definitivo ao resolver questões, e o padrão atualizado no caso de itens discursivos anulados.

`assets/bacen2024-detalhado.json` registra fontes, data, escopo e evidências por nome. `scripts/syllabus_evidence.py` reproduz os acréscimos. A aplicação associa a evidência ao ID estável do assunto sem mudar os estudos existentes.

# Coleção de 150 frases

Uma frase por data local, ciclo de 150 dias. Cada entrada contém autor, trecho em português, obra/versículo, URL da fonte e natureza da atribuição. São traduções próprias de trechos; não são transcrições literais de edições modernas em português. Relatos de Plutarco e atribuições tradicionais bíblicas são apresentados como tais.

| Autor ou tradição | Quantidade | Fonte |
|---|---:|---|
| Jesus nos Evangelhos | 20 | [Bíblia, KJV em domínio público](https://www.gutenberg.org/ebooks/10) |
| Salomão, atribuição tradicional | 15 | [Provérbios/Eclesiastes](https://www.gutenberg.org/ebooks/10) |
| Davi, atribuição tradicional | 5 | [Salmos](https://www.gutenberg.org/ebooks/10) |
| Epicteto | 20 | [Manual](https://www.gutenberg.org/ebooks/45109) |
| Confúcio | 20 | [Analectos](https://www.gutenberg.org/ebooks/3330) |
| Laozi, tradição textual | 20 | [Tao Te Ching](https://www.gutenberg.org/ebooks/216) |
| Benjamin Franklin | 20 | [The Way to Wealth](https://www.gutenberg.org/ebooks/43855) |
| Marco Aurélio | 10 | [Meditações, tradução de George Long](https://classics.mit.edu/Antoninus/meditations.html) |
| Francis Bacon | 6 | [Ensaios — Of Studies](https://www.gutenberg.org/ebooks/575) |
| Charles Darwin | 4 | [A origem das espécies](https://www.gutenberg.org/ebooks/1228) |
| Abraham Lincoln | 4 | [Segundo discurso de posse — Library of Congress](https://www.loc.gov/exhibits/lincoln/healing-the-nations-wounds.html) |
| Júlio César, relato de Plutarco | 1 | [Vida de César, 50](https://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Atext%3A1999.03.0078%3Atext%3DCaes.) |
| Alexandre, relato de Plutarco | 1 | [Sobre a fortuna ou virtude de Alexandre, I.10](https://atlas.perseus.tufts.edu/library/passage/urn%3Acts%3AgreekLit%3Atlg0007.tlg087.perseus-eng4%3A1.9-1.10/) |
| Albert Einstein | 2 | [The Ultimate Quotable Einstein — Princeton](https://assets.press.princeton.edu/chapters/s10176.pdf) |
| J. Robert Oppenheimer | 1 | [Entrevista NBC de 1965 — Atomic Archive](https://www.atomicarchive.com/media/videos/oppenheimer.html) |
| Marie Curie | 1 | [Conferência Nobel de 1911](https://www.nobelprize.org/prizes/chemistry/1911/marie-curie/lecture/) |

Corpus e referências: `assets/quotes.json`; geração reproduzível: `scripts/prepare_quotes.py`. O conjunto é carregado uma vez e as fontes externas só abrem quando você solicita.

A ordem de aprendizagem é uma curadoria pedagógica local em `learning.py`, e não uma ordem atribuída ao edital. Fundamentos precedem aplicações; modelos relacionais precedem SQL, e estruturas básicas precedem orientação a objetos. O texto oficial, a hierarquia e os identificadores não são alterados. Fonte Inter: https://github.com/rsms/inter/releases/tag/v4.1.
