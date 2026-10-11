-- Migration 001: character specs.
-- A saved spec version never changes, and an issued line ID is never removed,
-- so a deleted line's ID can't come back. The triggers enforce both for every
-- connection, including the sqlite3 command line.

CREATE TABLE characters (
  id INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL
);

-- body is canonical JSON (specs.canonical_json) and sha256 is its hash.
-- parent is the version this one was edited from; v1 has none.
CREATE TABLE spec_versions (
  id INTEGER PRIMARY KEY,
  character_id INTEGER NOT NULL REFERENCES characters (id),
  version INTEGER NOT NULL CHECK (version >= 1),
  parent INTEGER CHECK (parent < version),
  body TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  CHECK ((version = 1) = (parent IS NULL)),
  UNIQUE (character_id, version),
  FOREIGN KEY (character_id, parent) REFERENCES spec_versions (character_id, version)
);

-- Every line ID ever issued, with the version that first used it. New lines
-- are numbered past the highest ID here, so a removed ID is never reused.
-- WITHOUT ROWID leaves no hidden row id that INSERT OR REPLACE could reuse.
CREATE TABLE line_ids (
  character_id INTEGER NOT NULL REFERENCES characters (id),
  line_id TEXT NOT NULL,
  first_version INTEGER NOT NULL,
  PRIMARY KEY (character_id, line_id),
  FOREIGN KEY (character_id, first_version) REFERENCES spec_versions (character_id, version)
) WITHOUT ROWID;

CREATE TRIGGER spec_versions_no_update BEFORE UPDATE ON spec_versions
BEGIN
  SELECT RAISE(ABORT, 'spec versions are immutable');
END;

CREATE TRIGGER spec_versions_no_delete BEFORE DELETE ON spec_versions
BEGIN
  SELECT RAISE(ABORT, 'spec versions are immutable');
END;

-- INSERT OR REPLACE removes the old row without firing DELETE triggers, so
-- an insert that reuses a saved version or its row id is refused.
CREATE TRIGGER spec_versions_no_replace BEFORE INSERT ON spec_versions
WHEN EXISTS (
  SELECT 1 FROM spec_versions
  WHERE (character_id = NEW.character_id AND version = NEW.version) OR id = NEW.id
)
BEGIN
  SELECT RAISE(ABORT, 'spec versions are immutable');
END;

CREATE TRIGGER line_ids_no_update BEFORE UPDATE ON line_ids
BEGIN
  SELECT RAISE(ABORT, 'line IDs are insert-only');
END;

CREATE TRIGGER line_ids_no_delete BEFORE DELETE ON line_ids
BEGIN
  SELECT RAISE(ABORT, 'line IDs are insert-only');
END;

CREATE TRIGGER line_ids_no_replace BEFORE INSERT ON line_ids
WHEN EXISTS (
  SELECT 1 FROM line_ids WHERE character_id = NEW.character_id AND line_id = NEW.line_id
)
BEGIN
  SELECT RAISE(ABORT, 'line IDs are insert-only');
END;
