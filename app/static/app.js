/*
  Character Consistency Workbench: CP3 app, first copied from the CP2 prototype

  A plain script (no modules, no build step). Every screen talks to the
  workbench server, by way of api.js: specs, live chats, imported chats, their
  checks (the automatic checks, the AI judge, and its follow-up re-checks),
  and the creator's calls on each flag are saved there, so reloading the page
  keeps them all.

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

  // Everything a screen draws from. The server's data arrives through api.js.
  const state = createInitialState();

  // Counts spec requests, so only the newest one changes the screen.
  let specRequest = 0;
  // Gives each new line in the Spec editor form its own key.
  let newLineCount = 0;

  function createInitialState() {
    return {
      // Spec editor: the version on screen, from the server (see loadSpec).
      // specLoad.status is "loading", "ready", or "failed". specDraft holds
      // the form while the creator edits, and is null otherwise.
      specLoad: { status: "loading", message: "" },
      specView: null,
      specDraft: null,
      specSaving: false,
      specSaveError: null, // { message, field } from the last save that failed
      // Spec editor: the text in the search field.
      specQuery: "",
      // Set by "Go to flag" on the Spec editor; Flag review opens at this flag.
      openFlagId: null,
      // Run a conversation: the saved chats (live runs and imports) from the
      // server, the one on screen, and the next run's scenario and model.
      chats: [],
      chatsLoad: { status: "loading", message: "" },
      chatId: null,
      chat: null,
      runSetup: { scenarioId: null, modelId: null },
      runStarting: false,
      // The run streaming now: { chatId, phase ("waiting", "writing", or
      // "stopping"), turn, text so far, waitSeconds, scripted, stopRequested }.
      live: null,
      // The last turn that failed: { chatId, message, retry }.
      runError: null,
      // The message being typed, per chat ID.
      drafts: {},
      // Check results, per chat ID (see 3.2.2).
      checks: {},
      // Flag review: the saved checks and the creator's calls on their flags,
      // from the server (see 3.3), or null until they load.
      review: null,
      reviewLoad: { status: "loading", message: "" },
      // The chat Flag review and Compare runs show.
      reviewChatId: null,
      // Every map below is keyed by flag ID unless noted.
      contextOpen: {}, // the turn is expanded in the card right now
      citesOpen: {}, // "flagId:lineId" when a spec line chip is expanded
      overrideDrafts: {}, // the reason being typed; a key means the field is open
      overrideTypes: {}, // the right type picked in an open override form
      overrideErrors: {}, // why the server refused a reason, until the creator types again
      // Follow-up re-checks, keyed by chat ID: { status, message, id } while
      // one runs ("running"), after its request failed ("failed"), or after
      // the server kept saved re-check id with no new call ("saved").
      rechecks: {},
      recheckDrafts: {}, // the question being typed, keyed by chat ID
      flagFilter: "All",
      reviewTurn: null, // the turn highlighted in the conversation
      // The flag whose call left no open flag in its chat, for one redraw
      // with the sparkle (see Decorations in section 5).
      sparkleFlagId: null,
      // Set by "Open K2 in the spec" on Compare runs: { lineId, note }. The
      // Spec editor highlights that line once and lands on it.
      specHighlight: null,
    };
  }

  // 2. Helpers =============================================================

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

  // Every flag of every checked chat, each paired with its chat's review.
  function allFlags() {
    return reviewChats().flatMap((item) => item.flags.map((flag) => ({ item, flag })));
  }

  // Flag IDs are numbers on the server; data-flag attributes hold them as text.
  function findFlag(flagId) {
    return allFlags().find(({ flag }) => flag.id === Number(flagId)) || null;
  }

  // Saved spec versions are numbers on the server; the screens say "v2".
  function specLabel(version) {
    return `v${version}`;
  }

  // Where a flag sits, for example "Claude (CLA-F2), turn 4".
  function flagPlace(chat, flag) {
    return `${reviewLabel(chat)}, ${numberWord(chat).toLowerCase()} ${flag.turn}`;
  }

  const CONFIDENCE_ICONS = {
    High: "signal_cellular_alt",
    Medium: "signal_cellular_alt_2_bar",
    Low: "signal_cellular_alt_1_bar",
  };

  // What the codes mean, exactly as the "What the codes mean" dialog in
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

  // The spec's setting is saved, and cited by flags, as "Setting". The
  // screens call it Scene, so nobody mistakes it for the app's Settings.
  const SCENE_CITE = "Setting";

  // How a cite shows on screen: a line ID like K2, a field like Voice, or Scene.
  function citeLabel(lineId) {
    return lineId === SCENE_CITE ? "Scene" : lineId;
  }

  // Tooltip for a spec line, like "K2: knowledge limit", or a field a flag
  // cites, like "Voice: spec field".
  function lineTip(lineId) {
    return `${citeLabel(lineId)}: ${citeMeaning(lineId)}`;
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
  // The spec as one card per section, loaded from the server. A search
  // filters the lines, each ID chip opens a side sheet with the flags that
  // cite that line, and the Version list shows older versions. Only the
  // creator changes the spec (DESIGN_SPEC 7.1): Edit spec turns the latest
  // version into a form, and saving makes the next version. Saved versions
  // never change, so runs stay pinned to the version they used.

  const citingSheet = document.getElementById("citing-flags-sheet");
  const discardSpecDialog = document.getElementById("discard-spec-dialog");
  let specCountTimer = 0;

  // Loads one version ("latest" or a number), then redraws the screens that
  // show it, unless the creator is editing. Resolves true when it showed.
  async function loadSpec(version = "latest", { focusKey = null } = {}) {
    const ticket = ++specRequest;
    let shown = false;
    try {
      const slug = state.specView ? state.specView.character.slug : await firstCharacterSlug();
      const view = await WorkbenchApi.getSpec(slug, version);
      if (ticket !== specRequest) return false;
      state.specView = view;
      state.specLoad = { status: "ready", message: "" };
      shown = true;
      // The margin art's line IDs come from the spec on screen.
      drawMarginArt();
    } catch (error) {
      if (ticket !== specRequest) return false;
      // A spotlight waiting for this load would fire much later and clear the search.
      state.specHighlight = null;
      // With a version on screen, keep it: only the switch failed.
      if (state.specView) showSnackbar(`That version didn't load. ${error.message}`);
      else state.specLoad = { status: "failed", message: error.message };
    }
    if (!state.specDraft && (currentScreen === "define" || currentScreen === "compare")) refresh({ focusKey });
    return shown;
  }

  async function firstCharacterSlug() {
    const characters = await WorkbenchApi.listCharacters();
    if (characters.length === 0) throw new Error("The server has no character spec yet.");
    return characters[0].slug;
  }

  function renderDefine(body) {
    const view = state.specView;
    const chip = panelFor("define").querySelector("[data-spec-version]");
    chip.hidden = !view;
    chip.textContent = view ? specLabel(view.version) : "";

    if (!view) {
      body.innerHTML = state.specLoad.status === "failed"
        ? `
          <div class="card card--outlined spec-empty">
            <p>The spec didn't load. ${escapeHtml(state.specLoad.message)}</p>
            <button type="button" class="btn btn--text" data-action="retry-spec" data-focus-key="retry-spec">Try again</button>
          </div>`
        : '<p class="spec-status">Loading the spec.</p>';
      return null;
    }
    return state.specDraft ? renderSpecEdit(body) : renderSpecView(body);
  }

  function renderSpecView(body) {
    const view = state.specView;
    const isLatest = view.version === view.latest;

    // Arriving from "Open K2 in the spec": clear the search so the line
    // shows, highlight it this once, and land on its chip. It waits for the
    // latest version, the one a fix would edit.
    let spotlight = null;
    if (state.specHighlight && isLatest) {
      spotlight = state.specHighlight;
      state.specHighlight = null;
      state.specQuery = "";
      if (!specLineText(spotlight.lineId, view.body)) {
        showSnackbar(`${spotlight.lineId} isn't in ${specLabel(view.version)}.`);
        spotlight = null;
      }
    }

    body.innerHTML = `
      <div class="spec-editor">
        ${view.warnings.map((warning) => renderSpecWarning(warning, isLatest)).join("")}
        ${isLatest ? "" : renderOlderVersionNotice(view)}
        <div class="spec-toolbar">
          <div class="text-field text-field--icon-leading spec-toolbar__search">
            <span class="icon text-field__icon" aria-hidden="true">search</span>
            <input class="text-field__input" type="search" id="spec-search" placeholder=" "
              value="${escapeHtml(state.specQuery)}" autocomplete="off" spellcheck="false"
              aria-describedby="spec-search-help" aria-controls="spec-results" data-focus-key="spec-search">
            <label class="text-field__label" for="spec-search">Search lines</label>
            <p class="text-field__support" id="spec-search-help">Type an ID like K2, or words like prophecy.</p>
          </div>
          <div class="spec-toolbar__version">${selectField("spec-version", "Version", versionOptions(view))}</div>
          ${isLatest
            ? `<button type="button" class="btn btn--filled btn--icon-leading" data-action="edit-spec" data-focus-key="edit-spec">
                <span class="icon" aria-hidden="true">edit</span>
                <span>Edit spec</span>
              </button>`
            : ""}
        </div>
        <p class="spec-version-info">${escapeHtml(versionInfo(view))}</p>
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
    body.querySelector("#spec-version").addEventListener("change", async (event) => {
      const version = Number(event.target.value);
      if (await loadSpec(version)) announce(`Showing ${specLabel(version)}.`);
    });
    renderSpecResults(body, { announce: false, spotlight });
    return spotlight ? body.querySelector(`[data-focus-key="line-${spotlight.lineId}"]`) : null;
  }

  // "Saved Oct 10, 2026, 4:12 PM. Note: Added a setting"
  function versionInfo(view) {
    const saved = new Date(view.created_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
    return view.note ? `Saved ${saved}. Note: ${view.note}` : `Saved ${saved}.`;
  }

  // Newest first, with the latest marked.
  function versionOptions(view) {
    return view.versions
      .map(({ version }) => {
        const label = version === view.latest ? `${specLabel(version)} (latest)` : specLabel(version);
        return `<option value="${version}"${version === view.version ? " selected" : ""}>${escapeHtml(label)}</option>`;
      })
      .join("");
  }

  // A warning from the server, like an empty Scene. On the latest version
  // it offers the fix.
  function renderSpecWarning(warning, isLatest) {
    const fix = isLatest && warning.field === "setting"
      ? '<button type="button" class="btn btn--filled" data-action="add-setting" data-focus-key="add-setting">Add a scene</button>'
      : "";
    return `
      <div class="card card--filled spec-notice spec-notice--warning">
        <span class="icon" aria-hidden="true">warning</span>
        <p class="spec-notice__text">${escapeHtml(warning.message)}</p>
        ${fix}
      </div>`;
  }

  function renderOlderVersionNotice(view) {
    return `
      <div class="card card--filled spec-notice">
        <span class="icon" aria-hidden="true">history</span>
        <p class="spec-notice__text">You're viewing ${specLabel(view.version)}, an older version. Only the latest version can be edited.</p>
        <button type="button" class="btn btn--filled" data-action="show-latest-spec" data-focus-key="show-latest-spec">Show ${specLabel(view.latest)} (latest)</button>
      </div>`;
  }

  // Redraws only the cards, so the search field keeps focus while you type.
  function renderSpecResults(body, { announce = true, spotlight = null } = {}) {
    const terms = searchTerms(state.specQuery);
    let total = 0;
    let shown = 0;

    const cards = specCards(state.specView.body).map((card, index) => {
      const lines = card.lines.filter((line) => lineMatches(line, terms));
      total += card.lines.length;
      shown += lines.length;
      if (lines.length === 0 && terms.length > 0) return "";
      // A new version can delete every line of a section. Without a search
      // the section still shows, so the creator can see it is empty.
      const content = lines.length > 0
        ? renderSpecLines(lines, terms, spotlight)
        : '<p class="spec-card__empty">No lines in this version.</p>';
      return `
        <section class="card card--outlined spec-card" aria-labelledby="spec-card-${index}">
          <h2 class="spec-card__title" id="spec-card-${index}">${escapeHtml(card.heading)}</h2>
          ${content}
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
      const text = `<p class="spec-line__text${line.empty ? " spec-line__text--empty" : ""}">${highlight(line.text, terms)}</p>`;
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

  // The spec as cards of lines. "Who Harry is" holds the opening instruction,
  // the labeled fields, and the setting (shown as Scene), which have no IDs.
  // Every other line has an ID.
  function specCards(spec) {
    return [
      {
        heading: "Who Harry is",
        lines: [
          { text: spec.preamble },
          ...spec.fields.map((field) => ({ label: field.label, text: field.text })),
          { label: "Scene", text: spec.setting || "Not set yet.", empty: !spec.setting },
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

  // A line's text in a spec body.
  function specLineText(lineId, spec) {
    const line = spec.sections
      .flatMap((section) => section.lines)
      .find((candidate) => candidate.id === lineId);
    return line ? line.text : "";
  }

  // Side sheet body: the line as the version on screen has it, then every
  // flag of every checked chat that cites it, each with the spec version its
  // chat was made with.
  function renderCitingFlags(lineId) {
    const line = `
      <div class="cited-line">
        <span class="chip" tabindex="0" data-tooltip="${escapeHtml(lineTip(lineId))}">${escapeHtml(lineId)}<span class="visually-hidden">: ${escapeHtml(citeMeaning(lineId))}</span></span>
        <p class="cited-line__text">${escapeHtml(specLineText(lineId, state.specView.body))}</p>
      </div>`;
    if (!state.review) {
      const text = state.reviewLoad.status === "failed"
        ? `The saved flags didn't load. ${state.reviewLoad.message}`
        : "The saved flags are still loading.";
      return `${line}<p class="sheet-summary">${escapeHtml(text)}</p>`;
    }

    const citing = allFlags().filter(({ flag }) => flag.line_id === lineId);
    let summary = `${citing.length} flags cite this line.`;
    if (citing.length === 0) summary = "No flags cite this line.";
    if (citing.length === 1) summary = "1 flag cites this line.";
    return `
      ${line}
      <p class="sheet-summary">${summary}</p>
      ${citing.length > 0 ? `<ul class="flag-list">${citing.map(renderFlagSummary).join("")}</ul>` : ""}`;
  }

  // A short card for one flag.
  function renderFlagSummary({ item, flag }) {
    const place = flagPlace(item.chat, flag);
    return `
      <li class="card card--outlined flag-summary">
        <h3 class="flag-summary__title">
          <span class="flag-summary__place">${escapeHtml(place)}<span class="visually-hidden">:</span></span>
          <span>${escapeHtml(capitalized(flag.type))}</span>
        </h3>
        <p>${confidenceHtml(capitalized(flag.confidence))}</p>
        <dl class="flag-summary__details">
          <div>
            <dt>Evidence</dt>
            <dd><q>${escapeHtml(flag.quote)}</q></dd>
          </div>
          <div>
            <dt>Why</dt>
            <dd>${escapeHtml(flag.why)}</dd>
          </div>
          <div>
            <dt>Chat made with</dt>
            <dd>Spec ${escapeHtml(specLabel(item.chat.spec_version))}</dd>
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

  // From the citing-flags sheet, or from What changed on Flag review itself,
  // where the screen redraws and lands on the card.
  actions["go-to-flag"] = (button) => {
    const target = findFlag(button.dataset.flag);
    if (target) {
      state.reviewChatId = target.item.chat.id;
      state.openFlagId = target.flag.id;
    }
    citingSheet.close();
    if (currentScreen === "diagnose") refresh();
    else goToScreen("diagnose");
  };

  actions["retry-spec"] = () => {
    state.specLoad = { status: "loading", message: "" };
    refresh();
    loadSpec("latest", { focusKey: "edit-spec" });
  };

  actions["show-latest-spec"] = async () => {
    if (await loadSpec("latest", { focusKey: "edit-spec" })) {
      announce(`Showing ${specLabel(state.specView.version)}, the latest version.`);
    }
  };

  // 3.1.1 Editing the spec --------------------------------------------------
  // The latest version as a form. Typing changes the draft in `state` without
  // a redraw (see the input listener in section 5); adding, removing, or
  // restoring a line redraws. The server cleans the text, numbers new lines,
  // and keeps each line's attributes, so the form only sends IDs and words.

  // Measures the save bar, so the CSS can keep a focused field from hiding
  // under it (see --spec-save-bar-height in styles.css).
  const saveBarObserver = "ResizeObserver" in window
    ? new ResizeObserver((entries) => {
        document.documentElement.style.setProperty("--spec-save-bar-height", `${entries[0].target.offsetHeight}px`);
      })
    : null;

  // Where the browser can grow a textarea to fit its text by itself.
  const FIELD_SIZING = Boolean(window.CSS && CSS.supports && CSS.supports("field-sizing", "content"));

  function renderSpecEdit(body) {
    const view = state.specView;
    const draft = state.specDraft;
    const next = specLabel(view.version + 1);
    const error = state.specSaveError;
    // The field the server named in its last error reads as wrong.
    const invalid = (key) => Boolean(error && error.field === key);

    body.innerHTML = `
      <div class="spec-editor">
        <div class="card card--filled spec-notice">
          <span class="icon" aria-hidden="true">edit_note</span>
          <p class="spec-notice__text">Only you can change the spec. Saving makes ${next}. Lines keep their IDs, new lines get the next unused ID, and earlier runs keep the version they used.</p>
        </div>
        <div class="spec-results spec-results--editing">
          <section class="card card--outlined spec-card" aria-labelledby="spec-edit-who">
            <h2 class="spec-card__title" id="spec-edit-who">Who Harry is</h2>
            <ul class="spec-lines">
              <li class="spec-edit-line">${textField("preamble", "Opening instruction", draft.preamble, { invalid: invalid("preamble") })}</li>
              ${draft.fields
                .map((field, i) => `<li class="spec-edit-line">${textField(`field-${i}`, field.label, field.text, { invalid: invalid(`field-${i}`) })}</li>`)
                .join("")}
              <li class="spec-edit-line">${textField("setting", "Scene", draft.setting, {
                hint: "Where and when the user meets the character.",
                invalid: invalid("setting"),
              })}</li>
            </ul>
          </section>
          ${draft.sections.map((section, s) => renderEditSection(section, s, invalid)).join("")}
          ${textField("note", "What changed (optional)", draft.note, { single: true, invalid: invalid("note") })}
        </div>
        <div class="spec-save-bar">
          ${error
            ? `<p class="spec-save-bar__error" id="spec-save-error">
                <span class="icon" aria-hidden="true">error</span>
                <span>${escapeHtml(error.message)}</span>
              </p>`
            : ""}
          <div class="spec-save-bar__actions">
            <button type="button" class="btn btn--text" data-action="cancel-spec-edit" data-focus-key="cancel-spec-edit"
              aria-disabled="${state.specSaving}">Cancel</button>
            <button type="button" class="btn btn--filled" data-action="save-spec" data-focus-key="save-spec"
              aria-disabled="${state.specSaving}">${state.specSaving ? "Saving" : `Save as ${next}`}</button>
          </div>
        </div>
      </div>`;

    fitTextareas(Array.from(body.querySelectorAll("textarea[data-draft-key]")));
    if (saveBarObserver) {
      saveBarObserver.disconnect();
      saveBarObserver.observe(body.querySelector(".spec-save-bar"));
    }

    // Arriving from "Open K2 in the spec" while editing: land on that line's field.
    const spotlight = state.specHighlight;
    state.specHighlight = null;
    if (!spotlight) return null;
    const field = body.querySelector(`[data-draft-key="line-${spotlight.lineId}"]`);
    if (!field) showSnackbar(`${spotlight.lineId} isn't in your draft.`);
    return field;
  }

  // One outlined field of the form; key is its data-draft-key. single makes a
  // one-line input, where Enter does nothing, since there is no form to submit.
  // While a save is on its way the field is read-only, since the saved version
  // replaces the draft and anything typed then would be lost.
  function textField(key, label, text, { hint = "", invalid = false, single = false, labelExtra = "" } = {}) {
    const id = `spec-${key}`;
    const describedBy = [hint && `${id}-hint`, invalid && "spec-save-error"].filter(Boolean).join(" ");
    const attributes = `class="text-field__input" id="${escapeHtml(id)}" placeholder=" " data-draft-key="${escapeHtml(key)}"
      data-focus-key="${escapeHtml(id)}"${invalid ? ' aria-invalid="true"' : ""}${describedBy ? ` aria-describedby="${escapeHtml(describedBy)}"` : ""}${state.specSaving ? " readonly" : ""}`;
    // Nothing but the text goes between the textarea tags, or every field
    // would count as changed.
    const input = single
      ? `<input ${attributes} autocomplete="off" value="${escapeHtml(text)}">`
      : `<textarea ${attributes} rows="1">${escapeHtml(text)}</textarea>`;
    return `
      <div class="text-field${invalid ? " text-field--error" : ""}">
        ${input}
        <label class="text-field__label" for="${escapeHtml(id)}">${escapeHtml(label)}${labelExtra}</label>
        ${hint ? `<p class="text-field__support" id="${escapeHtml(id)}-hint">${escapeHtml(hint)}</p>` : ""}
      </div>`;
  }

  function renderEditSection(section, s, invalid) {
    const headingId = `spec-edit-section-${s}`;
    return `
      <section class="card card--outlined spec-card" aria-labelledby="${headingId}">
        <h2 class="spec-card__title" id="${headingId}">${escapeHtml(section.heading)}</h2>
        <ul class="spec-lines">${section.lines.map((line) => renderEditLine(section, line, invalid)).join("")}</ul>
        <button type="button" class="btn btn--text btn--icon-leading spec-add-line" data-action="add-spec-line"
          data-section="${s}" data-focus-key="add-line-${s}" aria-disabled="${state.specSaving}">
          <span class="icon" aria-hidden="true">add</span>
          <span>Add a line<span class="visually-hidden"> to ${escapeHtml(section.heading)}</span></span>
        </button>
      </section>`;
  }

  // A saved line shows its ID, and a new one waits for its ID. A removed line
  // stays until Save, with Undo.
  function renderEditLine(section, line, invalid) {
    const key = `line-${line.key}`;
    if (line.removed) {
      return `
        <li class="spec-edit-line is-removed">
          <p class="spec-edit-line__removed">${escapeHtml(line.id)} will be removed when you save.</p>
          <button type="button" class="btn btn--text" data-action="undo-delete-spec-line" data-line-key="${escapeHtml(line.key)}"
            data-focus-key="undo-${escapeHtml(line.key)}" aria-disabled="${state.specSaving}">Undo<span class="visually-hidden">: keep ${escapeHtml(line.id)}</span></button>
        </li>`;
    }
    const field = line.id
      ? textField(key, line.id, line.text, {
          invalid: invalid(key),
          labelExtra: `<span class="visually-hidden">, ${escapeHtml(LINE_MEANINGS[line.id[0]] || "line")}</span>`,
        })
      : textField(key, "New line", line.text, {
          hint: "Gets its ID when you save.",
          invalid: invalid(key),
          labelExtra: `<span class="visually-hidden"> in ${escapeHtml(section.heading)}</span>`,
        });
    return `
      <li class="spec-edit-line">
        ${field}
        <button type="button" class="btn btn--text btn--icon-leading" data-action="delete-spec-line"
          data-line-key="${escapeHtml(line.key)}" data-focus-key="delete-${escapeHtml(line.key)}" aria-disabled="${state.specSaving}">
          <span class="icon" aria-hidden="true">delete</span>
          <span>Delete<span class="visually-hidden"> ${escapeHtml(line.id || "this new line")}</span></span>
        </button>
      </li>`;
  }

  // The form's starting point. Each line keeps a key that stays the same while
  // the creator edits, even a new line, which has no ID yet.
  function draftFrom(view) {
    const { body } = view;
    return {
      parent: view.version,
      note: "",
      preamble: body.preamble,
      fields: body.fields.map(({ label, text }) => ({ label, text })),
      setting: body.setting,
      sections: body.sections.map(({ heading, lines }) => ({
        heading,
        lines: lines.map(({ id, text }) => ({ key: id, id, text, removed: false })),
      })),
    };
  }

  // What Save sends, plus the draft key of each line sent, so a line the
  // server names by position ("line-2-5") can be found in the form again.
  function editPayload(draft) {
    const lineKeys = {};
    const sections = draft.sections.map((section, s) => {
      const lines = section.lines.filter((line) => !line.removed);
      lines.forEach((line, i) => {
        lineKeys[`line-${s}-${i}`] = `line-${line.key}`;
      });
      return { heading: section.heading, lines: lines.map(({ id, text }) => ({ id, text })) };
    });
    const edit = {
      parent: draft.parent,
      note: draft.note,
      preamble: draft.preamble,
      fields: draft.fields.map(({ label, text }) => ({ label, text })),
      setting: draft.setting,
      sections,
    };
    return { edit, lineKeys };
  }

  // The server's cleanup (whitespace collapses, zero-width marks go), so the
  // form counts as changed only when saving would change something.
  function cleanText(text) {
    return text.replace(/[\u200b\ufeff]/g, "").split(/\s+/).filter(Boolean).join(" ");
  }

  function draftChanged() {
    if (!state.specDraft || !state.specView) return false;
    const comparable = (edit) =>
      JSON.stringify([
        cleanText(edit.preamble),
        edit.fields.map((field) => cleanText(field.text)),
        cleanText(edit.setting),
        edit.sections.map((section) => section.lines.map((line) => [line.id, cleanText(line.text)])),
      ]);
    return comparable(editPayload(state.specDraft).edit) !== comparable(editPayload(draftFrom(state.specView)).edit);
  }

  function findDraftLine(key) {
    for (const section of state.specDraft.sections) {
      const line = section.lines.find((candidate) => candidate.key === key);
      if (line) return { section, line };
    }
    return null;
  }

  // Typing only updates the draft, since the field already shows the text.
  function setDraftText(key, value) {
    const draft = state.specDraft;
    if (key === "preamble" || key === "setting" || key === "note") {
      draft[key] = value;
    } else if (key.startsWith("field-")) {
      draft.fields[Number(key.slice("field-".length))].text = value;
    } else if (key.startsWith("line-")) {
      const found = findDraftLine(key.slice("line-".length));
      if (found) found.line.text = value;
    }
  }

  // Grows textareas to fit their text where field-sizing (styles.css) can't.
  // Every height is cleared, then read, then set, so the page lays out once.
  function fitTextareas(boxes) {
    if (FIELD_SIZING) return;
    boxes.forEach((box) => {
      box.style.height = "auto";
    });
    const heights = boxes.map((box) => box.scrollHeight);
    // scrollHeight leaves out the 1px borders.
    boxes.forEach((box, index) => {
      box.style.height = `${heights[index] + 2}px`;
    });
  }

  // After a line is added, removed, or restored: redraw the form, keep the
  // page where it was, then move focus.
  function redrawEditor(focusKey) {
    const top = window.scrollY;
    refresh();
    window.scrollTo(0, top);
    const target = panelFor("define").querySelector(`[data-focus-key="${CSS.escape(focusKey)}"]`);
    if (target) target.focus();
  }

  // Redraws the Spec editor and moves focus, or leaves it for when the
  // creator comes back to that screen.
  function refreshDefine(focusKey) {
    if (currentScreen === "define") refresh({ focusKey });
  }

  function startEditing(focusKey) {
    const view = state.specView;
    if (!view || view.version !== view.latest || state.specDraft) return;
    // A version that is still loading must not swap in under the form.
    specRequest += 1;
    state.specDraft = draftFrom(view);
    state.specSaveError = null;
    refresh({ focusKey });
    announce(`Editing ${specLabel(view.version)}. Saving makes ${specLabel(view.version + 1)}.`);
  }

  function leaveEditing() {
    state.specDraft = null;
    state.specSaveError = null;
    refresh({ focusKey: "edit-spec" });
  }

  actions["edit-spec"] = () => startEditing("spec-preamble");

  actions["add-setting"] = () => startEditing("spec-setting");

  // Adding, deleting, and restoring lines wait while a save is on its way. A
  // double click counts once: the first click redraws the form, so the second
  // would land on whatever moved under the pointer, like the next Delete.
  function editorBusy(event) {
    return !state.specDraft || state.specSaving || Boolean(event && event.detail > 1);
  }

  actions["add-spec-line"] = (button, event) => {
    if (editorBusy(event)) return;
    const section = state.specDraft.sections[Number(button.dataset.section)];
    newLineCount += 1;
    const key = `new-${newLineCount}`;
    section.lines.push({ key, id: null, text: "", removed: false });
    redrawEditor(`spec-line-${key}`);
    announce(`New line added to ${section.heading}. It gets its ID when you save.`);
  };

  actions["delete-spec-line"] = (button, event) => {
    const found = editorBusy(event) ? null : findDraftLine(button.dataset.lineKey);
    if (!found) return;
    const { section, line } = found;
    if (line.id) {
      // A saved line stays in the form until Save, so Undo can bring it back.
      line.removed = true;
      redrawEditor(`undo-${line.key}`);
      announce(`${line.id} will be removed when you save.`);
    } else {
      section.lines.splice(section.lines.indexOf(line), 1);
      redrawEditor(`add-line-${state.specDraft.sections.indexOf(section)}`);
      announce("New line removed.");
    }
  };

  actions["undo-delete-spec-line"] = (button, event) => {
    const found = editorBusy(event) ? null : findDraftLine(button.dataset.lineKey);
    if (!found) return;
    const { line } = found;
    line.removed = false;
    redrawEditor(`spec-line-${line.key}`);
    announce(`${line.id} is back.`);
  };

  actions["cancel-spec-edit"] = (button) => {
    if (state.specSaving) return;
    if (!draftChanged()) {
      leaveEditing();
      return;
    }
    // Discarding redraws the screen, so focus goes to Edit spec, not back to
    // the Cancel button that is gone.
    openDialog(discardSpecDialog, button, (choice) => {
      if (choice === "discard") leaveEditing();
    });
  };

  actions["save-spec"] = async () => {
    // A second click while saving would post the same edit again and get a 409.
    if (state.specSaving || !state.specDraft) return;
    const { edit, lineKeys } = editPayload(state.specDraft);
    const slug = state.specView.character.slug;
    state.specSaving = true;
    state.specSaveError = null;
    specRequest += 1;
    refresh({ focusKey: "save-spec" });
    try {
      const saved = await WorkbenchApi.saveSpec(slug, edit);
      state.specView = saved;
      state.specDraft = null;
      state.specSaving = false;
      refreshDefine("edit-spec");
      // The server takes emails, phone numbers, and keys out of a spec before saving it.
      const removed = removedParts(saved.removed);
      showSnackbar(`Saved ${specLabel(saved.version)}. Earlier runs keep the version they used.${removed.length
        ? ` Removed ${listText(removed)}.`
        : ""}`);
    } catch (error) {
      state.specSaving = false;
      const field = error.field ? lineKeys[error.field] || error.field : null;
      state.specSaveError = { message: error.message, field };
      refreshDefine(field ? `spec-${field}` : "save-spec");
      announce(error.message);
    }
  };

  // 3.2 Run a conversation (Stress-test) ------------------------------------
  // Start run makes a live chat on the server, pinned to the latest spec
  // version, then plays the scenario's script one turn at a time. Each reply
  // streams in as the model writes it. Stop ends the reply and the script, and
  // then, like after the last scripted line, the message box takes the
  // creator's own lines. Import adds a saved chat (pasted, a sample, or the
  // seeded transcript) to the same Chat list. While a reply streams, the
  // screen changes in place, so focus and scrolling stay where the creator
  // left them, and no other screen is redrawn by it.

  // Loaded from the server and kept outside `state`.
  let runOptions = null;
  let runOptionsLoad = { status: "loading", message: "" };
  let samples = [];
  // Counts runs and chat loads, so a reply that belongs to an older one changes nothing.
  let runTicket = 0;
  let chatRequest = 0;
  // The reply streaming now, as { chatId, controller }, so Stop can end it.
  let runStream = null;
  // The chat on screen, kept per tab, so a reload comes back to it.
  const CHAT_KEY = "workbench-chat";

  function rememberChat(id) {
    try {
      sessionStorage.setItem(CHAT_KEY, String(id));
    } catch {
      // Storage can be off; the newest chat shows instead.
    }
  }

  function rememberedChat() {
    try {
      return Number(sessionStorage.getItem(CHAT_KEY)) || null;
    } catch {
      return null;
    }
  }

  // "4 seconds", "1 second". Rounded to whole seconds, at least 1.
  function secondsText(value) {
    const whole = Math.max(1, Math.round(value));
    return `${whole} ${whole === 1 ? "second" : "seconds"}`;
  }

  // A message that sends people to Settings gets a button that opens it.
  function mentionsSettings(text) {
    return /\bin Settings\b/.test(text || "");
  }

  function settingsButton(focusKey) {
    return `
      <button type="button" class="btn btn--outlined btn--icon-leading" data-action="open-settings" data-focus-key="${focusKey}"
        aria-haspopup="dialog">
        <span class="icon" aria-hidden="true">settings</span>
        <span>Open Settings</span>
      </button>`;
  }

  // While Check this chat or a re-check runs, its card counts the seconds, so
  // a slow AI never looks frozen. The count is plain text, outside any live
  // region, so screen readers hear only the start and the end.
  let elapsedTimer = null;

  function elapsedText(since) {
    const seconds = Math.max(0, Math.floor((Date.now() - since) / 1000));
    return `${seconds} ${seconds === 1 ? "second" : "seconds"} so far`;
  }

  function elapsedLine(since) {
    return `<p class="check-start__elapsed" data-elapsed-since="${since}">${elapsedText(since)}</p>`;
  }

  function anyCheckRunning() {
    const running = (entry) => Boolean(entry && entry.status === "running");
    return Object.values(state.checks).some(running) || Object.values(state.rechecks).some(running);
  }

  // One timer for every running check. It updates the count in place, with no
  // redraw, and stops once nothing is running.
  function startElapsedTimer() {
    if (elapsedTimer) return;
    elapsedTimer = setInterval(() => {
      if (!anyCheckRunning()) {
        clearInterval(elapsedTimer);
        elapsedTimer = null;
        return;
      }
      document.querySelectorAll("[data-elapsed-since]").forEach((line) => {
        line.textContent = elapsedText(Number(line.dataset.elapsedSince));
      });
    }, 1000);
  }

  function chatTime(iso) {
    return new Date(iso).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
  }

  // How the Chat menu names a chat: a live run by its scenario and model, an
  // imported chat by its tool and receipt, like "Claude (CLA-F2)".
  function chatLabel(chat) {
    if (chat.kind === "live") return `${chat.scenario} live run, ${chat.model}, ${chatTime(chat.created_at)}`;
    return `${chat.title}, imported`;
  }

  // Chats number their messages by turn, or by line when the source did.
  function numberWord(chat) {
    return chat.numbering === "line" ? "Line" : "Turn";
  }

  // A model's name, from every model of the provider, the fallback models too.
  function modelLabel(id) {
    return (runOptions && runOptions.model_labels && runOptions.model_labels[id]) || id;
  }

  function isLive(chatId) {
    return Boolean(state.live && state.live.chatId === chatId);
  }

  // The last line is still waiting for a reply, after a turn that failed:
  // nothing answered it, or a model error cut the reply off.
  function pendingLine(chat) {
    const last = chat.messages[chat.messages.length - 1];
    return Boolean(last && (last.speaker === "user" || last.failed));
  }

  function canContinue(chat) {
    return chat.kind === "live" && chat.status === "active" && !isLive(chat.id) && (chat.script_left > 0 || pendingLine(chat));
  }

  // Try again answers the line still waiting, in a chat whose script has ended too.
  function canRetry(chat) {
    return chat.kind === "live" && !isLive(chat.id) && pendingLine(chat);
  }

  function canType(chat) {
    return chat.kind === "live" && (chat.status === "script_done" || chat.status === "stopped") && !isLive(chat.id);
  }

  // Why Start run can't start now, or "" when it can.
  function startBlockedReason() {
    if (!runOptions.key_set) return "No AI is connected yet. Connect one in Settings to start a run.";
    if (runOptions.used_today >= runOptions.daily_cap) {
      return `Today's ${runOptions.daily_cap} model calls are used up. The count starts over at midnight Pacific time.`;
    }
    const limit = runOptions.session_run_limit;
    if (runOptions.session_runs >= limit) {
      return `This browser session has started ${limit} ${limit === 1 ? "run" : "runs"}, the most one session may start. To allow more, raise the session run limit in Settings.`;
    }
    return "";
  }

  function waitText(seconds) {
    return `Waiting ${secondsText(seconds)} so calls stay under ${runOptions.calls_per_minute} a minute.`;
  }

  // The notice under the progress bar while the next words are on their way:
  // the server's words for a retry or the fallback model, or the call slot's
  // wait. Empty when there is nothing to say.
  function waitNotice(live) {
    if (live.phase !== "waiting") return "";
    if (live.waitMessage) return live.waitMessage;
    return live.waitSeconds > 0 ? waitText(live.waitSeconds) : "";
  }

  function progressText(chat, live) {
    if (!live.turn) return "Starting the next turn";
    return live.scripted && chat.script_last_turn ? `Turn ${live.turn} of ${chat.script_last_turn}` : `Turn ${live.turn}`;
  }

  function liveLabel(live) {
    if (live.phase === "stopping") return "Stopping";
    return live.phase === "writing" ? "Writing" : "Waiting";
  }

  // Where the chat came from. Live runs say when and with which model;
  // imported chats repeat what their receipt recorded.
  function sourceText(chat) {
    if (chat.kind === "live") {
      return `Started ${chatTime(chat.created_at)} with ${modelLabel(chat.model)}. It keeps spec ${specLabel(chat.spec_version)}, even after you save a newer version.`;
    }
    const { date, mode, model, note } = chat.source;
    const saved = date ? `Saved ${date}${mode ? ` (${mode})` : ""}.` : `Imported ${chatTime(chat.created_at)}.`;
    return [saved, model ? `Model shown: ${model}.` : "", note].filter(Boolean).join(" ");
  }

  // Keeps the Chat menu's entry for a chat in step with its latest view.
  function updateChatSummary(view) {
    const { source, messages, ...summary } = view;
    const index = state.chats.findIndex((chat) => chat.id === view.id);
    if (index === -1) state.chats.unshift(summary);
    else state.chats[index] = summary;
  }

  async function loadRunOptions() {
    try {
      runOptions = await WorkbenchApi.runOptions();
      runOptionsLoad = { status: "ready", message: "" };
      const setup = state.runSetup;
      // F2, the demo's scenario, is last in the list.
      if (!runOptions.scenarios.some((scenario) => scenario.id === setup.scenarioId)) {
        setup.scenarioId = runOptions.scenarios[runOptions.scenarios.length - 1].id;
      }
      if (!runOptions.models.some((model) => model.id === setup.modelId)) setup.modelId = runOptions.default_model;
    } catch (error) {
      runOptionsLoad = { status: "failed", message: error.message };
    }
    refreshRun();
  }

  async function loadSamples() {
    try {
      samples = await WorkbenchApi.listSamples();
    } catch {
      samples = [];
    }
  }

  // Loads the Chat menu, then one chat: select if given, else the one on
  // screen, else the one this tab showed last, else an unfinished live run,
  // else the newest.
  async function loadChats({ select = null, focusKey = null } = {}) {
    const ticket = ++chatRequest;
    try {
      const chats = await WorkbenchApi.listChats();
      if (ticket !== chatRequest) return;
      state.chats = chats;
      state.chatsLoad = { status: "ready", message: "" };
      const known = (id) => id && chats.some((chat) => chat.id === id);
      const unfinished = chats.find((chat) => chat.kind === "live" && chat.status === "active");
      const id = [select, state.chatId, rememberedChat()].find(known) || (unfinished || chats[0] || {}).id;
      if (id) {
        await loadChat(id, { focusKey });
      } else {
        state.chatId = null;
        state.chat = null;
        refreshRun({ focusKey });
      }
    } catch (error) {
      if (ticket !== chatRequest) return;
      state.chatsLoad = { status: "failed", message: error.message };
      refreshRun({ focusKey });
    }
  }

  async function loadChat(id, { focusKey = null } = {}) {
    const ticket = ++chatRequest;
    try {
      const chat = await WorkbenchApi.getChat(id);
      if (ticket !== chatRequest) return false;
      state.chatId = chat.id;
      state.chat = chat;
      rememberChat(chat.id);
      updateChatSummary(chat);
      refreshRun({ focusKey });
      // The check's buttons appear only once it loads, so focus meant for one lands then.
      loadCheck(chat.id, { focusKey });
      return true;
    } catch (error) {
      if (ticket !== chatRequest) return false;
      showSnackbar(`That chat didn't load. ${error.message}`);
      return false;
    }
  }

  // Redraws Run a conversation only while it's on screen. Otherwise the
  // change waits in `state`, and coming back to the screen draws it.
  function refreshRun(options) {
    if (currentScreen === "run") refresh(options);
  }

  // The Run screen's body, or null while another screen shows.
  function runBody() {
    return currentScreen === "run" ? panelFor("run").querySelector("[data-screen-body]") : null;
  }

  function chip(icon, text) {
    return `
      <span class="chip chip--icon-leading">
        <span class="icon" aria-hidden="true">${icon}</span>
        <span>${escapeHtml(text)}</span>
      </span>`;
  }

  function renderRun(body) {
    if (runOptionsLoad.status === "loading") {
      body.innerHTML = '<p class="spec-status">Loading the run setup.</p>';
      return null;
    }
    if (runOptionsLoad.status === "failed") {
      body.innerHTML = `
        <div class="card card--outlined spec-empty">
          <p>The run setup didn't load. ${escapeHtml(runOptionsLoad.message)}</p>
          <button type="button" class="btn btn--filled" data-action="retry-run-options" data-focus-key="retry-run-options">Try again</button>
        </div>`;
      return null;
    }

    const chat = state.chat;
    body.innerHTML = `
      <div class="run-screen">
        ${renderRunSetup()}
        ${state.chats.length ? renderChatPicker() : ""}
        ${chat ? renderTranscript(chat) : renderNoChat()}
        ${chat ? renderRunAfter(chat) : ""}
      </div>`;

    body.querySelector("#run-scenario").addEventListener("change", (event) => {
      state.runSetup.scenarioId = event.target.value;
      // Only the tooltip changes, so nothing else redraws mid-run.
      const tip = scenarioTip(event.target.value);
      event.target.dataset.tooltip = tip;
      body.querySelector("#run-scenario-meaning").textContent = tip;
    });
    body.querySelector("#run-model").addEventListener("change", (event) => {
      state.runSetup.modelId = event.target.value;
    });
    const picker = body.querySelector("#run-chat");
    if (picker) {
      picker.addEventListener("change", (event) => {
        if (state.live) {
          event.target.value = String(state.chatId);
          announce("Stop the run to switch chats.");
          return;
        }
        state.runError = null;
        loadChat(Number(event.target.value), { focusKey: "run-chat" });
      });
    }
    const message = chat ? body.querySelector("#run-message") : null;
    if (message) {
      message.addEventListener("input", () => {
        state.drafts[chat.id] = message.value;
        body.querySelector('[data-action="send-message"]').setAttribute("aria-disabled", String(!message.value.trim()));
      });
      message.addEventListener("keydown", (event) => {
        // Enter sends; Shift+Enter starts a new line. Enter that confirms
        // an input method's text (as in Japanese or Chinese) never sends.
        if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
        event.preventDefault();
        actions["send-message"]();
      });
    }

    const messages = body.querySelector(".chat");
    if (messages) messages.scrollTop = messages.scrollHeight;
    return null;
  }

  function renderRunSetup() {
    const setup = state.runSetup;
    const scenarioOptions = runOptions.scenarios
      .map((scenario) => `<option value="${escapeHtml(scenario.id)}"${scenario.id === setup.scenarioId ? " selected" : ""}>${escapeHtml(scenario.name)}</option>`)
      .join("");
    const modelOptions = runOptions.models
      .map((model) => {
        const label = model.id === runOptions.default_model ? `${model.label} (default)` : model.label;
        return `<option value="${escapeHtml(model.id)}"${model.id === setup.modelId ? " selected" : ""}>${escapeHtml(label)}</option>`;
      })
      .join("");
    const blocked = startBlockedReason();
    const support = blocked ||
      `Calls start at least ${secondsText(60 / runOptions.calls_per_minute)} apart. ${runOptions.used_today} of ${runOptions.daily_cap} calls used today.`;
    const busy = Boolean(state.live || state.runStarting);
    // With no AI connected, Connect an AI is the step to take, so it comes first and Start steps back.
    // At the session run limit, Open Settings is where the limit goes up.
    const connect = !runOptions.key_set
      ? `
          <button type="button" class="btn btn--filled btn--icon-leading" data-action="open-settings" data-focus-key="connect-ai"
            aria-haspopup="dialog">
            <span class="icon" aria-hidden="true">link</span>
            <span>Connect an AI</span>
          </button>`
      : mentionsSettings(blocked) ? settingsButton("raise-limit") : "";
    return `
      <div class="run-setup">
        ${selectField("run-scenario", "Scenario", scenarioOptions, {
          support: "T2 tests the reviewer, not the character, so it isn't a run.",
          tooltip: scenarioTip(setup.scenarioId),
        })}
        ${selectField("run-model", "Model", modelOptions, { support })}
        <div class="run-setup__actions">
          ${connect}
          <button type="button" class="btn ${runOptions.key_set ? "btn--filled" : "btn--outlined"} btn--icon-leading" data-action="start-run" data-focus-key="start-run"
            aria-disabled="${Boolean(blocked) || busy}"${blocked ? ' aria-describedby="run-model-help"' : ""}>
            <span class="icon" aria-hidden="true">play_arrow</span>
            <span>Start run</span>
          </button>
          <button type="button" class="btn btn--outlined btn--icon-leading" data-action="open-import" data-focus-key="open-import"
            aria-haspopup="dialog" aria-disabled="${busy}">
            <span class="icon" aria-hidden="true">upload_file</span>
            <span>Import a chat</span>
          </button>
        </div>
      </div>`;
  }

  function renderChatPicker() {
    const options = state.chats
      .map((chat) => `<option value="${chat.id}"${chat.id === state.chatId ? " selected" : ""}>${escapeHtml(chatLabel(chat))}</option>`)
      .join("");
    return `
      <div class="run-chats">
        ${selectField("run-chat", "Chat", options, {
          support: "Live runs and imported chats, newest first. Each keeps the spec version it used.",
        })}
      </div>`;
  }

  // No chats yet gets the mascot with speech bubbles; a load error doesn't.
  function renderNoChat() {
    const failed = state.chatsLoad.status === "failed";
    const text = failed
      ? `The saved chats didn't load. ${state.chatsLoad.message}`
      : "No chats yet. Pick a scenario and a model, then press Start run. Or import a saved chat.";
    return `
      <section class="card card--outlined transcript" aria-label="Transcript">
        <div class="chat">
          <div class="chat__empty">
            ${failed ? "" : decorScene("chat")}
            <p>${escapeHtml(text)}</p>
          </div>
        </div>
      </section>`;
  }

  function renderTranscript(chat) {
    const live = isLive(chat.id) ? state.live : null;
    const items = [];
    // Turn 1 of every scripted chat is the spec itself.
    if (chat.numbering === "turn" && (chat.kind === "live" || chat.scenario)) {
      items.push(`
        <li class="chat__system">
          <span class="icon" aria-hidden="true">description</span>
          <span>Turn 1: character spec ${escapeHtml(specLabel(chat.spec_version))} loaded</span>
        </li>`);
    }
    chat.messages.forEach((message) => items.push(renderBubble(chat, message)));
    if (live && live.turn) items.push(renderLiveBubble(chat, live));

    return `
      <section class="card card--outlined transcript" aria-labelledby="transcript-title">
        <div class="transcript__header">
          <h2 class="transcript__title" id="transcript-title">Transcript</h2>
          ${chat.kind === "live" ? chip("bolt", "Live run") : chip("upload_file", "Imported")}
          ${chat.receipt ? chip("receipt_long", `Receipt ${chat.receipt}`) : ""}
          ${chip("description", `Spec ${specLabel(chat.spec_version)}`)}
          ${chat.model ? chip("smart_toy", chat.model) : ""}
        </div>
        <p class="transcript__source">${escapeHtml(sourceText(chat))}</p>
        ${live ? renderRunProgress(chat, live) : ""}
        <div class="chat" tabindex="0" role="region" aria-label="Messages" data-focus-key="run-messages">
          ${items.length ? "" : '<p class="chat__empty">No messages yet.</p>'}
          <ol class="chat__list">${items.join("")}</ol>
        </div>
      </section>`;
  }

  // A line that reads like an instruction to the AI, marked for the creator.
  // Nothing about the line changes. With explain, a tooltip and hidden words say
  // what the mark means; the Import dialog leaves them out, since its note says it.
  const INJECTION_MEANS = "This line reads like an instruction to the AI. The AI judge reads it as chat data and doesn't follow it.";

  function injectionStatus(className, { explain = true } = {}) {
    return `<span class="${className}"${explain ? ` data-tooltip="${INJECTION_MEANS}"` : ""}>
      <span class="icon" aria-hidden="true">gpp_maybe</span><span>Possible injection</span>${explain
        ? `<span class="visually-hidden">. ${INJECTION_MEANS}</span>`
        : ""}</span>`;
  }

  // A reply the last check flagged says so, with the flags' quotes marked. A
  // reply also says when a model error cut it off, when the fallback model
  // wrote it, and when a line reads like an instruction to the AI.
  function renderBubble(chat, message) {
    const name = message.speaker === "user" ? chat.user_name : chat.character_name;
    let stopped = "";
    if (message.failed) {
      stopped = `<span class="bubble__status"><span class="icon" aria-hidden="true">error</span><span>Cut off by an error</span></span>`;
    } else if (message.stopped) {
      stopped = `<span class="bubble__status"><span class="icon" aria-hidden="true">stop_circle</span><span>Stopped</span></span>`;
    }
    const fallback = message.fallback
      ? `<span class="bubble__status" data-tooltip="The chat's own model stayed busy, so its fallback model wrote this reply.">
          <span class="icon" aria-hidden="true">swap_horiz</span><span>Fallback: ${escapeHtml(modelLabel(message.model))}</span></span>`
      : "";
    const injected = message.injection ? injectionStatus("bubble__status bubble__status--injection") : "";
    const check = message.speaker === "character" && !message.stopped ? readyCheck(chat.id) : null;
    const flags = check ? check.flags.filter((flag) => flag.turn === message.turn) : [];
    // A rule flag sits at its first break and lists the other turns that broke the same line.
    const alsoLines = check && flags.length === 0
      ? [...new Set(check.flags.filter((flag) => flag.also_turns.includes(message.turn)).map((flag) => flag.line_id))]
      : [];
    let flagStatus = "";
    if (flags.length > 0) {
      flagStatus = `<span class="bubble__status bubble__status--flagged"><span class="icon icon--filled" aria-hidden="true">flag</span><span>Flagged</span></span>`;
    } else if (alsoLines.length > 0) {
      flagStatus = `<span class="bubble__status"><span class="icon" aria-hidden="true">flag</span><span>Also breaks ${escapeHtml(listText(alsoLines.map(citeLabel)))}</span></span>`;
    }
    return `
      <li class="bubble bubble--${message.speaker === "user" ? "user" : "character"}" data-seq="${message.seq}"
        data-turn="${message.turn}" tabindex="-1">
        <p class="bubble__meta">
          <span class="bubble__speaker">${escapeHtml(name)}</span>
          <span class="bubble__turn">${numberWord(chat)} ${message.turn}<span class="visually-hidden">:</span></span>
          ${stopped}
          ${fallback}
          ${injected}
          ${flagStatus}
        </p>
        <p class="bubble__text keep-lines">${highlight(message.text, flags.map((flag) => flag.quote.toLowerCase()))}</p>
      </li>`;
  }

  // The reply being written. Its text changes in place on every delta; screen
  // readers hear the whole reply once it's done, not each piece.
  function renderLiveBubble(chat, live) {
    return `
      <li class="bubble bubble--character bubble--live" data-live-bubble aria-busy="true">
        <p class="bubble__meta">
          <span class="bubble__speaker">${escapeHtml(chat.character_name)}</span>
          <span class="bubble__turn">Turn ${live.turn}<span class="visually-hidden">:</span></span>
          <span class="bubble__status" data-live-status><span class="icon" aria-hidden="true">edit</span><span>${liveLabel(live)}</span></span>
        </p>
        <p class="bubble__text keep-lines" data-live-text>${escapeHtml(live.text)}</p>
      </li>`;
  }

  // "Turn 5 of 11", the bar, Stop, and the wait notice, for the whole run.
  function renderRunProgress(chat, live) {
    const scripted = live.scripted && chat.script_last_turn;
    const stopping = live.phase === "stopping";
    const notice = waitNotice(live);
    return `
      <div class="run-progress">
        <p class="run-progress__label" id="run-progress-label" data-run-progress>${escapeHtml(progressText(chat, live))}</p>
        ${scripted
          ? `<progress class="linear-progress" max="${chat.script_last_turn}" value="${live.turn || 1}" aria-labelledby="run-progress-label" data-run-bar></progress>`
          : ""}
        <button type="button" class="btn btn--text btn--icon-leading" data-action="stop-run" data-focus-key="stop-run" aria-disabled="${stopping}">
          <span class="icon" aria-hidden="true">stop_circle</span>
          <span>${stopping ? "Stopping" : "Stop"}</span>
        </button>
      </div>
      <p class="run-wait" data-run-wait${notice ? "" : " hidden"}>${escapeHtml(notice)}</p>`;
  }

  // Below the transcript: what went wrong, what happens next, and the message box.
  function renderRunAfter(chat) {
    if (isLive(chat.id)) return "";
    const parts = [];
    const error = state.runError && state.runError.chatId === chat.id ? state.runError : null;
    if (error) {
      parts.push(`
        <div class="card card--outlined run-error">
          <span class="icon" aria-hidden="true">error</span>
          <p class="run-error__text">${escapeHtml(error.message)}</p>
          ${mentionsSettings(error.message) ? settingsButton("run-error-settings") : ""}
          ${error.retry && canRetry(chat)
            ? '<button type="button" class="btn btn--filled" data-action="retry-turn" data-focus-key="retry-turn">Try again</button>'
            : ""}
        </div>`);
    } else if (chat.kind !== "live") {
      parts.push(`
        <div class="card card--filled run-result__card">
          <span class="icon" aria-hidden="true">upload_file</span>
          <p class="run-result__text">Imported chat, pinned to spec ${escapeHtml(specLabel(chat.spec_version))}. Imported chats are read-only.</p>
        </div>`);
    } else if (chat.status === "script_done" || chat.status === "stopped") {
      const ended = chat.status === "stopped" ? "Run stopped. The script won't go on in this chat." : "Script finished.";
      parts.push(`
        <div class="card card--filled run-result__card">
          <span class="icon" aria-hidden="true">task_alt</span>
          <p class="run-result__text">${ended} Type your own next message below, or start a new run.</p>
        </div>`);
    }
    if (canContinue(chat) && !error) {
      const left = chat.script_left;
      const text = pendingLine(chat)
        ? "The last line is still waiting for a reply."
        : `${left} scripted ${left === 1 ? "line is" : "lines are"} left.`;
      parts.push(`
        <div class="run-continue">
          <button type="button" class="btn btn--filled btn--icon-leading" data-action="continue-run" data-focus-key="continue-run">
            <span class="icon" aria-hidden="true">play_arrow</span>
            <span>Continue run</span>
          </button>
          <p class="run-continue__text">${escapeHtml(text)}</p>
        </div>`);
    }
    if (canType(chat)) parts.push(renderMessageBox(chat));
    parts.push(renderCheck(chat));
    return parts.join("");
  }

  function renderMessageBox(chat) {
    const draft = state.drafts[chat.id] || "";
    return `
      <div class="message-box">
        <div class="text-field message-box__field">
          <textarea class="text-field__input" id="run-message" rows="2" placeholder=" " maxlength="${runOptions.max_typed_chars}"
            aria-describedby="run-message-help" data-focus-key="run-message">${escapeHtml(draft)}</textarea>
          <label class="text-field__label" for="run-message">Your next line, as ${escapeHtml(chat.user_name)}</label>
          <p class="text-field__support" id="run-message-help">Enter sends. Shift+Enter starts a new line.</p>
        </div>
        <button type="button" class="btn btn--filled btn--icon-leading" data-action="send-message" data-focus-key="send-message"
          aria-disabled="${!draft.trim()}">
          <span class="icon" aria-hidden="true">send</span>
          <span>Send</span>
        </button>
      </div>`;
  }

  // In-place changes while a reply streams.

  // Follows new text only when the creator hasn't scrolled up to reread.
  function followChat(box, change) {
    const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 48;
    change();
    if (atBottom) box.scrollTop = box.scrollHeight;
  }

  function updateRunProgress(body) {
    const live = state.live;
    if (!live || !state.chat) return;
    const label = body.querySelector("[data-run-progress]");
    if (label) label.textContent = progressText(state.chat, live);
    const bar = body.querySelector("[data-run-bar]");
    if (bar && live.turn) bar.value = live.turn;
    const wait = body.querySelector("[data-run-wait]");
    if (wait) {
      const notice = waitNotice(live);
      wait.hidden = !notice;
      wait.textContent = notice;
    }
    const stop = body.querySelector('[data-action="stop-run"]');
    if (stop) {
      stop.setAttribute("aria-disabled", String(live.phase === "stopping"));
      stop.lastElementChild.textContent = live.phase === "stopping" ? "Stopping" : "Stop";
    }
    const status = body.querySelector("[data-live-status]");
    if (status) status.lastElementChild.textContent = liveLabel(live);
  }

  // The user's line and an empty reply bubble, once the server saved the line.
  function showLiveTurn(chatId) {
    const body = runBody();
    if (!body || state.chatId !== chatId) return;
    const box = body.querySelector(".chat");
    if (!box) return;
    const list = box.querySelector(".chat__list");
    const chat = state.chat;
    followChat(box, () => {
      const empty = box.querySelector(".chat__empty");
      if (empty) empty.remove();
      const message = chat.messages[chat.messages.length - 1];
      if (message && !list.querySelector(`[data-seq="${message.seq}"]`)) {
        list.insertAdjacentHTML("beforeend", renderBubble(chat, message));
      }
      const old = list.querySelector("[data-live-bubble]");
      if (old) old.remove();
      list.insertAdjacentHTML("beforeend", renderLiveBubble(chat, state.live));
    });
    updateRunProgress(body);
  }

  // Finds the bubble on every delta, so a redraw in between can't leave it stale.
  function showLiveText(chatId) {
    const body = runBody();
    if (!body || state.chatId !== chatId || !state.live) return;
    const box = body.querySelector(".chat");
    const text = box && box.querySelector("[data-live-text]");
    if (!text) return;
    followChat(box, () => {
      text.textContent = state.live.text;
    });
    updateRunProgress(body);
  }

  // Swaps the reply bubble for the saved reply, or removes it when nothing was saved.
  function showSavedReply(chatId, message) {
    const body = runBody();
    if (!body || state.chatId !== chatId) return;
    const list = body.querySelector(".chat__list");
    if (!list) return;
    const bubble = list.querySelector("[data-live-bubble]");
    const html = message ? renderBubble(state.chat, message) : "";
    if (bubble) bubble.outerHTML = html;
    else if (html) list.insertAdjacentHTML("beforeend", html);
    updateRunProgress(body);
  }

  function addMessage(chatId, message) {
    const chat = state.chat;
    if (!chat || chat.id !== chatId || chat.messages.some((saved) => saved.seq === message.seq)) return;
    chat.messages.push(message);
    chat.message_count = chat.messages.length;
  }

  // Applies one server event of the turn streaming in chatId.
  function handleRunEvent(chatId, name, data) {
    const live = state.live;
    if (!live || live.chatId !== chatId) return;
    if (name === "user") {
      live.turn = data.turn;
      live.phase = live.phase === "stopping" ? "stopping" : "waiting";
      live.text = "";
      live.waitSeconds = 0;
      live.waitMessage = "";
      addMessage(chatId, {
        seq: data.seq,
        turn: data.turn,
        speaker: "user",
        text: data.text,
        source: live.scripted ? "script" : "typed",
        stopped: false,
        injection: data.injection,
      });
      showLiveTurn(chatId);
      // The chat just changed, so a check of it no longer covers it, and Flag review's count changes.
      loadReview();
    } else if (name === "wait") {
      // A retry or the fallback model comes with the server's own words.
      live.waitSeconds = data.seconds;
      live.waitMessage = data.message || "";
      showLiveText(chatId);
      if (data.message) announce(data.message);
    } else if (name === "delta") {
      if (!live.turn && state.chat) live.turn = state.chat.messages[state.chat.messages.length - 1].turn;
      if (live.phase !== "stopping") live.phase = "writing";
      live.waitSeconds = 0;
      live.waitMessage = "";
      live.text += data.text;
      if (runBody() && state.chatId === chatId && !runBody().querySelector("[data-live-bubble]")) showLiveTurn(chatId);
      else showLiveText(chatId);
    } else if (name === "done") {
      if (data.message) addMessage(chatId, data.message);
      if (state.chat && state.chat.id === chatId) {
        state.chat.status = data.status;
        state.chat.script_left = data.script_left;
      }
      runOptions.used_today = data.used_today;
      live.text = "";
      if (live.phase !== "stopping") live.phase = "waiting";
      showSavedReply(chatId, data.message);
      if (data.message && !data.stopped && state.chat) announce(`${state.chat.character_name} replied.`);
    } else if (name === "error") {
      state.runError = { chatId, message: data.message, retry: data.retry };
      // The words that came before the error are saved, marked as cut off.
      if (data.partial) addMessage(chatId, data.partial);
      if (state.chat && state.chat.id === chatId) state.chat.status = data.status;
    }
  }

  // Streams one turn: kind "next" (the next scripted line, or the line still
  // waiting for a reply) or "typed". Resolves with { name, data } for done or
  // error, { name: "failed", data: ApiError } when the request failed, or null
  // when Stop or a newer run came before the server answered.
  async function streamTurn(chatId, kind, text, ticket) {
    const controller = new AbortController();
    runStream = { chatId, controller };
    let outcome = null;
    const onEvent = (name, data) => {
      if (ticket !== runTicket) return;
      handleRunEvent(chatId, name, data);
      if (name === "done" || name === "error") outcome = { name, data };
    };
    try {
      if (kind === "typed") await WorkbenchApi.sendMessage(chatId, text, onEvent, controller.signal);
      else await WorkbenchApi.nextTurn(chatId, onEvent, controller.signal);
    } catch (error) {
      if (ticket !== runTicket || (error && error.name === "AbortError")) return null;
      // Stop that reached the server between two turns ends the script, so the next turn is refused.
      if (error.status === 409 && state.live && state.live.stopRequested) return null;
      outcome = { name: "failed", data: error };
    } finally {
      if (runStream && runStream.controller === controller) runStream = null;
    }
    return outcome;
  }

  // Plays the script from where the chat is, one streamed turn after another,
  // until it ends, a turn fails, or the creator presses Stop.
  async function playRun(chatId) {
    const ticket = ++runTicket;
    state.runError = null;
    state.live = { chatId, phase: "waiting", turn: null, text: "", waitSeconds: 0, waitMessage: "", scripted: true, stopRequested: false };
    refreshRun({ focusKey: "stop-run" });
    let outcome = null;
    for (;;) {
      outcome = await streamTurn(chatId, "next", null, ticket);
      if (ticket !== runTicket) return;
      const live = state.live;
      if (!outcome || outcome.name !== "done" || outcome.data.stopped || outcome.data.status !== "active" || live.stopRequested) break;
      if (outcome.data.script_left === 0) break;
      live.turn = null;
      live.phase = "waiting";
      const body = runBody();
      if (body) updateRunProgress(body);
    }
    await finishRun(chatId, ticket, outcome);
  }

  // After a run or a typed line: reloads the saved chat, so the screen shows
  // exactly what the server kept, and moves focus on only if Stop had it.
  async function finishRun(chatId, ticket, outcome) {
    const active = document.activeElement;
    const stopHadFocus = Boolean(active && active.closest && active.closest('[data-action="stop-run"]'));
    if (outcome && outcome.name === "failed") {
      state.runError = { chatId, message: outcome.data.message, retry: outcome.data.status === 0 };
    }
    try {
      const chat = await WorkbenchApi.getChat(chatId);
      if (ticket !== runTicket) return;
      if (state.chatId === chatId) state.chat = chat;
      updateChatSummary(chat);
    } catch {
      // The screen keeps what it streamed.
    }
    if (ticket !== runTicket) return;
    state.live = null;
    let focusKey = null;
    if (stopHadFocus && state.chat) {
      if (state.runError && state.runError.chatId === chatId && state.runError.retry && canRetry(state.chat)) focusKey = "retry-turn";
      else if (canType(state.chat)) focusKey = "run-message";
      else if (canContinue(state.chat)) focusKey = "continue-run";
      else focusKey = "start-run";
    }
    refreshRun({ focusKey });
    if (state.runError && state.runError.chatId === chatId) announce(state.runError.message);
    // The chat grew, so an earlier check no longer covers it.
    loadCheck(chatId);
    loadReview();
  }

  actions["start-run"] = async (button) => {
    if (state.live || state.runStarting || (button && button.getAttribute("aria-disabled") === "true")) return;
    const ticket = runTicket;
    state.runStarting = true;
    try {
      const chat = await WorkbenchApi.startChat({
        character: runOptions.character.slug,
        scenario: state.runSetup.scenarioId,
        model: state.runSetup.modelId,
      });
      state.runStarting = false;
      // Counts toward this session's run limit, so Start run can say when it's reached.
      runOptions.session_runs += 1;
      if (ticket !== runTicket) return;
      state.chatId = chat.id;
      state.chat = chat;
      rememberChat(chat.id);
      updateChatSummary(chat);
      playRun(chat.id);
    } catch (error) {
      state.runStarting = false;
      if (ticket !== runTicket) return;
      showSnackbar(error.message);
      loadRunOptions();
    }
  };

  actions["continue-run"] = () => {
    if (state.live || !state.chat || !canContinue(state.chat)) return;
    playRun(state.chat.id);
  };

  // Try again after a failed turn answers the line that is still waiting. In a
  // chat whose script has ended, that is the one turn; otherwise the run goes on.
  actions["retry-turn"] = () => {
    if (state.live || !state.chat || !canRetry(state.chat)) return;
    playRun(state.chat.id);
  };

  actions["stop-run"] = async (button) => {
    const live = state.live;
    if (!live || live.phase === "stopping" || (button && button.getAttribute("aria-disabled") === "true")) return;
    live.stopRequested = true;
    live.phase = "stopping";
    const body = runBody();
    if (body) updateRunProgress(body);
    try {
      await WorkbenchApi.stopChat(live.chatId);
    } catch (error) {
      // The server didn't hear Stop, so end the request; it saves what came in so far.
      if (runStream && runStream.chatId === live.chatId) runStream.controller.abort();
      showSnackbar(`Stop didn't reach the server. ${error.message}`);
    }
  };

  actions["send-message"] = async () => {
    const chat = state.chat;
    if (!chat || state.live || !canType(chat)) return;
    const text = (state.drafts[chat.id] || "").trim();
    if (!text) {
      announce("Type a message first.");
      return;
    }
    const ticket = ++runTicket;
    state.runError = null;
    state.live = { chatId: chat.id, phase: "waiting", turn: null, text: "", waitSeconds: 0, waitMessage: "", scripted: false, stopRequested: false };
    refreshRun({ focusKey: "stop-run" });
    const outcome = await streamTurn(chat.id, "typed", text, ticket);
    if (ticket !== runTicket) return;
    // A line the server refused keeps its draft, so it can be fixed and sent again.
    if (outcome && outcome.name !== "failed") delete state.drafts[chat.id];
    await finishRun(chat.id, ticket, outcome);
  };

  // "Review flags" under a check: Flag review opens on that chat.
  actions["review-flags"] = (button) => {
    state.reviewChatId = Number(button.dataset.chat);
    state.openFlagId = null;
    goToScreen("diagnose");
  };

  actions["retry-run-options"] = () => {
    runOptionsLoad = { status: "loading", message: "" };
    refreshRun({ focusKey: "retry-run-options" });
    loadRunOptions();
  };

  // 3.2.1 Import a chat -----------------------------------------------------
  // The dialog body is drawn once each time it opens. After that only the
  // preview area changes, so arrowing through the choices and typing in the
  // fields never loses focus.

  const importDialog = document.getElementById("import-dialog");
  const importBody = importDialog.querySelector("[data-import-body]");
  let importBusy = false;

  function importSource() {
    const picked = importBody.querySelector('input[name="import-source"]:checked');
    return picked ? picked.value : "paste";
  }

  function specVersionsNewestFirst() {
    if (state.specView) return state.specView.versions.map((summary) => summary.version);
    const latest = runOptions ? runOptions.latest_spec_version : 1;
    return Array.from({ length: latest }, (_, index) => latest - index);
  }

  // Samples and the seeded transcript default to the version they were made
  // with; a pasted chat defaults to the latest.
  function defaultSpecVersion(source) {
    const versions = specVersionsNewestFirst();
    if (source === "paste") return versions[0];
    const sample = samples.find((item) => `sample:${item.id}` === source);
    return sample ? sample.spec_version : versions[0];
  }

  function renderImportBody() {
    const choices = samples.map((sample) => {
      const seeded = sample.path !== null;
      const note = seeded
        ? `<span class="import__path">${escapeHtml(sample.path)}${sample.available ? "" : ". File not found"}</span>`
        : "";
      return `
        <label class="import__choice">
          <input type="radio" name="import-source" value="sample:${escapeHtml(sample.id)}"${sample.available ? "" : " disabled"}>
          <span><span>${escapeHtml(seeded ? sample.label : `Sample: ${sample.label}`)}</span>${note}</span>
        </label>`;
    });
    const versions = specVersionsNewestFirst()
      .map((version) => `<option value="${version}">${escapeHtml(specLabel(version))}</option>`)
      .join("");
    importBody.innerHTML = `
      <fieldset class="import__choices">
        <legend class="import__legend">Where is the chat?</legend>
        <label class="import__choice">
          <input type="radio" name="import-source" value="paste" checked>
          <span><span>Paste it, or choose a file</span></span>
        </label>
        ${choices.join("")}
      </fieldset>
      <div class="import__paste" data-import-paste>
        <div class="text-field">
          <textarea class="text-field__input import__text" id="import-text" rows="7" placeholder=" " aria-describedby="import-text-help"></textarea>
          <label class="text-field__label" for="import-text">Chat</label>
          <p class="text-field__support" id="import-text-help">One message per line, like "Alex: Hi." A receipt log, or a table with a speaker column, works too.</p>
        </div>
        <label class="import__file">
          <span>Or choose a file (.md, .txt, or .json)</span>
          <input type="file" id="import-file" accept=".md,.txt,.json,text/plain,text/markdown,application/json">
        </label>
        <div class="import__meta">
          <div class="text-field">
            <input class="text-field__input" id="import-tool" placeholder=" " autocomplete="off">
            <label class="text-field__label" for="import-tool">Tool (optional)</label>
          </div>
          <div class="text-field">
            <input class="text-field__input" id="import-receipt" placeholder=" " autocomplete="off">
            <label class="text-field__label" for="import-receipt">Receipt ID (optional)</label>
          </div>
        </div>
      </div>
      ${selectField("import-spec", "Spec version this chat used", versions, {
        support: "The chat stays pinned to this version.",
      })}
      <div class="import__preview" data-import-preview></div>`;

    importBody.querySelector("#import-spec").value = String(defaultSpecVersion("paste"));
    importBody.querySelectorAll('input[name="import-source"]').forEach((radio) => {
      radio.addEventListener("change", () => {
        const source = importSource();
        importBody.querySelector("[data-import-paste]").hidden = source !== "paste";
        importBody.querySelector("#import-spec").value = String(defaultSpecVersion(source));
        importBody.querySelector("[data-import-preview]").innerHTML = "";
      });
    });
    importBody.querySelector("#import-file").addEventListener("change", (event) => {
      const [file] = event.target.files;
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        importBody.querySelector("#import-text").value = String(reader.result);
        importBody.querySelector("[data-import-preview]").innerHTML = "";
        announce(`Read ${file.name}. Press Preview to check it.`);
      };
      reader.onerror = () => announce(`${file.name} couldn't be read.`);
      reader.readAsText(file);
    });
  }

  function importRequest() {
    const source = importSource();
    const picked = importBody.querySelector('input[name="import-role"]:checked');
    const body = {
      source: source === "paste" ? "paste" : "sample",
      character: runOptions.character.slug,
      spec_version: Number(importBody.querySelector("#import-spec").value),
      character_label: picked ? picked.value : null,
    };
    if (source === "paste") {
      body.text = importBody.querySelector("#import-text").value;
      body.tool = importBody.querySelector("#import-tool").value;
      body.receipt = importBody.querySelector("#import-receipt").value;
    } else {
      body.sample = source.slice("sample:".length);
    }
    return body;
  }

  function rowsText(rows) {
    if (rows.length === 0) return "";
    const shown = rows.slice(0, 12).join(", ");
    return rows.length > 12 ? `${shown}, and ${rows.length - 12} more` : shown;
  }

  function renderProblems(problems) {
    return `
      <div class="import__problems" tabindex="-1" data-import-problems>
        <p class="import__problems-title">
          <span class="icon" aria-hidden="true">error</span>
          <span>Fix ${problems.length === 1 ? "this row" : "these rows"}, then preview again.</span>
        </p>
        <ul>${problems.map((problem) => `<li>${escapeHtml(problem.message)}</li>`).join("")}</ul>
      </div>`;
  }

  function renderPreview(preview) {
    const word = preview.numbering === "line" ? "line" : "turn";
    const range = preview.first_number === null ? "" : ` (${word}s ${preview.first_number} to ${preview.last_number})`;
    const speakers = preview.speakers
      .map((speaker) => {
        const role = speaker.role === "character" ? ", the character" : speaker.role === "user" ? ", the other speaker" : "";
        return `<li>${escapeHtml(speaker.label)}: ${speaker.count} ${speaker.count === 1 ? "message" : "messages"}${role}</li>`;
      })
      .join("");
    const roles = preview.needs_roles
      ? `
        <fieldset class="import__roles">
          <legend class="import__legend">Which speaker is the character?</legend>
          ${preview.speakers
            .map((speaker) => `
              <label class="import__choice">
                <input type="radio" name="import-role" value="${escapeHtml(speaker.label)}">
                <span><span>${escapeHtml(speaker.label)}</span></span>
              </label>`)
            .join("")}
        </fieldset>`
      : "";
    const row = (item) => `
      <li>
        <span class="import__row-meta">${escapeHtml(item.label)}, ${word} ${item.number}${item.injection
          ? `<span class="visually-hidden">,</span> ${injectionStatus("import__row-injection", { explain: false })}`
          : ""}</span>
        <span class="import__row-text">${escapeHtml(item.text)}</span>
      </li>`;
    const gap = preview.last_rows.length && preview.message_count > preview.first_rows.length + preview.last_rows.length
      ? '<li class="import__row-gap" aria-hidden="true">...</li>'
      : "";
    const removed = removedNote(preview.removed);
    const injected = injectionNote(preview);
    return `
      <div class="import-preview">
        <p class="import-preview__summary">${escapeHtml(preview.title)}: ${preview.message_count} ${preview.message_count === 1 ? "message" : "messages"}${escapeHtml(range)}, pinned to ${escapeHtml(specLabel(preview.spec_version))}.</p>
        <ul class="import-preview__speakers">${speakers}</ul>
        ${roles}
        <ol class="import-preview__rows">${preview.first_rows.map(row).join("")}${gap}${preview.last_rows.map(row).join("")}</ol>
        ${removed
          ? `<p class="import-preview__note import-preview__note--icon"><span class="icon" aria-hidden="true">privacy_tip</span><span>${escapeHtml(removed)}</span></p>`
          : ""}
        ${injected
          ? `<p class="import-preview__note import-preview__note--icon"><span class="icon" aria-hidden="true">gpp_maybe</span><span>${escapeHtml(injected)}</span></p>`
          : ""}
        ${preview.skipped_rows.length ? `<p class="import-preview__note">Skipped ${preview.skipped_rows.length} ${preview.skipped_rows.length === 1 ? "line that isn't a message" : "lines that aren't messages"} (rows ${escapeHtml(rowsText(preview.skipped_rows))}).</p>` : ""}
        ${preview.duplicate_of ? '<p class="import-preview__note">This chat is already imported. Import shows the saved chat.</p>' : ""}
        ${preview.problems.length ? renderProblems(preview.problems) : ""}
      </div>`;
  }

  // "Removed 3 items before saving: 1 email, 1 phone number, and 1 key. Each
  // shows as a label, like [email removed]." Empty when nothing was removed.
  function removedNote(removed) {
    const parts = removedParts(removed);
    if (!parts.length) return "";
    const total = REMOVED_KINDS.reduce((sum, [field]) => sum + removed[field], 0);
    const [, , , label] = REMOVED_KINDS.find(([field]) => removed[field] > 0);
    return `Removed ${total} ${total === 1 ? "item" : "items"} before saving: ${listText(parts)}. ${total === 1 ? "It shows" : "Each shows"} as a label, like ${label}.`;
  }

  // "Turn 3 reads like an instruction to the AI, so it's marked as possible
  // injection. The AI judge reads it as chat data." Empty when no line does.
  function injectionNote(preview) {
    const numbers = preview.injection_numbers || [];
    if (!numbers.length) return "";
    const one = numbers.length === 1;
    const word = capitalized(preview.numbering === "line" ? "line" : "turn");
    return `${word}${one ? "" : "s"} ${listText(numbers.map(String))} ${one ? "reads" : "read"} like an instruction to the AI, so ${one ? "it's" : "they're"} marked as possible injection. The AI judge reads ${one ? "it" : "them"} as chat data.`;
  }

  actions["open-import"] = (button) => {
    if (state.live || !runOptions) return;
    renderImportBody();
    openDialog(importDialog, button);
  };

  actions["preview-import"] = async () => {
    if (importBusy) return;
    importBusy = true;
    const area = importBody.querySelector("[data-import-preview]");
    try {
      const preview = await WorkbenchApi.previewImport(importRequest());
      area.innerHTML = renderPreview(preview);
      const speakers = `${preview.speakers.length} ${preview.speakers.length === 1 ? "speaker" : "speakers"}`;
      const problems = preview.problems.length
        ? `${preview.problems.length} ${preview.problems.length === 1 ? "problem" : "problems"}`
        : "no problems";
      const notes = [removedNote(preview.removed), injectionNote(preview)].filter(Boolean).map((note) => ` ${note}`).join("");
      announce(`${preview.message_count} messages, ${speakers}, ${problems}.${notes}${preview.needs_roles ? " Say which speaker is the character." : ""}`);
      const problemBox = area.querySelector("[data-import-problems]");
      if (problemBox) problemBox.focus();
    } catch (error) {
      area.innerHTML = error.problems && error.problems.length
        ? renderProblems(error.problems)
        : `<p class="import__problems" tabindex="-1" data-import-problems>${escapeHtml(error.message)}</p>`;
      announce(error.message);
      area.querySelector("[data-import-problems]").focus();
    } finally {
      importBusy = false;
    }
  };

  actions["confirm-import"] = async () => {
    if (importBusy) return;
    importBusy = true;
    const area = importBody.querySelector("[data-import-preview]");
    try {
      const known = new Set(state.chats.map((chat) => chat.id));
      const chat = await WorkbenchApi.importChat(importRequest());
      importDialog.close();
      state.runError = null;
      state.chatId = chat.id;
      state.chat = chat;
      rememberChat(chat.id);
      updateChatSummary(chat);
      refreshRun({ focusKey: "run-chat" });
      loadCheck(chat.id);
      showSnackbar(known.has(chat.id)
        ? `Already imported. Showing ${chat.title}.`
        : `Imported ${chat.title}. It's pinned to spec ${specLabel(chat.spec_version)}.`);
    } catch (error) {
      area.innerHTML = error.problems && error.problems.length
        ? renderProblems(error.problems)
        : `<p class="import__problems" tabindex="-1" data-import-problems>${escapeHtml(error.message)}</p>`;
      announce(error.message);
      area.querySelector("[data-import-problems]").focus();
    } finally {
      importBusy = false;
    }
  };

  // 3.2.2 Check a chat ------------------------------------------------------
  // Check this chat runs the automatic checks on every finished reply, then
  // has the AI judge review the whole chat in one model call. The results
  // here sum the check up, and the flags themselves go to Flag review, where
  // the creator makes the call on each one. The server keeps every check, so
  // coming back to a chat shows its check with no new call, until the chat
  // changes.

  // state.checks[chatId] is { status, view, message, retry }. status is
  // "loading", "none" (not checked as it stands), "running" (this tab is
  // checking it), "elsewhere" (another tab is), "ready" (view holds the
  // results), or "failed" (the request failed; retry is "check" or "look").

  function readyCheck(chatId) {
    const check = state.checks[chatId];
    return check && check.status === "ready" ? check.view : null;
  }

  function hasFinishedReply(chat) {
    return chat.messages.some((message) => message.speaker === "character" && !message.stopped && message.text.trim());
  }

  function checkRunning(chatId) {
    return Boolean(state.checks[chatId] && state.checks[chatId].status === "running");
  }

  // "3, 4, and 6"
  function listText(items) {
    if (items.length <= 2) return items.join(" and ");
    return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
  }

  // What redaction took out, as ["1 email", "2 phone numbers"], with the label each kind shows as.
  const REMOVED_KINDS = [
    ["emails", "email", "emails", "[email removed]"],
    ["phone_numbers", "phone number", "phone numbers", "[phone number removed]"],
    ["keys", "key", "keys", "[key removed]"],
  ];

  function removedParts(removed) {
    if (!removed) return [];
    return REMOVED_KINDS.filter(([field]) => removed[field] > 0)
      .map(([field, one, many]) => `${removed[field]} ${removed[field] === 1 ? one : many}`);
  }

  // What a cited line or field is, for screen readers: "behavior rule", or "spec field" for a label like Voice.
  function citeMeaning(lineId) {
    return /^[A-Z][0-9]+$/.test(lineId) && LINE_MEANINGS[lineId[0]] ? LINE_MEANINGS[lineId[0]] : "spec field";
  }

  function capitalized(word) {
    return word.charAt(0).toUpperCase() + word.slice(1);
  }

  // Loads the saved check, which never calls a model, and redraws if the chat
  // is on screen. focusKey names a control of the check, like Check this chat,
  // that focus was meant for: it moves there once drawn, if focus is still on
  // the screen's heading, where it went while the control wasn't there yet.
  async function loadCheck(chatId, { focusKey = null } = {}) {
    if (checkRunning(chatId)) return;
    if (!state.checks[chatId]) state.checks[chatId] = { status: "loading", view: null, message: "", retry: null };
    let next;
    try {
      const found = await WorkbenchApi.getCheck(chatId);
      next = found.result
        ? { status: "ready", view: found.result, message: "", retry: null }
        : { status: found.running ? "elsewhere" : "none", view: null, message: "", retry: null };
    } catch (error) {
      next = { status: "failed", view: null, message: `The saved check didn't load. ${error.message}`, retry: "look" };
    }
    if (checkRunning(chatId)) return;
    state.checks[chatId] = next;
    if (state.chatId !== chatId) return;
    const heading = currentScreen === "run" ? panelFor("run").querySelector(".screen__title") : null;
    refreshRun(focusKey && heading && document.activeElement === heading ? { focusKey } : {});
  }

  // "8 flags: 1 from automatic checks and 7 from the AI judge." After a
  // re-check: "8 flags: 1 from automatic checks, 6 from the AI judge, and 1
  // from its re-check."
  function checkSummary(view) {
    const total = view.flags.length;
    const fromRules = view.flags.filter((flag) => flag.source === "rule").length;
    const fromRecheck = view.flags.filter((flag) => flag.source === "recheck").length;
    const noun = total === 1 ? "flag" : "flags";
    if (total === 0) {
      return view.judge.status === "ok"
        ? "No flags. The automatic checks and the AI judge found no breaks."
        : "No flags from the automatic checks.";
    }
    if (view.judge.status === "ok") {
      return fromRecheck
        ? `${total} ${noun}: ${fromRules} from automatic checks, ${total - fromRules - fromRecheck} from the AI judge, and ${fromRecheck} from its re-check.`
        : `${total} ${noun}: ${fromRules} from automatic checks and ${total - fromRules} from the AI judge.`;
    }
    return `${total} ${noun}, all from automatic checks.`;
  }

  // "1 flag hidden: its quote wasn't in the chat." What changed says "new flag".
  function hiddenText(chat, item, noun = "flag") {
    const one = item.count === 1;
    const word = numberWord(chat).toLowerCase();
    const spec = specLabel(chat.spec_version);
    const reasons = {
      quote_not_found: one ? "its quote wasn't in the chat" : "their quotes weren't in the chat",
      quote_other_turn: one ? `its quote was from a different ${word}` : `their quotes were from different ${word}s`,
      quote_from_user: `${one ? "its quote was" : "their quotes were"} ${chat.user_name}'s words, not ${chat.character_name}'s`,
      unknown_line: one ? `it cited a line that isn't in spec ${spec}` : `they cited lines that aren't in spec ${spec}`,
      not_a_reply: one
        ? `its ${word} has no finished reply from ${chat.character_name}`
        : `their ${word}s have no finished reply from ${chat.character_name}`,
    };
    return `${item.count} ${one ? noun : `${noun}s`} hidden: ${reasons[item.reason]}.`;
  }

  // "AI judge: Gemini 3.5 Flash-Lite", "(fallback)" after one, or "unavailable" when it gave no answer.
  function judgeText(judge) {
    if (judge.status !== "ok") return "AI judge: unavailable";
    return `AI judge: ${judge.model_label}${judge.fallback ? " (fallback)" : ""}`;
  }

  function checkButton(label, focusKey) {
    return `
      <button type="button" class="btn btn--filled btn--icon-leading" data-action="check-chat" data-focus-key="${focusKey}">
        <span class="icon" aria-hidden="true">fact_check</span>
        <span>${label}</span>
      </button>`;
  }

  // Below the transcript: the button, the check under way, or the results.
  function renderCheck(chat) {
    if (!hasFinishedReply(chat)) return "";
    const check = state.checks[chat.id];
    if (!check || check.status === "loading") return "";
    if (check.status === "ready") return renderCheckResults(chat, check.view);

    if (check.status === "running" || check.status === "elsewhere") {
      const here = check.status === "running";
      return `
        <div class="card card--outlined check-start">
          <span class="icon" aria-hidden="true">hourglass_top</span>
          <div class="check-start__text">
            <p class="check-start__title" tabindex="-1" data-focus-key="check-status">Checking this chat</p>
            <p class="check-start__body">${here
              ? "The automatic checks run first. Then the AI judge reads the whole chat in one call, which can take a minute."
              : "A check of this chat started in another tab or before a reload. Look again in a moment."}</p>
            ${here ? `${elapsedLine(check.startedAt)}<div class="check-progress" aria-hidden="true"></div>${decorScan()}` : ""}
          </div>
          ${here
            ? ""
            : '<button type="button" class="btn btn--outlined" data-action="reload-check" data-focus-key="reload-check">Look again</button>'}
        </div>`;
    }

    if (check.status === "failed") {
      return `
        <div class="card card--outlined run-error">
          <span class="icon" aria-hidden="true">error</span>
          <p class="run-error__text">${escapeHtml(check.message)}</p>
          ${mentionsSettings(check.message) ? settingsButton("check-error-settings") : ""}
          ${check.retry === "look"
            ? '<button type="button" class="btn btn--filled" data-action="reload-check" data-focus-key="reload-check">Look again</button>'
            : checkButton("Try again", "check-chat")}
        </div>`;
    }

    return `
      <div class="card card--outlined check-start">
        <span class="icon" aria-hidden="true">fact_check</span>
        <div class="check-start__text">
          <p class="check-start__title">Check this chat for breaks</p>
          <p class="check-start__body">Automatic checks count sentences and look for banned words in every reply from ${escapeHtml(chat.character_name)}. Then an AI judge reads the whole chat once and flags each break with a quote and the spec line it breaks. That's one model call, or two if the first answer can't be read.</p>
        </div>
        ${checkButton("Check this chat", "check-chat")}
      </div>`;
  }

  function renderCheckResults(chat, view) {
    const judge = view.judge;
    const effort = judge.reasoning_effort ? ` at ${judge.reasoning_effort} reasoning effort` : "";
    const notes = [];
    if (judge.status !== "ok") {
      notes.push(`
        <li class="check__note check__note--error">
          <span class="icon" aria-hidden="true">error</span>
          <span class="check__note-text">${escapeHtml(judge.note)}</span>
          ${mentionsSettings(judge.note) ? settingsButton("judge-note-settings") : ""}
          ${checkButton("Try again", "check-chat")}
        </li>`);
    }
    view.hidden.forEach((item) => {
      notes.push(`
        <li class="check__note">
          <span class="icon" aria-hidden="true">visibility_off</span>
          <span class="check__note-text">${escapeHtml(hiddenText(chat, item))}</span>
        </li>`);
    });
    if (judge.fallback) {
      notes.push(`
        <li class="check__note">
          <span class="icon" aria-hidden="true">swap_horiz</span>
          <span class="check__note-text">The AI judge's own model stayed busy, so its fallback model, ${escapeHtml(judge.model_label)}, read the chat.</span>
        </li>`);
    }
    if (judge.same_model) {
      notes.push(`
        <li class="check__note">
          <span class="icon" aria-hidden="true">sync_problem</span>
          <span class="check__note-text">The AI judge is the same model that wrote some of these replies, so it may miss its own mistakes. Those flags say "Same model reviewed."</span>
        </li>`);
    }
    return `
      <section class="check" aria-labelledby="check-title">
        <div class="check__head">
          <h2 class="check__title" id="check-title" tabindex="-1" data-focus-key="check-results">Check results</h2>
          ${chip("description", `Spec ${specLabel(view.spec_version)}`)}
          ${chip("smart_toy", judgeText(judge))}
        </div>
        <p class="check__source">Checked ${escapeHtml(chatTime(judge.checked_at))}${escapeHtml(effort)}.${view.cached
          ? " Shown from the saved check, with no new model call."
          : ""}</p>
        <p class="check__summary">${escapeHtml(checkSummary(view))}</p>
        ${notes.length ? `<ul class="check__notes">${notes.join("")}</ul>` : ""}
        ${renderCheckReview(chat, view)}
        ${renderCheckGaps(chat, view)}
      </section>`;
  }

  // Where the flags went: how many still need the creator's call, from the
  // saved calls once they have loaded, and the way to Flag review.
  function renderCheckReview(chat, view) {
    if (view.flags.length === 0) return "";
    const item = reviewItem(chat.id);
    let text = "";
    if (item) {
      const open = item.open_calls;
      text = open === 0
        ? "Every flag has your call."
        : `${open} ${open === 1 ? "flag needs" : "flags need"} your call on Flag review.`;
    }
    return `
      <div class="check-review">
        ${text ? `<p class="check-review__text">${escapeHtml(text)}</p>` : ""}
        <button type="button" class="btn btn--filled btn--icon-leading" data-action="review-flags" data-chat="${chat.id}"
          data-focus-key="review-flags">
          <span class="icon" aria-hidden="true">flag</span>
          <span>Review flags</span>
        </button>
      </div>`;
  }

  // What the judge said the spec and the chat can't settle. Flag review shows
  // it too, under its own heading ID.
  function renderCheckGaps(chat, view, titleId = "check-gaps-title") {
    if (view.not_checked.length === 0) return "";
    const word = numberWord(chat).toLowerCase();
    const items = view.not_checked.map((gap) => `
      <div class="not-checked__item">
        <p><span class="flag-card__label">${escapeHtml(gap.topic)}.</span> ${escapeHtml(gap.why)}</p>
        ${gap.turns.length > 0
          ? `<p class="flag-card__also">${capitalized(word)}${gap.turns.length === 1 ? "" : "s"} ${escapeHtml(listText(gap.turns))}</p>`
          : ""}
      </div>`);
    return `
      <section class="card card--outlined not-checked" aria-labelledby="${titleId}">
        <h3 class="not-checked__title" id="${titleId}">
          <span class="icon" aria-hidden="true">visibility_off</span>
          <span>Not checked by the AI</span>
        </h3>
        ${items.join("")}
      </section>`;
  }

  actions["check-chat"] = async (button) => {
    const chat = state.chat;
    if (!chat || isLive(chat.id) || checkRunning(chat.id) || (button && button.getAttribute("aria-disabled") === "true")) return;
    const chatId = chat.id;
    state.checks[chatId] = { status: "running", view: null, message: "", retry: null, startedAt: Date.now() };
    refreshRun({ focusKey: "check-status" });
    announce("Checking this chat. The AI judge can take a minute.");
    startElapsedTimer();
    try {
      const view = await WorkbenchApi.checkChat(chatId);
      state.checks[chatId] = { status: "ready", view, message: "", retry: null };
      if (state.chatId === chatId) {
        refreshRun({ focusKey: "check-results" });
        announce(`Check done. ${checkSummary(view)}`);
      }
    } catch (error) {
      state.checks[chatId] = { status: "failed", view: null, message: error.message, retry: "check" };
      if (state.chatId === chatId) {
        refreshRun({ focusKey: "check-chat" });
        announce(error.message);
      }
    }
    // The judge's calls count toward today's total, shown by Start run.
    loadRunOptions();
    // The new check's flags go to Flag review and its badge.
    loadReview();
  };

  actions["reload-check"] = () => {
    if (!state.chat) return;
    delete state.checks[state.chat.id];
    loadCheck(state.chat.id);
  };

  // 3.3 Flag review (Diagnose) ----------------------------------------------
  // The heart of the workbench: the AI proposes flags, and the creator makes
  // the call on each one (DESIGN_SPEC 7.1 to 7.4). The flags come from the
  // saved checks, and the server saves every call with its time.
  // - Evidence first: Agree unlocks only after "Show in context", and the
  //   server refuses an Agree before the evidence was opened.
  // - An override needs a reason of at least 3 words. It may name the right
  //   type instead, and then the flag still counts as a break.
  // - Agree and Override look the same, so the screen doesn't push agreement.
  // - Agreeing with every flag triggers a rubber-stamp check.
  // - What the AI could not check is listed for the creator to read.
  // - The follow-up re-check (DESIGN_SPEC 7.2) looks again at the AI's
  //   weakest flags, with the creator's question if they ask one. What
  //   changed lists what it did, and a flag where it and the creator's call
  //   (or the first pass) disagree shows both views (DESIGN_SPEC 7.4).
  // Every call redraws the screen from the server's answer; announceReview()
  // tells screen readers.

  const CONFIDENCE_FILTERS = ["All", "High", "Medium", "Low"];
  const RUBBER_STAMP_MESSAGE =
    "You agreed with every flag. The AI makes mistakes too, so check again whether each one is really a break.";

  // Why the spec alone can't settle a flag, for the flags code sends to the
  // creator: persona exits, guesses near the knowledge boundary, and lines
  // the spec marks.
  const NEEDS_CALL_TEXT = {
    persona_exit: () => "The character stepped out of the role. Only you can judge how much that matters.",
    near_guess: (chat) => `A guess near what ${chat.character_name} can't know. Only you can tell a guess from a leak.`,
    unsure_boundary: () => "The AI isn't sure this crosses the knowledge boundary, so it's yours to decide.",
    line: () => "The spec marks this line for your call.",
    judge: () => "The AI judge left this one to you.",
  };

  // Where a flag came from, as its chip's icon and words.
  const SOURCE_CHIPS = {
    rule: ["rule", "Automatic check"],
    judge: ["smart_toy", "AI judge"],
    recheck: ["manage_search", "AI re-check"],
  };

  // Why a flag the re-check would withdraw stayed in the review.
  const KEPT_BECAUSE_TEXT = {
    needs_call: "only you can settle it",
    your_call: "it has your call",
  };

  // The groups in What changed, in order. "stayed" holds the flags the
  // re-check would withdraw but that stayed for the creator's call, and
  // "against" the ones it still calls breaks after the creator said they aren't.
  const CHANGE_GROUPS = [
    { key: "added", title: "Added", icon: "add_circle" },
    { key: "withdrawn", title: "Withdrawn", icon: "remove_circle" },
    { key: "rerated", title: "Re-rated", icon: "swap_vert" },
    { key: "stayed", title: "Stayed for your call", icon: "pending" },
    { key: "against", title: "Kept against your call", icon: "compare_arrows" },
  ];

  // Counts review loads, so only the newest one changes the screen.
  let reviewRequest = 0;
  // A review load is on its way.
  let reviewLoading = false;
  // Flags with a call on its way to the server, so a second click waits.
  const reviewPending = new Set();
  // Evidence openings on their way to the server, by flag ID, so an Agree
  // pressed right after "Show in context" waits for the opening to land.
  const evidenceRequests = new Map();

  // Measures the sticky summary bar, so the CSS can keep keyboard focus from
  // scrolling under it (see --review-bar-height in styles.css).
  const reviewBarObserver = "ResizeObserver" in window
    ? new ResizeObserver((entries) => {
        const height = entries[0].target.offsetHeight;
        document.documentElement.style.setProperty("--review-bar-height", `${height}px`);
      })
    : null;

  function reviewChats() {
    return state.review ? state.review.chats : [];
  }

  function reviewItem(chatId) {
    return reviewChats().find((item) => item.chat.id === chatId) || null;
  }

  // The chat on screen: the one picked, else the chat on Run a conversation
  // if it was checked, else the first with calls left, else the first.
  function selectedReview() {
    const chats = reviewChats();
    return reviewItem(state.reviewChatId) || reviewItem(state.chatId)
      || chats.find((item) => item.open_calls > 0) || chats[0] || null;
  }

  // How Flag review names a chat: an imported chat by its title, like
  // "Claude (CLA-F2)", and a live run by its scenario, model, and start time.
  function reviewLabel(chat) {
    if (chat.kind !== "live") return chat.title;
    return `${chat.scenario} live run, ${modelLabel(chat.model)}, ${chatTime(chat.created_at)}`;
  }

  // Loads the saved checks and calls, then redraws what shows them. A load
  // that found nothing new redraws nothing, so a reason being typed while a
  // run plays keeps its place. A reply streaming on Run a conversation is
  // never redrawn by this.
  async function loadReview({ focusKey = null } = {}) {
    const ticket = ++reviewRequest;
    reviewLoading = true;
    let changed;
    try {
      const review = await WorkbenchApi.getReview();
      if (ticket !== reviewRequest) return;
      changed = state.reviewLoad.status !== "ready" || JSON.stringify(review) !== JSON.stringify(state.review);
      state.review = review;
      state.reviewLoad = { status: "ready", message: "" };
    } catch (error) {
      if (ticket !== reviewRequest) return;
      changed = state.reviewLoad.status !== "failed" || state.reviewLoad.message !== error.message;
      state.reviewLoad = { status: "failed", message: error.message };
    }
    reviewLoading = false;
    if (!changed && !focusKey) return;
    if (currentScreen === "diagnose" || currentScreen === "compare") refresh({ focusKey });
    else if (currentScreen === "run" && !state.live) refresh();
    else updateTodoBadge();
  }

  // Puts a chat's review, as a call answered it, in place of the one on
  // screen, unless the one on screen saw a later call. A review load that
  // started before this answer may not have the call, so a fresh one starts.
  function replaceReviewChat(updated) {
    if (reviewLoading) loadReview();
    if (!state.review) return;
    const chats = state.review.chats;
    const index = chats.findIndex((item) => item.chat.id === updated.chat.id);
    if (index === -1 || chats[index].last_event_id > updated.last_event_id) return;
    chats[index] = updated;
    state.review.open_calls = chats.reduce((sum, item) => sum + item.open_calls, 0);
  }

  // Redraws the screen that shows the review, or only the badge elsewhere.
  function redrawReview() {
    if (currentScreen === "diagnose" || currentScreen === "compare") refresh();
    else updateTodoBadge();
  }

  // A call the server refused or couldn't take. A 409 means this tab's view
  // is out of date, so the review loads again.
  function reviewError(error) {
    showSnackbar(error.message);
    if (error.status === 409) loadReview();
  }

  function countWords(text) {
    return text.trim().split(/\s+/).filter(Boolean).length;
  }

  // "At least 3 words. 2 of 3 words." under an override's reason, so a Save
  // that is off says why. Once the reason is long enough: "At least 3 words. 4 words."
  function wordCountText(text) {
    const min = state.review.min_reason_words;
    const count = countWords(text);
    return `At least ${min} words. ${count < min ? `${count} of ${min}` : count} words.`;
  }

  // "agreed", "retyped" (overridden with the right type, so still a break),
  // "overridden", or null while the flag needs the creator's call.
  function verdictOf(flag) {
    if (!flag.call) return null;
    if (flag.call.verdict === "agreed") return "agreed";
    return flag.call.type ? "retyped" : "overridden";
  }

  // "6 flags, 2 agreed, 1 overridden. First break: turn 3." Retyped flags
  // show only when there are some. The first break is the earliest flag that
  // still counts as one.
  function reviewSummary(item) {
    const flags = item.flags;
    const count = (verdict) => flags.filter((flag) => verdictOf(flag) === verdict).length;
    const retyped = count("retyped");
    const noun = flags.length === 1 ? "flag" : "flags";
    const firstBreak = item.first_break === null ? "none" : `${numberWord(item.chat).toLowerCase()} ${item.first_break}`;
    return `${flags.length} ${noun}, ${count("agreed")} agreed, ${retyped ? `${retyped} retyped, ` : ""}${count("overridden")} overridden. First break: ${firstBreak}.`;
  }

  // A checked chat with no flags gets one line instead of an empty list. It
  // stays true when only the automatic checks ran.
  function noFlagsText(item) {
    return item.judge.status === "ok"
      ? "No flags in this chat. The automatic checks and the AI judge found nothing to decide."
      : "No flags in this chat. The automatic checks found nothing to decide, and the AI judge didn't finish.";
  }

  function visibleFlags(flags, filter) {
    return filter === "All" ? flags : flags.filter((flag) => capitalized(flag.confidence) === filter);
  }

  // "Turn 4, knowledge-boundary violation"
  function flagTitle(chat, flag) {
    return `${numberWord(chat)} ${flag.turn}, ${flag.type}`;
  }

  function cardId(flag) {
    return `flag-${flag.id}`;
  }

  function renderDiagnose(body) {
    if (!state.review) {
      body.innerHTML = state.reviewLoad.status === "failed"
        ? `
          <div class="card card--outlined spec-empty">
            <p>The saved flags didn't load. ${escapeHtml(state.reviewLoad.message)}</p>
            <button type="button" class="btn btn--filled" data-action="retry-review" data-focus-key="retry-review">Try again</button>
          </div>`
        : '<p class="spec-status">Loading the saved flags.</p>';
      return null;
    }
    const item = selectedReview();
    if (!item) {
      body.innerHTML = `
        <div class="review">
          ${renderChangedChats()}
          ${renderNoCheckedChats()}
        </div>`;
      return null;
    }
    // Keeps this chat on screen while calls change which chats have calls left.
    state.reviewChatId = item.chat.id;
    const flags = item.flags;

    // Arriving from "Go to flag": make sure that flag shows, then land on it.
    const target = flags.find((flag) => flag.id === state.openFlagId) || null;
    state.openFlagId = null;
    if (target) {
      if (visibleFlags([target], state.flagFilter).length === 0) state.flagFilter = "All";
      state.reviewTurn = target.turn;
    }

    const shown = visibleFlags(flags, state.flagFilter);
    let cards = "";
    if (shown.length > 0) {
      cards = `<ol class="flag-cards">${shown.map((flag) => `<li>${renderFlagCard(item, flag)}</li>`).join("")}</ol>`;
    } else if (flags.length > 0) {
      cards = `<p class="card card--outlined flag-cards__empty">No ${state.flagFilter.toLowerCase()}-confidence flags in this chat.</p>`;
    }
    const bar = flags.length > 0
      ? `
        <p class="review__summary">${escapeHtml(reviewSummary(item))}</p>
        ${item.agreed_with_every
          ? `<p class="review__nudge">
              <span class="icon" aria-hidden="true">fact_check</span>
              <span>${RUBBER_STAMP_MESSAGE}</span>
            </p>`
          : ""}
        ${renderFlagFilters()}`
      : `<p class="review__empty">${escapeHtml(noFlagsText(item))}</p>`;

    body.innerHTML = `
      <div class="review">
        <div class="review__main">
          ${renderChangedChats()}
          <div class="review__bar-wrap">
            ${renderChatSwitcher(item)}
            <div class="review__bar">${bar}</div>
          </div>
          ${renderCheckSource(item)}
          ${renderWhatChanged(item)}
          <h2 class="visually-hidden">Flags</h2>
          ${cards}
          ${renderFollowUp(item)}
          ${renderCheckGaps(item.chat, item, "not-checked-title")}
        </div>
        ${renderConversation(item)}
      </div>`;

    body.querySelectorAll("[data-reason-for]").forEach((field) => {
      const flagId = field.dataset.reasonFor;
      field.addEventListener("input", () => {
        state.overrideDrafts[flagId] = field.value;
        // Typing again puts the word count back in place of the server's refusal.
        if (state.overrideErrors[flagId]) {
          delete state.overrideErrors[flagId];
          field.removeAttribute("aria-invalid");
          field.closest(".text-field").classList.remove("text-field--error");
        }
        const ready = countWords(field.value) >= state.review.min_reason_words;
        body.querySelector(`#reason-${flagId}-help`).textContent = wordCountText(field.value);
        const save = body.querySelector(`[data-focus-key="save-${flagId}"]`);
        save.setAttribute("aria-disabled", String(!ready));
        if (ready) save.removeAttribute("aria-describedby");
        else save.setAttribute("aria-describedby", `reason-${flagId}-help`);
      });
      // Escape closes the reason field, the same as Cancel.
      field.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        event.preventDefault();
        cancelOverride(flagId);
      });
    });
    body.querySelectorAll("[data-type-for]").forEach((menu) => {
      menu.addEventListener("change", () => {
        state.overrideTypes[menu.dataset.typeFor] = menu.value;
      });
    });
    // Typing the question only updates the draft, since the field already shows it.
    const question = body.querySelector("[data-question-for]");
    if (question) {
      question.addEventListener("input", () => {
        state.recheckDrafts[question.dataset.questionFor] = question.value;
      });
    }
    const picker = body.querySelector("#review-chat");
    if (picker) picker.addEventListener("change", () => pickReviewChat(Number(picker.value), "review-chat"));
    if (reviewBarObserver) {
      reviewBarObserver.disconnect();
      reviewBarObserver.observe(body.querySelector(".review__bar-wrap"));
    }

    if (!target) return null;
    revealTurn(body);
    return body.querySelector(`#${cardId(target)}`);
  }

  // Flag review and Compare runs before any chat is checked: the words, with
  // the mascot and faint line IDs beside them.
  function renderNoCheckedChats() {
    return `
      <div class="card card--outlined flag-cards__empty empty-state">
        ${decorScene("ids")}
        <p class="empty-state__text">No checked chats yet. On Run a conversation, open a chat and press Check this chat.</p>
        <button type="button" class="btn btn--filled" data-action="go-to-screen" data-screen="run" data-focus-key="go-to-run">Go to Run a conversation</button>
      </div>`;
  }

  // When the chat was checked and which judge read it, plus the judge's note
  // when only the automatic checks ran.
  function renderCheckSource(item) {
    const judge = item.judge;
    const note = judge.status === "ok" ? "" : ` ${judge.note}`;
    return `<p class="review__source">Checked ${escapeHtml(chatTime(judge.checked_at))}. ${escapeHtml(judgeText(judge))}.${escapeHtml(note)}</p>`;
  }

  // The flags the follow-up re-check looks at again: the AI's, rated Low or Medium.
  function weakFlags(item) {
    return item.flags.filter((flag) => flag.source !== "rule" && (flag.confidence === "low" || flag.confidence === "medium"));
  }

  // Which group of What changed a change goes in. A flag the re-check kept or
  // re-rated that is now disputed goes in "against", since the creator overrode it.
  function changeGroup(item, change) {
    if (change.kept_because) return "stayed";
    const flag = item.flags.find((found) => found.id === change.flag_id);
    return flag && flag.disputed ? "against" : change.change;
  }

  // What changed in the latest re-check of this chat's check (DESIGN_SPEC
  // 7.2): the flags it added, withdrew, and re-rated, each with its one-line
  // reason, the ones it would withdraw that stayed for the creator's call,
  // and its answer to the creator's question. A withdrawn flag is gone from
  // the flags below, so its evidence shows here.
  function renderWhatChanged(item) {
    const recheck = item.recheck;
    if (!recheck) return "";
    const chat = item.chat;
    const shown = state.rechecks[chat.id];
    const saved = Boolean(shown && shown.status === "saved" && shown.id === recheck.id);
    const source = `Re-checked ${chatTime(recheck.checked_at)}. AI judge: ${recheck.model_label}.${saved
      ? " Shown from the saved re-check, with no new model call."
      : ""}`;
    const head = `
      <h2 class="what-changed__title" id="what-changed-title" tabindex="-1" data-focus-key="what-changed">
        <span class="icon" aria-hidden="true">published_with_changes</span>
        <span>What changed in the re-check</span>
      </h2>
      <p class="what-changed__source">${escapeHtml(source)}</p>`;

    if (recheck.status !== "ok") {
      return `
        <section class="card card--outlined what-changed" aria-labelledby="what-changed-title">
          ${head}
          <p class="what-changed__error">
            <span class="icon" aria-hidden="true">error</span>
            <span>${escapeHtml(recheck.note)}</span>
          </p>
        </section>`;
    }

    const looked = recheck.picked === 0
      ? "No flags were rated Low or Medium, so it read the chat again for anything missed."
      : `It looked again at ${recheck.picked === 1 ? "the one flag" : `the ${recheck.picked} flags`} rated Low or Medium, and read the chat again for anything missed.`;
    const question = recheck.question
      ? `
        <div class="what-changed__qa">
          <p><span class="flag-card__label">Your question:</span> <span class="keep-lines">${escapeHtml(recheck.question)}</span></p>
          <p><span class="flag-card__label">The AI's answer:</span> <span class="keep-lines">${escapeHtml(recheck.answer || "It gave no answer.")}</span></p>
          <p class="what-changed__hint">The answer is the AI's own words. Only its flags pass the evidence checks.</p>
        </div>`
      : "";
    const groups = CHANGE_GROUPS.map((group) => {
      const changes = recheck.changes.filter((change) => changeGroup(item, change) === group.key);
      if (changes.length === 0) return "";
      const id = `what-changed-${group.key}`;
      return `
        <section class="what-changed__group" aria-labelledby="${id}">
          <h3 class="what-changed__group-title" id="${id}">
            <span class="icon" aria-hidden="true">${group.icon}</span>
            <span>${group.title} (${changes.length})</span>
          </h3>
          <ul class="what-changed__list">${changes.map((change) => renderChange(item, change)).join("")}</ul>
        </section>`;
    }).join("");

    const notes = [];
    const kept = recheck.changes.filter((change) => changeGroup(item, change) === "kept").length;
    if (!groups) {
      notes.push(recheck.picked > 0
        ? "Nothing changed. The re-check kept every flag it looked at and added none."
        : "Nothing changed. The re-check added no flags.");
    } else if (kept > 0) {
      notes.push(`Kept ${kept} ${kept === 1 ? "flag as it was" : "flags as they were"}.`);
    }
    recheck.hidden.forEach((hidden) => notes.push(hiddenText(chat, hidden, "new flag")));

    return `
      <section class="card card--filled what-changed" aria-labelledby="what-changed-title">
        ${head}
        <p class="what-changed__text">${escapeHtml(looked)}</p>
        ${question}
        ${groups}
        ${notes.length ? `<ul class="what-changed__notes">${notes.map((note) => `<li>${escapeHtml(note)}</li>`).join("")}</ul>` : ""}
      </section>`;
  }

  // One line of What changed: where the flag is, its quote, what the re-check
  // did and why, and Go to flag while the flag is still in the review.
  function renderChange(item, change) {
    const flag = item.flags.find((found) => found.id === change.flag_id) || null;
    const place = `${numberWord(item.chat)} ${change.turn}, ${change.type}, ${citeLabel(change.line_id)}`;
    let did = "";
    if (change.change === "rerated") {
      did = `${capitalized(change.from_confidence)} to ${capitalized(change.to_confidence)}. `;
    }
    if (change.kept_because) {
      did = `It would withdraw this flag, but ${KEPT_BECAUSE_TEXT[change.kept_because]}.${flag && flag.disputed ? " Both views are on its card." : ""} `;
    } else if (flag && flag.disputed) {
      did += "It still calls this a break, but your call stands. Both views are on its card. ";
    }
    return `
      <li class="what-changed__item">
        <p class="what-changed__place">${escapeHtml(place)}</p>
        <p class="keep-lines"><q>${escapeHtml(change.quote)}</q></p>
        <p>${escapeHtml(did)}<span class="flag-card__label">Why:</span> ${escapeHtml(change.why)}</p>
        ${flag
          ? `<button type="button" class="btn btn--text" data-action="go-to-flag" data-flag="${flag.id}"
              data-focus-key="change-${flag.id}">Go to flag<span class="visually-hidden">: ${escapeHtml(place)}</span></button>`
          : ""}
      </li>`;
  }

  // What a screen reader hears when a re-check ends: "Re-check done: 1
  // added, 1 withdrawn, and 1 re-rated." or "Re-check done. Nothing changed."
  function recheckSummary(item) {
    const recheck = item.recheck;
    if (!recheck) return "Re-check done.";
    if (recheck.status !== "ok") return recheck.note;
    const parts = CHANGE_GROUPS.map((group) => {
      const count = recheck.changes.filter((change) => changeGroup(item, change) === group.key).length;
      return count ? `${count} ${group.title.toLowerCase()}` : "";
    }).filter(Boolean);
    return parts.length ? `Re-check done: ${listText(parts)}.` : "Re-check done. Nothing changed.";
  }

  // The built-in follow-up (DESIGN_SPEC 7.2), after the flags: the AI judge's
  // model looks again at the flags it rated Low or Medium and reads the chat
  // again for anything missed, with the creator's question if they ask one.
  // The question box stays neutral, with no example questions, so it never
  // steers what a creator asks.
  function renderFollowUp(item) {
    const chat = item.chat;
    const title = `
      <h2 class="follow-up__title" id="follow-up-title">
        <span class="icon" aria-hidden="true">manage_search</span>
        <span>Follow-up re-check</span>
      </h2>`;
    if (item.judge.status !== "ok") {
      return `
        <section class="card card--outlined follow-up" aria-labelledby="follow-up-title">
          ${title}
          <p class="follow-up__text">The re-check needs the AI judge's first pass, which didn't finish for this chat. Check the chat again on Run a conversation first.</p>
          <div class="follow-up__actions">
            <button type="button" class="btn btn--outlined" data-action="check-changed-chat" data-chat="${chat.id}"
              data-focus-key="follow-up-go-run">Go to Run a conversation</button>
          </div>
        </section>`;
    }
    const weak = weakFlags(item).length;
    const text = weak === 0
      ? "No low or medium flags to re-check. It will still look for anything missed and answer your question."
      : `The AI judge looks again at the ${weak === 1 ? "one flag" : `${weak} flags`} it rated Low or Medium, Low first, and reads the chat again for anything it missed. It can keep, re-rate, or withdraw a flag, or add one, but it never withdraws a flag that only you can settle or that has your call.`;
    const recheck = state.rechecks[chat.id] || null;
    const running = Boolean(recheck && recheck.status === "running");
    const failed = recheck && recheck.status === "failed" ? recheck.message : "";
    const action = running
      ? `
        <div class="follow-up__status">
          <p class="check-start__title" tabindex="-1" data-focus-key="recheck-status">Re-checking this chat</p>
          <p class="check-start__body">The AI judge reads the chat again in one call, which can take a minute.</p>
          ${elapsedLine(recheck.startedAt)}
          <div class="check-progress" aria-hidden="true"></div>
          ${decorScan()}
        </div>`
      : `
        <div class="follow-up__actions">
          <button type="button" class="btn btn--filled btn--icon-leading" data-action="recheck" data-chat="${chat.id}"
            data-focus-key="recheck">
            <span class="icon" aria-hidden="true">manage_search</span>
            <span>${item.recheck ? "Re-check again" : "Re-check"}</span>
          </button>
          <p class="follow-up__cost">One model call, or two if the first answer can't be read.</p>
        </div>
        ${failed
          ? `<p class="follow-up__error">
              <span class="icon" aria-hidden="true">error</span>
              <span>${escapeHtml(failed)}</span>
            </p>
            ${mentionsSettings(failed) ? `<div class="follow-up__actions">${settingsButton("recheck-error-settings")}</div>` : ""}`
          : ""}`;
    return `
      <section class="card card--outlined follow-up" aria-labelledby="follow-up-title">
        ${title}
        <p class="follow-up__text">${escapeHtml(text)}</p>
        <div class="text-field follow-up__question">
          <textarea class="text-field__input" id="recheck-question" rows="2"
            placeholder="Ask about anything the first pass might have missed"
            maxlength="${state.review.max_reason_chars}" aria-describedby="recheck-question-help"${running ? " readonly" : ""}
            data-question-for="${chat.id}" data-focus-key="recheck-question">${escapeHtml(state.recheckDrafts[chat.id] || "")}</textarea>
          <label class="text-field__label" for="recheck-question">Your question (optional)</label>
          <p class="text-field__support" id="recheck-question-help">The AI answers it in the re-check, and it's saved with the re-check.</p>
        </div>
        ${action}
      </section>`;
  }

  // Checked chats that changed after their check, like a live run that went
  // on. A new check makes new flags, and the calls on the old ones stay in the log.
  function renderChangedChats() {
    const changed = state.review ? state.review.changed : [];
    if (changed.length === 0) return "";
    const one = changed.length === 1;
    const rows = changed.map((chat) => `
      <li class="changed-chats__item">
        <span>${escapeHtml(reviewLabel(chat))}</span>
        <button type="button" class="btn btn--text" data-action="check-changed-chat" data-chat="${chat.id}"
          data-focus-key="changed-${chat.id}">Check it again<span class="visually-hidden">: ${escapeHtml(reviewLabel(chat))}</span></button>
      </li>`);
    return `
      <section class="card card--filled changed-chats" aria-labelledby="changed-chats-title">
        <h2 class="changed-chats__title" id="changed-chats-title">
          <span class="icon" aria-hidden="true">update</span>
          <span>${one ? "Changed since its check" : "Changed since their checks"}</span>
        </h2>
        <p class="changed-chats__text">${one
          ? "This chat grew after it was checked. Checking it again makes a new set of flags, and each needs your call. Your calls on the old flags stay in the log."
          : "These chats grew after they were checked. Checking one again makes a new set of flags, and each needs your call. Your calls on the old flags stay in the log."}</p>
        <ul class="changed-chats__list">${rows.join("")}</ul>
      </section>`;
  }

  // The human-in-the-loop to-do. Every flag needs the creator's call, agree
  // or override, before the review is done. The cues below count calls made,
  // never agreements, so they push the creator to decide, not to agree
  // quickly (the rubber-stamp risk in THEORY_LENS Part 1). They show in four
  // places: the badge on the Flag review tab, each chat in the chat switcher,
  // a "Needs your call" label on each open card, and a notice on Compare runs.
  // The server counts them from the saved calls, so they follow each check.

  // "2 need your call", or "All 3 decided" once every flag has a call.
  function decidedText(item) {
    const total = item.flags.length;
    const open = item.open_calls;
    if (total === 0) return "No flags";
    if (open > 0) return `${open} ${open === 1 ? "needs" : "need"} your call`;
    return total === 1 ? "Decided" : `All ${total} decided`;
  }

  // Switches between the checked chats without leaving the screen. Each shows
  // how many calls are left, with a progress bar, so a chat nobody has
  // reviewed stands out. Past five chats it becomes a menu (DESIGN_SPEC 3).
  // On phones the buttons stack (see styles.css).
  function renderChatSwitcher(item) {
    const chats = reviewChats();
    if (chats.length < 2) return "";
    if (chats.length > 5) {
      const options = chats
        .map((other) => `<option value="${other.chat.id}"${other.chat.id === item.chat.id ? " selected" : ""}>${escapeHtml(`${reviewLabel(other.chat)}: ${decidedText(other)}`)}</option>`)
        .join("");
      return `<div class="chat-switcher-menu">${selectField("review-chat", "Chat to review", options)}</div>`;
    }
    const buttons = chats.map((other) => {
      const selected = other.chat.id === item.chat.id;
      const total = other.flags.length;
      const done = other.open_calls === 0;
      const icon = selected ? "check" : done ? "task_alt" : "pending";
      return `
        <button type="button" class="segmented__button chat-switcher__button" aria-pressed="${selected}"
          data-action="pick-chat" data-chat="${other.chat.id}" data-focus-key="chat-${other.chat.id}">
          <span class="icon${done && !selected ? " icon--filled" : ""}" aria-hidden="true">${icon}</span>
          <span class="chat-switcher__text">
            <span class="chat-switcher__name">${escapeHtml(reviewLabel(other.chat))}</span>
            <span class="chat-switcher__count">${decidedText(other)}</span>
            <progress class="linear-progress chat-switcher__progress" max="${Math.max(total, 1)}" value="${total ? total - other.open_calls : 1}" aria-hidden="true"></progress>
          </span>
        </button>`;
    });
    return `<div class="segmented chat-switcher" role="group" aria-label="Chat to review">${buttons.join("")}</div>`;
  }

  // The badge on the Flag review tab: how many calls are left across every
  // checked chat, so the open work shows from any screen.
  function updateTodoBadge() {
    const open = state.review ? state.review.open_calls : 0;
    const badge = document.querySelector("[data-todo-badge]");
    badge.hidden = open === 0;
    badge.textContent = String(open);
    document.querySelector("[data-todo-label]").textContent =
      open === 0 ? "" : `, ${open} ${open === 1 ? "flag needs" : "flags need"} your call`;
  }

  function pickReviewChat(chatId, focusKey) {
    if (chatId === state.reviewChatId) return;
    state.reviewChatId = chatId;
    state.reviewTurn = null;
    refresh({ focusKey });
    const item = selectedReview();
    if (item) announce(`Showing ${reviewLabel(item.chat)}. ${item.flags.length ? reviewSummary(item) : noFlagsText(item)}`);
  }

  actions["pick-chat"] = (button) => {
    pickReviewChat(Number(button.dataset.chat), `chat-${button.dataset.chat}`);
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

  function renderFlagCard(item, flag) {
    const chat = item.chat;
    const id = cardId(flag);
    const verdict = verdictOf(flag);
    const contextOpen = Boolean(state.contextOpen[flag.id]);
    const classes = `card card--outlined flag-card${verdict ? ` is-${verdict}` : ""}`;
    const level = capitalized(flag.confidence);
    let note = "";
    if (flag.needs_call) {
      note = NEEDS_CALL_TEXT[flag.needs_call_reason](chat);
    } else if (flag.confidence === "low") {
      note = "The AI is unsure. Read the turn before deciding.";
    }

    return `
      <article class="${classes}" id="${id}" tabindex="-1" aria-labelledby="${id}-title">
        <div class="flag-card__head">
          <h3 class="flag-card__title" id="${id}-title">${escapeHtml(flagTitle(chat, flag))}</h3>
          ${verdict
            ? ""
            : '<span class="needs-call"><span class="icon" aria-hidden="true">pending</span><span>Needs your call</span></span>'}
        </div>
        <figure class="flag-card__evidence">
          <blockquote><p class="keep-lines"><q>${escapeHtml(flag.quote)}</q></p></blockquote>
          <figcaption>From ${escapeHtml(chat.character_name)}'s reply</figcaption>
        </figure>
        <div class="flag-card__chips">
          ${chip(...SOURCE_CHIPS[flag.source])}
          ${renderCiteChip(flag)}
          <span class="chip chip--icon-leading flag-card__confidence">
            <span class="icon" aria-hidden="true">${CONFIDENCE_ICONS[level]}</span>
            <span>${level}<span class="visually-hidden"> confidence</span></span>
          </span>
          ${flag.same_model ? chip("sync_problem", "Same model reviewed") : ""}
        </div>
        ${renderCiteText(flag)}
        <p class="flag-card__why"><span class="flag-card__label">Why this flag?</span> ${escapeHtml(flag.why)}</p>
        ${flag.also_turns.length > 0
          ? `<p class="flag-card__also">Also in ${numberWord(chat).toLowerCase()}s ${escapeHtml(listText(flag.also_turns))}.</p>`
          : ""}
        ${note
          ? `<p class="flag-card__unsure">
              <span class="icon" aria-hidden="true">help</span>
              <span>${escapeHtml(note)}</span>
            </p>`
          : ""}
        ${renderRecheckNote(flag)}
        <button type="button" class="btn btn--text btn--icon-leading" data-action="toggle-context" data-flag="${flag.id}"
          aria-expanded="${contextOpen}" aria-controls="${id}-context" data-focus-key="context-${flag.id}">
          <span class="icon" aria-hidden="true">${contextOpen ? "expand_less" : "expand_more"}</span>
          <span>${contextOpen ? "Hide context" : "Show in context"}</span>
        </button>
        <div class="flag-card__context" id="${id}-context"${contextOpen ? "" : " hidden"}>
          ${renderFlagContext(item, flag)}
        </div>
        ${renderDecision(item, flag)}
      </article>`;
  }

  // The cited line's chip, like K2, which expands to show the line's own words.
  function renderCiteChip(flag) {
    const lineId = flag.line_id;
    const open = Boolean(state.citesOpen[`${flag.id}:${lineId}`]);
    const key = `cite-${flag.id}`;
    return `
      <button type="button" class="chip chip--assist chip--icon-trailing" data-action="toggle-cite"
        data-flag="${flag.id}" data-line="${escapeHtml(lineId)}" aria-expanded="${open}"
        aria-controls="${key}-text" data-focus-key="${key}"
        data-tooltip="${escapeHtml(lineTip(lineId))}">
        <span>${escapeHtml(citeLabel(lineId))}<span class="visually-hidden">: ${escapeHtml(citeMeaning(lineId))}</span></span>
        <span class="icon" aria-hidden="true">${open ? "expand_less" : "expand_more"}</span>
      </button>`;
  }

  // The cited line in the spec's own words, from the chat's spec version.
  function renderCiteText(flag) {
    const open = Boolean(state.citesOpen[`${flag.id}:${flag.line_id}`]);
    return `
      <p class="flag-card__cite-text" id="cite-${flag.id}-text"${open ? "" : " hidden"}>
        <span class="flag-card__label">${escapeHtml(citeLabel(flag.line_id))}.</span> ${escapeHtml(flag.line_text)}
      </p>`;
  }

  // What the latest re-check said about this flag, on its card: both views
  // when the two disagree, or one line when it re-rated the flag.
  function renderRecheckNote(flag) {
    const recheck = flag.recheck;
    if (!recheck) return "";
    if (flag.disputed) return renderBothViews(flag);
    if (recheck.change !== "rerated") return "";
    const rerated = `Re-rated by the re-check, ${capitalized(recheck.from_confidence)} to ${capitalized(recheck.to_confidence)}: ${recheck.why}`;
    return `
      <p class="flag-card__recheck">
        <span class="icon" aria-hidden="true">swap_vert</span>
        <span>${escapeHtml(rerated)}</span>
      </p>`;
  }

  // A disputed flag: the re-check and the flag's standing, the creator's call
  // or else the first pass, disagree on whether it is a break. Both views
  // show side by side instead of the flag silently flipping (DESIGN_SPEC
  // 7.4), and the creator's call decides.
  function renderBothViews(flag) {
    const recheck = flag.recheck;
    const verdict = verdictOf(flag);
    let standing;
    if (verdict === "agreed") {
      standing = ["Your call", "Agreed: it's a break."];
    } else if (verdict === "retyped") {
      standing = ["Your call", `Retyped as ${flag.call.type}, so still a break. Your reason: ${flag.call.reason}`];
    } else if (verdict === "overridden") {
      standing = ["Your call", `Overridden: not a break. Your reason: ${flag.call.reason}`];
    } else {
      standing = [flag.source === "recheck" ? "Earlier re-check" : "AI first pass", `A break. ${flag.why}`];
    }
    let view = `Still a break, so it keeps this flag. ${recheck.why}`;
    if (recheck.kept_because) {
      view = `Not a break, so it would withdraw this flag. ${recheck.why}`;
    } else if (recheck.change === "rerated") {
      view = `Still a break, re-rated ${capitalized(recheck.from_confidence)} to ${capitalized(recheck.to_confidence)}. ${recheck.why}`;
    }
    const settles = verdict
      ? "Your call stands. The AI can't change it."
      : "The two AI views disagree, so the flag stays for your call.";
    return `
      <div class="both-views" role="group" aria-labelledby="both-views-${flag.id}">
        <p class="both-views__title" id="both-views-${flag.id}">
          <span class="icon" aria-hidden="true">compare_arrows</span>
          <span>Both views</span>
        </p>
        <div class="both-views__grid">
          <div class="both-views__view">
            <h4 class="both-views__heading">${escapeHtml(standing[0])}</h4>
            <p class="keep-lines">${escapeHtml(standing[1])}</p>
          </div>
          <div class="both-views__view">
            <h4 class="both-views__heading">AI re-check</h4>
            <p>${escapeHtml(view)}</p>
          </div>
        </div>
        <p class="both-views__note">${escapeHtml(settles)}</p>
      </div>`;
  }

  // The turn in context: the creator's line before the reply, every finished
  // reply in that turn with the quote marked, and the cited line in the
  // spec's own words.
  function renderFlagContext(item, flag) {
    const chat = item.chat;
    const word = numberWord(chat).toLowerCase();
    const replies = chat.messages.filter(
      (message) => message.speaker === "character" && message.turn === flag.turn && !message.stopped,
    );
    const first = replies[0];
    const before = first ? chat.messages.filter((message) => message.speaker === "user" && message.seq < first.seq) : [];
    const userLine = before[before.length - 1];
    const lines = replies.map(
      (reply) => `
        <p class="context-line">
          <span class="context-line__speaker">${escapeHtml(chat.character_name)}, ${word} ${reply.turn}</span>
          <span class="keep-lines">${highlight(reply.text, [flag.quote.toLowerCase()])}</span>
        </p>`,
    );
    return `
      ${userLine
        ? `<p class="context-line">
            <span class="context-line__speaker">${escapeHtml(chat.user_name)}, ${word} ${userLine.turn}</span>
            <span class="keep-lines">${escapeHtml(userLine.text)}</span>
          </p>`
        : ""}
      ${lines.join("")}
      <p class="context-line">
        <span class="context-line__speaker">Spec ${escapeHtml(citeLabel(flag.line_id))}</span>
        ${escapeHtml(flag.line_text)}
      </p>`;
  }

  // The bottom of a card: Agree and Override, the override form, or the
  // creator's call with Undo.
  function renderDecision(item, flag) {
    const verdict = verdictOf(flag);
    const undo = `
      <button type="button" class="btn btn--text" data-action="undo-decision" data-flag="${flag.id}" data-focus-key="undo-${flag.id}">
        Undo<span class="visually-hidden">: ${escapeHtml(flagTitle(item.chat, flag))}</span>
      </button>`;

    // The call that left no open flag in the chat gets the sparkle, once.
    const sparkle = flag.id === state.sparkleFlagId ? sparkleHtml() : "";

    if (verdict === "agreed") {
      return `
        <div class="flag-card__actions">
          <p class="flag-card__status">
            <span class="icon icon--filled" aria-hidden="true">check_circle</span>
            <span>Agreed by you</span>
            ${sparkle}
          </p>
          ${undo}
        </div>`;
    }

    if (verdict) {
      const status = verdict === "retyped"
        ? `<span class="icon" aria-hidden="true">edit</span><span>Retyped by you: ${escapeHtml(flag.call.type)}</span>`
        : '<span class="icon" aria-hidden="true">block</span><span>Overridden by you</span>';
      return `
        <div class="flag-card__actions">
          <p class="flag-card__status">${status}${sparkle}</p>
          <p class="flag-card__reason"><span class="flag-card__label">Your reason:</span> ${escapeHtml(flag.call.reason)}</p>
          ${undo}
        </div>`;
    }

    if (flag.id in state.overrideDrafts) {
      const draft = state.overrideDrafts[flag.id];
      const ready = countWords(draft) >= state.review.min_reason_words;
      const error = state.overrideErrors[flag.id];
      const picked = state.overrideTypes[flag.id] || "";
      const types = state.review.failure_types
        .filter((type) => type !== flag.type)
        .map((type) => `<option value="${escapeHtml(type)}"${type === picked ? " selected" : ""}>${escapeHtml(capitalized(type))}</option>`)
        .join("");
      return `
        <div class="flag-card__override">
          <div class="text-field${error ? " text-field--error" : ""}">
            <textarea class="text-field__input" id="reason-${flag.id}" rows="2" placeholder=" "
              maxlength="${state.review.max_reason_chars}" aria-describedby="reason-${flag.id}-help"${error ? ' aria-invalid="true"' : ""}
              data-reason-for="${flag.id}" data-focus-key="reason-${flag.id}">${escapeHtml(draft)}</textarea>
            <label class="text-field__label" for="reason-${flag.id}">Why is the AI wrong?</label>
            <p class="text-field__support" id="reason-${flag.id}-help">${escapeHtml(error || wordCountText(draft))}</p>
          </div>
          <div class="text-field text-field--select">
            <select class="text-field__input" id="type-${flag.id}" aria-describedby="type-${flag.id}-help"
              data-type-for="${flag.id}" data-focus-key="type-${flag.id}">
              <option value="">None: it isn't a break</option>
              ${types}
            </select>
            <label class="text-field__label" for="type-${flag.id}">Right type</label>
            <p class="text-field__support" id="type-${flag.id}-help">Pick one if the turn breaks the spec in another way. It stays a break, with your type.</p>
          </div>
          <div class="flag-card__actions">
            <button type="button" class="btn btn--filled" data-action="save-override" data-flag="${flag.id}"
              aria-disabled="${!ready}"${ready ? "" : ` aria-describedby="reason-${flag.id}-help"`} data-focus-key="save-${flag.id}">Save</button>
            <button type="button" class="btn btn--text" data-action="cancel-override" data-flag="${flag.id}"
              data-focus-key="cancel-${flag.id}">Cancel</button>
          </div>
        </div>`;
    }

    // Evidence first: Agree stays off until the server has saved an opening
    // of this flag's evidence. aria-disabled (not disabled) keeps it
    // reachable, with the reason linked.
    const seen = flag.evidence_opened;
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

  // The compact conversation, one item per turn, or per line when the chat
  // numbers lines. Flagged turns get a colored border, a flag icon, and the
  // word "Flagged", plus the creator's call once every flag there has the same one.
  function renderConversation(item) {
    const chat = item.chat;
    const word = numberWord(chat);
    const groups = [];
    chat.messages.forEach((message) => {
      const last = groups[groups.length - 1];
      if (last && last.turn === message.turn) last.messages.push(message);
      else groups.push({ turn: message.turn, messages: [message] });
    });
    const statusText = { agreed: "Agreed by you", retyped: "Retyped by you", overridden: "Overridden by you" };

    const turns = groups.map((group) => {
      const turnFlags = item.flags.filter((flag) => flag.turn === group.turn);
      const verdicts = turnFlags.map(verdictOf);
      const shared = verdicts.length > 0 && verdicts.every((verdict) => verdict && verdict === verdicts[0]) ? verdicts[0] : null;
      let classes = "convo-turn";
      if (turnFlags.length > 0) classes += " convo-turn--flagged";
      if (shared === "overridden") classes += " convo-turn--overridden";
      const quotes = turnFlags.map((flag) => flag.quote.toLowerCase());
      const lines = group.messages.map((message) => {
        const name = message.speaker === "user" ? chat.user_name : chat.character_name;
        const text = message.speaker === "character" ? highlight(message.text, quotes) : escapeHtml(message.text);
        let cut = "";
        if (message.failed) cut = " (cut off by an error)";
        else if (message.stopped) cut = " (stopped)";
        const mark = message.injection ? ` ${injectionStatus("convo-turn__injection")}` : "";
        return `<p class="convo-turn__line"><span class="convo-turn__speaker">${escapeHtml(name)}${cut}:</span>${mark} <span class="keep-lines">${text}</span></p>`;
      });
      return `
        <li class="${classes}" data-turn="${group.turn}"${state.reviewTurn === group.turn ? ' aria-current="true"' : ""}>
          <p class="convo-turn__head">
            <span>${word} ${group.turn}</span>
            ${turnFlags.length > 0
              ? `<span class="convo-turn__flag"><span class="icon icon--filled" aria-hidden="true">flag</span>Flagged</span>`
              : ""}
            ${shared ? `<span class="convo-turn__status">${statusText[shared]}</span>` : ""}
          </p>
          ${lines.join("")}
        </li>`;
    });
    // Turn 1 of every scripted chat is the spec itself.
    const specLine = chat.numbering === "turn" && (chat.kind === "live" || chat.scenario)
      ? `<li class="convo__system">Turn 1: character spec ${escapeHtml(specLabel(chat.spec_version))} loaded</li>`
      : "";

    return `
      <div class="review__conversation">
        <div class="review__convo-head">
          <h2 class="review__convo-title" id="review-convo-title">Conversation</h2>
          <p class="review__convo-run">${escapeHtml(reviewLabel(chat))}</p>
        </div>
        <div class="review__convo-scroll" tabindex="0" role="region" aria-labelledby="review-convo-title"
          data-scroll-key="review-convo">
          <ol class="convo">
            ${specLine}
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

  // Screen readers hear the new summary after each call, and the
  // rubber-stamp check when it applies.
  function announceReview() {
    const item = selectedReview();
    if (!item) return;
    const summary = item.flags.length ? reviewSummary(item) : noFlagsText(item);
    announce(item.agreed_with_every ? `${summary} ${RUBBER_STAMP_MESSAGE}` : summary);
  }

  function diagnoseBody() {
    return panelFor("diagnose").querySelector("[data-screen-body]");
  }

  // Sends one call, then redraws from the server's answer. Focus moves to
  // focusKey only if Flag review still shows that chat and focus is still in
  // the flag's card. A refused call throws, and the screen stays as it was.
  async function sendCall(found, request, focusKey) {
    const flagId = found.flag.id;
    reviewPending.add(flagId);
    let updated;
    try {
      updated = await request();
    } finally {
      reviewPending.delete(flagId);
    }
    replaceReviewChat(updated);
    delete state.overrideDrafts[flagId];
    delete state.overrideTypes[flagId];
    delete state.overrideErrors[flagId];
    // The call that leaves no open flag in the chat gets a sparkle in this
    // redraw only. Not when the rubber-stamp check shows, since the screen
    // warns then. Like the other cues, it counts calls, not agreements.
    const finished = found.item.open_calls > 0 && updated.open_calls === 0;
    state.sparkleFlagId = finished && !updated.agreed_with_every ? flagId : null;
    const body = currentScreen === "diagnose" ? diagnoseBody() : null;
    const card = body ? body.querySelector(`#${cardId(found.flag)}`) : null;
    const inCard = Boolean(card && card.contains(document.activeElement)) && state.reviewChatId === found.item.chat.id;
    if (body) refresh(inCard ? { focusKey } : {});
    else redrawReview();
    state.sparkleFlagId = null;
    if (state.reviewChatId === found.item.chat.id) announceReview();
  }

  actions["retry-review"] = () => {
    state.reviewLoad = { status: "loading", message: "" };
    refresh();
    loadReview();
  };

  // Opens a changed chat on Run a conversation, where Check this chat checks it again.
  actions["check-changed-chat"] = (button) => {
    goToScreen("run");
    if (state.live) {
      announce("Stop the run to switch chats.");
      return;
    }
    loadChat(Number(button.dataset.chat), { focusKey: "check-chat" });
  };

  actions["filter-flags"] = (chip) => {
    state.flagFilter = chip.dataset.filter;
    refresh();
  };

  actions["toggle-cite"] = (chip) => {
    const key = `${chip.dataset.flag}:${chip.dataset.line}`;
    state.citesOpen[key] = !state.citesOpen[key];
    refresh();
  };

  // Every opening of the evidence is saved, and the server's answer unlocks Agree.
  actions["toggle-context"] = async (button) => {
    const found = findFlag(button.dataset.flag);
    if (!found) return;
    const flagId = found.flag.id;
    const opening = !state.contextOpen[flagId];
    state.contextOpen[flagId] = opening;
    if (opening) state.reviewTurn = found.flag.turn;
    refresh();
    if (!opening) return;
    revealTurn(diagnoseBody());
    const request = WorkbenchApi.openEvidence(flagId);
    evidenceRequests.set(flagId, request);
    try {
      replaceReviewChat(await request);
      redrawReview();
    } catch (error) {
      reviewError(error);
    } finally {
      if (evidenceRequests.get(flagId) === request) evidenceRequests.delete(flagId);
    }
  };

  actions["agree"] = async (button) => {
    const flagId = Number(button.dataset.flag);
    if (reviewPending.has(flagId)) return;
    // Marked before anything waits, so a second click while the first is on its way does nothing.
    reviewPending.add(flagId);
    try {
      // An opening on its way lands first, so Agree right after "Show in context" works.
      if (evidenceRequests.has(flagId)) await evidenceRequests.get(flagId).catch(() => {});
      const found = findFlag(flagId);
      if (!found) return;
      if (!found.flag.evidence_opened) {
        // Not yet: send the creator to the evidence instead.
        const toggle = diagnoseBody().querySelector(`[data-focus-key="context-${flagId}"]`);
        if (toggle) toggle.focus();
        return;
      }
      await sendCall(found, () => WorkbenchApi.agreeFlag(flagId), `undo-${flagId}`);
    } catch (error) {
      reviewError(error);
    } finally {
      reviewPending.delete(flagId);
    }
  };

  actions["start-override"] = (button) => {
    const flagId = Number(button.dataset.flag);
    state.overrideDrafts[flagId] = "";
    refresh({ focusKey: `reason-${flagId}` });
  };

  function cancelOverride(flagId) {
    delete state.overrideDrafts[flagId];
    delete state.overrideTypes[flagId];
    delete state.overrideErrors[flagId];
    refresh({ focusKey: `override-${flagId}` });
  }

  actions["cancel-override"] = (button) => {
    cancelOverride(button.dataset.flag);
  };

  actions["save-override"] = async (button) => {
    const found = findFlag(button.dataset.flag);
    if (!found || reviewPending.has(found.flag.id)) return;
    const flagId = found.flag.id;
    const reason = (state.overrideDrafts[flagId] || "").trim();
    if (countWords(reason) < state.review.min_reason_words) {
      diagnoseBody().querySelector(`[data-focus-key="reason-${flagId}"]`).focus();
      return;
    }
    const type = state.overrideTypes[flagId] || null;
    try {
      await sendCall(found, () => WorkbenchApi.overrideFlag(flagId, reason, type), `undo-${flagId}`);
    } catch (error) {
      if (error.status !== 422) {
        reviewError(error);
        return;
      }
      // The server's own check of the reason, shown under the field like the word count.
      state.overrideErrors[flagId] = error.message;
      if (currentScreen === "diagnose") refresh({ focusKey: `reason-${flagId}` });
      announce(error.message);
    }
  };

  actions["undo-decision"] = async (button) => {
    const found = findFlag(button.dataset.flag);
    if (!found || reviewPending.has(found.flag.id)) return;
    try {
      await sendCall(found, () => WorkbenchApi.undoCall(found.flag.id), `agree-${found.flag.id}`);
    } catch (error) {
      reviewError(error);
    }
  };

  // The follow-up re-check takes up to a minute, so its card shows it working
  // while other calls go on. Afterward, focus lands on What changed.
  actions["recheck"] = async (button) => {
    const item = reviewItem(Number(button.dataset.chat));
    if (!item || item.judge.status !== "ok") return;
    const chatId = item.chat.id;
    if (state.rechecks[chatId] && state.rechecks[chatId].status === "running") return;
    const question = (state.recheckDrafts[chatId] || "").trim();
    const before = item.recheck ? item.recheck.id : null;
    state.rechecks[chatId] = { status: "running", message: "", startedAt: Date.now() };
    refresh({ focusKey: "recheck-status" });
    announce("Re-checking this chat. The AI judge can take a minute.");
    startElapsedTimer();
    const here = () => currentScreen === "diagnose" && state.reviewChatId === chatId;
    try {
      const updated = await WorkbenchApi.recheckChat(chatId, question || null);
      // The same flags with the same question: the server kept the saved re-check.
      const saved = Boolean(updated.recheck) && updated.recheck.id === before;
      if (saved) state.rechecks[chatId] = { status: "saved", message: "", id: before };
      else delete state.rechecks[chatId];
      delete state.recheckDrafts[chatId];
      replaceReviewChat(updated);
      if (here()) {
        refresh({ focusKey: "what-changed" });
        announce(saved ? "Shown from the saved re-check, with no new model call." : recheckSummary(updated));
      } else {
        redrawReview();
      }
    } catch (error) {
      state.rechecks[chatId] = { status: "failed", message: error.message };
      if (here()) {
        refresh({ focusKey: "recheck" });
        announce(error.message);
      }
      if (error.status === 409) loadReview();
    }
    // The call counts toward today's total on Run a conversation, and the
    // re-check's flags change the check results there.
    loadRunOptions();
    if (state.checks[chatId]) loadCheck(chatId);
  };

  // 3.4 Compare runs (Repair) -----------------------------------------------
  // Same script, same spec, different results: where each chat broke, the
  // replies side by side, and a next step for every spec line that broke in
  // every chat, which leads back to the Spec editor (Repair closes the loop
  // to Define). It compares the checked chats that ran the same scenario on
  // the same spec version as the chat on Flag review, however many there are,
  // turn by turn through the script. A break is any flag that still counts as
  // one: open, agreed, or retyped. Flags the creator overrode don't, so the
  // creator's calls shape this screen.

  // The checked chats that ran the same script on the same spec version as
  // this one, or none when this chat has no script.
  function compareGroup(item) {
    if (!item.chat.scenario) return [];
    return reviewChats().filter(
      (other) => other.chat.scenario === item.chat.scenario && other.chat.spec_version === item.chat.spec_version,
    );
  }

  // A chat's scripted lines, by turn. A typed line can reuse the next
  // scripted turn's number, so typed lines never count here.
  function scriptedLines(item) {
    const lines = new Map();
    item.chat.messages.forEach((message) => {
      if (message.speaker === "user" && message.source !== "typed" && !lines.has(message.turn)) {
        lines.set(message.turn, message);
      }
    });
    return lines;
  }

  // Every scripted turn of the compared chats, in order.
  function comparedTurns(items) {
    const turns = new Set();
    items.forEach((item) => scriptedLines(item).forEach((line, turn) => turns.add(turn)));
    return [...turns].sort((a, b) => a - b);
  }

  // A chat's reply to its own scripted line at that turn, or null.
  function scriptedReply(item, turn) {
    if (!scriptedLines(item).has(turn)) return null;
    const replies = item.chat.messages.filter((message) => message.speaker === "character" && message.turn === turn);
    return replies[replies.length - 1] || null;
  }

  // The flags at a turn: those on the turn itself, plus rule flags that list
  // it among the other turns that broke the same line.
  function flagsAt(item, turn) {
    return item.flags.filter((flag) => flag.turn === turn || flag.also_turns.includes(turn));
  }

  // "missing" when the chat has no reply at that scripted turn, "clean" when
  // nothing there was flagged, "break" when a flag there still counts as one,
  // and "overridden" when the creator overrode every flag there.
  function turnStatus(item, turn) {
    if (!scriptedReply(item, turn)) return "missing";
    const turnFlags = flagsAt(item, turn);
    if (turnFlags.length === 0) return "clean";
    return turnFlags.some((flag) => flag.counts_as_break) ? "break" : "overridden";
  }

  // The flags on the compared turns that are this chat's own scripted turns.
  // A typed line can reuse a scripted turn's number, so its flags stay on Flag review.
  function comparedFlags(item, turns) {
    const own = scriptedLines(item);
    return item.flags.filter((flag) => turns.includes(flag.turn) && own.has(flag.turn));
  }

  function breaksIn(item, turns) {
    return comparedFlags(item, turns).filter((flag) => flag.counts_as_break);
  }

  function firstBreakText(item, turns) {
    const found = breaksIn(item, turns).map((flag) => flag.turn);
    return found.length > 0 ? `First break: turn ${Math.min(...found)}.` : "No breaks.";
  }

  // Spec lines that a standing flag cites in every chat, in the order of the
  // spec on screen. A field, like Voice, has no line to open, so it isn't listed.
  function linesBrokenInAll(items, turns) {
    const citedPerChat = items.map((item) => new Set(breaksIn(item, turns).map((flag) => flag.line_id)));
    const shared = [...(citedPerChat[0] || [])].filter(
      (lineId) => /^[A-Z][0-9]+$/.test(lineId) && citedPerChat.every((cited) => cited.has(lineId)),
    );
    const order = state.specView
      ? state.specView.body.sections.flatMap((section) => section.lines.map((line) => line.id))
      : [];
    const rank = (lineId) => (order.includes(lineId) ? order.indexOf(lineId) : order.length);
    return shared.sort((a, b) => rank(a) - rank(b) || a.localeCompare(b, undefined, { numeric: true }));
  }

  // The version a fix would make: one past the latest saved version, once
  // the spec has loaded from the server.
  function nextSpecLabel() {
    return state.specView ? specLabel(state.specView.latest + 1) : "the next version";
  }

  // "both chats" for two, "all 3 chats" for three or more.
  function chatsText(count) {
    if (count === 1) return "the one chat";
    return count === 2 ? "both chats" : `all ${count} chats`;
  }

  // While any flag is still open, this comparison counts it as a break, so
  // the creator hears that before trusting the numbers.
  function renderReviewNotice(items, turns) {
    const open = items.reduce((sum, item) => sum + comparedFlags(item, turns).filter((flag) => !flag.call).length, 0);
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
    if (!state.review) {
      body.innerHTML = state.reviewLoad.status === "failed"
        ? `
          <div class="card card--outlined spec-empty">
            <p>The saved flags didn't load. ${escapeHtml(state.reviewLoad.message)}</p>
            <button type="button" class="btn btn--filled" data-action="retry-review" data-focus-key="retry-review">Try again</button>
          </div>`
        : '<p class="spec-status">Loading the saved flags.</p>';
      return null;
    }
    const item = selectedReview();
    if (!item) {
      body.innerHTML = renderNoCheckedChats();
      return null;
    }
    // The same chat stays on Flag review and here.
    state.reviewChatId = item.chat.id;
    const items = compareGroup(item);
    if (items.length === 0) {
      body.innerHTML = `
        <div class="card card--outlined flag-cards__empty empty-state">
          <p class="empty-state__text">Compare runs lines up chats that ran the same test script. ${escapeHtml(reviewLabel(item.chat))} was imported without one, so there's nothing to compare it with. On Flag review, pick a chat from a scenario run.</p>
          <button type="button" class="btn btn--filled" data-action="go-to-screen" data-screen="diagnose" data-focus-key="go-to-review">Go to Flag review</button>
        </div>`;
      return null;
    }
    const turns = comparedTurns(items);
    const broken = linesBrokenInAll(items, turns);
    const missing = items.some((other) => turns.some((turn) => turnStatus(other, turn) === "missing"));

    body.innerHTML = `
      <div class="compare">
        ${renderReviewNotice(items, turns)}
        <section aria-labelledby="drift-title">
          <h2 class="compare__heading" id="drift-title">Where each chat broke</h2>
          <div class="drift">${items.map((other) => renderDriftRow(other, turns)).join("")}</div>
          <ul class="drift__legend">
            <li><span class="drift__turn drift__turn--sample" aria-hidden="true"></span>Clean turn</li>
            <li>
              <span class="drift__turn drift__turn--break drift__turn--sample" aria-hidden="true">
                <span class="icon icon--filled">flag</span>
              </span>Break
            </li>
            <li><span class="drift__turn drift__turn--overridden drift__turn--sample" aria-hidden="true"></span>Flag you overrode</li>
            ${missing
              ? '<li><span class="drift__turn drift__turn--missing drift__turn--sample" aria-hidden="true"></span>No reply</li>'
              : ""}
          </ul>
        </section>

        <section aria-labelledby="side-by-side-title">
          <h2 class="compare__heading" id="side-by-side-title">Turn by turn</h2>
          ${renderCompareTable(items, turns)}
        </section>

        <div class="compare__next">
          ${broken.length > 0
            ? broken.map((lineId) => renderNextStep(lineId, items.length)).join("")
            : `<p class="card card--outlined">No spec line broke in ${chatsText(items.length)}.</p>`}
        </div>
      </div>`;
    return null;
  }

  // One small square per scripted turn: outlined when clean, filled with a
  // flag icon when it broke, dashed when the creator overrode its flags, and
  // dotted when the chat has no reply there. A chat whose AI judge didn't
  // finish says so, since only its automatic checks could flag a break.
  function renderDriftRow(item, turns) {
    const said = { clean: "clean", break: "break", overridden: "flag overridden by you", missing: "no reply" };
    const squares = turns.map((turn) => {
      const status = turnStatus(item, turn);
      return `
        <li class="drift__turn${status === "clean" ? "" : ` drift__turn--${status}`}">
          ${status === "break" ? '<span class="icon icon--filled" aria-hidden="true">flag</span>' : ""}
          <span><span class="visually-hidden">Turn </span>${turn}<span class="visually-hidden">, ${said[status]}</span></span>
        </li>`;
    });
    const label = reviewLabel(item.chat);
    const range = turns.length > 0 ? `, turns ${turns[0]} to ${turns[turns.length - 1]}` : "";
    const judge = item.judge.status === "ok" ? "" : " Automatic checks only: the AI judge didn't finish.";
    return `
      <div class="drift__row">
        <p class="drift__run">${escapeHtml(label)}</p>
        <ol class="drift__strip" aria-label="${escapeHtml(label + range)}">${squares.join("")}</ol>
        <p class="drift__first">${firstBreakText(item, turns)}${judge}</p>
      </div>`;
  }

  // The chats side by side: one row per scripted turn with the user's line,
  // then each chat's reply. Replies that broke are highlighted, with the
  // evidence marked.
  function renderCompareTable(items, turns) {
    const heads = items.map((item) => `<th scope="col">${escapeHtml(reviewLabel(item.chat))}</th>`);
    const rows = turns.map((turn) => {
      const owner = items.find((item) => scriptedLines(item).has(turn));
      const line = scriptedLines(owner).get(turn);
      return `
        <tr>
          <th scope="row">
            <span class="compare-table__turn">Turn ${turn}</span>
            <span><span class="compare-table__speaker">${escapeHtml(owner.chat.user_name)}:</span> ${escapeHtml(line.text)}</span>
          </th>
          ${items.map((item) => renderCompareCell(item, turn)).join("")}
        </tr>`;
    });
    return `
      <div class="compare-table-wrap" tabindex="0" role="region" aria-labelledby="side-by-side-title">
        <table class="compare-table" style="min-width: ${12 + items.length * 14}rem">
          <thead><tr><th scope="col">Turn</th>${heads.join("")}</tr></thead>
          <tbody>${rows.join("")}</tbody>
        </table>
      </div>`;
  }

  function renderCompareCell(item, turn) {
    const reply = scriptedReply(item, turn);
    if (!reply) return '<td class="compare-reply compare-reply--missing"><p>No reply at this turn.</p></td>';
    const status = turnStatus(item, turn);
    const standing = flagsAt(item, turn).filter((flag) => flag.counts_as_break);

    let label = "";
    if (status === "break") {
      // A retyped flag is a break of the type the creator gave it.
      const types = [...new Set(standing.map((flag) => (verdictOf(flag) === "retyped" ? flag.call.type : flag.type)))].join(", ");
      const cites = [...new Set(standing.map((flag) => citeLabel(flag.line_id)))].join(", ");
      label = `
        <p class="compare-reply__label">
          <span class="icon icon--filled" aria-hidden="true">flag</span>
          <span>Flagged: ${escapeHtml(types)}, ${escapeHtml(cites)}</span>
        </p>`;
    } else if (status === "overridden") {
      label = '<p class="compare-reply__label compare-reply__label--quiet">Flag overridden by you</p>';
    }
    const stopped = reply.stopped ? '<p class="compare-reply__label compare-reply__label--quiet">Stopped</p>' : "";
    // A rule flag's quote is from its first break, so only flags on this turn mark this reply.
    const quotes = standing.filter((flag) => flag.turn === turn).map((flag) => flag.quote.toLowerCase());
    return `
      <td class="compare-reply${status === "break" ? " compare-reply--break" : ""}">
        ${label}
        ${stopped}
        <p class="keep-lines">${highlight(reply.text, quotes)}</p>
      </td>`;
  }

  function renderNextStep(lineId, chatCount) {
    return `
      <article class="card card--filled next-step" aria-labelledby="next-step-${escapeHtml(lineId)}">
        <h2 class="next-step__title" id="next-step-${escapeHtml(lineId)}">
          <span class="icon" aria-hidden="true">lightbulb</span>
          <span>Next step</span>
        </h2>
        <p>${escapeHtml(lineId)} broke in ${chatsText(chatCount)}. Consider making it more specific in ${nextSpecLabel()}.</p>
        <button type="button" class="btn btn--filled btn--icon-leading" data-action="open-spec-line"
          data-line="${escapeHtml(lineId)}" data-focus-key="open-${escapeHtml(lineId)}">
          <span class="icon" aria-hidden="true">edit_note</span>
          <span>Open ${escapeHtml(lineId)} in the spec</span>
        </button>
      </article>`;
  }

  actions["open-spec-line"] = (button) => {
    const item = selectedReview();
    const note = `From Compare runs: this line broke in ${chatsText(item ? compareGroup(item).length : 0)}.`;
    state.specHighlight = { lineId: button.dataset.line, note };
    // The spotlight lands on the latest version, the one a fix would edit.
    const view = state.specView;
    if (view && view.version !== view.latest && !state.specDraft) loadSpec("latest");
    goToScreen("define");
  };

  // "Review them": Flag review opens at the first compared flag still waiting for a call.
  actions["review-open-flags"] = () => {
    const item = selectedReview();
    if (!item) return;
    const items = compareGroup(item);
    const turns = comparedTurns(items);
    for (const other of items) {
      const open = comparedFlags(other, turns).find((flag) => !flag.call);
      if (open) {
        state.reviewChatId = other.chat.id;
        state.openFlagId = open.id;
        goToScreen("diagnose");
        return;
      }
    }
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

  // The "Go to" button in an empty state that names another screen.
  actions["go-to-screen"] = (button) => goToScreen(button.dataset.screen);

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
  // given, else to the element the screen asks to land on, else back to the
  // control that had it (matched by data-focus-key), else to the screen
  // heading if that control is gone.
  function refresh({ focusKey = null } = {}) {
    const panel = panelFor(currentScreen);
    const body = panel.querySelector("[data-screen-body]");
    const active = document.activeElement;
    const focusWasInBody = body.contains(active);
    const key = focusKey || (focusWasInBody ? active.getAttribute("data-focus-key") : null);
    // A text field that gets focus back also keeps its caret, so typing goes on where it was.
    const caret = focusWasInBody && typeof active.selectionStart === "number" && key === active.getAttribute("data-focus-key")
      ? [active.selectionStart, active.selectionEnd, active.selectionDirection]
      : null;
    const scrolls = Array.from(body.querySelectorAll("[data-scroll-key]"), (box) => [box.dataset.scrollKey, box.scrollTop]);

    // A redraw replaces the element a tooltip belongs to, so the tooltip goes.
    hideTooltip();
    const landing = renderScreen(currentScreen);

    scrolls.forEach(([scrollKey, top]) => {
      const box = body.querySelector(`[data-scroll-key="${CSS.escape(scrollKey)}"]`);
      if (box) box.scrollTop = top;
    });
    // A screen can ask to land somewhere, like the line "Open K2 in the spec"
    // waited for while the spec loaded. That wins over putting focus back.
    if (landing && !focusKey) {
      scrollBelowHeader(landing);
      landing.focus({ preventScroll: true });
      return;
    }
    if (!focusWasInBody && !focusKey) return;
    const target = key ? body.querySelector(`[data-focus-key="${CSS.escape(key)}"]`) : null;
    if (target) {
      target.focus();
      if (caret && typeof target.setSelectionRange === "function") target.setSelectionRange(...caret);
    } else {
      panel.querySelector(".screen__title").focus({ preventScroll: true });
    }
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

  // A dialog that asks before it closes, like Settings with changes, closes
  // through its guard instead.
  const dialogGuards = new Map();

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
      if (pressedScrim && isOnScrim(event)) {
        const guard = dialogGuards.get(dialog);
        if (guard) guard();
        else dialog.close();
      }
      pressedScrim = false;
    });
  });

  // Clicks on [data-action] controls anywhere on the page, sheets included.
  document.addEventListener("click", (event) => {
    const control = event.target.closest("[data-action]");
    const handler = control && actions[control.dataset.action];
    if (handler) handler(control, event);
  });

  // Typing in the Spec editor form. One listener for the whole page, so
  // redraws never stack listeners. It updates the draft and grows the field.
  document.addEventListener("input", (event) => {
    const field = event.target.closest("[data-draft-key]");
    // While a save is on its way the fields are read-only, and the saved version replaces the draft.
    if (!field || !state.specDraft || state.specSaving) return;
    setDraftText(field.dataset.draftKey, field.value);
    if (field.tagName === "TEXTAREA") fitTextareas([field]);
  });

  // Asks before a reload or a closed tab drops spec edits that aren't saved,
  // or cuts off a reply that is streaming (the server keeps it, marked stopped).
  window.addEventListener("beforeunload", (event) => {
    if (!draftChanged() && !state.live) return;
    event.preventDefault();
    event.returnValue = "";
  });

  const codesDialog = document.getElementById("codes-dialog");

  // Codes in the top bar opens "What the codes mean". Escape, Close, or a
  // click on the scrim closes it, and focus goes back to the button.
  actions["show-codes"] = (button) => {
    openDialog(codesDialog, button);
  };

  // Settings (M6.5), from the top app bar ----------------------------------
  // The creator picks the AI provider, pastes a key, chooses the models, and
  // sets the limits, with no file edits and no restart. The body is drawn
  // once each time the dialog opens. After that only the parts a choice
  // changes are redrawn, so focus and anything typed stay put. A key goes to
  // the server only with Test or Save, never comes back, and leaves the page
  // when the dialog closes. Test tries the form as typed and saves nothing.
  // The key hint runs here alone: matching a key's prefix sends nothing.

  const settingsDialog = document.getElementById("settings-dialog");
  const settingsBody = settingsDialog.querySelector("[data-settings-body]");
  const discardSettingsDialog = document.getElementById("discard-settings-dialog");
  const KEY_PROVIDERS = ["gemini", "openai_compatible"];
  const PROVIDER_CHOICES = [
    { id: "gemini", label: "Gemini (Google AI Studio)", line: "Free with a Google key. Needs the internet." },
    { id: "ollama", label: "Local model (Ollama)", line: "Runs on this computer. No key or internet needed." },
    { id: "fake", label: "Fake model (no network)", line: "Canned replies for trying the app without a key. Don't use it for the demo." },
    { id: "openai_compatible", label: "Another service (OpenAI, Claude, Grok, Groq, OpenRouter, and more)", line: "Any service with an OpenAI-style API, at its own address." },
  ];
  // The setting behind each control, so a control the shell sets shows as locked.
  const SETTING_NAMES = {
    provider: "WORKBENCH_PROVIDER",
    base_url: "OPENAI_COMPATIBLE_BASE_URL",
    character_model: "WORKBENCH_CHARACTER_MODEL",
    judge_model: "WORKBENCH_JUDGE_MODEL",
    calls_per_minute: "WORKBENCH_CALLS_PER_MINUTE",
    daily_call_cap: "WORKBENCH_DAILY_CALL_CAP",
    session_run_limit: "WORKBENCH_SESSION_RUN_LIMIT",
    session_judge_limit: "WORKBENCH_SESSION_JUDGE_LIMIT",
  };
  // The control for each field the server can name in an error.
  const SETTINGS_FIELDS = {
    base_url: "settings-base-url",
    api_key: "settings-key",
    character_model: "settings-character",
    judge_model: "settings-judge",
    calls_per_minute: "settings-calls",
    daily_call_cap: "settings-cap",
    session_run_limit: "settings-session-runs",
    session_judge_limit: "settings-session-judge",
  };
  const LOCKED_LINE = "Set in the shell that started the server, so Settings can't change it.";
  // Where CSS can hide the key's characters, the key stays a plain text
  // field, so no browser or password manager offers to save it.
  const MASK_KEY = Boolean(window.CSS && CSS.supports && CSS.supports("-webkit-text-security", "disc"));

  // The settings as the server sent them, and the form as it opened.
  let settingsView = null;
  let settingsStart = "";
  let settingsOpening = false;
  let settingsSaving = false;
  let settingsTesting = false;
  // Models Ollama has installed, once the local model helper has looked.
  let ollamaInstalled = [];
  let ollamaRequest = 0;
  // A Test passed with the connection as the form shows it now.
  let connectionTested = false;
  // The creator picked the judge, so a new model for the character no longer moves it.
  let judgePicked = false;
  let lastKeyHint = "";

  function settingsField(id) {
    return settingsBody.querySelector(`#${id}`);
  }

  function chosenProvider() {
    const picked = settingsBody.querySelector('input[name="settings-provider"]:checked');
    return picked ? picked.value : settingsView.provider;
  }

  function providerMenus(provider) {
    return settingsView.providers.find((menu) => menu.provider === provider);
  }

  function isLocked(field) {
    return settingsView.locked.includes(SETTING_NAMES[field]);
  }

  function presetById(id) {
    return settingsView.presets.find((preset) => preset.id === id) || null;
  }

  // A base URL compared the way the server does: the host's case and a trailing slash don't count.
  function plainUrl(url) {
    const [scheme, rest = ""] = url.trim().split("://");
    const slash = rest.indexOf("/");
    const host = slash === -1 ? rest : rest.slice(0, slash);
    const path = slash === -1 ? "" : rest.slice(slash);
    return `${scheme.toLowerCase()}://${host.toLowerCase()}${path}`.replace(/\/+$/, "");
  }

  function presetForUrl(url) {
    const wanted = plainUrl(url);
    return settingsView.presets.find((preset) => plainUrl(preset.base_url) === wanted) || null;
  }

  // A whole number from a number field, or 0, which the server answers with the allowed range.
  function wholeNumber(id) {
    const value = Number(settingsField(id).value);
    return Number.isInteger(value) ? value : 0;
  }

  // What Test and Save send: the form as it stands.
  function settingsDraft() {
    const provider = chosenProvider();
    const key = settingsField("settings-key").value.trim();
    return {
      provider,
      base_url: provider === "openai_compatible" ? settingsField("settings-base-url").value.trim() : settingsView.base_url,
      api_key: KEY_PROVIDERS.includes(provider) && key ? key : null,
      character_model: settingsField("settings-character").value.trim(),
      judge_model: settingsField("settings-judge").value.trim(),
      calls_per_minute: wholeNumber("settings-calls"),
      daily_call_cap: wholeNumber("settings-cap"),
      session_run_limit: wholeNumber("settings-session-runs"),
      session_judge_limit: wholeNumber("settings-session-judge"),
      simulate_busy: settingsField("settings-busy").checked,
    };
  }

  function settingsChanged() {
    return Boolean(settingsView) && settingsDialog.open && JSON.stringify(settingsDraft()) !== settingsStart;
  }

  function settingsNotice(icon, text, modifier = "", action = "") {
    return `
      <div class="settings__notice ${modifier}">
        <span class="icon" aria-hidden="true">${icon}</span>
        <p class="settings__notice-text">${escapeHtml(text)}</p>
        ${action}
      </div>`;
  }

  // An outlined field whose one plain line says what it's for, or that the shell sets it.
  function settingsSupport(id, line, locked) {
    const text = locked ? LOCKED_LINE : line;
    return `<p class="text-field__support" id="${id}-help" data-line="${escapeHtml(text)}">${escapeHtml(text)}</p>`;
  }

  function settingsText(id, label, value, line, field, extra = "") {
    const locked = isLocked(field);
    return `
      <div class="text-field">
        <input class="text-field__input" id="${id}" value="${escapeHtml(value || "")}" placeholder=" " autocomplete="off"
          autocapitalize="off" spellcheck="false" aria-describedby="${id}-help"${extra}${locked ? " disabled" : ""}>
        <label class="text-field__label" for="${id}">${escapeHtml(label)}</label>
        ${settingsSupport(id, line, locked)}
      </div>`;
  }

  function settingsNumber(id, label, value, most, line, field) {
    const locked = isLocked(field);
    return `
      <div class="text-field">
        <input class="text-field__input" id="${id}" type="number" inputmode="numeric" min="1" max="${most}" step="1"
          value="${value}" placeholder=" " aria-describedby="${id}-help"${locked ? " disabled" : ""}>
        <label class="text-field__label" for="${id}">${escapeHtml(label)}</label>
        ${settingsSupport(id, line, locked)}
      </div>`;
  }

  // A model menu: the models file's menu, then the models Ollama has
  // installed, then the model in force if it's neither.
  function settingsModelMenu(id, label, listed, installed, chosen, line, field) {
    const known = listed.map((option) => option.id);
    const options = [
      ...listed,
      ...installed.filter((model) => !known.includes(model)).map((model) => ({ id: model, label: `${model} (installed)` })),
    ];
    if (chosen && !options.some((option) => option.id === chosen)) options.push({ id: chosen, label: chosen });
    const locked = isLocked(field);
    return `
      <div class="text-field text-field--select">
        <select class="text-field__input" id="${id}" aria-describedby="${id}-help"${locked ? " disabled" : ""}>${options
          .map((option) => `<option value="${escapeHtml(option.id)}"${option.id === chosen ? " selected" : ""}>${escapeHtml(option.label)}</option>`)
          .join("")}</select>
        <label class="text-field__label" for="${id}">${escapeHtml(label)}</label>
        ${settingsSupport(id, line, locked)}
      </div>`;
  }

  function renderSettingsBody(view) {
    const providerLocked = isLocked("provider");
    const choices = PROVIDER_CHOICES.map((choice) => `
      <label class="settings__choice">
        <input type="radio" name="settings-provider" value="${choice.id}"${choice.id === view.provider ? " checked" : ""}${providerLocked ? " disabled" : ""}>
        <span><span>${escapeHtml(choice.label)}</span><span class="settings__line">${escapeHtml(choice.line)}</span></span>
      </label>`).join("");
    const presets = view.presets
      .map((preset) => `<option value="${escapeHtml(preset.id)}">${escapeHtml(preset.label)}</option>`)
      .join("");
    const busyLine = view.force_mode === "all"
      ? "Every model fails as if busy, as app/.env sets, so the AI judge and the replies show their error cards. Turning this off lasts until a restart."
      : "Every call to the first model fails as if busy, so the fallback model answers. A restart turns this off.";
    settingsBody.innerHTML = `
      <section class="settings__section" aria-labelledby="settings-connection-title">
        <h3 class="settings__title" id="settings-connection-title">AI connection</h3>
        <fieldset class="settings__choices">
          <legend class="settings__legend">Provider</legend>
          ${choices}
          ${providerLocked ? `<p class="settings__line">${LOCKED_LINE}</p>` : ""}
        </fieldset>
        <div class="settings__group" data-settings-service hidden>
          ${selectField("settings-preset", "Service", `${presets}<option value="">Other</option>`, {
            support: "Fills in the address. You can still change it.",
          })}
          ${settingsText("settings-base-url", "Base URL", view.base_url, "Like https://api.example.com/v1.", "base_url", ' inputmode="url"')}
          <div data-settings-preset-note></div>
        </div>
        <div class="settings__group" data-settings-key-area hidden>
          <div class="text-field settings__key-field">
            <input class="text-field__input settings__key${MASK_KEY ? " is-masked" : ""}" id="settings-key"
              type="${MASK_KEY ? "text" : "password"}" placeholder=" " autocomplete="${MASK_KEY ? "off" : "new-password"}"
              autocapitalize="off" spellcheck="false" data-1p-ignore data-lpignore="true" data-bwignore data-form-type="other"
              aria-describedby="settings-key-help settings-key-free">
            <label class="text-field__label" for="settings-key" data-settings-key-label>API key</label>
            <button type="button" class="btn btn--text btn--icon-leading settings__reveal" data-action="toggle-settings-key"
              aria-controls="settings-key">
              <span class="icon" aria-hidden="true">visibility</span>
              <span>Show key</span>
            </button>
            <p class="text-field__support" id="settings-key-help" data-settings-key-state></p>
            <p class="text-field__support" id="settings-key-free" data-settings-key-free hidden>Free key, no card:
              <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer">aistudio.google.com<span class="visually-hidden"> (opens in a new tab)</span></a></p>
          </div>
          <div data-settings-key-hint></div>
        </div>
        <div class="settings__test">
          <button type="button" class="btn btn--outlined btn--icon-leading" data-action="test-settings">
            <span class="icon" aria-hidden="true">network_check</span>
            <span>Test</span>
          </button>
          <div class="settings__result-area" data-settings-result role="status"></div>
        </div>
      </section>
      <section class="settings__section" aria-labelledby="settings-models-title">
        <h3 class="settings__title" id="settings-models-title">Models</h3>
        <div class="settings__group" data-settings-models></div>
      </section>
      <section class="settings__section" data-settings-ollama aria-labelledby="settings-ollama-title" hidden>
        <h3 class="settings__title" id="settings-ollama-title">Local models</h3>
        <div data-settings-ollama-body role="status"></div>
        <button type="button" class="btn btn--text btn--icon-leading settings__check" data-action="check-ollama">
          <span class="icon" aria-hidden="true">refresh</span>
          <span>Check again</span>
        </button>
      </section>
      <details class="settings__more">
        <summary class="settings__summary">
          <span class="icon settings__chevron" aria-hidden="true">expand_more</span>
          <span class="settings__summary-title">Limits</span>
          <span class="settings__summary-note">${view.used_today} of ${view.daily_call_cap} calls used today</span>
        </summary>
        <div class="settings__fields">
          ${settingsNumber("settings-calls", "Calls per minute", view.calls_per_minute, view.max_calls_per_minute,
            `How fast the app may call the AI. Gemini's free tier allows ${view.max_calls_per_minute}.`, "calls_per_minute")}
          ${settingsNumber("settings-cap", "Daily cap", view.daily_call_cap, view.max_daily_call_cap,
            "Stops the app before Google's daily limit.", "daily_call_cap")}
          ${settingsNumber("settings-session-runs", "Session run limit", view.session_run_limit, view.max_daily_call_cap,
            "Runs one browser tab may start.", "session_run_limit")}
          ${settingsNumber("settings-session-judge", "Session judge limit", view.session_judge_limit, view.max_daily_call_cap,
            "AI checks and re-checks one browser tab may ask for.", "session_judge_limit")}
        </div>
      </details>
      <details class="settings__more">
        <summary class="settings__summary">
          <span class="icon settings__chevron" aria-hidden="true">expand_more</span>
          <span class="settings__summary-title">Advanced</span>
          <span class="settings__summary-note" data-settings-busy-note></span>
        </summary>
        <div class="settings__fields">
          <div class="settings__switch-row">
            <label class="settings__switch-label" for="settings-busy">Simulate a busy AI service (for demos)</label>
            <input type="checkbox" role="switch" class="switch" id="settings-busy" aria-describedby="settings-busy-help"${view.simulate_busy ? " checked" : ""}>
          </div>
          <p class="settings__line" id="settings-busy-help">${escapeHtml(busyLine)}</p>
          <div class="settings__switch-row">
            <label class="settings__switch-label" for="settings-decor">Decorations</label>
            <input type="checkbox" role="switch" class="switch" id="settings-decor" aria-describedby="settings-decor-help"${document.documentElement.dataset.decor === "on" ? " checked" : ""}>
          </div>
          <p class="settings__line" id="settings-decor-help">Faint drawings in empty, waiting, and finished spots. Changes right away, in this browser only.</p>
        </div>
      </details>
      <p class="settings__saved">${view.saved_at ? `These settings were saved ${escapeHtml(chatTime(view.saved_at))}. ` : ""}Every model call records the settings it used.</p>
      <p class="settings__error" data-settings-error role="alert" hidden></p>`;
  }

  // The models for a provider: menus, or typed IDs for another OpenAI-compatible service.
  function renderSettingsModels(provider, character, judge) {
    const area = settingsBody.querySelector("[data-settings-models]");
    const focused = area.contains(document.activeElement) ? document.activeElement.id : null;
    const name = settingsView.character_name;
    if (provider === "openai_compatible") {
      area.innerHTML = `
        ${settingsText("settings-character", `${name}'s model`, character, `Plays ${name}`, "character_model")}
        ${settingsText("settings-judge", "The judge's model", judge, "Reviews the chat", "judge_model")}
        <div data-settings-same></div>`;
    } else {
      const menus = providerMenus(provider);
      const installed = provider === "ollama" ? ollamaInstalled : [];
      area.innerHTML = `
        ${settingsModelMenu("settings-character", `${name}'s model`, menus.character_models, installed, character, `Plays ${name}`, "character_model")}
        ${settingsModelMenu("settings-judge", "The judge's model", menus.judge_models, installed, judge, "Reviews the chat", "judge_model")}
        <div data-settings-same></div>`;
    }
    if (focused && settingsField(focused)) settingsField(focused).focus();
    showSameModel();
  }

  // When one model would play the character and judge it, say what that means.
  function showSameModel() {
    const box = settingsBody.querySelector("[data-settings-same]");
    const character = settingsField("settings-character").value.trim();
    const same = character && character === settingsField("settings-judge").value.trim();
    const name = settingsView.character_name;
    box.innerHTML = same
      ? settingsNotice(
        "warning",
        `The same model plays ${name} and reviews the chat, so the judge checks its own replies, and its flags say "Same model reviewed". A different judge gives a more independent check.`,
        "settings__notice--warning",
      )
      : "";
  }

  // A new model for the character moves the judge off it, until the creator picks the judge.
  function moveJudgeOff(character) {
    const judge = settingsField("settings-judge");
    if (judgePicked || judge.tagName !== "SELECT" || judge.value !== character) return;
    const menus = providerMenus(chosenProvider());
    const options = Array.from(judge.options, (option) => option.value);
    const other = menus.default_judge && menus.default_judge !== character && options.includes(menus.default_judge)
      ? menus.default_judge
      : options.find((model) => model !== character);
    if (other) judge.value = other;
  }

  function showPresetNote(preset) {
    settingsBody.querySelector("[data-settings-preset-note]").innerHTML =
      preset && preset.note ? settingsNotice("info", preset.note) : "";
  }

  // The Service menu follows the base URL: a known address picks its service, any other picks Other.
  function syncPresetFromUrl() {
    const preset = presetForUrl(settingsField("settings-base-url").value);
    settingsField("settings-preset").value = preset ? preset.id : "";
    showPresetNote(preset);
  }

  // Shows the parts of the dialog the provider needs, with its saved models or its defaults.
  function showProvider(provider) {
    const view = settingsView;
    const keyed = KEY_PROVIDERS.includes(provider);
    settingsBody.querySelector("[data-settings-service]").hidden = provider !== "openai_compatible";
    settingsBody.querySelector("[data-settings-key-area]").hidden = !keyed;
    settingsBody.querySelector("[data-settings-ollama]").hidden = provider !== "ollama";
    if (keyed) {
      const key = view.keys[provider];
      let line;
      if (key.locked) line = LOCKED_LINE;
      else if (key.saved) line = key.last4 ? `Key saved, ends in ${key.last4}. Paste a new one to replace it.` : "Key saved. Paste a new one to replace it.";
      else line = provider === "gemini" ? "No key saved yet." : "No key saved yet. A service on this computer may need none.";
      const help = settingsBody.querySelector("[data-settings-key-state]");
      help.textContent = line;
      help.dataset.line = line;
      settingsBody.querySelector("[data-settings-key-label]").textContent = provider === "gemini" ? "Gemini API key" : "API key";
      settingsBody.querySelector("[data-settings-key-free]").hidden = provider !== "gemini";
      settingsField("settings-key").disabled = key.locked;
    }
    const menus = providerMenus(provider);
    const saved = provider === view.provider;
    judgePicked = false;
    renderSettingsModels(
      provider,
      saved ? view.character_model : menus.default_character || "",
      saved ? view.judge_model : menus.default_judge || "",
    );
    if (provider === "openai_compatible") syncPresetFromUrl();
    if (provider === "ollama") checkOllama();
  }

  // The connection changed, so an earlier Test result no longer holds.
  function connectionChanged() {
    connectionTested = false;
    settingsBody.querySelector("[data-settings-result]").innerHTML = "";
    showKeyHint();
  }

  // The service a pasted key's prefix points to, with the longest prefix winning, or null.
  function keyMatch(value) {
    const key = value.trim();
    if (!key) return null;
    const candidates = [
      ...settingsView.gemini_key_prefixes.map((prefix) => ({ prefix, provider: "gemini", preset: null })),
      ...settingsView.presets.flatMap((preset) => preset.key_prefixes.map((prefix) => ({ prefix, provider: "openai_compatible", preset }))),
    ];
    return candidates.filter((item) => key.startsWith(item.prefix)).sort((a, b) => b.prefix.length - a.prefix.length)[0] || null;
  }

  // "This looks like a Groq key. Use the Groq preset?" when the key points elsewhere than the form.
  function showKeyHint() {
    const box = settingsBody.querySelector("[data-settings-key-hint]");
    const provider = chosenProvider();
    const match = KEY_PROVIDERS.includes(provider) ? keyMatch(settingsField("settings-key").value) : null;
    const here = provider === "openai_compatible" ? presetForUrl(settingsField("settings-base-url").value) : null;
    const fits = match && match.provider === provider && (!match.preset || (here && here.id === match.preset.id));
    if (!match || fits || isLocked("provider")) {
      box.innerHTML = "";
      lastKeyHint = "";
      return;
    }
    const name = match.preset ? match.preset.label : "Gemini";
    const article = /^[aeiouxAEIOUX]/.test(name) ? "an" : "a";
    const text = `This looks like ${article} ${name} key. ${match.preset ? `Use the ${name} preset?` : "Use Gemini?"}`;
    box.innerHTML = settingsNotice(
      "lightbulb",
      text,
      "",
      `<button type="button" class="btn btn--text" data-action="use-key-hint" data-provider="${match.provider}"
        data-preset="${match.preset ? escapeHtml(match.preset.id) : ""}">Use ${escapeHtml(name)}</button>`,
    );
    if (text !== lastKeyHint) announce(text);
    lastKeyHint = text;
  }

  async function checkOllama() {
    const ticket = ++ollamaRequest;
    const box = settingsBody.querySelector("[data-settings-ollama-body]");
    box.innerHTML = '<p class="settings__line">Looking for Ollama on this computer.</p>';
    let found;
    try {
      found = await WorkbenchApi.ollamaModels();
    } catch (error) {
      found = { running: false, models: [], missing: [], message: error.message };
    }
    if (ticket !== ollamaRequest || !settingsDialog.open) return;
    ollamaInstalled = found.models;
    const list = found.models.length
      ? `<ul class="settings__list">${found.models.map((model) => `<li>${escapeHtml(model)}</li>`).join("")}</ul>`
      : "";
    const missing = found.running
      ? found.missing.map((model) => `<p class="settings__line">${escapeHtml(model)} isn't installed. Install it with ollama pull ${escapeHtml(model)}.</p>`).join("")
      : "";
    box.innerHTML = `
      <p class="settings__ollama">
        <span class="icon" aria-hidden="true">${found.running ? "check_circle" : "info"}</span>
        <span>${escapeHtml(found.message)}</span>
      </p>
      ${list}${missing}`;
    // The menus gain the installed models and keep what was picked.
    if (chosenProvider() === "ollama") {
      renderSettingsModels("ollama", settingsField("settings-character").value, settingsField("settings-judge").value);
    }
  }

  // Advanced holds two switches, so its note names the one that matters in a demo.
  function showBusyNote() {
    settingsBody.querySelector("[data-settings-busy-note]").textContent = settingsField("settings-busy").checked ? "Busy service on" : "";
  }

  function settingsResult(ok, message, next) {
    return `
      <div class="settings__result ${ok ? "settings__result--ok" : "settings__result--error"}">
        <span class="icon" aria-hidden="true">${ok ? "check_circle" : "error"}</span>
        <div>
          <p class="settings__result-message">${escapeHtml(message)}</p>
          ${next ? `<p class="settings__result-next">${escapeHtml(next)}</p>` : ""}
        </div>
      </div>`;
  }

  // An error the server tied to one field shows in that field's line, M3 style.
  function showSettingsFieldError(field, message) {
    const control = SETTINGS_FIELDS[field] ? settingsField(SETTINGS_FIELDS[field]) : null;
    if (!control) return null;
    const wrap = control.closest(".text-field");
    wrap.classList.add("text-field--error");
    control.setAttribute("aria-invalid", "true");
    wrap.querySelector(".text-field__support").textContent = message;
    const section = control.closest("details");
    if (section) section.open = true;
    return control;
  }

  function clearSettingsFieldError(control) {
    const wrap = control.closest(".text-field");
    if (!wrap || !wrap.classList.contains("text-field--error")) return;
    wrap.classList.remove("text-field--error");
    control.removeAttribute("aria-invalid");
    const help = wrap.querySelector(".text-field__support");
    help.textContent = help.dataset.line || "";
  }

  function clearSettingsErrors() {
    settingsBody.querySelectorAll('[aria-invalid="true"]').forEach(clearSettingsFieldError);
    const box = settingsBody.querySelector("[data-settings-error]");
    box.hidden = true;
    box.textContent = "";
  }

  function showSettingsError(message) {
    const box = settingsBody.querySelector("[data-settings-error]");
    box.textContent = message;
    box.hidden = false;
  }

  // Typing and picking in the dialog. One listener each for the whole body,
  // so redraws never stack listeners.
  settingsBody.addEventListener("input", (event) => {
    const control = event.target;
    if (!settingsView) return;
    clearSettingsFieldError(control);
    if (control.id === "settings-key") {
      connectionChanged();
    } else if (control.id === "settings-base-url") {
      syncPresetFromUrl();
      connectionChanged();
    } else if (control.id === "settings-character") {
      moveJudgeOff(control.value);
      showSameModel();
      connectionChanged();
    } else if (control.id === "settings-judge") {
      judgePicked = true;
      showSameModel();
    }
  });

  settingsBody.addEventListener("change", (event) => {
    const control = event.target;
    if (!settingsView) return;
    if (control.name === "settings-provider") {
      showProvider(control.value);
      connectionChanged();
    } else if (control.id === "settings-preset") {
      const preset = presetById(control.value);
      if (preset) settingsField("settings-base-url").value = preset.base_url;
      clearSettingsFieldError(settingsField("settings-base-url"));
      showPresetNote(preset);
      connectionChanged();
    } else if (control.id === "settings-busy") {
      showBusyNote();
    } else if (control.id === "settings-decor") {
      // Not part of Save or Cancel: it applies now and stays in this browser.
      applyDecorations(control.checked);
      rememberDecorations(control.checked);
    }
  });

  // Closing with changes asks first, from Cancel, Escape, or the scrim.
  function closeSettings() {
    if (settingsSaving) return;
    if (!settingsChanged()) {
      settingsDialog.close();
      return;
    }
    const back = document.activeElement;
    openDialog(discardSettingsDialog, null, (choice) => {
      if (choice === "discard") settingsDialog.close();
      else if (back && settingsDialog.contains(back)) back.focus();
    });
  }

  dialogGuards.set(settingsDialog, closeSettings);

  settingsDialog.addEventListener("cancel", (event) => {
    if (settingsSaving || settingsChanged()) {
      event.preventDefault();
      closeSettings();
    }
  });

  actions["open-settings"] = async (button) => {
    if (settingsOpening || settingsDialog.open) return;
    settingsOpening = true;
    try {
      settingsView = await WorkbenchApi.getSettings();
    } catch (error) {
      showSnackbar(`Settings didn't open. ${error.message}`);
      return;
    } finally {
      settingsOpening = false;
    }
    connectionTested = false;
    judgePicked = false;
    ollamaInstalled = [];
    lastKeyHint = "";
    renderSettingsBody(settingsView);
    showProvider(settingsView.provider);
    showBusyNote();
    settingsStart = JSON.stringify(settingsDraft());
    openDialog(settingsDialog, button, () => {
      // A typed key leaves the page with the dialog.
      settingsBody.innerHTML = "";
      settingsSaving = false;
      settingsTesting = false;
      ollamaRequest += 1;
    });
    settingsBody.querySelector('input[name="settings-provider"]:checked').focus();
  };

  actions["cancel-settings"] = () => {
    if (settingsDialog.open) closeSettings();
  };

  // Shows or hides what was typed in this dialog. The saved key never comes to the page at all.
  actions["toggle-settings-key"] = (button) => {
    const key = settingsField("settings-key");
    const show = button.dataset.shown !== "true";
    button.dataset.shown = String(show);
    if (MASK_KEY) key.classList.toggle("is-masked", !show);
    else key.type = show ? "text" : "password";
    button.querySelector(".icon").textContent = show ? "visibility_off" : "visibility";
    button.querySelector(".icon + span").textContent = show ? "Hide key" : "Show key";
    announce(show ? "The key you typed shows." : "The key you typed is hidden.");
  };

  actions["use-key-hint"] = (button) => {
    const provider = button.dataset.provider;
    const radio = settingsBody.querySelector(`input[name="settings-provider"][value="${provider}"]`);
    if (!radio || radio.disabled) return;
    radio.checked = true;
    showProvider(provider);
    const preset = presetById(button.dataset.preset);
    if (preset) {
      settingsField("settings-preset").value = preset.id;
      settingsField("settings-base-url").value = preset.base_url;
      showPresetNote(preset);
    }
    connectionChanged();
    settingsField("settings-key").focus();
    announce(`Switched to ${preset ? preset.label : "Gemini"}.`);
  };

  actions["check-ollama"] = () => {
    if (settingsView && settingsDialog.open) checkOllama();
  };

  actions["test-settings"] = async (button) => {
    if (!settingsView || !settingsDialog.open || settingsTesting || settingsSaving) return;
    const area = settingsBody.querySelector("[data-settings-result]");
    clearSettingsErrors();
    settingsTesting = true;
    button.setAttribute("aria-disabled", "true");
    area.innerHTML = '<p class="settings__line">Testing with one tiny call. This takes a few seconds.</p>';
    try {
      const result = await WorkbenchApi.testSettings(settingsDraft());
      if (!settingsDialog.open) return;
      area.innerHTML = settingsResult(result.ok, result.message, result.next);
      connectionTested = result.ok;
    } catch (error) {
      if (!settingsDialog.open) return;
      area.innerHTML = settingsResult(false, error.message, "");
      if (error.field) showSettingsFieldError(error.field, error.message);
    } finally {
      settingsTesting = false;
      button.setAttribute("aria-disabled", "false");
    }
  };

  actions["save-settings"] = async (button) => {
    if (!settingsView || !settingsDialog.open || settingsSaving || settingsTesting) return;
    const draft = settingsDraft();
    const newConnection = Boolean(draft.api_key) || draft.provider !== settingsView.provider ||
      (draft.provider === "openai_compatible" && draft.base_url !== settingsView.base_url);
    const untested = newConnection && !connectionTested;
    clearSettingsErrors();
    settingsSaving = true;
    button.setAttribute("aria-disabled", "true");
    try {
      const saved = await WorkbenchApi.saveSettings(draft);
      settingsView = saved;
      settingsSaving = false;
      settingsDialog.close();
      const key = saved.keys[saved.provider];
      const parts = ["Settings saved."];
      if (draft.api_key && key && key.saved) parts.push(key.last4 ? `Key saved, ends in ${key.last4}.` : "Key saved.");
      if (untested) parts.push("Press Test to check the connection.");
      showSnackbar(parts.join(" "));
      await settingsApplied();
    } catch (error) {
      settingsSaving = false;
      if (!settingsDialog.open) return;
      const control = error.field ? showSettingsFieldError(error.field, error.message) : null;
      if (control) control.focus();
      else showSettingsError(error.message);
    } finally {
      button.setAttribute("aria-disabled", "false");
    }
  };

  // The screens pick up what was saved: the Run screen's menu and limits, and
  // the open chat's check, which a new judge may not cover yet.
  async function settingsApplied() {
    const landOnStart = Boolean(document.activeElement && document.activeElement.dataset.focusKey === "connect-ai");
    await loadRunOptions();
    if (runOptions) state.runSetup.modelId = runOptions.default_model;
    refreshRun(landOnStart ? { focusKey: "start-run" } : undefined);
    if (state.chatId) loadCheck(state.chatId);
  }

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
  // It lives in memory, so a reload follows the system setting again.
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

  // Decorations ------------------------------------------------------------
  // Original drawings for quiet places only (styles.css says how they look
  // and move): the mascot with still art in empty states, the magnifier
  // while a check runs, the sparkle after a chat's last call, and still art
  // in the side margins of wide windows. All are drawn here as inline SVG,
  // so they work offline, and all are aria-hidden. They show while the
  // Decorations switch in Settings, Advanced is on. It starts on, and this
  // browser remembers it.

  const DECOR_KEY = "workbench-decorations";
  // Line IDs for the faint art: the 2nd knowledge limit, the 4th behavior
  // rule, and so on, from the spec on screen once it has loaded.
  const DECOR_PICKS = [["K", 2], ["B", 4], ["C", 17], ["R", 3]];

  function decorationsOn() {
    try {
      return localStorage.getItem(DECOR_KEY) !== "off";
    } catch {
      return true;
    }
  }

  function applyDecorations(on) {
    document.documentElement.dataset.decor = on ? "on" : "off";
  }

  function rememberDecorations(on) {
    try {
      localStorage.setItem(DECOR_KEY, on ? "on" : "off");
    } catch {
      // Storage can be off; the choice then lasts until a reload.
    }
  }

  // Nothing moves while the tab is hidden (styles.css keys off this).
  function trackPageVisibility() {
    document.documentElement.toggleAttribute("data-page-hidden", document.hidden);
  }

  document.addEventListener("visibilitychange", trackPageVisibility);

  function decorIds() {
    const ids = state.specView
      ? state.specView.body.sections.flatMap((section) => section.lines.map((line) => line.id))
      : [];
    return DECOR_PICKS.map(([letter, nth]) => {
      const same = ids.filter((id) => id[0] === letter);
      return same.length > 0 ? same[Math.min(nth, same.length) - 1] : `${letter}${nth}`;
    });
  }

  // The mascot: a friendly theater mask, like the top bar's mark. Its eyes
  // blink and its head tilts now and then.
  function mascotSvg() {
    return `
      <svg class="mascot" viewBox="0 0 64 64" width="56" height="56" focusable="false" aria-hidden="true">
        <path class="mascot__ribbon" d="M11 20C5 22 4 30 8 35M53 20C59 22 60 30 56 35"/>
        <path class="mascot__face" d="M11 14C21 7 43 7 53 14C56 31 50 47 32 57C14 47 8 31 11 14Z"/>
        <path class="mascot__brow" d="M17 21Q22.5 17 28 21M36 21Q41.5 17 47 21"/>
        <g class="mascot__eyes">
          <ellipse class="mascot__ink" cx="22.5" cy="27" rx="4.5" ry="3"/>
          <ellipse class="mascot__ink" cx="41.5" cy="27" rx="4.5" ry="3"/>
        </g>
        <circle class="mascot__cheek" cx="17.5" cy="35" r="3.2"/>
        <circle class="mascot__cheek" cx="46.5" cy="35" r="3.2"/>
        <path class="mascot__ink" d="M22 38Q32 50 42 38Q32 43 22 38Z"/>
      </svg>`;
  }

  function bubbleSvg(flip = false) {
    return `
      <svg class="decor-bubble${flip ? " decor-bubble--flip" : ""}" viewBox="0 0 44 34" width="44" height="34" focusable="false" aria-hidden="true">
        <path d="M7 3h30a4 4 0 0 1 4 4v14a4 4 0 0 1-4 4H18l-8 6v-6H7a4 4 0 0 1-4-4V7a4 4 0 0 1 4-4z"/>
        <path d="M10 11h20M10 17h13"/>
      </svg>`;
  }

  function idTag(id) {
    return `<span class="decor-id">${escapeHtml(id)}</span>`;
  }

  // An empty state's drawing: the mascot with still, faint art around it,
  // speech bubbles for a chat ("chat") or line IDs for flags ("ids").
  function decorScene(kind) {
    const art = kind === "chat" ? [bubbleSvg(), bubbleSvg(true), bubbleSvg()] : decorIds().map(idTag);
    return `
      <div class="decor decor-scene" aria-hidden="true">
        <div class="decor-art">
          ${art.map((item, i) => `<span class="decor-scene__item decor-scene__item--${i + 1}">${item}</span>`).join("")}
        </div>
        ${mascotSvg()}
      </div>`;
  }

  // While a check or re-check runs: a magnifier sweeps a faux line of words.
  // The status words beside it say what's happening; this only decorates.
  function decorScan() {
    return `
      <div class="decor decor-scan" aria-hidden="true">
        <div class="decor-scan__line decor-art">${'<span class="decor-scan__word"></span>'.repeat(7)}</div>
        <div class="decor-scan__mover">
          <svg class="decor-scan__lens" viewBox="0 0 32 32" width="32" height="32" focusable="false" aria-hidden="true">
            <circle cx="13" cy="13" r="9"/>
            <path d="M20 20l8 8"/>
          </svg>
        </div>
      </div>`;
  }

  // Three small stars that play once, after the call that leaves no open
  // flag in a chat (see sendCall).
  function sparkleHtml() {
    const star = '<svg class="decor-sparkle__star" viewBox="0 0 12 12" focusable="false" aria-hidden="true"><path d="M6 0L7.4 4.6L12 6L7.4 7.4L6 12L4.6 7.4L0 6L4.6 4.6Z"/></svg>';
    return `<span class="decor decor-sparkle" aria-hidden="true">${star.repeat(3)}</span>`;
  }

  // The side margins of wide windows, redrawn when the spec loads so the
  // line IDs match it. styles.css shows them from 1440px.
  function drawMarginArt() {
    const [first, second, third] = decorIds();
    const side = (where, items) => `
      <div class="decor-margins__side decor-margins__side--${where} decor-art">
        ${items.map((item) => `<span class="decor-margins__item">${item}</span>`).join("")}
      </div>`;
    document.querySelector("[data-decor-margins]").innerHTML =
      side("start", [bubbleSvg(), idTag(first), bubbleSvg(true)]) + side("end", [idTag(second), bubbleSvg(true), idTag(third)]);
  }

  // Walkthrough, from the "?" in the top app bar -----------------------------
  // The words of every step live in TOUR_STEPS. A step can open a screen
  // first. Its ring goes around the first of its spots that is drawn, and
  // until one is (no chat checked yet, the spec still loading) around its
  // anchor, a data-tour element of index.html, so every step makes sense on
  // a first visit. Escape skips, Tab stays in the card, and closing returns
  // to the screen the tour started on and to the control that opened it.

  const TOUR_STEPS = [
    {
      anchor: "brand",
      title: "Welcome to the workbench",
      text: "Build an AI character that stays in character. You write its spec, test it in chats, and decide which flagged breaks are real.",
    },
    {
      anchor: "settings",
      title: "Connect an AI",
      text: "Open Settings to choose an AI service, paste its key, then press Test and Save. You need this before a live run or an AI check.",
    },
    {
      screen: "define",
      anchor: "define",
      spots: [".spec-toolbar"],
      title: "Spec editor",
      text: "Every spec line has an ID, like K2 for knowledge limit 2, and each save makes a new version, so older runs keep theirs. Scene says where and when the user meets the character.",
    },
    {
      screen: "run",
      anchor: "run",
      spots: [".run-setup"],
      title: "Run a conversation",
      text: "Pick a test script and a model, then press Start run and watch each reply arrive. You can also import a saved chat.",
    },
    {
      screen: "run",
      anchor: "run",
      spots: [".check-start", ".check"],
      title: "Check this chat",
      text: "After a run, Check this chat counts sentences, looks for banned words, and has an AI judge read the whole chat. Each possible break becomes a flag with a quote and the spec line it breaks.",
    },
    {
      screen: "diagnose",
      anchor: "diagnose",
      spots: [".flag-card", ".review__bar-wrap"],
      title: "Flag review",
      text: "Open the evidence with Show in context before you Agree, or Override a flag with a reason when the AI is wrong. Follow-up re-check has the AI look again at its weakest flags.",
    },
    {
      screen: "compare",
      anchor: "compare",
      spots: [".drift"],
      title: "Compare runs",
      text: "Chats that ran the same script on the same spec version line up turn by turn, so you can see where each one broke. Flags you overrode don't count as breaks.",
    },
    {
      anchor: "tour",
      title: "Take the tour again",
      text: "Press this button any time to see these steps again.",
    },
  ];

  // Set once the walkthrough has opened in this browser. Blocked storage only
  // means it opens again on the next visit.
  const TOUR_SEEN_KEY = "workbench-tour-seen";
  const tourDialog = document.getElementById("tour-dialog");
  const tourRing = tourDialog.querySelector("[data-tour-ring]");
  const tourCard = tourDialog.querySelector("[data-tour-card]");
  const tourButtons = {
    skip: tourDialog.querySelector('[data-action="tour-skip"]'),
    back: tourDialog.querySelector('[data-action="tour-back"]'),
    next: tourDialog.querySelector('[data-action="tour-next"]'),
  };
  const phoneQuery = window.matchMedia("(max-width: 599px)");
  // The open tour, as { step, startScreen, target }, or null.
  let tour = null;
  let tourFrame = 0;
  // Redraws can move the target, so the ring follows the page's size too.
  const tourResize = "ResizeObserver" in window ? new ResizeObserver(() => placeTourSoon()) : null;

  function tourSeen() {
    try {
      return localStorage.getItem(TOUR_SEEN_KEY) === "1";
    } catch {
      return false;
    }
  }

  function rememberTourSeen() {
    try {
      localStorage.setItem(TOUR_SEEN_KEY, "1");
    } catch {
      // Storage can be off; the tour then opens again next time.
    }
  }

  function openTour(opener) {
    if (tour || document.querySelector("dialog[open]")) return;
    rememberTourSeen();
    hideTooltip();
    tour = { step: 0, startScreen: currentScreen, target: null };
    document.documentElement.toggleAttribute("data-touring", true);
    tourDialog.querySelector("[data-tour-mascot]").innerHTML = mascotSvg();
    // The words go in first, so the dialog opens with its name.
    showTourWords(0);
    openDialog(tourDialog, opener, closeTour);
    tourButtons.next.focus();
    window.addEventListener("scroll", placeTourSoon, { capture: true, passive: true });
    window.addEventListener("resize", placeTourSoon);
    if (tourResize) tourResize.observe(document.body);
    if (document.fonts) document.fonts.ready.then(placeTourSoon);
    placeTour({ scroll: true });
  }

  // Runs as the dialog closes (Done, Skip tutorial, or Escape), before focus
  // goes back to the control that opened it.
  function closeTour() {
    window.removeEventListener("scroll", placeTourSoon, { capture: true });
    window.removeEventListener("resize", placeTourSoon);
    if (tourResize) tourResize.disconnect();
    cancelAnimationFrame(tourFrame);
    const start = tour ? tour.startScreen : null;
    tour = null;
    document.documentElement.toggleAttribute("data-touring", false);
    tourDialog.querySelector("[data-tour-mascot]").innerHTML = "";
    if (start && start !== currentScreen) visitScreen(start);
  }

  // Opens a screen without a history entry, so Back after the tour doesn't
  // step through the screens it showed. The hash change that follows finds
  // the screen already showing.
  function visitScreen(id) {
    showScreen(id);
    location.replace(`#${id}`);
  }

  function showTourWords(index) {
    const step = TOUR_STEPS[index];
    const last = index === TOUR_STEPS.length - 1;
    tourDialog.querySelector("[data-tour-count]").textContent = `Step ${index + 1} of ${TOUR_STEPS.length}`;
    tourDialog.querySelector("[data-tour-title]").textContent = step.title;
    tourDialog.querySelector("[data-tour-text]").textContent = step.text;
    tourButtons.back.hidden = index === 0;
    tourButtons.skip.hidden = last;
    tourButtons.next.textContent = last ? "Done" : "Next";
  }

  function showTourStep(index) {
    const step = TOUR_STEPS[index];
    tour.step = index;
    showTourWords(index);
    if (step.screen && step.screen !== currentScreen) visitScreen(step.screen);
    placeTour({ scroll: true });
    // A button that just hid (Back on the first step) hands focus to Next.
    if (!tourCard.contains(document.activeElement)) tourButtons.next.focus();
  }

  // The first drawn spot of the step on its screen, else its anchor.
  function tourTarget(step) {
    const panel = step.screen ? panelFor(step.screen) : null;
    for (const selector of step.spots || []) {
      const spot = panel ? panel.querySelector(selector) : null;
      if (spot && spot.getClientRects().length > 0) return spot;
    }
    return document.querySelector(`[data-tour="${step.anchor}"]`);
  }

  // The box to ring. The title's own box fills the bar's free space, so the
  // ring goes around its words instead.
  function tourBox(target) {
    if (!target) return null;
    let box = target.getBoundingClientRect();
    if (target.dataset.tour === "brand") {
      const words = document.createRange();
      words.selectNodeContents(target);
      box = words.getBoundingClientRect();
    }
    return box.width > 0 && box.height > 0 ? box : null;
  }

  // A target on a screen scrolls to just below the header (and Flag review's
  // sticky bar). The header's own controls need no scrolling, except on
  // phones, where the header scrolls away with the page.
  function revealTourTarget(target) {
    if (!target) return;
    if (header.contains(target)) {
      if (getComputedStyle(header).position !== "sticky") window.scrollTo(0, 0);
      return;
    }
    scrollBelowHeader(target);
  }

  function placeTour({ scroll = false } = {}) {
    if (!tour) return;
    // Room under the page as tall as the card, so a target at the very end
    // can still scroll up above a docked card.
    document.documentElement.style.setProperty("--tour-room", `${tourCard.offsetHeight + 32}px`);
    const target = tourTarget(TOUR_STEPS[tour.step]);
    // A spot that just got drawn takes over from the anchor, so it scrolls into view.
    const moved = target !== tour.target;
    tour.target = target;
    if (scroll || moved) revealTourTarget(target);
    const box = tourBox(target);
    tourDialog.classList.toggle("is-untargeted", !box);
    tourRing.hidden = !box;
    if (box) {
      const pad = 6;
      tourRing.style.left = `${box.left - pad}px`;
      tourRing.style.top = `${box.top - pad}px`;
      tourRing.style.width = `${box.width + pad * 2}px`;
      tourRing.style.height = `${box.height + pad * 2}px`;
    }
    placeTourCard(box);
  }

  // Below the ring if the card fits there, else above it, else docked at
  // the bottom of the window, where it always sits on a phone.
  function placeTourCard(box) {
    const margin = 16;
    let spot = null;
    if (box && !phoneQuery.matches) {
      const card = tourCard.getBoundingClientRect();
      const below = box.bottom + margin;
      const above = box.top - margin - card.height;
      let top = null;
      if (below + card.height <= window.innerHeight - margin) top = below;
      else if (above >= margin) top = above;
      if (top !== null) {
        spot = { top, left: Math.min(Math.max(margin, box.left), window.innerWidth - card.width - margin) };
      }
    }
    tourDialog.classList.toggle("is-docked", !spot);
    tourCard.style.top = spot ? `${spot.top}px` : "";
    tourCard.style.left = spot ? `${spot.left}px` : "";
  }

  function placeTourSoon() {
    cancelAnimationFrame(tourFrame);
    tourFrame = requestAnimationFrame(() => placeTour());
  }

  // Tab and Shift+Tab go round the card's buttons and never leave it.
  tourDialog.addEventListener("keydown", (event) => {
    if (event.key !== "Tab") return;
    const buttons = Object.values(tourButtons).filter((button) => !button.hidden);
    const first = buttons[0];
    const last = buttons[buttons.length - 1];
    const at = buttons.indexOf(document.activeElement);
    if (at === -1 || (event.shiftKey && at === 0) || (!event.shiftKey && at === buttons.length - 1)) {
      event.preventDefault();
      (event.shiftKey ? last : first).focus();
    }
  });

  actions["start-tour"] = (button) => openTour(button);

  actions["tour-next"] = () => {
    if (!tour) return;
    if (tour.step === TOUR_STEPS.length - 1) tourDialog.close("done");
    else showTourStep(tour.step + 1);
  };

  actions["tour-back"] = () => {
    if (tour && tour.step > 0) showTourStep(tour.step - 1);
  };

  actions["tour-skip"] = () => {
    if (tour) tourDialog.close("skip");
  };

  // 6. Start ===============================================================

  applyTheme(darkQuery && darkQuery.matches ? "dark" : "light");
  applyDecorations(decorationsOn());
  trackPageVisibility();
  drawMarginArt();
  window.addEventListener("hashchange", onHashChange);
  revealIconsWhenReady();
  updateHeader();

  const firstScreen = screenFromHash();
  if (!firstScreen) location.replace(`#${DEFAULT_SCREEN}`);
  showScreen(firstScreen || DEFAULT_SCREEN);
  loadSpec();
  loadRunOptions();
  loadSamples();
  loadChats();
  loadReview();
  // A first visit opens the walkthrough once.
  if (!tourSeen()) openTour(null);
})();
