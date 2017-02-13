# Copyright (c) 2013-2017 Christian Geier et al.
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

from datetime import date, datetime, time, timedelta
import signal
import sys

import urwid

from .. import utils
from ..khalendar.exceptions import ReadOnlyCalendarError
from . import colors
from .widgets import ExtendedEdit as Edit, NPile, NColumns, NListBox, Choice, AlarmsEditor, \
    linebox
from .base import Pane, Window
from .startendeditor import StartEndEditor
from .calendarwidget import CalendarWidget


#  Overview of how this all meant to fit together:
#
#   +--ClassicView(Pane)---------------------------------------+
#   |                                                          |
#   | +-CalendarWidget--+ +----EventColumn-------------------+ |
#   | |                 | |                                  | |
#   | |                 | | +-DListBox---------------------+ | |
#   | |                 | | |                              | | |
#   | |                 | | | +-DayWalker----------------+ | | |
#   | |                 | | | |                          | | | |
#   | |                 | | | | +-BoxAdapter-----------+ | | | |
#   | |                 | | | | |                      | | | | |
#   | |                 | | | | | +-DateListBox------+ | | | | |
#   | |                 | | | | | | DateHeader       | | | | | |
#   | |                 | | | | | | U_Event          | | | | | |
#   | |                 | | | | | |  ...             | | | | | |
#   | |                 | | | | | | U_Event          | | | | | |
#   | |                 | | | | | +------------------+ | | | | |
#   | |                 | | | | +----------------------+ | | | |
#   | |                 | | | |       ...                | | | |
#   | |                 | | | | +-BoxAdapter-----------+ | | | |
#   | |                 | | | | |                      | | | | |
#   | |                 | | | | | +-DateListBox------+ | | | | |
#   | |                 | | | | | | DateHeader       | | | | | |
#   | |                 | | | | | | U_Event          | | | | | |
#   | |                 | | | | | |  ...             | | | | | |
#   | |                 | | | | | | U_Event          | | | | | |
#   | |                 | | | | | +------------------+ | | | | |
#   | |                 | | | | +----------------------+ | | | |
#   | |                 | | | +--------------------------+ | | |
#   | |                 | | +------------------------------+ | |
#   | +-----------------+ +----------------------------------+ |
#   +----------------------------------------------------------+

NOREPEAT = 'No'
ALL = 1
INSTANCES = 2


class DateConversionError(Exception):
    pass


class SelectableText(urwid.Text):
    def selectable(self):
        return True

    def keypress(self, size, key):
        return key

    def get_cursor_coords(self, size):
        return 0, 0

    def render(self, size, focus=False):
        canv = super().render(size, focus)
        if focus:
            canv = urwid.CompositeCanvas(canv)
            canv.cursor = 0, 0
        return canv


class DateHeader(SelectableText):
    def __init__(self, day, dateformat):
        """
        :type day: datetime.date
        :type dateformat: format to print `day` in
        :type dateformat: str
        """
        self._day = day
        self._dateformat = dateformat
        super().__init__('')
        self.update_date_line()

    def update_date_line(self):
        """update self, so that the timedelta is accurate

        to be called after a date change
        """
        self.set_text(self.relative_day(self._day, self._dateformat))

    def relative_day(self, day, dtformat):
        """convert day into a string with its weekday and relative distance to today

        :param day: day to be converted
        :type: day: datetime.day
        :param dtformat: the format day is to be printed in, passed to strftime
        :tpye dtformat: str
        :rtype: str
        """

        weekday = day.strftime('%A')
        daystr = day.strftime(dtformat)
        if day == date.today():
            return 'Today ({}, {})'.format(weekday, daystr)
        elif day == date.today() + timedelta(days=1):
            return 'Tomorrow ({}, {})'.format(weekday, daystr)
        elif day == date.today() - timedelta(days=1):
            return 'Yesterday ({}, {})'.format(weekday, daystr)

        approx_delta = utils.relative_timedelta_str(day)

        return '{weekday}, {day} ({approx_delta})'.format(
            weekday=weekday,
            approx_delta=approx_delta,
            day=day.strftime('%A'),
        )


class U_Event(urwid.Text):
    def __init__(self, event, conf, delete_status, this_date=None, relative=True):
        """representation of an event in EventList

        :param event: the encapsulated event
        :type event: khal.event.Event
        """
        if relative:
            if isinstance(this_date, datetime) or not isinstance(this_date, date):
                raise ValueError('`this_date` is of type `{}`, sould be '
                                 '`datetime.date`'.format(type(this_date)))
        self.event = event
        self.delete_status = delete_status
        self.this_date = this_date
        self._conf = conf
        self.relative = relative
        super().__init__('', wrap='clip')
        self.set_title()

    def get_cursor_coords(self, size):
        return 0, 0

    def render(self, size, focus=False):
        canv = super().render(size, focus)
        if focus:
            canv = urwid.CompositeCanvas(canv)
            canv.cursor = 0, 0
        return canv

    @classmethod
    def selectable(cls):
        return True

    @property
    def uid(self):
        return self.event.calendar + '\n' + \
            str(self.event.href) + '\n' + str(self.event.etag)

    @property
    def recuid(self):
        return (self.uid, self.event.recurrence_id)

    def set_title(self, mark=' '):
        mark = {ALL: 'D', INSTANCES: 'd', False: ''}[self.delete_status(self.recuid)]
        if self.relative:
            format_ = self._conf['view']['agenda_event_format']
        else:
            format_ = self._conf['view']['event_format']
        if self.this_date:
            date_ = self.this_date
        elif self.event.allday:
            date_ = self.event.start
        else:
            date_ = self.event.start.date()
        text = self.event.format(format_, date_, colors=False)
        if self._conf['locale']['unicode_symbols']:
            newline = ' \N{LEFTWARDS ARROW WITH HOOK} '
        else:
            newline = ' -- '

        self.set_text(mark + ' ' + text.replace('\n', newline))

    def keypress(self, _, key):
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
            **kwargs):
        self._init = True
        self.parent = parent
        self.delete_status = delete_status
        self.toggle_delete_instance = toggle_delete_instance
        self.toggle_delete_all = toggle_delete_all
        self._conf = conf
        self._old_focus = None
        self.set_focus_date_callback = set_focus_date_callback
        super().__init__(*args, **kwargs)

    def keypress(self, size, key):
        return super().keypress(size, key)

    @property
    def focus_event(self):
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
    def __init__(self, *args, **kwargs):
        dynamic_days = kwargs.pop('dynamic_days', True)
        super().__init__(*args, **kwargs)
        self._init = dynamic_days

    def render(self, size, focus=False):
        if self._init:
            while 'bottom' in self.ends_visible(size):
                self.body._autoextend()
            self._init = False
        return super().render(size, focus)

    def clean(self):
        """reset event most recently in focus"""
        if self._old_focus is not None:
            self.body[self._old_focus].body[0].set_attr_map({None: 'date'})

    def ensure_date(self, day):
        """ensure an entry for `day` exists and bring it into focus"""
        try:
            self._old_focus = self.focus_position
        except IndexError:
            pass
        rval = self.body.ensure_date(day)
        self.clean()
        return rval

    def keypress(self, size, key):
        if key in self._conf['keybindings']['up']:
            key = 'up'
        if key in self._conf['keybindings']['down']:
            key = 'down'

        if key in self._conf['keybindings']['today']:
            self.parent.calendar.base_widget.set_focus_date(date.today())

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
    def current_date(self):
        return self.body.current_day

    def refresh_titles(self, start, end, recurring):
        self.body.refresh_titles(start, end, recurring)

    def update_date_line(self):
        self.body.update_date_line()


class DayWalker(urwid.SimpleFocusListWalker):
    """A list Walker that contains a list of DateListBox objects, each representing
    one day and associated events"""

    def __init__(self, this_date, eventcolumn, conf, collection, delete_status):
        self.eventcolumn = eventcolumn
        self._conf = conf
        self.delete_status = delete_status
        self._init = True
        self._last_day = this_date
        self._first_day = this_date
        self._collection = collection

        super().__init__(list())
        self.ensure_date(this_date)

    def ensure_date(self, day):
        """make sure a DateListBox for `day` exists, update it and bring it into focus"""
        # TODO this function gets called twice on every date change, not necessary but
        # isn't very costly either
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

    def update_events_ondate(self, day):
        """refresh the contents of the day's DateListBox"""
        offset = (day - self[0].date).days
        assert self[offset].date == day
        self[offset] = self._get_events(day)

    def refresh_titles(self, start, end, everything):
        """refresh events' titles

        if `everything` is True, reset all titles, otherwise only
        those between `start` and `end`

        :type start: datetime.date
        :type end: datetime.date
        :type bool: bool
        """
        start = start.date() if isinstance(start, datetime) else start
        end = end.date() if isinstance(end, datetime) else end

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

    def update_range(self, start, end, everything=False):
        """refresh contents of all days between start and end (inclusive)

        :type start: datetime.date
        :type end: datetime.date
        """
        start = start.date() if isinstance(start, datetime) else start
        end = end.date() if isinstance(end, datetime) else end

        if everything:
            start = self[0].date
            end = self[-1].date
        else:
            start = max(self[0].date, start)
            end = min(self[-1].date, end)

        day = start
        while day <= end:
            self.update_events_ondate(day)
            day += timedelta(days=1)

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
        self._last_day += timedelta(days=1)
        pile = self._get_events(self._last_day)
        self.append(pile)

    def _autoprepend(self):
        """prepend the day before the first day to ourself"""
        # we need to actively reset the last element's attribute, as their
        # render() method does not get called otherwise, and they would
        # be indicated as the currently selected date
        self[self.focus or 0].reset_style()
        self._first_day -= timedelta(days=1)
        pile = self._get_events(self._first_day)
        self.insert(0, pile)

    def _get_events(self, day):
        """get all events on day, return a DateListBox of `U_Event()`s

        :type day: datetime.date
        """
        event_list = list()
        date_header = DateHeader(
            day=day,
            dateformat=self._conf['locale']['longdateformat'],
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

    def selectable(self):
        """mark this widget as selectable"""
        return True

    @property
    def focus_event(self):
        return self[self.focus].original_widget.focus_event

    @property
    def current_day(self):
        return self[self.focus].original_widget.date


class StaticDayWalker(DayWalker):
    """Only show events for a fixed number of days."""

    def ensure_date(self, day):
        """make sure a DateListBox for `day` exists, update it and bring it into focus"""
        # TODO cache events for each day and update as needed
        num_days = max(1, self._conf['default']['timedelta'].days)

        for delta in range(num_days):
            pile = self._get_events(day + timedelta(days=delta))
            if len(self) <= delta:
                self.append(pile)
            else:
                self[delta] = pile
        assert self[0].date == day

    def update_events_ondate(self, day):
        """refresh the contents of the day's DateListBox"""
        self[0] = self._get_events(day)

    def refresh_titles(self, start, end, everything):
        """refresh events' titles

        if `everything` is True, reset all titles, otherwise only
        those between `start` and `end`

        :type start: datetime.date
        :type end: datetime.date
        :type bool: bool
        """
        for one in self:
            one.refresh_titles()

    def update_range(self, start, end, everything=False):
        """refresh contents of all days between start and end (inclusive)

        :type start: datetime.date
        :type end: datetime.date
        """
        start = start.date() if isinstance(start, datetime) else start
        end = end.date() if isinstance(end, datetime) else end

        update = everything
        for one in self:
            if (start <= one.date <= end):
                update = True
        if update:
            self.ensure_date(self[0].date)

    def set_focus(self, position):
        """set focus by item number"""
        return urwid.SimpleFocusListWalker.set_focus(self, position)


class DateListBox(NListBox):
    """A ListBox container for a SimpleFocusListWalker, that contains one day
    worth of events"""

    selected_date = None

    def __init__(self, content, date):
        self.date = date
        super().__init__(content)

    def __repr__(self):
        return '<DateListBox {}>'.format(self.date)

    __str__ = __repr__

    def render(self, size, focus):
        if focus:
            self.body[0].set_attr_map({None: 'date focused'})
        elif DateListBox.selected_date == self.date:
            self.body[0].set_attr_map({None: 'date selected'})
        else:
            self.reset_style()
        return super().render(size, focus)

    def reset_style(self):
        self.body[0].set_attr_map({None: 'date'})

    def set_selected_date(self, day):
        """Mark `day` as selected

        :param day: day to mark as selected
        :type day: datetime.date
        """
        DateListBox.selected_date = day
        # we need to touch the title's content to make sure
        # that urwid re-renders the title
        title = self.body[0].original_widget
        title.set_text(title.get_text()[0])

    @property
    def focus_event(self):
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

    def __init__(self, elistbox, pane):
        self.pane = pane
        self._conf = pane._conf
        self.divider = urwid.Divider('─')
        self.editor = False
        self._current_date = None
        self._eventshown = False
        self.event_width = int(self.pane._conf['view']['event_view_weighting'])
        self.delete_status = pane.delete_status
        self.toggle_delete_all = pane.toggle_delete_all
        self.toggle_delete_instance = pane.toggle_delete_instance
        self.dlistbox = elistbox
        self.container = urwid.Pile([self.dlistbox])
        urwid.WidgetWrap.__init__(self, self.container)

    @property
    def focus_event(self):
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
    def focus_date(self):
        return self._current_date

    @focus_date.setter
    def focus_date(self, date):
        self._current_date = date
        self.dlistbox.ensure_date(date)

    def update(self, min_date, max_date, everything):
        """update DateListBox

        if `everything` is True, reset all displayed dates, else only those between
        min_date and max_date
        """
        if everything:
            min_date = self.pane.calendar.base_widget.walker.earliest_date
            max_date = self.pane.calendar.base_widget.walker.latest_date
        self.pane.base_widget.calendar.base_widget.reset_styles_range(min_date, max_date)
        self.dlistbox.body.update_range(min_date, max_date)

    def refresh_titles(self, min_date, max_date, everything):
        """refresh titles in DateListBoxes

        if `everything` is True, reset all displayed dates, else only those between
        min_date and max_date
        """
        self.dlistbox.refresh_titles(min_date, max_date, everything)

    def update_date_line(self):
        """refresh titles in DateListBoxes"""
        self.dlistbox.update_date_line()

    def edit(self, event, always_save=False):
        """create an EventEditor and display it

        :param event: event to edit
        :type event: khal.event.Event
        :param always_save: even save the event if it hasn't changed
        :type always_save: bool
        """
        if event.readonly:
            self.pane.window.alert(
                ('light red', 'Calendar {} is read-only.'.format(event.calendar)))
            return

        if isinstance(event.start_local, datetime):
            original_start = event.start_local.date()
        else:
            original_start = event.start_local
        if isinstance(event.end_local, datetime):
            original_end = event.end_local.date()
        else:
            original_end = event.end_local

        def update_colors(new_start, new_end, everything=False):
            """reset colors in the calendar widget and dates in DayWalker
            between min(new_start, original_start)

            :type new_start: datetime.date
            :type new_end: datetime.date
            :param everything: set to True if event is a recurring one, than everything
                  gets reseted
            """
            # TODO cleverer support for recurring events, where more than start and
            # end dates are affected (complicated)
            if isinstance(new_start, datetime):
                new_start = new_start.date()
            if isinstance(new_end, datetime):
                new_end = new_end.date()
            start = min(original_start, new_start)
            end = max(original_end, new_end)
            self.pane.eventscolumn.base_widget.update(start, end, everything)

        if self.editor:
            self.pane.window.backtrack()

        assert not self.editor
        self.editor = True
        editor = EventEditor(self.pane, event, update_colors, always_save=always_save)

        ContainerWidget = linebox[self.pane._conf['view']['frame']]
        new_pane = urwid.Columns([
            ('weight', 2, ContainerWidget(editor)),
            ('weight', 1, ContainerWidget(self.dlistbox))
        ], dividechars=0, focus_column=0)
        new_pane.title = editor.title
        new_pane.get_keys = editor.get_keys

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
                self.pane.window.alert(
                    ('light red', 'Failed to save event: %s' % error))
            else:
                self.pane.window.backtrack()
                self.pane.window.alert(
                    ('light green', 'Event successfuly exported'))

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
            self.eventcolumn.pane.window.alert(
                ('light red',
                 'Calendar {} is read-only.'.format(self.event.calendar)))
            return
        status = self.delete_status(event.recuid)
        refresh = True
        if status == ALL:
            self.toggle_delete_all(event.recuid)
        elif status == INSTANCES:
            self.toggle_delete_instance(event.recuid)
        elif event.event.recurring:
            # FIXME if in search results, original pane is used for overlay, not search results
            # also see issue of reseting titles below, probably related
            overlay = urwid.Overlay(
                DeleteDialog(
                    delete_this,
                    delete_all,
                    self.pane.window.backtrack,
                ),
                self.pane,
                'center', ('relative', 70), ('relative', 70), None)
            self.pane.window.open(overlay)
            refresh = False
        else:
            self.toggle_delete_all(event.recuid)
        if refresh:
            self.refresh_titles(
                event.event.start_local, event.event.end_local, event.event.recurring)
            event.set_title()  # if we are in search results, refresh_titles doesn't work properly

    def duplicate(self):
        """duplicate the event in focus"""
        # TODO copying from birthday calendars is currently problematic
        # because their title is determined by X-BIRTHDAY and X-FNAME properties
        # which are also copied. If the events's summary is edited it will show
        # up on disk but not be displayed in khal
        event = self.focus_event.event.duplicate()
        try:
            self.pane.collection.new(event)
        except ReadOnlyCalendarError:
            event.calendar = self.pane.collection.default_calendar_name or \
                self.pane.collection.writable_names[0]
            self.edit(event, always_save=True)
        start_date, end_date = event.start_local, event.end_local
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()
        self.pane.eventscolumn.base_widget.update(start_date, end_date, event.recurring)
        try:
            self._old_focus = self.focus_position
        except IndexError:
            pass

    def new(self, date, end=None):
        """create a new event on `date` at the next full hour and edit it

        :param date: default date for new event
        :type date: datetime.date
        :param end: optional, date the event ends on (inclusive)
        :type end: datetime.date
        """
        if not self.pane.collection.writable_names:
            self.pane.window.alert(('light red', 'No writable calendar.'))
            return
        if end is None:
            start = datetime.combine(date, time(datetime.now().hour))
            end = start + timedelta(minutes=60)
            event = utils.new_event(
                dtstart=start, dtend=end, summary="new event",
                timezone=self._conf['locale']['default_timezone'],
                locale=self._conf['locale'],
            )
        else:
            event = utils.new_event(
                dtstart=date, dtend=end + timedelta(days=1), summary="new event",
                allday=True, locale=self._conf['locale'],
            )
        event = self.pane.collection.new_event(
            event.to_ical(), self.pane.collection.default_calendar_name)
        self.edit(event)

    def selectable(self):
        return True

    def keypress(self, size, key):
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
            if key in self._conf['keybindings']['view'] or \
                    self._conf['view']['event_view_always_visible']:
                if self._eventshown == self.focus_event.recuid:
                    # the event in focus is already viewed -> edit
                    self.clear_event_view()  # do not move before the if condition
                    if self.delete_status(self.focus_event.recuid):
                        self.pane.window.alert(('light red', 'This event is marked as deleted'))
                    self.edit(self.focus_event.event)
                else:
                    self.clear_event_view()
                    self._eventshown = self.focus_event.recuid
                    self.view(self.focus_event.event)

        if key in ['esc'] and self._eventshown:
            self.clear_event_view()
            key = None
        return rval

    def render(self, a, focus):
        if focus:
            DateListBox.selected_date = None
        return super().render(a, focus)


class RecurrenceEditor(urwid.WidgetWrap):

    def __init__(self, rrule):
        # TODO: support more recurrence schemes

        self.rrule = rrule
        recurrence = self.rrule['freq'][0].lower() if self.rrule else NOREPEAT
        self.recurrence_choice = Choice(
            [NOREPEAT, u"weekly", u"monthly", u"yearly"], recurrence)
        self.columns = urwid.Columns([(10, urwid.Text('Repeat: ')), (11, self.recurrence_choice)])
        urwid.WidgetWrap.__init__(self, self.columns)

    @property
    def changed(self):
        if self.recurrence_choice.changed:
            return True
        return False

    @property
    def active(self):
        recurrence = self.recurrence_choice.active
        if recurrence != NOREPEAT:
            self.rrule["freq"] = [recurrence]
            return self.rrule
        return None

    @active.setter
    def active(self, val):
        self.recurrence_choice.active = val


class EventDisplay(urwid.WidgetWrap):
    """A widget showing one Event()'s details """

    def __init__(self, conf, event, collection=None):
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

        # start and end time/date
        if event.allday:
            startstr = event.start_local.strftime(self._conf['locale']['dateformat'])
            endstr = event.end_local.strftime(self._conf['locale']['dateformat'])
        else:
            startstr = event.start_local.strftime(
                '{} {}'.format(self._conf['locale']['dateformat'],
                               self._conf['locale']['timeformat'])
            )
            if event.start_local.date == event.end_local.date:
                endstr = event.end_local.strftime(self._conf['locale']['timeformat'])
            else:
                endstr = event.end_local.strftime(
                    '{} {}'.format(self._conf['locale']['dateformat'],
                                   self._conf['locale']['timeformat'])
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


class EventEditor(urwid.WidgetWrap):
    """Widget that allows Editing one `Event()`"""

    def __init__(self, pane, event, save_callback=None, always_save=False):
        """
        :type event: khal.event.Event
        :param save_callback: call when saving event with new start and end
             dates and recursiveness of original and edited event as parameters
        :type save_callback: callable
        :param always_save: save event even if it has not changed
        :type always_save: bool
        """

        self.pane = pane
        self.event = event
        self._save_callback = save_callback

        self.collection = pane.collection
        self._conf = pane._conf

        self._abort_confirmed = False

        self.description = event.description
        self.location = event.location
        self.categories = event.categories
        self.startendeditor = StartEndEditor(
            event.start_local, event.end_local, self._conf,
            self.pane.eventscolumn.original_widget.set_focus_date)
        self.recurrenceeditor = RecurrenceEditor(self.event.recurobject)
        self.summary = Edit(caption='Title: ', edit_text=event.summary)

        divider = urwid.Divider(' ')

        def decorate_choice(c):
            return ('calendar ' + c['name'], c['name'])

        self.calendar_chooser = Choice(
            [self.collection._calendars[c] for c in self.collection.writable_names],
            self.collection._calendars[self.event.calendar],
            decorate_choice
        )
        self.description = Edit(caption='Description: ',
                                edit_text=self.description, multiline=True)
        self.location = Edit(caption='Location: ',
                             edit_text=self.location)
        self.categories = Edit(caption='Categories: ',
                               edit_text=self.categories)
        self.alarms = AlarmsEditor(self.event)
        self.pile = NListBox(urwid.SimpleFocusListWalker([
            NColumns([self.summary, self.calendar_chooser], dividechars=2),
            divider,
            self.location,
            self.categories,
            self.description,
            divider,
            self.startendeditor,
            self.recurrenceeditor,
            divider,
            self.alarms,
            divider,
            urwid.Button('Save', on_press=self.save),
            urwid.Button('Export', on_press=self.export)
        ]), outermost=True)
        self._always_save = always_save
        urwid.WidgetWrap.__init__(self, self.pile)

    @property
    def title(self):  # Window title
        return 'Edit: {}'.format(self.summary.get_edit_text())

    def get_keys(self):
        return [(['arrowsu'], 'navigate through properties'),
                (['enter'], 'edit property'),
                (['esc'], 'abort')]

    @classmethod
    def selectable(cls):
        return True

    @property
    def changed(self):
        if self.summary.get_edit_text() != self.event.summary:
            return True
        if self.description.get_edit_text() != self.event.description:
            return True
        if self.location.get_edit_text() != self.event.location:
            return True
        if self.categories.get_edit_text() != self.event.categories:
            return True
        if self.startendeditor.changed or self.calendar_chooser.changed:
            return True
        if self.recurrenceeditor.changed:
            return True
        if self.alarms.changed:
            return True
        return False

    def update_vevent(self):
        self.event.update_summary(self.summary.get_edit_text())
        self.event.update_description(self.description.get_edit_text())
        self.event.update_location(self.location.get_edit_text())
        self.event.update_categories(self.categories.get_edit_text())

        if self.startendeditor.changed:
            self.event.update_start_end(
                self.startendeditor.startdt, self.startendeditor.enddt)
        if self.recurrenceeditor.changed:
            rrule = self.recurrenceeditor.active
            self.event.update_rrule(rrule)

        if self.alarms.changed:
            self.event.update_alarms(self.alarms.get_alarms())

    def export(self, button):
        """
        export the event as ICS
        :param button: not needed, passed via the button press
        """
        def export_this(_, user_data):
            try:
                self.event.export_ics(user_data.get_edit_text())
            except Exception as e:
                self.pane.window.backtrack()
                self.pane.window.alert(
                    ('light red',
                     'Failed to save event: %s' % e))
                return

            self.pane.window.backtrack()
            self.pane.window.alert(
                ('light green',
                 'Event successfuly exported'))

        overlay = urwid.Overlay(
            ExportDialog(
                export_this,
                self.pane.window.backtrack,
                self.event,
            ),
            self.pane,
            'center', ('relative', 50), ('relative', 50), None)
        self.pane.window.open(overlay)

    def save(self, button):
        """saves the event to the db

        (only when it has been changed or always_save is set)
        :param button: not needed, passed via the button press
        """
        if not self.startendeditor.validate():
            self.pane.window.alert(
                ('light red', "Can't save: end date is before start date!"))
            return
        if self._always_save or self.changed is True:
            self.update_vevent()
            self.event.allday = self.startendeditor.allday
            self.event.increment_sequence()
            if self.event.etag is None:  # has not been saved before
                self.event.calendar = self.calendar_chooser.active['name']
                self.collection.new(self.event)
            elif self.calendar_chooser.changed:
                self.collection.change_collection(
                    self.event,
                    self.calendar_chooser.active['name']
                )
            else:
                self.collection.update(self.event)

            self._save_callback(
                self.event.start_local, self.event.end_local,
                self.event.recurring or self.recurrenceeditor.changed,
            )
        self._abort_confirmed = False
        self.pane.window.backtrack()

    def keypress(self, size, key):
        if key in ['esc'] and self.changed and not self._abort_confirmed:
            self.pane.window.alert(
                ('light red', 'Unsaved changes! Hit ESC again to discard.'))
            self._abort_confirmed = True
            return
        else:
            self._abort_confirmed = False
        if key in self.pane._conf['keybindings']['save']:
            self.save(None)
            return
        return super().keypress(size, key)


class DeleteDialog(urwid.WidgetWrap):
    def __init__(self, this_func, all_func, abort_func):
        lines = []
        lines.append(urwid.Text('This is a recurring event.'))
        lines.append(urwid.Text('Which instances do you want to delete?'))
        lines.append(urwid.Text(''))
        buttons = NColumns(
            [urwid.Button('Only this', on_press=this_func),
             urwid.Button('All (past and future)', on_press=all_func),
             urwid.Button('Abort', on_press=abort_func),
             ], outermost=True)
        lines.append(buttons)
        content = urwid.Pile(lines)
        urwid.WidgetWrap.__init__(self, urwid.LineBox(content))


class ExportDialog(urwid.WidgetWrap):
    def __init__(self, this_func, abort_func, event):
        lines = []
        lines.append(urwid.Text('Export event as ICS file'))
        lines.append(urwid.Text(''))
        export_location = Edit(
            caption='Location: ', edit_text="~/%s.ics" % event.summary.strip())
        lines.append(export_location)
        lines.append(urwid.Divider(' '))
        lines.append(
            urwid.Button('Save', on_press=this_func, user_data=export_location)
        )
        content = NPile(lines)
        urwid.WidgetWrap.__init__(self, urwid.LineBox(content))


class SearchDialog(urwid.WidgetWrap):
    """A Search Dialog Widget"""
    def __init__(self, search_func, abort_func):

        class Search(Edit):

            def keypress(self, size, key):
                if key == 'enter':
                    search_func(self.text)
                else:
                    return super().keypress(size, key)

        search_field = Search('')

        def this_func(_):
            search_func(search_field.text)

        lines = []
        lines.append(urwid.Text('Please enter a search term (Escape cancels):'))
        lines.append(search_field)
        buttons = NColumns([urwid.Button('Search', on_press=this_func),
                            urwid.Button('Abort', on_press=abort_func)])
        lines.append(buttons)
        content = NPile(lines, outermost=True)
        urwid.WidgetWrap.__init__(self, urwid.LineBox(content))


class ClassicView(Pane):

    """default Pane for khal

    showing a CalendarWalker on the left and the eventList + eventviewer/editor
    on the right
    """

    def __init__(self, collection, conf=None, title='', description=''):
        self.init = True
        # Will be set when opening the view inside a Window
        self.window = None
        self._conf = conf
        self.collection = collection
        self._deleted = {ALL: [], INSTANCES: []}

        ContainerWidget = linebox[self._conf['view']['frame']]
        if self._conf['view']['dynamic_days']:
            Walker = DayWalker
        else:
            Walker = StaticDayWalker
        daywalker = Walker(
            date.today(), eventcolumn=self, conf=self._conf, delete_status=self.delete_status,
            collection=self.collection,
        )
        elistbox = DListBox(
            daywalker, parent=self, conf=self._conf,
            delete_status=self.delete_status,
            toggle_delete_all=self.toggle_delete_all,
            toggle_delete_instance=self.toggle_delete_instance,
            dynamic_days=self._conf['view']['dynamic_days'],
        )
        self.eventscolumn = ContainerWidget(EventColumn(pane=self, elistbox=elistbox))
        calendar = CalendarWidget(
            on_date_change=self.eventscolumn.original_widget.set_focus_date,
            keybindings=self._conf['keybindings'],
            on_press={key: self.new_event for key in self._conf['keybindings']['new']},
            firstweekday=self._conf['locale']['firstweekday'],
            weeknumbers=self._conf['locale']['weeknumbers'],
            get_styles=collection.get_styles
        )
        if self._conf['view']['dynamic_days']:
            elistbox.set_focus_date_callback = calendar.set_focus_date
        else:
            elistbox.set_focus_date_callback = lambda _: None
        self.calendar = ContainerWidget(calendar)
        self.lwidth = 31 if self._conf['locale']['weeknumbers'] == 'right' else 28
        columns = NColumns(
            [(self.lwidth, self.calendar), self.eventscolumn],
            dividechars=0,
            box_columns=[0, 1],
            outermost=True,
        )
        Pane.__init__(self, columns, title=title, description=description)

    def delete_status(self, uid):
        if uid[0] in self._deleted[ALL]:
            return ALL
        elif uid in self._deleted[INSTANCES]:
            return INSTANCES
        else:
            return False

    def toggle_delete_all(self, recuid):
        uid, _ = recuid
        if uid in self._deleted[ALL]:
            self._deleted[ALL].remove(uid)
        else:
            self._deleted[ALL].append(uid)

    def toggle_delete_instance(self, uid):
        if uid in self._deleted[INSTANCES]:
            self._deleted[INSTANCES].remove(uid)
        else:
            self._deleted[INSTANCES].append(uid)

    def cleanup(self, data):
        """delete all events marked for deletion"""
        for part in self._deleted[ALL]:
            account, href, etag = part.split('\n', 2)
            self.collection.delete(href, etag, account)
        for part, rec_id in self._deleted[INSTANCES]:
            account, href, etag = part.split('\n', 2)
            event = self.collection.get_event(href, account)
            event.delete_instance(rec_id)
            self.collection.update(event)

    def keypress(self, size, key):
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

    def _search(self, search_term):
        """search for events matching `search_term"""
        self.window.backtrack()
        events = list(self.collection.search(search_term))
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
            title="Search results for \"{}\" (Esc for backtrack)".format(search_term),
        )
        columns.set_focus_column(1)
        self.window.open(pane)

    def render(self, size, focus=False):
        rval = super(ClassicView, self).render(size, focus)
        if self.init:
            # starting with today's events
            self.eventscolumn.current_date = date.today()
            self.init = False
        return rval

    def get_keys(self):
        """return all bound keys"""
        # FIXME show current bindings
        return [(['arrows'], 'navigate through the calendar'),
                (['t'], 're-focus on today'),
                (['enter', 'tab'], 'select a date/event, show/edit event'),
                (['n'], 'create event on selected day'),
                (['d'], 'delete selected event'),
                (['e'], 'export selected event'),
                (['q', 'esc'], 'previous pane/quit'),
                ]

    def new_event(self, date, end):
        """create a new event starting on date and ending on end (if given)"""
        self.eventscolumn.original_widget.new(date, end)


def _urwid_palette_entry(name, color, hmethod):
    """Create an urwid compatible palette entry.

    :param name: name of the new attribute in the palette
    :type name: string
    :param color: color for the new attribute
    :type color: string
    :returns: an urwid palette entry
    :rtype: tuple
    """
    from ..terminal import COLORS
    if color == '' or color in COLORS or color is None:
        # Named colors already use urwid names, no need to change anything.
        pass
    elif color.isdigit():
        # Colors from the 256 color palette need to be prefixed with h in
        # urwid.
        color = 'h' + color
    else:
        # 24-bit colors are not supported by urwid.
        # Convert it to some color on the 256 color palette that might resemble
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
        return (name, '', '', '', color, '')
    else:
        return (name, '', '', '', '', color)


def _add_calendar_colors(palette, collection):
    """Add the colors for the defined calendars to the palette.

    :param palette: the base palette
    :type palette: list
    :param collection:
    :type collection: CalendarCollection
    :returns: the modified palette
    :rtype: list
    """
    for cal in collection.calendars:
        if cal['color'] == '':
            # No color set for this calendar, use default_color instead.
            color = collection.default_color
        else:
            color = cal['color']
        palette.append(_urwid_palette_entry('calendar ' + cal['name'], color,
                                            collection.hmethod))
    palette.append(_urwid_palette_entry('highlight_days_color',
                                        collection.color, collection.hmethod))
    palette.append(_urwid_palette_entry('highlight_days_multiple',
                                        collection.multiple, collection.hmethod))
    return palette


def start_pane(pane, callback, program_info='', quit_keys=['q']):
    """Open the user interface with the given initial pane."""
    frame = Window(
        footer=program_info + ' | {}: quit, ?: help'.format(quit_keys[0]),
        quit_keys=quit_keys,
    )
    frame.open(pane, callback)
    palette = _add_calendar_colors(
        getattr(colors, pane._conf['view']['theme']), pane.collection)
    loop = urwid.MainLoop(
        frame, palette, unhandled_input=frame.on_key_press, pop_ups=True)
    frame.loop = loop

    def redraw_today(loop, pane, meta={'last_today': None}):
        # TODO calculate how many seconds the new day is away and set timer
        # to that
        # XXX TODO this currently assumes, today moves forward by exactly one
        # day, but it could either move forward more (suspend-to-disk/ram) or
        # even move backwards
        today = date.today()
        if meta['last_today'] != today:
            meta['last_today'] = today
            pane.calendar.original_widget.reset_styles_range(today - timedelta(days=1), today)
            pane.eventscolumn.original_widget.update_date_line()
        loop.set_alarm_in(60, redraw_today, pane)

    redraw_today(frame.loop, pane)
    # Make urwid use 256 color mode.
    loop.screen.set_terminal_properties(
        colors=256, bright_is_bold=pane._conf['view']['bold_for_light_color'])

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
