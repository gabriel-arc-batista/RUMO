-- Run as migration owner; auth.users/auth.uid() supplied by Supabase.
begin;
create schema if not exists rumo_private;
revoke all on schema rumo_private from public;
create table public.rumo_lessons (
 id text not null, version text not null check(length(version) between 1 and 64), pages integer not null check(pages>0),
 title text not null, primary key(id,version)
);
create table rumo_private.questions (
 id text not null, version text not null check(length(version) between 1 and 64), prompt text not null,
 options jsonb not null check(jsonb_typeof(options)='object'), answer text not null,
 annulled boolean not null default false, primary key(id,version), check(options ? answer)
);
create view public.rumo_questions with (security_barrier=true) as
 select id,version,prompt,options,annulled from rumo_private.questions;
create table public.rumo_cards (
 id text not null, version text not null check(length(version) between 1 and 64), front text not null, back text not null,
 explanation text not null default '', primary key(id,version)
);
create table rumo_private.events (
 user_id uuid not null references auth.users(id) on delete cascade,
 id uuid not null, device_id uuid not null, kind text not null, entity_id text not null,
 base_revision bigint not null, payload jsonb not null,
 sequence bigint generated always as identity unique,
 revision bigint not null, received_at timestamptz not null default clock_timestamp(),
 primary key(user_id,id)
);
create index events_account_cursor on rumo_private.events(user_id,sequence);
create table rumo_private.entities (
 user_id uuid not null references auth.users(id) on delete cascade,
 kind text not null, entity_id text not null, revision bigint not null,
 payload jsonb not null, primary key(user_id,kind,entity_id)
);
create table rumo_private.results (
 user_id uuid not null references auth.users(id) on delete cascade,
 event_id uuid not null, result jsonb not null,
 primary key(user_id,event_id), foreign key(user_id,event_id) references rumo_private.events(user_id,id)
);
create table rumo_private.card_schedule (
 user_id uuid not null references auth.users(id) on delete cascade,
 card_id text not null, version text not null,
 repetitions integer not null default 0, interval_days integer not null default 0,
 ease numeric not null default 2.5, due_at timestamptz not null,
 reviewed_at timestamptz not null default clock_timestamp(),
 primary key(user_id,card_id,version)
);
-- Catalog versions are append-only, including corrections and annulments.
create function rumo_private.immutable_content() returns trigger language plpgsql as $$
begin raise exception 'immutable_content'; end $$;
create trigger immutable_question before update or delete on rumo_private.questions
 for each row execute function rumo_private.immutable_content();
create trigger immutable_card before update or delete on public.rumo_cards
 for each row execute function rumo_private.immutable_content();
create trigger immutable_lesson before update or delete on public.rumo_lessons
 for each row execute function rumo_private.immutable_content();
alter table public.rumo_lessons enable row level security;
alter table public.rumo_cards enable row level security;
create policy catalog_read on public.rumo_lessons for select to authenticated using(true);
create policy catalog_read on public.rumo_cards for select to authenticated using(true);
alter table rumo_private.questions enable row level security;
alter table rumo_private.events enable row level security;
alter table rumo_private.entities enable row level security;
alter table rumo_private.results enable row level security;
alter table rumo_private.card_schedule enable row level security;
create policy own_events on rumo_private.events for select to authenticated using(user_id=auth.uid());
create policy own_entities on rumo_private.entities for select to authenticated using(user_id=auth.uid());
create policy own_results on rumo_private.results for select to authenticated using(user_id=auth.uid());
create policy own_schedule on rumo_private.card_schedule for select to authenticated using(user_id=auth.uid());
revoke all on all tables in schema rumo_private from public,anon,authenticated;
revoke all on public.rumo_lessons,public.rumo_cards,public.rumo_questions from public,anon,authenticated;
grant select on public.rumo_lessons,public.rumo_cards,public.rumo_questions to authenticated;

create function public.push_events(events jsonb) returns jsonb
language plpgsql security definer set search_path=pg_catalog,rumo_private as $$
declare
 uid uuid:=auth.uid(); e jsonb; p jsonb; eid uuid; did uuid; k text; ent text; base bigint;
 old rumo_private.events%rowtype; rev bigint; seq bigint; accepts jsonb:='[]';
 q rumo_private.questions%rowtype; result jsonb; schedule rumo_private.card_schedule%rowtype;
 rating integer; v text; n integer; ease numeric; days integer; quality integer; card jsonb; lesson_pages integer; allowed_keys text[];
begin
 if uid is null then raise exception 'unauthenticated'; end if;
 if jsonb_typeof(events) is distinct from 'array' or jsonb_array_length(events)>100 then raise exception 'invalid_event'; end if;
 -- Serialize each account; duplicate IDs and CAS remain atomic across devices.
 perform pg_advisory_xact_lock(hashtextextended(uid::text,0));
 for e in select value from jsonb_array_elements(events) loop
  if jsonb_typeof(e) is distinct from 'object' or not(e ?& array['id','device_id','kind','entity_id','base_revision','payload']) then raise exception 'invalid_event'; end if;
  if jsonb_typeof(e->'id') is distinct from 'string' or jsonb_typeof(e->'device_id') is distinct from 'string' or jsonb_typeof(e->'kind') is distinct from 'string' or jsonb_typeof(e->'entity_id') is distinct from 'string' or jsonb_typeof(e->'base_revision') is distinct from 'number' or e->>'base_revision' !~ '^[0-9]+$' then raise exception 'invalid_event'; end if;
  begin
   eid:=(e->>'id')::uuid; did:=(e->>'device_id')::uuid; base:=(e->>'base_revision')::bigint;
  exception when others then raise exception 'invalid_event'; end;
  k:=e->>'kind'; ent:=e->>'entity_id'; p:=e->'payload'; result:=null;
  if eid is null or did is null or base is null or base<0 or ent is null or length(ent) not between 1 and 300 or jsonb_typeof(p) is distinct from 'object' or octet_length(p::text)>65536 then raise exception 'invalid_event'; end if;
  select * into old from rumo_private.events where user_id=uid and id=eid;
  if found then
   if old.device_id is distinct from did or old.kind is distinct from k or old.entity_id is distinct from ent or old.base_revision is distinct from base or old.payload is distinct from p then raise exception 'event_mismatch'; end if;
   accepts:=accepts||jsonb_build_array(jsonb_build_object('id',eid,'sequence',old.sequence)); continue;
  end if;
  select revision into rev from rumo_private.entities where user_id=uid and kind=k and entity_id=ent;
  rev:=coalesce(rev,0);
  if rev<>base then raise exception 'revision_conflict'; end if;
  if k in ('arena.attempt','card.review') and rev<>0 then raise exception 'revision_conflict'; end if;
  -- Require every contract field; SQL NULL must never bypass a guard.
  allowed_keys:=case k
   when 'reading.page' then array['lesson_id','version','page','pages','read']
   when 'reading.position' then array['lesson_id','version','page','pages']
   when 'note.save' then array['lesson_id','version','page','text','deleted']
   when 'favorite.set' then array['target_type','target_id','version','favorite']
   when 'arena.attempt' then array['question_id','version','answer','session_id']
   when 'card.review' then array['card_id','version','rating','session_id']
   when 'card.save' then array['deck_id','front','back','explanation','source','lesson_id','question_id','suspended','deleted']
   when 'study.session' then array['plan_id','subject_id','topic_id','day','category','elapsed','lesson_id','lesson_version']
   else array['unsupported_event'] end;
  if not(p ?& allowed_keys) then raise exception 'invalid_event'; end if;
  if k='note.save' then allowed_keys:=allowed_keys||array['question_id']; end if;
  if p-allowed_keys<>'{}'::jsonb then raise exception 'invalid_event'; end if;
  if exists(select 1 from jsonb_each(p) where jsonb_typeof(value)='string' and length(value#>>'{}')>20000) then raise exception 'invalid_event'; end if;
  if exists(select 1 from jsonb_each(p) where value='null'::jsonb and key not in ('lesson_id','lesson_version','question_id','topic_id') and not(k='note.save' and key='page')) then raise exception 'invalid_event'; end if;
  if k in ('reading.page','reading.position') and (p->>'lesson_id' is null or p->>'version' is null) then raise exception 'invalid_event'; end if;
  if p ? 'version' and jsonb_typeof(p->'version') is distinct from 'string' then raise exception 'invalid_event'; end if;
  if p ? 'version' and (k<>'favorite.set' or p->>'version'<>'') and (p->>'version' is null or p->>'version' !~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$') then raise exception 'invalid_event'; end if;
  if k='card.review' and (jsonb_typeof(p->'rating') is distinct from 'number' or p->>'rating' !~ '^[1-4]$') then raise exception 'invalid_event'; end if;
  begin
  if k in ('reading.page','reading.position') then
   v:=p->>'version';
   select pages into lesson_pages from public.rumo_lessons where id=p->>'lesson_id' and version=v and (coalesce(to_jsonb(rumo_lessons)->>'status','')='publicada' or coalesce((to_jsonb(rumo_lessons)->>'example')::boolean,false));
   if not found then raise exception 'content_unavailable'; end if;
   if (jsonb_typeof(p->'page') is distinct from 'number' or (p->>'page') !~ '^[0-9]+$' or (p->>'page')::integer not between 1 and lesson_pages) then raise exception 'invalid_event'; end if;
   if (jsonb_typeof(p->'pages') is distinct from 'number' or p->>'pages' !~ '^[1-9][0-9]*$' or (p->>'pages')::integer is distinct from lesson_pages) then raise exception 'invalid_event'; end if;
   if k='reading.page' then
    if jsonb_typeof(p->'read') is distinct from 'boolean' or ent<>concat(p->>'lesson_id',':',v,':page:',p->>'page') then raise exception 'invalid_event'; end if;
   elsif k='reading.position' then
    if ent<>concat(p->>'lesson_id',':',v,':position') then raise exception 'invalid_event'; end if;
   end if;
  elsif k='note.save' then
   perform ent::uuid;
   if (p->>'lesson_id' is null)=(p->>'question_id' is null) then raise exception 'invalid_event'; end if;
   if p->>'question_id' is not null then
    if jsonb_typeof(p->'question_id') is distinct from 'string' or p->'page'<>'null'::jsonb then raise exception 'invalid_event'; end if;
    if not exists(select 1 from rumo_private.questions qn where qn.id=p->>'question_id' and qn.version=p->>'version' and (coalesce(to_jsonb(qn)->>'status','')='publicada' or coalesce((to_jsonb(qn)->>'example')::boolean,false))) then raise exception 'content_unavailable'; end if;
   else
    select pages into lesson_pages from public.rumo_lessons where id=p->>'lesson_id' and version=p->>'version' and (coalesce(to_jsonb(rumo_lessons)->>'status','')='publicada' or coalesce((to_jsonb(rumo_lessons)->>'example')::boolean,false));
    if not found then raise exception 'content_unavailable'; end if;
    if p->'page'<>'null'::jsonb and (jsonb_typeof(p->'page') is distinct from 'number' or (p->>'page') !~ '^[0-9]+$' or (p->>'page')::integer not between 1 and lesson_pages) then raise exception 'invalid_event'; end if;
   end if;
   if jsonb_typeof(p->'text') is distinct from 'string' or length(p->>'text')>20000 or jsonb_typeof(p->'deleted') is distinct from 'boolean' then raise exception 'invalid_event'; end if;
  elsif k='favorite.set' then
   if jsonb_typeof(p->'target_id') is distinct from 'string' or ent<>concat(p->>'target_type',':',p->>'target_id',':',p->>'version',':favorite') then raise exception 'invalid_event'; end if;
   if jsonb_typeof(p->'favorite') is distinct from 'boolean' or length(p->>'target_id') not between 1 and 300 or p->>'target_type' not in ('lesson','question','card','deck','bookmark') or length(p->>'version')>64 then raise exception 'invalid_event'; end if;
  elsif k='arena.attempt' then
   perform ent::uuid;
   if jsonb_typeof(p->'session_id') not in ('string','number') or length(p->>'session_id') not between 1 and 300 then raise exception 'invalid_event'; end if;
   select * into q from rumo_private.questions where id=p->>'question_id' and version=p->>'version' and (coalesce(to_jsonb(questions)->>'status','')='publicada' or coalesce((to_jsonb(questions)->>'example')::boolean,false));
   if not found then raise exception 'content_unavailable'; end if;
   if jsonb_typeof(p->'answer') is distinct from 'string' or not(q.options ? (p->>'answer')) then raise exception 'invalid_answer'; end if;
   result:=jsonb_build_object('status',case when q.annulled then 'annulled' when q.answer=p->>'answer' then 'correct' else 'incorrect' end,'answer',q.answer,'comment',coalesce(to_jsonb(q)->>'comment',''));
  elsif k='card.save' then
   perform ent::uuid;
   if not(p ?& array['deck_id','front','back','explanation','source','lesson_id','question_id','suspended','deleted']) or jsonb_typeof(p->'suspended') is distinct from 'boolean' or jsonb_typeof(p->'deleted') is distinct from 'boolean' then raise exception 'invalid_event'; end if;
   for card in select value from jsonb_each(p) where key in ('deck_id','front','back','explanation','source') loop
    if jsonb_typeof(card) is distinct from 'string' or length(card#>>'{}')>20000 then raise exception 'invalid_event'; end if;
   end loop;
   if length(p->>'front')=0 or length(p->>'back')=0 then raise exception 'invalid_event'; end if;
  elsif k='card.review' then
   perform ent::uuid;
   if jsonb_typeof(p->'session_id') not in ('string','number') or length(p->>'session_id') not between 1 and 300 then raise exception 'invalid_event'; end if;
   v:=p->>'version'; rating:=(p->>'rating')::integer;
   if rating not between 1 and 4 or length(v) not between 1 and 64 then raise exception 'invalid_event'; end if;
   select payload into card from rumo_private.entities where user_id=uid and kind='card.save' and entity_id=p->>'card_id' and revision::text=v;
   if found then
    if (card->>'suspended')::boolean or (card->>'deleted')::boolean then raise exception 'card_suspended'; end if;
   elsif not exists(select 1 from public.rumo_cards where id=p->>'card_id' and version=v and (coalesce(to_jsonb(rumo_cards)->>'status','')='publicada' or coalesce((to_jsonb(rumo_cards)->>'example')::boolean,false))) then raise exception 'content_unavailable'; end if;
   select * into schedule from rumo_private.card_schedule where user_id=uid and card_id=p->>'card_id' and version=v;
   if not found then select * into schedule from rumo_private.card_schedule where user_id=uid and card_id=p->>'card_id' order by reviewed_at desc limit 1; end if;
   n:=coalesce(schedule.repetitions,0); ease:=coalesce(schedule.ease,2.5);
   quality:=case rating when 1 then 1 when 2 then 3 when 3 then 4 else 5 end;
   if rating=1 then n:=0; days:=1;
   else n:=n+1; days:=case when n=1 then 1 when n=2 then 6 else greatest(1,floor(schedule.interval_days*ease+0.5)::integer) end; end if;
   ease:=round(greatest(1.3,ease+0.1-(5-quality)*(0.08+(5-quality)*0.02)),4);
   insert into rumo_private.card_schedule(user_id,card_id,version,repetitions,interval_days,ease,due_at) values(uid,p->>'card_id',v,n,days,ease,clock_timestamp()+make_interval(days=>days))
   on conflict(user_id,card_id,version) do update set repetitions=excluded.repetitions,interval_days=excluded.interval_days,ease=excluded.ease,due_at=excluded.due_at,reviewed_at=clock_timestamp();
   result:=jsonb_build_object('interval_days',days,'repetitions',n,'ease',ease,'due_at',(select due_at from rumo_private.card_schedule where user_id=uid and card_id=p->>'card_id' and version=v));
  elsif k='study.session' then
   if jsonb_typeof(p->'plan_id') not in ('string','number') or length(p->>'plan_id') not between 1 and 300 or jsonb_typeof(p->'subject_id') not in ('string','number') or length(p->>'subject_id') not between 1 and 300 or (p->'topic_id'<>'null'::jsonb and jsonb_typeof(p->'topic_id') not in ('string','number')) then raise exception 'invalid_event'; end if;
   if not(p ?& array['plan_id','subject_id','topic_id','day','category','elapsed','lesson_id','lesson_version']) or jsonb_typeof(p->'elapsed') is distinct from 'number' or (p->>'elapsed') !~ '^[0-9]+$' or (p->>'elapsed')::integer not between 0 and 86400 then raise exception 'invalid_event'; end if;
   if jsonb_typeof(p->'day') is distinct from 'string' or p->>'day' !~ '^\d{4}-\d{2}-\d{2}$' or jsonb_typeof(p->'category') is distinct from 'string' or p->>'category' not in ('Teoria','Questões','Revisão','Simulado') then raise exception 'invalid_event'; end if;
   perform (p->>'day')::date;
   if (p->>'lesson_id' is null)<>(p->>'lesson_version' is null) then raise exception 'invalid_event'; end if;
   if p->>'lesson_id' is not null and not exists(select 1 from public.rumo_lessons where id=p->>'lesson_id' and version=p->>'lesson_version' and (coalesce(to_jsonb(rumo_lessons)->>'status','')='publicada' or coalesce((to_jsonb(rumo_lessons)->>'example')::boolean,false))) then raise exception 'content_unavailable'; end if;
   result:=jsonb_build_object('xp',(p->>'elapsed')::integer/60,'coins',(p->>'elapsed')::integer/600);
  else raise exception 'invalid_event'; end if;
  exception when invalid_text_representation or numeric_value_out_of_range or datetime_field_overflow or invalid_datetime_format then raise exception 'invalid_event'; end;
  insert into rumo_private.events(user_id,id,device_id,kind,entity_id,base_revision,payload,revision)
   values(uid,eid,did,k,ent,base,p,rev+1) returning sequence into seq;
  insert into rumo_private.entities values(uid,k,ent,rev+1,p)
   on conflict(user_id,kind,entity_id) do update set revision=excluded.revision,payload=excluded.payload;
  if result is not null then insert into rumo_private.results values(uid,eid,result); end if;
  accepts:=accepts||jsonb_build_array(jsonb_build_object('id',eid,'sequence',seq));
 end loop;
 return accepts;
end $$;

create function public.pull_events(after_sequence bigint default 0,batch_size integer default 200)
returns jsonb language plpgsql security definer set search_path=pg_catalog,rumo_private as $$
begin
 if auth.uid() is null then raise exception 'unauthenticated'; end if;
 if after_sequence is null or after_sequence<0 or batch_size is null or batch_size not between 1 and 200 then raise exception 'invalid_event'; end if;
 return coalesce((select jsonb_agg(to_jsonb(t) order by t.sequence) from (
  select e.id,e.device_id,e.kind,e.entity_id,e.base_revision,e.payload,e.sequence,e.revision,e.received_at,r.result
  from rumo_private.events e left join rumo_private.results r on r.user_id=e.user_id and r.event_id=e.id
  where e.user_id=auth.uid() and e.sequence>after_sequence order by e.sequence limit batch_size
 )t),'[]'::jsonb);
end $$;
revoke all on function public.push_events(jsonb),public.pull_events(bigint,integer) from public,anon;
grant execute on function public.push_events(jsonb),public.pull_events(bigint,integer) to authenticated;
revoke all on function rumo_private.immutable_content() from public;
commit;
