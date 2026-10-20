-- Migration 008: the session limits in Settings. The runs and the AI judge
-- calls one browser session may make join the settings each app_settings row
-- records, so a change to either is a dated row too. Rows from before have NULL.
ALTER TABLE app_settings ADD COLUMN session_run_limit INTEGER CHECK (session_run_limit IS NULL OR session_run_limit >= 1);
ALTER TABLE app_settings ADD COLUMN session_judge_limit INTEGER CHECK (session_judge_limit IS NULL OR session_judge_limit >= 1);
