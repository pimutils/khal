"""ikhal's window: header clock, editing screen (width, split, right column views)"""

from __future__ import annotations

import datetime as dt

import pytest
from freezegun import freeze_time

from khal import ui

from .visual import NOW, Screen, make_collection, make_conf

try:  # contrib/khal_timegrid is a separate package, not installed in CI
    import khal_timegrid  # noqa: F401

    HAS_TIMEGRID = True
except ImportError:
    HAS_TIMEGRID = False
needs_timegrid = pytest.mark.skipif(not HAS_TIMEGRID, reason="needs the khal_timegrid plugin")


@pytest.fixture
def setup(tmp_path):
    count = iter(range(1000))

    def make(size=(100, 28), **view):
        directory = tmp_path / str(next(count))
        directory.mkdir()
        conf = make_conf(directory, **view)
        return Screen(conf, make_collection(conf), size=size)

    return make


def test_seconds_to_next_minute():
    assert ui.seconds_to_next_minute(dt.datetime(2026, 11, 26, 11, 20, 0)) == 60
    assert ui.seconds_to_next_minute(dt.datetime(2026, 11, 26, 11, 20, 59, 500000)) == 0.5
    assert ui.seconds_to_next_minute(dt.datetime(2026, 11, 26, 11, 20, 59, 999999)) >= 0.05


class FakeLoop:
    def __init__(self):
        self.alarms = []

    def set_alarm_in(self, seconds, callback, data=None):
        self.alarms.append((seconds, callback, data))


def test_header_clock_on_the_minute(setup):
    with freeze_time(NOW) as frozen:
        screen = setup()
        assert "11:20" in screen.text().splitlines()[0]
        assert "next: Lunch w/ Bob in 1h10m" in screen.text().splitlines()[0]
        loop = FakeLoop()
        frozen.tick(dt.timedelta(minutes=70, seconds=42))  # 12:30:42
        ui.redraw_today(loop, (screen.pane, {"last_today": NOW.date()}))
        header = screen.text().splitlines()[0]
        assert "12:30" in header
        # the next event is recomputed: Lunch has started, Choir is next
        assert "next: Choir in 6h29m" in header
        assert loop.alarms[0][0] == pytest.approx(18)  # on the next full minute
        assert loop.alarms[0][1] is ui.redraw_today


# -- the editing screen


def open_editor(screen: Screen, uid: str = "great"):
    from khal.ui.editing import EditingScreen

    screen.render()
    screen.column.edit(screen.event(uid))
    editing = screen.window._get_current_pane()
    assert isinstance(editing, EditingScreen)
    return editing


def test_editor_width():
    from khal.ui.editing import EDITOR_MAX, automatic_width, clamp_width, parse_width

    assert automatic_width(100) == 67
    assert automatic_width(200) == EDITOR_MAX  # the rest is for the events
    assert parse_width("", 100) is None
    assert parse_width("60%", 120) == 72
    assert parse_width("70", 120) == 70
    assert parse_width("junk", 120) is None
    assert clamp_width(200, 100) == 84  # the right column keeps 16 columns
    assert clamp_width(3, 100) == 16


@freeze_time(NOW)
def test_editor_width_configured(setup):
    screen = setup((120, 30), editor_width="50%")
    editing = open_editor(screen)
    screen.render()
    assert editing.editor_width(120) == 60
    assert screen.text().splitlines()[1].index("╮") == 59


@freeze_time(NOW)
def test_frame_title_and_status(setup):
    screen = setup()
    editing = open_editor(screen)
    lines = screen.text().splitlines()
    assert lines[1].startswith("╭─ Edit event ─")
    assert "11:20" in lines[0]  # the header keeps the clock
    screen.press("end", "!")
    assert "● unsaved ─╮" in screen.text().splitlines()[1]
    assert "unsaved" not in screen.text().splitlines()[-3]  # not in the action bar
    assert editing.editor.status_in_frame


@freeze_time(NOW)
def test_no_frame_keeps_status_in_action_bar(setup):
    screen = setup(frame="False")
    open_editor(screen)
    screen.press("end", "!")
    text = screen.text()
    assert "Edit event" not in text
    assert "Edit: Great Event" in text.splitlines()[0]
    assert "● unsaved" in text


@freeze_time(NOW)
def test_action_bar_key_hints(setup):
    screen = setup()
    open_editor(screen)
    bar = [line for line in screen.text().splitlines() if "Save" in line][0]
    assert bar.index("Save") < bar.index("Export") < bar.index("M-enter save  esc cancel")


@needs_timegrid
@freeze_time(NOW)
def test_focus_other_column_and_switch_view(setup):
    screen = setup()
    editing = open_editor(screen)
    assert not editing.right_focused
    screen.press("f6")
    assert editing.right_focused
    screen.press("w")  # the right column's own keys work there
    assert screen.pane._current_view == "timegrid"
    assert "Fr" in screen.text()
    screen.press("3")
    assert screen.column.dlistbox.days == 3
    screen.press("esc")  # back to the editor, the editor stays open
    assert not editing.right_focused
    assert screen.window._get_current_pane() is editing
    screen.press("meta w")  # next view without leaving the editor
    assert screen.pane._current_view == "list"
    assert not editing.right_focused


@freeze_time(NOW)
def test_right_column_follows_the_event(setup):
    screen = setup()
    open_editor(screen, "dentist")  # on Monday
    right = [line.split("││")[1] for line in screen.text().splitlines()[2:4]]
    assert "Mo 30 Nov" in right[0]


@freeze_time(NOW)
def test_resize_with_keys(setup):
    screen = setup()
    editing = open_editor(screen)
    assert editing.editor_width(100) == 67
    screen.press("meta <")
    assert editing.editor_width(100) == 63
    screen.press("meta >", "meta >")
    assert editing.editor_width(100) == 71
    # kept for the session
    screen.press("esc")
    editing = open_editor(screen, "dentist")
    assert editing.editor_width(100) == 71


@freeze_time(NOW)
def test_resize_with_mouse(setup):
    screen = setup()
    editing = open_editor(screen)
    screen.render()
    size = (100, 26)  # the body of the window
    assert editing.mouse_event(size, "mouse press", 1, 66, 5, True)
    editing.mouse_event(size, "mouse drag", 1, 50, 5, True)
    editing.mouse_event(size, "mouse release", 0, 50, 5, True)
    assert editing.editor_width(100) == 51
    # clicks elsewhere don't move it
    editing.mouse_event(size, "mouse press", 1, 20, 5, True)
    editing.mouse_event(size, "mouse release", 0, 20, 5, True)
    assert editing.editor_width(100) == 51


@freeze_time(NOW)
def test_narrow_fallback(setup):
    """an explicitly chosen layout falls back to compact while narrow"""
    screen = setup((120, 30), editor_layout="cards")
    editing = open_editor(screen)
    screen.render()
    assert editing.editor.layout.name == "cards"
    editing.set_editor_width(50)
    screen.render()
    assert editing.editor.layout.name == "compact"
    editing.set_editor_width(90)
    screen.render()
    assert editing.editor.layout.name == "cards"


@freeze_time(NOW)
def test_narrow_fallback_off(setup):
    screen = setup((120, 30), editor_layout="cards", editor_compact_below=0)
    editing = open_editor(screen)
    editing.set_editor_width(50)
    screen.render()
    assert editing.editor.layout.name == "cards"


@freeze_time(NOW)
def test_narrow_fallback_keeps_focus(setup):
    from khal.ui.editor_layout import focus_field, focused_field_id

    screen = setup((120, 30), editor_layout="sections")
    editing = open_editor(screen)
    screen.render()
    focus_field(editing.editor._w, "location")
    editing.set_editor_width(50)
    screen.render()
    assert editing.editor.layout.name == "compact"
    assert focused_field_id(editing.editor._w) == "location"


# -- viewing an event


def focus_lunch(screen: Screen) -> None:
    screen.press("tab", "down", "down")
    assert screen.column.focus_event.event.summary == "Lunch w/ Bob"


@freeze_time(NOW)
def test_view_inline_then_edit(setup):
    from khal.ui.editing import EditingScreen

    screen = setup()
    focus_lunch(screen)
    screen.press("enter")
    lines = screen.text().splitlines()
    row = next(i for i, line in enumerate(lines) if i and "Lunch w/ Bob" in line)
    assert "╭" in lines[row + 1]  # the card, right under the event
    assert "● home · Thu 26 Nov · 12:30–13:30 · 1h · today" in lines[row + 2]
    assert "enter edit  d delete  p duplicate  esc close" in screen.text()
    screen.press("enter")  # again: edit
    assert isinstance(screen.window._get_current_pane(), EditingScreen)


@freeze_time(NOW)
def test_view_inline_esc_closes(setup):
    screen = setup()
    focus_lunch(screen)
    before = screen.text()
    screen.press("enter", "esc")
    assert screen.text() == before
    assert screen.window._get_current_pane() is screen.pane


@freeze_time(NOW)
def test_view_inline_moving_away_closes(setup):
    screen = setup()
    focus_lunch(screen)
    screen.press("enter", "down")
    assert "esc close" not in screen.text()
    assert screen.column.focus_event.event.summary == "Choir"
    screen.press("enter")  # Choir's card, not the editor
    assert "esc close" in screen.text()
    assert screen.window._get_current_pane() is screen.pane


@freeze_time(NOW)
@pytest.mark.parametrize(
    ("key", "check"),
    [
        ("d", lambda screen: "✕ 12:30   Lunch w/ Bob" in screen.text()),
        ("e", lambda screen: "Export" in screen.text()),
        ("p", lambda screen: "Lunch w/ Bob Copy" in screen.text()),
    ],
)
def test_view_inline_keys(setup, key, check):
    screen = setup()
    focus_lunch(screen)
    screen.press("enter", key)
    assert "esc close" not in screen.text()
    assert check(screen)


@freeze_time(NOW)
def test_view_inline_delete_marks_event(setup):
    screen = setup()
    focus_lunch(screen)
    screen.press("enter", "d")
    line = next(line for line in screen.text().splitlines()[1:] if "Lunch w/ Bob" in line)
    assert "✕ 12:30   Lunch w/ Bob" in line
    assert line.rstrip(" │").endswith("deleted")


@freeze_time(NOW)
def test_view_column_on_wide_screens(setup):
    screen = setup((150, 28))
    focus_lunch(screen)
    screen.press("enter")
    lines = screen.text().splitlines()
    assert "╭─ Event " in lines[1]
    assert "Lunch w/ Bob" in lines[2].split("││")[-1]
    screen.press("down")  # follows the focused event
    assert "Choir" in screen.text().splitlines()[2].split("││")[-1]
    screen.press("esc")
    assert "╭─ Event " not in screen.text()


@freeze_time(NOW)
def test_view_column_then_edit(setup):
    from khal.ui.editing import EditingScreen

    screen = setup((150, 28))
    focus_lunch(screen)
    screen.press("enter", "enter")
    assert isinstance(screen.window._get_current_pane(), EditingScreen)


@freeze_time(NOW)
def test_view_bottom_split(setup):
    screen = setup(event_view_always_visible="True")
    focus_lunch(screen)
    text = screen.text()
    assert "enter edit  d delete" in text  # below the list, without enter
    assert "esc close" not in text


# -- the finder


@freeze_time(NOW)
def test_finder(setup):
    from khal.ui.finder import Finder

    screen = setup()
    screen.press("/")
    finder = screen.window._get_current_pane().top_w
    assert isinstance(finder, Finder)
    screen.press(*"din")
    text = screen.text()
    assert "› din" in text
    assert "▌▍28.11. Dinner at Anna's" in text
    assert "1/1" in text
    assert "● home · Sat 28 Nov · 20:00–23:00" in text  # the preview
    assert "where   Kreuzberg" in text
    assert "finder match focus" in screen.attributes()  # "Din" highlighted
    screen.press("backspace", "backspace", "backspace", *"e")
    screen.render()  # searches once per screen update
    assert finder.total > 3
    before = finder.selected
    screen.press("down")
    assert finder.selected is not before
    screen.press("up", "ctrl n", "ctrl p")
    assert finder.selected is before


@freeze_time(NOW)
def test_finder_enter_jumps(setup):
    from khal.ui.editing import EditingScreen

    screen = setup()
    screen.press("/", *"dentist", "enter")
    assert screen.window._get_current_pane() is screen.pane
    assert screen.column.focus_event.event.summary == "Dentist"
    assert screen.column.focus_date == NOW.date() + dt.timedelta(days=4)
    screen.press("enter")  # the card
    assert "esc close" in screen.text()
    screen.press("enter")  # the editor
    assert isinstance(screen.window._get_current_pane(), EditingScreen)


@freeze_time(NOW)
def test_finder_esc(setup):
    screen = setup()
    before = screen.text()
    screen.press("/", *"yoga", "esc")
    assert screen.window._get_current_pane() is screen.pane
    assert screen.text() == before


@freeze_time(NOW)
def test_finder_past_events_and_no_results(setup):
    screen = setup()
    screen.press("/", *"yoga")
    assert "24.11. Yoga" in screen.text()  # in the past
    screen.press(*"xyz")
    assert "0/0" in screen.text()


# -- events marked for deletion


def mark_three(screen: Screen) -> None:
    """Standup: this one, Lunch: the whole event, Choir: this & following"""
    screen.press("tab", "down", "d", "t", "d", "d", "f")


def event_rows(screen: Screen) -> dict[str, str]:
    rows = {}
    for line in screen.text().splitlines()[2:]:
        right = line.split("││")[-1] if "││" in line else line
        for title in ("Standup", "Lunch w/ Bob", "Choir"):
            if title in right and title not in rows:
                rows[title] = right
    return rows


@freeze_time(NOW)
def test_marked_events_in_the_list(setup):
    screen = setup()
    mark_three(screen)
    rows = event_rows(screen)
    assert "✕ 09:00   Standup" in rows["Standup"]
    assert rows["Standup"].rstrip(" │").endswith("this one")
    assert rows["Lunch w/ Bob"].rstrip(" │").endswith("deleted")
    assert rows["Choir"].rstrip(" │").endswith("this & following")
    assert "⟳" not in rows["Choir"]
    attributes = screen.attributes()
    assert {"agenda deleted", "agenda deleted mark", "agenda deleted scope"} <= attributes
    footer = screen.text().splitlines()[-1]
    assert footer.startswith(" ✕ 3 marked · deleted when you quit · d undo  U undo all")
    assert footer.endswith("khal 0.14")
    assert not screen.undefined_attributes()


@freeze_time(NOW)
def test_unmark_and_undo_all(setup):
    screen = setup()
    mark_three(screen)
    screen.press("up", "up", "d")  # Lunch: unmark again
    assert "✕ 2 marked" in screen.text().splitlines()[-1]
    assert event_rows(screen)["Lunch w/ Bob"].rstrip(" │").endswith("1h")
    screen.press("U")
    assert "marked" not in screen.text()
    assert "✕" not in screen.text()
    assert screen.pane.marked_count == 0
    assert "n new" in screen.text().splitlines()[-1]


@freeze_time(NOW)
@pytest.mark.parametrize("density", ["dense", "comfortable"])
def test_marked_events_in_other_densities(setup, density):
    screen = setup(density=density)
    screen.press("tab", "down", "d")  # Standup
    screen.press("a")  # all occurrences
    text = screen.text()
    assert "✕" in text
    assert "deleted" in text
    assert "agenda deleted" in screen.attributes()


@freeze_time(NOW)
def test_marked_event_card(setup):
    screen = setup()
    screen.press("tab", "down", "down", "d", "up", "enter")  # Lunch
    assert "✕ marked for deletion (deleted) · d undo" in screen.text()


@needs_timegrid
@freeze_time(NOW)
def test_marked_blocks_in_the_time_grid(setup):
    screen = setup((100, 40))
    mark_three(screen)
    screen.press("w", "3", "t")
    text = screen.text()
    assert "✕Lunch w/ Bob" in text
    assert "✕ deleted ╱╱" in text
    assert "✕ this & following" in text
    assert "timegrid home deleted hatch" in screen.attributes()
    assert not screen.undefined_attributes()


@needs_timegrid
@freeze_time(NOW)
def test_marked_blocks_without_256_colours(setup):
    screen = setup((100, 40))
    screen.screen.colors = 16
    mark_three(screen)
    screen.press("w", "3", "t")
    text = screen.text()
    assert "✕ deleted" in text
    assert "╱" not in text  # greyed instead of hatched
    assert {"timegrid deleted", "timegrid deleted mark"} <= screen.attributes()
    assert not screen.undefined_attributes()


# -- the log


@freeze_time(NOW)
def test_log_view(setup):

    from tests.ui.test_visual import fill_log

    screen = setup((100, 28))
    fill_log(screen)
    lines = screen.text().splitlines()
    top = next(i for i, line in enumerate(lines) if "╭─ Log " in line)
    assert "esc close ─╮" in lines[top]
    body = "\n".join(lines[top:])
    assert "11:02:07 debug  loaded 4 calendars" in body
    assert "11:08:07 warn   Calendar `birthdays` is read-only." in body
    assert "11:11:07 error  Could not save" in body
    # wrapped with a hanging indent under the message
    error = next(i for i, line in enumerate(lines) if "11:11:07 error" in line)
    column = lines[error].index("Could")
    assert lines[error + 1][column - 1] == " "
    assert lines[error + 1][column] != " "
    assert {"log time", "log error", "log warning", "log info", "log debug"} <= screen.attributes()
    assert not screen.undefined_attributes()
    # the newest entry is in view, esc closes
    assert "Saved “Great Event” to home" in screen.text()
    screen.press("esc")
    assert screen.window._get_current_pane() is screen.pane


@freeze_time(NOW)
def test_log_scrolls_to_the_newest(setup):
    from khal.ui.floating import LogEntry

    screen = setup((80, 16))
    for number in range(40):
        screen.window.log(LogEntry(NOW, 20, f"entry number {number}"))
    screen.press("L")
    text = screen.text()
    assert "entry number 39" in text
    assert "entry number 0 " not in text
    screen.press("home")
    assert "entry number 0" in screen.text()
    assert "entry number 39" not in screen.text()
    screen.press("end")
    assert "entry number 39" in screen.text()
    screen.press("page up")
    assert "entry number 39" not in screen.text()


@freeze_time(NOW)
def test_log_empty_and_plain_text(setup):
    screen = setup()
    screen.press("L")
    assert "nothing logged yet" in screen.text()
    screen.press("esc")
    screen.window.log("a plain message")  # the old API: a text
    screen.press("L")
    assert "11:20:00 info   a plain message" in screen.text()


@freeze_time(NOW)
def test_log_gets_records_with_time_and_level(setup):
    """start_pane's handler: record time and level, message with its args"""
    import logging

    from khal.ui.floating import LogEntry

    screen = setup()
    record = logging.LogRecord("khal", logging.WARNING, "", 0, "%s is read-only", ("work",), None)
    entry = LogEntry(dt.datetime.fromtimestamp(record.created), record.levelno, record.getMessage())
    screen.window.log(entry)
    screen.press("L")
    assert "warn   work is read-only" in screen.text()


# -- the time grid, round 2


@pytest.fixture
def busy(tmp_path):
    def make(size=(100, 28), **view):
        conf = make_conf(tmp_path, **view)
        return Screen(conf, make_collection(conf, busy=True), size=size)

    return make


def grid_lines(screen: Screen) -> list[str]:
    """the rows inside the right column's frame (header row first)"""
    return [line.split("││")[-1] for line in screen.text().splitlines()[2:-2]]


def row_of(lines: list[str], label: str) -> str:
    return next(line for line in lines if line.startswith(label))


@needs_timegrid
@freeze_time(NOW)
def test_grid_auto_is_the_work_week(busy):
    screen = busy()
    screen.press("tab", "w", "0")
    lines = screen.text().splitlines()
    assert "╭─ Week 48 · Mon–Fri ─" in lines[1]
    assert "timegrid" not in lines[0] or "next:" not in lines[0]  # (mode message)
    header = grid_lines(screen)[0].rstrip("│")
    assert header.split() == ["Mo", "23", "Tu", "24", "We", "25", "Th", "26", "Fr", "27"]
    rows = grid_lines(screen)
    assert rows[3].startswith("07:00")  # starts at day_start, two rows per hour


@needs_timegrid
@freeze_time(NOW)
def test_grid_badge_counts_hidden_events(busy):
    screen = busy()
    screen.press("tab", "w", "0")
    rows = grid_lines(screen)
    counts = [row.rstrip(" │")[-2:] for row in rows if "▌+" in row]
    assert counts == ["+2", "+4", "+4", "+4", "+2", "+1", "+1", "+1", "+1"]


@needs_timegrid
@freeze_time(NOW)
def test_grid_enter_on_badge_lists_the_events(busy):
    screen = busy()
    screen.press("tab", "w", "0", "t", "right", "up", "up")  # Friday 10:00
    grid = screen.column.dlistbox
    assert screen.column.focus_event.event.summary == "Great Event"
    assert not grid.handles_view_key()
    screen.press("right")  # the badge
    assert grid.handles_view_key()
    hidden = screen.column.focus_event.event.summary
    screen.press("enter")
    text = screen.text()
    assert "Fr 27 · 10:00" in text
    assert "5 at once" in text
    assert "▍ 09:30–11:30  Interview" in text
    assert "esc close" not in text  # the event itself is not shown
    screen.press("enter")  # the focused one is selected in the list
    assert screen.column.focus_event.event.summary == hidden
    assert "5 at once" not in screen.text()


@freeze_time(NOW)
def test_grid_badge_list_esc(busy):
    screen = busy()
    screen.press("tab", "w", "0", "t", "right", "up", "up", "right", "enter", "esc")
    assert "5 at once" not in screen.text()
    assert screen.window._get_current_pane() is screen.pane


@needs_timegrid
@freeze_time(NOW)
def test_grid_day_view_shows_all_lanes(busy):
    screen = busy()
    screen.press("tab", "w", "1", "t", "right")
    rows = grid_lines(screen)
    assert "▌+" not in "\n".join(rows)
    nine = row_of(rows, "09:00")
    # titles first, wrapped on whole words, then the start time
    assert "▌Anna: 1:1" in nine
    assert "▌Team sync" in nine
    assert "▌with Max" in rows[rows.index(nine) + 1]


@needs_timegrid
@freeze_time(NOW)
def test_grid_no_hour_lines_inside_groups(busy):
    screen = busy()
    screen.press("tab", "w", "1", "t", "right")
    rows = grid_lines(screen)
    for label in ("09:00", "10:00", "11:00", "12:00"):
        assert "┈" not in row_of(rows, label)
    assert "┈" in row_of(rows, "07:00")


@needs_timegrid
@freeze_time(NOW)
def test_grid_now_line_only_in_today(setup):
    screen = setup((140, 28))
    screen.press("tab", "w", "0")
    now = next(line for line in grid_lines(screen) if line.startswith("11:20"))
    # gutter, then dotted lines (Mon–Wed), the now line in Thursday only
    assert now.count("━") < 25
    assert "┈" in now.split("━")[-1]


@needs_timegrid
@freeze_time(NOW)
def test_grid_all_day_bar_across_days(setup):
    screen = setup((140, 28))
    screen.press("tab", "w", "0")
    allday = grid_lines(screen)[1]
    assert allday.count("Hiking trip") == 1  # one bar over Sat and Sun
    assert "▌Hiking trip" in allday


# -- moving through time


def test_shift_months():
    from khal.ui.navigation import shift_months

    assert shift_months(dt.date(2026, 11, 26), 1) == dt.date(2026, 12, 26)
    assert shift_months(dt.date(2026, 12, 26), 1) == dt.date(2027, 1, 26)
    assert shift_months(dt.date(2027, 1, 31), 1) == dt.date(2027, 2, 28)
    assert shift_months(dt.date(2028, 1, 31), 1) == dt.date(2028, 2, 29)  # leap year
    assert shift_months(dt.date(2028, 2, 29), 12) == dt.date(2029, 2, 28)
    assert shift_months(dt.date(2028, 2, 29), -48) == dt.date(2024, 2, 29)
    assert shift_months(dt.date(2026, 3, 31), -1) == dt.date(2026, 2, 28)
    assert shift_months(dt.date(2026, 1, 15), -1) == dt.date(2025, 12, 15)


@freeze_time(NOW)
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2027-03-01", dt.date(2027, 3, 1)),  # ISO
        ("Mon 2027-03-01", dt.date(2027, 3, 1)),  # longdateformat
        ("05.12.", dt.date(2026, 12, 5)),  # dateformat (short)
        ("friday", dt.date(2026, 11, 27)),
        ("Mon", dt.date(2026, 11, 30)),
        ("today", dt.date(2026, 11, 26)),
        ("tomorrow", dt.date(2026, 11, 27)),
        ("yesterday", dt.date(2026, 11, 25)),
        ("+3d", dt.date(2026, 11, 29)),
        ("-2w", dt.date(2026, 11, 12)),
        ("+1m", dt.date(2026, 12, 26)),
        ("-1y", dt.date(2025, 11, 26)),
        ("+ 10 d", dt.date(2026, 12, 6)),
        ("bogus", None),
        ("", None),
        ("friday bogus", None),
    ],
)
def test_parse_goto(setup, text, expected):
    from khal.ui.navigation import parse_goto

    screen = setup()
    assert parse_goto(text, screen.conf["locale"]) == expected


@freeze_time(NOW)
@pytest.mark.parametrize("where", ["calendar", "list", pytest.param("grid", marks=needs_timegrid)])
def test_month_and_year_keys(setup, where):
    screen = setup()
    keys = {"calendar": (), "list": ("tab",), "grid": ("tab", "w")}[where]
    screen.press(*keys)
    screen.press("}")
    assert screen.pane.focus_date == dt.date(2026, 12, 26)
    assert "→ December 2026" in screen.text().splitlines()[0]
    screen.press("]", "]")
    assert screen.pane.focus_date == dt.date(2028, 12, 26)
    screen.press("{", "[")
    assert screen.pane.focus_date == dt.date(2027, 11, 26)
    assert screen.pane.calendar.base_widget.focus_date == dt.date(2027, 11, 26)
    if where == "grid":
        assert screen.column.dlistbox.pane_title == "Fri 26 Nov"  # the shown day moved
    else:
        assert screen.column.focus_date == dt.date(2027, 11, 26)


@freeze_time(NOW)
def test_goto_date(setup):
    screen = setup()
    screen.press("tab", "g")
    assert screen.text().splitlines()[-1].startswith(" go to")
    screen.press(*"bogus", "enter")
    assert "✗ not a date" in screen.text().splitlines()[-1]  # stays open
    for _ in "bogus":
        screen.press("backspace")
    screen.press(*"+1m", "enter")
    assert screen.pane.focus_date == dt.date(2026, 12, 26)
    assert "→ December 2026" in screen.text().splitlines()[0]
    assert "go to" not in screen.text().splitlines()[-1]
    screen.press("g", *"2027-03-01", "enter")
    assert screen.pane.focus_date == dt.date(2027, 3, 1)
    assert "→ March 2027" in screen.text().splitlines()[0]


@freeze_time(NOW)
def test_goto_date_esc(setup):
    screen = setup()
    screen.press("tab", "g", *"+3d", "esc")
    assert screen.pane.focus_date == NOW.date()
    assert "n new" in screen.text().splitlines()[-1]
    assert screen.window._get_current_pane() is screen.pane


@needs_timegrid
def test_navigation_keys_dont_collide():
    """the new defaults are not bound to anything else (incl. the time grid)"""
    from khal_timegrid import COMMANDS

    from khal.settings import get_config

    conf = get_config("tests/configs/small.conf", _get_color_from_vdir=lambda p: None)
    keys = conf["keybindings"]
    new = {"next_month", "prev_month", "next_year", "prev_year", "goto_date"}
    taken = {k for name, bound in keys.items() if name not in new for k in bound}
    taken |= {k for command in COMMANDS for k in command.default_keys}
    for name in new:
        assert not set(keys[name]) & taken, name


# -- header line and frame titles


@freeze_time(NOW)
def test_header_line_date_and_next_event(setup):
    """the left part of the header, independent of which views are installed"""
    header = setup().text().splitlines()[0]
    assert header.startswith(
        " Thursday, 26 November 2026 · week 48 · 11:20  next: Lunch w/ Bob in 1h10m"
    )


@needs_timegrid
@freeze_time(NOW)
def test_header_line_like_the_mockup(setup):
    screen = setup()
    header = screen.text().splitlines()[0]
    assert header == (
        " Thursday, 26 November 2026 · week 48 · 11:20  next: Lunch w/ Bob in 1h10m"
        "        [list]  day  week"
    )
    attributes = screen.attributes()
    assert {"header date", "header time", "header dim", "header tab active"} <= attributes


@freeze_time(NOW)
def test_header_line_narrow(setup):
    screen = setup((80, 24))
    assert screen.text().splitlines()[0] == (
        " Thursday, 26 November 2026 · week 48 · 11:20  next: Lunch w/ Bob in 1h10m"
    )
    screen = setup((50, 24))
    assert screen.text().splitlines()[0] == " Thu 26 Nov 11:20  next: Lunch w/ Bob in 1h10m"


@needs_timegrid
@freeze_time(NOW)
def test_header_tabs_follow_the_view(setup):
    screen = setup()
    screen.press("tab", "w", "1")
    assert screen.text().splitlines()[0].endswith("list  [day]  week")
    screen.press("7")
    assert screen.text().splitlines()[0].endswith("list  day  [week]")
    screen = setup(header_view_tabs="False")
    assert "[list]" not in screen.text().splitlines()[0]


@freeze_time(NOW)
def test_frame_titles(setup):
    screen = setup()
    top = screen.text().splitlines()[1]
    assert top.startswith("╭─ November ─")
    assert "╭─ Agenda ─" in top
    assert top.endswith(" 5 days ─╮")
    assert "frame title" in screen.attributes()
    screen.press("}")  # the month column follows
    assert screen.text().splitlines()[1].startswith("╭─ December ─")


@freeze_time(NOW)
def test_no_frame_titles_without_frames(setup):
    screen = setup(frame="False")
    text = screen.text()
    assert "November ─" not in text
    assert "Agenda" not in text
