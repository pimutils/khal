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

"""The details of one event, laid out like the headline editor.

Title as headline, a summary line, a rule, then short noun labels (the
`noun` labels of the editor's field registry), the description as plain
text and key hints at the bottom.
"""

from __future__ import annotations

import datetime as dt

import urwid

from .editor_layout import (
    ASCII,
    FIELD,
    UNICODE,
    Glyphs,
    format_alarm,
    format_key,
    relative_to_now,
    section_rule,
)
from .floating import describe_rrule

LABEL_WIDTH = 8
PARTSTAT = {
    # PARTSTAT: (unicode mark, ascii mark, attribute)
    "ACCEPTED": ("✓", "+", "attendee accepted"),
    "DECLINED": ("✗", "-", "attendee declined"),
    "TENTATIVE": ("?", "?", "attendee tentative"),
    "NEEDS-ACTION": ("?", "?", "attendee tentative"),
}


def _day(value) -> dt.date:
    return value.date() if isinstance(value, dt.datetime) else value


def attendee_markup(attendees: list[tuple[str, str]], glyphs: Glyphs) -> list:
    markup: list = []
    for index, (address, partstat) in enumerate(attendees):
        unicode_mark, ascii_mark, attr = PARTSTAT.get(partstat, ("?", "?", "attendee tentative"))
        if index:
            markup.append("   ")
        markup.append((attr, unicode_mark if glyphs is UNICODE else ascii_mark))
        markup.append(" ")
        markup.append(("details dim" if partstat == "DECLINED" else "details text", address))
    return markup


def _relative_markup(event, today: dt.date | None = None) -> list:
    """`tomorrow`, `now · ends in 6 days`, `ended yesterday` (see
    relative_to_now); `today` (for tests) stands in for now's date"""
    now = dt.datetime.now()
    if today is not None and today != now.date():
        now = dt.datetime.combine(today, now.time())
    word, rest = relative_to_now(event.start_local, event.end_local, event.allday, now)
    if word:
        return [("details relative", word), ("details label", f" · {rest}")]
    return [("details relative", rest)]


def _short_day(day: dt.date) -> str:
    """`Fr 27 Nov`, like the day headers of the list"""
    return f"{day:%a}"[:2] + f" {day.day} {day:%b}"


def when_parts(event, conf) -> tuple[str, str, str]:
    """(start, end, duration) of the `when` row; `end` is empty for events
    within one day, which read `Fr 27 Nov 08:00–17:30`; never "all day"
    (the date says it)"""
    from .agenda import _naive, event_days, short_duration

    timeformat = conf["locale"]["timeformat"]
    first, last = event_days(event)
    duration = short_duration(event)
    if event.allday:
        if first == last:
            return _short_day(first), "", ""
        return _short_day(first), _short_day(last), duration
    start, end = _naive(event.start_local), _naive(event.end_local)
    times = f"{start.strftime(timeformat)}–{end.strftime(timeformat)}"
    if first == last:
        return f"{_short_day(first)} {times}", "", duration
    if end - start < dt.timedelta(hours=24):  # overnight
        return f"{_short_day(first)} {times} (+1 day)", "", duration
    return (
        f"{_short_day(first)} {start.strftime(timeformat)}",
        f"{_short_day(last)} {end.strftime(timeformat)}",
        duration,
    )


class WhenText(urwid.WidgetWrap):
    """`Fr 27 Nov 18:00 – Mo 30 Nov 12:00 · 2d18h`, or (if it doesn't fit)
    broken after the dash, each end on its own line"""

    def __init__(self, start: str, end: str, duration: str) -> None:
        tail = [("details dim", f" · {duration}")] if duration else []
        if end:
            self._one = [("details text", f"{start} – {end}"), *tail]
            self._two = [("details text", f"{start} –\n{end}"), *tail]
        else:
            self._one = self._two = [("details text", start), *tail]
        self._text = urwid.Text(self._one)
        super().__init__(self._text)

    def _choose(self, maxcol: int) -> None:
        text = urwid.decompose_tagmarkup(self._one)[0]
        markup = self._one if urwid.calc_width(text, 0, len(text)) <= maxcol else self._two
        if self._text.get_text()[0] != urwid.decompose_tagmarkup(markup)[0]:
            self._text.set_text(markup)

    def rows(self, size, focus=False):
        self._choose(size[0])
        return super().rows(size, focus)

    def render(self, size, focus=False):
        self._choose(size[0])
        return super().render(size, focus)


def details_rows(
    event,
    conf,
    glyphs: Glyphs,
    today: dt.date | None = None,
    headline: bool = True,
    rule: bool = True,
) -> list[urwid.Widget]:
    """the rows of the details (the inline card, the details column and the
    details view): the title (with `headline`), `● work · tomorrow`, then
    when, where, who, alarm, repeat, tags, link and notes, each a label and
    a value (free text as one string, wrapped)

    :param rule: (ignored, kept for compatibility)
    """
    del rule
    start = event.start_local
    entries: list[tuple[str, urwid.Widget]] = []

    def add(field_id: str | None, label: str, value) -> None:
        if field_id is not None:
            label = FIELD[field_id].noun or label
        entries.append((label, value if isinstance(value, urwid.Widget) else urwid.Text(value)))

    add(None, "when", WhenText(*when_parts(event, conf)))
    if event.location:
        add("location", "where", ("details text", event.location.strip()))
    attendees = event.attendees_status
    if attendees:
        add("attendees", "who", attendee_markup(attendees, glyphs))
    if event.organizer:
        add(None, "by", ("details text", event.organizer))
    for index, (delta, _) in enumerate(event.alarms):
        add(None, "alarm" if index == 0 else "", ("details text", format_alarm(delta)))
    if event.recurring:
        repeat = describe_rrule(event.recurobject, start, conf["locale"]["timeformat"])
        repeat = repeat.removeprefix("Repeats ").rstrip(".") if repeat else "repeats"
        add(None, "repeat", ("details text", repeat))
    if event.categories:
        add("categories", "tags", ("details text", event.categories))
    if event.url:
        add("url", "link", ("details link", event.url))
    if event.description:
        add(None, "notes", ("details text", event.description.strip()))

    width = max(len(label) for label, _ in entries) + 1
    rows: list[urwid.Widget] = []
    if headline:
        rows += [
            urwid.Divider(),
            urwid.Text(("details headline", event.summary or "(no title)")),
        ]
    rows += [
        urwid.Text(
            [
                (f"calendar {event.calendar} mark", glyphs.dot + " "),
                ("details label", f"{event.calendar} · "),
                *_relative_markup(event, today),
            ]
        ),
        urwid.Divider(),
    ]
    rows += [
        urwid.Columns([(width, urwid.Text(("details label", label))), value])
        for label, value in entries
    ]
    return rows


def key_hints(conf, glyphs: Glyphs, close: bool = False) -> list:
    """`enter edit  d delete  p duplicate` (and `esc close`)"""
    keys = conf["keybindings"]
    markup: list = []
    commands = [("view", "edit"), ("delete", "delete"), ("duplicate", "duplicate")]
    if not close:
        commands.append(("export", "export"))
    for command, text in commands:
        if keys.get(command):
            markup += [
                ("editor key", format_key(keys[command][0], glyphs)),
                ("editor hint", f" {text}  "),
            ]
    if close:
        markup += [("editor key", "esc"), ("editor hint", " close")]
    return markup


def _glyphs(conf) -> Glyphs:
    return UNICODE if conf.get("locale", {}).get("unicode_symbols", True) else ASCII


def deletion_row(conf, scope: str, glyphs: Glyphs) -> urwid.Widget:
    """`✕ marked for deletion (this one) · d undo`"""
    markup: list = [
        ("details deleted", f"{'✕' if glyphs is UNICODE else 'x'} marked for deletion ({scope})")
    ]
    keys = conf["keybindings"].get("delete")
    if keys:
        markup += [
            ("details dim", " · "),
            ("editor key", format_key(keys[0], glyphs)),
            ("details dim", " undo"),
        ]
    return urwid.Text(markup)


def card_rows(
    conf,
    event,
    today: dt.date | None = None,
    headline: bool = False,
    deleted: str | None = None,
) -> list:
    """
    :param deleted: the scope of the event's deletion mark (e.g. "this one")
    """
    glyphs = _glyphs(conf)
    rows = details_rows(event, conf, glyphs, today, headline=headline, rule=False)
    if headline:
        rows = rows[1:]  # no blank row at the top of the card
    if deleted:
        rows.insert(2 if headline else 1, deletion_row(conf, deleted, glyphs))
    # the keys are in the footer (see ClassicView.footer_hints)
    return rows


def event_card(
    conf, event, today: dt.date | None = None, deleted: str | None = None
) -> urwid.Widget:
    """the details of `event` in an accent framed card (a flow widget), for
    right under the event's row in the list (so without its title)"""
    from .floating import float_box

    rows = card_rows(conf, event, today, deleted=deleted)
    return float_box("", urwid.Pile(rows), "", _glyphs(conf))


def event_column(
    conf, event, today: dt.date | None = None, deleted: str | None = None
) -> urwid.Widget:
    """the details of `event` in their own column (a box widget) next to the list"""
    from .floating import float_box

    rows = card_rows(conf, event, today, headline=True, deleted=deleted)
    body = urwid.Filler(urwid.Pile(rows), valign="top")
    return float_box("Event", body, "esc", _glyphs(conf))


class EventDetails(urwid.WidgetWrap):
    """A (box) widget showing one Event()'s details"""

    def __init__(self, conf, event, collection=None, today: dt.date | None = None) -> None:
        self._conf = conf
        self.collection = collection
        self.event = event
        glyphs = _glyphs(conf)
        body = urwid.Padding(urwid.Pile(details_rows(event, conf, glyphs, today)), left=1, right=1)
        footer = urwid.Padding(
            urwid.Pile([section_rule(None, glyphs), urwid.Text(key_hints(conf, glyphs))]),
            left=1,
            right=1,
        )
        super().__init__(urwid.Frame(urwid.Filler(body, valign="top"), footer=footer))
