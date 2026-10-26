"""Screen tests: the walkthrough, the Scene wording, and the decorations, read
from app/static with no browser and no network.

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
