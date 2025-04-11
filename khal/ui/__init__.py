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

import datetime as dt
import logging
import signal
import sys
from enum import IntEnum
from typing import Literal, Optional

import click
import urwid

from .. import plugins, utils
from ..khalendar import CalendarCollection
from ..khalendar.exceptions import FatalError, ReadOnlyCalendarError
from ..parse_datetime import timedelta2str
from . import colors
from .base import Pane, Window
from .editor import EventEditor, ExportDialog
from .widgets import CalendarWidget, CAttrMap, NColumns, NPile, button, linebox
from .widgets import ExtendedEdit as Edit

logger = logging.getLogger('khal')

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

class DeletionType(IntEnum):
    ALL = 0
    INSTANCES = 1


class DateConversionError(Exception):
    pass


class SelectableText(urwid.Text):
    def selectable(self) -> bool:
        return True

    def keypress(self, size: tuple[int], key: Optional[str]) -> Optional[str]:
        return key

    def get_cursor_coords(self, size: tuple[int]) -> tuple[int, int]:
        return 0, 0

    def render(self, size, focus=False):
        canv = super().render(size, focus)
        if focus:
            canv = urwid.CompositeCanvas(canv)
            canv.cursor = 0, 0
        return canv


class DateHeader(SelectableText):
    def __init__(self, day: dt.date, dateformat: str, conf) -> None:
        """
        :param day: the date that is represented by this DateHeader instance
        :param dateformat: format to print `day` in
        """
        self._day = day
        self._dateformat = dateformat
        self._conf = conf
        super().__init__('', wrap='clip')
        self.update_date_line()

    def update_date_line(self) -> None:
        """update self, so that the timedelta is accurate

        to be called after a date change
        """
        self.set_text(self.relative_day(self._day, self._dateformat))

    def relative_day(self, day: dt.date, dtformat: str) -> str:
        """convert day into a string with its weekday and relative distance to today

        :param day: day to be converted
        :param dtformat: the format day is to be printed in, passed to strftime
        """

        weekday = day.strftime('%A')
        daystr = day.strftime(dtformat)
        if day == dt.date.today():
            return f'Today ({weekday}, {daystr})'
        elif day == dt.date.today() + dt.timedelta(days=1):
            return f'Tomorrow ({weekday}, {daystr})'
        elif day == dt.date.today() - dt.timedelta(days=1):
            return f'Yesterday ({weekday}, {daystr})'

        approx_delta = utils.relative_timedelta_str(day)

        return f'{weekday}, {daystr} ({approx_delta})'

    def keypress(self, size: tuple[int], key: Optional[str]) -> Optional[str]:
        binds = self._conf['keybindings']
        if key in binds['left']:
            key = 'left'
        elif key in binds['up']:
            key = 'up'
        elif key in binds['right']:
            key = 'right'
        elif key in binds['down']:
            key = 'down'
        return key


class U_Event(urwid.Text):
    def __init__(self, event, conf, delete_status, this_date=None, relative=True) -> None:
        """representation of an event in EventList

        :param event: the encapsulated event
        :type event: khal.event.Event
        """
        if relative:
            if isinstance(this_date, dt.datetime) or not isinstance(this_date, dt.date):
                raise ValueError(f'`this_date` is of type `{type(this_date)}`, '
                                 'should be `datetime.date`')
        self.event = event
        self.delete_status = delete_status
        self.this_date = this_date
        self._conf = conf
        self.relative = relative
        super().__init__('', wrap='clip')
        self.set_title()

    def get_cursor_coords(self, size) -> tuple[int, int]:
        return 0, 0

    def render(self, size, focus=False):
        canv = super().render(size, focus)
        if focus:
            canv = urwid.CompositeCanvas(canv)
            canv.cursor = 0, 0
        return canv

    @classmethod
    def selectable(cls) -> bool:
        return True

    @property
    def uid(self) -> str:
        return self.event.calendar + '\n' + \
            str(self.event.href) + '\n' + str(self.event.etag)

    @property
    def recuid(self) -> tuple[str, str]:
        return (self.uid, self.event.recurrence_id)

    def set_title(self, mark: str=' ') -> None:
        mark = {
            DeletionType.ALL: 'D',
            DeletionType.INSTANCES: 'd',
            None: '',
        }[self.delete_status(self.recuid)]
        if self.relative:
            format_ = self._conf['view']['agenda_event_format']
        else:
            format_ = self._conf['view']['event_format']
        formatter_ = utils.human_formatter(format_, colors=False)
        if self.this_date:
            date_ = self.this_date
        elif self.event.allday:
            date_ = self.event.start
        else:
            date_ = self.event.start.date()
        text = formatter_(self.event.attributes(date_, colors=False))
        if self._conf['locale']['unicode_symbols']:
            newline = ' \N{LEFTWARDS ARROW WITH HOOK} '
        else:
            newline = ' -- '

        self.set_text(mark + ' ' + text.replace('\n', newline))

    def keypress(self, size: tuple[int], key: Optional[str]) -> Optional[str]:
        binds = self._conf['keybindings']
        if key in binds['left']:
            key = 'left'
        elif key in binds['up']:
            key = 'up'
        elif key in binds['right']:
            key = 'right'
        elif key in binds['down']:
            key = 'down'
        return key


class EventListBox(urwid.ListBox):
    """Container for list of U_Events"""

    def __init__(
            self, *args, parent, conf,
            delete_status, toggle_delete_instance, toggle_delete_all,
            set_focus_date_callback=None,
            **kwargs) -> None:
        self._init: bool = True
        self.parent: 'ClassicView' = parent
        self.delete_status = delete_status
        self.toggle_delete_instance = toggle_delete_instance
        self.toggle_delete_all = toggle_delete_all
        self._conf = conf
        self._old_focus = None
        self.set_focus_date_callback = set_focus_date_callback
        super().__init__(*args, **kwargs)

    def keypress(self, size: tuple[int], key: Optional[str]) -> Optional[str]:
        return super().keypress(size, key)

    @property
    def focus_event(self) -> Optional[U_Event]:
        if self.focus is None:
            return None
        else:
            return self.focus.original_widget

    def refresh_titles(self, min_date, max_date, everything):
        """Refresh only the currently focused event's title

        as we currently only use `EventListBox` in search and there we can only
        modify the currently focused event, no real implementation is needad at
        this time

        ignores all arguments
        """
        self.focus.original_widget.set_title()


class DListBox(EventListBox):
    """Container for a DayWalker"""
    # XXX unfortunate naming, there is also DateListBox

    def __init__(self, *args, **kwargs) -> None:
        dynamic_days = kwargs.pop('dynamic_days', True)
        super().__init__(*args, **kwargs)
        self._init = dynamic_days

    def render(self, size, focus=False):
        if self._init:
            self._init = False
        while not isinstance(self.body, StaticDayWalker) and 'bottom' in self.ends_visible(size):
            self.body._autoextend()
        return super().render(size, focus)

    def clean(self):
        """reset event most recently in focus"""
        if self._old_focus is not None:
            try:
                self.body[self._old_focus].body[0].set_attr_map({None: 'date'})
            except IndexError:
                # after reseting the EventList, the old focus might not exist
                pass

    def ensure_date(self, day: dt.date) -> None:
        """ensure an entry for `day` exists and bring it into focus"""
        try:
            self._old_focus = self.focus_position
        except IndexError:
            pass
        self.body.ensure_date(day)
        self.clean()

    def keypress(self, size: tuple[int], key: Optional[str]) -> Optional[str]:
        if key in self._conf['keybindings']['up']:
            key = 'up'
        if key in self._conf['keybindings']['down']:
            key = 'down'

        if key in self._conf['keybindings']['today']:
            self.parent.calendar.base_widget.set_focus_date(dt.date.today())

        rval = super().keypress(size, key)
        self.clean()
        if key in ['up', 'down']:
            try:
                self._old_focus = self.focus_position
            except IndexError:
                pass
            day = self.body[self.body.focus].date

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
        return self.body.focus_event

    @property
    def current_date(self) -> dt.date:
        return self.body.current_day

    def refresh_titles(self, start, end, recurring):
        self.body.refresh_titles(start, end, recurring)

    def update_date_line(self):
        self.body.update_date_line()


class DayWalker(urwid.SimpleFocusListWalker):
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

        super().__init__([])
        self.ensure_date(this_date)


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

    def update_range(self, start: dt.date, end: dt.date, everything: bool=False):
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

    def _get_events(self, day: dt.date) -> urwid.Widget:
        """get all events on day, return a DateListBox of `U_Event()`s """
        event_list = []
        date_header = DateHeader(
            day=day,
            dateformat=self._conf['locale']['longdateformat'],
            conf=self._conf,
        )
        event_list.append(urwid.AttrMap(date_header, 'date'))
        self.events = sorted(self._collection.get_events_on(day))
        event_list.extend([
            urwid.AttrMap(
                U_Event(event, conf=self._conf, this_date=day, delete_status=self.delete_status),
                'calendar ' + event.calendar, 'reveal focus')
            for event in self.events])
        return urwid.BoxAdapter(
            DateListBox(urwid.SimpleFocusListWalker(event_list), date=day),
            (len(event_list) + 1) if self.events else 1
        )

    def selectable(self) -> bool:
        """mark this widget as selectable"""
        return True

    @property
    def focus_event(self) -> U_Event:
        return self[self.focus].original_widget.focus_event

    @property
    def current_day(self) -> dt.date:
        return self[self.focus].original_widget.date

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
        num_days = max(1, self._conf['default']['timedelta'].days)

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

    def update_range(self, start: dt.date, end: dt.date, everything: bool=False):
        """refresh contents of all days between start and end (inclusive)"""
        start = start.date() if isinstance(start, dt.datetime) else start
        end = end.date() if isinstance(end, dt.datetime) else end

        update = everything
        for one in self:
            if (start <= one.date <= end):
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

    def __init__(self, content, date) -> None:
        self.date = date
        super().__init__(content)

    def __repr__(self) -> str:
        return f'<DateListBox {self.date}>'

    __str__ = __repr__

    def render(self, size, focus):
        if focus:
            self.body[0].set_attr_map({None: 'date header focused'})
        elif DateListBox.selected_date == self.date:
            self.body[0].set_attr_map({None: 'date header selected'})
        else:
            self.reset_style()
        return super().render(size, focus)

    def reset_style(self):
        self.body[0].set_attr_map({None: 'date header'})

    def set_selected_date(self, day: dt.date) -> None:
        """Mark `day` as selected

        :param day: day to mark as selected
        """
        DateListBox.selected_date = day
        # we need to touch the title's content to make sure
        # that urwid re-renders the title
        title = self.body[0].original_widget
        title.set_text(title.get_text()[0])

    @property
    def focus_event(self) -> Optional[U_Event]:
        if self.body.focus == 0:
            return None
        else:
            return self.focus.original_widget

    def refresh_titles(self):
        """refresh the titles of all events"""
        for uevent in self.body[1:]:
            if isinstance(uevent._original_widget, U_Event):
                uevent.original_widget.set_title()

    def update_date_line(self):
        """update the date text in the first line, e.g., if the current date changed"""
        self.body[0].original_widget.update_date_line()


class EventColumn(urwid.WidgetWrap):
    """Container for list of events

    Handles modifying events, showing events' details and editing them
    """

    def __init__(self, elistbox, pane) -> None:
        self.pane = pane
        self._conf = pane._conf
        self.divider = urwid.Divider('─')
        self.editor = False
        self._last_focused_date: Optional[dt.date] = None
        self._eventshown: Optional[tuple[str, str]] = None
        self.event_width = int(self.pane._conf['view']['event_view_weighting'])
        self.delete_status = pane.delete_status
        self.toggle_delete_all = pane.toggle_delete_all
        self.toggle_delete_instance = pane.toggle_delete_instance
        self.dlistbox: DListBox = elistbox
        self.container = urwid.Pile([self.dlistbox])
        urwid.WidgetWrap.__init__(self, self.container)

    @property
    def focus_event(self) -> Optional[U_Event]:
        """returns the event currently in focus"""
        return self.dlistbox.focus_event

    def view(self, event):
        """show event in the lower part of this column"""
        self.container.contents.append((self.divider, ('pack', None)))
        self.container.contents.append(
            (EventDisplay(self.pane._conf, event, collection=self.pane.collection),
             ('weight', self.event_width)))

    def clear_event_view(self):
        while len(self.container.contents) > 1:
            self.container.contents.pop()

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
        if everything:
            min_date = self.dlistbox.body.first_date
            max_date = self.dlistbox.body.last_date
        self.dlistbox.body.update_range(min_date, max_date)

    def refresh_titles(self, min_date: dt.date, max_date: dt.date, everything: bool) -> None:
        """refresh titles in DateListBoxes

        if `everything` is True, reset all displayed dates, else only those between
        min_date and max_date
        """
        self.dlistbox.refresh_titles(min_date, max_date, everything)

    def update_date_line(self) -> None:
        """refresh titles in DateListBoxes"""
        self.dlistbox.update_date_line()

    def edit(self, event, always_save: bool=False, external_edit: bool=False) -> None:
        """create an EventEditor and display it

        :param event: event to edit
        :type event: khal.event.Event
        :param always_save: even save the event if it hasn't changed
        """
        if event.readonly:
            self.pane.window.alert(
                ('alert', f'Calendar `{event.calendar}` is read-only.'))
            return

        if isinstance(event.start_local, dt.datetime):
            original_start = event.start_local.date()
        else:
            original_start = event.start_local
        if isinstance(event.end_local, dt.datetime):
            original_end = event.end_local.date()
        else:
            original_end = event.end_local

        def update_colors(new_start: dt.date, new_end: dt.date, everything: bool=False):
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
                new_event.start_local,
                new_event.end_local,
                (event.recurring or new_event.recurring)
            )
        else:
            self.editor = True
            editor = EventEditor(self.pane, event, update_colors, always_save=always_save)

            ContainerWidget = linebox[self.pane._conf['view']['frame']]
            new_pane = urwid.Columns([
                ('weight', 2, CAttrMap(ContainerWidget(editor), 'editor', 'editor focus')),
                ('weight', 1, CAttrMap(ContainerWidget(self.dlistbox), 'reveal focus')),
            ], dividechars=0, focus_column=0)
            new_pane.title = editor.title

            def teardown(data):
                self.editor = False
            self.pane.window.open(new_pane, callback=teardown)

    def export_event(self):
        """export the event in focus as an ICS file"""
        def export_this(_, user_data):
            try:
                self.focus_event.event.export_ics(user_data.get_edit_text())
            except Exception as error:
                self.pane.window.backtrack()
                self.pane.window.alert(('alert', 'Failed to save event: %s' % error))
            else:
                self.pane.window.backtrack()
                self.pane.window.alert('Event successfully exported')

        overlay = urwid.Overlay(
            ExportDialog(
                export_this,
                self.pane.window.backtrack,
                self.focus_event.event,
            ),
            self.pane,
            'center', ('relative', 50), ('relative', 50), None)
        self.pane.window.open(overlay)

    def toggle_delete(self):
        """toggle the delete status of the event in focus"""
        event = self.focus_event

        def delete_this(_):
            self.toggle_delete_instance(event.recuid)
            self.pane.window.backtrack()
            self.refresh_titles(
                event.event.start_local, event.event.end_local, event.event.recurring)

        def delete_all(_):
            self.toggle_delete_all(event.recuid)
            self.pane.window.backtrack()
            self.refresh_titles(
                event.event.start_local, event.event.end_local, event.event.recurring)

        if event.event.readonly:
            self.pane.window.alert(
                ('alert', f'Calendar {event.event.calendar} is read-only.'),
            )
            return
        status = self.delete_status(event.recuid)
        refresh = True
        if status == DeletionType.ALL:
            self.toggle_delete_all(event.recuid)
        elif status == DeletionType.INSTANCES:
            self.toggle_delete_instance(event.recuid)
        elif event.event.recurring:
            # FIXME if in search results, original pane is used for overlay, not search results
            # also see issue of reseting titles below, probably related
            self.pane.dialog(
                text='This is a recurring event.\nWhich instances do you want to delete?',
                buttons=[
                    ('Only this', delete_this),
                    ('All (past and future)', delete_all),
                    ('Abort', self.pane.window.backtrack),
                ]
            )
            refresh = False
        else:
            self.toggle_delete_all(event.recuid)
        if refresh:
            self.refresh_titles(
                event.event.start_local, event.event.end_local, event.event.recurring)
            event.set_title()  # if we are in search results, refresh_titles doesn't work properly

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
            event.calendar = self.pane.collection.default_calendar_name or \
                self.pane.collection.writable_names[0]
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

    def new(self, date: dt.date, end: Optional[dt.date]=None) -> None:
        """create a new event on `date` at the next full hour and edit it

        :param date: default date for new event
        :param end: date the event ends on (inclusive)
        """
        dtstart: dt.date
        dtend: dt.date
        if not self.pane.collection.writable_names:
            self.pane.window.alert(('alert', 'No writable calendar.'))
            return
        if date is None:
            date = dt.datetime.now()
        if end is None:
            dtstart = dt.datetime.combine(date, dt.time(dt.datetime.now().hour))
            dtend = dtstart + dt.timedelta(minutes=60)
            allday = False
        else:  # TODO XXX why do we use allday if end is not set???
            dtstart = date
            dtend = end + dt.timedelta(days=1)
            allday = True
        event = self.pane.collection.create_event_from_dict({
            'dtstart': dtstart,
            'dtend': dtend,
            'summary': '',
            'timezone': self._conf['locale']['default_timezone'],
            'allday': allday,
            'alarms': timedelta2str(self._conf['default']['default_event_alarm']),
        })
        self.edit(event)

    def selectable(self):
        return True

    def keypress(self, size: tuple[int], key: Optional[str]) -> Optional[str]:
        prev_shown = self._eventshown
        self._eventshown = None
        self.clear_event_view()

        if key in self._conf['keybindings']['new']:
            self.new(self.focus_date, None)
            key = None

        if self.focus_event:
            if key in self._conf['keybindings']['delete']:
                self.toggle_delete()
                key = 'down'
            elif key in self._conf['keybindings']['duplicate']:
                self.duplicate()
                key = None
            elif key in self._conf['keybindings']['export']:
                self.export_event()
                key = None

        rval = super().keypress(size, key)
        if self.focus_event:
            if key in self._conf['keybindings']['view'] and \
                    prev_shown == self.focus_event.recuid:
                # the event in focus is already viewed -> edit
                if self.delete_status(self.focus_event.recuid):
                    self.pane.window.alert(('alert', 'This event is marked as deleted'))
                self.edit(self.focus_event.event)
            elif key in self._conf['keybindings']['external_edit']:
                self.edit(self.focus_event.event, external_edit=True)
            elif key in self._conf['keybindings']['view'] or \
                    self._conf['view']['event_view_always_visible']:
                self._eventshown = self.focus_event.recuid
                self.view(self.focus_event.event)
        return rval

    def render(self, a, focus):
        if focus:
            DateListBox.selected_date = None
        return super().render(a, focus)


class EventDisplay(urwid.WidgetWrap):
    """A widget showing one Event()'s details """

    def __init__(self, conf, event, collection=None) -> None:
        self._conf = conf
        self.collection = collection
        self.event = event
        divider = urwid.Divider(' ')

        lines = []
        lines.append(urwid.Text('Title: ' + event.summary))

        # show organizer
        if event.organizer != '':
            lines.append(urwid.Text('Organizer: ' + event.organizer))

        if event.location != '':
            lines.append(urwid.Text('Location: ' + event.location))

        if event.categories != '':
            lines.append(urwid.Text('Categories: ' + event.categories))

        if event.url != '':
            lines.append(urwid.Text('URL: ' + event.url))

        if event.attendees != '':
            lines.append(urwid.Text('Attendees:'))
            for attendee in event.attendees.split(', '):
                lines.append(urwid.Text(f'  - {attendee}'))

        # start and end time/date
        if event.allday:
            startstr = event.start_local.strftime(self._conf['locale']['dateformat'])
            endstr = event.end_local.strftime(self._conf['locale']['dateformat'])
        else:
            startstr = event.start_local.strftime(
                f"{self._conf['locale']['dateformat']} "
                f"{self._conf['locale']['timeformat']}"
            )
            if event.start_local.date == event.end_local.date:
                endstr = event.end_local.strftime(self._conf['locale']['timeformat'])
            else:
                endstr = event.end_local.strftime(
                    f"{self._conf['locale']['dateformat']} "
                    f"{self._conf['locale']['timeformat']}"
                )

        if startstr == endstr:
            lines.append(urwid.Text('Date: ' + startstr))
        else:
            lines.append(urwid.Text('Date: ' + startstr + ' - ' + endstr))

        lines.append(urwid.Text('Calendar: ' + event.calendar))
        lines.append(divider)

        if event.description != '':
            lines.append(urwid.Text(event.description))

        pile = urwid.Pile(lines)
        urwid.WidgetWrap.__init__(self, urwid.Filler(pile, valign='top'))


class SearchDialog(urwid.WidgetWrap):
    """A Search Dialog Widget"""

    def __init__(self, search_func, abort_func) -> None:

        class Search(Edit):

            def keypress(self, size: tuple[int], key: Optional[str]) -> Optional[str]:
                if key == 'enter':
                    search_func(self.text)
                    return None
                else:
                    return super().keypress(size, key)

        search_field = Search('')

        def this_func(_):
            search_func(search_field.text)

        lines = []
        lines.append(urwid.Text('Please enter a search term (Escape cancels):'))
        lines.append(urwid.AttrMap(search_field, 'edit', 'edit focused'))
        lines.append(urwid.Text(''))
        buttons = NColumns([
            button('Search', on_press=this_func, padding_left=0),
            button('Abort', on_press=abort_func, padding_right=0),
        ])
        lines.append(buttons)
        content = NPile(lines, outermost=True)
        urwid.WidgetWrap.__init__(self, urwid.LineBox(content))


class ClassicView(Pane):
    """default Pane for khal

    showing a CalendarWalker on the left and the eventList + eventviewer/editor
    on the right
    """

    def __init__(self, collection, conf=None, title: str='', description: str='') -> None:
        self.init = True
        # Will be set when opening the view inside a Window
        self.window = None
        self._conf = conf
        self.collection = collection
        self._deleted: dict[int, list[str]] = {DeletionType.ALL: [], DeletionType.INSTANCES: []}

        ContainerWidget = linebox[self._conf['view']['frame']]
        if self._conf['view']['dynamic_days']:
            Walker = DayWalker
        else:
            Walker = StaticDayWalker
        daywalker = Walker(
            dt.date.today(), eventcolumn=self, conf=self._conf,
            delete_status=self.delete_status, collection=self.collection,
        )
        elistbox = DListBox(
            daywalker, parent=self, conf=self._conf,
            delete_status=self.delete_status,
            toggle_delete_all=self.toggle_delete_all,
            toggle_delete_instance=self.toggle_delete_instance,
            dynamic_days=self._conf['view']['dynamic_days'],
        )
        self.eventscolumn = ContainerWidget(
            CAttrMap(EventColumn(pane=self, elistbox=elistbox),
                     'eventcolumn',
                     'eventcolumn focus',
                     ),
        )
        calendar = CAttrMap(CalendarWidget(
            on_date_change=self.eventscolumn.original_widget.set_focus_date,
            keybindings=self._conf['keybindings'],
            on_press={key: self.new_event for key in self._conf['keybindings']['new']},
            firstweekday=self._conf['locale']['firstweekday'],
            weeknumbers=self._conf['locale']['weeknumbers'],
            monthdisplay=self._conf['view']['monthdisplay'],
            get_styles=collection.get_styles
        ), 'calendar', 'calendar focus')
        if self._conf['view']['dynamic_days']:
            elistbox.set_focus_date_callback = calendar.set_focus_date
        else:
            elistbox.set_focus_date_callback = lambda _: None
        self.calendar = ContainerWidget(calendar)
        self.lwidth = 31 if self._conf['locale']['weeknumbers'] == 'right' else 28
        if self._conf['view']['frame'] in ["width", "color"]:
            self.lwidth += 2
        columns = NColumns(
            [(self.lwidth, self.calendar), self.eventscolumn],
            dividechars=0,
            box_columns=[0, 1],
            outermost=True,
        )
        Pane.__init__(self, columns, title=title, description=description)

    def delete_status(self, uid: str) -> Optional[DeletionType]:
        if uid[0] in self._deleted[DeletionType.ALL]:
            return DeletionType.ALL
        elif uid in self._deleted[DeletionType.INSTANCES]:
            return DeletionType.INSTANCES
        else:
            return None

    def toggle_delete_all(self, recuid: tuple[str, str]) -> None:
        uid, _ = recuid
        if uid in self._deleted[DeletionType.ALL]:
            self._deleted[DeletionType.ALL].remove(uid)
        else:
            self._deleted[DeletionType.ALL].append(uid)

    def toggle_delete_instance(self, uid: str) -> None:
        if uid in self._deleted[DeletionType.INSTANCES]:
            self._deleted[DeletionType.INSTANCES].remove(uid)
        else:
            self._deleted[DeletionType.INSTANCES].append(uid)

    def cleanup(self, data):
        """delete all events marked for deletion"""
        # If we delete several recuids from the same vevent, the etag will
        # change after each deletion. As we check for matching etags before
        # deleting, deleting any subsequent recuids will fail.
        # We therefore keep track of the etags of the events we already
        # deleted.
        updated_etags = {}
        for part in self._deleted[DeletionType.ALL]:
            account, href, etag = part.split('\n', 2)
            self.collection.delete(href, etag, account)
        for part, rec_id in self._deleted[DeletionType.INSTANCES]:
            account, href, etag = part.split('\n', 2)
            etag = updated_etags.get(href) or etag
            event = self.collection.delete_instance(href, etag, account, rec_id)
            updated_etags[event.href] = event.etag

    def keypress(self, size: tuple[int], key: Optional[str]) -> Optional[str]:
        binds = self._conf['keybindings']
        if key in binds['search']:
            self.search()
        return super().keypress(size, key)

    def search(self):
        """create a search dialog and display it"""
        overlay = urwid.Overlay(
            SearchDialog(self._search, self.window.backtrack), self,
            align='center',
            width=('relative', 70),
            valign=('relative', 50),
            height=None)
        self.window.open(overlay)

    def _search(self, search_term: str) -> None:
        """search for events matching `search_term"""
        assert self.window is not None
        self.window.backtrack()
        events = sorted(self.collection.search(search_term))
        event_list = []
        event_list.extend([
            urwid.AttrMap(
                U_Event(event, relative=False, conf=self._conf, delete_status=self.delete_status),
                'calendar ' + event.calendar, 'reveal focus')
            for event in events])
        events = EventListBox(
            urwid.SimpleFocusListWalker(event_list), parent=self.eventscolumn, conf=self._conf,
            delete_status=self.delete_status,
            toggle_delete_all=self.toggle_delete_all,
            toggle_delete_instance=self.toggle_delete_instance
        )
        events = EventColumn(pane=self, elistbox=events)
        ContainerWidget = linebox[self._conf['view']['frame']]
        columns = NColumns(
            [(self.lwidth, self.calendar), ContainerWidget(events)],
            dividechars=0,
            box_columns=[0, 0],
            outermost=True,
        )
        pane = Pane(
            columns,
            title=f"Search results for \"{search_term}\" (Esc for backtrack)",
        )
        pane._conf = self._conf
        columns.set_focus_column(1)
        self.window.open(pane)

    def render(self, size, focus=False):
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
    name: str, color: str, hmethod: str, color_mode: Literal['256colors', 'rgb'],
    foreground: str = '', background: str = '',
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
    from ..terminal import COLORS
    if color == '' or color in COLORS or color is None:
        # Named colors already use urwid names, no need to change anything.
        pass
    elif color.isdigit():
        # Colors from the 256 color palette need to be prefixed with h in
        # urwid.
        color = 'h' + color
    elif color_mode == '256color':
        # Convert to some color on the 256 color palette that might resemble
        # the 24-bit color.
        # First, generate the palette (indices 16-255 only). This assumes, that
        # the terminal actually uses the same palette, which may or may not be
        # the case.
        colors = {}
        # Colorcube
        colorlevels = (0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff)
        for r in range(0, 6):
            for g in range(0, 6):
                for b in range(0, 6):
                    colors[r * 36 + g * 6 + b + 16] = \
                        (colorlevels[r], colorlevels[g], colorlevels[b])
        # Grayscale
        graylevels = [0x08 + 10 * i for i in range(0, 24)]
        for c in range(0, 24):
            colors[232 + c] = (graylevels[c], ) * 3
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
        color = 'h' + str(best)
    # We unconditionally add the color to the high color slot. It seems to work
    # in lower color terminals as well.
    if hmethod in ['fg', 'foreground']:
        return (name, '', '', '', color, background)
    else:
        return (name, '', '', '', foreground, color)


def _add_calendar_colors(
    palette: list[tuple[str, ...]],
    collection: 'CalendarCollection',
    color_mode: Literal['256colors', 'rgb'],
    base: Optional[str] = None,
    attr_template: str = 'calendar {}',
) -> list[tuple[str, ...]]:
    """Add the colors for the defined calendars to the palette.

    We support setting a fixed background or foreground color that we extract
    from a giving attribute

    :param palette: the base palette
    :param collection:
    :param color_mode: which color mode we are in
    :param base: the attribute to extract the background and foreground color from
    :param attr_template: the template to use for the attribute name
    :returns: the modified palette
    """
    bg_color, fg_color = '', ''
    for attr in palette:
        if base and attr[0] == base:
            if color_mode == 'rgb' and len(attr) >= 5:
                bg_color = attr[5]
                fg_color = attr[4]
            else:
                bg_color = attr[2]
                fg_color = attr[1]

    for cal in collection.calendars:
        if cal['color'] == '':
            # No color set for this calendar, use default_color instead.
            color = collection.default_color
        else:
            color = cal['color']

        # In case the color contains an alpha value, remove it for urwid.
        # eg '#RRGGBBAA' -> '#RRGGBB' and '#RGBA' -> '#RGB'.
        if color and len(color) == 9 and color[0] == '#':
            color = color[0:7]
        elif color and len(color) == 5 and color[0] == '#':
            color = color[0:4]

        entry = _urwid_palette_entry(
            attr_template.format(cal['name']),
            color,
            collection.hmethod,
            color_mode=color_mode,
            foreground=fg_color,
            background=bg_color,
        )
        palette.append(entry)

    entry = _urwid_palette_entry(
        'highlight_days_color',
        collection.color,
        collection.hmethod,
        color_mode=color_mode,
        foreground=fg_color,
        background=bg_color,
    )
    palette.append(entry)
    entry = _urwid_palette_entry('highlight_days_multiple',
        collection.multiple,
        collection.hmethod,
        color_mode=color_mode,
        foreground=fg_color,
        background=bg_color)
    palette.append(entry)

    return palette


def start_pane(
        pane,
        callback,
        program_info='',
        quit_keys=None,
        color_mode: Literal['rgb', '256colors']='rgb',
):
    """Open the user interface with the given initial pane."""
    # We don't validate the themes in settings.spec but instead here
    # first try to load built-in themes, then try to load themes from
    # plugins
    theme = colors.themes.get(pane._conf['view']['theme'])
    if theme is None:
        theme = plugins.THEMES.get(pane._conf['view']['theme'])
    if theme is None:
        logger.fatal(f'Invalid theme {pane._conf["view"]["theme"]} configured')
        logger.fatal(f'Available themes are: {", ".join(colors.themes.keys())}')
        raise FatalError

    quit_keys = quit_keys or ['q']

    frame = Window(
        footer=program_info + f' | {quit_keys[0]}: quit, ?: help',
        quit_keys=quit_keys,
    )

    class LogPaneFormatter(logging.Formatter):
        def get_prefix(self, level):
            if level >= 50:
                return 'CRITICAL'
            if level >= 40:
                return 'ERROR'
            if level >= 30:
                return 'WARNING'
            if level >= 20:
                return 'INFO'
            else:
                return 'DEBUG'

        def format(self, record) -> str:
            return f'{self.get_prefix(record.levelno)}: {record.msg}'

    class HeaderFormatter(LogPaneFormatter):
        def format(self, record):
            return (
                super().format(record)[:30] + '... '
                f"[Press `{pane._conf['keybindings']['log'][0]}` to view log]"
            )

    class LogPaneHandler(logging.Handler):
        def emit(self, record):
            frame.log(self.format(record))

    class LogHeaderHandler(logging.Handler):
        def emit(self, record):
            frame.alert(self.format(record))

    if len(logger.handlers) > 0 and not isinstance(logger.handlers[-1], logging.FileHandler):
        logger.handlers.pop()

    pane_handler = LogPaneHandler()
    pane_handler.setFormatter(LogPaneFormatter())
    logger.addHandler(pane_handler)

    header_handler = LogHeaderHandler()
    header_handler.setFormatter(HeaderFormatter())
    logger.addHandler(header_handler)

    frame.open(pane, callback)
    palette = _add_calendar_colors(
        theme, pane.collection, color_mode=color_mode,
        base='calendar', attr_template='calendar {}',
    )
    palette = _add_calendar_colors(
        palette, pane.collection, color_mode=color_mode,
        base='popupbg', attr_template='calendar {} popup',
    )

    def merge_palettes(pallete_a, pallete_b) -> list[tuple[str, ...]]:
        """Merge two palettes together, with the second palette taking priority."""
        merged = {}
        for entry in pallete_a:
            merged[entry[0]] = entry
        for entry in pallete_b:
            merged[entry[0]] = entry
        return list(merged.values())

    overwrite = [(key, *values) for key, values in pane._conf['palette'].items()]
    palette = merge_palettes(palette, overwrite)
    loop = urwid.MainLoop(
        widget=frame,
        palette=palette,
        unhandled_input=frame.on_key_press,
        pop_ups=True,
        handle_mouse=pane._conf['default']['enable_mouse'],
    )
    frame.loop = loop

    def redraw_today(loop, pane, meta=None):
        meta = meta or {'last_today': None}
        # XXX TODO this currently assumes, today moves forward by exactly one
        # day, but it could either move forward more (suspend-to-disk/ram) or
        # even move backwards
        today = dt.date.today()
        if meta['last_today'] != today:
            meta['last_today'] = today
            pane.calendar.original_widget.reset_styles_range(today - dt.timedelta(days=1), today)
            pane.eventscolumn.original_widget.update_date_line()
        loop.set_alarm_in(60, redraw_today, pane)

    loop.set_alarm_in(60, redraw_today, pane)

    def check_for_updates(loop, pane):
        if pane.collection.needs_update():
            pane.window.alert('detected external vdir modification, updating...')
            pane.collection.update_db()
            pane.eventscolumn.base_widget.update(None, None, everything=True)
            pane.window.alert('detected external vdir modification, updated.')
        loop.set_alarm_in(60, check_for_updates, pane)

    loop.set_alarm_in(60, check_for_updates, pane)

    colors_ = 2**24 if color_mode == 'rgb' else 256
    loop.screen.set_terminal_properties(
        colors=colors_, bright_is_bold=pane._conf['view']['bold_for_light_color'],
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
