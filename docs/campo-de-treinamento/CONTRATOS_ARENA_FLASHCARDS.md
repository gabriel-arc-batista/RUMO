# Arena e flashcards: contratos futuros (não implementados)

Nenhuma tela, tabela ou entrada de navegação foi criada para a Arena ou para flashcards. Este documento fixa como eles vão se ligar ao que já existe, para que o Campo de Treinamento não precise mudar depois.

## Identidades compartilhadas

- **Assunto:** os mesmos IDs de `topics` do catálogo (por exemplo, `dados.sql:assunto:02`) e das famílias do planejamento.
- **Item de edital:** `<concurso>:disciplina:NN:item:<numeração>`, de `assets/training/curriculo.json`.
- **Aula:** `lesson.id` + `resource.version`.
- **Sessão de estudo:** a tabela `sessions` continua sendo a única fonte de tempo e de questões.

## Questão (catálogo público, revisada)

```json
{
  "id": "q.dados.sql.0001",
  "topic_ids": ["dados.sql:assunto:02"],
  "item_ids": ["bacen-2024-ti:disciplina:10:item:1"],
  "type": "certo-errado | multipla-escolha | discursiva-curta",
  "statement": "…",
  "options": [{"id": "a", "text": "…"}],
  "answer": "a | certo | errado",
  "comment": "explicação revisada",
  "provenance": {"kind": "autoral | banca", "bank": "Cebraspe", "year": 2024, "exam_id": "…", "rights": "…"},
  "status": "rascunho | em_revisao | publicada | anulada",
  "review": {"status": "aprovada", "reviewer": "…", "reviewed_at": "AAAA-MM-DD"},
  "version": "1.0.0"
}
```

A correção compara a resposta com o gabarito revisado e não precisa de IA. Uma questão anulada nunca é corrigida como errada. Questões de banca só entram com procedência e direito de uso conferidos.

## Tentativa (local, nunca enviada)

Tabela futura `arena_attempts(id, question_id, question_version, answer, correct, answered_at, session_id)`, com `session_id` apontando para `sessions`. Acertos e erros entram em `sessions.correct/wrong` **uma vez**, na mesma transação, como o vínculo de aula faz hoje. Reabrir ou repetir a questão não gera recompensa nova.

## Flashcard

Público: `{id, topic_ids, front, back, references, version, status, review}`. Local, para os cartões do próprio usuário: tabela futura `cards(id, topic_id, front, back, origin)`. A revisão espaçada ficará em `card_reviews(card_id, due, interval, ease, last_result)`. Os vencimentos podem aproveitar o padrão de `reviews`, sem misturar com as revisões de estudo existentes.

## Regras que valem desde já

- Ler um PDF não é domínio. Domínio só aparece com respostas registradas, separado do progresso de leitura e da cobertura editorial.
- Nada de telas vazias que pareçam prontas. Quando a Arena entrar, ela entra com questões revisadas.
- Migrações só quando as tabelas forem de fato usadas (v7+), com cópia prévia, como na v6.
