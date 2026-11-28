"""palette entries must not depend on the terminal's ANSI table for structure

Many terminal palettes (e.g. Solarized) map "dark gray" (bright black) to the
background colour, so the new UI parts give every entry explicit high colours
and avoid "black"/"dark gray" in their 16 colour fallbacks.
"""

import pytest

from khal.ui import colors

NEW_UI = colors.NEW_UI_PREFIXES
INVISIBLE_16 = {"black", "dark gray"}


def _colour(spec: str) -> str:
    return (spec or "").split(",")[0].strip()


def _new_entries(palette):
    # entries without any colour are pure wrappers ("editor", "editor focus")
    # that let the surrounding colours through; they can't be invisible
    return [
        entry
        for entry in palette
        if entry[0].startswith(NEW_UI) and any(part for part in entry[1:] if part)
    ]


@pytest.mark.parametrize("name", list(colors.themes))
def test_new_ui_entries_have_high_colours(name):
    theme = colors.themes[name]
    palette = colors.expand_theme(theme) if colors.is_semantic_theme(theme) else theme
    entries = _new_entries(palette)
    assert len(entries) >= len(colors.NEW_UI_NAMES)
    for entry in entries:
        assert len(entry) == 6, entry
        fg_high = _colour(entry[4])
        assert fg_high.startswith(("#", "h", "g")), entry
        if entry[2]:  # a fill in 16 colours has a fill in high colours, too
            assert _colour(entry[5]).startswith(("#", "h", "g")), entry


@pytest.mark.parametrize("name", list(colors.themes))
def test_no_invisible_16_colour_fallbacks(name):
    theme = colors.themes[name]
    palette = colors.expand_theme(theme) if colors.is_semantic_theme(theme) else theme
    for entry in _new_entries(palette):
        fg16, bg16 = _colour(entry[1]), _colour(entry[2])
        if not bg16:  # on the terminal's background
            assert fg16 not in INVISIBLE_16, entry
        assert bg16 not in INVISIBLE_16, entry


def test_backdrop_twins_visible_in_16_colours():
    for entry in colors.add_backdrop_twins(list(colors.dark)):
        if entry[0].endswith(colors.BACKDROP_SUFFIX) or entry[0] == colors.BACKDROP_DEFAULT:
            assert _colour(entry[1]) not in INVISIBLE_16, entry
            assert _colour(entry[4]).startswith("#"), entry


def _wrapper_attributes() -> set[str]:
    """fixed attribute names khal's widgets are wrapped in (AttrMap, CAttrMap,
    set_attr_map); an attribute missing from a theme makes urwid fall back to
    the terminal's default colours, punching holes into painted backgrounds"""
    import ast
    import pathlib

    names: set[str] = set()
    for path in pathlib.Path("khal/ui").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            # attribute names chosen in a variable first: `attr = "monthname"`
            if (
                isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "attr" for t in node.targets)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                names.add(node.value.value)
                continue
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            fname = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if fname in ("AttrMap", "CAttrMap"):
                for arg in node.args[1:3]:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        names.add(arg.value)
            elif fname == "set_attr_map" and node.args and isinstance(node.args[0], ast.Dict):
                for value in node.args[0].values:
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        names.add(value.value)
    return names


@pytest.mark.parametrize("name", sorted(colors.themes))
def test_wrapper_attributes_defined(name):
    theme = colors.themes[name]
    if colors.is_semantic_theme(theme):
        theme = colors.expand_theme(theme)
    defined = {entry[0] for entry in theme}
    missing = sorted(_wrapper_attributes() - defined)
    assert not missing, f"theme {name} lacks {missing}"
