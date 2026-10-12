# Validação da integração 2.0.0 — 12/10/2026

- Suíte específica de sincronização: 37 testes aprovados e um PostgreSQL opt-in; suíte completa conferida novamente no build final.
- `backend/tests/run.sh`: PostgreSQL 16/Docker real descartável, sete migrações. RLS entre contas, RPC, repetição, CAS, rollback, gabarito privado, versões semver, suspensão, metadados/filtros, rascunhos ocultos e aprovação editorial.
- PostgreSQL 17.6/PostgREST 14.2/GoTrue 2.177.0 reais em containers locais: cadastro/login/refresh/logout, RPC HTTP, isolamento, CAS concorrente. CLI Supabase aplicou sete migrações em banco descartável e confirmou ausência de reaplicação. Nenhum bootstrap de teste autorizado em produção.
- `test_sync_integration.py`: dois workspaces (representando browser/desktop), páginas distintas combinadas, desmarcação recalcula conclusão, tentativa repetida uma vez, flashcard agendado uma vez, sessão importada duas vezes com um registro/10 XP. Transporte SQL usa mesmas RPCs, não HTTP.
- `test_sync_desktop.py`: associação não envia histórico, PDFs pessoais locais, contagens manuais preservadas, associação de assunto não se torna edição remota, ack antes de pull preserva estado/revisão offline.
- Journal de importação: falhas antes/depois da gravação canônica, retomada após reinício e rollback da finalização não duplicam resultados. Mudanças manuais intervenientes são preservadas; Configurações → Resolver conflitos permite conferir e confirmar os totais locais.
- `scripts/verify_sync_gui.py`: Tk real Linux, base e PDF de teste temporários; configurações sem conta, checkbox do leitor, última página sem conclusão automática, todas páginas concluem, desmarcação desfaz, nenhum XP/sessão por leitura.
- Black nos Python alterados; TypeScript compartilhado `tsc --noEmit --strict --lib es2022,dom`; Bandit nos quatro módulos novos revisado (consultas parametrizadas, sem alertas após simplificação); arquivos rastreados sem padrões conhecidos de segredos.

Serviço RUMO hospedado recebeu migrações 001–008 e passou Auth/RPC HTTPS com duas contas temporárias; dados de teste removidos (zero usuários/eventos após limpeza). Auditoria de segurança Supabase sem findings após 008. Não houve uso do banco pessoal,
teste final do browser hospedado, build Windows desta versão ou teste de carga
remoto. Browser em modo exemplo abriu login/início/Campo/Arena/Flashcards/conta sem pageerror;
tipos/build frontend passaram; os testes foram adicionados pelo Claude e estão sendo revistos na integração final.
O frontend ainda precisa alinhar os itens em `.agents/SITE_WORK.md` antes
que a integração final possa ser declarada pronta. Backups antigos continuam no
formato canônico; dados da conta/fila têm exportação separada.

Pacote Linux 2.0.0: 171 testes sem falhas (um ignorado), migração temporária v5→v6
e GUI de conta/leitura aprovadas. Executável abre/fecha com base temporária
integra no esquema 6 e sem variáveis do runtime de desenvolvimento. Documentos,
licenças e ausência de bancos/credenciais no tar conferidos. Os detalhes ficam
em `RELEASE_CHECKS.md`. CI Windows, revisão integrada final do frontend e
publicação do site/release ainda pendentes; nenhuma destas etapas é presumida
aprovada pela validação do serviço.
