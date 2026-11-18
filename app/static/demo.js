/*
  Character Consistency Workbench: the public demo's part of the page

  The server adds this file to the page only in demo mode
  (app/workbench/demo.py), after app.js, so the local workbench never loads
  it. It changes nothing in app.js or api.js. It adds the banner, swaps
  Settings for the demo code button, rewords the tour's Settings step, and
  steps in front of the buttons that need the demo code or that a limit has
  closed. It talks only to the server's /api/demo/ paths.

  The server is the guard: it checks the code and every limit on each
  request. This file only saves a visitor from a refused request, by showing
  the same message in a card first.
*/
(() => {
  "use strict";

  const STATE_PATH = "/api/demo/state";
  const CODE_PATH = "/api/demo/code";

  // Shown until the server's own wording arrives, and if it never does.
  const BANNER =
    "Public demo. Don't type anything personal: text sent to the AI goes to Google's free tier, which may use it to improve its products. Your copy of the demo is wiped after 2 hours.";
  const CODE_HEAD = "Live AI needs a demo code";
  const CODE_TEXT =
    "This link is a demo. The workbench is built to run on your own computer, with your own free AI key. Setup takes about 15 minutes.";
  const SPEC_OFF =
    "Saving a spec version is off in the public demo. To edit the spec, run the workbench on your own computer.";
  const QUICK_START = "https://github.com/FlinnH/IS492-CharacterAI-Team-Project#how-to-run-the-app";
  const FOOTER =
    "Public demo of the IS 492 workbench. Live chats, Check this chat, and Re-check make model calls and need the demo code. Your copy of the demo, with your calls on Flag review, is temporary.";

  // The tour's Settings step, by its title in app.js, and the words the demo shows in its place.
  const TOUR_SETTINGS_TITLE = "Connect an AI";
  const TOUR_DEMO_TITLE = "Live AI needs a demo code";
  const TOUR_DEMO_TEXT =
    "This demo already has an AI connected, so there is nothing to set up. The two sample chats, Flag review, and Compare runs work with no code. A live run or an AI check asks for the demo code here.";

  // Buttons of app.js that need the demo code, by their data-action. The
  // value is the visitor's limit the button counts toward: "model" for one
  // that only spends model calls, and "code" for one that only stores typed text.
  const GATED = {
    "start-run": "runs",
    "run-all": "runs",
    "new-free-chat": "runs",
    "continue-run": "model",
    "retry-turn": "model",
    "send-message": "model",
    "check-chat": "checks",
    "recheck": "rechecks",
    "start-override": "code",
    "save-override": "code",
    "open-import": "code",
    "preview-import": "code",
    "confirm-import": "code",
  };
  // Buttons that are off in the demo, with the card each one opens.
  const OFF = {
    "edit-spec": SPEC_OFF,
    "add-setting": SPEC_OFF,
  };
  const LIMIT_HEADS = {
    runs: "You've used this demo's live chats",
    checks: "You've used this demo's AI checks",
    rechecks: "You've used this demo's re-checks",
  };

  // What the server last said: { unlocked, limits, calls_left, ... }, or null.
  let state = null;
  // The button a card stepped in front of, pressed again once the code is in.
  let waiting = null;
  // The button being pressed again, which the click listener lets through.
  let passing = null;

  async function ask(method, path, body) {
    const init = { method, headers: { Accept: "application/json" } };
    if (body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
    try {
      const response = await fetch(path, init);
      const data = await response.json().catch(() => null);
      return { ok: response.ok, data };
    } catch {
      return { ok: false, data: null };
    }
  }

  async function loadState() {
    const answer = await ask("GET", STATE_PATH);
    if (answer.ok && answer.data) {
      state = answer.data;
      showState();
    }
    return answer.ok ? state : null;
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function icon(name) {
    const node = element("span", "icon", name);
    node.setAttribute("aria-hidden", "true");
    return node;
  }

  function announce(text) {
    const announcer = document.getElementById("announcer");
    if (announcer) announcer.textContent = text;
  }

  // The banner ------------------------------------------------------------

  const banner = element("div", "demo-banner");
  banner.setAttribute("role", "note");
  const bannerInner = element("div", "demo-banner__inner");
  const bannerText = element("span", "", BANNER);
  bannerInner.append(icon("info"), bannerText);
  banner.append(bannerInner);
  const header = document.getElementById("app-header");
  if (header) header.prepend(banner);
  else document.body.prepend(banner);

  const footer = document.querySelector(".app-footer p");
  if (footer) footer.textContent = FOOTER;

  // The demo code button, where Settings is in the local workbench ---------

  const codeButton = element("button", "btn btn--text btn--icon-leading");
  codeButton.type = "button";
  codeButton.dataset.demo = "code";
  codeButton.setAttribute("aria-haspopup", "dialog");
  const codeIcon = icon("key");
  const codeLabel = element("span", "", "Demo code");
  codeButton.append(codeIcon, codeLabel);
  const settingsButton = document.querySelector('.top-app-bar [data-action="open-settings"]');
  if (settingsButton) {
    settingsButton.before(codeButton);
    // The tour's Settings step now rings the demo code button.
    settingsButton.removeAttribute("data-tour");
    codeButton.dataset.tour = "settings";
  } else {
    const bar = document.querySelector(".top-app-bar__actions");
    if (bar) bar.prepend(codeButton);
  }
  codeButton.addEventListener("click", () => {
    if (state && state.unlocked) loadState().then(() => showStatusCard(codeButton));
    else showCodeCard(codeButton, null);
  });

  function showState() {
    if (!state) return;
    bannerText.textContent = state.banner || BANNER;
    codeIcon.textContent = state.unlocked ? "lock_open" : "key";
    codeLabel.textContent = state.unlocked ? "Live AI on" : "Demo code";
  }

  // The tour ---------------------------------------------------------------
  // app.js fills the tour's card from its own steps. When it shows the
  // Settings step, the demo's words go in instead.

  const tourBody = document.querySelector("#tour-dialog .tour__body");
  function fixTour() {
    const title = tourBody.querySelector("[data-tour-title]");
    const text = tourBody.querySelector("[data-tour-text]");
    if (!title || !text || title.textContent !== TOUR_SETTINGS_TITLE) return;
    title.textContent = TOUR_DEMO_TITLE;
    text.textContent = TOUR_DEMO_TEXT;
  }
  if (tourBody) {
    new MutationObserver(fixTour).observe(tourBody, { childList: true, subtree: true, characterData: true });
    fixTour();
  }

  // Cards ------------------------------------------------------------------
  // One dialog, filled for the card that is showing.

  const dialog = element("dialog", "dialog demo-dialog");
  dialog.id = "demo-dialog";
  dialog.setAttribute("aria-labelledby", "demo-dialog-title");
  const dialogTitle = element("h2", "dialog__headline");
  dialogTitle.id = "demo-dialog-title";
  const dialogBody = element("div", "dialog__content demo-dialog__content");
  const dialogActions = element("div", "dialog__actions");
  dialog.append(dialogTitle, dialogBody, dialogActions);
  document.body.append(dialog);
  let opener = null;

  // A click on the scrim around the card closes it, like the app's dialogs.
  dialog.addEventListener("click", (event) => {
    if (event.target !== dialog) return;
    const box = dialog.getBoundingClientRect();
    const outside =
      event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom;
    if (outside) dialog.close();
  });
  dialog.addEventListener("close", () => {
    waiting = null;
    if (opener && opener.isConnected) opener.focus();
    opener = null;
  });

  function button(label, className, onClick) {
    const node = element("button", `btn ${className}`, label);
    node.type = "button";
    node.addEventListener("click", onClick);
    return node;
  }

  function quickStartLine() {
    const line = element("p");
    const link = element("a", "", "Quick start in the README");
    link.href = (state && state.quick_start) || QUICK_START;
    link.target = "_blank";
    link.rel = "noopener";
    line.append(link);
    return line;
  }

  function openCard(from, title, parts, actions) {
    // A card that is already showing is refilled in place and keeps its opener.
    if (!dialog.open) opener = from;
    dialogTitle.textContent = title;
    dialogBody.replaceChildren(...parts);
    dialogActions.replaceChildren(...actions);
    if (!dialog.open) dialog.showModal();
  }

  // A plain card: a headline, a message, and Close.
  function showCard(from, title, message, withQuickStart) {
    const parts = [element("p", "", message)];
    if (withQuickStart) parts.push(quickStartLine());
    const close = button("Close", "btn--text", () => dialog.close());
    openCard(from, title, parts, [close]);
    close.focus();
  }

  function showStatusCard(from) {
    const left = (kind) => Math.max(0, state.limits[kind].limit - state.limits[kind].used);
    const message =
      `You can start ${left("runs")} more live chats (test cases and free chats count together), ` +
      `run ${left("checks")} more AI checks, and ${left("rechecks")} more re-checks. ` +
      (state.calls_left ? "Every visitor shares today's AI calls." : state.cap_message);
    showCard(from, "Live AI is on", message, false);
  }

  // The code card. pending is the button to press again once the code is in.
  function showCodeCard(from, pending) {
    const field = element("div", "text-field");
    const input = element("input", "text-field__input");
    input.id = "demo-code";
    // Dots, like a key, so the code stays off a shared screen. No form wraps
    // it, so no browser offers to save it as a password.
    input.type = "password";
    input.autocomplete = "off";
    input.spellcheck = false;
    input.placeholder = " ";
    input.setAttribute("aria-describedby", "demo-code-status");
    const label = element("label", "text-field__label", "Demo code");
    label.htmlFor = "demo-code";
    const status = element("p", "text-field__support");
    status.id = "demo-code-status";
    status.setAttribute("role", "status");
    field.append(input, label, status);

    const close = button("Close", "btn--text", () => dialog.close());
    const unlock = button("Unlock", "btn--filled", submit);
    let sending = false;

    async function submit() {
      const code = input.value.trim();
      if (sending) return;
      if (!code) {
        fail("Type the demo code first.");
        return;
      }
      sending = true;
      unlock.setAttribute("aria-disabled", "true");
      status.classList.remove("demo-dialog__status--error");
      status.textContent = "Checking the code.";
      const answer = await ask("POST", CODE_PATH, { code });
      sending = false;
      unlock.removeAttribute("aria-disabled");
      if (!answer.ok) {
        const detail = answer.data && typeof answer.data.detail === "string" ? answer.data.detail : "";
        fail(detail || "Couldn't reach the demo. Check your connection and try again.");
        return;
      }
      state = answer.data;
      showState();
      const next = waiting;
      dialog.close();
      announce("Live AI is on.");
      if (next) pass(next);
    }

    function fail(message) {
      field.classList.add("text-field--error");
      status.classList.add("demo-dialog__status--error");
      status.textContent = message;
      input.focus();
    }

    input.addEventListener("input", () => {
      field.classList.remove("text-field--error");
      status.classList.remove("demo-dialog__status--error");
      status.textContent = "";
    });
    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" || event.isComposing) return;
      event.preventDefault();
      submit();
    });

    openCard(from, CODE_HEAD, [element("p", "", CODE_TEXT), quickStartLine(), field], [close, unlock]);
    waiting = pending;
    input.focus();
  }

  // Stepping in front of app.js's buttons -----------------------------------
  // This listener runs before app.js's own, which listens on the way back up.

  function block(event) {
    event.preventDefault();
    event.stopPropagation();
  }

  // The same button after a redraw replaced it, found by what it acts on.
  function twin(control) {
    if (control.isConnected) return control;
    let selector = `[data-action="${control.dataset.action}"]`;
    ["flag", "chat"].forEach((name) => {
      if (control.dataset[name]) selector += `[data-${name}="${control.dataset[name]}"]`;
    });
    return document.querySelector(selector);
  }

  // Presses the button again, this time through to app.js.
  function pass(control) {
    const target = twin(control);
    if (!target) return;
    passing = target;
    try {
      target.click();
    } finally {
      passing = null;
    }
  }

  // The card for a limit that is used up, or false when the button may go on.
  function showLimit(control, kind) {
    const limit = state.limits[kind];
    if (limit && limit.used >= limit.limit) {
      showCard(control, LIMIT_HEADS[kind], limit.message, false);
      return true;
    }
    if (kind !== "code" && !state.calls_left) {
      showCard(control, "Today's AI calls are used up", state.cap_message, false);
      return true;
    }
    return false;
  }

  async function decide(control, kind) {
    // Asked fresh each time, since a run or a check in another tab counts too.
    const fresh = await loadState();
    if (!fresh) {
      // The server answers for itself when the demo's state can't be read.
      pass(control);
      return;
    }
    if (!fresh.unlocked) showCodeCard(twin(control), control);
    else if (!showLimit(twin(control), kind)) pass(control);
  }

  document.addEventListener(
    "click",
    (event) => {
      const control = event.target instanceof Element ? event.target.closest("[data-action]") : null;
      if (!control) return;
      const action = control.dataset.action;
      if (Object.hasOwn(OFF, action)) {
        block(event);
        showCard(control, "Off in the public demo", OFF[action], true);
        return;
      }
      if (!Object.hasOwn(GATED, action)) return;
      if (passing === control || control.disabled || control.getAttribute("aria-disabled") === "true") return;
      block(event);
      if (state && !state.unlocked) showCodeCard(control, control);
      else decide(control, GATED[action]);
    },
    true,
  );

  // Enter in the Free Chat box sends the message without a click.
  document.addEventListener(
    "keydown",
    (event) => {
      if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
      if (!(event.target instanceof Element) || event.target.id !== "free-message") return;
      if (!state || state.unlocked) return;
      block(event);
      showCodeCard(event.target, null);
    },
    true,
  );

  loadState();
})();
