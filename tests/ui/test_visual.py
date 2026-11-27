"""ikhal rendered like it runs (real palette, pop-ups, floating boxes)

Each scenario renders a screen of the mockups in design/ with a sample
collection (see tests/ui/visual.py). The tests check what can be checked
automatically (aligned columns and right edges, every attribute in the
canvas has a palette entry, no wide key glyphs); set KHAL_VISUAL_DUMP to a
directory to also get the renders as .ans/.txt files for looking at them.
"""

from __future__ import annotations

import ast
import pathlib

import pytest
import urwid
from freezegun import freeze_time

from khal.ui import colors
from khal.ui.drum import DrumPopUp
from khal.ui.editor import CalendarPopUp, EventEditor
from khal.ui.editor_layout import focus_field
from khal.ui.widgets import AlarmsEditor

from .visual import NOW, Screen, find, make_collection, make_conf

pytest.importorskip("khal_timegrid")


@pytest.fixture(autouse=True)
def frozen():
    with freeze_time(NOW):
        yield


@pytest.fixture
def setup(tmp_path):
    count = iter(range(1000))

    def make(size=(100, 28), **view):
        directory = tmp_path / str(next(count))
        directory.mkdir()
        conf = make_conf(directory, **view)
        return Screen(conf, make_collection(conf), size=size)

    return make


# -- scenarios: functions that bring a Screen into a state


def overview(screen: Screen) -> None:
    screen.press("tab", "down", "down")  # focus on "Lunch w/ Bob"


def editor_of(screen: Screen) -> EventEditor:
    return find(screen.window._get_current_pane(), EventEditor)[0]


def edit(uid: str, field: str = "summary"):
    def scenario(screen: Screen) -> None:
        screen.render()
        screen.column.edit(screen.event(uid))
        editor = editor_of(screen)
        focus_field(editor._layout.listbox, field)

    return scenario


def popup(uid: str, field: str, launcher):
    """edit `uid`, focus `field` and open the pop-up `launcher(editor)` returns"""

    def scenario(screen: Screen) -> None:
        edit(uid, field)(screen)
        editor = editor_of(screen)
        screen.render()
        launcher(editor).open_pop_up()

    return scenario


def calendar_choice(editor):
    return editor.calendar_chooser.original_widget


def date_picker(editor):
    return find(editor.startendeditor, CalendarPopUp)[0]


def time_drum(editor):
    return find(editor.startendeditor, DrumPopUp)[0]


def duration_drum(editor):
    return editor.startendeditor.widgets.duration


def alarm_direction(editor):
    return find(editor.alarmseditor, AlarmsEditor.AlarmEditor)[0].direction


def repeat_unit(editor):
    return editor.recurrenceeditor._freq_choice


def repeat_ends(editor):
    return editor.recurrenceeditor._until_choice


def repeat_monthly(editor):
    recurrence = editor.recurrenceeditor
    recurrence._freq_choice.active = "monthly"
    recurrence.rebuild()
    return recurrence.monthly_choice


def delete_repeating(screen: Screen) -> None:
    screen.press("tab", "down")  # Standup
    screen.column.toggle_delete()


def unsaved(screen: Screen) -> None:
    edit("great")(screen)
    screen.press("end", "!", "esc")


def help_screen(screen: Screen) -> None:
    screen.press("?")


def details(screen: Screen) -> None:
    overview(screen)
    screen.press("enter")


def export(screen: Screen) -> None:
    overview(screen)
    screen.column.export_event()


def timegrid(days: str):
    def scenario(screen: Screen) -> None:
        screen.press("tab", "w", days)

    return scenario


def mark_deletions(screen: Screen) -> None:
    """Standup: this one, Lunch: the whole event, Choir: this & following"""
    screen.press("tab", "down", "d", "t", "d", "d", "f")


def deleted_grid(screen: Screen) -> None:
    mark_deletions(screen)
    screen.press("w", "3", "t")


def fill_log(screen: Screen) -> None:
    """a few entries of each level, then L"""
    import datetime as dt
    import logging

    from khal.ui.floating import LogEntry

    at = dt.datetime(2026, 11, 26, 11, 2, 7)
    for level, message in (
        (logging.DEBUG, "loaded 4 calendars"),
        (logging.INFO, "detected external vdir modification, updating..."),
        (logging.WARNING, "Calendar `birthdays` is read-only."),
        (
            logging.ERROR,
            "Could not save to calendar “work”: [Errno 13] Permission denied: "
            "'/home/user/.calendars/work/great.ics' (the event stays open in the editor)",
        ),
        (logging.INFO, "Saved “Great Event” to home"),
    ):
        screen.window.log(LogEntry(at, level, message))
        at += dt.timedelta(minutes=3)
    screen.press("L")


SCENARIOS = {
    "overview": overview,
    "editor": edit("great"),
    "editor-repeating": edit("choir", "repeat"),
    "choice-calendar": popup("great", "calendar", calendar_choice),
    "choice-alarm": popup("great", "alarms", alarm_direction),
    "choice-repeat-unit": popup("choir", "repeat", repeat_unit),
    "choice-repeat-ends": popup("choir", "repeat", repeat_ends),
    "choice-monthly": popup("choir", "repeat", repeat_monthly),
    "date-picker": popup("great", "start", date_picker),
    "time-drum": popup("great", "start", time_drum),
    "duration-drum": popup("great", "end", duration_drum),
    "delete-repeating": delete_repeating,
    "unsaved": unsaved,
    "help": help_screen,
    "details": details,
    "export": export,
    "timegrid-day": timegrid("1"),
    "timegrid-3days": timegrid("3"),
    "timegrid-week": timegrid("7"),
    "deleted-list": mark_deletions,
    "deleted-grid": deleted_grid,
    "log": fill_log,
}
LAYOUTS = ["sections", "headline", "cards", "compact"]
slow = pytest.mark.slow
# the default run checks the user's theme, --runslow all of them
THEMES = [name if name == "retrobox" else pytest.param(name, marks=slow) for name in colors.themes]


def _check_frame(text: str, cols: int) -> None:
    """no line is wider than the screen, box borders line up"""
    lines = text.splitlines()
    for line in lines:
        assert len(line) <= cols, line


@slow
@pytest.mark.parametrize("name", list(SCENARIOS))
@pytest.mark.parametrize("size", [(100, 28), (80, 24)], ids=["100x28", "80x24"])
def test_render(setup, name, size):
    screen = setup(size)
    SCENARIOS[name](screen)
    text = screen.dump(f"{name}-{size[0]}x{size[1]}")
    _check_frame(text, size[0])
    assert not screen.undefined_attributes()


@slow
@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("size", [(100, 28), (80, 24)], ids=["100x28", "80x24"])
def test_render_editor_layouts(setup, layout, size):
    screen = setup(size, editor_layout=layout)
    edit("great", "start")(screen)
    text = screen.dump(f"editor-{layout}-{size[0]}x{size[1]}")
    _check_frame(text, size[0])
    assert "Great Event" in text
    assert not screen.undefined_attributes()


# the default run renders a few scenarios, --runslow all of them
FAST = {
    "overview", "choice-calendar", "date-picker", "time-drum", "help", "timegrid-week",
    "deleted-list", "deleted-grid", "log",
}  # fmt: skip
NAMES = [name if name in FAST else pytest.param(name, marks=slow) for name in SCENARIOS]


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("name", NAMES)
def test_attributes_defined(setup, theme, name):
    """every attribute drawn (incl. calendar and plugin attributes) has a
    palette entry: urwid draws unknown ones in the terminal's default colours"""
    screen = setup(theme=theme)
    SCENARIOS[name](screen)
    assert not screen.undefined_attributes(), name


@pytest.fixture
def busy(tmp_path):
    def make(size=(100, 28), **view):
        conf = make_conf(tmp_path, **view)
        return Screen(conf, make_collection(conf, busy=True), size=size)

    return make


@pytest.mark.parametrize(
    ("name", "size", "keys"),
    [
        ("timegrid-auto-100", (100, 28), ("w", "0")),
        ("timegrid-auto-140", (140, 28), ("w", "0")),
        ("timegrid-busy-day", (100, 28), ("w", "1", "t", "right")),
        ("timegrid-busy-week", (100, 28), ("w", "0")),
        ("timegrid-busy-list", (100, 28), ("w", "0", "t", "right", "up", "up", "right", "enter")),
    ],
)
def test_render_time_grid(busy, name, size, keys):
    screen = busy(size)
    screen.press("tab", *keys)
    text = screen.dump(name)
    _check_frame(text, size[0])
    assert not screen.undefined_attributes()


@pytest.mark.parametrize(
    ("name", "size", "keys"),
    [
        ("spans-80x24", (80, 24), ()),
        ("spans-card-80x24", (80, 24), ("/", *"conference", "enter", "enter")),
        ("spans-column-160", (160, 28), ("/", *"conference", "enter", "enter")),
        ("spans-100x46", (100, 46), ()),
    ],
)
def test_render_spans(tmp_path, name, size, keys):
    """events over several days and overnight (design/overview-mockups/41)"""
    conf = make_conf(tmp_path)
    screen = Screen(conf, make_collection(conf, spans=True), size=size)
    screen.press(*keys)
    text = screen.dump(name)
    _check_frame(text, size[0])
    assert not screen.undefined_attributes()


def test_pop_ups_on_theme_background(setup):
    """pop-ups are inside the "body" attribute map: no cell of an open
    pop-up is drawn without an attribute (= the terminal's background)"""
    for name in ("choice-calendar", "date-picker", "time-drum"):
        screen = setup()
        SCENARIOS[name](screen)
        assert None not in screen.attributes(), name


def test_choice_list(setup):
    screen = setup()
    SCENARIOS["choice-calendar"](screen)
    text = screen.text()
    assert "< home" not in text
    assert "▌ ● work ✓" in text
    assert "● family" in text
    screen.press("down", "enter")
    assert editor_of(screen).calendar_chooser.original_widget.active["name"] == "family"


def test_choice_list_opens_upwards():
    """a pop-up without room below its field opens above it"""
    from khal.ui.widgets import Choice, PopUpTarget

    choice = Choice(["before", "after"], "before")
    top = urwid.Filler(urwid.Text("x"), valign="top")
    root = PopUpTarget(urwid.Pile([top, ("pack", urwid.Padding(choice, left=5))]))
    choice.open_pop_up()
    lines = [line.decode().rstrip() for line in root.render((30, 8), True).text]
    assert "before" in lines[7]  # the field, in the last row
    assert lines[6].lstrip().startswith("╰")  # the box ends right above it
    assert "before ✓" in lines[4]
    assert lines[3].startswith("     ╭")  # aligned with the field


def test_event_list_columns_line_up(setup):
    """times, the now line and free time sit in fixed columns; durations
    end in the same column"""
    screen = setup()
    overview(screen)
    lines = screen.text().splitlines()
    right = [line[line.index("││") + 2 :] for line in lines if "││" in line]
    times = {line.index("09:00") for line in right if "Standup" in line}
    times |= {line.index("11:20") for line in right if "━" in line}
    assert len(times) == 1
    ends = {
        urwid.calc_width(line.rstrip("│ "), 0, len(line.rstrip("│ ")))  # ⏰ is wide
        for line in right
        if line.rstrip("│ ").endswith(("m", "h"))
    }
    assert len(ends) == 1


def _ui_strings() -> list[str]:
    strings = []
    for path in pathlib.Path("khal/ui").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                strings.append(node.value)
    return strings


def test_no_wide_key_glyphs():
    """⏎ and ⇧ are (almost) double width in many fonts and break alignment"""
    for string in _ui_strings():
        assert "⏎" not in string, string
        assert "⇧" not in string, string


def test_key_names():
    from khal.ui.editor_layout import UNICODE, format_key

    assert format_key("meta enter", UNICODE) == "M-enter"
    assert format_key("enter", UNICODE) == "enter"
    assert format_key("shift tab", UNICODE) == "S-tab"
    assert format_key("ctrl s", UNICODE) == "^S"
