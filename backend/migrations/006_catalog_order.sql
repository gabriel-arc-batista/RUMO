-- Content versions are opaque identifiers, not sortable numbers.
begin;
alter table public.rumo_lessons add column catalog_revision bigint generated always as identity;
alter table rumo_private.questions add column catalog_revision bigint generated always as identity;
alter table public.rumo_cards add column catalog_revision bigint generated always as identity;
alter table public.rumo_decks add column catalog_revision bigint generated always as identity;
create or replace view public.rumo_questions with(security_barrier=true) as
 select id,version,prompt,options,annulled,type,subject_id,topic_ids,exam_ids,provenance,example,status,review,catalog_revision
 from rumo_private.questions where status='publicada' or example;
commit;
