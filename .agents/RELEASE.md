# Versionamento e release

Repositório na conta pessoal **gabriel-arc-batista**, a mesma de projetos de sites. Não publicar em conta ou organização Briko. Verificar `gh api user` e o proprietário do remoto antes de qualquer push. A conta antiga pode aparecer no cache de `gh auth status`; confiar na identidade confirmada pela API. Repositório privado por padrão.

1. Revisar código, segurança e arquivos rastreados; excluir bancos, logs, `.env`, `validation/`, ferramentas baixadas e builds do Git.
2. Atualizar versão em `scripts/installer.iss`, documentação e script de verificação de upgrade. Mudanças de esquema exigem migração e testes antigos.
3. Rodar testes/QA relevantes e `python scripts/build.py`. PyInstaller gera pasta `dist/RUMO`, ZIP portátil e instalador Inno Setup. Para Inno, usar `tools/inno/ISCC.exe` ou o compilador instalado; ferramentas não entram no Git.
4. Validar o EXE isolado, licenças/assets, dependências e malware com ferramenta disponível. Registrar assinatura digital ausente enquanto não houver certificado.
5. Se atualização local tiver sido solicitada: guardar backup antes, verificar se há relógio ativo, fechar normalmente, instalar silenciosamente com tarefa `desktopicon`, conferir versão e hashes e reabrir. Preservar dados e preferência de tema. Não reiniciar nem matar sessão ativa para facilitar o build.
6. Commit descritivo, tag semântica `vX.Y.Z`, push para `origin/main` e release no repositório privado. Anexar apenas instalador, ZIP portátil e SHA256SUMS; nunca bancos ou relatórios de caminhos pessoais.
7. Conferir commit remoto, release, assets e resultado da CI, se ativada. O template está em `.agents/templates/checks.yml`; a publicação inicial não ativou CI por ausência do escopo `workflow`. Não declarar CI aprovada se estiver pendente.

Na primeira publicação, a versão final auditada é 1.4.1; não anexar o build 1.4.0 anterior às correções de segurança.
