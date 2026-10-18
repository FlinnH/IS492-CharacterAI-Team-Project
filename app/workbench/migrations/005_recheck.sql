-- Migration 005: the follow-up re-check (M5). After the first pass, the AI
-- judge's model looks again at its weakest flags and reads the chat again for
-- anything it missed, with the creator's question if there is one. Each
-- re-check is a row here, and each flag it touched is a flag_changes row. A
-- re-check changes a flag only as migration 003 allows: its status, when it
-- withdraws the flag, or its confidence, when it re-rates it. Its new flags
-- are flags rows with source 'recheck' and the judge run's run_id. None of
-- these rows holds a key.

-- run_id is the judge run whose flags were re-checked. content_key and
-- cache_key work like the judge's: an ok re-check of the same flags, with the
-- same question, prompt, schema, model, and reasoning effort, is shown again
-- with no new call. question is the creator's own, or NULL. picked is a JSON
-- list of the flag IDs it looked at again, weakest first. answer is the AI's
-- answer to the question. failure is a short code and note is what the
-- creator sees; neither holds chat text. raw_json is the answer, kept only
-- when it matched the schema.
CREATE TABLE rechecks (
  id INTEGER PRIMARY KEY,
  transcript_id INTEGER NOT NULL REFERENCES transcripts (id),
  run_id INTEGER NOT NULL REFERENCES judge_runs (id),
  session TEXT,
  content_key TEXT NOT NULL,
  cache_key TEXT NOT NULL,
  question TEXT,
  prompt_version TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  model TEXT NOT NULL,
  reasoning_effort TEXT,
  model_call_id INTEGER REFERENCES model_calls (id),
  attempts INTEGER NOT NULL CHECK (attempts >= 0),
  status TEXT NOT NULL CHECK (status IN ('ok', 'failed')),
  failure TEXT,
  note TEXT NOT NULL DEFAULT '',
  same_model INTEGER NOT NULL DEFAULT 0 CHECK (same_model IN (0, 1)),
  picked TEXT NOT NULL DEFAULT '[]',
  answer TEXT,
  raw_json TEXT,
  created_at TEXT NOT NULL,
  CHECK ((status = 'ok') = (failure IS NULL))
);

CREATE UNIQUE INDEX rechecks_one_ok ON rechecks (cache_key) WHERE status = 'ok';
CREATE INDEX rechecks_run ON rechecks (run_id, id);

CREATE TRIGGER rechecks_no_update BEFORE UPDATE ON rechecks
BEGIN
  SELECT RAISE(ABORT, 'rechecks are append-only');
END;

CREATE TRIGGER rechecks_no_delete BEFORE DELETE ON rechecks
BEGIN
  SELECT RAISE(ABORT, 'rechecks are append-only');
END;

-- INSERT OR REPLACE removes the old row without firing DELETE triggers.
CREATE TRIGGER rechecks_no_replace BEFORE INSERT ON rechecks
WHEN EXISTS (SELECT 1 FROM rechecks WHERE id = NEW.id)
BEGIN
  SELECT RAISE(ABORT, 'rechecks are append-only');
END;

-- What one re-check did to one flag: added it, withdrew it, re-rated it, or
-- kept it. from_confidence and to_confidence are the flag's confidence before
-- and after; they differ only for a re-rated flag. kept_because is set when
-- the re-check asked to withdraw a flag that stayed: only the creator can
-- settle the flag (needs_call), or it has the creator's call (your_call).
-- why is the re-check's one-line reason.
CREATE TABLE flag_changes (
  id INTEGER PRIMARY KEY,
  recheck_id INTEGER NOT NULL REFERENCES rechecks (id),
  flag_id INTEGER NOT NULL REFERENCES flags (id),
  change TEXT NOT NULL CHECK (change IN ('added', 'withdrawn', 'rerated', 'kept')),
  from_confidence TEXT NOT NULL CHECK (from_confidence IN ('high', 'medium', 'low')),
  to_confidence TEXT NOT NULL CHECK (to_confidence IN ('high', 'medium', 'low')),
  kept_because TEXT CHECK (kept_because IN ('needs_call', 'your_call')),
  why TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (recheck_id, flag_id),
  CHECK (kept_because IS NULL OR change = 'kept'),
  CHECK ((change = 'rerated') = (from_confidence != to_confidence))
);

CREATE INDEX flag_changes_flag ON flag_changes (flag_id, id);

CREATE TRIGGER flag_changes_no_update BEFORE UPDATE ON flag_changes
BEGIN
  SELECT RAISE(ABORT, 'flag changes are append-only');
END;

CREATE TRIGGER flag_changes_no_delete BEFORE DELETE ON flag_changes
BEGIN
  SELECT RAISE(ABORT, 'flag changes are append-only');
END;

CREATE TRIGGER flag_changes_no_replace BEFORE INSERT ON flag_changes
WHEN EXISTS (SELECT 1 FROM flag_changes WHERE id = NEW.id)
BEGIN
  SELECT RAISE(ABORT, 'flag changes are append-only');
END;

-- A new flag from a re-check that failed the evidence checks names its
-- re-check here. run_id stays the judge run it re-checked, so a first pass's
-- own count of hidden flags leaves these out.
ALTER TABLE rejected_flags ADD COLUMN recheck_id INTEGER REFERENCES rechecks (id);
