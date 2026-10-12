# Backend opt-in do RUMO

Migrações PostgreSQL 16 para Supabase: **não aplicadas a projeto remoto**. O desktop continua canônico offline. Leia `docs/integration/CONTRACT.md` antes de integrar. Nenhum catálogo real é incluído; fixtures vivem exclusivamente nos testes e se identificam como exemplos.

## Preparação local e validação

Execute `backend/tests/run.sh` com Docker disponível. O script cria um PostgreSQL descartável, simula somente `auth.users` e `auth.uid()`, aplica todas as migrações e executa as asserções SQL. Apaga o container ao terminar. Não lê banco pessoal, credenciais ou configurações Supabase. A imagem requer rede na primeira execução. A simulação de Auth não valida login/refresh/logout, PostgREST nem infraestrutura Supabase hospedada.

Para ambiente Supabase de desenvolvimento, aplicar `migrations/*.sql` em ordem como proprietário das migrações, com Auth já instalado. Não aplicar `tests/bootstrap.sql` no Supabase. Expor somente esquema `public` na API; `rumo_private` nunca deve entrar nos esquemas expostos. O frontend usa chave pública e Bearer da sessão. A chave administrativa nunca entra no frontend ou no desktop. Não há deploy automatizado.

`push_events(events)` e `pull_events(after_sequence,batch_size)` seguem o contrato. O pull inclui `result` derivado para tentativas, revisões e sessões. `study_summary()` deriva tempo, XP e moedas do estado atual das sessões, corrigindo o total após edição; questões são contadas somente quando vinculadas a uma sessão existente. Tentativas anuladas contam participação, mas não acertos. Nenhuma recompensa vem de leitura ou revisão. Sequências podem ter lacunas por rollback; cursor não presume contiguidade.

Operações de uma conta usam advisory lock transacional para combinar CAS e idempotência entre dispositivos. O lote inteiro falha se um evento é inválido. Histórico e tombstones não são apagados. Revogação dos grants impede escrita direta mesmo antes de RLS; implementações SECURITY DEFINER privadas têm search_path fixo e referências qualificadas. O gabarito está em tabela privada, separado da view pública sem resposta. Todas as tabelas privadas têm RLS. O dono das migrações é uma identidade administrativa de confiança.

## Agendamento determinístico

A adaptação de SM-2 mantém estado por conta/cartão/versão e histórico imutável de cada revisão. Uma versão ainda não revisada herda o estado da última versão revisada do cartão, sem apagar o estado anterior. Fator inicial 2,5; mínimo 1,3. Ratings 1/2/3/4 mapeiam para qualidade q=1/3/4/5. Erro zera repetições e agenda um dia. Respostas 2/3/4 incrementam repetições: primeiro intervalo um dia, segundo seis; demais arredondam para inteiro mais próximo (meios para cima) intervalo anterior × fator anterior, mínimo um dia. Após calcular o intervalo, fator novo = máximo(1,3; fator anterior + 0,1 − (5−q) × (0,08 + (5−q) × 0,02)), com quatro casas decimais. Prazo é derivado do recebimento no servidor. O replay do mesmo UUID não avança o agendamento. IDs distintos representam novas revisões confirmadas. Cartão pessoal usa a revisão CAS de `card.save` como versão; suspenso/excluído recusa revisão.

Versões de conteúdo são strings estáveis (incluindo `1.0.0`); IDs de sessões locais são strings preservadas. Favorito global pode ter versão vazia. Marcadores usam `target_type=bookmark`, com `target_id` apontando aula/versão/página.

## Conteúdo editorial

`rumo_lessons`, `rumo_cards` e `rumo_private.questions` recebem somente versões novas por uma operação editorial administrativa. UPDATE/DELETE são recusados; correções ou anulações entram em nova versão, preservando correção das tentativas antigas. Importar somente conteúdo revisado autorizado: esta camada não revisa materiais e não cria PDFs. Catálogo vazio é esperado. O banco não hospeda arquivos ou aceita caminhos locais.

## Limites

Não implementa inventário, compras, metas, ciclos, edital, migração de cartões entre IDs, upload legado nem PDFs pessoais. Não prova duração real do estudo: aceita até 86.400 segundos líquidos declarados por sessão explicitamente confirmada, conforme contrato. Testes locais verificam PostgreSQL e políticas SQL; validação hospedada e concorrência sob carga permanecem etapas separadas.

## Metadados e filtros

A migração 003 acrescenta matéria/assuntos/concursos, tipo de questão, proveniência e comentário. Proveniência é um objeto opcional: banca/ano/dificuldade permanecem ausentes quando desconhecidos. Comentário sai apenas no resultado de uma tentativa confirmada, nunca na view pública ou catálogo. `question_catalog(subject,topic,exam,wrong_only,favorite_only,bank,year,difficulty,batch_size)` filtra no servidor; erros usam a última tentativa do usuário na versão da questão, favoritos usam a projeção privada. Gabaritos continuam privados. `rumo_decks` distingue decks publicados de cartões pessoais, e cartões publicados aceitam vínculos de fonte/aula/questão. `rumo_lessons.resource` é metadado editorial opcional, não upload de PDF ou permissão para executar caminhos. Não há materiais revisados neste pacote.

A migração 004 completa `rumo_subjects`, `rumo_topics` e `rumo_exams`, leitura pública autenticada, e os campos editoriais das aulas. Aula publicada exige revisão aprovada, revisor/data e recurso HTTPS com tamanho/hash; aula planejada não recebe URL. Os catálogos possuem `example` explícito, usado nas fixtures de teste. Decks oferecem `topic_id` e `topic_ids`. Após confirmar, apenas o dono da tentativa recebe `answer` e `comment` no pull. `progress_summary()` fornece nível, XP dentro do nível, XP exigido para o próximo, moedas e `look:null`; aparência e ciclos permanecem fora da sincronização. Sessões do site podem usar `plan_id:"site"` e IDs editoriais estáveis, sem fingir conhecer os IDs locais do desktop.

A migração 005 separa rascunhos/publicações/arquivados de questões e cartões: catálogo seguro e tentativas/revisões admitem somente publicados ou exemplos explicitamente sinalizados. Publicação requer revisão aprovada com revisor/data; versões são imutáveis e a publicação cria nova versão. Aulas planejadas continuam visíveis como planejamento, mas recusam eventos de leitura (exceto fixtures com `example:true`). URLs editoriais de PDF recusam credenciais e caracteres de controle/espaço. As fixtures ocultas de teste representam rascunhos, não materiais disponíveis.

Migrações adicionais 003–006 acrescentam metadados editoriais, visibilidade,
catálogos de matérias/assuntos/concursos e `catalog_revision` monotônico para
escolher a edição mais recente. Versões são strings opacas, inclusive semver.
Planejadas não aceitam marcações; exemplos de teste são exceção identificada.
Questões/cartões publicados exigem aprovação; gabarito e comentário chegam
somente no `result` da tentativa do dono. `progress_summary` usa a mesma fórmula
de níveis da Jornada nativa e retorna `look:null`, pois aparência não sincroniza.

## Auditoria antes da publicação

`python3 backend/tests/run_postgrest.py` valida PostgreSQL **17.6** e PostgREST **14.2** sobre HTTP com JWTs sintéticos. `python3 backend/tests/run_auth_postgrest.py` acrescenta **GoTrue 2.177.0 real**: cadastro sintético, login por senha, refresh e logout, então RPC com os tokens reais emitidos pelo Auth. Ambos usam imagens Docker já disponíveis, containers descartáveis e portas somente em loopback; não leem credenciais hospedadas nem dados pessoais. O harness mantém histórico/checksum de migrações no banco de teste: reaplicação com checksum igual não repete DDL, conteúdo alterado após aplicação é erro. Isso simula o registro versionado que o deploy deve manter; arquivos SQL individuais não são scripts para reaplicar livremente.

A migração 007 coloca implementações SECURITY DEFINER no esquema privado e preserva as assinaturas públicas em adaptadores SECURITY INVOKER. Execução/uso do esquema são restritos a authenticated; acesso direto às tabelas de progresso continua revogado. A view de questões usa SECURITY INVOKER e RLS, com grants somente das colunas públicas; answer/comment não recebem SELECT. Envelope/payload são validados por tipo, campos permitidos e identidade canônica dos favoritos. Versões são strings opacas, sem coerção numérica.

Notas aceitam exatamente uma origem: aula (página opcional) ou questão (página nula), mantendo UUID/CAS/tombstone. Versão precisa estar disponível; criar nota não devolve resposta privada. `question_id` é opcional apenas para compatibilidade com notas anteriores de aula.

Limites de validação: não foi usado o gateway/Kong, SMTP, configuração hospedada, chaves assimétricas/JWKS, CAPTCHA, e-mail de recuperação/confirmado nem dispositivos pessoais. GoTrue usa chave HS256 temporária local; o JWT não é impresso. Logout revoga sessão/refresh, mas access tokens já emitidos continuam válidos até sua expiração. O cliente deve apagar tokens/fila visível ao sair conforme contrato; não afirmar revogação instantânea de JWT. Desempenho sob carga, contenção simultânea e quotas/rate limits hospedados precisam de validação própria. Migrações foram verificadas na versão local 17.6; não foi executada a versão hospedada 17.11.

`python3 backend/tests/run_migration_cli.py` verifica também o **CLI Supabase instalado**, em workspace temporário não vinculado: aplica os sete arquivos originais por `db push --db-url` exclusivamente em PostgreSQL17 descartável/loopback, confirma sete registros em `supabase_migrations.schema_migrations` e uma segunda execução sem reaplicar DDL. Vault é ignorado, sem acesso a tokens hospedados, instalação ou seed real. Esse teste usa o histórico real do CLI; o teste separado de checksum pertence ao harness, não presume que o CLI detecte alterações no conteúdo de versões já aplicadas. Após o primeiro deploy, congele arquivos aplicados e acrescente nova migração para mudanças.

A migração 008 fixa `search_path` do trigger editorial e indexa as três referências de chaves estrangeiras reportadas pelos Advisors. Arquivos 001–007 já aplicados foram congelados; mudanças novas entram somente em nova migração.

`backend/tests/run_hosted.py` é um teste HTTPS explícito: recebe `RUMO_HOSTED_URL`, `RUMO_HOSTED_PUBLIC_KEY` e `RUMO_HOSTED_ADMIN_KEY` somente do ambiente do processo, cria duas contas temporárias confirmadas, testa senha/refresh/logout/RPC/isolamento/CAS e remove as contas no `finally`. Não imprime chaves/tokens/senhas e recusa redirecionamentos para impedir envio de credenciais a outra origem. Cria somente eventos privados temporários, nunca fixtures editoriais ou PDFs na produção. Caso a exclusão falhe, mostra apenas IDs de contas para repetir a limpeza. Não executar sem autorização para criar/remover contas de teste no projeto escolhido. Não altera plano, assinatura, cobrança, organização ou configuração Auth.
