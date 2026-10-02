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
    5. Dialogs, snackbar, and top app bar
    6. Start
*/
(() => {
  "use strict";

  // 1. Data and state ======================================================

  const main = document.getElementById("main");

  if (!window.WORKBENCH_DATA) {
    main.innerHTML =
      '<p class="load-error">The demo data did not load. Check that data.js is in the same folder as index.html.</p>';
    return;
  }

  // Frozen, so no screen can change the original by accident. Screens read
  // and change `state`, which is a copy; "Reset demo" makes a fresh one.
  const DATA = deepFreeze(window.WORKBENCH_DATA);

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

  // Where a flag sits, for example "Run 1, turn 4".
  function flagPlace(run, flag) {
    return `${run.name}, turn ${flag.turn}`;
  }

  const CONFIDENCE_ICONS = {
    High: "signal_cellular_alt",
    Medium: "signal_cellular_alt_2_bar",
    Low: "signal_cellular_alt_1_bar",
  };

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
  // chip opens a side sheet with the demo flags that cite that line, and
  // "Edit spec" says that only the creator can change the spec (DESIGN_SPEC
  // 7.1). Runs stay pinned to the version they used.

  const citingSheet = document.getElementById("citing-flags-sheet");
  const editSpecDialog = document.getElementById("edit-spec-dialog");
  let specCountTimer = 0;

  function renderDefine(body) {
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
    renderSpecResults(body, { announce: false });
  }

  // Redraws only the cards, so the search field keeps focus while you type.
  function renderSpecResults(body, { announce = true } = {}) {
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
          ${renderSpecLines(lines, terms)}
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

  function renderSpecLines(lines, terms) {
    const items = lines.map((line) => {
      const text = `<p class="spec-line__text">${highlight(line.text, terms)}</p>`;
      if (line.id) {
        return `
          <li class="spec-line">
            <button type="button" class="chip chip--assist spec-line__id" data-action="show-citing-flags"
              data-line="${escapeHtml(line.id)}" data-focus-key="line-${escapeHtml(line.id)}" aria-haspopup="dialog">
              ${escapeHtml(line.id)}<span class="visually-hidden">, show flags that cite this line</span>
            </button>
            ${text}
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

  // Side sheet body: the line itself, then every demo flag that cites it.
  function renderCitingFlags(lineId) {
    const citing = allFlags().filter(({ flag }) => flag.cites.includes(lineId));
    let summary = `${citing.length} demo flags cite this line.`;
    if (citing.length === 0) summary = "No demo flags cite this line.";
    if (citing.length === 1) summary = "1 demo flag cites this line.";

    return `
      <div class="cited-line">
        <span class="chip">${escapeHtml(lineId)}</span>
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

  function renderRun(body) {
    body.innerHTML = emptyState();
  }

  // 3.3 Flag review (Diagnose) ----------------------------------------------

  function renderDiagnose(body) {
    const target = state.openFlagId ? findFlag(state.openFlagId) : null;
    const note = target
      ? `You chose the flag at ${flagPlace(target.run, target.flag)}. This screen will open there once it is built.`
      : "";
    body.innerHTML = emptyState(note);
  }

  // 3.4 Compare runs (Repair) -----------------------------------------------

  function renderCompare(body) {
    body.innerHTML = emptyState();
  }

  // Placeholder until each screen is built.
  function emptyState(note = "") {
    return `
      <div class="card card--outlined empty-state">
        <span class="icon" aria-hidden="true">construction</span>
        <div>
          <p>Nothing on this screen yet.</p>
          ${note ? `<p class="empty-state__note">${escapeHtml(note)}</p>` : ""}
        </div>
      </div>`;
  }

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

    renderScreen(id);
    if (isChange) window.scrollTo(0, 0);
    if (moveFocus) panelFor(id).querySelector(".screen__title").focus({ preventScroll: true });
  }

  function renderScreen(id) {
    SCREENS[id].render(panelFor(id).querySelector("[data-screen-body]"));
  }

  // Redraws the current screen after a state change, then puts focus back
  // on the control that had it (matched by data-focus-key), or on the
  // screen heading if that control is gone.
  function refresh() {
    const panel = panelFor(currentScreen);
    const body = panel.querySelector("[data-screen-body]");
    const active = document.activeElement;
    const focusWasInBody = body.contains(active);
    const focusKey = focusWasInBody ? active.getAttribute("data-focus-key") : null;

    renderScreen(currentScreen);

    if (!focusWasInBody) return;
    const target = focusKey
      ? body.querySelector(`[data-focus-key="${CSS.escape(focusKey)}"]`)
      : null;
    (target || panel.querySelector(".screen__title")).focus();
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

  // 5. Dialogs, snackbar, and top app bar ==================================

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
      state = createInitialState();
      refresh();
      showSnackbar("Demo reset. Everything is back to the starting data.");
    });
  });

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

  // M3: the top app bar changes color once content scrolls under it.
  const header = document.getElementById("app-header");

  function updateHeader() {
    header.classList.toggle("is-scrolled", window.scrollY > 0);
  }

  window.addEventListener("scroll", updateHeader, { passive: true });

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

  window.addEventListener("hashchange", onHashChange);
  revealIconsWhenReady();
  updateHeader();

  const firstScreen = screenFromHash();
  if (!firstScreen) location.replace(`#${DEFAULT_SCREEN}`);
  showScreen(firstScreen || DEFAULT_SCREEN);
})();
