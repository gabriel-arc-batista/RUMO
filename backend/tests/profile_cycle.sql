\set ON_ERROR_STOP on
-- Migração 009: perfil, ciclo e vitórias. Usuários sintéticos próprios.
reset role;
insert into auth.users values('00000000-0000-0000-0000-000000000009'),('00000000-0000-0000-0000-000000000010');
set role authenticated;
select set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000009',false);
do $$
declare profile jsonb; cycle jsonb; summary jsonb; n integer;
begin
 profile:='[{"id":"90000000-0000-0000-0000-000000000001","device_id":"20000000-0000-0000-0000-000000000009","kind":"profile.character","entity_id":"profile:character","base_revision":0,"payload":{"name":"Viajante","look":{"face":"rosto-1","skin":"morena-clara","hair":"curto"},"equipped":["rusty_sword","travel_tunic"]}}]';
 if public.push_events(profile)<>public.push_events(profile) then raise exception 'profile retry not idempotent'; end if;
 begin perform public.push_events(jsonb_set(profile,'{0,payload,name}','"Outro"')); raise exception 'profile mismatch accepted'; exception when raise_exception then if sqlerrm<>'event_mismatch' then raise; end if; end;
 begin perform public.push_events(jsonb_set(profile,'{0,id}','"90000000-0000-0000-0000-000000000002"')); raise exception 'stale profile accepted'; exception when raise_exception then if sqlerrm<>'revision_conflict' then raise; end if; end;
 -- Campos extras, valores livres e entidade errada são recusados.
 begin perform public.push_events(jsonb_set(jsonb_set(profile,'{0,id}','"90000000-0000-0000-0000-000000000003"'),'{0,payload,email}','"x@y"')); raise exception 'extra field accepted'; exception when raise_exception then if sqlerrm<>'invalid_event' then raise; end if; end;
 begin perform public.push_events(jsonb_set(jsonb_set(profile,'{0,id}','"90000000-0000-0000-0000-000000000004"'),'{0,payload,look,hair}','"<script>"')); raise exception 'unsafe look accepted'; exception when raise_exception then if sqlerrm<>'invalid_event' then raise; end if; end;
 begin perform public.push_events(jsonb_set(jsonb_set(profile,'{0,id}','"90000000-0000-0000-0000-000000000005"'),'{0,entity_id}','"profile:other"')); raise exception 'wrong entity accepted'; exception when raise_exception then if sqlerrm<>'invalid_event' then raise; end if; end;

 cycle:='[{"id":"90000000-0000-0000-0000-000000000010","device_id":"20000000-0000-0000-0000-000000000009","kind":"cycle.snapshot","entity_id":"cycle:current","base_revision":0,"payload":{"plan_name":"BACEN 2024","position":1,"items":[{"subject":"Bancos de dados","topic":"Normalização","category":"Teoria","target_minutes":45,"done":true},{"subject":"Estatística","topic":null,"category":"Questões","target_minutes":30,"done":false}]}}]';
 perform public.push_events(cycle);
 begin perform public.push_events(jsonb_set(jsonb_set(cycle,'{0,id}','"90000000-0000-0000-0000-000000000011"'),'{0,base_revision}','1') #- '{0,payload,items,0,done}'); raise exception 'incomplete item accepted'; exception when raise_exception then if sqlerrm<>'invalid_event' then raise; end if; end;
 begin perform public.push_events(jsonb_set(jsonb_set(cycle,'{0,id}','"90000000-0000-0000-0000-000000000012"'),'{0,payload,position}','9')); raise exception 'position out of range accepted'; exception when raise_exception then if sqlerrm<>'invalid_event' then raise; end if; end;

 -- Lote misto: um tipo antigo inválido desfaz também o perfil válido do mesmo lote.
 begin
  perform public.push_events(jsonb_set(jsonb_set(profile,'{0,id}','"90000000-0000-0000-0000-000000000020"'),'{0,base_revision}','1')||'[{"id":"bad"}]'::jsonb);
  raise exception 'mixed batch accepted';
 exception when raise_exception then if sqlerrm<>'invalid_event' then raise; end if; end;
 select count(*) into n from jsonb_array_elements(public.pull_events()) x where x->>'id'='90000000-0000-0000-0000-000000000020';
 if n<>0 then raise exception 'mixed batch not atomic'; end if;

 -- Vitórias: acerto repetido na mesma questão conta uma vez; erro e anulada não contam.
 perform public.push_events('[
  {"id":"90000000-0000-0000-0000-000000000030","device_id":"20000000-0000-0000-0000-000000000009","kind":"arena.attempt","entity_id":"91000000-0000-0000-0000-000000000001","base_revision":0,"payload":{"question_id":"example","version":"1","answer":"a","session_id":"92000000-0000-0000-0000-000000000001"}},
  {"id":"90000000-0000-0000-0000-000000000031","device_id":"20000000-0000-0000-0000-000000000009","kind":"arena.attempt","entity_id":"91000000-0000-0000-0000-000000000002","base_revision":0,"payload":{"question_id":"example","version":"1","answer":"a","session_id":"92000000-0000-0000-0000-000000000001"}},
  {"id":"90000000-0000-0000-0000-000000000032","device_id":"20000000-0000-0000-0000-000000000009","kind":"arena.attempt","entity_id":"91000000-0000-0000-0000-000000000003","base_revision":0,"payload":{"question_id":"example","version":"1","answer":"b","session_id":"92000000-0000-0000-0000-000000000001"}},
  {"id":"90000000-0000-0000-0000-000000000033","device_id":"20000000-0000-0000-0000-000000000009","kind":"arena.attempt","entity_id":"91000000-0000-0000-0000-000000000004","base_revision":0,"payload":{"question_id":"annulled","version":"1","answer":"a","session_id":"92000000-0000-0000-0000-000000000001"}}]');
 summary:=public.progress_summary();
 if (summary->>'victories')::integer<>1 then raise exception 'victories wrong: %',summary; end if;
 if summary->'look'->>'hair'<>'curto' or summary->>'name'<>'Viajante' or jsonb_array_length(summary->'equipped')<>2 then raise exception 'profile missing: %',summary; end if;
 if (summary->>'xp')::integer<>0 then raise exception 'victories changed XP: %',summary; end if;
 if (select count(*) from jsonb_array_elements(public.pull_events()) x where x->>'kind' in ('profile.character','cycle.snapshot'))<>2 then raise exception 'pull missing profile/cycle'; end if;
end $$;
-- Outra conta não vê perfil, ciclo nem vitórias alheias.
select set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000010',false);
do $$
declare summary jsonb:=public.progress_summary();
begin
 if (summary->>'victories')::integer<>0 or summary->'look'<>'null'::jsonb or jsonb_array_length(public.pull_events())<>0 then raise exception 'isolation broken: %',summary; end if;
end $$;
reset role;
select 'profile/cycle/victories checks passed';
