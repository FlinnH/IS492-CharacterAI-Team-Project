"""Screen tests: the walkthrough, the Scene wording, the decorations, the
buttons that take people where a message sends them, the seconds a check has
run, and the tab icon, read from app/static with no browser and no network.

Every walkthrough step points at a hook index.html always has, so a step makes
sense before anything loads. The decorations keep the rules in styles.css:
faint, still background art, and movement only from the mascot, the
magnifier, and the sparkle, in transform and opacity alone."""

import re

import pytest

from conftest import APP_DIR

STATIC_DIR = APP_DIR / "static"
APP_JS = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
INDEX = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
STYLES = (STATIC_DIR / "styles.css").read_text(encoding="utf-8")

# app.js with its whole-line comments dropped, since comments quote old words
CODE = re.sub(r"^\s*//.*$", "", APP_JS, flags=re.M)
TABS = re.findall(r'role="tab"[^>]*data-screen="([a-z]+)"', INDEX)


def tour_steps():
    """The TOUR_STEPS list in app.js, as one dict of each step's string fields."""
    block = re.search(r"const TOUR_STEPS = \[(.*?)\n  \];", APP_JS, re.S)
    assert block, "app.js has no TOUR_STEPS list"
    return [dict(re.findall(r'(\w+): "([^"]*)"', body)) for body in re.findall(r"\{(.*?)\}", block.group(1), re.S)]


def css_rules(css):
    """Every innermost rule as (selector, declarations), comments dropped."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return [(selector.strip(), body) for selector, body in re.findall(r"([^{};]+)\{([^{}]*)\}", css)]


def keyframes(css):
    """Each @keyframes block's body, by name."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    found = {}
    for match in re.finditer(r"@keyframes\s+([\w-]+)\s*\{", css):
        depth, end = 1, match.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(css[end], 0)
            end += 1
        found[match.group(1)] = css[match.end():end - 1]
    return found


# The walkthrough


def test_the_tour_has_eight_steps():
    steps = tour_steps()
    assert len(steps) == 8
    assert all(step.get("anchor") and step.get("title") and step.get("text") for step in steps)


@pytest.mark.parametrize("step", tour_steps(), ids=lambda step: step["title"])
def test_every_tour_step_points_at_an_element_in_index_html(step):
    assert INDEX.count(f'data-tour="{step["anchor"]}"') == 1
    if "screen" in step:
        assert step["screen"] in TABS


def test_the_tour_visits_every_screen_and_ends_on_its_button():
    steps = tour_steps()
    assert [step["anchor"] for step in steps[:2]] == ["brand", "settings"]
    assert [step["screen"] for step in steps if "screen" in step] == ["define", "run", "run", "diagnose", "compare"]
    assert set(TABS) == {"define", "run", "diagnose", "compare"}
    assert steps[-1]["anchor"] == "tour"
    button = re.search(r'<button[^>]*data-tour="tour"[^>]*>', INDEX).group(0)
    assert 'data-action="start-tour"' in button
    assert 'aria-label="Take the tour"' in button
    assert 'data-tooltip="Take the tour"' in button


def test_the_tour_words_follow_the_prose_rules():
    for step in tour_steps():
        for words in (step["title"], step["text"]):
            assert words.isascii(), words
            assert " - " not in words and "--" not in words, words
        assert not step["title"].endswith(".")
        assert len(re.findall(r"[.!?](?=\s|$)", step["text"])) <= 2, step["text"]


def test_storage_is_only_touched_inside_try():
    # Blocked storage must only mean the tour shows again and decorations start on.
    lines = APP_JS.splitlines()
    uses = [number for number, line in enumerate(lines) if "localStorage." in line and not line.strip().startswith("//")]
    assert uses
    assert [lines[number - 1].strip() for number in uses] == ["try {"] * len(uses)


# The Scene field


def test_the_spec_field_reads_scene_on_screen():
    assert 'textField("setting", "Scene", draft.setting, {' in CODE
    assert 'hint: "Where and when the user meets the character.",' in CODE
    assert '{ label: "Scene", text: spec.setting' in CODE
    assert ">Add a scene</button>" in CODE
    assert "Add a setting" not in CODE
    assert "Where and how this conversation happens" not in CODE
    assert not re.search(r'label: "Setting"|textField\("setting", "Setting"', CODE)
    # Only the stored cite keeps the old name, which the screens show as Scene.
    assert CODE.count('"Setting"') == 1
    assert 'const SCENE_CITE = "Setting";' in CODE


# Decorations


def test_settings_has_a_decorations_switch_under_advanced():
    advanced = re.search(r'settings__summary-title">Advanced</span>(.*?)</details>', APP_JS, re.S)
    assert advanced, "Settings has no Advanced section"
    assert re.search(r'<label class="settings__switch-label" for="settings-decor">Decorations</label>', advanced.group(1))
    assert re.search(r'<input type="checkbox" role="switch" class="switch" id="settings-decor"', advanced.group(1))
    # It applies at once and stays in this browser, so Save never sends it.
    draft = re.search(r"function settingsDraft\(\) \{(.*?)\n  \}", APP_JS, re.S)
    assert "settings-decor" not in draft.group(1)


def test_background_art_stays_faint_and_still():
    assert float(re.search(r"--decor-art-opacity:\s*([0-9.]+);", STYLES).group(1)) <= 0.12
    art = [
        (selector, body)
        for selector, body in css_rules(STYLES)
        if re.search(r"decor-(art|bubble|id|scene__item|margins)", selector)
    ]
    assert art
    for selector, body in art:
        assert "animation" not in body, selector
        for value in re.findall(r"(?<![\w-])opacity:\s*([^;]+);", body):
            assert value.strip() == "var(--decor-art-opacity)", selector


def test_only_the_mascot_the_magnifier_and_the_sparkle_move():
    frames = keyframes(STYLES)
    decor = {name: body for name, body in frames.items() if name.startswith("decor-")}
    assert set(decor) == {"decor-blink", "decor-tilt", "decor-scan", "decor-sparkle"}
    for name, body in decor.items():
        assert set(re.findall(r"([a-z-]+)\s*:", body)) <= {"transform", "opacity"}, name
    runs = {}
    for selector, body in css_rules(STYLES):
        for name in decor:
            if re.search(rf"animation:[^;]*\b{name}\b", body):
                runs.setdefault(name, []).append(selector)
    assert runs == {
        "decor-blink": [".mascot__eyes"],
        "decor-tilt": [".mascot"],
        "decor-scan": [".decor-scan__mover"],
        "decor-sparkle": [".decor-sparkle__star"],
    }
    # The walkthrough changes steps in place.
    assert not [name for name in frames if name.startswith("tour")]
    assert not [selector for selector, body in css_rules(STYLES) if ".tour" in selector and "animation" in body]


def test_decorations_pause_when_hidden_and_stay_still_when_motion_is_reduced():
    assert ':root:not([data-decor="on"]) .decor' in STYLES
    assert re.search(r":root\[data-page-hidden\] \.decor \*\s*\{\s*animation-play-state: paused !important;", STYLES)
    assert 'document.addEventListener("visibilitychange", trackPageVisibility);' in APP_JS
    reduced = STYLES[STYLES.rindex("@media (prefers-reduced-motion: reduce)"):]
    assert re.search(r"\.decor \*\s*\{\s*animation: none !important;", reduced)
    assert re.search(r"\.decor-sparkle\s*\{\s*display: none;", reduced)


def test_the_sparkle_lasts_about_a_second_and_is_easy_to_see():
    rules = css_rules(STYLES)
    star = next(body for selector, body in rules if selector == ".decor-sparkle__star")
    duration = int(re.search(r"animation: decor-sparkle (\d+)ms", star).group(1))
    delays = [int(ms) for selector, body in rules if "decor-sparkle__star" in selector for ms in re.findall(r"animation-delay: (\d+)ms;", body)]
    assert 900 < duration <= 1200
    assert delays and duration + max(delays) <= 1500
    assert "infinite" not in star
    box = next(body for selector, body in rules if selector == ".decor-sparkle" and "width" in body)
    assert int(re.search(r"width: (\d+)px;", box).group(1)) >= 32
    # Agreeing with every flag gets the rubber-stamp reminder, never a sparkle.
    assert "state.sparkleFlagId = finished && !updated.agreed_with_every ? flagId : null;" in CODE


# Getting people where a message sends them


def function_body(name):
    """The source of one function in app.js, up to its closing brace at two spaces."""
    found = re.search(rf"\n  function {name}\([^)]*\) \{{(.*?)\n  \}}", CODE, re.S)
    assert found, f"app.js has no function {name}"
    return found.group(1)


def test_every_message_that_sends_people_to_another_screen_has_a_button():
    lines = CODE.splitlines()
    sends = [number for number, line in enumerate(lines) if re.search(r"\b[Oo]n (Run a conversation|Flag review|Spec editor|Compare runs)(,| first)", line)]
    assert len(sends) == 3
    for number in sends:
        nearby = "\n".join(lines[number:number + 6])
        assert re.search(r'data-action="(go-to-screen|check-changed-chat)"', nearby), lines[number]
        assert ">Go to " in nearby, lines[number]
    assert '>Go to Run a conversation</button>' in function_body("renderNoCheckedChats")
    assert '>Go to Flag review</button>' in function_body("renderCompare")


def test_go_to_buttons_name_a_real_screen():
    screens = re.findall(r'data-action="go-to-screen" data-screen="([a-z]+)"', CODE)
    assert screens and set(screens) <= set(TABS)
    assert 'actions["go-to-screen"] = (button) => goToScreen(button.dataset.screen);' in CODE


def test_every_message_that_points_to_settings_has_an_open_settings_button():
    assert re.search(r"function mentionsSettings\(text\) \{\s*return /\\bin Settings\\b/", CODE)
    button = function_body("settingsButton")
    assert 'data-action="open-settings"' in button and "<span>Open Settings</span>" in button
    # The session run limit, a turn's error, a failed check, the judge's note, and a failed re-check.
    for message, key in [
        ("blocked", "raise-limit"),
        ("error.message", "run-error-settings"),
        ("check.message", "check-error-settings"),
        ("judge.note", "judge-note-settings"),
        ("failed", "recheck-error-settings"),
    ]:
        assert re.search(rf'mentionsSettings\({re.escape(message)}\) \? [^:]*settingsButton\("{key}"\)', CODE), key


def test_a_running_check_counts_its_seconds_without_announcing_them():
    for action, entry in [("check-chat", "state.checks[chatId]"), ("recheck", "state.rechecks[chatId]")]:
        body = re.search(rf'actions\["{action}"\] = async \(button\) => \{{(.*?)\n  \}};', CODE, re.S).group(1)
        assert re.search(rf"{re.escape(entry)} = \{{ status: \"running\",[^}}]*startedAt: Date\.now\(\) \}};", body), action
        assert "startElapsedTimer();" in body, action
    # The count sits in the status text, never inside the bar or the magnifier,
    # which hide or show by the Decorations switch.
    check = function_body("renderCheck")
    assert check.index("elapsedLine(check.startedAt)") < check.index('<div class="check-progress"')
    follow_up = function_body("renderFollowUp")
    assert follow_up.index("elapsedLine(recheck.startedAt)") < follow_up.index('<div class="check-progress"')
    assert '`${seconds} ${seconds === 1 ? "second" : "seconds"} so far`' in function_body("elapsedText")
    line = function_body("elapsedLine")
    assert "data-elapsed-since" in line and "aria-live" not in line and "role=" not in line
    # One timer, once a second, updating the text in place and stopping when nothing runs.
    timer = function_body("startElapsedTimer")
    assert "setInterval(" in timer and "}, 1000);" in timer and "clearInterval(elapsedTimer);" in timer
    assert "textContent = elapsedText(" in timer
    assert "announce(" not in timer and "refresh" not in timer
    assert ".check-start__elapsed" in dict(css_rules(STYLES))


# The tab icon


def test_the_tab_icon_is_the_mascot_drawn_in_the_page():
    from urllib.parse import unquote

    link = re.search(r'<link rel="icon" type="image/svg\+xml" href="(data:image/svg\+xml,[^"]+)">', INDEX)
    assert link, "index.html has no inline SVG favicon"
    assert link.group(1).isascii()
    svg = unquote(link.group(1).removeprefix("data:image/svg+xml,"))
    assert svg.startswith("<svg xmlns='http://www.w3.org/2000/svg'") and svg.endswith("</svg>")
    # The mascot's face, from mascotSvg(), and nothing loaded from anywhere.
    face = re.search(r'class="mascot__face" d="([^"]+)"', APP_JS).group(1)
    assert f"d='{face}'" in svg
    assert re.findall(r"https?://[^']+", svg) == ["http://www.w3.org/2000/svg"]
    assert "href" not in svg and "<image" not in svg
