-- Perfil do personagem e retrato do ciclo (desktop → site) e vitórias na Arena.
-- Não reescreve a implementação aplicada: o adaptador valida os dois tipos novos
-- e repassa os demais, um a um, à função existente na MESMA transação (lote
-- continua atômico e na ordem enviada; idempotência/CAS iguais aos demais tipos).
begin;
alter function rumo_private.push_events(jsonb) rename to push_events_core;
revoke all on function rumo_private.push_events_core(jsonb) from public,anon,authenticated;

create function rumo_private.push_events(events jsonb) returns jsonb
language plpgsql security definer set search_path=pg_catalog as $$
declare
 uid uuid:=auth.uid(); e jsonb; p jsonb; k text; ent text; eid uuid; did uuid; base bigint;
 old rumo_private.events%rowtype; rev bigint; seq bigint; accepts jsonb:='[]'; item jsonb;
begin
 if uid is null then raise exception 'unauthenticated'; end if;
 if jsonb_typeof(events) is distinct from 'array' or jsonb_array_length(events)>100 then raise exception 'invalid_event'; end if;
 perform pg_advisory_xact_lock(hashtextextended(uid::text,0));
 for e in select value from jsonb_array_elements(events) loop
  k:=e->>'kind';
  if k is null or k not in ('profile.character','cycle.snapshot') then
   accepts:=accepts||rumo_private.push_events_core(jsonb_build_array(e));
   continue;
  end if;
  if jsonb_typeof(e) is distinct from 'object' or not(e ?& array['id','device_id','kind','entity_id','base_revision','payload']) then raise exception 'invalid_event'; end if;
  begin
   eid:=(e->>'id')::uuid; did:=(e->>'device_id')::uuid; base:=(e->>'base_revision')::bigint;
  exception when others then raise exception 'invalid_event'; end;
  ent:=e->>'entity_id'; p:=e->'payload';
  if base<0 or jsonb_typeof(p) is distinct from 'object' or octet_length(p::text)>16384 then raise exception 'invalid_event'; end if;
  select * into old from rumo_private.events where user_id=uid and id=eid;
  if found then
   if old.device_id<>did or old.kind<>k or old.entity_id<>ent or old.base_revision<>base or old.payload<>p then raise exception 'event_mismatch'; end if;
   accepts:=accepts||jsonb_build_array(jsonb_build_object('id',eid,'sequence',old.sequence)); continue;
  end if;
  if k='profile.character' then
   -- Só aparência/nome/equipados: identificadores curtos, sem texto livre além do nome.
   if ent<>'profile:character' or not(p ?& array['name','look','equipped'])
    or exists(select 1 from jsonb_object_keys(p) x where x not in ('name','look','equipped'))
    or jsonb_typeof(p->'name') is distinct from 'string' or length(btrim(p->>'name')) not between 1 and 60
    or jsonb_typeof(p->'look') is distinct from 'object' or jsonb_typeof(p->'equipped') is distinct from 'array'
    or (select count(*) from jsonb_object_keys(p->'look'))>20 or jsonb_array_length(p->'equipped')>20
    or exists(select 1 from jsonb_each(p->'look') l where l.key !~ '^[a-z_]{1,24}$' or jsonb_typeof(l.value) is distinct from 'string' or l.value#>>'{}' !~ '^[a-z0-9-]{1,40}$')
    or exists(select 1 from jsonb_array_elements(p->'equipped') q where jsonb_typeof(q) is distinct from 'string' or q#>>'{}' !~ '^[a-z0-9_]{1,48}$')
   then raise exception 'invalid_event'; end if;
  else
   -- Retrato do ciclo atual do desktop: contexto de leitura no site, nunca editável lá.
   if ent<>'cycle:current' or not(p ?& array['plan_name','position','items'])
    or exists(select 1 from jsonb_object_keys(p) x where x not in ('plan_name','position','items'))
    or jsonb_typeof(p->'plan_name') is distinct from 'string' or length(p->>'plan_name')>120
    or jsonb_typeof(p->'items') is distinct from 'array' or jsonb_array_length(p->'items')>80
    or jsonb_typeof(p->'position') is distinct from 'number' or (p->>'position') !~ '^[0-9]+$' or (p->>'position')::integer>jsonb_array_length(p->'items')
   then raise exception 'invalid_event'; end if;
   for item in select value from jsonb_array_elements(p->'items') loop
    if jsonb_typeof(item) is distinct from 'object'
     or exists(select 1 from jsonb_object_keys(item) x where x not in ('subject','topic','category','target_minutes','done'))
     or not(item ?& array['subject','topic','category','target_minutes','done'])
     or jsonb_typeof(item->'subject') is distinct from 'string' or length(item->>'subject') not between 1 and 120
     or (item->'topic'<>'null'::jsonb and (jsonb_typeof(item->'topic') is distinct from 'string' or length(item->>'topic')>200))
     or item->>'category' not in ('Teoria','Questões','Revisão','Simulado')
     or jsonb_typeof(item->'target_minutes') is distinct from 'number' or (item->>'target_minutes') !~ '^[0-9]+$' or (item->>'target_minutes')::integer not between 1 and 600
     or jsonb_typeof(item->'done') is distinct from 'boolean'
    then raise exception 'invalid_event'; end if;
   end loop;
  end if;
  select revision into rev from rumo_private.entities where user_id=uid and kind=k and entity_id=ent;
  rev:=coalesce(rev,0);
  if rev<>base then raise exception 'revision_conflict'; end if;
  insert into rumo_private.events(user_id,id,device_id,kind,entity_id,base_revision,payload,revision)
   values(uid,eid,did,k,ent,base,p,rev+1) returning sequence into seq;
  insert into rumo_private.entities values(uid,k,ent,rev+1,p)
   on conflict(user_id,kind,entity_id) do update set revision=excluded.revision,payload=excluded.payload;
  accepts:=accepts||jsonb_build_array(jsonb_build_object('id',eid,'sequence',seq));
 end loop;
 return accepts;
end $$;
revoke all on function rumo_private.push_events(jsonb) from public,anon;
grant execute on function rumo_private.push_events(jsonb) to authenticated;

-- Vitórias: questões (id+versão) distintas com ao menos um acerto confirmado.
-- Repetir uma questão vencida não soma; anuladas não contam. Não altera XP/moedas.
create or replace function rumo_private.progress_summary() returns jsonb
language plpgsql security definer set search_path=pg_catalog as $$
declare uid uuid:=auth.uid(); totals jsonb; xp bigint; lvl bigint; floor_xp bigint; profile jsonb; victories bigint;
begin
 if uid is null then raise exception 'unauthenticated'; end if;
 totals:=rumo_private.study_summary(); xp:=(totals->>'xp')::bigint;
 lvl:=greatest(1,floor((1+sqrt(1+8*(xp/100)::numeric))/2)::bigint);
 while 50*lvl*(lvl+1)<=xp loop lvl:=lvl+1; end loop;
 floor_xp:=50*(lvl-1)*lvl;
 select payload into profile from rumo_private.entities where user_id=uid and kind='profile.character' and entity_id='profile:character';
 select count(distinct (e.payload->>'question_id',e.payload->>'version')) into victories
  from rumo_private.events e join rumo_private.results r on r.user_id=e.user_id and r.event_id=e.id
  where e.user_id=uid and e.kind='arena.attempt' and r.result->>'status'='correct';
 return jsonb_build_object('level',lvl,'xp',xp-floor_xp,'xp_next',100*lvl,'coins',totals->'coins',
  'look',profile->'look','name',profile->'name','equipped',coalesce(profile->'equipped','[]'::jsonb),'victories',victories);
end $$;
revoke all on function rumo_private.progress_summary() from public,anon;
grant execute on function rumo_private.progress_summary() to authenticated;
notify pgrst,'reload schema';
commit;
