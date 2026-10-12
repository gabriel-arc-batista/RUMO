# Versionamento e release

Repositório na conta pessoal **gabriel-arc-batista**, a mesma de projetos de sites. Não publicar em conta ou organização Briko. Verificar `gh api user` e o proprietário do remoto antes de qualquer push. A conta antiga pode aparecer no cache de `gh auth status`; confiar na identidade confirmada pela API. Repositório privado por padrão.

1. Revisar código, segurança e arquivos rastreados; excluir bancos, logs, `.env`, `validation/`, ferramentas baixadas e builds do Git.
2. Atualizar versão em `scripts/installer.iss`, documentação e script de verificação de upgrade. Mudanças de esquema exigem migração e testes antigos.
3. Rodar testes/QA relevantes e `python scripts/build.py`. PyInstaller gera pasta `dist/RUMO`, ZIP portátil e instalador Inno Setup. Para Inno, usar `tools/inno/ISCC.exe` ou o compilador instalado; ferramentas não entram no Git.
4. Validar o EXE isolado, licenças/assets, dependências e malware com ferramenta disponível. Registrar assinatura digital ausente enquanto não houver certificado.
5. Se atualização local tiver sido solicitada: guardar backup antes, verificar se há relógio ativo, fechar normalmente, instalar silenciosamente com tarefa `desktopicon`, conferir versão e hashes e reabrir. Preservar dados e preferência de tema. Não reiniciar nem matar sessão ativa para facilitar o build.
6. Commit descritivo, tag semântica `vX.Y.Z`, push para `origin/main` e release no repositório privado. Anexar apenas instalador, ZIP portátil Windows, tar.gz nativo Linux e SHA256SUMS; nunca bancos ou relatórios de caminhos pessoais.
7. Conferir commit remoto, release, assets e resultado da CI, se ativada. O workflow manual `.github/workflows/rumo-windows.yml` gera pacotes e hashes depois das verificações em Windows. Não declarar CI aprovada se estiver pendente.

Versão alvo atual: **2.0.0** (`scripts/installer.iss`). Esquema desktop 6, backups
v1–v6 preservados e workspace da conta separado. O pacote Linux foi construído
e validado com dados temporários. O serviço hospedado recebeu 001–008 e passou
Auth/RPC HTTPS e isolamento entre duas contas, removidas após validação.
Frontend final e CI Windows permanecem pendentes; não criar afirmação de release
ou site publicados antes de conferir os respectivos resultados. Evidências e
limites em `docs/integration/VALIDATION.md` e `RELEASE_CHECKS.md`.

## Serviço e site opcionais
Publicação web é independente do instalador. Seguir `docs/integration/SETUP.md`:
migrações testadas em projeto de desenvolvimento isolado, Auth/URLs autorizadas,
RLS e esquemas expostos revisados, build frontend e validação entre duas contas.
Nunca aplicar bootstrap/fixtures de testes nem chave administrativa ao cliente.
Não declarar deploy por ter gerado SQL ou por tests Docker terem passado.
Workspace da conta tem exportação separada; preservar dados antes da migração.
