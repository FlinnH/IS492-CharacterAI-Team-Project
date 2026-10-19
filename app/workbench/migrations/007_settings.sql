-- Migration 007: settings saved as data (M6.5). The Settings dialog changes the
-- provider, the key, the models, the limits, and the busy switch without a
-- restart. Each Save, each Test (with the settings it tried), each preflight,
-- and each server start whose settings differ from the last row adds one row
-- with its time. A model call's row names the row it ran with, so the log shows
-- which settings every call used. No key, and no part of one, is saved here:
-- key_set says only whether the provider had one.
CREATE TABLE app_settings (
  id INTEGER PRIMARY KEY,
  saved_at TEXT NOT NULL,
  session TEXT,
  source TEXT NOT NULL CHECK (source IN ('startup', 'settings', 'connection_test', 'preflight')),
  -- The fields that differ from the settings in force before, comma-separated.
  -- "key" when a new key was saved. Empty for the first row.
  changed TEXT NOT NULL,
  provider TEXT NOT NULL,
  -- Where calls go. Empty for the fake model, which needs no network.
  base_url TEXT NOT NULL,
  character_model TEXT NOT NULL,
  judge_model TEXT NOT NULL,
  calls_per_minute INTEGER NOT NULL CHECK (calls_per_minute >= 1),
  daily_call_cap INTEGER NOT NULL CHECK (daily_call_cap >= 1),
  force_model_error TEXT NOT NULL CHECK (force_model_error IN ('off', 'primary', 'all')),
  key_set INTEGER NOT NULL CHECK (key_set IN (0, 1)),
  models_version TEXT NOT NULL
);

CREATE TRIGGER app_settings_no_update BEFORE UPDATE ON app_settings
BEGIN
  SELECT RAISE(ABORT, 'settings rows are append-only');
END;

CREATE TRIGGER app_settings_no_delete BEFORE DELETE ON app_settings
BEGIN
  SELECT RAISE(ABORT, 'settings rows are append-only');
END;

CREATE TRIGGER app_settings_no_replace BEFORE INSERT ON app_settings
WHEN EXISTS (SELECT 1 FROM app_settings WHERE id = NEW.id)
BEGIN
  SELECT RAISE(ABORT, 'settings rows are append-only');
END;

-- Calls from before M6.5 have no settings row.
ALTER TABLE model_calls ADD COLUMN app_settings_id INTEGER REFERENCES app_settings (id);
