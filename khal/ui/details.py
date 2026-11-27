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
    relative_day,
    section_rule,
    summary_line,
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


def details_rows(
    event,
    conf,
    glyphs: Glyphs,
    today: dt.date | None = None,
    headline: bool = True,
    rule: bool = True,
) -> list[urwid.Widget]:
    """the rows of the details view (without the key hints)

    :param headline: start with the event's title (not needed right under
        the event's row in the list)
    :param rule: a rule below the title and summary line
    """

    def row(field_id: str | None, label: str, value) -> urwid.Widget:
        if field_id is not None:
            label = FIELD[field_id].noun or label
        return urwid.Columns(
            [(LABEL_WIDTH, urwid.Text(("details label", label))), urwid.Text(value)]
        )

    start, end = event.start_local, event.end_local
    rows: list[urwid.Widget] = []
    if headline:
        rows += [
            urwid.Divider(),
            urwid.Text(("details headline", event.summary or "(no title)")),
        ]
    rows.append(
        urwid.Text(
            summary_line(
                event.calendar,
                start,
                end,
                event.allday,
                conf,
                glyphs,
                [relative_day(_day(start), today)],
                attr="details dim",
                compact=True,
            )
        )
    )
    if rule:
        rows.append(section_rule(None, glyphs))
    rows.append(urwid.Divider())
    if event.location:
        rows.append(row("location", "where", ("details text", event.location)))
    attendees = event.attendees_status
    if attendees:
        rows.append(row("attendees", "who", attendee_markup(attendees, glyphs)))
    if event.organizer:
        rows.append(row(None, "by", ("details text", event.organizer)))
    for index, (delta, _) in enumerate(event.alarms):
        rows.append(row(None, "alarm" if index == 0 else "", ("details text", format_alarm(delta))))
    if event.recurring:
        rule = describe_rrule(event.recurobject, start, conf["locale"]["timeformat"])
        rule = rule.removeprefix("Repeats ").rstrip(".") if rule else "repeats"
        rows.append(row(None, "repeat", ("details text", rule)))
    if event.categories:
        rows.append(row("categories", "tags", ("details text", event.categories)))
    if event.url:
        rows.append(row("url", "link", ("details link", event.url)))
    if event.description:
        rows.append(urwid.Divider())
        rows.extend(urwid.Text(("details text", line)) for line in event.description.splitlines())
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
    return rows + [urwid.Divider(), urwid.Text(key_hints(conf, glyphs, close=True))]


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
