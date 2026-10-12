\set ON_ERROR_STOP on
insert into auth.users values('00000000-0000-0000-0000-000000000001'),('00000000-0000-0000-0000-000000000002');
insert into public.rumo_lessons(id,version,pages,title,example) values('example','1',2,'EXEMPLO DE TESTE',true),('semver','1.0.0',2,'EXEMPLO SEMVER',true);
insert into rumo_private.questions(id,version,prompt,options,answer,annulled,subject_id,topic_ids,exam_ids,provenance,comment,example) values('example','1','EXEMPLO DE TESTE','{"a":"A","b":"B"}','a',false,'test-subject',array['test-topic'],array['test-exam'],'{"example":true,"bank":"EXEMPLO","year":2026,"difficulty":"example"}','Comentário somente após confirmar',true);
insert into public.rumo_cards(id,version,front,back,explanation,example) values('example','1','EXEMPLO','TESTE','',true),('example','2','EXEMPLO NOVA VERSÃO','TESTE','',true);
insert into public.rumo_lessons(id,version,pages,title) values('planned-hidden','1',1,'PLANEJADA');
insert into rumo_private.questions(id,version,prompt,options,answer) values('draft-hidden','1','RASCUNHO','{"a":"A"}','a');
insert into public.rumo_cards(id,version,front,back) values('draft-hidden','1','RASCUNHO','RASCUNHO');
insert into rumo_private.questions(id,version,prompt,options,answer,annulled,example) values('annulled','1','EXEMPLO ANULADO','{"a":"A"}','a',true,true);
set role authenticated;
select set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',false);
do $$
declare e jsonb; receipt jsonb; pulled jsonb;
begin
 e:='[{"id":"10000000-0000-0000-0000-000000000001","device_id":"20000000-0000-0000-0000-000000000001","kind":"reading.page","entity_id":"example:1:page:1","base_revision":0,"payload":{"lesson_id":"example","version":"1","page":1,"pages":2,"read":true}}]';
 receipt:=public.push_events(e);
 if receipt<>public.push_events(e) then raise exception 'retry not idempotent'; end if;
 begin perform public.push_events(jsonb_set(e,'{0,payload,read}','false')); raise exception 'mismatch accepted'; exception when raise_exception then if sqlerrm<>'event_mismatch' then raise; end if; end;
 begin perform public.push_events(jsonb_set(e,'{0,id}','"10000000-0000-0000-0000-000000000002"')); raise exception 'stale accepted'; exception when raise_exception then if sqlerrm<>'revision_conflict' then raise; end if; end;
 e:=jsonb_set(e,'{0,id}','"10000000-0000-0000-0000-000000000003"');
 e:=jsonb_set(e,'{0,base_revision}','1');
 e:=jsonb_set(e,'{0,payload,read}','false');
 perform public.push_events(e);
 -- Whole-batch rollback: first valid event must disappear after second invalid.
 e:=jsonb_set(e,'{0,id}','"10000000-0000-0000-0000-000000000004"');
 e:=jsonb_set(e,'{0,base_revision}','2');
 begin perform public.push_events(e||jsonb_build_array('{"id":"bad"}'::jsonb)); raise exception 'invalid accepted'; exception when raise_exception then if sqlerrm<>'invalid_event' then raise; end if; end;
 if jsonb_array_length(public.pull_events())<>2 then raise exception 'batch not atomic'; end if;
 perform public.push_events('[{"id":"10000000-0000-0000-0000-000000000005","device_id":"20000000-0000-0000-0000-000000000001","kind":"arena.attempt","entity_id":"30000000-0000-0000-0000-000000000001","base_revision":0,"payload":{"question_id":"example","version":"1","answer":"b","session_id":"40000000-0000-0000-0000-000000000001"}},{"id":"10000000-0000-0000-0000-000000000006","device_id":"20000000-0000-0000-0000-000000000001","kind":"study.session","entity_id":"40000000-0000-0000-0000-000000000001","base_revision":0,"payload":{"plan_id":1,"subject_id":1,"topic_id":null,"day":"2026-10-12","category":"Teoria","elapsed":659,"lesson_id":null,"lesson_version":null}},{"id":"10000000-0000-0000-0000-000000000007","device_id":"20000000-0000-0000-0000-000000000001","kind":"card.review","entity_id":"50000000-0000-0000-0000-000000000001","base_revision":0,"payload":{"card_id":"example","version":"1","rating":3,"session_id":"40000000-0000-0000-0000-000000000001"}}]');
 pulled:=public.pull_events();
 if pulled->2->'result'->>'status'<>'incorrect' or (pulled->3->'result'->>'xp')::int<>10 or (pulled->3->'result'->>'coins')::int<>1 or (pulled->4->'result'->>'interval_days')::int<>1 then raise exception 'server projections incorrect'; end if;
 if (select options ? 'a' from public.rumo_questions where id='example') is not true then raise exception 'catalog unavailable'; end if;
 begin perform answer from rumo_private.questions; raise exception 'answer leaked'; exception when insufficient_privilege then null; end;
 begin perform * from rumo_private.events; raise exception 'events direct access'; exception when insufficient_privilege then null; end;
 perform set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',false);
 if public.pull_events()<>'[]'::jsonb then raise exception 'cross-account leakage'; end if;
 perform set_config('request.jwt.claim.sub','',false);
 begin perform public.pull_events(); raise exception 'anonymous accepted'; exception when raise_exception then if sqlerrm<>'unauthenticated' then raise; end if; end;
end $$;
do $$
declare e jsonb; p jsonb; r jsonb;
begin
 perform set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',false);
 r:=public.study_summary();
 if r->>'attempts'<>'1' or r->>'correct'<>'0' or r->>'xp'<>'10' then raise exception 'summary invalid'; end if;
 e:='[{"id":"10000000-0000-0000-0000-000000000008","device_id":"20000000-0000-0000-0000-000000000001","kind":"study.session","entity_id":"40000000-0000-0000-0000-000000000001","base_revision":1,"payload":{"plan_id":1,"subject_id":1,"topic_id":null,"day":"2026-10-12","category":"Teoria","elapsed":59,"lesson_id":null,"lesson_version":null}}]';
 perform public.push_events(e);
 if public.study_summary()->>'xp'<>'0' then raise exception 'correction inflated XP'; end if;
 e:=jsonb_set(e,'{0,id}','"10000000-0000-0000-0000-000000000009"');
 e:=jsonb_set(e,'{0,base_revision}','2');
 begin perform public.push_events(jsonb_set(e,'{0,payload,elapsed}','null')); raise exception 'null accepted'; exception when raise_exception then if sqlerrm<>'invalid_event' then raise; end if; end;
 begin perform public.push_events(jsonb_set(e,'{0,payload,elapsed}','86401')); raise exception 'oversized session accepted'; exception when raise_exception then if sqlerrm<>'invalid_event' then raise; end if; end;
 begin perform public.push_events(e #- '{0,payload,elapsed}'); raise exception 'missing accepted'; exception when raise_exception then if sqlerrm<>'invalid_event' then raise; end if; end;
 perform public.push_events('[{"id":"10000000-0000-0000-0000-000000000010","device_id":"20000000-0000-0000-0000-000000000001","kind":"card.review","entity_id":"50000000-0000-0000-0000-000000000002","base_revision":0,"payload":{"card_id":"example","version":"2","rating":3,"session_id":"40000000-0000-0000-0000-000000000001"}}]');
 p:=public.pull_events();
 if p->(jsonb_array_length(p)-1)->'result'->>'interval_days'<>'6' then raise exception 'new version reset reviews'; end if;
 perform public.push_events('[{"id":"10000000-0000-0000-0000-000000000011","device_id":"20000000-0000-0000-0000-000000000001","kind":"arena.attempt","entity_id":"30000000-0000-0000-0000-000000000002","base_revision":0,"payload":{"question_id":"annulled","version":"1","answer":"a","session_id":"40000000-0000-0000-0000-000000000001"}}]');
 p:=public.pull_events();
 if p->(jsonb_array_length(p)-1)->'result'->>'status'<>'annulled' then raise exception 'annulled graded'; end if;
 if public.study_summary()->>'correct'<>'0' then raise exception 'annulled counted correct'; end if;
 if jsonb_array_length(public.question_catalog(wrong_only=>true))<>1 then raise exception 'wrong filter invalid'; end if;
 if jsonb_array_length(public.question_catalog(subject=>'test-subject',topic=>'test-topic',exam=>'test-exam',bank=>'EXEMPLO',year=>2026,difficulty=>'example'))<>1 then raise exception 'metadata filter invalid'; end if;
 if jsonb_array_length(public.question_catalog(bank=>'nonexistent'))<>0 then raise exception 'missing metadata invented'; end if;
 if public.question_catalog()->0 ? 'answer' or public.question_catalog()->0 ? 'comment' then raise exception 'pre-confirmation leak'; end if;
 if public.pull_events()->2->'result'->>'comment'<>'Comentário somente após confirmar' then raise exception 'confirmed comment missing'; end if;
 if public.pull_events()->2->'result'->>'answer'<>'a' then raise exception 'confirmed answer missing'; end if;
 if public.progress_summary()->>'look' is not null or public.progress_summary()->>'level'<>'1' then raise exception 'progress invalid'; end if;

 perform public.push_events('[{"id":"10000000-0000-0000-0000-000000000012","device_id":"20000000-0000-0000-0000-000000000001","kind":"reading.page","entity_id":"semver:1.0.0:page:1","base_revision":0,"payload":{"lesson_id":"semver","version":"1.0.0","page":1,"pages":2,"read":true}},{"id":"10000000-0000-0000-0000-000000000013","device_id":"20000000-0000-0000-0000-000000000001","kind":"favorite.set","entity_id":"lesson:example::favorite","base_revision":0,"payload":{"target_type":"lesson","target_id":"example","version":"","favorite":true}}]');
 perform set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',false);
 perform public.push_events('[{"id":"10000000-0000-0000-0000-000000000012","device_id":"20000000-0000-0000-0000-000000000001","kind":"reading.page","entity_id":"semver:1.0.0:page:1","base_revision":0,"payload":{"lesson_id":"semver","version":"1.0.0","page":1,"pages":2,"read":false}}]');
 if jsonb_array_length(public.pull_events())<>1 then raise exception 'account isolation failed'; end if;
 perform public.push_events('[{"id":"10000000-0000-0000-0000-000000000018","device_id":"20000000-0000-0000-0000-000000000001","kind":"note.save","entity_id":"70000000-0000-0000-0000-000000000002","base_revision":0,"payload":{"lesson_id":null,"question_id":"example","version":"1","page":null,"text":"Nota sobre a questão","deleted":false}}]');
 begin
  perform public.push_events('[{"id":"10000000-0000-0000-0000-000000000019","device_id":"20000000-0000-0000-0000-000000000001","kind":"note.save","entity_id":"70000000-0000-0000-0000-000000000003","base_revision":0,"payload":{"lesson_id":"example","question_id":"example","version":"1","page":null,"text":"Ambígua","deleted":false}}]');
  raise exception 'ambiguous note accepted';
 exception when raise_exception then if sqlerrm<>'invalid_event' then raise; end if; end;

 if exists(select 1 from public.rumo_questions where id='draft-hidden') or exists(select 1 from public.rumo_cards where id='draft-hidden') then raise exception 'draft visible'; end if;
 begin
  perform public.push_events('[{"id":"10000000-0000-0000-0000-000000000017","device_id":"20000000-0000-0000-0000-000000000001","kind":"reading.page","entity_id":"planned-hidden:1:page:1","base_revision":0,"payload":{"lesson_id":"planned-hidden","version":"1","page":1,"pages":1,"read":true}}]');
  raise exception 'planned reading accepted';
 exception when raise_exception then if sqlerrm<>'content_unavailable' then raise; end if; end;

 perform public.push_events('[{"id":"10000000-0000-0000-0000-000000000016","device_id":"20000000-0000-0000-0000-000000000001","kind":"note.save","entity_id":"70000000-0000-0000-0000-000000000001","base_revision":0,"payload":{"lesson_id":"semver","version":"1.0.0","page":null,"text":"Nota geral","deleted":false}}]');

 perform public.push_events('[{"id":"10000000-0000-0000-0000-000000000014","device_id":"20000000-0000-0000-0000-000000000001","kind":"card.save","entity_id":"60000000-0000-0000-0000-000000000001","base_revision":0,"payload":{"deck_id":"personal","front":"Teste","back":"Resposta","explanation":"","source":"","lesson_id":null,"question_id":null,"suspended":true,"deleted":false}}]');
 begin
  perform public.push_events('[{"id":"10000000-0000-0000-0000-000000000015","device_id":"20000000-0000-0000-0000-000000000001","kind":"card.review","entity_id":"50000000-0000-0000-0000-000000000003","base_revision":0,"payload":{"card_id":"60000000-0000-0000-0000-000000000001","version":"1","rating":3,"session_id":"local-session-12"}}]');
  raise exception 'suspended accepted';
 exception when raise_exception then if sqlerrm<>'card_suspended' then raise; end if; end;


end $$;
reset role;
do $$begin
 begin
  insert into public.rumo_lessons(id,version,pages,title,status,pdf_url,sha256,bytes,example)
  values('invalid-publication','1',1,'EXEMPLO INVÁLIDO','publicada','https://example.invalid/test.pdf',repeat('0',64),1,true);
  raise exception 'unreviewed publication accepted';
 exception when check_violation then null; end;
 begin
  insert into public.rumo_lessons(id,version,pages,title,status,pdf_url,sha256,bytes,example,review)
  values('credential-url','1',1,'EXEMPLO INVÁLIDO','publicada','https://user:pass@example.invalid/test.pdf',repeat('0',64),1,true,'{"status":"aprovada","reviewer":"TESTE","reviewed_at":"2026-10-12"}');
  raise exception 'credentials URL accepted';
 exception when check_violation then null; end;

end $$;
do $$begin
 begin update rumo_private.questions set answer='b' where id='example'; raise exception 'mutable question'; exception when raise_exception then if sqlerrm<>'immutable_content' then raise; end if; end;
end $$;
