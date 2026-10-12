# Segurança e privacidade

Não há autenticação, tokens do produto, `.env`, telemetria ou API de runtime. Ler `LOCALAPPDATA` e `RUMO_DATA` é configuração local, não credencial. `.gitignore` é uma barreira; revisar os arquivos efetivamente rastreados e o ZIP/binários antes de publicar.

Entradas externas: JSON/SQLite de backup, importação de edital, nomes/observações, links e pasta de backups. Dados do mesmo usuário do Windows podem ser lidos por outros programas desse usuário: SQLite e backups não são criptografados.

- SQL: valores parametrizados; tabelas/colunas permitidas. Não avaliar Python, carregar pickle ou habilitar extensões SQLite.
- Backup SQLite: somente leitura, `trusted_schema=OFF`, `query_only=ON`, integridade, recusa de views/triggers e prazo de consulta. JSON até 20 MB, SQLite até 100 MB; 100 mil registros, texto total até 20 milhões de caracteres e 1 milhão por campo. Não transformar o arquivo importado no banco ativo.
- Restauração: esquema conhecido, chaves estrangeiras, tipos, preferências e relações validados. Destino de backups importado é ignorado em favor da configuração local.
- Retenção: remover apenas backups gerados pelo programa com nome `RUMO-AAAA-MM-DD-HHMMSSffffff.sqlite3`; preservar bases, backups pré-upgrade e arquivos de terceiros. Não apagar links de diretórios ou arquivos arbitrários.
- CSV: neutralizar texto que uma planilha interpretaria como fórmula; manter números reais como números.
- Links: somente HTTP/HTTPS com hostname, sem controles ou credenciais. Link externo abre apenas por ação do usuário. Pasta deve existir e ser diretório; não executar um caminho recebido como se fosse pasta.
- Hierarquia: mesma matéria, sem ciclos, até 128 níveis, preservação de pais com filhos/histórico.
- Instalador: por usuário, sem administrador, sem tarefa de startup; não apagar os dados ao desinstalar.

O instalador ainda não tem assinatura Authenticode. Hashes de release identificam os arquivos; não substituem assinatura nem auditoria externa. Não enviar o programa ou dados a VirusTotal/serviços de terceiros sem autorização.

A marca do JSON é um rótulo de 1–64 caracteres, não uma barreira de segurança. Versão, tabelas, campos, relações, limites e preferências continuam integralmente validados. A migração da base recusa links simbólicos, bloqueia a instalação anterior e publica a cópia sem sobrescrever o destino; nunca apaga a origem.

Backups RPG v4/v5 exigem fontes únicas e recompensas compatíveis com sessões/revisões/desafios canônicos. Valores de catálogo, preços, slots e relações entre planos/assuntos são validados antes da restauração. Recompensas não são confiadas a números arbitrários do JSON. RPG não introduz serviços externos, pagamentos ou sorteios.

Itens de evolução têm IDs, slots, requisitos e preço zero no catálogo permitido. Backups mantêm aquisições antigas mesmo quando a correção reduz o nível; não inferir fraude só de um item cujo marco atual diminuiu. Atalhos não executam conteúdo externo nem geram registros. As classes não introduzem moedas pagas, sorteios, vantagens nas métricas ou penalidades por ausência.

Campo de Treinamento: catálogo público só por HTTPS ou pasta local; validação completa antes de ativar (último válido permanece). PDFs apenas de hosts aprovados (redirecionamentos conferidos), com limite de tamanho, SHA-256, verificação `%PDF-`, espaço em disco e gravação atômica. Nada do catálogo é executado. Aula publicada exige revisão aprovada; planejadas/rascunhos não têm URL. Preferência `training_source` validada nos backups (sem credenciais, remoto só HTTPS). Nenhum dado pessoal é enviado; SHA-256 não autentica o editor do catálogo (assinatura é evolução futura).

## Integração opcional autorizada (12/10/2026)
As afirmações iniciais de ausência de conta/rede referem-se ao modo local.
Supabase Auth + RLS/RPC é opcional, sem publicação nesta etapa. Backend usa
`auth.uid()`, lock por conta e security definer com search_path fixo. Tabelas
privadas não são expostas nem graváveis pelo cliente. Gabarito/comentário só
retornam ao dono após confirmar; XP/agenda derivam de eventos canônicos.
Catálogo publicado exige revisão; exemplos são explícitos, rascunhos ocultos.
Cliente HTTPS rejeita redirecionamentos/origens com credenciais; tokens em memória,
sem `.env` do desktop. Site só recebe chave pública, nunca administrativa.
Workspace não criptografado segue a proteção de arquivos do usuário do sistema.
Conta vinculada não pode ser trocada silenciosamente. Upload legado exige seleção;
PDFs pessoais e demais dados fora do contrato não são enviados. Cada evento tem
UUID e CAS; conflito preserva original. Backups antigos não apagam dados remotos;
exportar workspace separadamente. Logout impede rede mas mantém pendências locais.
