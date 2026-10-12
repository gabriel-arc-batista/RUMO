# Trabalho em andamento — Codex, 12/10/2026

Contexto principal continua em `.agents/README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `TESTING.md`, `logs_claude.md`.

**Contrato compartilhado:** `docs/integration/CONTRACT.md` (ler antes de implementar).

Claude: frontend em `web/`. Codex: `backend/`, `shared/`, `sync_client.py`, `study_sync.py`, `desktop_sync.py`, `screen_account.py`, `tests/test_sync*`, `tests/test_study_sync.py`, documentação `docs/integration/`. Codex fará edições pequenas em `app.py` (entrada da conta), `training.py`, `pdf_reader.py` e `screen_training.py` (marcação manual por página); não mexer nesses arquivos simultaneamente. Não mover runtime desktop para navegador.

A API é Supabase Auth + RPC versionada. Ainda não há serviço publicado. Exemplos em `shared/examples.json` não são conteúdo editorial. Catálogo real vazio deve ser tratado como vazio.

Frontend deve chamar RPC com token do usuário, nunca gravar tabelas privadas ou aceitar XP arbitrário. Implementar fila IndexedDB, confirmação de resposta e resolução explícita de conflitos. As três áreas usam eventos e sessões explícitas.

Atualizar o contrato em conjunto ao introduzir campos. Validação final do browser depende do frontend concluído; não declarar integrada antes de rodar.

## Etapa Codex implementada
Backend, clientes e integração nativa disponíveis; migrações 001–006 não publicadas.
Respostas detalhadas às lacunas frontend estão em SITE_WORK.md. Validação real
PostgreSQL com fila Python em dois dispositivos cobre Campo/Arena/Flashcards e
Store/RPG, além de GUI nativa temporária. Frontend ainda em implementação: versão
string opaca, ordenação catalog_revision, IDs favoritos canônicos, sessão site e
resultados privados precisam ser consumidos antes do teste de navegador completo.

## Publicação autorizada pelo usuário (12/10/2026)
Ao concluir frontend e integração, usuário pediu “integre tudo e suba”. Commit,
push/release e publicação do site/serviço estão autorizados; não publicar etapa
incompleta. “Acho que é v3” foi hipótese: GitHub atual indica v1.0.0 como latest,
sem v2/v3. Definir numeração coerente com histórico ao preparar release.
Codex está preparando release/backend e validando fonte; `web/` continua em uso
pelo Claude até declarar concluído. Nenhum banco pessoal em QA.

## Handoff pendente para publicação integrada
Native Linux 2.0.0 preparado: build com 171 testes sem falhas / 1 opt-in ignorado,
GUI temporária e binário independente aprovados; hash em dist (não versionar).
Backend Auth/PostgREST/CLI locais aprovados, serviço hospedado ainda não criado.
Frontend compila e smoke exemplo passou, mas versões/favoritos/bookmarks precisam
alinhar ao contrato e npm test precisa de testes. Nenhum commit/push/deploy efetuado.
Duas respostas solicitadas: organização Supabase (create_project exige escolha
explícita e depois confirmação de custo), e status do Claude para editar web sem
colisão. Publicação autorizada continua válida; não pedir novamente por push.
Ao retomar: get_cost/confirm_cost depois organização; validar frontend completo,
criar serviço isolado, configurar Auth/URLs, integrar default público no desktop,
rebuild se mudar configuração/código, commit em main, CI Windows, release e deploy.
`shared/rumo-api.ts` exporta validatePublicKey e recusa chaves privilegiadas; chamar
antes de createClient para falhar cedo. Não assumir exemplos como conteúdo real.

Atualização posterior: Claude alinhou strings/favoritos/ordem editorial e adicionou
15 testes; types/build web passaram. Testes: 14 aprovados / 1 falha no helper waitFor
(off lido antes de inicializar; solução detalhada SITE_WORK). Handoff ainda não
recebido e hosted pendente. Pacote Linux com 171 testes, 0 falhas; integração PostgreSQL
opt-in passou separadamente. Status não é publicado/integrado em produção.

## Serviço remoto criado com custo zero
Usuário aprovou organização chessrex39-max's Org e exige zero custo, sem planos
pagos/adicionais. get_cost retornou0 e create_project free confirmou RUMO
ref dfxzxnrttppoonywfzwd sa-east1 ACTIVE_HEALTHY. Migrações001–007 aplicadas;
backend revisará008 para immutable_content search_path/índices FK. Não editar
migrações já aplicadas. Publicável e URL em service_config.py; native preenchido
por padrão, serviço avançado oculto, GUI temporária sem rede aprovou defaults.
CLI Supabase conectado e configpull em pasta temporária; Vercel usuário
chessrex39-max plano Hobby confirmado viaAPI. Claude ainda trabalha: preservar
web e aguardar handoff. Não há site publicado ainda.
