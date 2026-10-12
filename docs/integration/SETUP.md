# Execução e publicação da integração

Serviço gratuito RUMO criado em Supabase, organização autorizada pelo usuário. Origem: `https://dfxzxnrttppoonywfzwd.supabase.co`. Migrações 001–008 aplicadas e Auth/RPC HTTPS validados com contas temporárias removidas. Site publicado: `https://rumo-estudos.vercel.app`, plano Hobby gratuito, smoke de login/persistência/logout aprovado. Consulte `DEPLOYMENT.md` antes de futuras migrações: os identificadores MCP diferem dos prefixos locais.

1. Ler CONTRACT.md e backend/README.md. Desenvolvimento sem conta continua por `python app.py`.
2. Para validar banco isolado: `bash backend/tests/run.sh`. Para fluxo Python integrado: `RUMO_POSTGRES_TEST=1 python -m unittest discover -s tests -p test_sync_integration.py -v`. Docker usa somente banco descartável.
3. Num projeto Supabase de desenvolvimento separado, aplicar `backend/migrations/*.sql` em ordem como proprietário, com Supabase Auth instalado. Não usar bootstrap ou fixtures em produção. Expor apenas `public`, nunca `rumo_private`. Configurar provedores de Auth, confirmação de e-mail, política de senhas e URLs autorizadas para login/redefinição. Rever RLS antes de uso real.
4. Claude: configuração pública em `web/.env.local` ignorado (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` ou chave publicável compatível); seguir web/README.md quando concluído. Nunca incluir service_role. Tipo de versão é string opaca.
5. Desktop: Configurações → Conta e sincronização. O serviço RUMO vem preenchido; entrar com as credenciais da mesma conta. Configuração do serviço permite conferir a origem/chave pública ou escolher uma instalação própria. Consentimento autoriza **novas** ações. Ações anteriores são escolhidas individualmente. Token só memória; entrar novamente após reinício. Associação de sessões remotas escolhe um assunto do plano atual e não pede quantidades.
6. Servidor não hospeda PDFs. Publicar apenas conteúdo revisado autorizado com HTTPS, SHA-256, bytes e versão estável. Planejamento sem recurso não é aula disponível. Nenhum serviço de IA é necessário.
7. Publicação exige validar Auth real/PostgREST, acesso de duas contas, IndexedDB offline do site, reader/CSP/downloads, build web e executável Windows. Confirmar resultado da hospedagem antes de dizer que foi publicada. Catálogo permanece vazio até conteúdo editorial real.

Workspace independente `study-sync.sqlite3` contém eventos pessoais, cursor, vínculo e metadados públicos; nunca versioná-lo. Configurações oferecem exportação consistente separada. Backups desktop v1–v6 conservam o formato original. Restaurar backup local não muda o remoto; preservar/exportar ambos antes de restaurar. Não modificar bancos pessoais para testar.

SM-2 documentado em FLASHCARDS.md. Inventário, compras, aparência, ciclos, edital/metas e registros antigos fora das ações selecionadas continuam locais. XP remoto representa ganhos das sessões compartilhadas; aparência e equipamentos locais não são apresentados como sincronizados.

Auth mantém confirmação de e-mail. O remetente padrão do Supabase limita confirmação/recuperação aos membros da organização; uso público desses e-mails requer SMTP próprio. Nenhum plano pago/adicional foi contratado. Essa entrega não configurou SMTP externo nem testou entrega de mensagens.
