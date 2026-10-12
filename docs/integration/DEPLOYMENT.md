# Publicação da integração RUMO

Baseline verificado em **12/10/2026**. Projeto Supabase `dfxzxnrttppoonywfzwd`, região `sa-east-1`, organização escolhida pelo usuário. Plano **Free**, custo de criação informado **US$ 0**. O usuário exige não contratar planos pagos; qualquer alteração com cobrança exige nova autorização explícita. Não há chaves, senhas ou tokens neste documento.

## Histórico aplicado

As migrações foram aplicadas pelo MCP do Supabase. O serviço gerou versões de histórico diferentes dos prefixos dos arquivos locais:

| Arquivo local congelado | Versão no histórico hospedado |
|---|---|
| `001_sync.sql` | `20261012051057` |
| `002_projections.sql` | `20261012051102` |
| `003_content_metadata.sql` | `20261012051104` |
| `004_frontend_catalog.sql` | `20261012051107` |
| `005_editorial_visibility.sql` | `20261012051109` |
| `006_catalog_order.sql` | `20261012051111` |
| `007_private_rpc.sql` | `20261012051113` |
| `008_advisor_hardening.sql` | `20261012051453` |

**Não executar `supabase db push` dos arquivos `001`–`008` diretamente contra esse projeto.** O CLI compara identificadores de versões, não apenas o conteúdo SQL: os prefixos locais não coincidem com o histórico remoto e poderiam ser tratados como migrações novas. Os testes locais do CLI, com banco descartável iniciado vazio, não autorizam reaplicar a baseline hospedada.

Arquivos aplicados estão congelados. Toda alteração posterior deve entrar em uma nova migração; não editar a baseline para corrigir um projeto já criado.

Antes de adotar deploy pelo CLI, reconciliar explicitamente a baseline em workspace isolado: consultar o histórico remoto e comparar esquema/conteúdo de cada migração; preparar cópias com os oito identificadores hospedados acima; conferir que o CLI apresenta correspondência local/remota; revisar `db push --dry-run` antes de aplicar somente migrações novas. A reconciliação deve preservar o histórico já aplicado. Não executar `migration repair`, marcar versões como revertidas ou remover histórico automaticamente para contornar divergências. Registrar o procedimento escolhido antes da primeira publicação pelo CLI.

## Evidência verificada

- Migrações `001`–`008` aplicadas no projeto escolhido.
- Advisors hospedados de segurança sem avisos após a migração `008`. Desempenho registrou somente três índices ainda sem uso no catálogo vazio; os índices de chaves estrangeiras foram preservados.
- Teste HTTPS hospedado aprovado: login por senha, refresh/logout, RPC autenticado, replay idempotente, CAS, isolamento entre duas contas, projeção de XP e catálogo seguro.
- Contas temporárias removidas: **zero contas de teste restantes** após a limpeza verificada. Nenhuma fixture editorial ou PDF de teste foi publicado no banco hospedado.
- Validação local adicional: PostgreSQL 17.6, PostgREST 14.2 e GoTrue 2.177.0 em containers descartáveis; testes SQL, HTTP, CAS simultâneo, fluxo Python de dois dispositivos e aplicação/reaplicação via CLI em banco vazio.

Logout revoga refresh/sessão; JWTs de acesso já emitidos permanecem válidos até expirar. Advisors sem avisos e testes aprovados descrevem estas verificações; não constituem garantia de ausência de defeitos.

## Configuração e publicação do frontend

O frontend recebe somente URL do projeto e chave pública/publicável, por `VITE_SUPABASE_URL` e `VITE_SUPABASE_ANON_KEY`. Chave administrativa/service-role nunca entra em `web/`, bundle, logs, argumentos de comando ou artefato de publicação. O nome histórico `ANON_KEY` da variável não permite substituir seu valor por uma chave administrativa.

A configuração Auth deve cadastrar a origem HTTPS final e os redirects reais do frontend antes do teste de login/recuperação nessa origem. Login/refresh/logout HTTPS foram testados; entrega de e-mail, recuperação por e-mail e redirects na origem final precisam da verificação correspondente. Aparência, ciclos e PDFs pessoais permanecem locais conforme `CONTRACT.md`.

Publicação Vercel só deve prosseguir no plano gratuito autorizado. Um bundle prebuilt exige configuração pública incorporada no build, assets estáticos e roteamento das rotas da SPA para `index.html`; não basta publicar arquivos soltos que retornem 404 ao abrir links internos. Testar o bundle e os redirects na origem efetiva antes de anunciar o site publicado. Esta baseline não afirma que o frontend já foi publicado nem informa uma URL Vercel final.

## Operação posterior

Use ambientes/dados temporários nos testes e nunca o banco pessoal. O script `backend/tests/run_hosted.py` exige credenciais apenas no ambiente do processo, cria contas isoladas e remove-as no `finally`; ele não muda cobrança nem semeia conteúdo editorial. Depois de executá-lo, conferir a limpeza também no projeto.

Publicação de conteúdo real exige revisão editorial e uma versão nova com proveniência válida. Catálogo vazio é estado legítimo. Não converter exemplos em materiais aprovados para preencher o site. Conservar URLs HTTPS sem credenciais, SHA-256/tamanho dos PDFs e aprovação registrada nas aulas publicadas.
