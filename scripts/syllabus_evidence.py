"""Explicit additions grounded in the official BCB/STJ 2024 papers.

Each line: official section | study detail | question numbers | source paper.
No exam statement is copied as an answer: questions may be false or annulled.
"""

import re

BCB = "https://cdn.cebraspe.org.br/concursos/bcb_24/arquivos/"
STJ = "https://cdn.cebraspe.org.br/concursos/stj_24/arquivos/"
ADDITIONS = {
    "Ciência De Dados": """1|Validação K-fold: separação de treino, validação e teste|52,54|BCB-TI
2|Descida de gradiente e retropropagação no treinamento|53|BCB-TI
3|Bag of Words: frequência, ordem e contexto das palavras|51|BCB-TI
4|HDFS: NameNode, DataNode e checkpoints do Secondary NameNode|55|BCB-TI
6|Transferência indutiva e transdutiva: domínios e tarefas|58|BCB-TI
7|Temperature, diversidade da geração e configuração de threads|59,60|BCB-TI
8|LSTM, redes recorrentes e dependências de longo prazo|61|BCB-TI""",
    "Segurança Da Informação": """1|SAML: sujeito, provedor de identidade e provedor de serviço|65,66|BCB-TI
4|Fuzzing: entradas inesperadas e análise de falhas|67|BCB-TI
5|MFA adaptativa: contexto, localização e tentativas de acesso|69,70|BCB-TI
7|NIST CSF 2.0: Govern, Identify, Protect, Detect, Respond e Recover|71|BCB-TI""",
    "Engenharia De Software": """1|HTTP/2: multiplexação e transporte usado pelo gRPC|74,75|BCB-TI
1|WebSocket: comunicação bidirecional orientada a mensagens|72|BCB-TI
2|DevOps: plan, code, build, test, release, deploy, operate e monitor|Discursiva P4|BCB-DISC
2|Entrega contínua versus implantação contínua e intervenção humana|Discursiva P4|BCB-DISC
2|Shift-left: antecipação de testes e segurança|Discursiva P4|BCB-DISC
3|HTTP 429, limitação de requisições e proteção contra abuso|78|BCB-TI
3|XXE: entidades externas XML e configurações seguras de parser|79|BCB-TI
5|Serverless: responsabilidades, BaaS e FaaS orientado a eventos|82,83,84,85,86|BCB-TI
7|Diferença entre execução sequencial, concorrente e assíncrona|87|BCB-TI
8|REST stateless e diferenças entre consultas GraphQL e SQL|89,90|BCB-TI
10|Abstract Factory, Facade, Composite, Decorator e Memento|91,92|BCB-TI
12|Java: rastreamento de chamadas recursivas e caso base|94|BCB-TI
12|Python: len() em strings, listas e dicionários|95|BCB-TI
11|Git: clone, branches, merge, resolução de conflitos e Gitflow|67,71,72|STJ-ANALISE""",
    "Infraestrutura Em Ti": """2|Kubernetes: Pod, Node, kubelet, kube-scheduler e autoscaling|82,83,96,98|BCB-TI
2|Manifests YAML: diferença entre Service e Deployment|96|BCB-TI
2|Runtimes CRI-O e containerd e independência do Docker|99|BCB-TI
4|Prometheus: counter, gauge, histogram e summary|101|BCB-TI
4|Grafana: fontes de dados, consultas e dashboards|100|BCB-TI
4|APM: traces, taxas de erro e requisições HTTP 500|102|BCB-TI
5|LDAP e integração com serviços de diretório|104|BCB-TI
6|Failover versus failback e recuperação da disponibilidade|107,108|BCB-TI
8|Live migration e migração de memória com pré-cópia|105|BCB-TI
9|Linux: dpkg, apt e resolução de dependências|112|BCB-TI
9|Windows Admin Center e administração remota do servidor|110|BCB-TI
2|etcd: armazenamento do estado e configuração do cluster|75|STJ-ANALISE""",
    "Bancos De Dados": """1|Sharding em NoSQL: particionamento e balanceamento entre nós|113|BCB-TI
2|Dependências funcionais e multivaloradas: 3FN, BCNF e 4FN|115|BCB-TI
3|SELECT: subconsultas aninhadas e consultas correlacionadas|114|BCB-TI
4|Data warehouse: concorrência, bloqueios e deadlocks|116|BCB-TI""",
    "Macroeconomia": """1|Modelo de Solow: crescimento populacional e produto de equilíbrio|52|BCB-ECO
2|SELIC, multiplicador monetário e instrumentos do Banco Central|56,59|BCB-ECO
3|Exigência de capital para risco operacional|54|BCB-ECO
4|DBGG e operações compromissadas do Banco Central|58|BCB-ECO
5|Paridade coberta: arbitragem e taxas de juros|62|BCB-ECO
5|Elasticidades do comércio exterior e resposta ao câmbio|63|BCB-ECO
6|Curva de Phillips: expectativas e distinção entre curto e longo prazo|60|BCB-ECO""",
    "Estatística E Econometria": """2|Lei dos grandes números e convergência em probabilidade|97,98|BCB-ECO
3|Estimadores de máxima verossimilhança e método dos momentos|99,100,101,102|BCB-ECO
5|VAR: defasagens, estacionariedade e previsão|103,104,105|BCB-ECO
6|Efeitos fixos e aleatórios: correlação com heterogeneidade não observada|106,107|BCB-ECO
7|Cadeias de Markov e probabilidades de transição|108|BCB-ECO""",
}
SOURCES = {
    "BCB-RET": dict(
        exam="BACEN 2024 • Retificação do edital",
        url=BCB + "ED_1_BCB_23_ABERTURA_ATUALIZADO_RET_4.PDF",
    ),
    "BCB-TI": dict(exam="BACEN 2024 • TI", url=BCB + "959_BCB_002_01.PDF"),
    "BCB-ECO": dict(exam="BACEN 2024 • Economia", url=BCB + "959_BCB_001_01.PDF"),
    "BCB-DISC": dict(
        exam="BACEN 2024 • Discursiva TI",
        url=BCB + "BCB_24_PADRO_DE_RESPOSTA_DEFINITIVO_CARGO_2_ATUALIZADO.PDF",
    ),
    "STJ-ANALISE": dict(
        exam="STJ 2024 • Análise de Sistemas", url=STJ + "018_STJ_003_01.PDF"
    ),
    "STJ-SUPORTE": dict(
        exam="STJ 2024 • Suporte de TI", url=STJ + "018_STJ_018_01.PDF"
    ),
}
ADDITIONS[
    "Gestão Em Ti"
] = """1|Kanban: fluxo contínuo, limites de WIP e diferença para sprint|118|BCB-TI
2|Sprint Planning: responsabilidades do Product Owner e Developers|117|BCB-TI
3|Estratégia de dados e planejamento da gestão de dados|119|BCB-TI
4|ITIL v4: gerenciamento de riscos e níveis de serviço|120|BCB-TI"""
ADDITIONS["Direito Administrativo"] = (
    "9|Lei 12.813/2013: identificação e prevenção de conflitos de interesses|Retificação do item 9|BCB-RET"
)
ADDITIONS[
    "Engenharia De Software"
] += "\n12|Java: interpretação e execução de programas em provas|75|STJ-SUPORTE"
ADDITIONS[
    "Microeconomia"
] = """1|Função de custo de longo prazo e escolha ótima de insumos|69,70|BCB-ECO
3|Equilíbrio de Nash, estratégias mistas e estratégias dominantes|71,72|BCB-ECO
4|Sinalização, reputação e relação principal-agente|73,74|BCB-ECO
5|Lei de Walras e demandas excedentes|75|BCB-ECO
6|Primeiro teorema do bem-estar e melhoria de Pareto|76|BCB-ECO
7|Teoria do prospecto, racionalidade e escolhas sob risco|77,78|BCB-ECO"""
ADDITIONS[
    "Finanças"
] = """1.1|Tesouro Prefixado e Tesouro IPCA: retorno e resgate antecipado|79,80|BCB-ECO
1.6|Ações ordinárias e preferenciais: voto e dividendos|81,82|BCB-ECO
1.8|Opções de venda: preço de exercício, prêmio e payoff|83|BCB-ECO
1.7|Classificação e composição de fundos cambiais|85|BCB-ECO
3.3|Risco sistemático versus risco diversificável|87|BCB-ECO
4.2|APT: múltiplos fatores e distinções em relação ao CAPM|88,89|BCB-ECO
5.3|Deslocamentos paralelos e mudanças na curva de rendimentos|90,91,92|BCB-ECO
6.3|Duration versus convexidade: sensibilidade ao juro|93|BCB-ECO
8.2|VaR versus testes de estresse e cenários extremos|95|BCB-ECO"""
ADDITIONS[
    "Contabilidade De Instituições Financeiras Padrão Cosif (Plano Contábil Das Instituições Do Sistema Financeiro Nacional)"
] = """1|Aplicação dos pronunciamentos CPC às instituições financeiras|110|BCB-ECO
2.2|Empréstimos versus financiamentos e destinação de recursos|109|BCB-ECO
2.1|Bonificações, custo de aplicações e categorias de títulos|111,112|BCB-ECO
7|Diferença entre provisão e passivo contingente|115|BCB-ECO
14|Comitê de auditoria e acompanhamento das recomendações|117|BCB-ECO
13|Liquidação extrajudicial e recuperabilidade de intangíveis|118|BCB-ECO"""


def enrich(output):
    count = 0
    for area, entries in output["areas"].items():
        for subject, text in ADDITIONS.items():
            for line in text.splitlines():
                code, name, questions, source = line.split("|")
                matches = [
                    e
                    for e in entries
                    if e["materia"] == subject
                    and re.match(re.escape(code) + r"\s", e["official"])
                ]
                if not matches:
                    if any(e["materia"] == subject for e in entries):
                        raise ValueError(
                            "Missing official parent: " + subject + " " + code
                        )
                    continue
                if len(matches) != 1:
                    raise ValueError(
                        "Ambiguous official parent: " + subject + " " + code
                    )
                entry = matches[0]
                if name not in entry["items"]:
                    entry["items"].append(name)
                    count += 1
                entry.setdefault("evidence", {})[name] = dict(
                    SOURCES[source], questions=questions
                )
    output["version"] = 2
    output["reviewed_on"] = "2026-10-10"
    output["review_sources"] = SOURCES
    output["evidence_additions"] = count
    output["review_scope"] = (
        "Edital de abertura BACEN 2024, conferência com a versão retificada; provas objetivas básicas e específicas de 2024 das duas áreas; padrão definitivo da discursiva TI; comparação com STJ 2024 Análise de Sistemas e Suporte de TI. Não é um levantamento de todas as provas históricas nem garantia de esgotar assuntos amplos."
    )
    return count
