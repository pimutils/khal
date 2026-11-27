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

"""Floating boxes for ikhal: dialogs with one-key answers, help, log.

All of them are a `float_box()` (an accent-coloured frame on the normal
background with the title and a hint in the top border), opened with
`Window.open_floating()`, which draws the screen behind them with the
greyscale `backdrop` palette twins (see `khal.ui.colors.add_backdrop_twins`).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass

import urwid

from .editor_layout import UNICODE, ActionButton, Card, FocusRow, Glyphs, format_key
from .widgets import NPile


def float_box(title: str, body: urwid.Widget, hint: str = "", glyphs: Glyphs = UNICODE) -> Card:
    """the frame of every floating box"""
    return Card(
        title,
        urwid.Padding(body, left=1, right=1),
        glyphs,
        hint=hint,
        attr="float border",
        focus_attr="float border",
        title_attr="float title",
        hint_attr="float hint",
    )


@dataclass
class Answer:
    """one answer of a ChoiceDialog, selected by pressing `key`"""

    key: str
    label: str
    callback: Callable[[], None]
    detail: str = ""


class ChoiceDialog(urwid.WidgetWrap):
    """a question with one answer per row, each with a mnemonic key in front

    The keys work directly, ↑↓ and enter work as well, esc calls `on_cancel`.
    The first answer has the focus (make it the safe choice).
    """

    def __init__(
        self,
        title: str,
        question: str,
        answers: list[Answer],
        on_cancel: Callable[[], None],
        description: str = "",
        glyphs: Glyphs = UNICODE,
    ) -> None:
        self.answers = answers
        self._on_cancel = on_cancel
        # the question lines up with the answers' keys
        rows: list[urwid.Widget] = [
            urwid.Divider(),
            urwid.Padding(urwid.Text(("float headline", question)), left=1),
        ]
        if description:
            rows.append(urwid.Padding(urwid.Text(("float text", description)), left=1))
        rows.append(urwid.Divider())
        key_width = max(len(answer.key) for answer in answers) + 2
        # the details (e.g. the date) in one column after the longest label
        label_width = max(len(answer.label) for answer in answers)
        for answer in answers:
            button = ActionButton(
                answer.label,
                lambda _, answer=answer: answer.callback(),
                attr="float answer",
                focus_attr="float answer focus",
            )
            content = urwid.Columns(
                [
                    (button.width, button),
                    (label_width - button.width + 2, urwid.Text("")),
                    urwid.Text(("float dim", answer.detail)),
                ],
            )
            rows.append(
                FocusRow(
                    answer.key,
                    content,
                    label=("float key", answer.key),
                    label_width=key_width,
                    margin=0,
                    glyphs=glyphs,
                )
            )
        rows.append(urwid.Divider())
        arrows = "↑↓ enter" if glyphs is UNICODE else "up/down enter"
        rows.append(urwid.Text(("float dim", f"  {arrows} also work · esc cancel")))
        rows.append(urwid.Divider())
        self.pile = NPile(rows)
        self.pile.focus_position = rows.index(
            next(row for row in rows if isinstance(row, FocusRow))
        )
        self.width = (
            max(
                len(question) + 1,
                len(description) + 1,
                *(key_width + 4 + len(a.label) + 2 + len(a.detail) for a in answers),
            )
            + 6
        )
        super().__init__(float_box(title, self.pile, "esc cancel", glyphs))

    def keypress(self, size, key):
        for answer in self.answers:
            if key == answer.key:
                answer.callback()
                return None
        if key == "esc":
            self._on_cancel()
            return None
        return super().keypress(size, key)


# -- help


@dataclass(frozen=True)
class HelpEntry:
    keys: tuple[str, ...]
    description: str


# command name in [keybindings] -> human description, grouped
HELP_GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "Move",
        (
            ("up", "up"),
            ("down", "down"),
            ("left", "left, previous day"),
            ("right", "right, next day"),
            ("today", "today"),
            ("next_month", "next month"),
            ("prev_month", "previous month"),
            ("next_year", "next year"),
            ("prev_year", "previous year"),
            ("goto_date", "go to a date"),
            ("mark", "mark a range"),
            ("other", "other end of range"),
        ),
    ),
    (
        "Events",
        (
            ("new", "new event"),
            ("view", "open, again: edit"),
            ("delete", "delete, again: undo"),
            ("undo_all_deletions", "undo all deletions"),
            ("duplicate", "duplicate"),
            ("export", "export as .ics"),
            ("external_edit", "edit in $EDITOR"),
        ),
    ),
    (
        "View",
        (
            ("switch_view", "next view"),
            ("toggle_calendars", "show/hide calendars"),
            ("search", "search"),
            ("log", "log"),
            ("help", "help"),
            ("quit", "quit"),
        ),
    ),
    (
        "Editor",
        (
            ("tab", "next field"),
            ("shift tab", "previous field"),
            ("save", "save"),
            ("esc", "back, asks if unsaved"),
            ("other_column", "editor / events"),
            ("switch_view_editor", "next view of the events"),
            ("editor_narrower", "narrower editor"),
            ("editor_wider", "wider editor"),
        ),
    ),
)
# keys that are not configurable
FIXED_KEYS = {"help": ["?", "f1"], "tab": ["tab"], "shift tab": ["shift tab"], "esc": ["esc"]}


def help_groups(
    keybindings: dict[str, list[str]],
    extra: list[tuple[str, list[tuple[str, list[str], str]]]] = (),  # type: ignore[assignment]
) -> list[tuple[str, list[HelpEntry]]]:
    """the groups shown in the help, `extra` are the sections plugins provide"""
    groups = []
    for title, commands in HELP_GROUPS:
        entries = []
        for command, description in commands:
            keys = keybindings.get(command, FIXED_KEYS.get(command))
            if keys:
                entries.append(HelpEntry(tuple(keys), description))
        groups.append((title, entries))
    for title, items in extra:
        groups.append(
            (
                title,
                [
                    HelpEntry(tuple(keys), description or command)
                    for command, keys, description in items
                ],
            )
        )
    return groups


class HelpView(urwid.WidgetWrap):
    """the keys, grouped, in one or two columns (depending on the width)

    A box widget that scrolls with ↑↓ (and page up/down).
    """

    KEY_WIDTH = 10
    COLUMN_WIDTH = 38

    def __init__(self, groups: list[tuple[str, list[HelpEntry]]], glyphs: Glyphs = UNICODE) -> None:
        self._groups = groups
        self._glyphs = glyphs
        self._maxcol: int | None = None
        self._walker = urwid.SimpleListWalker([])
        self.listbox = urwid.ListBox(self._walker)
        super().__init__(self.listbox)

    def _group_lines(self, title: str, entries: list[HelpEntry]) -> list:
        lines: list = [[("float title", title)]]
        for entry in entries:
            # letters before named keys: `k ↑`
            ordered = sorted(entry.keys, key=lambda key: len(key.strip()) != 1)
            keys = " ".join(format_key(key, self._glyphs) for key in ordered[:2])
            keys = keys.ljust(self.KEY_WIDTH - 1)
            lines.append([" ", ("float key", keys), " ", ("float text", entry.description)])
        return lines

    @staticmethod
    def _split(blocks: list[list]) -> int:
        """how many blocks go into the left column (the columns as even as possible)"""
        heights = [len(block) + 1 for block in blocks]
        best, best_height = len(blocks), sum(heights)
        for split in range(1, len(blocks)):
            height = max(sum(heights[:split]), sum(heights[split:]))
            if height < best_height:
                best, best_height = split, height
        return best

    def _layout(self, maxcol: int) -> None:
        if maxcol == self._maxcol:
            return
        self._maxcol = maxcol
        blocks = [self._group_lines(title, entries) for title, entries in self._groups if entries]
        if maxcol >= 2 * self.COLUMN_WIDTH and len(blocks) > 1:
            # groups flow down the left column, then down the right one
            split = self._split(blocks)
            columns = [blocks[:split], blocks[split:]]
        else:
            columns = [blocks]
        flowed = []
        for column in columns:
            lines: list = []
            for block in column:
                lines += [*block, ""]
            flowed.append(lines)
        rows: list[urwid.Widget] = [urwid.Divider()]
        for index in range(max(len(lines) for lines in flowed)):
            cells = [
                urwid.Text(lines[index] if index < len(lines) else "", wrap="ellipsis")
                for lines in flowed
            ]
            rows.append(urwid.Columns(cells, dividechars=2))
        self._walker[:] = rows

    def selectable(self) -> bool:
        return True

    def render(self, size, focus=False):
        self._layout(size[0])
        return super().render(size, focus)

    def keypress(self, size, key):
        self._layout(size[0])
        key = {"k": "up", "j": "down"}.get(key, key)
        if key in ("up", "down", "page up", "page down"):
            self.listbox.keypress(size, key)
            return None
        return key


# -- plain language


WEEKDAY_NAMES = {
    "MO": "Mon",
    "TU": "Tue",
    "WE": "Wed",
    "TH": "Thu",
    "FR": "Fri",
    "SA": "Sat",
    "SU": "Sun",
}
ORDINALS = {1: "1st", 2: "2nd", 3: "3rd", -1: "last"}


FULL_WEEKDAYS = {
    "MO": "Monday", "TU": "Tuesday", "WE": "Wednesday", "TH": "Thursday",
    "FR": "Friday", "SA": "Saturday", "SU": "Sunday",
}  # fmt: skip
UNDERSTOOD_PARTS = {"FREQ", "INTERVAL", "BYDAY", "BYMONTHDAY", "BYMONTH", "UNTIL", "COUNT", "WKST"}


def _ordinal(number: int) -> str:
    if number == -1:
        return "last"
    if number < 0:
        return f"{_ordinal(-number)} to last"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10 if number not in (11, 12, 13) else 0)
    return f"{number}{suffix or 'th'}"


def _nth_weekdays(byday: list[str]) -> str:
    parts = []
    for day in byday:
        number = day[:-2]
        name = FULL_WEEKDAYS.get(day[-2:], day)
        parts.append(f"{_ordinal(int(number))} {name}" if number not in ("", "+") else name)
    return " and ".join(parts)


def describe_rrule(rrule, start, timeformat: str = "%H:%M") -> str:
    """`Repeats every weekday at 09:00.` and the like

    Parts this can't phrase are appended as they are in the RRULE.
    """
    if not rrule:
        return ""
    freq = str(rrule.get("FREQ", ["?"])[0]).lower()
    interval = int(rrule.get("INTERVAL", [1])[0])
    unit = {"daily": "day", "weekly": "week", "monthly": "month", "yearly": "year"}.get(freq)
    if unit is None:
        return f"Repeats ({_raw(rrule)})."
    text = f"every {unit}" if interval == 1 else f"every {interval} {unit}s"
    byday = [str(day) for day in rrule.get("BYDAY", [])]
    if byday and freq == "weekly":
        days = [day[-2:] for day in byday]
        if interval == 1 and sorted(days) == sorted(["MO", "TU", "WE", "TH", "FR"]):
            text = "every weekday"
        else:
            text += " on " + ", ".join(WEEKDAY_NAMES.get(day, day) for day in days)
    elif byday and freq in ("monthly", "yearly"):
        if len(byday) == 1 and freq == "monthly" and byday[0][:-2] not in ("", "+"):
            number = int(byday[0][:-2])
            text += f" on the {ORDINALS.get(number, _ordinal(number))} "
            text += WEEKDAY_NAMES.get(byday[0][-2:], byday[0])
        else:
            prefix = "" if interval == 1 else f"every {interval} {unit}s: "
            text = f"{prefix}every {_nth_weekdays(byday)} of the {unit}"
    monthdays = rrule.get("BYMONTHDAY", [])
    if monthdays:
        text += " on the " + ", ".join(_ordinal(int(day)) for day in monthdays)
        if any(int(day) < 0 for day in monthdays):
            text += " day"
    months = rrule.get("BYMONTH", [])
    if months:
        text += " in " + ", ".join(dt.date(2000, int(m), 1).strftime("%b") for m in months)
    if isinstance(start, dt.datetime):
        text += f" at {start.strftime(timeformat)}"
    if "UNTIL" in rrule:
        until = rrule["UNTIL"][0]
        text += f" until {until:%Y-%m-%d}"
    elif "COUNT" in rrule:
        text += f", {rrule['COUNT'][0]} times"
    unknown = {key: value for key, value in rrule.items() if key.upper() not in UNDERSTOOD_PARTS}
    if unknown:
        text += f" ({_raw(unknown)})"
    return f"Repeats {text}."


def _raw(rrule) -> str:
    import icalendar

    try:
        return icalendar.vRecur(rrule).to_ical().decode()
    except Exception:
        return str(dict(rrule))


# -- the log


@dataclass
class LogEntry:
    """one entry of ikhal's log (see `Window.log`)"""

    time: dt.datetime
    level: int  # logging.DEBUG, INFO, WARNING, ERROR, CRITICAL
    message: str


# level (at least) -> tag, palette attribute
LOG_LEVELS = ((40, "error", "log error"), (30, "warn", "log warning"), (20, "info", "log info"))
LOG_DEBUG = ("debug", "log debug")
TAG_WIDTH = 6


def log_tag(level: int) -> tuple[str, str]:
    for minimum, tag, attr in LOG_LEVELS:
        if level >= minimum:
            return tag, attr
    return LOG_DEBUG


class LogView(urwid.WidgetWrap):
    """ikhal's log: one row per entry (time, level, the message with a
    hanging indent), the newest at the bottom and in view

    A box widget that scrolls with ↑↓/j k, page up/down, home/end.
    """

    def __init__(self, entries: list[LogEntry]) -> None:
        rows: list[urwid.Widget] = []
        for entry in entries:
            tag, attr = log_tag(entry.level)
            rows.append(
                urwid.Columns(
                    [
                        (8, urwid.Text(("log time", entry.time.strftime("%H:%M:%S")))),
                        (TAG_WIDTH, urwid.Text((attr, tag))),
                        urwid.Text(("log text", entry.message)),
                    ],
                    dividechars=1,
                )
            )
        if not rows:
            rows.append(urwid.Text(("log time", "nothing logged yet")))
        self._walker = urwid.SimpleFocusListWalker(rows)
        self.listbox = urwid.ListBox(self._walker)
        self._walker.set_focus(len(rows) - 1)
        self.listbox.set_focus_valign("bottom")
        super().__init__(self.listbox)

    def selectable(self) -> bool:
        return True

    def keypress(self, size, key):
        key = {"k": "up", "j": "down", "home": "home", "end": "end"}.get(key, key)
        if key in ("home", "end"):
            self._walker.set_focus(0 if key == "home" else len(self._walker) - 1)
            self.listbox.set_focus_valign("top" if key == "home" else "bottom")
            return None
        if key in ("up", "down", "page up", "page down"):
            self.listbox.keypress(size, key)
            return None
        return key
