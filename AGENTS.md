# RUMO — orientação para agentes

Antes de alterar o projeto, leia `.agents/README.md`, `.agents/ARCHITECTURE.md`, `.agents/SECURITY.md` e `.agents/TESTING.md`. Para publicar ou empacotar, leia `.agents/RELEASE.md`.

O produto é um aplicativo desktop nativo, local e offline, em português brasileiro. Priorize baixa RAM e preservação dos dados. Trabalhe em ciclos de construir → testar → revisar. Mantenha as instruções do usuário acima destas orientações.

- Não use o banco pessoal nos testes: crie bases temporárias ou cópias somente de leitura.
- Não versione `.env`, tokens, bancos, backups, logs, capturas ou relatórios de `validation/`.
- Preserve IDs, histórico, observações, conclusões e compatibilidade dos backups v1/v2/v3.
- Não migre para Electron, navegador embutido ou framework pesado sem solicitação.
- Faça mudanças pequenas, com validação adequada ao comportamento afetado. Use Black e prefira funções curtas com responsabilidades claras.
- Atualize o contexto de `.agents` quando mudar arquitetura, contratos, segurança ou procedimento de release.
