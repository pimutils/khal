"""tests for the layouts of ikhal's event editor (khal.ui.editor_layout)"""

import datetime as dt

import pytest

from khal import ui
from khal.settings import get_config
from khal.ui.editor import EventEditor
from khal.ui.editor_layout import (
    FIELDS,
    LAYOUTS,
    focus_field,
    focused_field_id,
)
from tests.utils import BERLIN, _get_text, cal1

LAYOUT_NAMES = ["sections", "headline", "cards", "compact", "compact-ascii"]


class FakeWindow:
    def __init__(self):
        self.alerts = []
        self.backtracked = 0

    def backtrack(self, *args):
        self.backtracked += 1

    def alert(self, message):
        self.alerts.append(message)

    def message(self, text, kind="info"):
        self.alerts.append((kind, text))

    def open(self, *args, **kwargs):
        pass


@pytest.fixture
def conf():
    conf = get_config(
        "tests/configs/small.conf",
        _get_color_from_vdir=lambda path: None,
        _get_vdir_type=lambda path: "calendar",
    )
    conf["locale"]["longdateformat"] = "%Y-%m-%d"
    conf["locale"]["timeformat"] = "%H:%M"
    return conf


@pytest.fixture
def pane(coll_vdirs, conf):
    collection, _ = coll_vdirs
    pane = ui.ClassicView(collection, conf)
    pane.window = FakeWindow()
    return pane


def make_editor(pane, layout, ics="event_dt_simple"):
    event = pane.collection.create_event_from_ics(_get_text(ics), calendar_name=cal1)
    saved = []
    editor = EventEditor(pane, event, save_callback=lambda *args: saved.append(args), layout=layout)
    return editor, event, saved


def render(editor, cols, rows=30):
    return "\n".join(line.decode().rstrip() for line in editor.render((cols, rows), True).text)


def type_text(editor, size, text):
    for char in text:
        editor.keypress(size, char)


def test_registry_ids_unique():
    ids = [field.id for field in FIELDS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("layout", LAYOUT_NAMES)
def test_layout_renders(pane, layout):
    editor, event, _ = make_editor(pane, layout)
    for cols in (46, 80, 120):
        text = render(editor, cols)
        assert "An Event" in text
        assert "Save" in text
    assert editor.layout is LAYOUTS[layout]
    if layout == "compact-ascii":
        assert all(ord(char) < 128 for char in render(editor, 60))


@pytest.mark.parametrize("layout", [*LAYOUT_NAMES, "auto"])
@pytest.mark.parametrize("cols", [50, 110])
def test_edit_title_and_save(pane, layout, cols):
    editor, event, saved = make_editor(pane, layout)
    size = (cols, 30)
    render(editor, cols)
    # the title has the focus initially
    assert focused_field_id(editor._w) == "summary"
    assert not editor.changed
    editor.keypress(size, "end")
    type_text(editor, size, " Renamed")
    render(editor, cols)
    assert editor.changed
    editor.save(None)
    assert event.summary == "An Event Renamed"
    assert len(saved) == 1
    assert pane.window.backtracked == 1


@pytest.mark.parametrize("layout", ["headline", "compact"])
def test_collapsed_field_expands(pane, layout):
    editor, event, _ = make_editor(pane, layout)
    size = (80, 30)
    text = render(editor, 80)
    assert "+ location" in text or "+loc" in text
    editor.expand("location")
    text = render(editor, 80)
    assert "+ location" not in text
    assert "+loc" not in text
    assert focused_field_id(editor._w) == "location"
    type_text(editor, size, "Berlin")
    editor.save(None)
    assert event.location == "Berlin"


def test_sections_tab_reaches_location(pane):
    editor, event, _ = make_editor(pane, "sections")
    size = (80, 40)
    render(editor, 80)
    for _ in range(50):
        if focused_field_id(editor._w) == "location":
            break
        editor.keypress(size, "tab")
    else:
        pytest.fail("tab never reached the location field")
    type_text(editor, size, "Somewhere")
    editor.save(None)
    assert event.location == "Somewhere"


def test_auto_switches_and_keeps_focus(pane):
    editor, event, _ = make_editor(pane, "auto")
    render(editor, 50)
    assert editor.layout.name == "compact"
    editor.expand("url")
    assert focused_field_id(editor._w) == "url"
    render(editor, 80)
    assert editor.layout.name == "sections"
    assert focused_field_id(editor._w) == "url"
    render(editor, 140, 60)
    assert editor.layout.name == "sections-airy"
    # too few rows for the airy spacing
    render(editor, 140, 15)
    assert editor.layout.name == "sections"
    assert focused_field_id(editor._w) == "url"


def test_alarms_add_and_delete(pane):
    editor, event, _ = make_editor(pane, "sections")
    assert editor.alarmseditor.get_alarms() == []
    editor.alarmseditor.add_alarm(None, dt.timedelta(minutes=-15))
    editor.alarmseditor.add_alarm(None, dt.timedelta(hours=-1))
    text = render(editor, 80)
    assert "15 minutes before" in text
    assert text.count("✕") == 2
    # ✕ on the first alarm row deletes that alarm
    first = editor.alarmseditor.alarm_editors[0]
    first.columns.contents[-1][0].keypress((1,), "enter")
    assert editor.alarmseditor.get_alarms() == [(dt.timedelta(hours=-1), "An Event")]
    editor.save(None)
    assert [alarm[0] for alarm in event.alarms] == [dt.timedelta(hours=-1)]


def test_collapsed_alarm_adder(pane):
    editor, event, _ = make_editor(pane, "compact")
    assert "+alrm" in render(editor, 46)
    editor.expand("alarms")
    assert len(editor.alarmseditor.get_alarms()) == 1
    assert focused_field_id(editor._w) == "alarms"


def test_allday_toggle_keeps_layout(pane):
    editor, event, _ = make_editor(pane, "sections")
    editor.startendeditor.checkallday.set_state(True)
    text = render(editor, 80)
    assert "[X] all day" in text
    assert "for 1d" in text  # event_dt_simple is on one day
    editor.save(None)
    assert event.allday


@pytest.mark.parametrize("layout", LAYOUT_NAMES)
def test_save_key_and_action_bar(pane, layout):
    editor, event, saved = make_editor(pane, layout)
    size = (80, 30)
    render(editor, 80)
    editor.keypress(size, "end")
    type_text(editor, size, "X")
    assert "unsaved" in render(editor, 80)
    editor.keypress(size, pane._conf["keybindings"]["save"][0])
    assert event.summary == "An EventX"
    assert len(saved) == 1


def test_choice_popup_closes_on_esc():
    from khal.ui.widgets import Choice, ChoiceList

    choice = Choice(["a", "b"], "a")
    closed = []
    choice.close_pop_up = lambda: closed.append(True)
    popup = choice.create_pop_up()
    assert isinstance(popup, ChoiceList)
    assert popup.keypress((10, 2), "esc") is None
    assert closed == [True]


RECURRING = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//EN
BEGIN:VEVENT
SUMMARY:Great Event
DTSTART;TZID=Europe/Berlin:20261126T220000
DTEND;TZID=Europe/Berlin:20261126T230000
DTSTAMP:20261101T000000Z
UID:recurring-event
RRULE:FREQ=WEEKLY;INTERVAL=2
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:Great Event
TRIGGER:-PT1H30M
END:VALARM
END:VEVENT
END:VCALENDAR
"""


def make_recurring(pane, layout):
    event = pane.collection.create_event_from_ics(RECURRING, calendar_name=cal1)
    return EventEditor(pane, event, save_callback=lambda *a: None, layout=layout), event


def test_parse_duration():
    from khal.ui.widgets import format_duration_long, parse_duration

    assert parse_duration("5m") == dt.timedelta(minutes=5)
    assert parse_duration("1h30m") == dt.timedelta(hours=1, minutes=30)
    assert parse_duration("1d 2h") == dt.timedelta(days=1, hours=2)
    assert parse_duration("0") == dt.timedelta(0)
    for invalid in ("", "x", "5", "-5m", "5 parsecs"):
        with pytest.raises(ValueError, match=r"."):
            parse_duration(invalid)
    assert format_duration_long(dt.timedelta(hours=1, minutes=30)) == "1 hour 30 minutes"


def test_alarm_single_field(pane):
    editor, event = make_recurring(pane, "sections")
    size = (80, 40)
    text = render(editor, 80, 40)
    assert "◔ 1 hour 30 minutes before" in text  # unfocused: plain text
    focus_field(editor._w, "alarms")
    text = render(editor, 80, 40)
    assert "◔ 1h30m    before ▾  text: Great Event" in text  # focused: the fields
    for key in ["backspace"] * 5 + list("2d"):
        editor.keypress(size, key)
    assert editor.alarmseditor.get_alarms() == [(-dt.timedelta(days=2), "Great Event")]
    editor.keypress(size, "x")  # "2dx" is invalid
    assert "✗ e.g. 1h30m" in render(editor, 80, 40)
    editor.keypress(size, "backspace")
    assert "✗ e.g. 1h30m" not in render(editor, 80, 40)
    editor.save(None)
    assert [alarm[0] for alarm in event.alarms] == [-dt.timedelta(days=2)]


@pytest.mark.parametrize(("layout", "cols"), [("sections", 80), ("compact", 44)])
def test_repeat_sentence(pane, layout, cols):
    editor, event = make_recurring(pane, layout)
    text = render(editor, cols, 40)
    assert "│ every 2  weeks ▾" in text
    assert "Su" in text  # wraps instead of cutting off Sunday
    assert "│ ends never ▾" in text
    assert "next: Thu 12-10 · Thu 12-24 ·" in text
    assert not editor.recurrenceeditor.changed
    # toggling a weekday changes the rule
    editor.recurrenceeditor.weekday_checks._weekday_boxes["MO"].keypress((2,), " ")
    assert editor.recurrenceeditor.rrule()["byday"] == ["MO", "TH"]
    assert editor.recurrenceeditor.changed


def test_repeat_unit_follows_interval(pane):
    editor, _ = make_recurring(pane, "sections")
    interval = editor.recurrenceeditor.interval_edit.base_widget
    interval.set_edit_text("1")
    assert "│ every 1  week ▾" in render(editor, 80, 40)


def test_end_time_rolls_over_and_invalid_time(pane):
    editor, event, _ = make_editor(pane, "sections")
    size = (80, 30)
    render(editor, 80)
    focus_field(editor._w, "end")
    editor.keypress(size, "tab")  # date -> time
    for key in ["backspace"] * 5 + list("25:7"):
        editor.keypress(size, key)
    end_row = next(line for line in render(editor, 80).splitlines() if "End" in line)
    assert "25:7" in end_row
    assert end_row.endswith("✗ not a valid time")
    for key in ["backspace"] * 4 + list("08:00"):
        editor.keypress(size, key)
    text = render(editor, 80)
    end_row = next(line for line in text.splitlines() if "End" in line)
    assert "Thu 2014-04-10   08:00    for 22h30m" in end_row
    assert end_row.endswith("+1d, ends the next day")
    assert editor.startendeditor.enddt.date() == dt.date(2014, 4, 10)


def _see(pane, start=(22, 0), minutes=60):
    from khal.ui.editor import StartEndEditor

    start_dt = BERLIN.localize(dt.datetime(2026, 11, 26, *start))
    return StartEndEditor(start_dt, start_dt + dt.timedelta(minutes=minutes), pane._conf)


def test_duration_field_moves_end(pane):
    see = _see(pane)
    see.render((60,), True)
    assert see.duration_text() == "1h"
    duration = see.widgets.duration.original_widget
    duration.base_widget.set_edit_text("1h30m")
    duration._validate()
    assert see.enddt == BERLIN.localize(dt.datetime(2026, 11, 26, 23, 30))
    assert see.widgets.endtime.base_widget.get_edit_text() == "23:30"
    # moving the start keeps the duration
    start = see.widgets.starttime.base_widget
    start.set_edit_text("20:00")
    see.widgets.starttime.original_widget.original_widget._validate()
    assert see.enddt == BERLIN.localize(dt.datetime(2026, 11, 26, 21, 30))
    # editing the end updates the duration
    end = see.widgets.endtime.original_widget.original_widget
    end.base_widget.set_edit_text("22:15")
    end._validate()
    assert duration.get_edit_text() == "2h15m"


def test_time_drum(pane):
    see = _see(pane)
    end_popup = see.widgets.endtime.original_widget
    end_popup.keypress((6,), "enter")
    drum = end_popup._drum
    assert drum is not None
    rendered = "\n".join(line.decode().rstrip() for line in drum.render((drum.width, 6), True).text)
    lines = rendered.splitlines()
    assert lines[2].split() == ["23", ":", "00", "1h"]  # current value, duration
    assert lines[0].split()[-1] == "–"  # 21:00: before the start
    assert lines[3].split()[-2:] == ["2h", "+1d"]  # 00:00 is past midnight
    assert "↑↓ ←→ enter esc" in lines[-1]
    drum.keypress((drum.width, 6), "down")  # 00
    drum.keypress((drum.width, 6), "right")
    drum.keypress((drum.width, 6), "down")  # :05
    drum.keypress((drum.width, 6), "enter")
    assert see.widgets.endtime.base_widget.get_edit_text() == "00:05"
    assert see.enddt == BERLIN.localize(dt.datetime(2026, 11, 27, 0, 5))  # +1d
    assert see.duration_text() == "2h5m"
    # esc restores, typed digits set the time
    end_popup.keypress((6,), "enter")
    drum = end_popup._drum
    for key in "2315":
        drum.keypress((drum.width, 6), key)
    assert drum.values == [23, 15]
    drum.keypress((drum.width, 6), "esc")
    assert see.widgets.endtime.base_widget.get_edit_text() == "00:05"


def test_duration_drum(pane):
    see = _see(pane, minutes=60)
    popup = see.widgets.duration
    popup.keypress((7,), "enter")
    drum = popup._drum
    rendered = [line.decode() for line in drum.render((drum.width, 6), True).text]
    assert rendered[2].split() == ["1h", "23:00"]
    assert rendered[3].split() == ["1h15m", "23:15"]
    drum.keypress((drum.width, 6), "down")
    drum.keypress((drum.width, 6), "enter")
    assert see.enddt == BERLIN.localize(dt.datetime(2026, 11, 26, 23, 15))
