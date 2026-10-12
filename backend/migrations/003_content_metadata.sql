begin;
alter table public.rumo_lessons add column subject_id text,
 add column topic_ids text[] not null default '{}',
 add column exam_ids text[] not null default '{}',
 add column resource jsonb;
alter table rumo_private.questions
 add column type text not null default 'multipla-escolha' check(type in ('multipla-escolha','certo-errado')),
 add column comment text not null default '',
 add column subject_id text,
 add column topic_ids text[] not null default '{}',
 add column exam_ids text[] not null default '{}',
 add column provenance jsonb not null default '{}' check(jsonb_typeof(provenance)='object');
create or replace view public.rumo_questions with(security_barrier=true) as
 select id,version,prompt,options,annulled,type,subject_id,topic_ids,exam_ids,provenance
 from rumo_private.questions;
create table public.rumo_decks (
 id text not null, version text not null,
 title text not null, subject_id text,
 topic_ids text[] not null default '{}',
 source text, primary key(id,version)
);
alter table public.rumo_decks enable row level security;
create policy catalog_read on public.rumo_decks for select to authenticated using(true);
create trigger immutable_deck before update or delete on public.rumo_decks
 for each row execute function rumo_private.immutable_content();
alter table public.rumo_cards add column deck_id text, add column deck_version text,
 add column source text, add column lesson_id text, add column lesson_version text,
 add column question_id text, add column question_version text,
 add constraint published_deck foreign key(deck_id,deck_version) references public.rumo_decks(id,version);
revoke all on public.rumo_decks from public,anon,authenticated;
grant select on public.rumo_decks to authenticated;

-- Does not expose answer or comment. Wrong filter uses the latest confirmed
-- attempt per version; favorites refer to the current user's projected state.
create function public.question_catalog(
 subject text default null, topic text default null, exam text default null,
 wrong_only boolean default false, favorite_only boolean default false,
 bank text default null, year integer default null, difficulty text default null,
 batch_size integer default 200
) returns jsonb language plpgsql security definer set search_path=pg_catalog,rumo_private as $$
declare uid uuid:=auth.uid();
begin
 if uid is null then raise exception 'unauthenticated'; end if;
 if batch_size is null or batch_size not between 1 and 200 then raise exception 'invalid_event'; end if;
 return coalesce((select jsonb_agg(to_jsonb(t)) from (
  select q.id,q.version,q.prompt,q.options,q.annulled,q.type,q.subject_id,q.topic_ids,q.exam_ids,q.provenance,coalesce((to_jsonb(q)->>'example')::boolean,false) as example,coalesce((to_jsonb(q)->>'catalog_revision')::bigint,0) as catalog_revision
  from rumo_private.questions q
  where (coalesce(to_jsonb(q)->>'status','')='publicada' or coalesce((to_jsonb(q)->>'example')::boolean,false))
   and (subject is null or q.subject_id=subject)
   and (topic is null or topic=any(q.topic_ids))
   and (exam is null or exam=any(q.exam_ids))
   and (bank is null or q.provenance->>'bank'=bank)
   and (year is null or q.provenance->>'year'=year::text)
   and (difficulty is null or q.provenance->>'difficulty'=difficulty)
   and (not wrong_only or (select r.result->>'status'
    from rumo_private.events e join rumo_private.results r on r.user_id=e.user_id and r.event_id=e.id
    where e.user_id=uid and e.kind='arena.attempt' and e.payload->>'question_id'=q.id
    and e.payload->>'version'=q.version order by e.sequence desc limit 1)='incorrect')
   and (not favorite_only or exists(select 1 from rumo_private.entities f
    where f.user_id=uid and f.kind='favorite.set' and f.payload->>'target_type'='question'
    and f.payload->>'target_id'=q.id and f.payload->>'version' in ('',q.version)
    and f.payload->>'favorite'='true'))
  order by q.id,q.version limit batch_size
 )t),'[]'::jsonb);
end $$;
revoke all on function public.question_catalog(text,text,text,boolean,boolean,text,integer,text,integer) from public,anon;
grant execute on function public.question_catalog(text,text,text,boolean,boolean,text,integer,text,integer) to authenticated;
commit;
