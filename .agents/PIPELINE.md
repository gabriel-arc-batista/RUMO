# Esteira de trabalho com vários agentes

Claude coordena e audita; agy, DeepSeek e GLM (terminais do Orca) implementam.
O usuário não precisa autorizar cada etapa; commit, push, tag, release e deploy
continuam exigindo o "ok" explícito dele.

## Etapas

1. **Especificar (Claude):** tarefa em `.agents/tasks/<id>.md` com objetivo, arquivos
   permitidos, contrato, critérios de aceite e comandos de validação.
2. **Criar (agente):** só nos arquivos permitidos. Ler antes `AGENTS.md`,
   `.agents/CONVENTIONS.md`, este arquivo e a tarefa.
3. **Testar (agente):** os comandos da tarefa, mais `-W error::ResourceWarning`
   nos testes tocados e `black --check` nos arquivos tocados.
4. **Revisar (agente):** reler o próprio diff contra a checklist de
   `CONVENTIONS.md` (camadas, enxuto, vazamentos, dados) antes de reportar.
5. **Reportar (agente):** `worker_done` pelo Orca com: arquivos alterados, comandos
   rodados e resultado, desvios do contrato e pendências. Sem afirmar o que não rodou.
6. **Auditar (Claude):** diff, suíte completa, Black, Bandit, vazamentos, captura de
   tela quando houver UI. Reprovado volta ao mesmo agente com a lista do que corrigir.
7. **Integrar (Claude):** `app.py`, docs de `.agents/`, registro em `logs_claude.md`.

## Regras para os agentes

- Não edite arquivos fora da lista da tarefa. Precisa de outro arquivo? Pergunte com
  `orca orchestration ask` e espere.
- Não faça commit, push, `git stash`, `git checkout --`, `git reset`, nem apague arquivos
  que não criou. Outros agentes trabalham na mesma pasta ao mesmo tempo.
- Não rode `black .`, instalação de pacotes, nem o app com a base pessoal.
- Python do projeto: `.venv/bin/python`. Testes: `.venv/bin/python -m unittest ...`.
- Dúvida de produto ou contrato: `ask` ao coordenador; não invente.

## Quem é dono do quê

| Área | Dono |
|---|---|
| `app.py`, `core.py`, `backups.py`, `storage.py`, `*_schema.py`, `.agents/*` | Claude |
| Arquivos listados em cada tarefa ativa | o agente da tarefa |
| Todo o resto | ninguém: não edite sem tarefa |

Tarefas ativas e histórico: `.agents/tasks/`.
