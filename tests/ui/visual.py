"""render ikhal like it runs, for visual checks and attribute tests

`Screen` builds ikhal's real palette (`khal.ui.build_palette`) and window
(`khal.ui.root_widget`) around a sample collection similar to the one of the
mockups in design/ (events from design/overview-mockups/gen_overview.py),
with the time frozen at Thursday, 2026-11-26 11:20.

To look at the renders, write them to a directory::

    KHAL_VISUAL_DUMP=/tmp/khal-renders .venv/bin/python -m pytest tests/ui/test_visual.py

which writes `<name>.ans` (24 bit colour, `cat` it in a terminal) and
`<name>.txt` (plain text) for every render.
"""

from __future__ import annotations

import datetime as dt
import os
import pathlib
import textwrap

import urwid

from khal import ui
from khal.khalendar import CalendarCollection
from khal.settings import get_config

NOW = dt.datetime(2026, 11, 26, 11, 20)

# name -> colour, the calendar colours of the retrobox mockups
CALENDARS = {
    "home": "#8ec07c",
    "work": "#83a598",
    "family": "#d3869b",
    "birthdays": "#fabd2f",
}

ALARM = "BEGIN:VALARM\nACTION:DISPLAY\nDESCRIPTION:{summary}\nTRIGGER:-PT5M\nEND:VALARM\n"


def _vevent(uid, summary, start, end, *, rrule="", alarm=False, location=""):
    if isinstance(start, dt.datetime):
        times = f"DTSTART:{start:%Y%m%dT%H%M%S}\nDTEND:{end:%Y%m%dT%H%M%S}\n"
    else:
        times = f"DTSTART;VALUE=DATE:{start:%Y%m%d}\nDTEND;VALUE=DATE:{end:%Y%m%d}\n"
    lines = (
        "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//khal//visual tests//EN\nBEGIN:VEVENT\n"
        f"UID:{uid}\nSUMMARY:{summary}\n{times}DTSTAMP:20261101T000000Z\n"
    )
    if rrule:
        lines += f"RRULE:{rrule}\n"
    if location:
        lines += f"LOCATION:{location}\n"
    if alarm:
        lines += ALARM.format(summary=summary)
    return lines + "END:VEVENT\nEND:VCALENDAR\n"


def _at(days: int, hhmm: str) -> dt.datetime:
    hour, minute = map(int, hhmm.split(":"))
    return dt.datetime.combine(NOW.date() + dt.timedelta(days=days), dt.time(hour, minute))


def _day(days: int) -> dt.date:
    return NOW.date() + dt.timedelta(days=days)


# (calendar, uid, summary, start, end, options); the events of the mockups,
# Standup and Choir repeat, the hiking trip spans the weekend
EVENTS = [
    ("work", "standup", "Standup", _at(-3, "09:00"), _at(-3, "09:15"),
     {"rrule": "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH"}),
    ("home", "lunch", "Lunch w/ Bob", _at(0, "12:30"), _at(0, "13:30"),
     {"location": "Café Lotte"}),
    ("family", "choir", "Choir", _at(0, "19:00"), _at(0, "21:00"),
     {"rrule": "FREQ=WEEKLY", "alarm": True}),
    ("work", "great", "Great Event", _at(1, "08:00"), _at(1, "17:30"),
     {"alarm": True, "location": "Haus der Kulturen"}),
    ("home", "beer", "beer", _at(1, "10:30"), _at(1, "12:30"), {}),
    ("home", "test", "test", _at(1, "14:00"), _at(1, "15:00"), {}),
    ("family", "hiking", "Hiking trip", _day(2), _day(4), {}),
    ("home", "dinner", "Dinner at Anna's", _at(2, "20:00"), _at(2, "23:00"),
     {"location": "Kreuzberg"}),
    ("home", "dentist", "Dentist", _at(4, "15:00"), _at(4, "16:00"), {"alarm": True}),
    ("birthdays", "mum", "Mum's birthday", _day(5), _day(6), {}),
    ("home", "yoga", "Yoga", _at(-2, "18:00"), _at(-2, "19:00"), {}),
    ("work", "planning", "Planning", _at(8, "10:00"), _at(8, "12:00"), {}),
    ("birthdays", "ben", "Ben's birthday", _day(12), _day(13), {}),
    ("family", "market", "Christmas market", _at(15, "19:30"), _at(15, "22:00"), {}),
]  # fmt: skip

# Friday morning with six events at once (design/overview-mockups/39-grid-overlaps)
BUSY = [
    ("work", "sync", "Team sync", _at(1, "09:00"), _at(1, "10:00"), {}),
    ("family", "anna", "Anna: 1:1 with Max", _at(1, "09:00"), _at(1, "11:00"), {}),
    ("birthdays", "review", "Ben: code review", _at(1, "09:30"), _at(1, "10:30"), {}),
    ("work", "interview", "Interview", _at(1, "09:30"), _at(1, "11:30"), {}),
    ("home", "plumber", "Call plumber", _at(1, "10:00"), _at(1, "11:00"), {}),
]  # fmt: skip

CONFIG = """
[calendars]
{calendars}
[locale]
local_timezone = UTC
default_timezone = UTC
timeformat = %H:%M
dateformat = %d.%m.
longdateformat = %a %Y-%m-%d
datetimeformat = %d.%m. %H:%M
longdatetimeformat = %a %Y-%m-%d %H:%M
firstweekday = 0
weeknumbers = right
unicode_symbols = True
[default]
default_calendar = home
highlight_event_days = True
[sqlite]
path = {db}
[view]
{view}
"""

DEFAULT_VIEW = {
    "theme": "retrobox",
    "editor_layout": "cards",
    "density": "auto",
    "day_marking": "dot",
    "frame": "color",
}


def make_conf(tmp_path: pathlib.Path, **view):
    """a configuration like the user's (retrobox, cards, dots, week numbers right)"""
    calendars = ""
    for name, color in CALENDARS.items():
        path = tmp_path / name
        path.mkdir(exist_ok=True)
        calendars += f"[[{name}]]\npath = {path}\ncolor = '{color}'\n"
    view = {**DEFAULT_VIEW, **view}
    text = CONFIG.format(
        calendars=textwrap.indent(calendars, "  "),
        db=tmp_path / "khal.db",
        view="\n".join(f"{key} = {value}" for key, value in view.items()),
    )
    config = tmp_path / "khal.conf"
    config.write_text(text, encoding="utf-8")
    return get_config(str(config), _get_color_from_vdir=lambda path: None)


def make_collection(conf, busy: bool = False) -> CalendarCollection:
    """the events of the mockups (with `busy`, also BUSY)"""
    from khal.cli_utils import build_collection

    collection = build_collection(conf, None)
    for calendar, uid, summary, start, end, options in EVENTS + (BUSY if busy else []):
        event = collection.create_event_from_ics(
            _vevent(uid, summary, start, end, **options), calendar_name=calendar
        )
        collection.insert(event)
    return collection


class Screen:
    """ikhal's window with the real palette, without running the main loop"""

    def __init__(self, conf, collection, size=(100, 28), color_mode="rgb", footer=True) -> None:
        self.conf = conf
        self.collection = collection
        self.size = size
        themed = ui.build_palette(conf, collection, color_mode)
        self.pane = ui.ClassicView(collection, conf, title="khal", description="")
        self.window = ui.Window(
            footer=ui.footer_hints(conf["keybindings"], ["q"]) if footer else "",
            quit_keys=["q"],
            version="khal 0.14",
        )
        self.window.theme_colors = themed.theme_colors
        self.window.paints_background = themed.paints_background
        self.window.backdrop = themed.backdrop
        self.window.open(self.pane)
        self.root = ui.root_widget(self.window)
        self.screen = urwid.display.raw.Screen()
        self.loop = urwid.MainLoop(
            self.root, palette=themed.palette, screen=self.screen, pop_ups=False
        )
        self.screen.colors = 2**24 if color_mode == "rgb" else 256
        self.window.loop = self.loop

    # -- driving
    def press(self, *keys: str) -> Screen:
        for key in keys:
            self.render()  # urwid widgets lay out on render
            unhandled = self.root.keypress(self.size, key)
            if unhandled is not None:  # like MainLoop(unhandled_input=...) in start_pane
                self.window.on_key_press(unhandled)
        return self

    def render(self) -> urwid.Canvas:
        return self.root.render(self.size, focus=True)

    @property
    def column(self):
        return self.pane.eventscolumn.original_widget

    def event(self, uid: str):
        for event in self.collection.search(""):
            if event.uid == uid:
                return event
        raise KeyError(uid)

    # -- output
    def text(self) -> str:
        return "\n".join(line.decode().rstrip() for line in self.render().text)

    def attributes(self) -> set:
        return {attr for row in self.render().content() for attr, _, _ in row}

    def undefined_attributes(self) -> set:
        """attributes in the canvas the screen has no palette entry for"""
        return {attr for attr in self.attributes() if attr not in self.screen._palette}

    def ansi(self) -> str:
        out = []
        for row in self.render().content():
            line = ""
            for attr, _, text in row:
                spec = self._spec(attr)
                line += _sgr(spec) + text.decode() + "\x1b[0m"
            out.append(line)
        return "\n".join(out) + "\n"

    def _spec(self, attr) -> urwid.AttrSpec | None:
        entry = self.screen._palette.get(attr)
        if entry is None:
            return None
        return entry[4] if self.screen.colors == 2**24 else entry[3]

    def dump(self, name: str) -> str:
        """the plain text render; with KHAL_VISUAL_DUMP set also write files"""
        text = self.text()
        directory = os.environ.get("KHAL_VISUAL_DUMP")
        if directory:
            path = pathlib.Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            (path / f"{name}.txt").write_text(text + "\n", encoding="utf-8")
            (path / f"{name}.ans").write_text(self.ansi(), encoding="utf-8")
        return text


def _sgr(spec: urwid.AttrSpec | None) -> str:
    if spec is None:
        return "\x1b[0m"
    codes = ["0"]
    if spec.bold:
        codes.append("1")
    if spec.italics:
        codes.append("3")
    if spec.underline:
        codes.append("4")
    if spec.standout:
        codes.append("7")
    fg, bg = spec.get_rgb_values()[:3], spec.get_rgb_values()[3:]
    if fg[0] is not None:
        codes.append("38;2;{};{};{}".format(*fg))
    if bg[0] is not None:
        codes.append("48;2;{};{};{}".format(*bg))
    return "\x1b[" + ";".join(codes) + "m"


def children(widget: urwid.Widget) -> list[urwid.Widget]:
    """the direct children of `widget` (containers, decorations, wraps)"""
    if isinstance(widget, urwid.WidgetDecoration):
        return [widget.original_widget]
    if isinstance(widget, urwid.WidgetWrap):
        return [widget._w]
    if isinstance(widget, urwid.PopUpLauncher):
        return [widget.original_widget]
    if isinstance(widget, urwid.ListBox):
        return list(widget.body)
    contents = getattr(widget, "contents", None)
    if isinstance(contents, list):
        return [item[0] if isinstance(item, tuple) else item for item in contents]
    return []


def find(widget: urwid.Widget, cls: type) -> list:
    """all widgets of type `cls` in the tree below `widget` (depth first)"""
    found, todo, seen = [], [widget], set()
    while todo:
        current = todo.pop(0)
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, cls):
            found.append(current)
        todo[0:0] = children(current)
    return found
