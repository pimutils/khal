"""ikhal's list of events: densities, {tab}, {range}, free time, now line, header"""

import datetime as dt

import pytest
import urwid
from freezegun import freeze_time

from khal import ui
from khal.settings import get_config
from khal.ui import agenda
from tests.utils import cal1


@pytest.fixture
def conf():
    conf = get_config(
        "tests/configs/small.conf",
        _get_color_from_vdir=lambda path: None,
        _get_vdir_type=lambda path: "calendar",
    )
    conf["locale"]["timeformat"] = "%H:%M"
    conf["locale"]["dateformat"] = "%d.%m."
    conf["locale"]["longdateformat"] = "%d.%m.%Y"
    conf["view"]["frame"] = "False"
    return conf


def add(collection, conf, start, minutes, title, allday_days=0, location=""):
    if allday_days:
        data = {"dtstart": start, "dtend": start + dt.timedelta(days=allday_days), "allday": True}
    else:
        data = {
            "dtstart": start,
            "dtend": start + dt.timedelta(minutes=minutes),
            "allday": False,
        }
    data.update(
        {
            "summary": title,
            "timezone": conf["locale"]["default_timezone"],
            "alarms": "",
            "location": location,
        }
    )
    event = collection.create_event_from_dict(data, calendar_name=cal1)
    collection.insert(event)
    return event


def test_align_tab():
    assert agenda.align_tab("09:00 Standup\t15m", 20) == "09:00 Standup    15m"
    assert agenda.align_tab("09:00 A very long title\t15m", 16) == "09:00 A ver… 15m"
    assert agenda.align_tab("a\tb\nc", 5) == "a   b\nc    "


def test_range_and_duration_short(coll_vdirs, conf):
    collection, _ = coll_vdirs
    hike = add(collection, conf, dt.date(2026, 11, 28), 0, "Hike", allday_days=2)
    attributes = hike.attributes(dt.date(2026, 11, 28), colors=False)
    assert attributes["range"] == " (Sat–Sun)"
    assert attributes["duration-short"] == ""
    lunch = add(collection, conf, dt.datetime(2026, 11, 26, 12, 30), 90, "Lunch")
    attributes = lunch.attributes(dt.date(2026, 11, 26), colors=False)
    assert attributes["range"] == ""
    assert attributes["duration-short"] == "1h30m"


def test_free_gaps(coll_vdirs, conf):
    collection, _ = coll_vdirs
    day = dt.date(2026, 11, 26)
    events = [
        add(collection, conf, dt.datetime(2026, 11, 26, 7, 0), 60, "a"),
        add(collection, conf, dt.datetime(2026, 11, 26, 12, 0), 60, "b"),
        add(collection, conf, dt.datetime(2026, 11, 26, 14, 0), 60, "c"),
        add(collection, conf, dt.datetime(2026, 11, 26, 20, 0), 60, "d"),
    ]
    events = sorted(events)
    gaps = agenda.free_gaps(events, day, dt.timedelta(hours=3))
    assert gaps == {1: dt.timedelta(hours=4), 3: dt.timedelta(hours=5)}
    hours = agenda.parse_hours("08:00-18:00")
    gaps = agenda.free_gaps(events, day, dt.timedelta(hours=3), hours)
    assert gaps == {1: dt.timedelta(hours=4), 3: dt.timedelta(hours=3)}
    assert agenda.parse_free_time("off") is None
    assert agenda.parse_free_time("90m") == dt.timedelta(minutes=90)


def test_choose_density(conf):
    counts = [3, 2, 2]
    # auto never picks comfortable (only when configured)
    assert agenda.choose_density(conf, counts, 40) == "regular"
    assert agenda.choose_density(conf, counts, 14) == "regular"
    assert agenda.choose_density(conf, counts, 8) == "dense"


@freeze_time("2026-11-26 11:20")
@pytest.mark.parametrize("density", ["regular", "comfortable", "dense", "classic"])
def test_render_list(coll_vdirs, conf, density):
    collection, _ = coll_vdirs
    add(collection, conf, dt.datetime(2026, 11, 26, 9, 0), 15, "Standup")
    add(collection, conf, dt.datetime(2026, 11, 26, 12, 30), 60, "Lunch", location="Café")
    add(collection, conf, dt.datetime(2026, 11, 26, 19, 0), 120, "Choir")
    add(collection, conf, dt.date(2026, 11, 28), 0, "Hike", allday_days=2)
    conf["view"]["density"] = density
    pane = ui.ClassicView(collection, conf)
    column = pane.eventscolumn.original_widget
    text = "\n".join(line.decode().rstrip() for line in column.render((60, 20), True).text)
    if density == "classic":
        assert "Today (Thursday, 26.11.2026)" in text
        return
    if density == "dense":
        assert "Th 26  ▍09:00   Standup" in text
        assert "── " not in text
    else:
        assert "── Th 26 Nov · today ─" in text
        assert "── Fr 27 Nov · tomorrow ─" in text
    assert "11:20 ━━━" in text  # the now line, between Standup and Lunch
    assert text.index("Standup") < text.index("11:20 ━") < text.index("Lunch")
    assert "┊ 5h30m free" in text  # 13:30 -> 19:00 (and 3h15m before Lunch)
    assert "Hike (Sat–Sun)" in text
    standup = next(line for line in text.splitlines() if "Standup" in line)
    assert standup.endswith("15m")
    if density == "comfortable":
        # the second row only with what the first doesn't show: no calendar
        rows = text.splitlines()
        lunch = rows[next(i for i, row in enumerate(rows) if "Lunch" in row) + 1]
        assert lunch.strip().endswith("Café")
        assert "foobar" not in text
        choir = next(i for i, row in enumerate(rows) if "Choir" in row)
        assert "▍" not in text.splitlines()[choir + 1]  # nothing to add: one row
        assert "12:30–13:30 Lunch" in text


@freeze_time("2026-11-26 11:20")
def test_header_line(coll_vdirs, conf):
    collection, _ = coll_vdirs
    add(collection, conf, dt.datetime(2026, 11, 26, 12, 30), 60, "Lunch w/ Bob")
    pane = ui.ClassicView(collection, conf)
    assert pane.title == (
        " Thursday, 26 November 2026 · week 48 · 11:20  next: Lunch w/ Bob in 1h10m"
    )
    text = urwid.decompose_tagmarkup(pane.header_markup(200))[0]
    assert text.startswith(" Thursday, 26 November 2026 · week 48 · 11:20  next: Lunch w/ Bob")
    # narrow: shorter, then without the next event
    assert urwid.decompose_tagmarkup(pane.header_markup(60))[0] == (
        " Thu 26 Nov 11:20  next: Lunch w/ Bob in 1h10m"
    )
    assert urwid.decompose_tagmarkup(pane.header_markup(30))[0] == " Thu 26 Nov 11:20"
    conf["view"]["header_format"] = "{date} {time}"
    assert pane.title == " 26.11. 11:20"


def test_default_day_headers_line_up():
    """single-digit days are padded, so headers of consecutive days align"""
    conf = {"locale": {"dateformat": "%d.%m.", "longdateformat": "%d.%m.%Y"}}
    today = dt.date(2026, 11, 26)
    nine, ten = (
        agenda.DEFAULT_DAY_FORMAT.format(
            **agenda.day_attributes(dt.date(2026, 12, d), conf, today=today)
        )
        for d in (9, 10)
    )
    assert len(nine) == len(ten)
    assert nine.index("Dec") == ten.index("Dec")


# -- the formats of the densities


def _list(collection, conf):
    pane = ui.ClassicView(collection, conf)
    column = pane.eventscolumn.original_widget
    return [line.decode().rstrip() for line in column.render((60, 20), True).text]


@freeze_time("2026-11-26 11:20")
@pytest.mark.parametrize(
    ("density", "option", "value", "expected"),
    [
        ("regular", "event_format_regular", "{bar}<{title}>{tab}{calendar}", "▍<Standup>"),
        ("dense", "event_format_dense", "{day-label:<7}{bar}{title}!", "Th 26  ▍Standup!"),
        (
            "comfortable",
            "event_format_comfortable",
            "{bar} {title} at {time}",
            "▍ Standup at 09:00",
        ),
    ],
)
def test_density_formats_can_be_overridden(coll_vdirs, conf, density, option, value, expected):
    collection, _ = coll_vdirs
    add(collection, conf, dt.datetime(2026, 11, 26, 9, 0), 15, "Standup")
    conf["view"]["density"] = density
    conf["view"][option] = value
    lines = _list(collection, conf)
    standup = next(line for line in lines if "Standup" in line)
    assert expected in standup
    if density == "regular":
        assert standup.endswith("foobar")  # right-aligned with {tab}


@freeze_time("2026-11-26 11:20")
def test_comfortable_details_format(coll_vdirs, conf):
    collection, _ = coll_vdirs
    add(collection, conf, dt.datetime(2026, 11, 26, 9, 0), 15, "Standup")
    add(collection, conf, dt.datetime(2026, 11, 26, 12, 30), 60, "Lunch", location="Café")
    conf["view"]["density"] = "comfortable"
    conf["view"]["event_format_comfortable_details"] = "{bar}   where: {location}"
    lines = _list(collection, conf)
    lunch = next(i for i, line in enumerate(lines) if "Lunch" in line)
    assert "▍   where: Café" in lines[lunch + 1]
    # Standup has no location: the second line ("where: ") is not empty, kept
    conf["view"]["event_format_comfortable_details"] = "{bar} {location}"
    lines = _list(collection, conf)
    standup = next(i for i, line in enumerate(lines) if "Standup" in line)
    assert "▍" not in lines[standup + 1]  # an empty second line is left out


def test_defaults_are_expressible():
    """the documented defaults in khal.spec are the presets"""
    import pathlib

    spec = pathlib.Path("khal/settings/khal.spec").read_text(encoding="utf-8")
    for density, preset in agenda.PRESETS.items():
        assert f"#   {density}:" in spec or density == "comfortable"
        assert preset["event_format"] in spec
        if preset["details_format"]:
            assert preset["details_format"] in spec


@freeze_time("2026-11-26 11:20")
def test_invalid_density_format(coll_vdirs, conf, caplog):
    collection, _ = coll_vdirs
    add(collection, conf, dt.datetime(2026, 11, 26, 9, 0), 15, "Standup")
    conf["view"]["density"] = "regular"
    conf["view"]["event_format_regular"] = "{bar} {nonsense}"
    lines = _list(collection, conf)
    assert any("Standup [format error]" in line for line in lines)
