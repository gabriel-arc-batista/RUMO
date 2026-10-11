"""Authorial study breakdown, kept separate from the unchanged official notice.

Each line identifies an official leaf by its section number. Separators create
independently trackable subjects, not a claim of additional official requirements.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDES = {}


def section(subject, text):
    GUIDES[subject] = {
        line.split("|")[0].strip(): [x.strip() for x in line.split("|")[1:]]
        for line in text.strip().splitlines()
    }


section(
    "Língua Portuguesa",
    """
1 | Tema e ideia central | Informações explícitas e implícitas | Inferências e pressupostos | Intenção comunicativa e ponto de vista
2 | Narração e descrição | Dissertação e argumentação | Exposição e injunção | Características e função dos gêneros textuais
3 | Emprego de letras e dígrafos | Acentuação gráfica | Hífen e escrita de palavras compostas
4.1 | Referenciação anafórica e catafórica | Substituição e elipse | Repetição e progressão textual | Conectores e relações de sentido
4.2 | Tempos e modos do indicativo e subjuntivo | Valores do imperativo | Correlação de tempos verbais
5.1 | Substantivos e adjetivos | Artigos, numerais e pronomes | Verbos e locuções verbais | Advérbios, preposições e conjunções
5.2 | Orações coordenadas sindéticas e assindéticas | Conjunções e seus valores | Coordenação entre termos
5.3 | Orações subordinadas substantivas | Orações subordinadas adjetivas | Orações subordinadas adverbiais | Orações reduzidas
5.4 | Vírgula e separação de termos e orações | Ponto e ponto e vírgula | Dois-pontos, travessões e parênteses | Pontuação e alteração de sentido
5.5 | Concordância verbal: sujeito simples e composto | Concordância verbal: casos especiais | Concordância nominal e casos especiais
5.6 | Regência verbal | Regência nominal | Pronomes relativos e preposições
5.7 | Casos obrigatórios de crase | Casos proibidos de crase | Casos facultativos e locuções
5.8 | Próclise | Ênclise | Mesóclise e colocação em locuções verbais
6.1 | Sinonímia e antonímia | Polissemia e ambiguidade | Sentido literal e figurado
6.2 | Substituição lexical com manutenção do sentido | Substituição de conectores | Reescrita de estruturas gramaticais
6.3 | Ordem direta e inversa | Transformação de orações e períodos | Voz ativa e passiva | Preservação de sentido e correção gramatical
6.4 | Adequação ao gênero textual | Registro formal e informal | Clareza, concisão e impessoalidade
""",
)
section(
    "Noções De Lógica E Estatística",
    """
1.1 | Relações e ordenação lógica | Condições necessárias e suficientes | Problemas de associação e sequências
1.2 | Premissas e conclusões | Validade de argumentos | Dedução e inferência | Analogias e falácias
1.3 | Sintaxe e semântica proposicional | Formalização de enunciados | Raciocínio com conectivos lógicos
10.3.1 | Proposições e valores lógicos | Negação e conectivos | Tradução de linguagem natural para proposições
10.3.2 | Construção de tabelas-verdade | Tautologia, contradição e contingência | Implicação e equivalência lógica
10.3.3 | Equivalência do condicional | Contraposição | Equivalências do bicondicional
10.3.4 | Negação de conjunções e disjunções | Leis de De Morgan | Aplicação em problemas de lógica
2.1 | População e amostra | Censo e amostragem | Parâmetros e estatísticas
2.2 | Frequência absoluta e relativa | Frequência acumulada | Histogramas e polígonos de frequência
2.3 | Média simples e ponderada | Mediana e moda | Quartis, decis e percentis
2.4 | Amplitude e variância | Desvio padrão | Coeficiente de variação
2.5 | Probabilidade condicional | Independência de eventos | Regra do produto e teorema de Bayes
2.6 | Variáveis discretas e contínuas | Função de probabilidade e densidade | Função de distribuição acumulada | Esperança e variância
""",
)
section(
    "Direito Administrativo",
    """
1.1 | Órgãos da administração direta | Entidades da administração indireta | Centralização, descentralização e desconcentração | Princípios expressos e implícitos da administração pública
2.1 | Poder hierárquico | Poder disciplinar | Poder regulamentar e normativo | Poder de polícia
2.2 | Excesso de poder | Desvio de finalidade | Controle do uso e abuso de poder
3.1 | Conceito e classificação dos serviços públicos | Princípios e continuidade | Formas de prestação e delegação
3.2 | Autarquias e fundações públicas | Agências reguladoras e executivas | Empresas públicas | Sociedades de economia mista
4.1 | Conceito e elementos do ato administrativo | Competência, finalidade, forma, motivo e objeto | Presunção de legitimidade, imperatividade e autoexecutoriedade
4.2 | Publicidade e publicação dos atos | Notificação e intimação | Efeitos da comunicação dos atos
4.3 | Anulação e efeitos | Revogação e mérito administrativo | Convalidação e limites
4.4 | Atos vinculados e discricionários | Mérito administrativo | Controle de legalidade
5.1.1 | Âmbito de aplicação da Lei 8.112 | Conceitos de servidor e cargo público | Requisitos básicos de investidura
5.1.2 | Nomeação, posse e exercício | Estágio probatório e estabilidade | Formas de provimento | Hipóteses de vacância | Remoção, redistribuição e substituição
5.1.3 | Vencimento e remuneração | Indenizações e gratificações | Férias e licenças | Afastamentos e concessões
5.1.4 | Deveres e proibições | Acumulação de cargos | Responsabilidades | Penalidades e prescrição
5.1.5 | Benefícios do plano de seguridade | Aposentadoria do servidor | Pensão civil | Licenças e auxílios da seguridade
5.1.6 | Sindicância e instauração | Inquérito, instrução e defesa | Relatório e julgamento | Revisão do processo disciplinar
6 | Sujeitos e dolo na improbidade | Enriquecimento ilícito | Prejuízo ao erário | Violação de princípios | Sanções e processo na Lei 8.429
7 | Regras deontológicas | Deveres fundamentais | Vedações ao servidor | Comissões de ética
8 | Abrangência do Código da Alta Administração | Conflitos de interesse e conduta | Presentes e atividades externas | Apuração e consequências
9 | Hipóteses de conflito de interesses | Conflitos durante e após o exercício do cargo | Consulta e prevenção | Competências de fiscalização
10 | Transparência ativa e passiva | Pedido e prazos de acesso | Restrições e classificação da informação | Recursos e responsabilidades
11 | Conceitos e princípios da LGPD | Bases legais de tratamento | Direitos do titular | Tratamento pelo poder público | Agentes, segurança e ANPD
""",
)
section(
    "Fundamentos De Macroeconomia E Microeconomia",
    """
Macroeconomia — 1 | PIB e PNB | Óticas do produto, renda e despesa | Valores nominais e reais | Identidades das contas nacionais
Macroeconomia — 2 | Moeda e funções | Base monetária | Agregados monetários e liquidez
Macroeconomia — 3 | Reservas e depósitos bancários | Multiplicador monetário | Criação de moeda pelos bancos | Destruição de moeda
Macroeconomia — 4 | Balanço do banco central | Contas dos bancos comerciais | Consolidação do sistema monetário
Macroeconomia — 5 | Conta corrente | Conta capital e financeira | Reservas internacionais | Identidade do balanço de pagamentos
Microeconomia — 1.1 | Formas de organização econômica | Papel dos preços | Custo de oportunidade | Fronteira de possibilidades de produção
Microeconomia — 2.1 | Preferências e utilidade | Curvas de indiferença | Taxa marginal de substituição
Microeconomia — 2.2 | Renda e preços na restrição orçamentária | Inclinação e interceptos | Deslocamentos da reta orçamentária
Microeconomia — 2.3 | Escolha ótima do consumidor | Solução interior e de canto | Equilíbrio e alterações de renda e preços
Microeconomia — 2.4 | Efeito substituição | Efeito renda | Efeito preço e bens inferiores
Microeconomia — 2.5 | Derivação da demanda individual | Demanda de mercado | Movimento e deslocamento da curva
Microeconomia — 2.6 | Elasticidade-preço da demanda | Elasticidade-renda | Elasticidade cruzada | Elasticidade e receita total
""",
)
section(
    "Atualidades",
    """
1 | Segurança e transportes | Política e instituições | Economia e sociedade | Educação e saúde | Cultura e tecnologia | Energia e transição energética | Relações internacionais | Desenvolvimento sustentável e ecologia
""",
)
section(
    "Ciência De Dados",
    """
1 | Preparação de dados e atributos | Regressão e classificação | Validação cruzada e métricas | Overfitting, underfitting e regularização
2 | Redes profundas e treinamento | Backpropagation e otimizadores | Redes convolucionais e recorrentes | Transformers e atenção
3 | Tokenização e normalização textual | Representação vetorial e embeddings | Classificação de textos | Análise de sentimentos e reconhecimento de entidades
4 | Volume, variedade e velocidade | Armazenamento distribuído | Processamento em lote e streaming | Particionamento e processamento paralelo
5 | Completude e consistência | Acurácia e validade | Unicidade e atualidade | Limpeza e validação de dados
6 | Aprendizado supervisionado | Aprendizado não supervisionado | Aprendizado semissupervisionado | Aprendizado por reforço | Aprendizado por transferência
7 | Modelos de linguagem e tokenização | Pré-treinamento e ajuste fino | Inferência e engenharia de prompts | Recuperação aumentada por geração | Alucinações e avaliação de respostas
8 | Neurônios, pesos e funções de ativação | Camadas e arquiteturas | Funções de perda | Propagação direta e retropropagação
9 | Gestão de código e experimentos | Treinamento e pipelines | Versionamento de dados e modelos | Implantação e automação | Monitoramento de desempenho e drift
10 | Transparência e explicabilidade | Responsabilidade e supervisão | Privacidade e segurança | Viés, equidade e avaliação de riscos
""",
)
section(
    "Segurança Da Informação",
    """
1 | Autenticação e autorização | Gestão de identidades e permissões | Single Sign-On | SAML | OAuth 2 | OpenID Connect
2 | Privacy by design e by default | Minimização e proteção de dados | Configurações seguras por padrão
3 | Malware e ransomware | Phishing e engenharia social | Injeção e XSS | Falhas de autenticação e controle de acesso | DoS e DDoS
4 | Validação de entradas e saídas | Gestão de sessões | Segurança de APIs e serviços web | Análise estática e dinâmica | Testes de segurança
5 | Fatores de conhecimento, posse e inerência | MFA e autenticação forte | Recuperação e proteção contra abuso
6 | Firewall e proxy | IDS e IPS | SIEM e correlação de eventos | IAM e PAM | Antivírus e antispam
7 | MITRE ATT&CK: táticas e técnicas | CIS Controls | NIST CSF: funções e gestão de riscos | Aplicação de frameworks na organização
8 | Preparação e identificação | Contenção | Erradicação e recuperação | Evidências e comunicação | Lições aprendidas
9 | Criptografia simétrica e assimétrica | Hash e integridade | Assinatura digital | Certificados e infraestrutura de chaves públicas | Proteção em trânsito e em repouso
10 | Responsabilidade compartilhada em nuvem | Identidades, redes e segredos | Segurança de imagens e contêineres | Isolamento e proteção de workloads
""",
)
section(
    "Engenharia De Software",
    """
1 | HTTP e HTTP/2 | gRPC | WebSockets | TLS | Proxy, cache e DNS | Balanceamento de carga | Tolerância a falhas e escalabilidade
2 | Cultura e práticas DevOps | DevSecOps e segurança no pipeline | Integração contínua | Entrega e implantação contínuas | Pipelines e automação
3 | Modelagem de ameaças | Validação e sanitização | Privilégio mínimo e gestão de segredos | Revisão de código e dependências
4 | Testes unitários | Testes de integração | TDD e ciclo red-green-refactor | BDD e cenários de aceitação | Isolamento, mocks e cobertura
5 | Arquitetura em camadas | Arquitetura baseada em serviços | Microsserviços e orquestração | API gateway | Arquitetura orientada a eventos | Cliente-servidor | Serverless
6 | Pesquisa e necessidades do usuário | Arquitetura da informação | Usabilidade e acessibilidade | Prototipação e testes de interface
7 | Concorrência e paralelismo | Event loop e operações não bloqueantes | Futures e promises | Async/await | Tratamento de erros e cancelamento
8 | Recursos, verbos HTTP e códigos de resposta | Idempotência e stateless | Versionamento e paginação de APIs | GraphQL: schema, queries e mutations | Resolvers e controle de acesso
9 | SOAP e envelopes | WSDL e contratos | Serialização XML e JSON | Interoperabilidade e segurança de serviços
10 | GoF: padrões criacionais | GoF: padrões estruturais | GoF: padrões comportamentais | GRASP: responsabilidades, coesão e acoplamento
11 | Repositórios e commits | Branches e merge | Rebase e resolução de conflitos | Remotes, fetch, pull e push | Reversão e inspeção do histórico
12 | Java: tipos, variáveis e operadores | Java: estruturas sequenciais e entrada/saída | Java: condicionais if/else e switch | Java: laços for, while e do/while | Java: arrays e strings | Java: classes, objetos e construtores | Java: métodos, parâmetros e sobrecarga | Java: encapsulamento e modificadores de acesso | Java: herança e polimorfismo | Java: interfaces e classes abstratas | Java: exceções e try/catch/finally | Java: generics e coleções | Java: lambdas e streams | Java: pacotes e organização do código | Python: tipos, variáveis e operadores | Python: estruturas sequenciais e entrada/saída | Python: condicionais e laços | Python: listas, tuplas, conjuntos e dicionários | Python: funções, parâmetros e escopo | Python: classes, métodos e herança | Python: exceções e context managers | Python: módulos e pacotes | Python: iteradores, generators e comprehensions
13 | Atomicidade e consistência distribuída | Commit em duas fases | Sagas e compensação | Idempotência e consistência eventual
14 | Ledgers distribuídos e blockchain | Consenso e validação | Redes permissionadas e não permissionadas | Contratos inteligentes | Integridade e rastreabilidade
""",
)
section(
    "Infraestrutura Em Ti",
    """
1 | Infraestrutura declarativa e imperativa | Versionamento e reprodutibilidade | Provisionamento automatizado | Idempotência e gestão de configuração
2 | Docker: imagens, containers e Dockerfile | Docker: redes e volumes | Kubernetes: pods e deployments | Kubernetes: services e ingress | ConfigMaps, secrets e persistência | Disponibilidade e boas práticas
3 | DNS no Windows Server | DHCP e concessões | RADIUS e autenticação | Serviços de certificados | Active Directory, domínios e políticas de grupo
4 | Métricas, logs e traces | Nagios e verificações | Prometheus e coleta de métricas | Grafana e dashboards | Elasticsearch e Kibana | APM, alertas e diagnóstico
5 | SMTP | HTTP e HTTPS | SSL/TLS | LDAP | NFS | SMB
6 | Redundância e alta disponibilidade | Failover e recuperação | Backup e restauração | RTO e RPO | Plano de continuidade e testes
7 | IaaS e provisionamento | PaaS e serviços gerenciados | SaaS e administração | Redes, armazenamento e identidade em nuvem | Monitoramento, custos e disponibilidade
8 | Hipervisores e máquinas virtuais | Redes e armazenamento virtualizados | Snapshots e migração | Capacidade, isolamento e disponibilidade
9 | Windows Server: serviços, usuários e permissões | Linux: usuários, grupos e permissões | Processos, serviços e logs | Sistemas de arquivos e armazenamento | Atualizações e administração remota
10 | LAN e comutação | WAN e interconexão | SDN: planos de controle e dados | VLANs e segmentação
11 | Puppet: manifests e estado desejado | Ansible: inventário e playbooks | Roles e reutilização | Idempotência e automação de configuração
""",
)
section(
    "Bancos De Dados",
    """
1 | Arquitetura e componentes de um SGBD | Modelo relacional e integridade | Transações ACID e níveis de isolamento | Controle de concorrência e bloqueios | Índices e planos de execução | Backup e recuperação | NoSQL: chave-valor | NoSQL: documentos | NoSQL: famílias de colunas | NoSQL: grafos | Replicação, particionamento e consistência
2 | Modelo conceitual e entidade-relacionamento | Entidades, atributos e relacionamentos | Cardinalidade e participação | Modelo lógico relacional e chaves | Dependências funcionais | Normalização: 1FN, 2FN, 3FN e BCNF | Modelo físico e índices | Modelagem dimensional: fatos e dimensões | Esquemas estrela e floco de neve | Modelagem de documentos, colunas e grafos
3 | DDL: CREATE, ALTER e DROP | DML: INSERT, UPDATE e DELETE | SELECT, WHERE e ORDER BY | INNER, LEFT, RIGHT e FULL JOIN | GROUP BY, HAVING e agregações | Subconsultas e operações de conjuntos | CTEs e consultas recursivas | Funções de janela | Constraints e integridade referencial | Views e índices | Transações: COMMIT, ROLLBACK e SAVEPOINT | SQL procedural: variáveis e controle de fluxo | Procedures, funções e triggers | Cursores e tratamento de exceções
4 | Data warehouse e integração de dados | Data marts | ETL e ELT | OLAP e operações analíticas | Data lake e organização de dados | Data mesh: domínios e produtos de dados | Governança, catálogo e linhagem
""",
)
section(
    "Gestão Em Ti",
    """
1 | Visualização do fluxo | Limites de trabalho em progresso | Lead time e cycle time | Gestão de fluxo e melhoria contínua
2 | Responsabilidades do Scrum | Eventos e timeboxes | Artefatos e compromissos | Product backlog e sprint backlog | Incremento e Definition of Done
3 | Papéis e responsabilidades sobre dados | Políticas e qualidade | Catálogo, metadados e linhagem | Acesso, segurança e conformidade
4 | Sistema de valor de serviço | Cadeia de valor de serviço | Princípios orientadores | Quatro dimensões | Práticas de gestão de serviços | Melhoria contínua
""",
)
section(
    "Macroeconomia",
    """
1 | Modelo clássico | Modelo novo-keynesiano | Oferta e demanda agregadas | Modelos de crescimento | Escolha intertemporal: consumo | Escolha intertemporal: investimento, governo e conta corrente
2 | Regras e discricionariedade | Credibilidade e consistência temporal | Instrumentos convencionais | Instrumentos não convencionais | Objetivos e transmissão da política monetária | Regime de metas de inflação
3 | Risco sistêmico | Instrumentos macroprudenciais | Pró-ciclicidade e estabilidade financeira
4 | Resultado primário e nominal | Déficit público | Dinâmica e sustentabilidade da dívida | Política fiscal e atividade econômica
5 | Paridade coberta de juros | Paridade descoberta de juros | Exportações e importações | Regimes cambiais | Câmbio de equilíbrio e termos de troca | Paridade do poder de compra
6 | Curva de Phillips de curto e longo prazo | Expectativas adaptativas e racionais | Inflação e desinflação
7 | Choques reais e produtividade | Propagação dos ciclos econômicos | Hipóteses e implicações dos modelos RBC
8 | Salários e emprego no modelo clássico | Rigidez salarial no modelo novo-keynesiano | Taxa natural de desemprego
""",
)
section(
    "Microeconomia",
    """
1 | Preferências e escolha do consumidor | Dualidade e demanda | Produção e tecnologia | Custos e escolha da firma | Maximização de lucro
2 | Medidas de concentração | Concorrência perfeita e monopólio | Oligopólio e competição | Barreiras à entrada | Organização industrial
3 | Jogos estáticos e dinâmicos | Estratégias e equilíbrio de Nash | Equilíbrio em subjogos | Jogos repetidos | Formatos de leilão e estratégias de lance
4 | Informação assimétrica | Seleção adversa | Risco moral | Externalidades e instrumentos de correção | Bens públicos e provisão
5 | Equilíbrio geral de trocas e produção | Lei de Walras | Eficiência de Pareto | Teoremas do bem-estar
6 | Excedentes do consumidor e produtor | Critérios de bem-estar | Eficiência e distribuição | Funções de bem-estar social
7 | Heurísticas e vieses | Aversão à perda e teoria do prospecto | Preferências intertemporais | Arquitetura de escolhas
""",
)
section(
    "Finanças",
    """
1.1 | Características dos títulos públicos | Indexadores e vencimentos | Negociação e remuneração
1.2 | Debêntures e notas comerciais | Remuneração e garantias | Risco de crédito e liquidez
1.3 | Estrutura de securitização | Lastro e cessão de recebíveis | Riscos e participantes
1.4 | Compra e venda com compromisso de reversão | Lastro e remuneração | Finalidade e riscos
1.5 | Depósitos a prazo e certificados | Depósitos interfinanceiros | Liquidez e remuneração
1.6 | Ações ordinárias e preferenciais | Dividendos e direitos | Mercados primário e secundário
1.7 | Estrutura e participantes dos fundos | Cotas e patrimônio | Taxas, rentabilidade e riscos
1.8 | Contratos a termo | Contratos futuros e ajustes | Swaps | Opções: calls e puts | Payoffs, hedge e arbitragem
1.9 | Transferência do risco de crédito | Credit default swaps | Eventos de crédito e liquidação
2.1 | Eficiência fraca | Eficiência semiforte | Eficiência forte
2.2 | Informação e formação de preços | Racionalidade e expectativas | Arbitragem e agentes financeiros
2.3 | Gestão ativa e passiva | Estratégias de alocação | Relação entre eficiência e estratégias
3.1 | Retornos simples e compostos | Retorno esperado | Variância, covariância e correlação
3.2 | Modelo de Markowitz | Restrições de carteira | Otimização média-variância
3.3 | Risco sistemático e específico | Correlação e diversificação | Efeito da composição da carteira
3.4 | Conjunto de carteiras possíveis | Carteira de mínima variância | Fronteira eficiente
3.5 | Utilidade esperada | Aversão ao risco | Escolha ótima de carteira
3.6 | Ativo livre de risco e carteira arriscada | Linha de alocação de capital | Carteira tangente
3.7 | Custos de negociação | Impacto sobre retorno e rebalanceamento | Liquidez e spreads
4.1 | Hipóteses do CAPM | Beta e retorno requerido | Linha do mercado de títulos | Extensões do CAPM
4.2 | Ausência de arbitragem | Modelos multifatoriais | Prêmios de risco e fatores
5.1 | Teoria das expectativas | Preferência pela liquidez | Segmentação de mercados | Habitat preferido
5.2 | Taxas spot | Taxas forward | Relação entre taxas e fatores de desconto
5.3 | Deslocamentos paralelos | Inclinação e curvatura | Efeitos sobre preços de títulos
6.1 | Valor presente e fluxo de caixa | Preço e yield to maturity | Títulos prefixados e indexados
6.2 | Imunização de carteiras | Casamento de fluxos | Estratégias de gestão de renda fixa
6.3 | Duration de Macaulay | Duration modificada | Convexidade | Sensibilidade a taxas de juros
7 | Fatores ambientais | Fatores sociais | Governança | Riscos ESG e avaliação financeira
8.1 | Volatilidade histórica | Volatilidade implícita | Estimação e interpretação da volatilidade
8.2 | VaR paramétrico | Simulação histórica | Simulação de Monte Carlo | Horizonte e nível de confiança
8.3 | Hipóteses de distribuição | Correlações e estabilidade de parâmetros | Limitações e backtesting
8.4 | Testes de estresse | Análise de cenários | Choques e sensibilidade de carteiras
""",
)
section(
    "Estatística E Econometria",
    """
1 | Distribuições discretas | Distribuições contínuas | Esperança e variância | Momentos | Esperança condicional
2 | Lei fraca dos grandes números | Lei forte dos grandes números | Convergência e aplicações
3 | Estimação pontual e propriedades | Intervalos de confiança | Testes de hipóteses e erros | P-valor e poder do teste | Amostragem e desenhos amostrais
4 | Regressão linear simples | Regressão múltipla | Mínimos quadrados ordinários | Hipóteses e inferência | Heterocedasticidade, autocorrelação e multicolinearidade
5 | Estacionaridade | Autocorrelação e modelos de séries | Vetores autorregressivos | Testes de raiz unitária | Previsão e diagnóstico
6 | Estrutura de dados em painel | Efeitos fixos | Efeitos aleatórios | Escolha e diagnóstico de modelos | Identificação e causalidade
7 | Processos estocásticos e propriedades | Passeio aleatório | Processos estacionários | Dependência temporal e momentos
""",
)
section(
    "Contabilidade De Instituições Financeiras Padrão Cosif (Plano Contábil Das Instituições Do Sistema Financeiro Nacional)",
    """
1 | Objetivos e estrutura do Cosif | Escrituração e critérios gerais | Reconhecimento e mensuração | Contas e documentação contábil
2.1 | Operações interfinanceiras de liquidez | Títulos e valores mobiliários | Instrumentos financeiros derivativos | Reconhecimento, mensuração e evidenciação
2.2 | Registro das operações de crédito | Classificação e mensuração | Encargos e reconhecimento de receitas | Perdas e provisões de crédito
2.3 | Classificação de investimentos mantidos para venda | Mensuração | Baixa e divulgação
3 | Classificação do arrendamento mercantil | Reconhecimento pelo arrendador e arrendatário | Mensuração e evidenciação
4 | Classificação de ativos não financeiros para venda | Mensuração e redução ao valor recuperável | Baixa e divulgação
5 | Reconhecimento e custo inicial | Depreciação | Redução ao valor recuperável | Baixa e evidenciação
6 | Critérios de reconhecimento do intangível | Vida útil e amortização | Recuperabilidade | Baixa e divulgação
7 | Reconhecimento de provisões | Mensuração e revisão | Passivos contingentes | Ativos contingentes e divulgação
8 | Composição do patrimônio líquido | Capital e reservas | Ajustes patrimoniais | Distribuição de resultados e remuneração do capital
9 | Balanço patrimonial | Demonstração do resultado | Demonstração dos fluxos de caixa | Mutações do patrimônio líquido | Notas explicativas
10 | Abrangência do conglomerado prudencial | Consolidação de demonstrações | Eliminações e ajustes | Divulgação consolidada
11.1 | Estrutura do balancete cooperativo | Agregação e consolidação | Ajustes e evidenciação
11.2 | Escopo da auditoria cooperativa | Procedimentos e evidências | Relatórios e responsabilidades
12 | Registro de grupos e cotas de consórcio | Recursos, obrigações e contemplações | Demonstrações e controles
13 | Contabilidade na liquidação extrajudicial | Apuração de ativos e obrigações | Demonstrações e prestação de contas
14 | Objetivo e alcance da auditoria independente | Independência e responsabilidades | Procedimentos e relatórios | Divulgação de resultados
""",
)


def build():
    source = json.loads((ROOT / "assets/bacen2024.json").read_text(encoding="utf-8"))
    output = {
        "version": 1,
        "kind": "authorial-study-guide",
        "note": "Desdobramento pedagógico dos itens oficiais. Não é texto do edital nem garantia de exaustividade; não altera o PDF histórico. Consulte o edital e suas retificações para o escopo exigido.",
        "sources": [
            source["source"],
            "https://dev.java/learn/",
            "https://docs.python.org/3/tutorial/",
            "https://www.postgresql.org/docs/current/tutorial.html",
            "https://www.planalto.gov.br/ccivil_03/leis/l8112cons.htm",
            "https://www.planalto.gov.br/ccivil_03/leis/l8429.htm",
            "https://www.bcb.gov.br/estabilidadefinanceira/cosif",
        ],
        "areas": {},
    }
    for area, rows in source["areas"].items():
        parents = {(r["materia"], r["pai"]) for r in rows if r["pai"]}
        result = []
        for row in rows:
            if (row["materia"], row["assunto"]) in parents:
                continue
            code = re.match(
                r"^(?:(?:Macroeconomia|Microeconomia) — )?\d+(?:\.\d+)*", row["assunto"]
            ).group()
            details = GUIDES[row["materia"]].get(code)
            if not details:
                raise ValueError(f'Missing outline: {row["materia"]}: {code}')
            if len(details) < 2 or len(set(details)) != len(details):
                raise ValueError("Invalid study breakdown")
            result.append(
                dict(materia=row["materia"], official=row["assunto"], items=details)
            )
        output["areas"][area] = result
    from syllabus_evidence import enrich

    enrich(output)
    (ROOT / "assets/bacen2024-detalhado.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        {
            area: sum(len(r["items"]) for r in rows)
            for area, rows in output["areas"].items()
        }
    )


if __name__ == "__main__":
    build()
