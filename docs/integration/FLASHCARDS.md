# Revisões e cartões pessoais

Esta entrega usa uma adaptação determinística de SM-2 sem dependência runtime.
A alternativa FSRS foi consultada na documentação oficial
https://open-spaced-repetition.github.io/py-fsrs/; exigiria parâmetros e integração
maiores. Esta fórmula não pretende implementar FSRS nem prever retenção.

O estado começa com facilidade 2,5, zero repetições e intervalo zero. Avaliações
Errei/Difícil/Bom/Fácil correspondem à qualidade 1/3/4/5. Errei reinicia repetições
e agenda um dia. As primeiras respostas positivas agendam 1 e 6 dias; seguintes
usam arredondamento half-up do intervalo anterior × facilidade anterior. Depois,
facilidade = max(1,3, facilidade + 0,1 − (5−q)×(0,08+(5−q)×0,02)). A próxima
revisão soma dias completos ao `received_at` UTC atribuído pelo servidor.

Eventos são processados por sequência crescente e deduplicados por UUID. A
agenda por cartão e versão usa apenas revisões aceitas: reenvios não contam.
Cartão suspenso não aceita nova revisão. Edição publicada cria versão nova:
histórico e agenda da versão antiga permanecem; na primeira revisão da nova
versão, o estado anterior é herdado, sem criar revisão adicional.
Cartões pessoais preservam identidade nas edições; exclusões são tombstones.

Importação/exportação UTF-8 JSON: `{ "format": "RUMO-personal-cards",
"version": 1, "cards": [...] }`. Campos seguem `card.save` no CONTRACT.md.
Exportação pode incluir `id` e `revision`; importação remove esses metadados e
retorna rascunhos a serem confirmados pelo usuário como novos cartões. Limite
2 MiB, mil cartões e 20 mil caracteres por texto. Não importa revisões nem XP.
Notas/erros geram somente rascunhos: a frente precisa ser preenchida antes de
salvar. Conteúdo e progresso publicados permanecem separados.

Referência da fórmula e intervalos SM-2: https://super-memory.com/english/ol/sm2.htm.
A escala de quatro botões é adaptação explícita (qualidades 1,3,4,5); não é o SM-2
original de seis avaliações. O serviço é autoridade e o Python reproduz a mesma
fórmula para projeção; o site deve usar o resultado aceito.
