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
    5. Reset demo, snackbar, and top app bar
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
      // Screens add the fields they need here, such as the creator's
      // decision on each flag.
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

  // 3. Screens =============================================================
  // Each render function fills its screen's body from `state`.
  // - Clickable controls carry data-action="name"; add a handler to
  //   `actions` under that name.
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

  main.addEventListener("click", (event) => {
    const control = event.target.closest("[data-action]");
    const handler = control && actions[control.dataset.action];
    if (handler) handler(control, event);
  });

  // Screen 1: Spec editor (Define)
  function renderDefine(body) {
    body.innerHTML = emptyState();
  }

  // Screen 2: Run a conversation (Stress-test)
  function renderRun(body) {
    body.innerHTML = emptyState();
  }

  // Screen 3: Flag review (Diagnose)
  function renderDiagnose(body) {
    body.innerHTML = emptyState();
  }

  // Screen 4: Compare runs (Repair)
  function renderCompare(body) {
    body.innerHTML = emptyState();
  }

  // Placeholder until each screen is built.
  function emptyState() {
    return `
      <div class="card card--outlined empty-state">
        <span class="icon" aria-hidden="true">construction</span>
        <p>Nothing on this screen yet.</p>
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
  // from a transcript to its flags.
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

  // 5. Reset demo, snackbar, and top app bar ================================

  const resetButton = document.getElementById("reset-demo");
  const resetDialog = document.getElementById("reset-dialog");

  resetButton.addEventListener("click", () => {
    resetDialog.returnValue = "";
    resetDialog.showModal();
  });

  // Both dialog buttons submit a method="dialog" form, which closes the
  // dialog and sets returnValue to the button's value. Esc and a click on
  // the scrim close it with returnValue left empty.
  resetDialog.addEventListener("close", () => {
    if (resetDialog.returnValue === "reset") {
      state = createInitialState();
      refresh();
      showSnackbar("Demo reset. Everything is back to the starting data.");
    }
    resetButton.focus();
  });

  resetDialog.addEventListener("click", (event) => {
    if (event.target !== resetDialog) return;
    const box = resetDialog.getBoundingClientRect();
    const onScrim =
      event.clientX < box.left || event.clientX > box.right ||
      event.clientY < box.top || event.clientY > box.bottom;
    if (onScrim) resetDialog.close();
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
