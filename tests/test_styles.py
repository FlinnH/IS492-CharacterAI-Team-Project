"""Style tests: the color pairs the screens use keep WCAG contrast in both
themes. Text needs 4.5:1, and the icon on the top bar's tile 3:1.

The colors come from the --md-sys-color-* tokens in styles.css, so a changed
token is checked here too."""

import re

import pytest

from conftest import APP_DIR

STYLES = (APP_DIR / "static" / "styles.css").read_text(encoding="utf-8")

# The soft red behind broken replies and turn squares in the dark theme
DARK_BREAK_TINT = "color-mix(in srgb, var(--md-sys-color-error) 20%, var(--md-sys-color-surface-container-lowest))"


def theme_colors(selector):
    """The --md-sys-color-* hex values in the block that starts with selector, by role."""
    block = re.search(re.escape(selector) + r"\s*\{(.*?)\}", STYLES, re.S)
    assert block, f"styles.css has no {selector} block"
    return {role: rgb(value) for role, value in re.findall(r"--md-sys-color-([a-z-]+):\s*(#[0-9a-fA-F]{6});", block.group(1))}


def rgb(hex_color):
    """A #rrggbb color as three sRGB channels from 0 to 1."""
    return tuple(int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))


def mix(first, second, share):
    """color-mix(in srgb, first share, second): each sRGB channel mixed on its own, as browsers do."""
    return tuple(share * a + (1 - share) * b for a, b in zip(first, second))


def luminance(color):
    """WCAG relative luminance."""
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in color]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(text, background):
    """WCAG contrast ratio, from 1 to 21."""
    lighter, darker = sorted([luminance(text), luminance(background)], reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


THEMES = {
    "light": theme_colors(":root"),
    "dark": theme_colors(':root[data-theme="dark"]'),
}


def test_both_themes_define_the_same_color_roles():
    assert len(THEMES["light"]) > 40
    assert THEMES["light"].keys() == THEMES["dark"].keys()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize(
    ("text", "background"),
    [
        ("on-surface", "surface"),
        ("on-surface-variant", "surface"),
        ("on-surface-variant", "surface-container-high"),
        ("on-secondary-container", "secondary-container"),
        ("on-surface", "surface-container-highest"),
        ("on-primary-container", "inverse-primary"),
    ],
    ids=["body-text", "secondary-text", "static-chips", "alex-lines", "harry-replies", "selected-text"],
)
def test_text_reaches_4_5_to_1(theme, text, background):
    colors = THEMES[theme]
    assert contrast(colors[text], colors[background]) >= 4.5


def test_broken_turns_and_replies_stay_readable():
    light = THEMES["light"]
    assert contrast(light["on-error-container"], light["error-container"]) >= 4.5

    # In the dark theme a break is a soft tint, not a solid dark red
    assert DARK_BREAK_TINT in STYLES
    dark = THEMES["dark"]
    tint = mix(dark["error"], dark["surface-container-lowest"], 0.2)
    assert contrast(dark["error"], tint) >= 4.5
    assert contrast(dark["on-surface"], tint) >= 4.5


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_top_bar_icon_reaches_3_to_1_on_its_tile(theme):
    colors = THEMES[theme]
    assert contrast(colors["on-primary-container"], colors["primary-container"]) >= 3
