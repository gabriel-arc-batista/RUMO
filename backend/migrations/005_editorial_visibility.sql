begin;
alter table rumo_private.questions
 add column status text not null default 'rascunho' check(status in ('rascunho','publicada','arquivada')),
 add column review jsonb not null default '{"status":"pendente","reviewer":null,"reviewed_at":null}' check(jsonb_typeof(review)='object'),
 add constraint question_publication_review check(status<>'publicada' or (
  coalesce(review->>'status','')='aprovada' and coalesce(length(review->>'reviewer'),0)>0 and review->>'reviewed_at' is not null));
alter table public.rumo_cards
 add column status text not null default 'rascunho' check(status in ('rascunho','publicada','arquivada')),
 add column review jsonb not null default '{"status":"pendente","reviewer":null,"reviewed_at":null}' check(jsonb_typeof(review)='object'),
 add constraint card_publication_review check(status<>'publicada' or (
  coalesce(review->>'status','')='aprovada' and coalesce(length(review->>'reviewer'),0)>0 and review->>'reviewed_at' is not null));
alter table public.rumo_lessons add constraint safe_pdf_url check(pdf_url is null or (
 pdf_url ~ '^https://[^/@[:space:][:cntrl:]]+(/[^[:space:][:cntrl:]]*)?$'
));
create or replace view public.rumo_questions with(security_barrier=true) as
 select id,version,prompt,options,annulled,type,subject_id,topic_ids,exam_ids,provenance,example,status,review
 from rumo_private.questions where status='publicada' or example;
drop policy catalog_read on public.rumo_cards;
create policy catalog_read on public.rumo_cards for select to authenticated using(status='publicada' or example);
commit;
