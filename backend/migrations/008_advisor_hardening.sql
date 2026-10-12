begin;
-- Trigger has no name lookups; pin path against future accidental resolution.
alter function rumo_private.immutable_content() set search_path=pg_catalog;
-- Index the referencing side of editorial foreign keys for joins/deletion checks.
create index rumo_cards_published_deck on public.rumo_cards(deck_id,deck_version);
create index rumo_topics_parent on public.rumo_topics(parent_id);
create index rumo_topics_subject on public.rumo_topics(subject_id);
commit;
