-- Migration 003: checks of a saved chat (M3). A check runs the rule checks,
-- which need no AI, and one AI judge review of the whole chat. Rule flags are
-- stored apart from any judge run, so a judge that fails never takes them
-- away. Judge flags that fail the evidence checks go to rejected_flags with
-- their reason, and the screen only counts them. Judge runs, rejected flags,
-- and not-checked topics never change. A flag keeps its evidence for good:
-- only its status and confidence may change, when a later re-check withdraws
-- or re-rates it. None of these rows holds a key.

-- content_key names the chat as the judge saw it: the chat, its spec version,
-- and every message. cache_key adds the judge prompt and schema versions, the
-- model, and the reasoning effort, so one ok run per cache_key means one judge
-- call per chat as it stands. model_call_id is the last attempt. failure is a
-- short code and note is what the creator sees; neither holds chat text.
-- raw_json is the judge's answer, kept only when it matched the schema.
CREATE TABLE judge_runs (
  id INTEGER PRIMARY KEY,
  transcript_id INTEGER NOT NULL REFERENCES transcripts (id),
  session TEXT,
  content_key TEXT NOT NULL,
  cache_key TEXT NOT NULL,
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
  raw_json TEXT,
  created_at TEXT NOT NULL,
  CHECK ((status = 'ok') = (failure IS NULL))
);

CREATE UNIQUE INDEX judge_runs_one_ok ON judge_runs (cache_key) WHERE status = 'ok';
CREATE INDEX judge_runs_chat ON judge_runs (transcript_id, cache_key);

CREATE TRIGGER judge_runs_no_update BEFORE UPDATE ON judge_runs
BEGIN
  SELECT RAISE(ABORT, 'judge runs are append-only');
END;

CREATE TRIGGER judge_runs_no_delete BEFORE DELETE ON judge_runs
BEGIN
  SELECT RAISE(ABORT, 'judge runs are append-only');
END;

-- INSERT OR REPLACE removes the old row without firing DELETE triggers.
CREATE TRIGGER judge_runs_no_replace BEFORE INSERT ON judge_runs
WHEN EXISTS (SELECT 1 FROM judge_runs WHERE id = NEW.id)
BEGIN
  SELECT RAISE(ABORT, 'judge runs are append-only');
END;

-- source: rule (code alone, no run), judge, or recheck (a later milestone).
-- turn is the source's own number. also_turns is a JSON list of the other
-- turns a rule flag covers. line_id is a line ID or a field label, as the
-- chat's spec version writes it. quote is an exact span of the reply.
-- first_confidence keeps the confidence the flag was saved with.
-- needs_call_reason says why the flag needs the creator's call.
CREATE TABLE flags (
  id INTEGER PRIMARY KEY,
  transcript_id INTEGER NOT NULL REFERENCES transcripts (id),
  content_key TEXT NOT NULL,
  run_id INTEGER REFERENCES judge_runs (id),
  source TEXT NOT NULL CHECK (source IN ('judge', 'rule', 'recheck')),
  turn INTEGER NOT NULL,
  also_turns TEXT NOT NULL DEFAULT '[]',
  type TEXT NOT NULL,
  line_id TEXT NOT NULL,
  quote TEXT NOT NULL,
  confidence TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
  first_confidence TEXT NOT NULL CHECK (first_confidence IN ('high', 'medium', 'low')),
  near_boundary_guess INTEGER NOT NULL DEFAULT 0 CHECK (near_boundary_guess IN (0, 1)),
  needs_call INTEGER NOT NULL DEFAULT 0 CHECK (needs_call IN (0, 1)),
  needs_call_reason TEXT
    CHECK (needs_call_reason IN ('persona_exit', 'near_guess', 'unsure_boundary', 'line', 'judge')),
  same_model INTEGER NOT NULL DEFAULT 0 CHECK (same_model IN (0, 1)),
  why TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'withdrawn')),
  created_at TEXT NOT NULL,
  CHECK (source != 'rule' OR run_id IS NULL),
  CHECK (source != 'judge' OR run_id IS NOT NULL),
  CHECK ((needs_call = 1) = (needs_call_reason IS NOT NULL))
);

CREATE INDEX flags_chat ON flags (transcript_id, content_key);

CREATE TRIGGER flags_keep_evidence BEFORE UPDATE ON flags
WHEN NEW.id IS NOT OLD.id
  OR NEW.transcript_id IS NOT OLD.transcript_id
  OR NEW.content_key IS NOT OLD.content_key
  OR NEW.run_id IS NOT OLD.run_id
  OR NEW.source IS NOT OLD.source
  OR NEW.turn IS NOT OLD.turn
  OR NEW.also_turns IS NOT OLD.also_turns
  OR NEW.type IS NOT OLD.type
  OR NEW.line_id IS NOT OLD.line_id
  OR NEW.quote IS NOT OLD.quote
  OR NEW.first_confidence IS NOT OLD.first_confidence
  OR NEW.near_boundary_guess IS NOT OLD.near_boundary_guess
  OR NEW.needs_call IS NOT OLD.needs_call
  OR NEW.needs_call_reason IS NOT OLD.needs_call_reason
  OR NEW.same_model IS NOT OLD.same_model
  OR NEW.why IS NOT OLD.why
  OR NEW.created_at IS NOT OLD.created_at
BEGIN
  SELECT RAISE(ABORT, 'a flag keeps its evidence: only its status and confidence change');
END;

CREATE TRIGGER flags_no_delete BEFORE DELETE ON flags
BEGIN
  SELECT RAISE(ABORT, 'flags are kept');
END;

CREATE TRIGGER flags_no_replace BEFORE INSERT ON flags
WHEN EXISTS (SELECT 1 FROM flags WHERE id = NEW.id)
BEGIN
  SELECT RAISE(ABORT, 'flags are kept');
END;

-- reason names the evidence check the flag failed, or says it repeated
-- another flag. raw_json is the flag or claim as the judge wrote it.
CREATE TABLE rejected_flags (
  id INTEGER PRIMARY KEY,
  run_id INTEGER NOT NULL REFERENCES judge_runs (id),
  transcript_id INTEGER NOT NULL REFERENCES transcripts (id),
  reason TEXT NOT NULL CHECK (reason IN (
    'not_a_reply', 'unknown_line', 'quote_other_turn', 'quote_from_user', 'quote_not_found',
    'duplicate', 'repeats_rule'
  )),
  turn INTEGER,
  line_id TEXT,
  quote TEXT,
  raw_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX rejected_flags_run ON rejected_flags (run_id);

CREATE TRIGGER rejected_flags_no_update BEFORE UPDATE ON rejected_flags
BEGIN
  SELECT RAISE(ABORT, 'rejected flags are append-only');
END;

CREATE TRIGGER rejected_flags_no_delete BEFORE DELETE ON rejected_flags
BEGIN
  SELECT RAISE(ABORT, 'rejected flags are append-only');
END;

CREATE TRIGGER rejected_flags_no_replace BEFORE INSERT ON rejected_flags
WHEN EXISTS (SELECT 1 FROM rejected_flags WHERE id = NEW.id)
BEGIN
  SELECT RAISE(ABORT, 'rejected flags are append-only');
END;

-- What the judge said the spec and the chat can't settle. turns is a JSON list.
CREATE TABLE not_checked (
  id INTEGER PRIMARY KEY,
  run_id INTEGER NOT NULL REFERENCES judge_runs (id),
  transcript_id INTEGER NOT NULL REFERENCES transcripts (id),
  topic TEXT NOT NULL,
  turns TEXT NOT NULL DEFAULT '[]',
  why TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX not_checked_run ON not_checked (run_id);

CREATE TRIGGER not_checked_no_update BEFORE UPDATE ON not_checked
BEGIN
  SELECT RAISE(ABORT, 'not-checked topics are append-only');
END;

CREATE TRIGGER not_checked_no_delete BEFORE DELETE ON not_checked
BEGIN
  SELECT RAISE(ABORT, 'not-checked topics are append-only');
END;

CREATE TRIGGER not_checked_no_replace BEFORE INSERT ON not_checked
WHEN EXISTS (SELECT 1 FROM not_checked WHERE id = NEW.id)
BEGIN
  SELECT RAISE(ABORT, 'not-checked topics are append-only');
END;
