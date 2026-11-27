"""built-in and semantic colour themes"""

import pytest
import urwid

from khal.ui import colors

SEMANTIC_KEYS = {"bg", "txt", "lbl", "dim", "acc", "row", "pop", "btn", "fld2", "errbg"}


@pytest.mark.parametrize("name", list(colors.SEMANTIC_THEMES))
@pytest.mark.parametrize("mode", ["rgb", "256colors"])
def test_semantic_themes_expand(name, mode):
    theme = colors.themes[name]
    assert colors.is_semantic_theme(theme)
    palette = colors.expand_theme(theme, mode)
    names = [entry[0] for entry in palette]
    # every attribute of the reference theme, once
    assert set(names) >= {entry[0] for entry in colors.dark}
    assert len(names) == len(set(names))
    for entry in palette:
        assert len(entry) == 6
        if mode == "rgb":
            assert entry[4].split(",")[0].startswith("#")
        else:
            assert entry[4].split(",")[0].startswith("h")
    # valid urwid palette, also with the backdrop twins
    screen = urwid.display.raw.Screen()
    screen.register_palette(colors.add_backdrop_twins(palette, colors.theme_is_dark(theme)))


def test_retrobox_matches_vim():
    """the 256 colour fallback of retrobox is what vim's retrobox uses"""
    body = {e[0]: e for e in colors.expand_theme(colors.themes["retrobox"], "256colors")}
    assert body["body"][4] == "h187"  # Normal ctermfg=187
    assert body["body"][5] == "h234"  # Normal ctermbg=234
    assert body["editor focus row"][5] == "h236"  # CursorLine ctermbg=236


def test_minimal_plugin_theme():
    theme = {
        "bg": "#101418", "txt": "#e0e4ea", "lbl": "#98a2b0", "dim": "#5b6470", "acc": "#e8a33d",
        "row": "#1c232b", "pop": "#242d37", "btn": "#242d37", "fld2": "#2e3945", "errbg": "#4a2124",
        "grn": "#8fc78a", "blu": "#7aa7e8", "red": "#ef6f6c", "yel": "#e8c766", "pur": "#c39be6",
    }  # fmt: skip
    palette = {e[0]: e for e in colors.expand_theme(theme)}
    assert palette["editor key"][4] == "#e8a33d,bold"
    assert palette["editor key"][1] in ("yellow,bold", "brown,bold", "light red,bold")
    assert palette["body"][2] == ""  # 16 colours keep the terminal background
    assert colors.theme_is_dark(theme)


def test_nearest_colours():
    assert colors.nearest_basic("#ff0000") == "light red"
    assert colors.nearest_256("#1c1c1c") == "h234"
    assert colors.blend("#000000", "#ffffff", 0.5) == "#808080"


class _Stop(Exception):
    pass


@pytest.mark.parametrize("theme", ["dark", "retrobox", "plugin"])
def test_start_pane_palette(coll_vdirs, monkeypatch, theme):
    """start_pane builds a valid palette (incl. calendar colours and twins)"""
    from khal import plugins, ui
    from khal.settings import get_config

    conf = get_config(
        "tests/configs/small.conf",
        _get_color_from_vdir=lambda path: None,
        _get_vdir_type=lambda path: "calendar",
    )
    conf["view"]["theme"] = theme
    monkeypatch.setitem(plugins.THEMES, "plugin", dict(colors.SEMANTIC_THEMES["ink"]))
    captured = {}

    def fake_loop(widget, palette, **kwargs):
        captured["palette"] = palette
        raise _Stop

    monkeypatch.setattr(urwid, "MainLoop", fake_loop)
    collection, _ = coll_vdirs
    pane = ui.ClassicView(collection, conf)
    with pytest.raises(_Stop):
        ui.start_pane(pane, pane.cleanup, program_info="khal test")
    names = {entry[0] for entry in captured["palette"]}
    assert "editor field grey" in names
    assert any(name.startswith("calendar ") and name.endswith(" grey") for name in names)
    urwid.display.raw.Screen().register_palette(captured["palette"])


@pytest.mark.parametrize("marking", ["calendar", "dot", "heat", "none"])
def test_day_marking(coll_vdirs, marking):
    import datetime as dt

    from khal import ui
    from khal.settings import get_config
    from khal.ui.calendarwidget import DayStyle
    from tests.utils import cal1

    conf = get_config(
        "tests/configs/small.conf",
        _get_color_from_vdir=lambda path: None,
        _get_vdir_type=lambda path: "calendar",
    )
    conf["view"]["day_marking"] = marking
    collection, _ = coll_vdirs
    day = dt.date.today() + dt.timedelta(days=2)
    for hour in (8, 10, 12, 14):
        event = collection.create_event_from_dict(
            {
                "dtstart": dt.datetime.combine(day, dt.time(hour)),
                "dtend": dt.datetime.combine(day, dt.time(hour, 30)),
                "summary": f"event {hour}",
                "timezone": conf["locale"]["default_timezone"],
                "allday": False,
                "alarms": "",
            },
            calendar_name=cal1,
        )
        collection.insert(event)
    pane = ui.ClassicView(collection, conf)
    style = pane.day_styles(day, False)
    empty = pane.day_styles(day + dt.timedelta(days=1), False)
    assert pane.day_styles(dt.date.today(), False) == "today"
    if marking == "dot":
        assert style == DayStyle(None, "•", f"calendar {cal1}")
        assert empty is None
        rendered = b"\n".join(pane.calendar.render((28, 10), False).text).decode()
        assert "•" in rendered
        assert all(len(line) <= 28 for line in rendered.splitlines())
    elif marking == "heat":
        assert style == "day heat 3"
        assert empty is None
    elif marking == "none":
        assert style is None
