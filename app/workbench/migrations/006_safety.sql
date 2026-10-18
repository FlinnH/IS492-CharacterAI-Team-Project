-- Migration 006: safety and failure handling (M6). For the demo, a model call
-- can be made to fail on purpose (WORKBENCH_FORCE_MODEL_ERROR in app/.env).
-- A forced attempt never reaches the provider, so it is logged with forced = 1
-- and never counts toward the daily cap. The index serves the limit on runs
-- one browser session may start.
ALTER TABLE model_calls ADD COLUMN forced INTEGER NOT NULL DEFAULT 0 CHECK (forced IN (0, 1));

CREATE INDEX transcripts_session ON transcripts (session, kind);
