# Verificação da release integrada

A versão é lida de `scripts/installer.iss`; o workflow usa o mesmo valor no nome
do artefato. O banco desktop continua no esquema 6. O workspace da conta é
separado e não altera os backups existentes.

## Validação local e CI

- `python scripts/verify_upgrade.py self-test`: migração v5→v6 em banco temporário,
  comparando IDs, observações e conclusão de assuntos; nunca usa a base pessoal.
- `python -m unittest discover -s tests -v`: persistência, backups, sessão canônica,
  projeções, filas, CAS, renovação, reenvios e conflitos.
- `python scripts/verify_sync_gui.py`: interface nativa com conta desconectada,
  leitura manual e persistência em dados temporários, sem rede.
- O workflow Windows executa as verificações nativas antigas, build, executável,
  instalador e hashes. Quando há lockfile do frontend, exige `npm ci`, typecheck,
  testes e build. Não publica site nem serviço.
- O ZIP portátil é recusado se contiver `.env*`, bancos, tokens por nome,
  backups, logs, `validation/`, `.git` ou `node_modules`. PyInstaller recebe
  assets explícitos; revisar os arquivos efetivos do build antes da publicação.
  Esta inspeção de nomes não substitui revisão de segredos no código.

## Atualização autorizada de instalação pessoal

Somente quando o usuário tiver solicitado a atualização local: executar
`verify_upgrade.py prepare`, fechar normalmente o aplicativo, instalar e executar
`verify_upgrade.py verify`. Estes dois modos acessam os dados reais e não entram
na CI. A verificação exige esquema 6, integridade, relações e preservação de cada
registro antigo, além da correspondência entre arquivos instalados e build.
O backup `pre-v<VERSÃO>-...sqlite3` nunca é anexado à release.

## Publicação

Seguir `.agents/RELEASE.md` e `docs/integration/SETUP.md`. Distribuir somente
instalador, portátil Windows, tar.gz Linux e SHA256SUMS. O build web contém apenas
URL e chave pública; service-role, senhas, tokens e workspace não entram nele.
Verificar configuração Auth/RLS e fluxo entre duas contas no serviço isolado;
fixtures sintéticas não são conteúdo publicado. Registrar separadamente testes
locais, CI Windows e deploy real. Não anunciar etapas pendentes como aprovadas.

## Evidência local — 12/10/2026, versão 2.0.0

Build final Linux executado com Python 3.14.4 e PyInstaller 6.16.0 em ambiente
isolado. A suíte executou 171 testes, sem falhas e com um teste ignorado.
`verify_sync_gui.py` passou novamente após os ajustes de importação/journal e
conflitos. Também passaram `verify_rpg_gui.py`, `verify_rpg_dialogs.py` e
`verify_appearance_gui.py`; este último percorreu 13 temas e todas as opções,
com cache limitado a 24 imagens, persistência e métricas preservadas (98,4 MiB
RSS ao final; acréscimo de 13,5 MiB).

O executável empacotado abriu e fechou normalmente com `RUMO_DATA` temporário,
sem `PYTHONPATH`, `LD_LIBRARY_PATH`, `TK_LIBRARY` ou `TCL_LIBRARY` herdados. A base
criada manteve esquema 6 e `integrity_check=ok`. O tar.gz foi inspecionado para
recusar bancos, `.env*`, logs, backups, `.git` e `node_modules`; inclui
`docs/integration/SETUP.md` e as licenças de pypdfium2/PDFium. O hash final fica
em `dist/SHA256SUMS-linux.txt`, fora do Git.

O PyInstaller emitiu avisos sobre diretório opcional Tcl ausente e ícone ignorado
no Linux; a abertura do executável funcionou após o build. Esta validação não
substitui os testes do instalador e executável Windows. A revisão final do frontend, a CI Windows e a publicação do site/release
continuam pendentes. O serviço Supabase hospedado foi validado separadamente
com Auth/RPC HTTPS e duas contas temporárias, conforme `VALIDATION.md`. Não houve acesso a banco pessoal,
instalação local, commit, push ou publicação nesta verificação.

Repetição final após inclusão dos padrões públicos do serviço: GUI validou URL e
chave padrão, configuração avançada inicialmente oculta e dois ciclos de
revelar/ocultar, e-mail/senha vazios e senha mascarada. O transporte foi
substituído por mock e nunca instanciado; nenhuma conta foi conectada ou chamada
de rede efetuada. Migração temporária v5→v6 e os 171 testes passaram novamente
(um ignorado); o pacote foi reconstruído e o teste isolado de abertura/fechamento
repetido. O workflow fixa Node 24 para os testes do frontend. Metadados da CLI
em `supabase/.temp/` não fazem parte da distribuição ou do código necessário.
A validação do frontend e do serviço real é registrada pela revisão integrada,
separadamente destes testes nativos sem rede.

Serviço hospedado: migrações 001–008 aplicadas e validadas; Auth/RPC HTTPS,
isolamento entre duas contas e auditoria sem findings. Após limpeza, zero
usuários/eventos de teste. Esse resultado não significa que o site ou os
artefatos da release foram publicados. Frontend final e CI Windows pendentes.
