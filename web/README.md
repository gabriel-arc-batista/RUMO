# RUMO — site

Campo de Treinamento (aulas em PDF), Arena (questões) e Flashcards (revisão espaçada), na mesma conta do aplicativo. Frontend em Vite + React + TypeScript; serviço do Codex em `backend/` (Supabase Auth + PostgreSQL/RLS + RPC), contrato em `docs/integration/CONTRACT.md`.

O site nunca acessa o banco do computador. Ele envia eventos (`push_events`) e lê os eventos aceitos (`pull_events`). Correção de questões, agenda dos cartões, XP e nível vêm do serviço.

## Rodar

```bash
cd web
npm ci
npm run dev            # http://localhost:5173
```

Sem configuração, o site abre no **modo EXEMPLO**: o "serviço" é simulado no navegador, com as mesmas regras do SQL, e todo o conteúdo leva o selo EXEMPLO. Qualquer e-mail com senha de 8 caracteres cria uma conta de teste guardada só neste navegador. Em Conta e progresso há uma opção para simular queda de conexão.

Para usar o serviço real, crie `web/.env.local` (fora do Git):

```
VITE_SUPABASE_URL=https://<projeto>.supabase.co
VITE_SUPABASE_ANON_KEY=<chave pública/publicável>
```

Nunca use a chave `service_role` no site.

## Comandos

| Comando | O que faz |
|---|---|
| `npm run build` | Typecheck + build de produção em `dist/` (copia fontes, retratos e PDFs de exemplo de `../assets`) |
| `npm test` | Testes de comportamento (Vitest): fila/replay, conflito entre dispositivos, conclusão manual, identidade de favoritos, correção, SM-2, importação |
| `npm run e2e` | Fluxo completo no Google Chrome real contra `npm run preview` (modo exemplo, porta 4173) |
| `npm run servico:up` | Sobe um Supabase mínimo e descartável (Postgres 17.6 + GoTrue + PostgREST + nginx como gateway) com as migrações de `backend/` e conteúdo de EXEMPLO. Gera `.env.servico.local` |
| `npm run build:servico` / `npm run preview:servico` | Build apontando para essa pilha e servidor na porta 4175 |
| `npm run e2e:servico` | Fluxo completo + cenários extras (favoritos/marcadores, nota de questão, sessão e nível, conflito entre dois dispositivos, isolamento entre contas, sair e entrar) contra o serviço real local |
| `python3 e2e/desktop_check.py` + `node e2e/desktop-para-site.mjs <email>` | Usa o cliente de sincronização do desktop (Codex) para conferir o que o site gravou e devolver ações ao site |
| `npm run servico:down` | Remove a pilha local |

Os testes no navegador usam `playwright-core` com o Chrome do sistema (`CHROME=/caminho` para outro). Capturas ficam em `e2e/.shots/` (não versionar).

## Publicar (Vercel)

Projeto Vercel com raiz `web/`. O `vercel.json` já define build, saída, reescrita de rotas para a SPA e cabeçalhos de segurança. Variáveis do ambiente: `VITE_SUPABASE_URL` e `VITE_SUPABASE_ANON_KEY`. No Supabase, autorize a URL do site em Auth → URL Configuration (login, confirmação e `/conta/nova-senha`).

O host dos PDFs publicados precisa permitir CORS para o domínio do site, porque o pdf.js baixa o arquivo pelo navegador. GitHub Pages permite; anexos de GitHub Releases não.

## Organização

```
src/service/    contrato (ponte com shared/rumo-api.ts), fila e sincronização (IndexedDB),
                serviço real (supabase.ts) e servidor de exemplo (example/)
src/domain/     projeção dos eventos, retrato do personagem, enunciados
src/pages/      Início, campo/ (biblioteca, detalhe, leitor), arena/, cards/, account/
src/components/ shell, sincronização, cronômetro explícito, diálogos e estados
src/styles/     tokens Norte Dourado (mesmos valores de theme.py) e estilos por área
```

## Terceiros

React, React Router, supabase-js (MIT), pdf.js (Apache-2.0), Lucide (ISC). Fontes Inter e Poppins (OFL) e retratos CC0 de N. Erebus vêm de `../assets` (ver `THIRD_PARTY_ASSETS.md`). Os PDFs de exemplo são gerados por `scripts/make-example-pdfs.mjs` e dizem em toda página que não são aulas.
