# Contexto para continuidade

Versão preparada: **1.4.1**, em 11/10/2026. Python 3.13, Tk 8.6, SQLite esquema 3. Plataforma executada: Windows 11 x64. O projeto principal é BACEN 2024, TI; também existe Economia e Finanças.

## Produto e decisões aceitas

Aplicativo sem conta, assinatura, servidor ou serviços em segundo plano. Dados ficam em `%LOCALAPPDATA%/RUMO`; binários instalados em `%LOCALAPPDATA%/Programs/RUMO`. `RUMO_DATA` permite uma pasta alternativa para testes. Não é segredo e não carrega `.env`.

Design preto/grafite e dourado, tema claro suave, fonte Inter carregada privadamente. Referências: Estudei, Linear e Material Design 3; links em `FONTES.md`. Frase diária no cabeçalho, indicadores e constância no início, sem espaços artificiais nos cartões. Animações de entrada, hover e foco são finitas e respeitam a preferência de reduzir movimento.

Cada subassunto tem conclusão verde e observações salvas sem reconstruir a lista. Nomes visíveis não mostram IDs. Relógio com busca, presets e progresso; pausas não contam. Desafios têm três níveis e permitem escolher a meta principal, lembrada no relógio. Preferências em quatro abas. Ciclo guiado usa 25 minutos por matéria e o próximo assunto pendente na ordem de aprendizagem; não é uma agenda diária rígida.

São 287 itens originais, mais 1.090 desdobramentos: 565 folhas em TI e 525 em Economia e Finanças. Original e retificado estão disponíveis offline. O guia é curadoria pedagógica, não texto oficial nem garantia de exaustividade. 150 frases com fontes; não inventar atribuições.

A revisão de segurança 1.4.1 separou backups, protegeu retenção, CSV e links, reforçou limites e relações e atualizou Pillow de desenvolvimento. Consulte `SECURITY.md` e o relatório público `SECURITY_REVIEW.md`.

## Leia em seguida

- `ARCHITECTURE.md`: módulos e contratos.
- `TESTING.md`: testes e limites de validação.
- `SECURITY.md`: superfície de ataque e invariantes.
- `RELEASE.md`: conta pessoal, build e publicação.
- `ROADMAP.md`: expansão sem regressões.
