-- Migration 002: chats, their messages, the model call log, and the event log.
-- A chat keeps the spec version, model, and source it started with, and only
-- its status changes. Messages, model calls, and events are append-only, so
-- the record of what was said and what each call cost can't be rewritten.
-- Rows never hold a key, and model calls never hold prompt or chat text.

-- kind: live (run in the workbench), import (pasted), or sample (a file the
-- workbench ships or points to). numbering says whether a message's turn
-- column holds a turn number or a line number, as the source numbered it.
CREATE TABLE transcripts (
  id INTEGER PRIMARY KEY,
  character_id INTEGER NOT NULL REFERENCES characters (id),
  spec_version INTEGER NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('live', 'import', 'sample')),
  title TEXT NOT NULL,
  sample TEXT,
  tool TEXT NOT NULL DEFAULT '',
  receipt TEXT NOT NULL DEFAULT '',
  scenario TEXT,
  model TEXT,
  numbering TEXT NOT NULL CHECK (numbering IN ('turn', 'line')),
  user_name TEXT NOT NULL,
  character_name TEXT NOT NULL,
  source_json TEXT NOT NULL DEFAULT '{}',
  content_sha256 TEXT,
  status TEXT NOT NULL CHECK (status IN ('active', 'script_done', 'stopped', 'imported')),
  session TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (character_id, spec_version) REFERENCES spec_versions (character_id, version)
);

CREATE INDEX transcripts_content ON transcripts (content_sha256);

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
BEGIN
  SELECT RAISE(ABORT, 'a chat keeps the spec version and settings it started with');
END;

CREATE TRIGGER transcripts_no_delete BEFORE DELETE ON transcripts
BEGIN
  SELECT RAISE(ABORT, 'chats are kept');
END;

-- INSERT OR REPLACE removes the old row without firing DELETE triggers.
CREATE TRIGGER transcripts_no_replace BEFORE INSERT ON transcripts
WHEN EXISTS (SELECT 1 FROM transcripts WHERE id = NEW.id)
BEGIN
  SELECT RAISE(ABORT, 'chats are kept');
END;

-- One row per attempt to call a model, written when the attempt ends. A call
-- the daily cap refused is logged as capped and never reached the provider.
-- quota_day is the provider's quota day (a Pacific date for Gemini).
-- output_tokens counts the visible reply; reasoning_tokens counts thinking.
CREATE TABLE model_calls (
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  quota_day TEXT NOT NULL,
  session TEXT,
  role TEXT NOT NULL,
  transcript_id INTEGER REFERENCES transcripts (id),
  turn INTEGER,
  provider TEXT NOT NULL,
  model_asked TEXT NOT NULL,
  model_reported TEXT,
  prompt_version TEXT NOT NULL,
  settings_version TEXT NOT NULL,
  reasoning_effort TEXT,
  attempt INTEGER NOT NULL DEFAULT 1 CHECK (attempt >= 1),
  fallback INTEGER NOT NULL DEFAULT 0 CHECK (fallback IN (0, 1)),
  same_model INTEGER NOT NULL DEFAULT 0 CHECK (same_model IN (0, 1)),
  ttft_ms INTEGER,
  latency_ms INTEGER,
  input_tokens INTEGER,
  cached_tokens INTEGER,
  output_tokens INTEGER,
  reasoning_tokens INTEGER,
  est_cost_usd REAL,
  status TEXT NOT NULL CHECK (status IN ('ok', 'stopped', 'error', 'timeout', 'empty', 'capped')),
  error TEXT
);

CREATE INDEX model_calls_day ON model_calls (quota_day, provider);

CREATE TRIGGER model_calls_no_update BEFORE UPDATE ON model_calls
BEGIN
  SELECT RAISE(ABORT, 'model calls are append-only');
END;

CREATE TRIGGER model_calls_no_delete BEFORE DELETE ON model_calls
BEGIN
  SELECT RAISE(ABORT, 'model calls are append-only');
END;

CREATE TRIGGER model_calls_no_replace BEFORE INSERT ON model_calls
WHEN EXISTS (SELECT 1 FROM model_calls WHERE id = NEW.id)
BEGIN
  SELECT RAISE(ABORT, 'model calls are append-only');
END;

-- turn is the source's own number. stopped marks a reply cut off by Stop or a
-- dropped connection. model_call_id links a model's reply to its call.
CREATE TABLE messages (
  id INTEGER PRIMARY KEY,
  transcript_id INTEGER NOT NULL REFERENCES transcripts (id),
  seq INTEGER NOT NULL CHECK (seq >= 1),
  turn INTEGER NOT NULL,
  speaker TEXT NOT NULL CHECK (speaker IN ('user', 'character')),
  text TEXT NOT NULL,
  source TEXT NOT NULL CHECK (source IN ('script', 'typed', 'import', 'model')),
  stopped INTEGER NOT NULL DEFAULT 0 CHECK (stopped IN (0, 1)),
  model_call_id INTEGER REFERENCES model_calls (id),
  created_at TEXT NOT NULL,
  UNIQUE (transcript_id, seq)
);

CREATE TRIGGER messages_no_update BEFORE UPDATE ON messages
BEGIN
  SELECT RAISE(ABORT, 'messages are append-only');
END;

CREATE TRIGGER messages_no_delete BEFORE DELETE ON messages
BEGIN
  SELECT RAISE(ABORT, 'messages are append-only');
END;

CREATE TRIGGER messages_no_replace BEFORE INSERT ON messages
WHEN EXISTS (
  SELECT 1 FROM messages
  WHERE (transcript_id = NEW.transcript_id AND seq = NEW.seq) OR id = NEW.id
)
BEGIN
  SELECT RAISE(ABORT, 'messages are append-only');
END;

-- What the creator did, for the CP4 study. M4 adds a flag_id column.
CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL,
  session TEXT,
  kind TEXT NOT NULL CHECK (kind IN (
    'evidence_opened', 'agree', 'override', 'undo', 'recheck', 'question_asked',
    'run_started', 'run_stopped', 'message_typed', 'import', 'spec_saved', 'error_shown'
  )),
  transcript_id INTEGER REFERENCES transcripts (id),
  reason TEXT
);

CREATE TRIGGER events_no_update BEFORE UPDATE ON events
BEGIN
  SELECT RAISE(ABORT, 'events are append-only');
END;

CREATE TRIGGER events_no_delete BEFORE DELETE ON events
BEGIN
  SELECT RAISE(ABORT, 'events are append-only');
END;

CREATE TRIGGER events_no_replace BEFORE INSERT ON events
WHEN EXISTS (SELECT 1 FROM events WHERE id = NEW.id)
BEGIN
  SELECT RAISE(ABORT, 'events are append-only');
END;
