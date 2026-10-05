/*
  Character Consistency Workbench: CP2 prototype app

  A plain script (no modules, no build step), so index.html works when it is
  opened straight from the file system. Reads window.WORKBENCH_DATA from
  data.js. Everything the creator changes lives in memory, so "Reset demo" or
  reloading the page starts over.

  Sections:
    1. Data and state
    2. Helpers
    3. Screens
    4. Router and tabs
    5. Dialogs, tooltips, snackbar, and top app bar
    6. Start
*/
(() => {
  "use strict";

  // 1. Data and state ======================================================

  const main = document.getElementById("main");

  if (!window.WORKBENCH_DATA) {
    main.innerHTML =
      '<p class="load-error">The data did not load. Check that data.js is in the same folder as index.html.</p>';
    return;
  }

  // Frozen, so no screen can change the original by accident. Screens read
  // and change `state`, which is a copy; "Reset demo" makes a fresh one.
  const DATA = deepFreeze(window.WORKBENCH_DATA);

  // Run a conversation: the scenarios that run a chat, and the tools in the
  // prompting study. Each tool ran each scenario once; the prototype holds the
  // F2 chats only. T2 isn't listed: it tests the reviewer, not the character.
  const SCENARIO_IDS = ["T1", "E1", "E2", "F1", "F2"];
  const TOOLS = ["ChatGPT", "Claude", "Gemini"];

  let state = createInitialState();

  function createInitialState() {
    return {
      spec: clone(DATA.spec),
      scenario: clone(DATA.scenario),
      runs: clone(DATA.runs),
      // Spec editor: the text in the search field.
      specQuery: "",
      // Set by "Go to flag" on the Spec editor; Flag review opens at this flag.
      openFlagId: null,
      // The chat that Run a conversation plays and Flag review shows, and how
      // far its playback has got. The Tool dropdown picks it, and its
      // scenario sets the Scenario dropdown.
      runId: DATA.runs[0].id,
      playback: { status: "idle", shown: 0 },
      // Flag review. Every map is keyed by flag ID unless noted.
      // decisions: { verdict: "agreed" } or { verdict: "overridden", reason }
      decisions: {},
      contextOpen: {}, // the turn is expanded in the card right now
      contextSeen: {}, // the creator has opened it at least once (unlocks Agree)
      citesOpen: {}, // "flagId:lineId" when a spec line chip is expanded
      overrideDrafts: {}, // the reason being typed; a key means the field is open
      flagFilter: "All",
      notCheckedReviewed: {}, // "runId:index" when marked as reviewed
      reviewTurn: null, // the turn highlighted in the conversation
      // Set by "Open K2 in the spec" on Compare runs: { lineId, note }. The
      // Spec editor highlights that line once and lands on it.
      specHighlight: null,
    };
  }

  // 2. Helpers =============================================================

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function deepFreeze(value) {
    if (value && typeof value === "object" && !Object.isFrozen(value)) {
      Object.freeze(value);
      Object.values(value).forEach(deepFreeze);
    }
    return value;
  }

  // Run any text through this before it goes into innerHTML.
  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // Escapes the text and wraps each case-insensitive match of the lowercase
  // terms in <mark>.
  function highlight(text, terms) {
    const lower = text.toLowerCase();
    const ranges = [];
    terms.forEach((term) => {
      if (!term) return;
      for (let at = lower.indexOf(term); at !== -1; at = lower.indexOf(term, at + term.length)) {
        ranges.push([at, at + term.length]);
      }
    });
    ranges.sort((a, b) => a[0] - b[0]);

    let html = "";
    let cursor = 0;
    ranges.forEach(([start, end]) => {
      if (end <= cursor) return;
      const from = Math.max(start, cursor);
      html += `${escapeHtml(text.slice(cursor, from))}<mark>${escapeHtml(text.slice(from, end))}</mark>`;
      cursor = end;
    });
    return html + escapeHtml(text.slice(cursor));
  }

  // Every flag in every run, each paired with its run.
  function allFlags() {
    return state.runs.flatMap((run) => run.flags.map((flag) => ({ run, flag })));
  }

  function findFlag(flagId) {
    return allFlags().find(({ flag }) => flag.id === flagId) || null;
  }

  // How the interface names a chat: its tool and receipt, like "Claude (CLA-F2)".
  function runLabel(run) {
    return `${run.tool} (${run.receipt})`;
  }

  // Where a flag sits, for example "Claude (CLA-F2), turn 4".
  function flagPlace(run, flag) {
    return `${runLabel(run)}, turn ${flag.turn}`;
  }

  const CONFIDENCE_ICONS = {
    High: "signal_cellular_alt",
    Medium: "signal_cellular_alt_2_bar",
    Low: "signal_cellular_alt_1_bar",
  };

  // What the codes mean, exactly as the "What do the codes mean?" dialog in
  // index.html says. Tooltips use these meanings and no others.
  const LINE_MEANINGS = { C: "canon fact", R: "relationship", K: "knowledge limit", B: "behavior rule" };
  const CASE_MEANINGS = { T: "typical case", E: "edge case", F: "failure case" };
  const SCENARIO_MEANINGS = {
    T1: "normal chat",
    T2: "reviewing a transcript",
    E1: "long chat",
    E2: "emotional chat",
    F1: '"you\'re an AI"',
    F2: "things Harry can't know yet",
  };

  // Tooltip for a spec line, like "K2: knowledge limit".
  function lineTip(lineId) {
    return `${lineId}: ${LINE_MEANINGS[lineId[0]]}`;
  }

  // Tooltip for a scenario, like "F2: failure case, things Harry can't know yet".
  function scenarioTip(id) {
    return `${id}: ${CASE_MEANINGS[id[0]]}, ${SCENARIO_MEANINGS[id]}`;
  }

  // Confidence in words, with a signal-bars icon as a second cue.
  function confidenceHtml(level) {
    return `
      <span class="confidence">
        <span class="icon" aria-hidden="true">${CONFIDENCE_ICONS[level]}</span>
        <span>${escapeHtml(level)} confidence</span>
      </span>`;
  }

  // 3. Screens =============================================================
  // Each render function fills its screen's body from `state`.
  // - Clickable controls carry data-action="name"; add a handler to
  //   `actions` under that name. This works anywhere on the page.
  // - Controls that should keep focus across a redraw carry a unique
  //   data-focus-key.
  // - After changing `state`, call refresh() to redraw the current screen.

  const SCREENS = {
    define: { title: "Spec editor", render: renderDefine },
    run: { title: "Run a conversation", render: renderRun },
    diagnose: { title: "Flag review", render: renderDiagnose },
    compare: { title: "Compare runs", render: renderCompare },
  };

  // Click handlers for [data-action] controls, keyed by data-action:
  // actions.name = (control, event) => { ... }
  const actions = Object.create(null);

  // 3.1 Spec editor (Define) ------------------------------------------------
  // The spec as one card per section. A search filters the lines, each ID
  // chip opens a side sheet with the flags that cite that line, and
  // "Edit spec" says that only the creator can change the spec (DESIGN_SPEC
  // 7.1). Runs stay pinned to the version they used.

  const citingSheet = document.getElementById("citing-flags-sheet");
  const editSpecDialog = document.getElementById("edit-spec-dialog");
  let specCountTimer = 0;

  function renderDefine(body) {
    // Arriving from "Open K2 in the spec": clear the search so the line
    // shows, highlight it this once, and land on its chip.
    const spotlight = state.specHighlight;
    state.specHighlight = null;
    if (spotlight) state.specQuery = "";

    panelFor("define").querySelector("[data-spec-version]").textContent = state.spec.version;

    body.innerHTML = `
      <div class="spec-editor">
        <div class="spec-toolbar">
          <div class="text-field text-field--icon-leading spec-toolbar__search">
            <span class="icon text-field__icon" aria-hidden="true">search</span>
            <input class="text-field__input" type="search" id="spec-search" placeholder=" "
              value="${escapeHtml(state.specQuery)}" autocomplete="off" spellcheck="false"
              aria-describedby="spec-search-help" aria-controls="spec-results" data-focus-key="spec-search">
            <label class="text-field__label" for="spec-search">Search lines</label>
            <p class="text-field__support" id="spec-search-help">Type an ID like K2, or words like prophecy.</p>
          </div>
          <button type="button" class="btn btn--filled btn--icon-leading" data-action="edit-spec"
            data-focus-key="edit-spec" aria-haspopup="dialog">
            <span class="icon" aria-hidden="true">edit</span>
            <span>Edit spec</span>
          </button>
        </div>
        <p class="spec-status">
          <span id="spec-count" role="status"></span>
          Select an ID to see the flags that cite it.
        </p>
        <div class="spec-results" id="spec-results"></div>
      </div>`;

    const search = body.querySelector("#spec-search");
    search.addEventListener("input", () => {
      state.specQuery = search.value;
      renderSpecResults(body);
    });
    renderSpecResults(body, { announce: false, spotlight });
    return spotlight ? body.querySelector(`[data-focus-key="line-${spotlight.lineId}"]`) : null;
  }

  // Redraws only the cards, so the search field keeps focus while you type.
  function renderSpecResults(body, { announce = true, spotlight = null } = {}) {
    const terms = searchTerms(state.specQuery);
    let total = 0;
    let shown = 0;

    const cards = specCards(state.spec).map((card, index) => {
      const lines = card.lines.filter((line) => lineMatches(line, terms));
      total += card.lines.length;
      shown += lines.length;
      if (lines.length === 0) return "";
      return `
        <section class="card card--outlined spec-card" aria-labelledby="spec-card-${index}">
          <h2 class="spec-card__title" id="spec-card-${index}">${escapeHtml(card.heading)}</h2>
          ${renderSpecLines(lines, terms, spotlight)}
        </section>`;
    });

    body.querySelector("#spec-results").innerHTML =
      shown > 0
        ? cards.join("")
        : `
          <div class="card card--outlined spec-empty">
            <p>No lines match <q>${escapeHtml(state.specQuery.trim())}</q>.</p>
            <button type="button" class="btn btn--text" data-action="clear-spec-search">Clear search</button>
          </div>`;

    let count = `Showing all ${total} lines.`;
    if (terms.length > 0) count = shown === 0 ? "No lines match." : `${shown} of ${total} lines match.`;

    // The count is a live region. Waiting for a pause in typing keeps screen
    // readers from reading it out after every keystroke.
    const status = body.querySelector("#spec-count");
    clearTimeout(specCountTimer);
    if (announce) {
      specCountTimer = setTimeout(() => {
        status.textContent = count;
      }, 300);
    } else {
      status.textContent = count;
    }
  }

  // spotlight, when set, is { lineId, note }: that line gets highlighted
  // with the note under its text.
  function renderSpecLines(lines, terms, spotlight = null) {
    const items = lines.map((line) => {
      const text = `<p class="spec-line__text">${highlight(line.text, terms)}</p>`;
      if (line.id) {
        const spotlit = Boolean(spotlight) && spotlight.lineId === line.id;
        const content = spotlit
          ? `<div class="spec-line__body">
              ${text}
              <p class="spec-line__note">
                <span class="icon" aria-hidden="true">compare_arrows</span>
                <span>${escapeHtml(spotlight.note)}</span>
              </p>
            </div>`
          : text;
        return `
          <li class="spec-line${spotlit ? " is-spotlit" : ""}">
            <button type="button" class="chip chip--assist spec-line__id" data-action="show-citing-flags"
              data-line="${escapeHtml(line.id)}" data-focus-key="line-${escapeHtml(line.id)}" aria-haspopup="dialog"
              data-tooltip="${escapeHtml(lineTip(line.id))}">
              ${escapeHtml(line.id)}<span class="visually-hidden">: ${escapeHtml(LINE_MEANINGS[line.id[0]])}. Show the flags that cite this line.</span>
            </button>
            ${content}
          </li>`;
      }
      if (line.label) {
        return `
          <li class="spec-line spec-line--field">
            <p class="spec-line__label">${highlight(line.label, terms)}</p>
            ${text}
          </li>`;
      }
      return `<li class="spec-line spec-line--intro">${text}</li>`;
    });
    return `<ul class="spec-lines">${items.join("")}</ul>`;
  }

  // The spec as cards of lines. "Who Harry is" holds the opening instruction
  // and the labeled fields, which have no IDs. Every other line has an ID.
  function specCards(spec) {
    return [
      {
        heading: "Who Harry is",
        lines: [
          { text: spec.preamble },
          ...spec.fields.map((field) => ({ label: field.label, text: field.text })),
        ],
      },
      ...spec.sections.map((section) => ({
        heading: section.heading,
        lines: section.lines.map((line) => ({ id: line.id, text: line.text })),
      })),
    ];
  }

  function searchTerms(query) {
    return query.toLowerCase().split(/\s+/).filter(Boolean);
  }

  // A line matches when every term is its ID (like "k2") or appears in its words.
  function lineMatches(line, terms) {
    const id = (line.id || "").toLowerCase();
    const words = `${line.label || ""} ${line.text}`.toLowerCase();
    return terms.every((term) => term === id || words.includes(term));
  }

  function specLineText(lineId) {
    const line = state.spec.sections
      .flatMap((section) => section.lines)
      .find((candidate) => candidate.id === lineId);
    return line ? line.text : "";
  }

  // Side sheet body: the line itself, then every flag that cites it.
  function renderCitingFlags(lineId) {
    const citing = allFlags().filter(({ flag }) => flag.cites.includes(lineId));
    let summary = `${citing.length} flags cite this line.`;
    if (citing.length === 0) summary = "No flags cite this line.";
    if (citing.length === 1) summary = "1 flag cites this line.";

    return `
      <div class="cited-line">
        <span class="chip" tabindex="0" data-tooltip="${escapeHtml(lineTip(lineId))}">${escapeHtml(lineId)}<span class="visually-hidden">: ${escapeHtml(LINE_MEANINGS[lineId[0]])}</span></span>
        <p class="cited-line__text">${escapeHtml(specLineText(lineId))}</p>
      </div>
      <p class="sheet-summary">${summary}</p>
      ${citing.length > 0 ? `<ul class="flag-list">${citing.map(renderFlagSummary).join("")}</ul>` : ""}`;
  }

  // A short card for one flag.
  function renderFlagSummary({ run, flag }) {
    const place = flagPlace(run, flag);
    return `
      <li class="card card--outlined flag-summary">
        <h3 class="flag-summary__title">
          <span class="flag-summary__place">${escapeHtml(place)}<span class="visually-hidden">:</span></span>
          <span>${escapeHtml(flag.type)}</span>
        </h3>
        <p>${confidenceHtml(flag.confidence)}</p>
        <dl class="flag-summary__details">
          <div>
            <dt>Evidence</dt>
            <dd><q>${escapeHtml(flag.evidence)}</q></dd>
          </div>
          <div>
            <dt>Why</dt>
            <dd>${escapeHtml(flag.why)}</dd>
          </div>
        </dl>
        <button type="button" class="btn btn--outlined" data-action="go-to-flag" data-flag="${escapeHtml(flag.id)}">
          Go to flag<span class="visually-hidden">: ${escapeHtml(place)}</span>
        </button>
      </li>`;
  }

  actions["clear-spec-search"] = () => {
    const body = panelFor("define").querySelector("[data-screen-body]");
    const search = body.querySelector("#spec-search");
    state.specQuery = "";
    search.value = "";
    renderSpecResults(body);
    search.focus();
  };

  actions["show-citing-flags"] = (chip) => {
    const lineId = chip.dataset.line;
    const sheetBody = citingSheet.querySelector("[data-sheet-body]");
    citingSheet.querySelector("#citing-flags-title").textContent = `Flags that cite ${lineId}`;
    sheetBody.innerHTML = renderCitingFlags(lineId);
    sheetBody.scrollTop = 0;
    openDialog(citingSheet, chip);
  };

  actions["go-to-flag"] = (button) => {
    const target = findFlag(button.dataset.flag);
    if (target && target.run.id !== state.runId) changeRunSetup({ runId: target.run.id });
    state.openFlagId = button.dataset.flag;
    citingSheet.close();
    goToScreen("diagnose");
  };

  actions["edit-spec"] = (button) => {
    openDialog(editSpecDialog, button, (choice) => {
      if (choice === "create") {
        showSnackbar(`This is a demo, so nothing was saved. The spec is still ${state.spec.version}.`);
      }
    });
  };

  // 3.2 Run a conversation (Stress-test) ------------------------------------
  // The Tool dropdown picks one real chat of the scenario, and Start run plays
  // it one message at a time, the way a live conversation arrives, with the
  // turn count and a way to skip ahead (DESIGN_SPEC section 4). Playback keeps
  // going if you switch screens. Picking another chat stops it.

  const PLAYBACK_STEP_MS = 500;
  let playbackTimer = 0;

  function selectedRun() {
    return state.runs.find((run) => run.id === state.runId) || state.runs[0];
  }

  // Picking another chat starts over, so the chat area clears.
  function changeRunSetup(change) {
    stopPlayback();
    Object.assign(state, change);
    state.playback = { status: "idle", shown: 0 };
  }

  function stopPlayback() {
    clearTimeout(playbackTimer);
  }

  // Everything the chat shows for one run, in order: the spec loading at
  // turn 1, then for each turn the script's line and the character's reply.
  function chatItems(scenario, run) {
    const items = [{ kind: "system", turn: 1, text: `Turn 1: character spec ${run.specVersion} loaded` }];
    scenario.userLines.forEach((line) => {
      items.push({ kind: "user", turn: line.turn, text: line.text });
      const reply = run.replies.find((candidate) => candidate.turn === line.turn);
      if (reply) items.push({ kind: "character", turn: reply.turn, text: reply.text });
    });
    return items;
  }

  function breaksText(count) {
    if (count === 0) return "no possible breaks";
    return count === 1 ? "1 possible break" : `${count} possible breaks`;
  }

  // Where the chat came from, as its block records it, for example
  // "Saved 2026-10-01 (Incognito). Model shown: Sonnet 5.5."
  function sourceText(run) {
    const { date, mode, model, note } = run.source;
    return [`Saved ${date} (${mode}).`, model ? `Model shown: ${model}.` : "", note].filter(Boolean).join(" ");
  }

  function renderRun(body) {
    const run = selectedRun();
    const items = chatItems(state.scenario, run);

    // The Scenario dropdown shows this chat's scenario. Scenarios with no chat
    // in the prototype can't be picked.
    const scenarioOptions = SCENARIO_IDS.map((id) => {
      const hasChats = state.runs.some((chat) => chat.scenarioId === id);
      const label = id === state.scenario.id ? state.scenario.name : `${id} (not in this prototype)`;
      return `<option value="${id}"${hasChats ? "" : " disabled"}${id === run.scenarioId ? " selected" : ""}>${escapeHtml(label)}</option>`;
    }).join("");
    // The Tool dropdown picks the chat. A tool without a chat of this
    // scenario says so and can't be picked.
    const toolOptions = TOOLS.map((tool) => {
      const chat = state.runs.find((candidate) => candidate.tool === tool && candidate.scenarioId === run.scenarioId);
      if (!chat) return `<option value="" disabled>${escapeHtml(tool)} (no chat yet)</option>`;
      return `<option value="${escapeHtml(chat.id)}"${chat.id === run.id ? " selected" : ""}>${escapeHtml(tool)}</option>`;
    }).join("");

    body.innerHTML = `
      <div class="run-screen">
        <div class="run-setup">
          ${selectField("run-scenario", "Scenario", scenarioOptions, {
            support: "T2 tests the reviewer, not the character, so it isn't a run.",
            tooltip: scenarioTip(run.scenarioId),
          })}
          ${selectField("run-tool", "Tool", toolOptions, {
            support: "Each tool ran this scenario once. Pick one to play its chat.",
          })}
          <button type="button" class="btn btn--filled btn--icon-leading" data-action="start-run" data-focus-key="start-run">
            <span class="icon" aria-hidden="true">play_arrow</span>
            <span>Start run</span>
          </button>
        </div>

        <section class="card card--outlined transcript" aria-labelledby="transcript-title">
          <div class="transcript__header">
            <h2 class="transcript__title" id="transcript-title">Transcript</h2>
            <span class="chip chip--icon-leading">
              <span class="icon" aria-hidden="true">receipt_long</span>
              <span>Receipt ${escapeHtml(run.receipt)}</span>
            </span>
            <span class="chip chip--icon-leading">
              <span class="icon" aria-hidden="true">description</span>
              <span>Spec ${escapeHtml(run.specVersion)}</span>
            </span>
          </div>
          <p class="transcript__source">${escapeHtml(sourceText(run))}</p>
          <div class="run-progress" hidden>
            <p class="run-progress__label" id="run-progress-label"></p>
            <progress class="linear-progress" aria-labelledby="run-progress-label"></progress>
            <button type="button" class="btn btn--text" data-action="skip-run" data-focus-key="skip-run">Skip to end</button>
          </div>
          <div class="chat" tabindex="0" role="region" aria-label="Messages">
            ${state.playback.shown === 0
              ? `<p class="chat__empty">Press Start run to play ${escapeHtml(run.receipt)} turn by turn.</p>`
              : ""}
            <ol class="chat__list">${items.slice(0, state.playback.shown).map(renderChatItem).join("")}</ol>
          </div>
        </section>

        <div class="run-result" role="status"></div>
      </div>`;

    body.querySelector("#run-tool").addEventListener("change", (event) => {
      changeRunSetup({ runId: event.target.value });
      refresh();
    });

    const chat = body.querySelector(".chat");
    chat.scrollTop = chat.scrollHeight;
    renderRunStatus(body);
  }

  // A native <select> dressed as an M3 outlined field. support is the quiet
  // line under it; tooltip shows on hover or focus and is read out as a
  // description too.
  function selectField(id, label, options, { support = "", tooltip = "" } = {}) {
    const describedBy = [support && `${id}-help`, tooltip && `${id}-meaning`].filter(Boolean).join(" ");
    return `
      <div class="text-field text-field--select">
        <select class="text-field__input" id="${id}" data-focus-key="${id}"${describedBy ? ` aria-describedby="${describedBy}"` : ""}${tooltip ? ` data-tooltip="${escapeHtml(tooltip)}" data-tooltip-place="above"` : ""}>${options}</select>
        <label class="text-field__label" for="${id}">${escapeHtml(label)}</label>
        ${support ? `<p class="text-field__support" id="${id}-help">${escapeHtml(support)}</p>` : ""}
        ${tooltip ? `<span class="visually-hidden" id="${id}-meaning">${escapeHtml(tooltip)}</span>` : ""}
      </div>`;
  }

  function renderChatItem(item) {
    if (item.kind === "system") {
      return `
        <li class="chat__system">
          <span class="icon" aria-hidden="true">description</span>
          <span>${escapeHtml(item.text)}</span>
        </li>`;
    }
    const speaker = item.kind === "user" ? state.scenario.userName : state.scenario.characterName;
    return `
      <li class="bubble bubble--${item.kind}">
        <p class="bubble__meta">
          <span class="bubble__speaker">${escapeHtml(speaker)}</span>
          <span class="bubble__turn">Turn ${item.turn}<span class="visually-hidden">:</span></span>
        </p>
        <p class="bubble__text keep-lines">${escapeHtml(item.text)}</p>
      </li>`;
  }

  // Updates what changes while a run plays: the turn count, the Start and
  // Skip buttons, and the result card at the end.
  function renderRunStatus(body) {
    const { status, shown } = state.playback;
    const run = selectedRun();
    const items = chatItems(state.scenario, run);
    const totalTurns = items[items.length - 1].turn;
    const turn = shown > 0 ? items[shown - 1].turn : 0;

    const progress = body.querySelector(".run-progress");
    const skipHadFocus = document.activeElement === progress.querySelector('[data-action="skip-run"]');
    progress.hidden = status !== "playing";
    progress.querySelector(".run-progress__label").textContent = `Turn ${turn} of ${totalTurns}`;
    const bar = progress.querySelector("progress");
    bar.max = totalTurns;
    bar.value = turn;

    body.querySelector('[data-action="start-run"]').disabled = status === "playing";

    // The result goes into a live region, so screen readers hear it once.
    const result = body.querySelector(".run-result");
    if (status !== "done") {
      result.innerHTML = "";
    } else if (!result.firstElementChild) {
      result.innerHTML = `
        <div class="card card--filled run-result__card">
          <span class="icon" aria-hidden="true">task_alt</span>
          <p class="run-result__text">Run complete. The workbench found ${breaksText(run.flags.length)}.</p>
          <button type="button" class="btn btn--filled" data-action="review-flags" data-focus-key="review-flags">Review flags</button>
        </div>`;
      // Skip to end just disappeared, so its focus moves to the next step.
      if (skipHadFocus) result.querySelector('[data-action="review-flags"]').focus();
    }
  }

  // Shows the next message. Only touches the page while the Run screen is
  // open; coming back to it redraws everything from `state`.
  function playNext() {
    const items = chatItems(state.scenario, selectedRun());
    state.playback.shown += 1;
    if (state.playback.shown >= items.length) {
      state.playback.status = "done";
    } else {
      playbackTimer = setTimeout(playNext, PLAYBACK_STEP_MS);
    }
    if (currentScreen !== "run") return;

    const body = panelFor("run").querySelector("[data-screen-body]");
    const chat = body.querySelector(".chat");
    // Follow new messages, unless the creator scrolled up to reread.
    const atBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight < 48;
    chat.querySelector(".chat__list").insertAdjacentHTML("beforeend", renderChatItem(items[state.playback.shown - 1]));
    if (atBottom) chat.scrollTop = chat.scrollHeight;
    renderRunStatus(body);
  }

  actions["start-run"] = () => {
    stopPlayback();
    state.playback = { status: "playing", shown: 1 };
    const body = panelFor("run").querySelector("[data-screen-body]");
    renderRun(body);
    // Start run is disabled while it plays, so focus moves to Skip to end.
    body.querySelector('[data-action="skip-run"]').focus();
    playbackTimer = setTimeout(playNext, PLAYBACK_STEP_MS);
  };

  actions["skip-run"] = () => {
    stopPlayback();
    const items = chatItems(state.scenario, selectedRun());
    const body = panelFor("run").querySelector("[data-screen-body]");
    const chat = body.querySelector(".chat");
    chat.querySelector(".chat__list").insertAdjacentHTML(
      "beforeend",
      items.slice(state.playback.shown).map(renderChatItem).join(""),
    );
    state.playback = { status: "done", shown: items.length };
    chat.scrollTop = chat.scrollHeight;
    renderRunStatus(body);
  };

  actions["review-flags"] = () => {
    state.openFlagId = null;
    goToScreen("diagnose");
  };

  // 3.3 Flag review (Diagnose) ----------------------------------------------
  // The heart of the workbench: the AI proposes flags, and the creator makes
  // the call on each one (DESIGN_SPEC 7.1 to 7.4).
  // - Evidence first: Agree unlocks only after "Show in context".
  // - An override needs a reason of at least 3 words.
  // - Agree and Override look the same, so the screen doesn't push agreement.
  // - Agreeing with every flag triggers a rubber-stamp check.
  // - What the AI could not check is listed for the creator to read.
  // Every decision redraws the screen; announceReview() tells screen readers.

  const CONFIDENCE_FILTERS = ["All", "High", "Medium", "Low"];
  const MIN_REASON_WORDS = 3;
  const RUBBER_STAMP_MESSAGE =
    "You agreed with every flag. The AI makes mistakes too, so check again whether each one is really a break.";

  // Measures the sticky summary bar, so the CSS can keep keyboard focus from
  // scrolling under it (see --review-bar-height in styles.css).
  const reviewBarObserver = "ResizeObserver" in window
    ? new ResizeObserver((entries) => {
        const height = entries[0].target.offsetHeight;
        document.documentElement.style.setProperty("--review-bar-height", `${height}px`);
      })
    : null;

  function countWords(text) {
    return text.trim().split(/\s+/).filter(Boolean).length;
  }

  function verdictOf(decisions, flag) {
    return decisions[flag.id] ? decisions[flag.id].verdict : null;
  }

  // "6 flags, 0 agreed, 0 overridden. First break: turn 3." The first break
  // is the earliest flag the creator hasn't overridden.
  function reviewSummary(flags, decisions) {
    const agreed = flags.filter((flag) => verdictOf(decisions, flag) === "agreed").length;
    const overridden = flags.filter((flag) => verdictOf(decisions, flag) === "overridden").length;
    const standing = flags.filter((flag) => verdictOf(decisions, flag) !== "overridden").map((flag) => flag.turn);
    const firstBreak = standing.length > 0 ? `turn ${Math.min(...standing)}` : "none";
    const noun = flags.length === 1 ? "flag" : "flags";
    return `${flags.length} ${noun}, ${agreed} agreed, ${overridden} overridden. First break: ${firstBreak}.`;
  }

  function agreedWithEvery(flags, decisions) {
    return flags.length > 0 && flags.every((flag) => verdictOf(decisions, flag) === "agreed");
  }

  function visibleFlags(flags, filter) {
    return filter === "All" ? flags : flags.filter((flag) => flag.confidence === filter);
  }

  // "Turn 4, knowledge boundary"
  function flagTitle(flag) {
    return `Turn ${flag.turn}, ${flag.type.toLowerCase()}`;
  }

  function cardId(flag) {
    return `flag-${flag.id}`;
  }

  function renderDiagnose(body) {
    const run = selectedRun();
    const flags = [...run.flags].sort((a, b) => a.turn - b.turn);

    // Arriving from "Go to flag": make sure that flag shows, then land on it.
    const target = state.openFlagId ? flags.find((flag) => flag.id === state.openFlagId) : null;
    state.openFlagId = null;
    if (target) {
      if (visibleFlags([target], state.flagFilter).length === 0) state.flagFilter = "All";
      state.reviewTurn = target.turn;
    }

    const shown = visibleFlags(flags, state.flagFilter);
    const cards = shown.length > 0
      ? `<ol class="flag-cards">${shown.map((flag) => `<li>${renderFlagCard(run, flag)}</li>`).join("")}</ol>`
      : `<p class="card card--outlined flag-cards__empty">No ${state.flagFilter.toLowerCase()}-confidence flags in this run.</p>`;

    body.innerHTML = `
      <div class="review">
        <div class="review__main">
          <div class="review__bar-wrap">
            ${renderChatSwitcher(run)}
            <div class="review__bar">
              <p class="review__summary">${escapeHtml(reviewSummary(flags, state.decisions))}</p>
              ${agreedWithEvery(flags, state.decisions)
                ? `<p class="review__nudge">
                    <span class="icon" aria-hidden="true">fact_check</span>
                    <span>${RUBBER_STAMP_MESSAGE}</span>
                  </p>`
                : ""}
              ${renderFlagFilters()}
            </div>
          </div>
          <h2 class="visually-hidden">Flags</h2>
          ${cards}
          ${renderNotChecked(run)}
        </div>
        ${renderConversation(run, flags)}
      </div>`;

    body.querySelectorAll("[data-reason-for]").forEach((field) => {
      const flagId = field.dataset.reasonFor;
      field.addEventListener("input", () => {
        state.overrideDrafts[flagId] = field.value;
        const save = body.querySelector(`[data-focus-key="save-${flagId}"]`);
        save.setAttribute("aria-disabled", String(countWords(field.value) < MIN_REASON_WORDS));
      });
      // Escape closes the reason field, the same as Cancel.
      field.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        event.preventDefault();
        cancelOverride(flagId);
      });
    });
    body.querySelectorAll("[data-reviewed]").forEach((box) => {
      box.addEventListener("change", () => {
        state.notCheckedReviewed[box.dataset.reviewed] = box.checked;
      });
    });
    if (reviewBarObserver) {
      reviewBarObserver.disconnect();
      reviewBarObserver.observe(body.querySelector(".review__bar-wrap"));
    }

    if (!target) return null;
    revealTurn(body);
    return body.querySelector(`#${cardId(target)}`);
  }

  // The human-in-the-loop to-do. Every flag needs the creator's call, agree
  // or override, before the review is done. The cues below count calls made,
  // never agreements, so they push the creator to decide, not to agree
  // quickly (the rubber-stamp risk in THEORY_LENS Part 1). They show in four
  // places: the badge on the Flag review tab, each chat in the chat switcher,
  // a "Needs your call" label on each open card, and a notice on Compare runs.

  // Every chat of the scenario on screen, one per tool.
  function scenarioChats() {
    const scenarioId = selectedRun().scenarioId;
    return state.runs.filter((run) => run.scenarioId === scenarioId);
  }

  // Flags still waiting for the creator's call, in every chat of the scenario.
  function openFlags() {
    return scenarioChats().flatMap((run) =>
      run.flags.filter((flag) => !verdictOf(state.decisions, flag)).map((flag) => ({ run, flag })),
    );
  }

  // "2 need your call", or "All 3 decided" once every flag has a call.
  function decidedText(run) {
    const total = run.flags.length;
    const open = run.flags.filter((flag) => !verdictOf(state.decisions, flag)).length;
    if (total === 0) return "No flags";
    if (open > 0) return `${open} ${open === 1 ? "needs" : "need"} your call`;
    return total === 1 ? "Decided" : `All ${total} decided`;
  }

  // Switches between the chats of this scenario without leaving the screen,
  // one button per tool. Each shows how many calls are left, with a progress
  // bar, so a chat nobody has reviewed stands out. It shares the chosen chat
  // with Run a conversation. On phones the buttons stack (see styles.css).
  function renderChatSwitcher(run) {
    const chats = scenarioChats();
    if (chats.length < 2) return "";
    const buttons = chats.map((chat) => {
      const selected = chat.id === run.id;
      const total = chat.flags.length;
      const decided = chat.flags.filter((flag) => verdictOf(state.decisions, flag)).length;
      const done = decided === total;
      const icon = selected ? "check" : done ? "task_alt" : "pending";
      return `
        <button type="button" class="segmented__button chat-switcher__button" aria-pressed="${selected}"
          data-action="pick-chat" data-run="${escapeHtml(chat.id)}" data-focus-key="chat-${escapeHtml(chat.id)}">
          <span class="icon${done && !selected ? " icon--filled" : ""}" aria-hidden="true">${icon}</span>
          <span class="chat-switcher__text">
            <span class="chat-switcher__name">${escapeHtml(runLabel(chat))}</span>
            <span class="chat-switcher__count">${decidedText(chat)}</span>
            <progress class="linear-progress chat-switcher__progress" max="${Math.max(total, 1)}" value="${total ? decided : 1}" aria-hidden="true"></progress>
          </span>
        </button>`;
    });
    return `<div class="segmented chat-switcher" role="group" aria-label="Chat to review">${buttons.join("")}</div>`;
  }

  // The badge on the Flag review tab: how many calls are left across every
  // chat of the scenario, so the open work shows from any screen.
  function updateTodoBadge() {
    const open = openFlags().length;
    const badge = document.querySelector("[data-todo-badge]");
    badge.hidden = open === 0;
    badge.textContent = String(open);
    document.querySelector("[data-todo-label]").textContent =
      open === 0 ? "" : `, ${open} ${open === 1 ? "flag needs" : "flags need"} your call`;
  }

  actions["pick-chat"] = (button) => {
    if (button.dataset.run === state.runId) return;
    changeRunSetup({ runId: button.dataset.run });
    state.reviewTurn = null;
    refresh({ focusKey: `chat-${button.dataset.run}` });
    const run = selectedRun();
    announce(`Showing ${runLabel(run)}. ${reviewSummary(run.flags, state.decisions)}`);
  };

  function renderFlagFilters() {
    const chips = CONFIDENCE_FILTERS.map((filter) => {
      const selected = filter === state.flagFilter;
      return `
        <button type="button" class="chip chip--filter${selected ? " chip--icon-leading" : ""}" aria-pressed="${selected}"
          data-action="filter-flags" data-filter="${filter}" data-focus-key="filter-${filter}">
          ${selected ? '<span class="icon" aria-hidden="true">check</span>' : ""}
          <span>${filter}</span>
        </button>`;
    }).join("");
    return `<div class="filter-chips" role="group" aria-label="Show flags by confidence">${chips}</div>`;
  }

  function renderFlagCard(run, flag) {
    const id = cardId(flag);
    const verdict = verdictOf(state.decisions, flag);
    const contextOpen = Boolean(state.contextOpen[flag.id]);
    const classes = `card card--outlined flag-card${verdict ? ` is-${verdict}` : ""}`;

    return `
      <article class="${classes}" id="${id}" tabindex="-1" aria-labelledby="${id}-title">
        <div class="flag-card__head">
          <h3 class="flag-card__title" id="${id}-title">${escapeHtml(flagTitle(flag))}</h3>
          ${verdict
            ? ""
            : '<span class="needs-call"><span class="icon" aria-hidden="true">pending</span><span>Needs your call</span></span>'}
        </div>
        <figure class="flag-card__evidence">
          <blockquote><p><q>${escapeHtml(flag.evidence)}</q></p></blockquote>
          <figcaption>From ${escapeHtml(state.scenario.characterName)}'s reply</figcaption>
        </figure>
        <div class="flag-card__chips">
          ${flag.cites.map((lineId) => renderCiteChip(flag, lineId)).join("")}
          <span class="chip chip--icon-leading flag-card__confidence">
            <span class="icon" aria-hidden="true">${CONFIDENCE_ICONS[flag.confidence]}</span>
            <span>${escapeHtml(flag.confidence)}<span class="visually-hidden"> confidence</span></span>
          </span>
        </div>
        ${flag.cites.map((lineId) => renderCiteText(flag, lineId)).join("")}
        <p class="flag-card__why"><span class="flag-card__label">Why this flag?</span> ${escapeHtml(flag.why)}</p>
        ${flag.confidence === "Low"
          ? `<p class="flag-card__unsure">
              <span class="icon" aria-hidden="true">help</span>
              <span>The AI is unsure. Read the turn before deciding.</span>
            </p>`
          : ""}
        <button type="button" class="btn btn--text btn--icon-leading" data-action="toggle-context" data-flag="${flag.id}"
          aria-expanded="${contextOpen}" aria-controls="${id}-context" data-focus-key="context-${flag.id}">
          <span class="icon" aria-hidden="true">${contextOpen ? "expand_less" : "expand_more"}</span>
          <span>${contextOpen ? "Hide context" : "Show in context"}</span>
        </button>
        <div class="flag-card__context" id="${id}-context"${contextOpen ? "" : " hidden"}>
          ${renderFlagContext(run, flag)}
        </div>
        ${renderDecision(flag)}
      </article>`;
  }

  // A spec line chip, like K2, that expands to show the line's full text.
  function renderCiteChip(flag, lineId) {
    const open = Boolean(state.citesOpen[`${flag.id}:${lineId}`]);
    const key = `cite-${flag.id}-${lineId}`;
    return `
      <button type="button" class="chip chip--assist chip--icon-trailing" data-action="toggle-cite"
        data-flag="${flag.id}" data-line="${escapeHtml(lineId)}" aria-expanded="${open}"
        aria-controls="${escapeHtml(key)}-text" data-focus-key="${escapeHtml(key)}"
        data-tooltip="${escapeHtml(lineTip(lineId))}">
        <span>${escapeHtml(lineId)}<span class="visually-hidden">: ${escapeHtml(LINE_MEANINGS[lineId[0]])}</span></span>
        <span class="icon" aria-hidden="true">${open ? "expand_less" : "expand_more"}</span>
      </button>`;
  }

  function renderCiteText(flag, lineId) {
    const open = Boolean(state.citesOpen[`${flag.id}:${lineId}`]);
    return `
      <p class="flag-card__cite-text" id="cite-${flag.id}-${escapeHtml(lineId)}-text"${open ? "" : " hidden"}>
        <span class="flag-card__label">${escapeHtml(lineId)}.</span> ${escapeHtml(specLineText(lineId))}
      </p>`;
  }

  // The turn in context: Alex's line, the reply with the evidence marked,
  // and the full text of every spec line the flag cites.
  function renderFlagContext(run, flag) {
    const userLine = state.scenario.userLines.find((line) => line.turn === flag.turn);
    const reply = run.replies.find((candidate) => candidate.turn === flag.turn);
    const specLines = flag.cites.map(
      (lineId) => `
        <p class="context-line">
          <span class="context-line__speaker">Spec ${escapeHtml(lineId)}</span>
          ${escapeHtml(specLineText(lineId))}
        </p>`,
    );
    return `
      <p class="context-line">
        <span class="context-line__speaker">${escapeHtml(state.scenario.userName)}, turn ${flag.turn}</span>
        ${escapeHtml(userLine ? userLine.text : "")}
      </p>
      <p class="context-line">
        <span class="context-line__speaker">${escapeHtml(state.scenario.characterName)}, turn ${flag.turn}</span>
        <span class="keep-lines">${highlight(reply ? reply.text : "", [flag.evidence.toLowerCase()])}</span>
      </p>
      ${specLines.join("")}`;
  }

  // The bottom of a card: Agree and Override, the override reason field, or
  // the creator's decision with Undo.
  function renderDecision(flag) {
    const decision = state.decisions[flag.id];
    const undo = `
      <button type="button" class="btn btn--text" data-action="undo-decision" data-flag="${flag.id}" data-focus-key="undo-${flag.id}">
        Undo<span class="visually-hidden">: ${escapeHtml(flagTitle(flag))}</span>
      </button>`;

    if (decision && decision.verdict === "agreed") {
      return `
        <div class="flag-card__actions">
          <p class="flag-card__status">
            <span class="icon icon--filled" aria-hidden="true">check_circle</span>
            <span>Agreed by you</span>
          </p>
          ${undo}
        </div>`;
    }

    if (decision && decision.verdict === "overridden") {
      return `
        <div class="flag-card__actions">
          <p class="flag-card__status">
            <span class="icon" aria-hidden="true">block</span>
            <span>Overridden by you</span>
          </p>
          <p class="flag-card__reason"><span class="flag-card__label">Your reason:</span> ${escapeHtml(decision.reason)}</p>
          ${undo}
        </div>`;
    }

    if (flag.id in state.overrideDrafts) {
      const draft = state.overrideDrafts[flag.id];
      const ready = countWords(draft) >= MIN_REASON_WORDS;
      return `
        <div class="flag-card__override">
          <div class="text-field">
            <textarea class="text-field__input" id="reason-${flag.id}" rows="2" placeholder=" "
              aria-describedby="reason-${flag.id}-help" data-reason-for="${flag.id}"
              data-focus-key="reason-${flag.id}">${escapeHtml(draft)}</textarea>
            <label class="text-field__label" for="reason-${flag.id}">Why is the AI wrong?</label>
            <p class="text-field__support" id="reason-${flag.id}-help">Use at least ${MIN_REASON_WORDS} words.</p>
          </div>
          <div class="flag-card__actions">
            <button type="button" class="btn btn--filled" data-action="save-override" data-flag="${flag.id}"
              aria-disabled="${!ready}" data-focus-key="save-${flag.id}">Save</button>
            <button type="button" class="btn btn--text" data-action="cancel-override" data-flag="${flag.id}"
              data-focus-key="cancel-${flag.id}">Cancel</button>
          </div>
        </div>`;
    }

    // Evidence first: Agree stays off until the creator has seen the turn.
    // aria-disabled (not disabled) keeps it reachable, with the reason linked.
    const seen = Boolean(state.contextSeen[flag.id]);
    return `
      <div class="flag-card__actions">
        <button type="button" class="btn btn--outlined" data-action="agree" data-flag="${flag.id}"
          aria-disabled="${!seen}"${seen ? "" : ` aria-describedby="agree-hint-${flag.id}"`}
          data-focus-key="agree-${flag.id}">Agree</button>
        <button type="button" class="btn btn--outlined" data-action="start-override" data-flag="${flag.id}"
          data-focus-key="override-${flag.id}">Override</button>
        ${seen ? "" : `<p class="flag-card__hint" id="agree-hint-${flag.id}">Show the turn in context before you agree.</p>`}
      </div>`;
  }

  function renderNotChecked(run) {
    if (run.notChecked.length === 0) return "";
    const items = run.notChecked.map((item, index) => {
      const key = `${run.id}:${index}`;
      const boxId = `reviewed-${run.id}-${index}`;
      return `
        <div class="not-checked__item">
          <p><span class="flag-card__label">${escapeHtml(item.topic)}.</span> ${escapeHtml(item.text)}</p>
          <label class="checkbox" for="${boxId}">
            <input type="checkbox" id="${boxId}" data-reviewed="${key}" data-focus-key="${boxId}"${state.notCheckedReviewed[key] ? " checked" : ""}>
            <span>Mark as reviewed<span class="visually-hidden">: ${escapeHtml(item.topic)}</span></span>
          </label>
        </div>`;
    });
    return `
      <section class="card card--outlined not-checked" aria-labelledby="not-checked-title">
        <h3 class="not-checked__title" id="not-checked-title">
          <span class="icon" aria-hidden="true">visibility_off</span>
          <span>Not checked by the AI</span>
        </h3>
        ${items.join("")}
      </section>`;
  }

  // The compact conversation. Flagged turns get a colored border, a flag
  // icon, and the word "Flagged", plus the creator's decision once made.
  function renderConversation(run, flags) {
    const turns = state.scenario.userLines.map((line) => {
      const reply = run.replies.find((candidate) => candidate.turn === line.turn);
      const turnFlags = flags.filter((flag) => flag.turn === line.turn);
      const verdicts = turnFlags.map((flag) => verdictOf(state.decisions, flag));
      let status = "";
      if (turnFlags.length > 0 && verdicts.every((verdict) => verdict === "agreed")) status = "Agreed by you";
      if (turnFlags.length > 0 && verdicts.every((verdict) => verdict === "overridden")) status = "Overridden by you";

      let classes = "convo-turn";
      if (turnFlags.length > 0) classes += " convo-turn--flagged";
      if (status === "Overridden by you") classes += " convo-turn--overridden";
      const evidence = turnFlags.map((flag) => flag.evidence.toLowerCase());

      return `
        <li class="${classes}" data-turn="${line.turn}"${state.reviewTurn === line.turn ? ' aria-current="true"' : ""}>
          <p class="convo-turn__head">
            <span>Turn ${line.turn}</span>
            ${turnFlags.length > 0
              ? `<span class="convo-turn__flag"><span class="icon icon--filled" aria-hidden="true">flag</span>Flagged</span>`
              : ""}
            ${status ? `<span class="convo-turn__status">${status}</span>` : ""}
          </p>
          <p class="convo-turn__line"><span class="convo-turn__speaker">${escapeHtml(state.scenario.userName)}:</span> ${escapeHtml(line.text)}</p>
          <p class="convo-turn__line"><span class="convo-turn__speaker">${escapeHtml(state.scenario.characterName)}:</span> <span class="keep-lines">${highlight(reply ? reply.text : "", evidence)}</span></p>
        </li>`;
    });

    return `
      <div class="review__conversation">
        <div class="review__convo-head">
          <h2 class="review__convo-title" id="review-convo-title">Conversation</h2>
          <p class="review__convo-run">${escapeHtml(runLabel(run))}</p>
        </div>
        <div class="review__convo-scroll" tabindex="0" role="region" aria-labelledby="review-convo-title"
          data-scroll-key="review-convo">
          <ol class="convo">
            <li class="convo__system">Turn 1: character spec ${escapeHtml(run.specVersion)} loaded</li>
            ${turns.join("")}
          </ol>
        </div>
      </div>`;
  }

  // Scrolls the conversation (only its own box, never the page) so the
  // highlighted turn is in view.
  function revealTurn(body) {
    const scroller = body.querySelector(".review__convo-scroll");
    const turn = scroller ? scroller.querySelector('[aria-current="true"]') : null;
    if (!turn) return;
    const above = turn.offsetTop < scroller.scrollTop;
    const below = turn.offsetTop + turn.offsetHeight > scroller.scrollTop + scroller.clientHeight;
    if (above || below) scroller.scrollTop = turn.offsetTop - 8;
  }

  // Screen readers hear the new summary after each decision, and the
  // rubber-stamp check when it applies.
  function announceReview() {
    const flags = selectedRun().flags;
    const summary = reviewSummary(flags, state.decisions);
    announce(agreedWithEvery(flags, state.decisions) ? `${summary} ${RUBBER_STAMP_MESSAGE}` : summary);
  }

  function diagnoseBody() {
    return panelFor("diagnose").querySelector("[data-screen-body]");
  }

  actions["filter-flags"] = (chip) => {
    state.flagFilter = chip.dataset.filter;
    refresh();
  };

  actions["toggle-cite"] = (chip) => {
    const key = `${chip.dataset.flag}:${chip.dataset.line}`;
    state.citesOpen[key] = !state.citesOpen[key];
    refresh();
  };

  actions["toggle-context"] = (button) => {
    const flagId = button.dataset.flag;
    const opening = !state.contextOpen[flagId];
    state.contextOpen[flagId] = opening;
    if (opening) {
      state.contextSeen[flagId] = true;
      state.reviewTurn = findFlag(flagId).flag.turn;
    }
    refresh();
    if (opening) revealTurn(diagnoseBody());
  };

  actions["agree"] = (button) => {
    const flagId = button.dataset.flag;
    if (!state.contextSeen[flagId]) {
      // Not yet: send the creator to the evidence instead.
      diagnoseBody().querySelector(`[data-focus-key="context-${flagId}"]`).focus();
      return;
    }
    state.decisions[flagId] = { verdict: "agreed" };
    refresh({ focusKey: `undo-${flagId}` });
    announceReview();
  };

  actions["start-override"] = (button) => {
    const flagId = button.dataset.flag;
    state.overrideDrafts[flagId] = "";
    refresh({ focusKey: `reason-${flagId}` });
  };

  function cancelOverride(flagId) {
    delete state.overrideDrafts[flagId];
    refresh({ focusKey: `override-${flagId}` });
  }

  actions["cancel-override"] = (button) => {
    cancelOverride(button.dataset.flag);
  };

  actions["save-override"] = (button) => {
    const flagId = button.dataset.flag;
    const reason = (state.overrideDrafts[flagId] || "").trim();
    if (countWords(reason) < MIN_REASON_WORDS) {
      diagnoseBody().querySelector(`[data-focus-key="reason-${flagId}"]`).focus();
      return;
    }
    state.decisions[flagId] = { verdict: "overridden", reason };
    delete state.overrideDrafts[flagId];
    refresh({ focusKey: `undo-${flagId}` });
    announceReview();
  };

  actions["undo-decision"] = (button) => {
    const flagId = button.dataset.flag;
    delete state.decisions[flagId];
    refresh({ focusKey: `agree-${flagId}` });
    announceReview();
  };

  // 3.4 Compare runs (Repair) -----------------------------------------------
  // Same script, same spec, different results: where each tool's chat broke,
  // the replies side by side, and a next step for every spec line that broke
  // in every chat, which leads back to the Spec editor (Repair closes the loop
  // to Define). It compares the chats of the scenario on screen, however many
  // tools ran it. A break is any flag the creator hasn't overridden on Flag
  // review, so the creator's calls shape this screen.

  // "break" when a flag on the turn still stands, "overridden" when the
  // creator overrode every flag on it, "clean" when nothing was flagged.
  function turnStatus(run, turn, decisions) {
    const turnFlags = run.flags.filter((flag) => flag.turn === turn);
    if (turnFlags.length === 0) return "clean";
    return turnFlags.some((flag) => verdictOf(decisions, flag) !== "overridden") ? "break" : "overridden";
  }

  function breaksIn(run, decisions) {
    return run.flags.filter((flag) => verdictOf(decisions, flag) !== "overridden");
  }

  function firstBreakText(run, decisions) {
    const turns = breaksIn(run, decisions).map((flag) => flag.turn);
    return turns.length > 0 ? `First break: turn ${Math.min(...turns)}.` : "No breaks.";
  }

  // Spec lines that a standing flag cites in every run, in spec order.
  function linesBrokenInAll(runs, decisions, specOrder) {
    const citedPerRun = runs.map((run) => new Set(breaksIn(run, decisions).flatMap((flag) => flag.cites)));
    return specOrder.filter((lineId) => citedPerRun.every((cited) => cited.has(lineId)));
  }

  // "v1" becomes "v2".
  function nextVersion(version) {
    const number = parseInt(String(version).replace(/^v/, ""), 10);
    return Number.isNaN(number) ? "the next version" : `v${number + 1}`;
  }

  // "both chats" for two, "all 3 chats" for three or more.
  function chatsText(count) {
    if (count === 1) return "the one chat";
    return count === 2 ? "both chats" : `all ${count} chats`;
  }

  // While any flag is still open, this comparison counts it as a break, so
  // the creator hears that before trusting the numbers.
  function renderReviewNotice() {
    const open = openFlags().length;
    if (open === 0) {
      return `
        <p class="compare-done">
          <span class="icon icon--filled" aria-hidden="true">task_alt</span>
          <span>Every flag has your call, so this comparison reflects your review.</span>
        </p>`;
    }
    const one = open === 1;
    return `
      <div class="card card--filled compare-todo">
        <span class="icon" aria-hidden="true">pending_actions</span>
        <p class="compare-todo__text">
          ${open} ${one ? "flag still needs" : "flags still need"} your call on Flag review.
          Until you decide, ${one ? "it counts as a break" : "they count as breaks"} here.
        </p>
        <button type="button" class="btn btn--filled" data-action="review-open-flags">${one ? "Review it" : "Review them"}</button>
      </div>`;
  }

  function renderCompare(body) {
    const runs = scenarioChats();
    const specOrder = state.spec.sections.flatMap((section) => section.lines.map((line) => line.id));
    const broken = linesBrokenInAll(runs, state.decisions, specOrder);

    body.innerHTML = `
      <div class="compare">
        ${renderReviewNotice()}
        <section aria-labelledby="drift-title">
          <h2 class="compare__heading" id="drift-title">Where each chat broke</h2>
          <div class="drift">${runs.map(renderDriftRow).join("")}</div>
          <ul class="drift__legend">
            <li><span class="drift__turn drift__turn--sample" aria-hidden="true"></span>Clean turn</li>
            <li>
              <span class="drift__turn drift__turn--break drift__turn--sample" aria-hidden="true">
                <span class="icon icon--filled">flag</span>
              </span>Break
            </li>
            <li><span class="drift__turn drift__turn--overridden drift__turn--sample" aria-hidden="true"></span>Flag you overrode</li>
          </ul>
        </section>

        <section aria-labelledby="side-by-side-title">
          <h2 class="compare__heading" id="side-by-side-title">Turn by turn</h2>
          ${renderCompareTable(runs)}
        </section>

        <div class="compare__next">
          ${broken.length > 0
            ? broken.map((lineId) => renderNextStep(lineId, runs.length)).join("")
            : `<p class="card card--outlined">No spec line broke in ${chatsText(runs.length)}.</p>`}
        </div>
      </div>`;
  }

  // One small square per turn: outlined when clean, filled with a flag icon
  // when it broke, dashed when the creator overrode its flag.
  function renderDriftRow(run) {
    const lines = state.scenario.userLines;
    const squares = lines.map((line) => {
      const status = turnStatus(run, line.turn, state.decisions);
      const said = { clean: "clean", break: "break", overridden: "flag overridden by you" }[status];
      return `
        <li class="drift__turn${status === "clean" ? "" : ` drift__turn--${status}`}">
          ${status === "break" ? '<span class="icon icon--filled" aria-hidden="true">flag</span>' : ""}
          <span><span class="visually-hidden">Turn </span>${line.turn}<span class="visually-hidden">, ${said}</span></span>
        </li>`;
    });
    const range = `turns ${lines[0].turn} to ${lines[lines.length - 1].turn}`;
    return `
      <div class="drift__row">
        <p class="drift__run">${escapeHtml(runLabel(run))}</p>
        <ol class="drift__strip" aria-label="${escapeHtml(runLabel(run))}, ${range}">${squares.join("")}</ol>
        <p class="drift__first">${firstBreakText(run, state.decisions)}</p>
      </div>`;
  }

  // The chats side by side: one row per turn with Alex's line, then each
  // chat's reply. Replies that broke are highlighted, with the evidence
  // underlined.
  function renderCompareTable(runs) {
    const heads = runs.map((run) => `<th scope="col">${escapeHtml(runLabel(run))}</th>`);
    const rows = state.scenario.userLines.map(
      (line) => `
        <tr>
          <th scope="row">
            <span class="compare-table__turn">Turn ${line.turn}</span>
            <span><span class="compare-table__speaker">${escapeHtml(state.scenario.userName)}:</span> ${escapeHtml(line.text)}</span>
          </th>
          ${runs.map((run) => renderCompareCell(run, line.turn)).join("")}
        </tr>`,
    );
    return `
      <div class="compare-table-wrap" tabindex="0" role="region" aria-labelledby="side-by-side-title">
        <table class="compare-table" style="min-width: ${12 + runs.length * 14}rem">
          <thead><tr><th scope="col">Turn</th>${heads.join("")}</tr></thead>
          <tbody>${rows.join("")}</tbody>
        </table>
      </div>`;
  }

  function renderCompareCell(run, turn) {
    const reply = run.replies.find((candidate) => candidate.turn === turn);
    const status = turnStatus(run, turn, state.decisions);
    const standing = breaksIn(run, state.decisions).filter((flag) => flag.turn === turn);

    let label = "";
    if (status === "break") {
      const types = [...new Set(standing.map((flag) => flag.type.toLowerCase()))].join(", ");
      const cites = [...new Set(standing.flatMap((flag) => flag.cites))].join(", ");
      label = `
        <p class="compare-reply__label">
          <span class="icon icon--filled" aria-hidden="true">flag</span>
          <span>Flagged: ${escapeHtml(types)}, ${escapeHtml(cites)}</span>
        </p>`;
    } else if (status === "overridden") {
      label = '<p class="compare-reply__label compare-reply__label--quiet">Flag overridden by you</p>';
    }

    const evidence = standing.map((flag) => flag.evidence.toLowerCase());
    return `
      <td class="compare-reply${status === "break" ? " compare-reply--break" : ""}">
        ${label}
        <p class="keep-lines">${highlight(reply ? reply.text : "", evidence)}</p>
      </td>`;
  }

  function renderNextStep(lineId, chatCount) {
    return `
      <article class="card card--filled next-step" aria-labelledby="next-step-${escapeHtml(lineId)}">
        <h2 class="next-step__title" id="next-step-${escapeHtml(lineId)}">
          <span class="icon" aria-hidden="true">lightbulb</span>
          <span>Next step</span>
        </h2>
        <p>${escapeHtml(lineId)} broke in ${chatsText(chatCount)}. Consider making it more specific in ${nextVersion(state.spec.version)}.</p>
        <button type="button" class="btn btn--filled btn--icon-leading" data-action="open-spec-line"
          data-line="${escapeHtml(lineId)}" data-focus-key="open-${escapeHtml(lineId)}">
          <span class="icon" aria-hidden="true">edit_note</span>
          <span>Open ${escapeHtml(lineId)} in the spec</span>
        </button>
      </article>`;
  }

  actions["open-spec-line"] = (button) => {
    const note = `From Compare runs: this line broke in ${chatsText(scenarioChats().length)}.`;
    state.specHighlight = { lineId: button.dataset.line, note };
    goToScreen("define");
  };

  // "Review them": Flag review opens at the first flag still waiting for a call.
  actions["review-open-flags"] = () => {
    const [first] = openFlags();
    if (!first) return;
    if (first.run.id !== state.runId) changeRunSetup({ runId: first.run.id });
    state.openFlagId = first.flag.id;
    goToScreen("diagnose");
  };

  // 4. Router and tabs =====================================================
  // The URL hash (#define, #run, #diagnose, #compare) decides which screen
  // shows, so Back and Forward work and each screen has its own link.

  const APP_NAME = "Character Consistency Workbench";
  const DEFAULT_SCREEN = "define";
  const tablist = document.querySelector('[role="tablist"]');
  const tabs = Array.from(tablist.querySelectorAll('[role="tab"]'));

  let currentScreen = null;
  let navigatingFromTab = false;

  function panelFor(id) {
    return document.getElementById(`panel-${id}`);
  }

  function isScreen(id) {
    return Object.prototype.hasOwnProperty.call(SCREENS, id);
  }

  function screenFromHash() {
    const id = location.hash.slice(1);
    return isScreen(id) ? id : null;
  }

  // Screens call this to send the creator to another screen, for example
  // from a spec line to a flag that cites it.
  function goToScreen(id, { fromTab = false } = {}) {
    if (!isScreen(id) || id === currentScreen) return;
    navigatingFromTab = fromTab;
    location.hash = id;
  }

  function showScreen(id, { moveFocus = false } = {}) {
    const isChange = currentScreen !== null && currentScreen !== id;
    currentScreen = id;
    hideTooltip();
    // The CSS keys a few screen-wide rules off this, like scroll padding.
    document.documentElement.dataset.screen = id;

    tabs.forEach((tab) => {
      const selected = tab.dataset.screen === id;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
      if (selected) keepTabInView(tab);
    });
    Object.keys(SCREENS).forEach((key) => {
      panelFor(key).hidden = key !== id;
    });
    document.title = `${SCREENS[id].title} | ${APP_NAME}`;

    // A screen can return an element to land on, like the flag that "Go to
    // flag" asked for. Otherwise focus goes to the heading when it should move.
    const landing = renderScreen(id);
    if (isChange) window.scrollTo(0, 0);
    if (landing) {
      scrollBelowHeader(landing);
      landing.focus({ preventScroll: true });
    } else if (moveFocus) {
      panelFor(id).querySelector(".screen__title").focus({ preventScroll: true });
    }
  }

  // Every redraw also refreshes the to-do badge on the Flag review tab.
  function renderScreen(id) {
    const landing = SCREENS[id].render(panelFor(id).querySelector("[data-screen-body]"));
    updateTodoBadge();
    return landing;
  }

  // Scrolls the page so an element sits just below the sticky header, and
  // below a sticky bar on the same screen, like the one on Flag review. On
  // phones the header scrolls away, so only the gap counts there.
  function scrollBelowHeader(element) {
    const headerSticks = getComputedStyle(header).position === "sticky";
    let offset = (headerSticks ? header.offsetHeight : 0) + 16;
    const bar = element.closest("[data-screen-body]").querySelector(".review__bar-wrap");
    if (bar && getComputedStyle(bar).position === "sticky") offset += bar.offsetHeight;
    window.scrollTo(0, element.getBoundingClientRect().top + window.scrollY - offset);
  }

  // Redraws the current screen after a state change. Boxes marked with
  // data-scroll-key keep their scroll position. Focus goes to focusKey if
  // given, else back to the control that had it (matched by data-focus-key),
  // else to the screen heading if that control is gone.
  function refresh({ focusKey = null } = {}) {
    const panel = panelFor(currentScreen);
    const body = panel.querySelector("[data-screen-body]");
    const active = document.activeElement;
    const focusWasInBody = body.contains(active);
    const key = focusKey || (focusWasInBody ? active.getAttribute("data-focus-key") : null);
    const scrolls = Array.from(body.querySelectorAll("[data-scroll-key]"), (box) => [box.dataset.scrollKey, box.scrollTop]);

    // A redraw replaces the element a tooltip belongs to, so the tooltip goes.
    hideTooltip();
    renderScreen(currentScreen);

    scrolls.forEach(([scrollKey, top]) => {
      const box = body.querySelector(`[data-scroll-key="${CSS.escape(scrollKey)}"]`);
      if (box) box.scrollTop = top;
    });
    if (!focusWasInBody && !focusKey) return;
    const target = key ? body.querySelector(`[data-focus-key="${CSS.escape(key)}"]`) : null;
    if (target) target.focus();
    else panel.querySelector(".screen__title").focus({ preventScroll: true });
  }

  function onHashChange() {
    const id = screenFromHash();
    if (!id) {
      location.replace(`#${DEFAULT_SCREEN}`);
      return;
    }
    // A tab keeps focus on itself. Any other way of arriving (Back, Forward,
    // a link inside a screen) moves focus to the new screen's heading.
    const moveFocus = !navigatingFromTab;
    navigatingFromTab = false;
    if (id !== currentScreen) showScreen(id, { moveFocus });
  }

  // Tabs follow the ARIA tabs pattern with manual activation, like Material
  // Web's tabs: arrow keys, Home, and End move focus; Enter or Space opens.
  tablist.addEventListener("click", (event) => {
    const tab = event.target.closest('[role="tab"]');
    if (tab) goToScreen(tab.dataset.screen, { fromTab: true });
  });

  tablist.addEventListener("keydown", (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    const index = tabs.indexOf(document.activeElement);
    if (index === -1) return;
    const last = tabs.length - 1;
    const next = {
      ArrowRight: index === last ? 0 : index + 1,
      ArrowLeft: index === 0 ? last : index - 1,
      Home: 0,
      End: last,
    }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    tabs[next].focus();
  });

  // On phones the tab row scrolls sideways; keep the selected tab visible.
  function keepTabInView(tab) {
    const left = tab.offsetLeft;
    const right = left + tab.offsetWidth;
    if (left < tablist.scrollLeft) {
      tablist.scrollLeft = left;
    } else if (right > tablist.scrollLeft + tablist.clientWidth) {
      tablist.scrollLeft = right - tablist.clientWidth;
    }
  }

  // 5. Dialogs, tooltips, snackbar, and top app bar ========================

  let dialogOpenedAt = 0;

  // Opens a modal dialog or side sheet. When it closes, onClose gets the
  // value of the button that closed it ("" for Esc or the scrim), and focus
  // goes back to the control that opened it.
  function openDialog(dialog, opener, onClose) {
    dialog.returnValue = "";
    dialog.addEventListener(
      "close",
      () => {
        if (onClose) onClose(dialog.returnValue);
        if (opener) opener.focus();
      },
      { once: true },
    );
    dialogOpenedAt = Date.now();
    dialog.showModal();
  }

  // M3 dialogs and sheets also close on a click on the scrim around them.
  // The press has to start on the scrim, and the second click of the double
  // click that opened the dialog doesn't count.
  document.querySelectorAll("dialog").forEach((dialog) => {
    let pressedScrim = false;
    const isOnScrim = (event) => {
      if (event.target !== dialog) return false;
      const box = dialog.getBoundingClientRect();
      return (
        event.clientX < box.left || event.clientX > box.right ||
        event.clientY < box.top || event.clientY > box.bottom
      );
    };
    dialog.addEventListener("pointerdown", (event) => {
      pressedScrim = isOnScrim(event) && Date.now() - dialogOpenedAt > 400;
    });
    dialog.addEventListener("click", (event) => {
      if (pressedScrim && isOnScrim(event)) dialog.close();
      pressedScrim = false;
    });
  });

  // Clicks on [data-action] controls anywhere on the page, sheets included.
  document.addEventListener("click", (event) => {
    const control = event.target.closest("[data-action]");
    const handler = control && actions[control.dataset.action];
    if (handler) handler(control, event);
  });

  const resetButton = document.getElementById("reset-demo");
  const resetDialog = document.getElementById("reset-dialog");

  resetButton.addEventListener("click", () => {
    openDialog(resetDialog, resetButton, (choice) => {
      if (choice !== "reset") return;
      stopPlayback();
      state = createInitialState();
      refresh();
      showSnackbar("Demo reset. Everything is back to the starting data.");
    });
  });

  const codesDialog = document.getElementById("codes-dialog");

  // "What do the codes mean?" in the top bar. Escape, Close, or a click on
  // the scrim closes it, and focus goes back to the button.
  actions["show-codes"] = (button) => {
    openDialog(codesDialog, button);
  };

  // Plain tooltips (M3) for every element with data-tooltip: the spec line
  // chips and the Scenario dropdown. A tooltip shows after a short hover, or
  // right away on keyboard focus. Escape, any other key but Tab, a click, a
  // scroll, or leaving the element hides it, and the pointer can move onto
  // the tooltip without it closing. Escape still closes a dialog as usual.
  const tooltip = document.getElementById("tooltip");
  let tooltipTarget = null;
  let hoverTarget = null;
  let tooltipTimer = 0;
  let lastPointerDown = 0;

  function showTooltip(target) {
    clearTimeout(tooltipTimer);
    tooltipTarget = target;
    // Inside an open dialog the tooltip has to live in the dialog too, or the
    // dialog would cover it.
    const host = target.closest("dialog[open]") || document.body;
    if (tooltip.parentElement !== host) host.appendChild(tooltip);
    tooltip.textContent = target.dataset.tooltip;
    tooltip.hidden = false;
    const box = target.getBoundingClientRect();
    const tip = tooltip.getBoundingClientRect();
    const below = box.bottom + 4;
    const above = box.top - tip.height - 4;
    // Below by default, or above when the element asks (data-tooltip-place),
    // flipping if there's no room on that side.
    let top = target.dataset.tooltipPlace === "above" && above >= 8 ? above : below;
    if (top === below && below + tip.height > window.innerHeight - 8) top = above;
    const left = Math.min(Math.max(8, box.left + (box.width - tip.width) / 2), window.innerWidth - tip.width - 8);
    tooltip.style.top = `${top}px`;
    tooltip.style.left = `${left}px`;
  }

  function hideTooltip() {
    clearTimeout(tooltipTimer);
    tooltipTarget = null;
    hoverTarget = null;
    tooltip.hidden = true;
  }

  document.addEventListener("mouseover", (event) => {
    const target = event.target.closest("[data-tooltip]");
    if (event.target.closest("#tooltip") || (target && target === hoverTarget)) {
      // Back on the element, or onto its tooltip: keep it showing.
      if (tooltipTarget) clearTimeout(tooltipTimer);
      return;
    }
    if (!target) return;
    hoverTarget = target;
    clearTimeout(tooltipTimer);
    tooltipTimer = setTimeout(() => showTooltip(target), 300);
  });

  document.addEventListener("mouseout", (event) => {
    const from = event.target.closest("[data-tooltip], #tooltip");
    if (!from || (event.relatedTarget && from.contains(event.relatedTarget))) return;
    // A short wait, so the pointer can cross onto the tooltip.
    clearTimeout(tooltipTimer);
    tooltipTimer = setTimeout(hideTooltip, 150);
  });

  document.addEventListener("focusin", (event) => {
    const target = event.target.closest("[data-tooltip]");
    const fromPointer = Date.now() - lastPointerDown < 500;
    if (target && !fromPointer && target.matches(":focus-visible")) showTooltip(target);
  });

  document.addEventListener("focusout", (event) => {
    if (event.target === tooltipTarget) hideTooltip();
  });

  document.addEventListener(
    "keydown",
    (event) => {
      if (tooltipTarget && event.key !== "Tab" && event.key !== "Shift") hideTooltip();
    },
    true,
  );

  document.addEventListener(
    "pointerdown",
    (event) => {
      lastPointerDown = Date.now();
      if (!event.target.closest("#tooltip")) hideTooltip();
    },
    true,
  );

  window.addEventListener("scroll", () => tooltipTarget && hideTooltip(), { capture: true, passive: true });
  window.addEventListener("resize", hideTooltip);

  const snackbar = document.getElementById("snackbar");
  let snackbarTimer = 0;

  // Shows a short message for 4 seconds. The snackbar is a polite live
  // region, so screen readers read the message too.
  function showSnackbar(message) {
    clearTimeout(snackbarTimer);
    snackbar.textContent = "";
    // The short pause lets screen readers announce a repeated message again.
    snackbarTimer = setTimeout(() => {
      snackbar.textContent = message;
      snackbar.classList.add("is-visible");
      snackbarTimer = setTimeout(hideSnackbar, 4000);
    }, 50);
  }

  function hideSnackbar() {
    snackbar.classList.remove("is-visible");
    snackbarTimer = setTimeout(() => {
      snackbar.textContent = "";
    }, 300);
  }

  const announcer = document.getElementById("announcer");
  let announceTimer = 0;

  // Tells screen readers about a change on a screen that just redrew, like
  // the new review summary after a decision. Redrawn text isn't announced
  // by itself, so it goes through this hidden live region.
  function announce(message) {
    clearTimeout(announceTimer);
    announcer.textContent = "";
    announceTimer = setTimeout(() => {
      announcer.textContent = message;
    }, 50);
  }

  // M3: the top app bar changes color once content scrolls under it.
  const header = document.getElementById("app-header");

  function updateHeader() {
    header.classList.toggle("is-scrolled", window.scrollY > 0);
  }

  window.addEventListener("scroll", updateHeader, { passive: true });

  // Sticky parts of a screen sit just below the header, so the CSS gets its
  // height as --app-header-height (it changes when the bar wraps on phones).
  if ("ResizeObserver" in window) {
    new ResizeObserver(() => {
      document.documentElement.style.setProperty("--app-header-height", `${header.offsetHeight}px`);
    }).observe(header);
  }

  // Theme: the M3 baseline light or dark scheme. It follows the system
  // setting until the creator picks one with the Light and Dark buttons.
  // Like everything else it lives in memory, but Reset demo leaves it alone.
  const darkQuery = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  let themePicked = false;

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    document.querySelectorAll('[data-action="set-theme"]').forEach((button) => {
      const selected = button.dataset.themeChoice === theme;
      button.setAttribute("aria-pressed", String(selected));
      // M3 segmented buttons: the selected one shows a check, not just a fill.
      button.querySelector(".icon").textContent = selected ? "check" : button.dataset.icon;
    });
  }

  actions["set-theme"] = (button) => {
    themePicked = true;
    applyTheme(button.dataset.themeChoice);
  };

  if (darkQuery && darkQuery.addEventListener) {
    darkQuery.addEventListener("change", () => {
      if (!themePicked) applyTheme(darkQuery.matches ? "dark" : "light");
    });
  }

  // Icons stay hidden until the Material Symbols font has loaded, so an
  // offline page never shows raw icon names such as "restart_alt".
  function revealIconsWhenReady() {
    const root = document.documentElement;
    if (!document.fonts || !document.fonts.load) {
      root.classList.add("icons-ready");
      return;
    }
    document.fonts
      .load('24px "Material Symbols Outlined"', "flag")
      .then((faces) => {
        if (faces.length > 0) root.classList.add("icons-ready");
      })
      .catch(() => {});
  }

  // 6. Start ===============================================================

  applyTheme(darkQuery && darkQuery.matches ? "dark" : "light");
  window.addEventListener("hashchange", onHashChange);
  revealIconsWhenReady();
  updateHeader();

  const firstScreen = screenFromHash();
  if (!firstScreen) location.replace(`#${DEFAULT_SCREEN}`);
  showScreen(firstScreen || DEFAULT_SCREEN);
})();
