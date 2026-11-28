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

from __future__ import annotations

import datetime as dt
import logging
import signal
import sys
from enum import IntEnum
from typing import Any, Literal, NamedTuple, Protocol, runtime_checkable

import click
import urwid

from khal import plugins, utils
from khal.khalendar import CalendarCollection
from khal.khalendar.exceptions import FatalError, ReadOnlyCalendarError
from khal.parse_datetime import timedelta2str

from . import colors
from .agenda import (
    BAR,
    DAY_LABEL_WIDTH,
    DEFAULT_HEADER_FORMAT,
    SHORT_HEADER_FORMATS,
    AgendaStyle,
    agenda_style,
    align_tab,
    choose_density,
    day_attributes,
    event_attributes,
    event_day,
    format_free,
    format_header,
    free_gaps,
    header_attributes,
    header_markup,
    list_order,
)
from .base import Pane, Window
from .calendars import CalendarsBox
from .calendarwidget import CalendarWidget, DayStyle
from .details import EventDetails, event_card, event_column
from .editing import EditingScreen
from .editor import EventEditor, ExportDialog, open_export_dialog  # noqa: F401
from .editor_layout import ASCII, UNICODE, format_key
from .finder import Finder
from .floating import Answer, LogEntry, describe_rrule
from .navigation import MONTH_STEPS, parse_goto, shift_months
from .widgets import CAttrMap, ListBoxSize, NColumns, PopUpTarget, Size, find_child, linebox

logger = logging.getLogger("khal")

#  Overview of how this all meant to fit together:
#
#   ┌──ClassicView(Pane)────────────────────────────────────────┐
#   │                                                           │
#   │ ┌─CalendarWidget──┐  ┌────EventColumn───────────────────┐ │
#   │ │                 │  │                                  │ │
#   │ │                 │  │ ┌─DListBox─────────────────────┐ │ │
#   │ │                 │  │ │                              │ │ │
#   │ │                 │  │ │ ┌─DayWalker────────────────┐ │ │ │
#   │ │                 │  │ │ │                          │ │ │ │
#   │ │                 │  │ │ │ ┌─BoxAdapter───────────┐ │ │ │ │
#   │ │                 │  │ │ │ │                      │ │ │ │ │
#   │ │                 │  │ │ │ │ ┌─DateListBox──────┐ │ │ │ │ │
#   │ │                 │  │ │ │ │ │ DateHeader       │ │ │ │ │ │
#   │ │                 │  │ │ │ │ │ U_Event          │ │ │ │ │ │
#   │ │                 │  │ │ │ │ │  ...             │ │ │ │ │ │
#   │ │                 │  │ │ │ │ │ U_Event          │ │ │ │ │ │
#   │ │                 │  │ │ │ │ └──────────────────┘ │ │ │ │ │
#   │ │                 │  │ │ │ └──────────────────────┘ │ │ │ │
#   │ │                 │  │ │ │       ...                │ │ │ │
#   │ │                 │  │ │ │ ┌─BoxAdapter───────────┐ │ │ │ │
#   │ │                 │  │ │ │ │                      │ │ │ │ │
#   │ │                 │  │ │ │ │ ┌─DateListBox──────┐ │ │ │ │ │
#   │ │                 │  │ │ │ │ │ DateHeader       │ │ │ │ │ │
#   │ │                 │  │ │ │ │ │ U_Event          │ │ │ │ │ │
#   │ │                 │  │ │ │ │ │  ...             │ │ │ │ │ │
#   │ │                 │  │ │ │ │ │ U_Event          │ │ │ │ │ │
#   │ │                 │  │ │ │ │ └──────────────────┘ │ │ │ │ │
#   │ │                 │  │ │ │ └──────────────────────┘ │ │ │ │
#   │ │                 │  │ │ └──────────────────────────┘ │ │ │
#   │ │                 │  │ └──────────────────────────────┘ │ │
#   │ └─────────────────┘  └──────────────────────────────────┘ │
#   └───────────────────────────────────────────────────────────┘


@runtime_checkable
class EventView(Protocol):
    """Interface of the widget shown in ikhal's right column

    The built-in implementation is :class:`DListBox`, plugins can provide
    alternative implementations via the ``khal.views`` entry point group, see
    :mod:`khal.plugins`. Implementations must be urwid box widgets and should
    call ``pane.calendar.base_widget.set_focus_date(day)`` when they move the
    focus to another day on their own.
    """

    @property
    def focus_event(self) -> U_Event | None:
        """the event currently in focus (or None)"""
        ...

    @property
    def current_date(self) -> dt.date:
        """the date currently in focus"""
        ...

    def ensure_date(self, day: dt.date) -> None:
        """bring `day` into view and focus it"""
        ...

    def update_range(
        self, start: dt.date | None, end: dt.date | None, everything: bool = False
    ) -> None:
        """reload events between `start` and `end` (inclusive), or all if
        `everything` (then `start` and `end` may be None)"""
        ...

    def refresh_titles(self, start: dt.date, end: dt.date, everything: bool) -> None:
        """re-render event titles (e.g. after an event was marked as deleted)"""
        ...

    def update_date_line(self) -> None:
        """called when the current date changed (e.g., at midnight)"""
        ...

    # Optionally, views may implement
    #
    #     @classmethod
    #     def keybindings_help(cls, conf) -> list[tuple[str, list[str], str]]
    #
    # returning (command, keys, description) tuples, shown in ikhal's help
    # (`?`), and
    #
    #     def new_event_range(self) -> tuple[dt.date, dt.date] | None
    #
    # which gets called when the user wants to create a new event. Returning two
    # datetimes creates a timed event with that start and end, two dates an
    # all-day event (end date inclusive), and None falls back to the default
    # (focused date, next full hour).


# the optional parts of an EventView (see the comment in EventView), each as
# its own protocol, so the window can check for them


@runtime_checkable
class HasNewEventRange(Protocol):
    def new_event_range(self) -> tuple[dt.date, dt.date] | None:
        """start and end of a new event (None: the focused date)"""
        ...


@runtime_checkable
class HandlesViewKey(Protocol):
    def handles_view_key(self) -> bool:
        """True: the view uses the `view` key (enter) itself right now"""
        ...


@runtime_checkable
class HasPaneTitle(Protocol):
    """the title of the right column's frame (`Agenda`, `Week 48 · Mon–Fri`)"""

    @property
    def pane_title(self) -> str: ...


@runtime_checkable
class HasPaneStatus(Protocol):
    """the status at the right of the right column's frame (`6 days`)"""

    @property
    def pane_status(self) -> str: ...


# (tabs in the header line: a view class may name its `tabs`, an instance
# its `active_tab`, see ClassicView.view_tabs)


class DeletionType(IntEnum):
    ALL = 0
    INSTANCES = 1
    FOLLOWING = 2  # this instance and all following ones


def deletion_scope(status: DeletionType) -> str:
    """what a deletion mark deletes, in words (shown instead of the duration)"""
    return {
        DeletionType.ALL: "deleted",
        DeletionType.INSTANCES: "this one",
        DeletionType.FOLLOWING: "this & following",
    }[status]


class DateConversionError(Exception):
    pass


class SelectableText(urwid.Text):
    def selectable(self) -> bool:
        return True

    def keypress(self, size: Size, key: str) -> str | None:
        return key

    def get_cursor_coords(self, size: tuple[int]) -> tuple[int, int]:
        return 0, 0

    def render(self, size, focus=False):
        canv = super().render(size, focus)
        if focus:
            canv = urwid.CompositeCanvas(canv)
            canv.cursor = 0, 0
        return canv


# columns right of a styled event (the margin of the list and one blank, so
# durations don't touch the frame)
RIGHT_MARGIN = 2


class DateHeader(SelectableText):
    def __init__(
        self, day: dt.date, dateformat: str, conf, style: AgendaStyle | None = None
    ) -> None:
        """
        :param day: the date that is represented by this DateHeader instance
        :param dateformat: format to print `day` in
        :param style: with a `day_format`, that is used instead of the classic
            "Today (Thursday, ...)"; `rule` draws the header as a rule
        """
        self._day = day
        self._dateformat = dateformat
        self._conf = conf
        self._style = style
        self._label = ""
        self._width: int | None = None
        super().__init__("", wrap="clip")
        self.update_date_line()

    def update_date_line(self) -> None:
        """update self, so that the timedelta is accurate

        to be called after a date change
        """
        style = self._style
        if style is not None and style.day_format:
            try:
                self._label = style.day_format.format(**day_attributes(self._day, self._conf))
            except (KeyError, ValueError, IndexError):
                self._label = style.day_format
        else:
            self._label = self.relative_day(self._day, self._dateformat)
        self._width = None
        if style is not None and not style.classic:
            self.set_text(" " + self._label)  # the margin of the events
        else:
            self.set_text(self._label)

    # the day is the focused one (set by DateListBox before rendering)
    day_focused = False

    def render(self, size, focus=False):
        style = self._style
        state = (size[0], focus, self.day_focused)
        if style is not None and style.day_header == "rule" and state != self._width:
            self._width = state
            unicode_symbols = self._conf["locale"].get("unicode_symbols", True)
            rule = "─" if unicode_symbols else "-"
            # one column margin on either side, like the events; focused like
            # a focused event: the ▌ marker and the day in the accent colour
            label_width = urwid.calc_width(self._label, 0, len(self._label))
            fill = rule * max(0, size[0] - 4 - label_width - 2)
            marker = ("editor marker", "▌" if unicode_symbols else ">") if focus else " "
            if focus or self.day_focused:
                self.set_text(
                    [
                        marker,
                        ("agenda rule", f"{rule * 2} "),
                        ("agenda day focus", self._label),
                        ("agenda rule", f" {fill}"),
                        " ",
                    ]
                )
            else:
                self.set_text([" ", f"{rule * 2} {self._label} {fill} "])
        return super().render(size, focus)

    def relative_day(self, day: dt.date, dtformat: str) -> str:
        """convert day into a string with its weekday and relative distance to today

        :param day: day to be converted
        :param dtformat: the format day is to be printed in, passed to strftime
        """

        weekday = day.strftime("%A")
        daystr = day.strftime(dtformat)
        if day == dt.date.today():
            return f"Today ({weekday}, {daystr})"
        elif day == dt.date.today() + dt.timedelta(days=1):
            return f"Tomorrow ({weekday}, {daystr})"
        elif day == dt.date.today() - dt.timedelta(days=1):
            return f"Yesterday ({weekday}, {daystr})"

        approx_delta = utils.relative_timedelta_str(day)

        return f"{weekday}, {daystr} ({approx_delta})"

    def keypress(self, size: Size, key: str) -> str | None:
        binds = self._conf["keybindings"]
        if key in binds["left"]:
            key = "left"
        elif key in binds["up"]:
            key = "up"
        elif key in binds["right"]:
            key = "right"
        elif key in binds["down"]:
            key = "down"
        return key


# event formats that failed (logged once)
_FORMAT_ERRORS: set[str] = set()


class U_Event(urwid.Text):
    def __init__(
        self,
        event,
        conf,
        delete_status,
        this_date=None,
        relative=True,
        style: AgendaStyle | None = None,
        first_of_day: bool = False,
    ) -> None:
        """representation of an event in EventList

        :param event: the encapsulated event
        :type event: khal.event.Event
        :param style: how the list looks (None or classic: `agenda_event_format`)
        :param first_of_day: this is the day's first event (`{day-label}`)
        """
        self.style = style
        self.first_of_day = first_of_day
        self._formatted: str | None = None  # text with \t, laid out in render()
        self._width: tuple[int, bool] | None = None  # (width, focus) of the layout
        if relative:
            if isinstance(this_date, dt.datetime) or not isinstance(this_date, dt.date):
                raise ValueError(
                    f"`this_date` is of type `{type(this_date)}`, should be `datetime.date`"
                )
        self.event = event
        self.delete_status = delete_status
        self.this_date = this_date
        self._conf = conf
        self.relative = relative
        super().__init__("", wrap="clip")
        self.set_title()

    def get_cursor_coords(self, size) -> tuple[int, int]:
        return 0, 0

    def render(self, size, focus=False):
        self._align(size[0], focus)
        canv = super().render(size, focus)
        if focus:
            canv = urwid.CompositeCanvas(canv)
            canv.cursor = 0, 0
        return canv

    def rows(self, size, focus=False):
        self._align(size[0], focus)
        return super().rows(size, focus)

    @property
    def row_count(self) -> int:
        """number of rows (lines) of this event"""
        if self._formatted is None:
            return 1
        return self._formatted.count("\n") + 1

    RIGHT_MARGIN = RIGHT_MARGIN

    def _align(self, width: int, focus: bool = False) -> None:
        """right-align `{tab}` parts and draw the bar (styled events only)

        A styled event is `[margin][mark][bar] [text]  `: the mark column
        shows the deletion mark (D, d, f) or, while focused, the focus marker
        ▌; dense events have their day label in front of the bar instead.
        """
        if self._formatted is None or (width, focus) == self._width:
            return
        self._width = (width, focus)
        unicode_symbols = self._conf["locale"].get("unicode_symbols", True)
        text = self._formatted
        mark: str | tuple[str, str] = self._mark[:1]
        if not mark and focus:
            mark = ("editor marker", "▌" if unicode_symbols else ">")
        mark = mark or " "
        bar = self.style is not None and self.style.event_color == "bar"
        dense = self.style is not None and self.style.density == "dense"
        # [margin][mark] then the formatted text, which has `{bar}` (BAR)
        # where the calendar's bar goes; dense: the mark is the margin
        prefix = 1 if dense else 2
        deleted = getattr(self, "deleted", None)
        if deleted is not None:
            # the scope instead of whatever was right-aligned, only on the first row
            lines = [line.partition("\t")[0] for line in text.split("\n")]
            lines[0] += "\t" + deletion_scope(deleted)
            text = "\n".join(lines)
        text = align_tab(
            text, max(1, width - prefix - self.RIGHT_MARGIN), "…" if unicode_symbols else "~"
        )
        markup: list = []
        suffix = " focus" if focus else ""
        if deleted is not None:
            bar_glyph: tuple | str = (
                "agenda deleted mark" + suffix,
                "✕" if unicode_symbols else "x",
            )
        elif bar and self.event.allday:
            # a marker of their own: bars of one calendar on consecutive rows
            # would look like one event running across the timed ones below
            bar_glyph = (
                "calendar " + self.event.calendar + " mark",
                "■" if unicode_symbols else "#",
            )
        elif bar:
            bar_glyph = (
                "calendar " + self.event.calendar + " mark",
                "▍" if unicode_symbols else "|",
            )
        else:
            bar_glyph = " "
        for index, line in enumerate(text.split("\n")):
            if index:
                markup.append("\n")
            row_mark = mark if index == 0 else " "
            markup += [row_mark] if dense else [" ", row_mark]
            scope = deletion_scope(deleted) if deleted is not None and index == 0 else ""
            body = line[: len(line) - len(scope)] if scope else line
            for number, part in enumerate(body.split(BAR)):
                if number:
                    markup.append(bar_glyph)
                if deleted is None or not part.strip():
                    markup.append(part)
                    continue
                # struck through: the text, not the blanks around it
                stripped = part.strip()
                lead = part[: len(part) - len(part.lstrip())]
                trail = part[len(part.rstrip()) :]
                markup += [lead, ("agenda deleted" + suffix, stripped), trail]
            if scope:
                markup.append(("agenda deleted scope" + suffix, scope))
        self.set_text([part for part in markup if part])

    @classmethod
    def selectable(cls) -> bool:
        return True

    @property
    def uid(self) -> str:
        return self.event.calendar + "\n" + str(self.event.href) + "\n" + str(self.event.etag)

    @property
    def recuid(self) -> tuple[str, str]:
        return (self.uid, self.event.recurrence_id)

    def set_title(self, mark: str = " ") -> None:
        status = self.delete_status(self.recuid)
        self.deleted = status
        mark = {
            DeletionType.ALL: "D",
            DeletionType.INSTANCES: "d",
            DeletionType.FOLLOWING: "f",
            None: "",
        }[status]
        if self.relative and self.style is not None and not self.style.classic:
            # marked events: a red ✕ instead of the bar, struck through text
            # and the scope instead of the duration (see _align)
            self._mark = ""
            attributes = event_attributes(self.event, self.this_date, self.first_of_day, self._conf)
            if status is not None:
                for key in ("duration-short", "duration"):
                    attributes[key] = ""
                attributes["repeat-symbol"] = attributes["alarm-symbol"] = ""
            try:
                formatted = self.style.event_format.format(**attributes)
                # rows without anything (e.g. comfortable's second row of an
                # event without location, attendees, ...) are left out
                lines = formatted.split("\n")
                kept = [lines[0]] + [
                    line for line in lines[1:] if line.replace("\t", "").replace(BAR, "").strip()
                ]
                self._formatted = "\n".join(kept)
            except (KeyError, ValueError, IndexError) as error:
                self._formatted = f"{attributes.get('title', '')} [format error]"
                if self.style.event_format not in _FORMAT_ERRORS:  # log it once
                    _FORMAT_ERRORS.add(self.style.event_format)
                    logger.error(f"Invalid event format {self.style.event_format!r}: {error!r}")
            self._width = None
            self.set_text(self._formatted.replace("\t", " ").replace(BAR, " "))
            return
        if self.relative:
            format_ = self._conf["view"]["agenda_event_format"]
        else:
            format_ = self._conf["view"]["event_format"]
        formatter_ = utils.human_formatter(format_, colors=False)
        if self.this_date:
            date_ = self.this_date
        elif self.event.allday:
            date_ = self.event.start
        else:
            date_ = self.event.start.date()
        text = formatter_(self.event.attributes(date_, colors=False))
        if self._conf["locale"]["unicode_symbols"]:
            newline = " \N{LEFTWARDS ARROW WITH HOOK} "
        else:
            newline = " -- "

        self.set_text(mark + " " + text.replace("\n", newline))

    def keypress(self, size: Size, key: str) -> str | None:
        binds = self._conf["keybindings"]
        if key in binds["left"]:
            key = "left"
        elif key in binds["up"]:
            key = "up"
        elif key in binds["right"]:
            key = "right"
        elif key in binds["down"]:
            key = "down"
        return key


class EventListBox(urwid.ListBox):
    """Container for list of U_Events"""

    def __init__(
        self,
        *args,
        parent,
        conf,
        delete_status,
        toggle_delete_instance,
        toggle_delete_all,
        set_focus_date_callback=None,
        **kwargs,
    ) -> None:
        self._init: bool = True
        self.parent: ClassicView = parent
        self.delete_status = delete_status
        self.toggle_delete_instance = toggle_delete_instance
        self.toggle_delete_all = toggle_delete_all
        self._conf = conf
        self._old_focus = None
        self.set_focus_date_callback = set_focus_date_callback
        super().__init__(*args, **kwargs)

    def keypress(
        self,
        size: ListBoxSize,  # type: ignore[override]  # urwid.ListBox narrows Widget's size, too
        key: str,
    ) -> str | None:
        return super().keypress(size, key)

    @property
    def focus_event(self) -> U_Event | None:
        if self.focus is None:
            return None
        return find_child(self.focus, U_Event)

    def refresh_titles(self, min_date, max_date, everything):
        """Refresh only the currently focused event's title

        as we currently only use `EventListBox` in search and there we can only
        modify the currently focused event, no real implementation is needad at
        this time

        ignores all arguments
        """
        event = self.focus_event
        if event is not None:
            event.set_title()


class DListBox(EventListBox):
    """Container for a DayWalker"""

    # XXX unfortunate naming, there is also DateListBox

    def __init__(self, *args, **kwargs) -> None:
        dynamic_days = kwargs.pop("dynamic_days", True)
        super().__init__(*args, **kwargs)
        self._init = dynamic_days

    pane_title = "Agenda"
    _size: tuple[int, int] | None = None  # of the last render

    @property
    def days(self) -> DayWalker:
        """the walker (self.body, with its type)"""
        body = self.body
        assert isinstance(body, DayWalker)
        return body

    @property
    def pane_status(self) -> str:
        """the number of days in view (`6 days`)"""
        if self._size is None:
            return ""
        try:
            visible = self.calculate_visible(self._size, True)
        except (TypeError, IndexError, AttributeError):
            return ""
        if visible[0] is None or visible[1] is None or visible[2] is None:
            return ""
        _, top, bottom = visible
        days = 1 + len(top[1]) + len(bottom[1])
        return f"{days} day{'s' if days != 1 else ''}"

    def prepare(self, size: tuple[int, int]) -> None:
        """density and enough days for `size` (before rendering, also for
        the title in the frame, which is drawn first)"""
        self._auto_density(size)
        while not isinstance(self.days, StaticDayWalker) and "bottom" in self.ends_visible(size):
            self.days._autoextend()
        self._size = size

    def render(self, size, focus=False):
        if self._init:
            self._init = False
        if len(size) == 2:
            self.prepare(size)
        return super().render(size, focus)

    _density_size: tuple[int, int] | None = None

    def _auto_density(self, size) -> None:
        """`[view] density = auto`: the airiest density that shows the next
        `density_min_days` days fully (only re-evaluated when the size changes)"""
        view = self._conf["view"]
        if view.get("density", "classic") != "auto" or size == self._density_size:
            return
        if not isinstance(self.body, DayWalker) or not len(self.body):
            return
        self._density_size = size
        start = self.body.current_day
        days = int(view.get("density_min_days", 3) or 3)
        counts = [
            len(list(self.parent.collection.get_events_on(start + dt.timedelta(days=offset))))
            for offset in range(days)
        ]
        density = choose_density(self._conf, counts, size[1])
        style = agenda_style(self._conf, density)
        self.body.set_style(style)

    def clean(self):
        """reset event most recently in focus"""
        if self._old_focus is not None:
            try:
                old = self.body[self._old_focus]
                if old.original_widget.has_header:
                    old.body[0].set_attr_map({None: "date"})
            except (IndexError, AttributeError):
                # after reseting the EventList, the old focus might not exist
                pass

    def ensure_date(self, day: dt.date) -> None:
        """ensure an entry for `day` exists and bring it into focus"""
        try:
            self._old_focus = self.focus_position
        except IndexError:
            pass
        self.days.ensure_date(day)
        self.clean()

    def keypress(
        self,
        size: ListBoxSize,  # type: ignore[override]  # urwid.ListBox narrows Widget's size, too
        key: str,
    ) -> str | None:
        if key in self._conf["keybindings"]["up"]:
            key = "up"
        if key in self._conf["keybindings"]["down"]:
            key = "down"

        if key in self._conf["keybindings"]["today"]:
            self.parent.month_column.set_focus_date(dt.date.today())

        rval = super().keypress(size, key)
        self.clean()
        if key in ["up", "down"]:
            try:
                self._old_focus = self.focus_position
            except IndexError:
                pass
            day = self.days.current_day

            # we need to save DateListBox.selected_date and reset it later, because
            # calling CalendarWalker.set_focus_date() calls back into
            # DayWalker().update_by_date() which actually sets selected_date
            # that's why it's called callback hell...
            currently_selected_date = DateListBox.selected_date
            self.set_focus_date_callback(day)  # TODO convert to callback
            DateListBox.selected_date = currently_selected_date
        return rval

    @property
    def focus_event(self):
        return self.days.focus_event

    @property
    def current_date(self) -> dt.date:
        return self.days.current_day

    def refresh_titles(self, start, end, recurring):
        self.days.refresh_titles(start, end, recurring)

    def update_range(
        self, start: dt.date | None, end: dt.date | None, everything: bool = False
    ) -> None:
        if everything or start is None or end is None:
            start = self.days.first_date
            end = self.days.last_date
        self.days.update_range(start, end)

    def update_date_line(self):
        self.days.update_date_line()


class DayWalker(urwid.SimpleFocusListWalker["urwid.BoxAdapter[DateListBox]"]):
    """A list Walker that contains a list of DateListBox objects, each representing
    one day and associated events"""

    def __init__(self, this_date, eventcolumn, conf, collection, delete_status) -> None:
        self.eventcolumn = eventcolumn
        self._conf = conf
        self.delete_status = delete_status
        self._init = True
        self._last_day = this_date
        self._first_day = this_date
        self._collection = collection
        self.style: AgendaStyle = agenda_style(conf)
        self._now_index: dict[dt.date, int | None] = {}

        super().__init__([])
        self.ensure_date(this_date)

    def set_style(self, style: AgendaStyle) -> None:
        """change how the days look (and rebuild them)"""
        if style == self.style:
            return
        self.style = style
        if len(self):
            focus = self.focus
            for index in range(len(self)):
                self[index] = self._get_events(self[index].date)
            if focus is not None:
                super().set_focus(focus)

    def reset(self):
        """delete all events contained in this DayWalker"""
        self.clear()
        self._last_day = None
        self._first_day = None

    def ensure_date(self, day: dt.date) -> None:
        """make sure a DateListBox for `day` exists, update it and bring it into focus"""
        # TODO this function gets called twice on every date change, not necessary but
        # isn't very costly either
        if self.days_to_next_already_loaded(day) > 200:  # arbitrary number
            self.reset()
        item_no = None
        if len(self) == 0:
            pile = self._get_events(day)
            self.append(pile)
            self._last_day = day
            self._first_day = day
            item_no = 0
        while day < self[0].date:
            self._autoprepend()
            item_no = 0
        while day > self[-1].date:
            self._autoextend()
            item_no = len(self) - 1
        if item_no is None:
            item_no = (day - self[0].date).days

        assert self[item_no].date == day
        self[item_no].set_selected_date(day)
        self.set_focus(item_no)

    def days_to_next_already_loaded(self, day: dt.date) -> int:
        """return number of days until `day` is already loaded into the CalendarWidget"""
        if len(self) == 0:
            return 0
        elif self[0].date <= day <= self[-1].date:
            return 0
        elif day <= self[0].date:
            return (self[0].date - day).days
        elif self[-1].date <= day:
            return (day - self[-1].date).days
        else:
            raise ValueError("This should not happen")

    def update_events_ondate(self, day):
        """refresh the contents of the day's DateListBox"""
        offset = (day - self[0].date).days
        assert self[offset].date == day
        self[offset] = self._get_events(day)

    def refresh_titles(self, start: dt.date, end: dt.date, everything: bool):
        """refresh events' titles

        if `everything` is True, reset all titles, otherwise only
        those between `start` and `end`
        """
        start = start.date() if isinstance(start, dt.datetime) else start
        end = end.date() if isinstance(end, dt.datetime) else end

        if everything:
            start = self[0].date
            end = self[-1].date
        else:
            start = max(self[0].date, start)
            end = min(self[-1].date, end)

        offset = (start - self[0].date).days
        length = (end - start).days
        for index in range(offset, offset + length + 1):
            self[index].refresh_titles()

    def update_range(self, start: dt.date, end: dt.date, everything: bool = False):
        """refresh contents of all days between start and end (inclusive)"""
        start = start.date() if isinstance(start, dt.datetime) else start
        end = end.date() if isinstance(end, dt.datetime) else end

        if everything:
            start = self[0].date
            end = self[-1].date
        else:
            start = max(self[0].date, start)
            end = min(self[-1].date, end)

        day = start
        while day <= end:
            self.update_events_ondate(day)
            day += dt.timedelta(days=1)

    def update_date_line(self):
        for one in self:
            one.update_date_line()
        # move the "now" line (rebuilding today only when it has to move)
        today = dt.date.today()
        if self.style.now_line and len(self) and self[0].date <= today <= self[-1].date:
            index = self._now_position(today, self._events_on(today))
            if index != self._now_index.get(today):
                self.update_events_ondate(today)

    def set_focus(self, position):
        """set focus by item number"""
        while position >= len(self) - 1:
            self._autoextend()
        while position <= 0:
            self._autoprepend()
            position += 1
        return super().set_focus(position)

    def _autoextend(self):
        self._last_day += dt.timedelta(days=1)
        pile = self._get_events(self._last_day)
        self.append(pile)

    def _autoprepend(self):
        """prepend the day before the first day to ourself"""
        # we need to actively reset the last element's attribute, as their
        # render() method does not get called otherwise, and they would
        # be indicated as the currently selected date
        self[self.focus or 0].reset_style()
        self._first_day -= dt.timedelta(days=1)
        pile = self._get_events(self._first_day)
        self.insert(0, pile)

    def _events_on(self, day: dt.date) -> list:
        events = sorted(self._collection.get_events_on(day))
        if self.style.classic:
            return events
        # all-day and continuing events first; overnight events only on
        # their first day
        events = [event for event in events if event_day(event, day).shown]
        return sorted(events, key=lambda event: list_order(event, day))

    @staticmethod
    def _now_position(day: dt.date, events) -> int | None:
        """index of the first event that starts after now (today only)"""
        if day != dt.date.today():
            return None
        now = dt.datetime.now()
        for index, event in enumerate(events):
            if event.allday:
                continue
            start = event.start_local
            if start.date() == day and start.replace(tzinfo=None) > now:
                return index
        return len(events)

    def _get_events(self, day: dt.date) -> urwid.BoxAdapter[DateListBox]:
        """get all events on day, return a DateListBox of `U_Event()`s"""
        style = self.style
        self.events = self._events_on(day)
        unicode_symbols = self._conf["locale"].get("unicode_symbols", True)
        event_list: list[urwid.Widget] = []
        heights: list[int] = []
        has_header = not (style.day_header == "none" and self.events)
        if has_header:
            date_header = DateHeader(
                day=day,
                dateformat=self._conf["locale"]["longdateformat"],
                conf=self._conf,
                style=None if style.classic and not style.day_format else style,
            )
            event_list.append(urwid.AttrMap(date_header, "date"))
            heights.append(1)
            if style.blank_after_header and self.events:
                event_list.append(urwid.Divider())
                heights.append(1)
        gaps = (
            free_gaps(self.events, day, style.free_time, style.free_hours)
            if style.free_time
            else {}
        )
        now_index = self._now_position(day, self.events) if style.now_line else None
        self._now_index[day] = now_index
        now = dt.datetime.now()
        for index, event in enumerate(self.events):
            if index == now_index:
                event_list.append(self._now_line(now, unicode_symbols))
                heights.append(1)
            if index in gaps:
                dots = "┊" if unicode_symbols else ":"
                # between the time and the title column (see U_Event._align)
                indent = " " * (self._time_column() + 6)
                event_list.append(
                    urwid.Text(("agenda free", f"{indent}{dots} {format_free(gaps[index])}"))
                )
                heights.append(1)
            uevent = U_Event(
                event,
                conf=self._conf,
                this_date=day,
                delete_status=self.delete_status,
                style=style,
                first_of_day=index == 0,
            )
            event_list.append(
                urwid.AttrMap(uevent, self._event_attr(event, style, now), "reveal focus")
            )
            heights.append(uevent.row_count)
        if len(self.events) in gaps:  # free until the end of the hours
            dots = "┊" if unicode_symbols else ":"
            indent = " " * (self._time_column() + 6)
            free = format_free(gaps[len(self.events)])
            event_list.append(urwid.Text(("agenda free", f"{indent}{dots} {free}")))
            heights.append(1)
        if now_index is not None and now_index == len(self.events) and self.events:
            event_list.append(self._now_line(now, unicode_symbols))
            heights.append(1)
        if not event_list:  # dense, no events: still one row for the day
            date_header = DateHeader(
                day=day, dateformat=self._conf["locale"]["longdateformat"], conf=self._conf,
                style=style,
            )  # fmt: skip
            event_list.append(urwid.AttrMap(date_header, "date"))
            heights.append(1)
            has_header = True
        filled = self.events or len(self.events) in gaps
        height = sum(heights) + (1 if filled and style.day_header != "none" else 0)
        return urwid.BoxAdapter(
            DateListBox(urwid.SimpleFocusListWalker(event_list), date=day, has_header=has_header),
            max(height, 1),
        )

    @staticmethod
    def _event_attr(event, style: AgendaStyle, now: dt.datetime) -> str | None:
        """past events are dimmed, `bar` keeps the text in the normal colour"""
        if not style.classic:
            end = event.end_local
            if not isinstance(end, dt.datetime):
                end = dt.datetime.combine(end + dt.timedelta(days=1), dt.time())
            try:
                if end.replace(tzinfo=None) <= now:
                    return "agenda past"
            except TypeError:
                pass
        if style.event_color == "bar":
            return "agenda event"
        return "calendar " + event.calendar

    def _time_column(self) -> int:
        return self._time_column_of(self.style)

    @staticmethod
    def _time_column_of(style: AgendaStyle) -> int:
        """the column of the events' times (see U_Event._align)"""
        if style.density == "dense":
            return 1 + DAY_LABEL_WIDTH + 1
        return 4  # margin, mark, bar (blank with event_color = line), blank

    def _now_line(self, now: dt.datetime, unicode_symbols: bool) -> urwid.Widget:
        time = now.strftime(self._conf["locale"]["timeformat"])
        indent = self._time_column()
        return urwid.Columns(
            [
                ("pack", urwid.Text(("agenda now", " " * indent + time + " "))),
                urwid.AttrMap(urwid.Divider("━" if unicode_symbols else "="), "agenda now"),
                (1, urwid.Text("")),
            ]
        )

    def selectable(self) -> bool:
        """mark this widget as selectable"""
        return True

    @property
    def focus_event(self) -> U_Event | None:
        return self[self.focus or 0].original_widget.focus_event

    @property
    def current_day(self) -> dt.date:
        return self[self.focus or 0].original_widget.date

    @property
    def first_date(self) -> dt.date:
        return self[0].original_widget.date

    @property
    def last_date(self) -> dt.date:
        return self[-1].original_widget.date


class StaticDayWalker(DayWalker):
    """Only show events for a fixed number of days."""

    def ensure_date(self, day: dt.date) -> None:
        """make sure a DateListBox for `day` exists, update it and bring it into focus"""
        # TODO cache events for each day and update as needed
        num_days = max(1, self._conf["default"]["timedelta"].days)

        for delta in range(num_days):
            pile = self._get_events(day + dt.timedelta(days=delta))
            if len(self) <= delta:
                self.append(pile)
            else:
                self[delta] = pile
        assert self[0].date == day

    def update_events_ondate(self, day):
        """refresh the contents of the day's DateListBox"""
        self[0] = self._get_events(day)

    def refresh_titles(self, start: dt.date, end: dt.date, everything: bool) -> None:
        """refresh events' titles

        if `everything` is True, reset all titles, otherwise only
        those between `start` and `end`
        """
        # TODO: why are we not using the arguments?
        for one in self:
            one.refresh_titles()

    def update_range(self, start: dt.date, end: dt.date, everything: bool = False):
        """refresh contents of all days between start and end (inclusive)"""
        start = start.date() if isinstance(start, dt.datetime) else start
        end = end.date() if isinstance(end, dt.datetime) else end

        update = everything
        for one in self:
            if start <= one.date <= end:
                update = True
        if update:
            self.ensure_date(self[0].date)

    def set_focus(self, position):
        """set focus by item number"""
        return urwid.SimpleFocusListWalker.set_focus(self, position)


class DateListBox(urwid.ListBox):
    """A ListBox container containing all events for one specific date
    used with a SimpleFocusListWalker
    """

    selected_date = None

    def __init__(
        self, content: urwid.SimpleFocusListWalker, date: dt.date, has_header: bool = True
    ) -> None:
        self.date = date
        self.has_header = has_header
        self.items = content  # (self.body, with its type)
        super().__init__(content)

    def __repr__(self) -> str:
        return f"<DateListBox {self.date}>"

    __str__ = __repr__

    def render(self, size, focus=False):
        header = self.items[0].original_widget if self.has_header else None
        rule = isinstance(header, DateHeader) and header._style is not None
        rule = rule and header._style.day_header == "rule"
        if rule and header.day_focused != bool(focus):
            header.day_focused = bool(focus)
            header._invalidate()
        if not self.has_header:
            pass
        elif focus and rule:
            # the header shows the focus itself (see DateHeader.render)
            self.body[0].set_attr_map({None: "date header"})
        elif focus:
            self.body[0].set_attr_map({None: "date header focused"})
        elif DateListBox.selected_date == self.date:
            self.body[0].set_attr_map({None: "date header selected"})
        else:
            self.reset_style()
        return super().render(size, focus)

    def reset_style(self):
        if self.has_header:
            self.body[0].set_attr_map({None: "date header"})

    def set_selected_date(self, day: dt.date) -> None:
        """Mark `day` as selected

        :param day: day to mark as selected
        """
        DateListBox.selected_date = day
        if not self.has_header:
            return
        # we need to touch the title's content to make sure
        # that urwid re-renders the title
        title = find_child(self.items[0], DateHeader)
        title.set_text(title.get_text()[0])

    @property
    def focus_event(self) -> U_Event | None:
        widget = self.focus
        if widget is None or not isinstance(getattr(widget, "original_widget", None), U_Event):
            return None
        return find_child(widget, U_Event)

    def refresh_titles(self):
        """refresh the titles of all events"""
        for uevent in self.body:
            if isinstance(getattr(uevent, "original_widget", None), U_Event):
                uevent.original_widget.set_title()

    def update_date_line(self):
        """update the date text in the first line, e.g., if the current date changed"""
        if self.has_header:
            self.body[0].original_widget.update_date_line()


class EventColumn(urwid.WidgetWrap):
    """Container for list of events

    Handles modifying events, showing events' details and editing them
    """

    def __init__(self, elistbox, pane) -> None:
        self.pane = pane
        self._conf = pane._conf
        self.divider = urwid.Divider("─")
        self.editor = False
        self._last_focused_date: dt.date | None = None
        self._eventshown: tuple[str, str] | None = None
        self.event_width = int(self.pane._conf["view"]["event_view_weighting"])
        self.delete_status = pane.delete_status
        self.toggle_delete_all = pane.toggle_delete_all
        self.toggle_delete_instance = pane.toggle_delete_instance
        self.dlistbox: EventView = elistbox
        self.container = urwid.Pile([self.dlistbox])
        urwid.WidgetWrap.__init__(self, self.container)

    def set_view(self, view: EventView) -> None:
        """replace the widget showing the events (e.g. the list of events)"""
        date = self.focus_date
        self.clear_event_view()
        self._eventshown = None
        self.dlistbox = view
        assert isinstance(view, urwid.Widget)  # views are urwid box widgets
        self.container.contents[0] = (view, self.container.options())
        view.ensure_date(date)

    @property
    def focus_event(self) -> U_Event | None:
        """returns the event currently in focus"""
        return self.dlistbox.focus_event

    # how an event is viewed (enter in the list), see view()
    _inline: tuple[urwid.BoxAdapter, urwid.Widget, int] | None = None
    _size: tuple[int, int] = (80, 24)

    def view_mode(self) -> str:
        """`bottom` (below the list, `[view] event_view_always_visible`),
        `column` (next to the list, on wide screens, see `[view]
        event_view_column_from`) or `inline` (a card under the event's row)"""
        view = self._conf["view"]
        if view.get("event_view_always_visible"):
            return "bottom"
        column_from = int(view.get("event_view_column_from", 140) or 0)
        if column_from and self.pane.width >= column_from:
            return "column"
        return "inline"

    def view(self, event):
        """show the details of `event` (see view_mode())"""
        mode = self.view_mode()
        if mode == "column":
            self.pane.show_details(event, self._deleted_scope())
            self.pane._marks_changed()  # the footer shows the keys for the details
            return
        if mode == "inline" and self._view_inline(event):
            self.pane._marks_changed()
            return
        self.container.contents.append((self.divider, ("pack", None)))
        self.container.contents.append(
            (
                EventDisplay(self.pane._conf, event, collection=self.pane.collection),
                ("weight", self.event_width),
            )
        )

    def _view_inline(self, event) -> bool:
        """open the details as a card right under the event's row (list only)"""
        body = getattr(self.dlistbox, "body", None)
        if not isinstance(body, DayWalker) or body.focus is None:
            return False
        day = body[body.focus]
        datelist = day.original_widget
        if not isinstance(datelist, DateListBox) or datelist.focus_event is None:
            return False
        card = urwid.Padding(
            event_card(self._conf, event, deleted=self._deleted_scope()),
            left=self._inline_indent(),
            right=RIGHT_MARGIN,
        )
        height = card.rows((self._size[0],))
        datelist.items.insert(datelist.focus_position + 1, card)
        day.height += height
        self._inline = (day, card, height)
        return True

    def _deleted_scope(self) -> str | None:
        """the scope of the focused event's deletion mark, if it has one"""
        uevent = self.focus_event
        status = self.delete_status(uevent.recuid) if uevent is not None else None
        return deletion_scope(status) if status is not None else None

    def _inline_indent(self) -> int:
        style = getattr(getattr(self.dlistbox, "body", None), "style", None)
        if style is None or style.classic:
            return 2
        return DayWalker._time_column_of(style)

    def clear_event_view(self):
        while len(self.container.contents) > 1:
            self.container.contents.pop()
        if self._inline is not None:
            day, card, height = self._inline
            self._inline = None
            body = day.original_widget.body
            if card in body:
                body.remove(card)
                day.height = max(1, day.height - height)
            self.pane._marks_changed()

    def jump_to(self, event) -> None:
        """bring `event` (its first day) into focus in the list"""
        start = event.start_local
        day = start.date() if isinstance(start, dt.datetime) else start
        self.pane.calendar.base_widget.set_focus_date(day)
        self.focus_date = day
        self.pane._columns.focus_position = 1
        body = getattr(self.dlistbox, "body", None)
        if not isinstance(body, DayWalker) or body.focus is None:
            return
        datelist = body[body.focus].original_widget
        for position, widget in enumerate(datelist.items):
            uevent = getattr(widget, "original_widget", None)
            if isinstance(uevent, U_Event) and uevent.event.uid == event.uid:
                datelist.set_focus(position)
                return

    def set_focus_date(self, date):
        """We need this, so we can use it as a callback"""
        self.focus_date = date

    @property
    def focus_date(self) -> dt.date:
        return self.dlistbox.current_date

    @focus_date.setter
    def focus_date(self, date: dt.date) -> None:
        self._last_focused_date = date
        self.dlistbox.ensure_date(date)

    def update(self, min_date, max_date: dt.date, everything: bool):
        """update DateListBox

        if `everything` is True, reset all displayed dates, else only those between
        min_date and max_date
        """
        if everything:
            min_date = self.pane.calendar.base_widget.walker.earliest_date
            max_date = self.pane.calendar.base_widget.walker.latest_date
        self.pane.base_widget.calendar.base_widget.reset_styles_range(min_date, max_date)
        self.dlistbox.update_range(min_date, max_date, everything)

    def refresh_titles(self, min_date: dt.date, max_date: dt.date, everything: bool) -> None:
        """refresh titles in DateListBoxes

        if `everything` is True, reset all displayed dates, else only those between
        min_date and max_date
        """
        self.dlistbox.refresh_titles(min_date, max_date, everything)

    def update_date_line(self) -> None:
        """refresh titles in DateListBoxes"""
        self.dlistbox.update_date_line()

    def edit(self, event, always_save: bool = False, external_edit: bool = False) -> None:
        """create an EventEditor and display it

        :param event: event to edit
        :type event: khal.event.Event
        :param always_save: even save the event if it hasn't changed
        """
        if event.readonly:
            self.pane.window.alert(("alert", f"Calendar `{event.calendar}` is read-only."))
            return

        if isinstance(event.start_local, dt.datetime):
            original_start = event.start_local.date()
        else:
            original_start = event.start_local
        if isinstance(event.end_local, dt.datetime):
            original_end = event.end_local.date()
        else:
            original_end = event.end_local

        def update_colors(new_start: dt.date, new_end: dt.date, everything: bool = False):
            """reset colors in the calendar widget and dates in DayWalker
            between min(new_start, original_start)

            :param everything: set to True if event is a recurring one, than everything
                  gets reseted
            """
            # TODO cleverer support for recurring events, where more than start and
            # end dates are affected (complicated)
            if isinstance(new_start, dt.datetime):
                new_start = new_start.date()
            if isinstance(new_end, dt.datetime):
                new_end = new_end.date()
            start = min(original_start, new_start)
            end = max(original_end, new_end)
            self.pane.eventscolumn.base_widget.update(start, end, everything)

            # set original focus date
            self.pane.calendar.original_widget.set_focus_date(new_start)
            self.pane.eventscolumn.original_widget.set_focus_date(new_start)

        if self.editor:
            self.pane.window.backtrack()

        assert not self.editor
        if external_edit:
            self.pane.window.loop.stop()
            ics = click.edit(event.raw, extension=".ics")
            self.pane.window.loop.start()
            if ics is None:
                return
            # KeyErrors can occur here when we destroy DTSTART,
            # otherwise, even broken .ics files seem to be no problem
            new_event = self.pane.collection.create_event_from_ics(
                ics,
                etag=event.etag,
                calendar_name=event.calendar,
                href=event.href,
            )
            self.pane.collection.update(new_event)
            update_colors(
                new_event.start_local, new_event.end_local, (event.recurring or new_event.recurring)
            )
        else:
            self.editor = True
            editor = EventEditor(self.pane, event, update_colors, always_save=always_save)

            new_pane = EditingScreen(self.pane, self, editor)
            # the right column follows the event
            start = event.start_local
            self.set_focus_date(start.date() if isinstance(start, dt.datetime) else start)

            def teardown(data):
                self.editor = False

            self.pane.window.open(new_pane, callback=teardown)

    def export_event(self):
        """export the event in focus as an ICS file"""
        open_export_dialog(self.pane.window, self.focus_event.event)

    def toggle_delete(self):
        """toggle the delete status of the event in focus

        For a repeating event, a floating box asks which instances to delete.
        """
        event = self.focus_event

        def refresh():
            self.refresh_titles(
                event.event.start_local, event.event.end_local, event.event.recurring
            )
            event.set_title()  # if we are in search results, refresh_titles doesn't work properly

        def delete(toggle):
            def run():
                toggle(event.recuid)
                refresh()

            return run

        if event.event.readonly:
            self.pane.window.alert(
                ("alert", f"Calendar {event.event.calendar} is read-only."),
            )
            return
        status = self.delete_status(event.recuid)
        if status == DeletionType.ALL:
            self.toggle_delete_all(event.recuid)
        elif status == DeletionType.INSTANCES:
            self.toggle_delete_instance(event.recuid)
        elif status == DeletionType.FOLLOWING:
            self.pane.toggle_delete_following(self.pane.following_mark(event.recuid))
        elif event.event.recurring:
            # FIXME if in search results, original pane is used for overlay, not search results
            # also see issue of reseting titles below, probably related
            start = event.event.start_local
            answers = [
                Answer(
                    "t",
                    "only this one",
                    delete(self.toggle_delete_instance),
                    f"{start:%a} {start.day} {start:%b}",
                ),
                Answer("a", "all occurrences", delete(self.toggle_delete_all)),
            ]
            if event.event.recurobject:  # only RRULEs can end before an instance
                answers.insert(
                    1,
                    Answer(
                        "f", "this and all following", delete(self.pane.toggle_delete_following)
                    ),
                )
            self.pane.choose(
                "Delete",
                f"Delete “{event.event.summary}”?",
                answers,
                description=describe_rrule(
                    event.event.recurobject,
                    event.event.start_local,
                    self._conf["locale"]["timeformat"],
                )
                or "This is a repeating event.",
            )
            return
        else:
            self.toggle_delete_all(event.recuid)
        refresh()

    def duplicate(self) -> None:
        """duplicate the event in focus"""
        # TODO copying from birthday calendars is currently problematic
        # because their title is determined by X-BIRTHDAY and X-FNAME properties
        # which are also copied. If the events' summary is edited it will show
        # up on disk but not be displayed in khal
        if self.focus_event is None:
            return None
        event = self.focus_event.event.duplicate()
        try:
            self.pane.collection.insert(event)
        except ReadOnlyCalendarError:
            event.calendar = (
                self.pane.collection.default_calendar_name or self.pane.collection.writable_names[0]
            )
            self.edit(event, always_save=True)
        start_date, end_date = event.start_local, event.end_local
        if isinstance(start_date, dt.datetime):
            start_date = start_date.date()
        if isinstance(end_date, dt.datetime):
            end_date = end_date.date()
        self.pane.eventscolumn.base_widget.update(start_date, end_date, event.recurring)
        try:
            self._old_focus = self.focus_position
        except IndexError:
            pass

    def new(self, date: dt.date, end: dt.date | None = None) -> None:
        """create a new event on `date` at the next full hour and edit it

        :param date: default date for new event
        :param end: date the event ends on (inclusive)

        If both `date` and `end` are datetimes, a timed event spanning from
        `date` to `end` is created instead.
        """
        dtstart: dt.date
        dtend: dt.date
        if not self.pane.collection.writable_names:
            self.pane.window.alert(("alert", "No writable calendar."))
            return
        if date is None:
            date = dt.datetime.now()
        if isinstance(date, dt.datetime) and isinstance(end, dt.datetime):
            dtstart, dtend = date, end
            allday = False
        elif end is None:
            dtstart = dt.datetime.combine(date, dt.time(dt.datetime.now().hour))
            dtend = dtstart + dt.timedelta(minutes=60)
            allday = False
        else:  # TODO XXX why do we use allday if end is not set???
            dtstart = date
            dtend = end + dt.timedelta(days=1)
            allday = True
        event = self.pane.collection.create_event_from_dict(
            {
                "dtstart": dtstart,
                "dtend": dtend,
                "summary": "",
                "timezone": self._conf["locale"]["default_timezone"],
                "allday": allday,
                "alarms": timedelta2str(self._conf["default"]["default_event_alarm"]),
            }
        )
        self.edit(event)

    def selectable(self):
        return True

    def keypress(self, size: Size, key: str) -> str | None:
        if len(size) == 2:
            self._size = size
        if self.pane.details_shown:
            # like the inline card: any key closes the details column; enter on
            # the same event then edits it, enter on another one shows that one
            self.pane.show_details(None)
            if key == "esc":
                self._eventshown = None
                return None
            return self._keypress(size, key)
        if key == "esc" and (self._inline is not None or len(self.container.contents) > 1):
            self._eventshown = None
            self.clear_event_view()
            return None
        return self._keypress(size, key)

    def _keypress(self, size: Size, key: str) -> str | None:
        view = self.dlistbox
        if (
            key in self._conf["keybindings"]["view"]
            and isinstance(view, HandlesViewKey)
            and view.handles_view_key()
        ):
            # the view uses the key itself (e.g. the time grid's "+N" badge)
            self._eventshown = None
            self.clear_event_view()
            return super().keypress(size, key)
        prev_shown = self._eventshown
        self._eventshown = None
        self.clear_event_view()

        if key in self._conf["keybindings"]["new"]:
            # views may suggest a date or time range for the new event
            view = self.dlistbox
            span = view.new_event_range() if isinstance(view, HasNewEventRange) else None
            if span is not None:
                self.new(*span)
            else:
                self.new(self.focus_date, None)
            return None

        if self.focus_event:
            if key in self._conf["keybindings"]["delete"]:
                self.toggle_delete()
                key = "down"
            elif key in self._conf["keybindings"]["duplicate"]:
                self.duplicate()
                return None
            elif key in self._conf["keybindings"]["export"]:
                self.export_event()
                return None

        rval = super().keypress(size, key)
        if self.focus_event:
            if key in self._conf["keybindings"]["view"] and prev_shown == self.focus_event.recuid:
                # the event in focus is already viewed -> edit
                if self.delete_status(self.focus_event.recuid):
                    self.pane.window.alert(("alert", "This event is marked as deleted"))
                self.edit(self.focus_event.event)
            elif key in self._conf["keybindings"]["external_edit"]:
                self.edit(self.focus_event.event, external_edit=True)
            elif (
                key in self._conf["keybindings"]["view"]
                or self._conf["view"]["event_view_always_visible"]
            ):
                self._eventshown = self.focus_event.recuid
                self.view(self.focus_event.event)
        return rval

    def render(self, a, focus):
        if focus:
            DateListBox.selected_date = None
        return super().render(a, focus)


class EventDisplay(EventDetails):
    """A widget showing one Event()'s details (see khal.ui.details)"""


class ClassicView(Pane):
    """default Pane for khal

    showing a CalendarWalker on the left and the eventList + eventviewer/editor
    on the right
    """

    def __init__(self, collection, conf=None, title: str = "", description: str = "") -> None:
        # calendars that start hidden (`hidden = True` in [calendars])
        for name, calendar in ((conf or {}).get("calendars") or {}).items():
            if calendar.get("hidden", False) and name in collection.names:
                collection.hidden_calendars.add(name)
        self.init = True
        # Will be set when opening the view inside a Window
        self.window = None
        self._conf = conf
        self.collection = collection
        self._deleted: dict[int, list[Any]] = {
            DeletionType.ALL: [],
            DeletionType.INSTANCES: [],
            DeletionType.FOLLOWING: [],
        }

        ContainerWidget = linebox[self._conf["view"]["frame"]]
        if self._conf["view"]["dynamic_days"]:
            Walker = DayWalker
        else:
            Walker = StaticDayWalker
        daywalker = Walker(
            dt.date.today(),
            eventcolumn=self,
            conf=self._conf,
            delete_status=self.delete_status,
            collection=self.collection,
        )
        elistbox = DListBox(
            daywalker,
            parent=self,
            conf=self._conf,
            delete_status=self.delete_status,
            toggle_delete_all=self.toggle_delete_all,
            toggle_delete_instance=self.toggle_delete_instance,
            dynamic_days=self._conf["view"]["dynamic_days"],
        )
        # all views available for the right column, plugin views get
        # instantiated lazily when they are first switched to
        self._views: dict[str, EventView | None] = {"list": elistbox}
        self._views.update(dict.fromkeys(plugins.get_views()))
        self._current_view = "list"
        self.eventscolumn = ContainerWidget(
            CAttrMap(
                EventColumn(pane=self, elistbox=elistbox),
                "eventcolumn",
                "eventcolumn focus",
            ),
            title=self.view_title,
            status=self.view_status,
            title_attr="frame title",
        )
        self._day_marking = self._conf["view"].get("day_marking", "calendar")
        calendar = CAttrMap(
            CalendarWidget(
                on_date_change=self.event_column.set_focus_date,
                keybindings=self._conf["keybindings"],
                on_press=dict.fromkeys(self._conf["keybindings"]["new"], self.new_event),
                firstweekday=self._conf["locale"]["firstweekday"],
                weeknumbers=self._conf["locale"]["weeknumbers"],
                monthdisplay=self._conf["view"]["monthdisplay"],
                get_styles=self.day_styles,
                day_markers=self._day_marking == "dot",
            ),
            "calendar",
            "calendar focus",
        )
        if self._conf["view"]["dynamic_days"]:
            elistbox.set_focus_date_callback = calendar.set_focus_date
        else:
            elistbox.set_focus_date_callback = lambda _: None
        self.calendar = ContainerWidget(calendar, title=self.month_title, title_attr="frame title")
        self.lwidth = 32 if self._conf["locale"]["weeknumbers"] == "right" else 28
        if self._conf["view"]["frame"] in ["width", "color"]:
            self.lwidth += 2
        columns = NColumns(
            [(self.lwidth, self.calendar), self.eventscolumn],
            dividechars=0,
            box_columns=[0, 1],
            outermost=True,
        )
        self._columns = columns
        self.width = 0  # columns, as of the last render
        Pane.__init__(self, columns, title=title, description=description)

        default_view = self._conf["view"].get("default_view", "list")
        if default_view not in self._views:
            logger.warning(
                f"Unknown view `{default_view}` configured, available views are: "
                f"{', '.join(self._views)}"
            )
        elif default_view != "list":
            self.switch_view(default_view)

    HEAT_LEVELS = ((1, 1), (2, 2), (4, 3))  # (minimum number of events, level)

    @property
    def month_column(self) -> CalendarWidget:
        """the month column (inside its frame and attribute map)"""
        return find_child(self.calendar, CalendarWidget)

    @property
    def event_column(self) -> EventColumn:
        """the right column (inside its frame and attribute map)"""
        return find_child(self.eventscolumn, EventColumn)

    @property
    def details_shown(self) -> bool:
        return len(self._columns.contents) > 2

    def show_details(self, event, deleted: str | None = None) -> None:
        """the details of `event` in a column right of the events (None: close it)"""
        if event is None:
            if self.details_shown:
                self._columns.contents.pop()
                self._columns.focus_position = 1
                self._marks_changed()
            return
        widget = event_column(self._conf, event, deleted=deleted)
        options = self._columns.options("weight", 1, True)
        if self.details_shown:
            self._columns.contents[2] = (widget, options)
        else:
            self._columns.contents.append((widget, options))
        self._columns.focus_position = 1

    def day_styles(self, date: dt.date, focus: bool):
        """styles of a day in the month column, see `[view] day_marking`"""
        marking = self._day_marking
        if marking == "calendar" or (marking != "dot" and (focus or date == dt.date.today())):
            # today and the focused day keep their own style
            return self.collection.get_styles(date, focus)
        if marking == "none":
            return None
        if marking == "dot":
            # today and the focused day keep their own style, but also their
            # marker (so it doesn't disappear while moving through the days)
            own = None
            if focus or date == dt.date.today():
                styles = self.collection.get_styles(date, focus)
                own = styles if isinstance(styles, str) else None
            calendars = self.collection.get_calendars_on(date)
            if not calendars:
                return own
            marker = "•" if len(calendars) == 1 else "‥"
            if not self._conf["locale"].get("unicode_symbols", True):
                marker = "*"
            return DayStyle(own, marker, "calendar " + calendars[0] + " mark")
        if marking == "heat":
            count = len(list(self.collection.get_events_on(date)))
            level = 0
            for minimum, heat in self.HEAT_LEVELS:
                if count >= minimum:
                    level = heat
            return f"day heat {level}" if level else None
        return None

    @property
    def title(self) -> str:
        """the header line: `[view] header_format` (date, time, next event)"""
        header = format_header(self._conf, self.collection) or self._title
        view = self._views.get(self._current_view) if hasattr(self, "_views") else None
        suffix = getattr(view, "title_suffix", "")
        return f"{header}  · {suffix}" if suffix else header

    def view_tabs(self) -> list:
        """`[list]  day  week`: the views of the right column (a view class
        can have several `tabs`, its instance names the `active_tab`)"""
        markup: list = []
        for name, view in self._views.items():
            source = view if view is not None else plugins.get_views().get(name)
            tabs = tuple(getattr(source, "tabs", None) or (name,))
            active = None
            if name == self._current_view:
                active = getattr(view, "active_tab", None) or tabs[0]
            for tab in tabs:
                if markup:
                    markup.append("  ")
                if tab == active:
                    markup.append(("header tab active", f"[{tab}]"))
                else:
                    markup.append(("header tab", tab))
        return markup

    def header_markup(self, maxcol: int) -> list | None:
        """the header line for a screen `maxcol` wide: `[view] header_format`
        and the view tabs at the right; when narrow, the tabs go first, then
        the default format gets shorter (see agenda.SHORT_HEADER_FORMATS)"""
        view = self._conf["view"]
        header_format = view.get("header_format", "") or ""
        if not header_format:
            return None
        try:
            attributes = header_attributes(self._conf, self.collection)
            variants = [header_format]
            if header_format == DEFAULT_HEADER_FORMAT:
                variants += list(SHORT_HEADER_FORMATS)
            formatted = [header_markup(variant, attributes) for variant in variants]
        except (KeyError, ValueError, IndexError):
            return [("header dim", " " + header_format)]
        tabs = (
            self.view_tabs() if view.get("header_view_tabs", True) and len(self._views) > 1 else []
        )

        def width(markup) -> int:
            text = urwid.decompose_tagmarkup(markup)[0] if markup else ""
            return urwid.calc_width(text, 0, len(text))

        options = [(left, tabs) for left in formatted[:1] if tabs] + [
            (left, []) for left in formatted
        ]
        for left, right in options:
            needed = 1 + width(left) + (2 + width(right) + 1 if right else 0)
            if needed <= maxcol:
                break
        if not right:
            return [" ", *left]
        gap = maxcol - 1 - width(left) - width(right) - 1
        return [" ", *left, " " * gap, *right, " "]

    def month_title(self) -> str:
        """the title of the month column: the month in focus (`November`,
        `January 2027` in another year)"""
        try:
            day = self.month_column.focus_date
        except (AttributeError, IndexError):
            return ""
        # the year only if it isn't this one
        return f"{day:%B}" if day.year == dt.date.today().year else f"{day:%B %Y}"

    def view_title(self) -> str:
        """the title of the right column: the current view's `pane_title`
        (`Agenda`, the time grid's `Week 48 · Mon–Fri`), if it has one"""
        view = self._views.get(self._current_view) if hasattr(self, "_views") else None
        return view.pane_title if isinstance(view, HasPaneTitle) else ""

    def view_status(self) -> list:
        """right in the right column's top border: `2 hidden` while calendars
        are hidden, else the view's `pane_status` (the list: `6 days`)"""
        hidden = len(self.collection.hidden_calendars)
        if hidden:
            return [("frame warning", f"{hidden} hidden")]
        view = self._views.get(self._current_view) if hasattr(self, "_views") else None
        status = view.pane_status if isinstance(view, HasPaneStatus) else ""
        return [("frame hint", status)] if status else []

    @property
    def marked_count(self) -> int:
        """number of deletion marks"""
        return sum(len(marks) for marks in self._deleted.values())

    @property
    def details_open(self) -> bool:
        """an event's details are open (the card in the list or the column)"""
        column = self.event_column
        return self.details_shown or getattr(column, "_inline", None) is not None

    def details_hints(self) -> list:
        """`enter edit  d delete  p duplicate  esc close  ? help`"""
        keys = self._conf["keybindings"]
        markup: list = [" "]
        for command, text in (("view", "edit"), ("delete", "delete"), ("duplicate", "duplicate")):
            if keys.get(command):
                markup += [("footer key", format_key(keys[command][0], UNICODE)), f" {text}  "]
        markup += [("footer key", "esc"), " close  ", ("footer key", "?"), " help"]
        return markup

    @property
    def footer_hints(self) -> list:
        keys = self._conf["keybindings"]
        if self.details_open:
            return self.details_hints()
        count = self.marked_count
        if not count:
            return footer_hints(keys, keys["quit"])
        # while anything is marked: how many, when they go, how to undo
        markup: list = [
            " ",
            ("footer deleted", f"✕ {count} marked"),
            ("footer version", " · deleted when you quit · "),
        ]
        for command, text in (("delete", " undo  "), ("undo_all_deletions", " undo all")):
            if keys.get(command):
                markup += [("footer key", format_key(keys[command][0], UNICODE)), text]
        return markup

    def _marks_changed(self) -> None:
        """the footer's hints depend on marks and open details"""
        if self.window is not None:
            self.window.refresh_footer()

    def undo_all_deletions(self) -> None:
        """remove all deletion marks"""
        if not self.marked_count:
            return
        for marks in self._deleted.values():
            marks.clear()
        today = dt.date.today()
        self.event_column.refresh_titles(today, today, True)
        self._marks_changed()

    def switch_view(self, name: str | None = None) -> None:
        """switch the right column to view `name` (or to the next available view)"""
        names = list(self._views)
        if name is None:
            name = names[(names.index(self._current_view) + 1) % len(names)]
        if self._views[name] is None:
            try:
                self._views[name] = plugins.get_views()[name](self)
            except Exception as error:
                logger.exception(error)
                logger.error(f"Could not load view `{name}`: {error}")
                del self._views[name]
                return
        view = self._views[name]
        assert view is not None  # loaded above
        self._current_view = name
        self.event_column.set_view(view)
        tabs = self._conf["view"].get("header_view_tabs", True) and self._conf["view"].get(
            "header_format"
        )
        if self.window is not None and not tabs:  # otherwise the tabs show it
            self.window.alert(f"view: {name}")

    def extra_keybindings(self) -> list[tuple[str, list[tuple[str, list[str], str]]]]:
        """keybindings of the currently active view (if it provides them)"""
        name = self._current_view
        keybindings_help = getattr(self._views[name], "keybindings_help", None)
        if keybindings_help is None:
            return []
        try:
            return [(f"{name} view", keybindings_help(self._conf))]
        except Exception as error:
            logger.error(f"Could not get keybindings of view `{name}`: {error}")
            return []

    def delete_status(self, uid: str) -> DeletionType | None:
        if uid[0] in self._deleted[DeletionType.ALL]:
            return DeletionType.ALL
        elif uid in self._deleted[DeletionType.INSTANCES]:
            return DeletionType.INSTANCES
        elif self.following_mark(uid) is not None:
            return DeletionType.FOLLOWING
        else:
            return None

    def following_mark(self, recuid) -> tuple[str, Any] | None:
        """the `this and following` deletion mark that covers `recuid` (if any)"""
        uid, rec_id = recuid
        for mark_uid, mark_rec_id in self._deleted[DeletionType.FOLLOWING]:
            if mark_uid != uid:
                continue
            try:
                if rec_id >= mark_rec_id:
                    return (mark_uid, mark_rec_id)
            except TypeError:  # date vs. datetime
                continue
        return None

    def toggle_delete_all(self, recuid: tuple[str, str]) -> None:
        uid, _ = recuid
        if uid in self._deleted[DeletionType.ALL]:
            self._deleted[DeletionType.ALL].remove(uid)
        else:
            self._deleted[DeletionType.ALL].append(uid)
        self._marks_changed()

    def toggle_delete_instance(self, uid: str) -> None:
        if uid in self._deleted[DeletionType.INSTANCES]:
            self._deleted[DeletionType.INSTANCES].remove(uid)
        else:
            self._deleted[DeletionType.INSTANCES].append(uid)
        self._marks_changed()

    def toggle_delete_following(self, recuid) -> None:
        """mark (or unmark) this instance and all following ones for deletion"""
        if recuid in self._deleted[DeletionType.FOLLOWING]:
            self._deleted[DeletionType.FOLLOWING].remove(recuid)
        else:
            self._deleted[DeletionType.FOLLOWING].append(recuid)
        self._marks_changed()

    def cleanup(self, data):
        """delete all events marked for deletion"""
        # If we delete several recuids from the same vevent, the etag will
        # change after each deletion. As we check for matching etags before
        # deleting, deleting any subsequent recuids will fail.
        # We therefore keep track of the etags of the events we already
        # deleted.
        updated_etags = {}
        for part in self._deleted[DeletionType.ALL]:
            account, href, etag = part.split("\n", 2)
            self.collection.delete(href, etag, account)
        for part, rec_id in self._deleted[DeletionType.FOLLOWING]:
            account, href, etag = part.split("\n", 2)
            if part in self._deleted[DeletionType.ALL]:
                continue
            etag = updated_etags.get(href) or etag
            event = self.collection.delete_following(href, etag, account, rec_id)
            if event is not None:
                updated_etags[event.href] = event.etag
        for part, rec_id in self._deleted[DeletionType.INSTANCES]:
            account, href, etag = part.split("\n", 2)
            etag = updated_etags.get(href) or etag
            event = self.collection.delete_instance(href, etag, account, rec_id)
            updated_etags[event.href] = event.etag

    # -- showing and hiding calendars

    def calendar_shown(self, name: str) -> bool:
        return name not in self.collection.hidden_calendars

    def show_calendar(self, name: str, shown: bool) -> None:
        """show or hide calendar `name`: the list, the month column and the
        views follow at once (they get their events through the collection)"""
        if shown:
            self.collection.hidden_calendars.discard(name)
        else:
            self.collection.hidden_calendars.add(name)
        # the month column: restyle the loaded weeks in place (no scrolling)
        walker = self.month_column.walker
        focus = walker.focus_row, walker.week(walker.focus_row).focus_position
        for row in range(len(walker)):
            for column, day in enumerate(walker.week(row).days(), 1):
                day.reset_styles((row, column) == focus)
        # every view (also those not shown right now) reloads its events
        for view in self._views.values():
            if view is not None:
                view.update_range(None, None, everything=True)

    def toggle_calendars(self) -> None:
        """the list of calendars, without the grey backdrop: the changes stay
        visible"""
        assert self.window is not None
        window = self.window
        box = CalendarsBox(
            list(self.collection.names),
            self.calendar_shown,
            self.show_calendar,
            window.backtrack,
            UNICODE if self._conf["locale"].get("unicode_symbols", True) else ASCII,
        )
        window.open_floating(box, width=box.width, height=box.height, backdrop=False)

    # -- moving through time

    @property
    def focus_date(self) -> dt.date:
        """the day in focus (in the month column or the right column)"""
        if self._columns.focus_position == 0:
            return self.month_column.focus_date
        return self.event_column.focus_date

    def jump_to_date(self, day: dt.date, announce: bool = False) -> None:
        """bring `day` into focus in the month column and the right column
        (list, time grid, ...); a jump to another month is announced in the
        header (`→ March 2027`), with `announce` always"""
        before = self.focus_date
        self.month_column.set_focus_date(day)
        self.event_column.focus_date = day
        if self.window is not None and (
            announce or (day.year, day.month) != (before.year, before.month)
        ):
            self.window.message(f"→ {day:%B %Y}", "info")

    def goto_date(self) -> None:
        """ask for a date at the bottom (`g`) and jump there"""
        assert self.window is not None

        def jump(text: str) -> str | None:
            day = parse_goto(text, self._conf["locale"])
            if day is None:
                return "not a date"
            self.jump_to_date(day, announce=True)
            return None

        self.window.prompt("go to", jump)

    def keypress(self, size: Size, key: str) -> str | None:
        binds = self._conf["keybindings"]
        for command, months in MONTH_STEPS.items():
            if key in binds.get(command, []):
                self.jump_to_date(shift_months(self.focus_date, months))
                return None
        if key in binds.get("goto_date", []):
            self.goto_date()
            return None
        if key in binds.get("toggle_calendars", []):
            self.toggle_calendars()
            return None
        if key in binds.get("undo_all_deletions", []):
            self.undo_all_deletions()
        elif key in binds["search"]:
            self.search()
        elif key in binds.get("switch_view", []):
            self.switch_view()
            return None
        return super().keypress(size, key)

    def search(self):
        """the finder: search as you type, enter jumps to the event"""
        assert self.window is not None
        window = self.window

        def jump(event):
            window.backtrack()
            self.eventscolumn.original_widget.jump_to(event)

        finder = Finder(
            self._conf,
            lambda term: list(self.collection.search(term)),
            hidden=lambda event: event.calendar in self.collection.hidden_calendars,
            on_jump=jump,
            on_close=window.backtrack,
        )
        window.open_floating(finder, width=("relative", 90), height=("relative", 80), min_width=40)

    def render(self, size, focus=False):
        self.width = size[0]
        listbox = self._views.get("list")
        if self._current_view == "list" and isinstance(listbox, DListBox) and len(size) == 2:
            # the right column's title (`6 days`) is drawn before the list
            frame = 2 if self._conf["view"]["frame"] in ("width", "color") else 0
            width = size[0] - self.lwidth - frame
            if (
                not self.details_shown
                and not self.eventscolumn.original_widget.container.contents[1:]
            ):
                listbox.prepare((max(1, width), max(1, size[1] - frame)))
        if self.details_shown and self.eventscolumn.original_widget.view_mode() != "column":
            self.show_details(None)  # got too narrow
        rval = super().render(size, focus)
        if self.init:
            # starting with today's events
            self.eventscolumn.current_date = dt.date.today()
            self.init = False
        return rval

    def new_event(self, date, end):
        """create a new event starting on date and ending on end (if given)"""
        self.eventscolumn.original_widget.new(date, end)


def _urwid_palette_entry(
    name: str,
    color: str,
    hmethod: str,
    color_mode: Literal["256colors", "rgb"],
    foreground: str = "",
    background: str = "",
) -> tuple[str, str, str, str, str, str]:
    """Create an urwid compatible palette entry.

    :param name: name of the new attribute in the palette
    :param color: color for the new attribute
    :param hmethod: which highlighting mode to use, foreground or background
    :param color_mode: which color mode we are in, if we are in 256-color mode,
    we transform 24-bit/RGB colors to a (somewhat) matching 256-color set color
    :param foreground: the foreground color to apply if we use background highlighting method
    :param background: the background color to apply if we use foreground highlighting method

    :returns: an urwid palette entry
    """
    from khal.terminal import COLORS

    if color == "" or color in COLORS or color is None:
        # Named colors already use urwid names, no need to change anything.
        pass
    elif color.isdigit():
        # Colors from the 256 color palette need to be prefixed with h in
        # urwid.
        color = "h" + color
    elif color_mode == "256color":
        # Convert to some color on the 256 color palette that might resemble
        # the 24-bit color.
        # First, generate the palette (indices 16-255 only). This assumes, that
        # the terminal actually uses the same palette, which may or may not be
        # the case.
        colors = {}
        # Colorcube
        colorlevels = (0x00, 0x5F, 0x87, 0xAF, 0xD7, 0xFF)
        for r in range(6):
            for g in range(6):
                for b in range(6):
                    colors[r * 36 + g * 6 + b + 16] = (
                        colorlevels[r],
                        colorlevels[g],
                        colorlevels[b],
                    )
        # Grayscale
        graylevels = [0x08 + 10 * i for i in range(24)]
        for c in range(24):
            colors[232 + c] = (graylevels[c],) * 3
        # Parse the HTML-style color into the variables r, g, b.
        if len(color) == 4:
            # e.g. #ABC, equivalent to #AABBCC
            r = int(color[1] * 2, 16)
            g = int(color[2] * 2, 16)
            b = int(color[3] * 2, 16)
        else:
            # e.g. #AABBCC
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
        # Now, find the color with the least distance to the requested color.
        best = None
        bestdist = 0.0
        for index, rgb in colors.items():
            # This is the euclidean distance metric. It is quick, simple and
            # wrong (in the sense of human color perception). However, any
            # serious color distance metric would be way more complicated.
            dist = (r - rgb[0]) ** 2 + (g - rgb[1]) ** 2 + (b - rgb[2]) ** 2
            if best is None or dist < bestdist:
                best = index
                bestdist = dist
        color = "h" + str(best)
    # We unconditionally add the color to the high color slot. It seems to work
    # in lower color terminals as well.
    if hmethod in ["fg", "foreground"]:
        return (name, "", "", "", color, background)
    else:
        return (name, "", "", "", foreground, color)


def _add_calendar_colors(
    palette: list[colors.PaletteEntry],
    collection: CalendarCollection,
    color_mode: Literal["256colors", "rgb"],
    base: str | None = None,
    attr_template: str = "calendar {}",
    highlight: bool = True,
    hmethod: str | None = None,
) -> list[colors.PaletteEntry]:
    """Add the colors for the defined calendars to the palette.

    We support setting a fixed background or foreground color that we extract
    from a giving attribute

    :param palette: the base palette
    :param collection:
    :param color_mode: which color mode we are in
    :param base: the attribute to extract the background and foreground color from
    :param attr_template: the template to use for the attribute name
    :param highlight: also add `highlight_days_color` and `highlight_days_multiple`
    :param hmethod: `fg`/`bg` instead of `[highlight_days] method` (markers like
        the month column's dots are always coloured in the foreground)
    :returns: the modified palette
    """
    bg_color, fg_color = "", ""
    for attr in palette:
        if base and attr[0] == base:
            if color_mode == "rgb" and len(attr) >= 5:
                bg_color = attr[5] or ""
                fg_color = attr[4] or ""
            else:
                bg_color = attr[2] or ""
                fg_color = attr[1] or ""

    for cal in collection.calendars:
        if cal["color"] == "":
            # No color set for this calendar, use default_color instead.
            color = collection.default_color
        else:
            color = cal["color"]

        # In case the color contains an alpha value, remove it for urwid.
        # eg '#RRGGBBAA' -> '#RRGGBB' and '#RGBA' -> '#RGB'.
        if color and len(color) == 9 and color[0] == "#":
            color = color[0:7]
        elif color and len(color) == 5 and color[0] == "#":
            color = color[0:4]

        entry = _urwid_palette_entry(
            attr_template.format(cal["name"]),
            color,
            hmethod or collection.hmethod,
            color_mode=color_mode,
            foreground=fg_color,
            background=bg_color,
        )
        palette.append(entry)

    if not highlight:
        return palette
    entry = _urwid_palette_entry(
        "highlight_days_color",
        collection.color,
        collection.hmethod,
        color_mode=color_mode,
        foreground=fg_color,
        background=bg_color,
    )
    palette.append(entry)
    entry = _urwid_palette_entry(
        "highlight_days_multiple",
        collection.multiple,
        collection.hmethod,
        color_mode=color_mode,
        foreground=fg_color,
        background=bg_color,
    )
    palette.append(entry)

    return palette


def footer_hints(keybindings: dict[str, list[str]], quit_keys: list[str]) -> list:
    """`n new  enter open  d delete  ...` for the footer line"""

    markup: list = [" "]
    for command, text in (
        ("new", "new"),
        ("view", "open"),
        ("delete", "delete"),
        ("switch_view", "view"),
        ("today", "today"),
        ("search", "search"),
    ):
        keys = keybindings.get(command)
        if keys:
            markup += [("footer key", format_key(keys[0], UNICODE)), f" {text}  "]
    markup += [("footer key", "?"), " help  ", ("footer key", quit_keys[0]), " quit"]
    return markup


class ThemePalette(NamedTuple):
    """the urwid palette of a theme and what ikhal's window needs to know of it"""

    palette: list[colors.PaletteEntry]
    # the theme's semantic colours (bg, acc, ...), e.g. for colours plugins compute
    theme_colors: dict[str, str]
    # the theme paints its own background
    paints_background: bool
    # attribute map for the screen behind floating boxes (None: no backdrop)
    backdrop: dict[str | None, str] | None


def build_palette(
    conf, collection, color_mode: Literal["rgb", "256colors"] = "rgb"
) -> ThemePalette:
    """the palette for ikhal: the configured theme, calendar colours, the
    [palette] overrides and (with `backdrop = grey`) the backdrop twins

    :raises FatalError: if the configured theme does not exist
    """
    # We don't validate the themes in settings.spec but instead here
    # first try to load built-in themes, then try to load themes from
    # plugins
    theme_name = conf["view"]["theme"]
    theme_source = colors.themes.get(theme_name)
    if theme_source is None:
        theme_source = plugins.THEMES.get(theme_name)
    if theme_source is None:
        logger.fatal(f"Invalid theme {theme_name} configured")
        logger.fatal(f"Available themes are: {', '.join(colors.themes.keys())}")
        raise FatalError
    semantic = colors.is_semantic_theme(theme_source)
    # the theme's background and accent, e.g. for colours plugins compute
    theme_colors: dict[str, str]
    theme: list[colors.PaletteEntry]
    if colors.is_semantic_theme(theme_source):
        theme_colors = dict(theme_source)
        # themes can be given as a few semantic colours (see colors.ROLES)
        theme = colors.expand_theme(theme_source, color_mode)
    elif isinstance(theme_source, list):
        dark = colors.theme_is_dark(theme_source, theme_name)
        theme_colors = dict(colors.NEUTRAL_DARK if dark else colors.NEUTRAL_LIGHT)
        theme = list(theme_source)
    else:
        logger.fatal(f"Theme {theme_name} is neither a palette nor a dict of semantic colours")
        raise FatalError

    palette = _add_calendar_colors(
        theme,
        collection,
        color_mode=color_mode,
        base="calendar",
        attr_template="calendar {}",
    )
    palette = _add_calendar_colors(
        palette,
        collection,
        color_mode=color_mode,
        base="popupbg",
        attr_template="calendar {} popup",
        highlight=False,
        hmethod="fg",
    )
    # markers (the list's bars, the month column's dots, the dots in details
    # and lists): always the calendar colour on the normal background, also
    # with `[highlight_days] method = background`
    palette = _add_calendar_colors(
        palette,
        collection,
        color_mode=color_mode,
        base="calendar",
        attr_template="calendar {} mark",
        highlight=False,
        hmethod="fg",
    )
    # the calendar's colour on the background of focused rows (dots in the
    # editor's calendar field and in choice lists)
    palette = _add_calendar_colors(
        palette,
        collection,
        color_mode=color_mode,
        base="editor focus row",
        attr_template="calendar {} row",
        highlight=False,
        hmethod="fg",
    )
    # calendar colors as background, e.g. for blocks in time based views
    for cal in collection.calendars:
        color = cal["color"] or collection.default_color
        if color and color[0] == "#" and len(color) in (5, 9):
            color = color[:-1] if len(color) == 5 else color[:7]
        palette.append(
            _urwid_palette_entry(
                f"calendar {cal['name']} bg",
                color,
                "bg",
                color_mode=color_mode,
                foreground="black",
            )
        )

    def merge_palettes(pallete_a, pallete_b) -> list[colors.PaletteEntry]:
        """Merge two palettes together, with the second palette taking priority."""
        merged = {}
        for entry in pallete_a:
            merged[entry[0]] = entry
        for entry in pallete_b:
            merged[entry[0]] = entry
        return list(merged.values())

    overwrite = [(key, *values) for key, values in conf["palette"].items()]
    palette = merge_palettes(palette, overwrite)
    backdrop = None
    if conf["view"].get("backdrop", "grey") == "grey":
        # greyscale twins for the screen behind floating boxes (dialogs, help)
        palette = colors.add_backdrop_twins(
            palette, dark_theme=colors.theme_is_dark(theme_source, theme_name)
        )
        backdrop = colors.backdrop_map(palette)
    return ThemePalette(palette, theme_colors, semantic, backdrop)


def seconds_to_next_minute(now: dt.datetime | None = None) -> float:
    """seconds until the next full minute (at least a bit more than 0)"""
    now = now or dt.datetime.now()
    return max(0.05, 60 - now.second - now.microsecond / 1e6)


def redraw_today(loop, data) -> None:
    """once a minute, on the full minute: the header line (clock and next
    event), the "now" line in the list and, after midnight, today's style

    :param data: (pane, meta), meta remembers the last day across calls
    """
    pane, meta = data
    today = dt.date.today()
    if meta["last_today"] != today:
        if meta["last_today"] is not None:
            pane.calendar.original_widget.reset_styles_range(
                min(meta["last_today"], today), max(meta["last_today"], today)
            )
        meta["last_today"] = today
    # moves the "now" line in the list of events
    pane.eventscolumn.original_widget.update_date_line()
    if pane.window is not None:
        # recomputes the pane's title, i.e. the clock and the next event
        pane.window.clear_header()
    loop.set_alarm_in(seconds_to_next_minute(), redraw_today, data)


def root_widget(frame: urwid.Widget) -> urwid.Widget:
    """the topmost widget of ikhal: `frame` and its pop-ups on the theme's background

    "body" gives the theme's background to everything without an attribute.
    The pop-up target must be inside that map (and not, as with
    `MainLoop(pop_ups=True)`, around it), otherwise pop-ups (choices, date
    picker, time drum) are drawn on the terminal's background.
    """
    return urwid.AttrMap(PopUpTarget(frame), "body")


def start_pane(
    pane,
    callback,
    program_info="",
    quit_keys=None,
    color_mode: Literal["rgb", "256colors"] = "rgb",
):
    """Open the user interface with the given initial pane."""
    themed = build_palette(pane._conf, pane.collection, color_mode)
    palette = themed.palette
    quit_keys = quit_keys or ["q"]

    frame = Window(
        footer=footer_hints(pane._conf["keybindings"], quit_keys),
        quit_keys=quit_keys,
        version=program_info,
        log_key=(pane._conf["keybindings"].get("log") or ["L"])[0],
    )
    frame.theme_colors = themed.theme_colors
    # semantic themes paint their own background; plugins registering palette
    # entries must then use it instead of the terminal's default background
    frame.paints_background = themed.paints_background
    frame.backdrop = themed.backdrop

    class HeaderFormatter(logging.Formatter):
        def format(self, record):
            return record.getMessage()

    class LogPaneHandler(logging.Handler):
        def emit(self, record):
            frame.log(
                LogEntry(
                    dt.datetime.fromtimestamp(record.created), record.levelno, record.getMessage()
                )
            )

    class LogHeaderHandler(logging.Handler):
        def emit(self, record):
            kind = "error" if record.levelno >= logging.WARNING else "info"
            frame.message(self.format(record), kind)

    if len(logger.handlers) > 0 and not isinstance(logger.handlers[-1], logging.FileHandler):
        logger.handlers.pop()

    pane_handler = LogPaneHandler()
    logger.addHandler(pane_handler)

    header_handler = LogHeaderHandler()
    header_handler.setFormatter(HeaderFormatter())
    logger.addHandler(header_handler)

    frame.open(pane, callback)
    screen = urwid.display.raw.Screen()
    loop = urwid.MainLoop(
        widget=root_widget(frame),
        palette=colors.urwid_palette(palette),
        screen=screen,
        unhandled_input=frame.on_key_press,
        pop_ups=False,  # root_widget() hosts the pop-ups
        handle_mouse=pane._conf["default"]["enable_mouse"],
    )
    frame.loop = loop

    meta = {"last_today": dt.date.today()}
    loop.set_alarm_in(seconds_to_next_minute(), redraw_today, (pane, meta))

    def check_for_updates(loop, pane):
        if pane.collection.needs_update():
            pane.window.alert("detected external vdir modification, updating...")
            pane.collection.update_db()
            pane.eventscolumn.base_widget.update(None, None, everything=True)
            pane.window.alert("detected external vdir modification, updated.")
        loop.set_alarm_in(60, check_for_updates, pane)

    loop.set_alarm_in(60, check_for_updates, pane)

    screen.set_terminal_properties(
        colors=16_777_216 if color_mode == "rgb" else 256,
        bright_is_bold=pane._conf["view"]["bold_for_light_color"],
    )

    def ctrl_c(signum, f):
        raise urwid.ExitMainLoop()

    signal.signal(signal.SIGINT, ctrl_c)
    try:
        loop.run()
    except Exception:
        import traceback

        tb = traceback.format_exc()
        try:  # Try to leave terminal in usable state
            loop.stop()
        except Exception:
            pass
        print(tb)
        sys.exit(1)
