# Observability

What the workbench logs, how it measures each model call, and how we debug a case. Everything is in one SQLite file, `app/data/workbench.db` by default (`WORKBENCH_DB_PATH`), which git ignores. Nothing is sent to an outside logging service.

## What we log, and what we don't

- Every attempt to call a model gets one `model_calls` row when it ends, however it ends: names, versions, timings, token counts, an estimated cost, and a short error. It never holds prompt or chat text, or a key.
- What the creator does gets an `events` row with its time: runs started and stopped, typed lines, imports, each opening of a flag's evidence, each Agree, Override, and Undo, each re-check and question, and each error card. These are the logs the CP4 study reads.
- The chats, specs, checks, flags, and re-checks are saved in their own tables, so a model call or an event can be traced back to them.
- Every settings change is a dated `app_settings` row, and each call names the row it ran with. These rows record only whether a key is set, never the key.
- Text that people typed or a model wrote is redacted before it is saved: emails, phone numbers, and key-like strings become labels like `[email removed]` (see [safety_privacy.md](safety_privacy.md)).
- The tour and the decorations log nothing. Whether someone took the tour, skipped it, or switched decorations off stays in their browser's `localStorage`, so the event log can't show it. A CP4 study session that needs this has to note it by hand.

**Append-only.** Triggers refuse UPDATE, DELETE, and INSERT OR REPLACE from any connection, including the sqlite3 command line. Three columns may change:

- `transcripts.status`, as a run goes on.
- `flags.status`, when the re-check withdraws a flag.
- `flags.confidence`, when the re-check re-rates a flag. `first_confidence` keeps the original.

## Tables and fields

Migrations 001 to 008 in `app/workbench/migrations/` make these tables. Times are UTC text ending in Z, like `2026-10-19T21:04:05.123Z`.

### characters (001)

| Field | What it holds |
| --- | --- |
| id, slug, name | One row per character. Harry (`harry`) is seeded from `app/samples/spec_v1.json`. |

### spec_versions (001)

| Field | What it holds |
| --- | --- |
| id, character_id, version | The character and the version number, from 1 up. |
| parent | The version this one was edited from. NULL for v1. |
| body | The whole spec as canonical JSON: fields, setting (shown on screen as Scene), sections, lines, line attributes, and check limits. |
| sha256 | The hash of body. |
| note | The creator's "What changed" note. |
| created_at | When it was saved. Spec saves are logged here, not in `events`. |

### line_ids (001)

| Field | What it holds |
| --- | --- |
| character_id, line_id, first_version | Every line ID ever issued, with the version that first used it, so a removed ID is never reused. |

### transcripts (002, 006)

One row per chat: a live run, an import, or a sample.

| Field | What it holds |
| --- | --- |
| id, character_id, spec_version | The chat and the spec version it is pinned to. |
| kind | live, import, or sample. |
| title, sample, tool, receipt, scenario | Where it came from, like `Claude (CLA-F2)`, `cla-f2`, `Claude`, `CLA-F2`, `F2`. |
| model | The model a live run started with. NULL for imports. |
| numbering | Whether the source numbers turns or lines. |
| user_name, character_name | Alex and Harry, or the labels an import used. |
| source_json | The source's date, mode, model, and note. |
| content_sha256 | The hash of an imported chat, so importing it again finds the saved one. |
| status | active, script_done, stopped, or imported. The only field that changes. |
| session | The browser tab's session ID. |
| created_at | When the chat started. |

### messages (002)

| Field | What it holds |
| --- | --- |
| id, transcript_id, seq | The chat and the message's place in it. |
| turn | The source's own turn or line number. |
| speaker | user or character. |
| text | The message, redacted. |
| source | script, typed, import, or model. |
| stopped | 1 when Stop, a closed tab, or an error cut the reply off. |
| model_call_id | The `model_calls` row of the attempt that wrote the reply. |
| created_at | When it was saved. |

### model_calls (002, 006, 007)

One row per attempt. A retry and a fallback each get their own row.

| Field | What it holds |
| --- | --- |
| id, started_at | When the attempt started, after any wait for its call slot. |
| quota_day | The Pacific date the attempt counts toward (`quota_timezone` in the models file). |
| session | The browser tab's session ID. NULL for preflight. |
| role | character, judge, recheck, connection_test (Test in Settings), or preflight. |
| transcript_id, turn | The chat, and the turn for a reply. Judge and re-check rows have no turn. |
| provider | gemini, ollama, openai_compatible, or fake. |
| model_asked | The model the attempt asked for. |
| model_reported | The model the service said it used. A mismatch shows a reroute. |
| prompt_version | character.v1, judge.v1, recheck.v1, or connection_test.v1. |
| settings_version | The models file in use, like models.v5. |
| reasoning_effort | The effort sent. NULL when none was sent. |
| attempt | 1 for the first try, then 2, 3, and on. |
| fallback | 1 when the fallback model made this attempt. |
| forced | 1 when `WORKBENCH_FORCE_MODEL_ERROR` or the busy switch failed it on purpose. It never reached the service. (006) |
| same_model | 1 when a judge or re-check call reviewed replies its own model wrote. |
| ttft_ms | Milliseconds to the first text. Streamed replies only. |
| latency_ms | Milliseconds for the whole attempt. |
| input_tokens, cached_tokens | Prompt tokens, and how many of them the service served from its cache. |
| output_tokens | Tokens of visible reply. |
| reasoning_tokens | Thinking tokens. |
| est_cost_usd | What the attempt would cost on the paid tier. |
| status | ok, stopped, error, timeout, empty, or capped. |
| error | A short reason, like `HTTP 429: ...`, `no first token in time`, `empty reply`, `daily cap reached`, or why a JSON answer didn't match its schema. Redacted, never chat text. |
| app_settings_id | The `app_settings` row the attempt ran with. NULL before M6.5. (007) |

### events (002, 004)

| Field | What it holds |
| --- | --- |
| id, created_at, session | When, and which browser tab. |
| kind | What happened (see the list below). |
| transcript_id | The chat. |
| flag_id | The flag, for evidence_opened, agree, override, and undo. (004) |
| flag_type | The type an override says is right, when the creator retyped the flag. (004) |
| reason | Depends on the kind (see the list below). Redacted. |

The kinds the code writes, with what goes in `reason`:

- `run_started`: the scenario ID.
- `run_stopped`: nothing.
- `message_typed`: nothing.
- `import`: the sample ID, or `paste`.
- `evidence_opened`: nothing.
- `agree`: nothing.
- `override`: the override's reason.
- `undo`: nothing.
- `recheck`: nothing.
- `question_asked`: the re-check question.
- `error_shown`: what failed, like `capped`, `error`, `timeout`, `empty`, `judge schema`, or `recheck no_key`.

The table also allows `spec_saved`, but no code writes it. Spec saves show in `spec_versions`.

The `decisions` view (004) gives each flag's standing call: its latest Agree, Override, or Undo. A flag whose latest call is an Undo, or that has none, still needs the creator's call.

### judge_runs (003)

One row per AI judge review of a chat.

| Field | What it holds |
| --- | --- |
| id, transcript_id, session | The chat and the browser tab. |
| content_key | A hash of the chat as the judge saw it: its ID, its spec version, and every message. |
| cache_key | content_key plus the judge prompt and schema versions, the model, and the reasoning effort. Only one ok run may have each cache_key, so one judge call covers a chat as it stands. |
| prompt_version, schema_version | judge.v1 and judge.schema.v1. |
| model, reasoning_effort | The model that answered (the fallback model, after a fallback) and its effort. |
| model_call_id | The last attempt's `model_calls` row. |
| attempts | How many attempts the run made. 0 when no call was made, as with no key, or for a sample's check that the demo reset loaded from the judge snapshot. Those runs have no `model_call_id`, and their `created_at` is the time of the real call they came from. |
| status | ok or failed. |
| failure | A short code when failed, like schema, cut_off, rate_limited, no_key, or session_limit. |
| note | What the creator read when the run failed. |
| same_model | 1 when the judge's model wrote some of the chat's replies. |
| raw_json | The judge's answer, kept only when it matched the schema. Redacted. |
| created_at | When the run was saved. |

### flags (003)

| Field | What it holds |
| --- | --- |
| id, transcript_id, content_key | The chat as it stood when it was checked. |
| run_id | The judge run. NULL for a rule flag. |
| source | rule, judge, or recheck. |
| turn, also_turns | The turn, and for a rule flag, the other turns that broke the same rule (a JSON list). |
| type | One of the eight failure types. |
| line_id | A line ID or a field label, as the chat's spec version writes it. |
| quote | The exact span of the reply. |
| confidence, first_confidence | The confidence now, and the one the flag was saved with. |
| near_boundary_guess | 1 when the reply guessed near what the character can't know. |
| needs_call, needs_call_reason | Whether only the creator can settle it, and why: persona_exit, near_guess, unsure_boundary, line, or judge. |
| same_model | 1 when the reviewing model wrote this reply. |
| why | One sentence on the break. |
| status | active or withdrawn. |
| created_at | When it was saved. |

### rejected_flags (003, 005)

Flags that failed the evidence checks. The creator never sees them, only a count.

| Field | What it holds |
| --- | --- |
| id, run_id, transcript_id | The judge run and the chat. |
| recheck_id | The re-check, when a re-check's new flag failed. (005) |
| reason | not_a_reply, unknown_line, quote_other_turn, quote_from_user, quote_not_found, duplicate, or repeats_rule. Only the first five are counted on screen. |
| turn, line_id, quote | What the flag said. |
| raw_json | The flag, or the claim about the user, as the model wrote it. |
| created_at | When it was saved. |

### not_checked (003)

| Field | What it holds |
| --- | --- |
| id, run_id, transcript_id | The judge run and the chat. |
| topic, turns, why | What the judge said the spec and the chat can't settle, and the turns it concerns. |
| created_at | When it was saved. |

### rechecks (005)

| Field | What it holds |
| --- | --- |
| id, transcript_id, run_id, session | The chat, the judge run it re-checked, and the browser tab. |
| content_key, cache_key | As for judge runs, plus the flags, their confidences, and the question. One ok re-check per cache_key. |
| question | The creator's question, redacted, or NULL. |
| prompt_version, schema_version, model, reasoning_effort | recheck.v1, recheck.schema.v1, and the judge's model and effort. |
| model_call_id, attempts, status, failure, note, same_model | As for judge runs. |
| picked | The flag IDs it looked at again, weakest first (a JSON list). |
| answer | The AI's answer to the question. |
| raw_json | The answer as JSON, kept only when it matched the schema. |
| created_at | When it was saved. |

### flag_changes (005)

| Field | What it holds |
| --- | --- |
| id, recheck_id, flag_id | The re-check and the flag. |
| change | added, withdrawn, rerated, or kept. |
| from_confidence, to_confidence | The confidence before and after. They differ only for a re-rated flag. |
| kept_because | needs_call or your_call, when the re-check asked to withdraw a flag that stayed. |
| why | The re-check's one-line reason. |
| created_at | When it was saved. |

### app_settings (007, 008)

One row for each Test in Settings and each Save that changes something, plus a row when the server starts, or preflight runs, with settings that differ from the last row.

| Field | What it holds |
| --- | --- |
| id, saved_at, session | When, and which browser tab. |
| source | startup, settings, connection_test, or preflight. |
| changed | The fields that differ from the settings before, comma-separated. `key` when a new key was saved. |
| provider, base_url | The service, and where its calls go. The base URL is empty for the fake model. |
| character_model, judge_model | The two models in force. |
| calls_per_minute, daily_call_cap | The limits. |
| force_model_error | off, primary, or all. |
| key_set | 1 when the provider had a key. Never the key. |
| models_version | The models file in use. |
| session_run_limit, session_judge_limit | The session limits. NULL in rows from before migration 008. (008) |

## How each number is measured

All of this happens in `app/workbench/gateway.py` and `providers.py`.

- **Latency.** The gateway reads a monotonic clock when the attempt starts, after the wait for its call slot, and again when it ends. `latency_ms` is the difference. For a streamed reply, the end is the last chunk, Stop, the first-token timeout, or an error. For a JSON call (the judge and the re-check), it covers the whole answer, thinking included. Pauses between retries fall between rows, so no row counts them.
- **Time to first token.** `ttft_ms` runs from the same start to the first chunk that holds text. Only streamed replies have one. JSON calls answer in one piece, so their rows leave it NULL.
- **Tokens.** They come from the service's usage counts, read by `usage_from` in providers.py:
  - `input_tokens` is the prompt, and `cached_tokens` is the cached part of it.
  - When the service reports thinking separately, as OpenAI does, `reasoning_tokens` is that number and `output_tokens` is the rest of the completion.
  - Gemini's endpoint counts thinking only in its total, so there `reasoning_tokens` is the total minus the prompt and the completion.
  - On a stream, Gemini repeats the counts on every chunk, and the last one seen wins. A reply cut off by Stop keeps the counts it saw by then.
  - A stream that brings no counts leaves the token fields NULL. The Mistral preset doesn't ask for them, since Mistral doesn't take `stream_options`.
  - The fake model estimates 4 characters per token.
- **Cost.** `est_cost_usd` = ((input - cached) x input price + cached x cached-input price + (output + thinking) x output price) / 1,000,000, rounded to 8 places. Prices are per million tokens, from the models file. Gemini's are Google's paid Standard tier, checked Oct 11, 2026. The free tier costs nothing, so this is what the call would cost on a paid key. Ollama and the fake model are priced at 0. A model the models file doesn't list has no price, so its cost is NULL.
- **The daily count.** The cap counts a provider's rows on today's quota day, plus calls still under way. It leaves out capped and forced rows, since those never reached the service. A retry counts as a call, because it reached the service.

## Five saved queries

Open the database read-only, so nothing can change by mistake:

```bash
sqlite3 -readonly -box app/data/workbench.db
```

Then paste a query. Each one was run on a freshly migrated database.

### 1. The slowest calls

```sql
-- The 20 slowest attempts that reached a model, with their wait for the first token and their tokens.
SELECT id, started_at, role, model_asked, model_reported, status,
       ttft_ms, latency_ms, input_tokens, output_tokens, reasoning_tokens
FROM model_calls
WHERE status != 'capped' AND forced = 0
ORDER BY latency_ms DESC
LIMIT 20;
```

### 2. Failed calls

```sql
-- Attempts that failed, newest first, with the settings each one ran with.
-- Add 'stopped' to the list to see the creator's Stops too.
SELECT c.id, c.started_at, c.role, c.transcript_id AS chat, c.turn,
       c.model_asked, c.attempt, c.fallback, c.forced, c.status, c.error,
       s.provider, s.base_url
FROM model_calls AS c
LEFT JOIN app_settings AS s ON s.id = c.app_settings_id
WHERE c.status NOT IN ('ok', 'stopped')
ORDER BY c.id DESC
LIMIT 50;
```

### 3. Hidden flags

```sql
-- Flags the evidence checks hid, newest first, with the model and prompt that wrote them.
SELECT r.id, r.created_at, r.transcript_id AS chat,
       CASE WHEN r.recheck_id IS NULL THEN 'judge' ELSE 'recheck' END AS source,
       COALESCE(k.model, j.model) AS model,
       COALESCE(k.prompt_version, j.prompt_version) AS prompt,
       r.reason, r.turn, r.line_id, r.quote
FROM rejected_flags AS r
JOIN judge_runs AS j ON j.id = r.run_id
LEFT JOIN rechecks AS k ON k.id = r.recheck_id
ORDER BY r.id DESC
LIMIT 50;
```

### 4. Calls, tokens, and cost per day

```sql
-- What each quota day used, per provider, role, and model. The attempts column,
-- summed over a provider, is what the daily cap counted.
SELECT quota_day, provider, role, model_asked,
       COUNT(*) AS attempts,
       SUM(status = 'ok') AS ok,
       SUM(input_tokens) AS input_tokens,
       SUM(cached_tokens) AS cached_tokens,
       SUM(output_tokens) AS output_tokens,
       SUM(reasoning_tokens) AS thinking_tokens,
       ROUND(SUM(est_cost_usd), 4) AS est_cost_usd
FROM model_calls
WHERE status != 'capped' AND forced = 0
GROUP BY quota_day, provider, role, model_asked
ORDER BY quota_day DESC, provider, role, model_asked;
```

### 5. One chat's timeline

```sql
-- Every model call and every creator event for one chat, in time order.
-- Put the chat's ID (from the Run screen's Chat menu, or transcripts.id) in place of 1.
SELECT started_at AS at, 'call' AS what,
       role || ' ' || status || ' (attempt ' || attempt || ')' AS detail,
       model_asked AS model, turn, latency_ms
FROM model_calls
WHERE transcript_id = 1
UNION ALL
SELECT created_at, 'event',
       kind || COALESCE(' on flag ' || flag_id, '') || COALESCE(': ' || reason, ''),
       NULL, NULL, NULL
FROM events
WHERE transcript_id = 1
ORDER BY at;
```

Quotes in query 3 and reasons in query 5 are text from the chat or the creator, already redacted.

## How we debug a case

- **A failing test.** Run it alone, and stop at the first failure:

  ```bash
  app/.venv/bin/pytest tests/test_judge.py -x -q
  app/.venv/bin/pytest -k recheck -vv
  ```

  Tests use the fake model, a fake clock, and a database in the test's own temporary folder. They never touch `app/data/`, `app/.env`, or the network. To read a test's database afterward, run it with `--basetemp=/tmp/workbench-tests`, then open the `workbench.db` in that test's folder with the sqlite3 command above. In a test, `FakeProvider.requests` holds every request the app sent, messages included, so a test can check exactly what a model would have seen.
- **A live chat or check that looks wrong.** Find its chat ID and run query 5. It shows each attempt, its status and error, the fallback model if one answered, and what the creator did. Query 3 shows any flags the evidence checks hid, with why.
- **The real model.** `app/.venv/bin/pytest tests/test_live.py --live -s` runs 3 turns of F2 against the provider in `app/.env` and prints the logged call rows. It uses about 3 free-tier calls.
- **The model setup before a demo.** `app/.venv/bin/python app/scripts/preflight.py`, with the server stopped, prints time to first token and token counts for each model and reasoning effort, and never chat text.
- **The server's own output.** run.sh prints one plain line when the server refuses to start, naming what to fix. While it runs, Uvicorn's access log shows each request's client address, method, path, and status code, never a body.
