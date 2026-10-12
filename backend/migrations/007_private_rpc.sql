begin;
-- Public exposes invoker-only adapters; privileged implementations stay private.
alter function public.push_events(jsonb) set schema rumo_private;
alter function public.pull_events(bigint,integer) set schema rumo_private;
alter function public.study_summary() set schema rumo_private;
alter function public.progress_summary() set schema rumo_private;
alter function public.question_catalog(text,text,text,boolean,boolean,text,integer,text,integer) set schema rumo_private;
grant usage on schema rumo_private to authenticated;
revoke all on all functions in schema rumo_private from public,anon;
grant execute on function rumo_private.push_events(jsonb),rumo_private.pull_events(bigint,integer),rumo_private.study_summary(),rumo_private.progress_summary(),rumo_private.question_catalog(text,text,text,boolean,boolean,text,integer,text,integer) to authenticated;

create function public.push_events(events jsonb) returns jsonb language sql security invoker set search_path=pg_catalog as $$ select rumo_private.push_events(events) $$;
create function public.pull_events(after_sequence bigint default 0,batch_size integer default 200) returns jsonb language sql security invoker set search_path=pg_catalog as $$ select rumo_private.pull_events(after_sequence,batch_size) $$;
create function public.study_summary() returns jsonb language sql security invoker set search_path=pg_catalog as $$ select rumo_private.study_summary() $$;
create function public.progress_summary() returns jsonb language sql security invoker set search_path=pg_catalog as $$ select rumo_private.progress_summary() $$;
create function public.question_catalog(subject text default null,topic text default null,exam text default null,wrong_only boolean default false,favorite_only boolean default false,bank text default null,year integer default null,difficulty text default null,batch_size integer default 200) returns jsonb language sql security invoker set search_path=pg_catalog as $$ select rumo_private.question_catalog(subject,topic,exam,wrong_only,favorite_only,bank,year,difficulty,batch_size) $$;
revoke all on function public.push_events(jsonb),public.pull_events(bigint,integer),public.study_summary(),public.progress_summary(),public.question_catalog(text,text,text,boolean,boolean,text,integer,text,integer) from public,anon;
grant execute on function public.push_events(jsonb),public.pull_events(bigint,integer),public.study_summary(),public.progress_summary(),public.question_catalog(text,text,text,boolean,boolean,text,integer,text,integer) to authenticated;
-- Cache each JWT user once per statement if policies are used from direct SQL.
alter policy own_events on rumo_private.events using(user_id=(select auth.uid()));
alter policy own_entities on rumo_private.entities using(user_id=(select auth.uid()));
alter policy own_results on rumo_private.results using(user_id=(select auth.uid()));
alter policy own_schedule on rumo_private.card_schedule using(user_id=(select auth.uid()));
create index events_arena_latest on rumo_private.events(user_id,(payload->>'question_id'),(payload->>'version'),sequence desc) where kind='arena.attempt';
-- The safe catalog view executes with caller privileges. Column grants never
-- include answer/comment; RLS additionally hides unpublished content.
create policy published_question_catalog on rumo_private.questions for select to authenticated using(status='publicada' or example);
grant select(id,version,prompt,options,annulled,type,subject_id,topic_ids,exam_ids,provenance,example,status,review,catalog_revision) on rumo_private.questions to authenticated;
alter view public.rumo_questions set(security_invoker=true);
notify pgrst,'reload schema';
commit;
