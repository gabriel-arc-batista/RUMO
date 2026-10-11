# Revisão de segurança — RUMO 1.4.1

Data: **11/10/2026**. Revisão local do código, entradas externas, persistência e empacotamento Windows. Não equivale a uma auditoria independente nem garante ausência absoluta de bugs.

## Correções aplicadas

| Achado | Resultado |
|---|---|
| Retenção abrangia todo `*.sqlite3` da pasta | Remoção limitada aos nomes próprios de backup; base ativa, backups pré-upgrade e arquivos alheios são preservados |
| Destino de backup importado podia redirecionar gravações | Restauração mantém a configuração de destino local |
| CSV interpretável como fórmula | Texto perigoso recebe apóstrofo; números reais permanecem numéricos |
| Abertura de pasta sem conferir tipo do caminho | Somente diretórios existentes podem ser abertos como pasta |
| Filtro de matéria interpolado na consulta | Valor passa como parâmetro; identificadores de tabelas/colunas seguem listas permitidas |
| Preferências novas e vínculos incompletamente validados | Verificação de tipos, limites, metas, relações de planos/matérias/assuntos e números finitos |
| Backup SQLite podia conter views/triggers | Objetos recusados; leitura somente de tabelas, sem extensões, com integridade e prazo de consulta |
| Entrada externa grande ou hierarquia profunda | Limites de arquivo, quantidade de registros, texto e profundidade; pais não podem formar ciclos ou mudar de matéria com filhos/histórico |
| Backup válido com pai criado depois do filho falhava | Chaves estrangeiras diferidas numa transação, verificadas antes de restaurar e no commit |
| Pillow 11.3.0 de desenvolvimento tinha avisos conhecidos | Atualizado para 12.3.0; Pillow é excluído do executável |
| Código compacto dificultava revisão | Formatação Black; validação de backups e políticas de segurança separadas do domínio |

## Evidências

- 57 testes unitários, incluindo entradas maliciosas e preservação dos dados, aprovados.
- Fluxos de nove telas em dois temas e registros/notas/metas/relógio verificados em bases temporárias.
- Dependências explicitamente fixadas de desenvolvimento verificadas com pip-audit: sem vulnerabilidades conhecidas no resultado posterior à atualização. A consulta não garante que vulnerabilidades desconhecidas ou de bibliotecas nativas não existam.
- Bandit em todos os módulos de runtime: zero achados de severidade alta; avisos médios de composição SQL revisados manualmente. Os valores são parâmetros e as partes estruturais vêm de tabelas/colunas/expressões permitidas. Avisos baixos de `os.startfile` correspondem a PDFs locais ou diretórios verificados; fallback de DPI é opcional. Os avisos não foram ocultados.
- `.env`, chaves privadas e credenciais não encontrados nos arquivos preparados para versionamento. Bancos, backups, logs, capturas, relatórios locais, ferramentas e builds excluídos do Git. Variáveis lidas pelo programa são configuração de caminho, sem valores secretos incorporados.
- Instalador por usuário, sem solicitação de administrador, serviço, inicialização automática ou remoção dos dados ao desinstalar. Binários de release precisam corresponder ao build 1.4.1 e receber hashes SHA-256.

Microsoft Defender: varredura personalizada da pasta `dist/` concluída, proteção ativa e nenhuma detecção associada aos artefatos no resultado local. Instalador confirmado como `NotSigned`. O executável compilado passou nos testes isolados de inicialização, persistência, bloqueio de segunda instância e ausência de sockets de internet observados. O ZIP foi inspecionado e não contém bancos, logs, `.env`, chaves privadas ou Pillow.

## Limites

O banco local e os backups não são criptografados: programas do mesmo usuário do Windows podem ler esses arquivos. O uso normal é offline; links externos abrem apenas por ação do usuário. O produto não contém credencial de GitHub nem usa a autenticação da ferramenta de desenvolvimento.

O instalador ainda **não tem assinatura Authenticode**. Uma verificação antivírus local e hashes ajudam a verificar o artefato, mas não substituem assinatura, análise independente ou testes em VM. Não foram realizados pentest externo, análise de todas as bibliotecas nativas, sandbox/VM ou testes Linux. Resultados locais detalhados permanecem em `validation/`, sem publicação de caminhos pessoais.
