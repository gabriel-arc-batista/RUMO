begin;
create function public.study_summary() returns jsonb
language plpgsql security definer set search_path=pg_catalog,rumo_private as $$
declare uid uuid:=auth.uid(); summary jsonb;
begin
 if uid is null then raise exception 'unauthenticated'; end if;
 select jsonb_build_object('elapsed',coalesce(sum((payload->>'elapsed')::int),0),
 'xp',coalesce(sum((payload->>'elapsed')::int/60),0),
 'coins',coalesce(sum((payload->>'elapsed')::int/600),0)) into summary
 from rumo_private.entities where user_id=uid and kind='study.session';
 return summary||jsonb_build_object('attempts',(
  select count(*) from rumo_private.events e
  where e.user_id=uid and e.kind='arena.attempt' and exists(
   select 1 from rumo_private.entities s where s.user_id=uid and s.kind='study.session'
   and s.entity_id=e.payload->>'session_id')),
 'correct',(
  select count(*) from rumo_private.events e join rumo_private.results r using(user_id)
  where e.user_id=uid and e.kind='arena.attempt' and r.event_id=e.id and r.result->>'status'='correct'
  and exists(select 1 from rumo_private.entities s where s.user_id=uid and s.kind='study.session' and s.entity_id=e.payload->>'session_id')));
end $$;
revoke all on function public.study_summary() from public,anon;
grant execute on function public.study_summary() to authenticated;
commit;
