# Copyright (c) 2013-2022 khal contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""How ikhal's list of events looks: densities, day headers, the header line.

A density is a preset of format strings (see `PRESETS`); `classic` keeps
`[view] agenda_event_format` and the old day headers. Besides the usual
event attributes (see `khal list --format`), the ikhal event formats know
`{time}` (start time, "all day" or an arrow for events that started
earlier), `{details}` (calendar · location · repeats), `{day-label}` (the
day, only on the first event of a day) and `{tab}` (the rest of the line is
right-aligned).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace

import urwid

from khal.parse_datetime import guesstimedeltafstr, timedelta2str

DENSITIES = ("comfortable", "regular", "dense")
DAY_LABEL_WIDTH = 7  # `{day-label:<7}` in the dense preset


@dataclass(frozen=True)
class AgendaStyle:
    density: str  # classic, comfortable, regular or dense
    event_format: str  # may contain \n (several rows per event) and {tab}
    day_format: str  # for the day headers (see day_attributes())
    day_header: str  # text, rule or none (dense: no header rows for days with events)
    blank_after_header: bool
    event_color: str  # line or bar
    free_time: dt.timedelta | None  # minimum gap shown as "┊ 3h free"
    now_line: bool
    free_hours: tuple[dt.time, dt.time] | None = None  # only count gaps within these

    @property
    def classic(self) -> bool:
        return self.density == "classic"

    def event_rows(self) -> int:
        return self.event_format.count("\n") + 1


PRESETS: dict[str, dict] = {
    "comfortable": {
        "event_format": "{start-end-time-style:<12}{title}{range}{tab}{duration-short}\n"
        "{empty:<12}{details}",
        "day_header": "rule",
        "blank_after_header": True,
    },
    "regular": {
        "event_format": "{time:<8}{title}{range}{repeat-symbol}{alarm-symbol}"
        "{location-gap}{location}{tab}{duration-short}",
        "day_header": "rule",
        "blank_after_header": False,
    },
    "dense": {
        "event_format": "{day-label:<7}{time:<8}{title}{range}{tab}{duration-short}",
        "day_header": "none",
        "blank_after_header": False,
    },
}
# {day-padded}: single-digit days get a leading space, so the headers of
# consecutive days line up (" 9 Dec" / "10 Dec")
DEFAULT_DAY_FORMAT = "{name-short} {day-padded} {month-short}{relative-separator}{relative}"


def parse_free_time(value) -> dt.timedelta | None:
    if isinstance(value, dt.timedelta):
        return value if value > dt.timedelta(0) else None
    value = str(value or "").strip().lower()
    if value in ("", "0", "off", "false", "no"):
        return None
    delta = guesstimedeltafstr(value)
    return delta if delta > dt.timedelta(0) else None


def parse_hours(value) -> tuple[dt.time, dt.time] | None:
    """`08:00-18:00` -> (08:00, 18:00), empty -> None"""
    value = str(value or "").strip()
    if not value:
        return None
    start, _, end = value.replace("–", "-").partition("-")
    return (
        dt.datetime.strptime(start.strip(), "%H:%M").time(),
        dt.datetime.strptime(end.strip(), "%H:%M").time(),
    )


def agenda_style(conf, density: str | None = None) -> AgendaStyle:
    """the style configured in `[view]` (with `density` instead of the configured one)"""
    view = conf["view"]
    if density is None:
        density = view.get("density", "classic")
        if density == "auto":
            density = "regular"
    ikhal_day_format = view.get("ikhal_day_format", "") or ""
    free_time = parse_free_time(view.get("show_free_time", "3h"))
    free_hours = parse_hours(view.get("free_time_hours", ""))
    if density == "classic":
        return AgendaStyle(
            density="classic",
            event_format=view.get("agenda_event_format", "{title}"),
            day_format=ikhal_day_format,
            day_header=view.get("day_header", "text"),
            blank_after_header=False,
            event_color=view.get("event_color", "line"),
            free_time=free_time,
            now_line=False,
            free_hours=free_hours,
        )
    preset = PRESETS[density]
    return AgendaStyle(
        density=density,
        event_format=preset["event_format"],
        day_format=ikhal_day_format or DEFAULT_DAY_FORMAT,
        day_header=preset["day_header"],
        blank_after_header=preset["blank_after_header"],
        event_color=view.get("event_color", "line"),
        free_time=free_time,
        now_line=True,
        free_hours=free_hours,
    )


def with_density(style: AgendaStyle, conf, density: str) -> AgendaStyle:
    return replace(agenda_style(conf, density), event_color=style.event_color)


def relative_day_name(day: dt.date, today: dt.date | None = None) -> str:
    today = today or dt.date.today()
    return {0: "today", 1: "tomorrow", -1: "yesterday"}.get((day - today).days, "")


def day_attributes(day: dt.date, conf, today: dt.date | None = None) -> dict[str, str]:
    """attributes for formatting a day header (`ikhal_day_format`)"""
    relative = relative_day_name(day, today)
    return {
        "name": day.strftime("%A"),
        "name-short": day.strftime("%a")[:2],
        "day": str(day.day),
        "day-padded": f"{day.day:2}",
        "month": day.strftime("%B"),
        "month-short": day.strftime("%b"),
        "date": day.strftime(conf["locale"]["dateformat"]),
        "date-long": day.strftime(conf["locale"]["longdateformat"]),
        "week": str(day.isocalendar()[1]),
        "relative": relative,
        "relative-separator": " · " if relative else "",
    }


def event_attributes(event, day: dt.date, first_of_day: bool, conf) -> dict[str, str]:
    """the ikhal-only attributes of an event in the list (see module doc)"""
    attributes = event.attributes(day, colors=False)
    if event.allday:
        time = "all day"
    else:
        time = attributes["start-style"]
    details = [event.calendar]
    if event.location:
        details.append(event.location.strip())
    if event.recurring:
        details.append("repeats")
    if event.alarms:
        details.append("alarm")
    attributes.update(
        {
            "time": time,
            "details": " · ".join(details),
            "day-label": f"{day:%a}"[:2] + f" {day.day:>2}" if first_of_day else "",
            "location-gap": "  " if event.location else "",
            "empty": "",
            "tab": "\t",
        }
    )
    return attributes


def text_width(text: str) -> int:
    """columns `text` takes in the terminal (wide characters count twice)"""
    return urwid.calc_width(text, 0, len(text))


def clip(text: str, width: int, ellipsis: str = "…") -> str:
    """`text` cut to `width` columns, with `ellipsis` if it had to be cut"""
    if text_width(text) <= width:
        return text
    room = max(0, width - text_width(ellipsis))
    out, used = "", 0
    for char in text:
        char_width = text_width(char)
        if used + char_width > room:
            break
        out += char
        used += char_width
    return out + ellipsis if width > 0 else ""


def align_tab(text: str, width: int, ellipsis: str = "…") -> str:
    """lay out each line `left\\tright` with `right` right-aligned in `width`
    (in terminal columns, wide characters count twice)"""
    lines = []
    for line in text.split("\n"):
        left, _, right = line.partition("\t")
        room = width - text_width(right) - (1 if right else 0)
        left = clip(left, room, ellipsis) if room > 0 else ""
        lines.append(left + " " * max(0, room - text_width(left)) + (" " + right if right else ""))
    return "\n".join(lines)


def format_free(gap: dt.timedelta) -> str:
    return timedelta2str(gap).replace(" ", "") + " free"


def free_gaps(
    events,
    day: dt.date,
    minimum: dt.timedelta,
    hours: tuple[dt.time, dt.time] | None = None,
) -> dict[int, dt.timedelta]:
    """index of an event -> the free time before it (only gaps >= minimum)

    With `hours`, only the part of a gap within those hours counts.
    """
    gaps: dict[int, dt.timedelta] = {}
    previous_end = None
    for index, event in enumerate(events):
        if event.allday:
            continue
        start = event.start_local.replace(tzinfo=None)
        end = event.end_local.replace(tzinfo=None)
        if start.date() != day:
            previous_end = end if end.date() == day else None
            continue
        if previous_end is not None:
            gap_start, gap_end = previous_end, start
            if hours is not None:
                gap_start = max(gap_start, dt.datetime.combine(day, hours[0]))
                gap_end = min(gap_end, dt.datetime.combine(day, hours[1]))
            gap = gap_end - gap_start
            if gap >= minimum:
                gaps[index] = gap
        if previous_end is None or end > previous_end:
            previous_end = end
    return gaps


def rows_needed(style: AgendaStyle, counts: list[int]) -> int:
    """rows the list needs for days with `counts` events each"""
    total = 0
    for count in counts:
        if style.day_header == "none":
            total += max(count, 1)
            continue
        total += 1 + (1 if style.blank_after_header else 0) + count * style.event_rows()
        total += 1 if count else 0  # the blank row after a day's events
    return total


def choose_density(conf, counts: list[int], rows: int) -> str:
    """the airiest density that shows `counts` (events per day) within `rows`"""
    for density in DENSITIES:
        if rows_needed(agenda_style(conf, density), counts) <= rows:
            return density
    return DENSITIES[-1]


# -- the window's header line


def next_event(collection, now: dt.datetime, days: int = 2):
    """the next event starting after `now` (within `days`), or None"""
    for offset in range(days):
        day = now.date() + dt.timedelta(days=offset)
        for event in sorted(collection.get_events_on(day)):
            if event.allday:
                continue
            try:
                start = event.start_local.replace(tzinfo=None)
            except (AttributeError, TypeError):
                continue
            if start > now:
                return event, start
    return None


def format_in(delta: dt.timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(minutes, 60)
    if hours >= 24:
        return f"in {hours // 24}d{hours % 24}h" if hours % 24 else f"in {hours // 24}d"
    if hours:
        return f"in {hours}h{minutes:02d}m" if minutes else f"in {hours}h"
    return f"in {minutes}m"


def header_attributes(conf, collection, now: dt.datetime | None = None) -> dict[str, str]:
    now = now or dt.datetime.now()
    attributes = {
        "date": now.strftime(conf["locale"]["dateformat"]),
        "date-long": now.strftime(conf["locale"]["longdateformat"]),
        "weekday": now.strftime("%a"),
        "day": str(now.day),
        "month-short": now.strftime("%b"),
        "time": now.strftime(conf["locale"]["timeformat"]),
        "week": str(now.isocalendar()[1]),
        "next-title": "",
        "next-in": "",
        "next-time": "",
        "next-separator": "",
    }
    found = next_event(collection, now) if collection is not None else None
    if found is not None:
        event, start = found
        attributes.update(
            {
                "next-title": event.summary,
                "next-in": format_in(start - now),
                "next-time": start.strftime(conf["locale"]["timeformat"]),
                "next-separator": "  next: ",
            }
        )
    return attributes


DEFAULT_HEADER_FORMAT = "{weekday} {day} {month-short} {time}{next-separator}{next-title} {next-in}"


def format_header(conf, collection, now: dt.datetime | None = None) -> str:
    header_format = conf["view"].get("header_format", "") or ""
    if not header_format:
        return ""
    try:
        return " " + header_format.format(**header_attributes(conf, collection, now)).rstrip()
    except (KeyError, ValueError, IndexError):
        return " " + header_format
