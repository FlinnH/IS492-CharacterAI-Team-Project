-- Migration 009: a custom run keeps the lines the model wrote for it.
-- File scenarios (T1, E1, and the rest) leave this empty and keep reading
-- app/samples/scenarios.v1.json. A custom script is part of the chat it
-- started with, so a later edit of the prompt cannot change it.
ALTER TABLE transcripts ADD COLUMN script_json TEXT;

DROP TRIGGER transcripts_keep_settings;
CREATE TRIGGER transcripts_keep_settings BEFORE UPDATE ON transcripts
WHEN NEW.id IS NOT OLD.id
  OR NEW.character_id IS NOT OLD.character_id
  OR NEW.spec_version IS NOT OLD.spec_version
  OR NEW.kind IS NOT OLD.kind
  OR NEW.title IS NOT OLD.title
  OR NEW.sample IS NOT OLD.sample
  OR NEW.tool IS NOT OLD.tool
  OR NEW.receipt IS NOT OLD.receipt
  OR NEW.scenario IS NOT OLD.scenario
  OR NEW.model IS NOT OLD.model
  OR NEW.numbering IS NOT OLD.numbering
  OR NEW.user_name IS NOT OLD.user_name
  OR NEW.character_name IS NOT OLD.character_name
  OR NEW.source_json IS NOT OLD.source_json
  OR NEW.content_sha256 IS NOT OLD.content_sha256
  OR NEW.session IS NOT OLD.session
  OR NEW.created_at IS NOT OLD.created_at
  OR NEW.script_json IS NOT OLD.script_json
BEGIN
  SELECT RAISE(ABORT, 'a chat keeps the spec version and settings it started with');
END;
