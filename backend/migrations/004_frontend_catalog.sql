begin;
create table public.rumo_subjects(id text primary key,name text not null);
create table public.rumo_topics(
 id text primary key,subject_id text not null references public.rumo_subjects(id),
 parent_id text references public.rumo_topics(id),name text not null,
 check(parent_id is distinct from id)
);
create table public.rumo_exams(id text primary key,name text not null);
alter table public.rumo_subjects enable row level security;
alter table public.rumo_topics enable row level security;
alter table public.rumo_exams enable row level security;
create policy catalog_read on public.rumo_subjects for select to authenticated using(true);
create policy catalog_read on public.rumo_topics for select to authenticated using(true);
create policy catalog_read on public.rumo_exams for select to authenticated using(true);
revoke all on public.rumo_subjects,public.rumo_topics,public.rumo_exams from public,anon,authenticated;
grant select on public.rumo_subjects,public.rumo_topics,public.rumo_exams to authenticated;
alter table public.rumo_lessons
 add column status text not null default 'planejada' check(status in ('publicada','planejada')),
 add column summary text not null default '',
 add column objectives text[] not null default '{}',
 add column prerequisite_topic_ids text[] not null default '{}',
 add column sources jsonb not null default '[]' check(jsonb_typeof(sources)='array'),
 add column review jsonb not null default '{"status":"pendente","reviewer":null,"reviewed_at":null}' check(jsonb_typeof(review)='object'),
 add column version_label text,
 add column pdf_url text,
 add column sha256 text check(sha256 is null or sha256 ~ '^[a-fA-F0-9]{64}$'),
 add column bytes bigint check(bytes is null or bytes>0),
 add column outline jsonb not null default '[]' check(jsonb_typeof(outline)='array'),
 add column example boolean not null default false,
 add constraint published_resource check(
  (status='planejada' and pdf_url is null) or
  (status='publicada' and pdf_url is not null and pdf_url ~ '^https://[^[:space:]]+$' and sha256 is not null and bytes is not null
   and coalesce(review->>'status','')='aprovada' and coalesce(length(review->>'reviewer'),0)>0 and review->>'reviewed_at' is not null)
 );
alter table public.rumo_decks add column topic_id text,add column example boolean not null default false;
alter table public.rumo_cards add column example boolean not null default false;
alter table rumo_private.questions add column example boolean not null default false;
create or replace view public.rumo_questions with(security_barrier=true) as
 select id,version,prompt,options,annulled,type,subject_id,topic_ids,exam_ids,provenance,example
 from rumo_private.questions;

-- xp is progress within this level; xp_next is 100 * level, as in native Journey.
create function public.progress_summary() returns jsonb
language plpgsql security definer set search_path=pg_catalog,rumo_private as $$
declare totals jsonb; xp bigint; lvl bigint; floor_xp bigint;
begin
 totals:=public.study_summary(); xp:=(totals->>'xp')::bigint;
 lvl:=greatest(1,floor((1+sqrt(1+8*(xp/100)::numeric))/2)::bigint);
 while 50*lvl*(lvl+1)<=xp loop lvl:=lvl+1; end loop;
 floor_xp:=50*(lvl-1)*lvl;
 return jsonb_build_object('level',lvl,'xp',xp-floor_xp,'xp_next',100*lvl,'coins',totals->'coins','look',null);
end $$;
revoke all on function public.progress_summary() from public,anon;
grant execute on function public.progress_summary() to authenticated;
commit;
