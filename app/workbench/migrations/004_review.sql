-- Migration 004: the creator's calls on flags (M4). Agree, Override, Undo,
-- and each opening of a flag's evidence are events, so the log keeps every
-- call with its time, and an Undo never erases the call it undid. flag_id
-- names the flag. flag_type is the type an override says is right, when the
-- creator changes the flag's type; that flag still counts as a break.

-- Every call on a flag names the flag. The check runs one way, so another
-- kind, like a later re-check, may name a flag too.
ALTER TABLE events ADD COLUMN flag_id INTEGER REFERENCES flags (id)
  CHECK (flag_id IS NOT NULL OR kind NOT IN ('evidence_opened', 'agree', 'override', 'undo'));

-- Only an override sets a type.
ALTER TABLE events ADD COLUMN flag_type TEXT CHECK (flag_type IS NULL OR kind = 'override');

CREATE INDEX events_flag ON events (flag_id, kind, id);

-- The standing call on each flag: its latest Agree, Override, or Undo. A flag
-- whose latest call is an Undo, or that has none, still needs the creator's call.
CREATE VIEW decisions AS
SELECT flag_id, kind, reason, flag_type, created_at, session
FROM events AS call
WHERE kind IN ('agree', 'override', 'undo')
  AND id = (
    SELECT MAX(id) FROM events
    WHERE flag_id = call.flag_id AND kind IN ('agree', 'override', 'undo')
  );

-- The call rules hold for every connection, including the sqlite3 command
-- line. review.py checks them first and gives the creator a plain message.

-- Agree only after the creator has opened the flag's evidence.
CREATE TRIGGER events_agree_after_evidence BEFORE INSERT ON events
WHEN NEW.kind = 'agree' AND NOT EXISTS (
  SELECT 1 FROM events WHERE kind = 'evidence_opened' AND flag_id = NEW.flag_id
)
BEGIN
  SELECT RAISE(ABORT, 'agree only after the evidence is opened');
END;

-- One standing call per flag: undo it before making another.
CREATE TRIGGER events_one_call BEFORE INSERT ON events
WHEN NEW.kind IN ('agree', 'override')
  AND (SELECT kind FROM decisions WHERE flag_id = NEW.flag_id) IN ('agree', 'override')
BEGIN
  SELECT RAISE(ABORT, 'a flag has one call at a time: undo it first');
END;

-- An Undo needs a standing call to undo.
CREATE TRIGGER events_undo_needs_a_call BEFORE INSERT ON events
WHEN NEW.kind = 'undo'
  AND COALESCE((SELECT kind FROM decisions WHERE flag_id = NEW.flag_id), 'undo') = 'undo'
BEGIN
  SELECT RAISE(ABORT, 'no call to undo');
END;

-- An override says why. review.py also asks for at least 3 words.
CREATE TRIGGER events_override_needs_a_reason BEFORE INSERT ON events
WHEN NEW.kind = 'override' AND length(trim(COALESCE(NEW.reason, ''))) = 0
BEGIN
  SELECT RAISE(ABORT, 'an override needs a reason');
END;
