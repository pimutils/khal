# vim: set ts=4 sw=4 expandtab sts=4 fileencoding=utf-8:
# Copyright (c) 2013-2015 Christian Geier et al.
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

from __future__ import unicode_literals

import calendar
from datetime import date, datetime, time, timedelta
import signal
import sys

import urwid

from .. import aux
from ..compat import to_unicode
from ..calendar_display import getweeknumber

from .base import Pane, Window, CColumns, CPile, CSimpleFocusListWalker, Choice
from .widgets import CEdit as Edit
from .startendeditor import StartEndEditor


class DateConversionError(Exception):
    pass


class Date(urwid.Text):

    """used in the main calendar for dates (a number)"""

    def __init__(self, date, pane):
        self.date = date
        self.pane = pane
        if date.today == date:
            urwid.AttrMap(super(Date, self).__init__(str(date.day).rjust(2)),
                          None,
                          'reveal focus')
        else:
            super(Date, self).__init__(str(date.day).rjust(2))

    @classmethod
    def selectable(cls):
        return True

    def keypress(self, _, key):
        if key in self.pane.conf['keybindings']['new']:  # TODO XXX
            self.pane.new_event(self.date)
            return 'tab'  # TODO return next
        else:
            return key


class DateCColumns(CColumns):

    """container for one week worth of dates
    which are horizontally aligned

    TODO: rename, awful name

    focus can only move away by pressing 'TAB',
    calls 'pane.show_date' on every focus change (see below for details)
    """

    def __init__(self, widget_list, pane=None, today=None, **kwargs):
        self.pane = pane
        self.keys = pane.conf['keybindings']
        self.today = today
        # we need the next two attributes to for attribute resetting when a
        # cell regains focus after having lost it the the events column before
        self._old_attr_map = False
        self._old_pos = 0
        super(DateCColumns, self).__init__(widget_list, focus_column=today,
                                           **kwargs)

    def _set_focus_position(self, position):
        """calls pane.show_date before calling super()._set_focus_position"""

        self.pane.show_date(
            self.contents[position][0].original_widget.date)
        super(DateCColumns, self)._set_focus_position(position)

    focus_position = property(
        CColumns._get_focus_position,
        _set_focus_position,
        doc=('Index of child widget in focus. Raises IndexError if read when '
             'CColumns is empty, or when set to an invalid index.')
    )

    def keypress(self, size, key):
        """only leave calendar area on pressing 'tab' or 'enter'"""

        if key in self.keys['left']:
            key = 'left'
        elif key in self.keys['up']:
            key = 'up'
        elif key in self.keys['right']:
            key = 'right'
        elif key in self.keys['down']:
            key = 'down'

        old_pos = self.focus_position
        key = super(DateCColumns, self).keypress(size, key)
        if key in self.keys['view']:
            self._old_attr_map = self.contents[self.focus_position][0].get_attr_map()
            self._old_pos = old_pos
            self.contents[self.focus_position][0].set_attr_map({None: 'today focus'})
            return 'right'
        elif self._old_attr_map:
            self.contents[self._old_pos][0].set_attr_map(self._old_attr_map)
            self._old_attr_map = False

        if old_pos == 7 and key == 'right':
            self.focus_position = 1
            return 'down'
        elif old_pos == 1 and key == 'left':
            self.focus_position = 7
            return 'up'
        elif key not in ['right']:
            return key


def calendar_walker(pane, firstweekday=0, weeknumbers=False):
    """creates a `Frame` filled with a `CalendarWalker`"""
    calendar.setfirstweekday(firstweekday)
    dnames = calendar.weekheader(2).split(' ')
    if weeknumbers == 'right':
        dnames.append('#w')
    dnames = CColumns(
        [(4, urwid.Text('    '))] + [(2, urwid.Text(name)) for name in dnames],
        dividechars=1)

    weeks = CalendarWalker(pane, firstweekday, weeknumbers)
    box = CListBox(weeks)
    frame = urwid.Frame(box, header=dnames)
    return frame


class CListBox(urwid.ListBox):
    """our custom version of ListBox for containing CalendarWalker

    it should contain a `CalendarWalker` instance which it autoextends on
    rendering, if needed """

    init = True

    def __init__(self, walker):
        self.keys = walker.pane.conf['keybindings']
        super(CListBox, self).__init__(walker)

    def render(self, size, focus=False):
        if self.init:
            while 'bottom' in self.ends_visible(size):
                self.body._autoextend()
            self.set_focus_valign('middle')
            self.init = False

        return super(CListBox, self).render(size, focus)

    def keypress(self, size, key):
        if key in self.keys['today']:
            self.body.set_focus(self.body.today)
            week = self.body[self.body.today]
            week.set_focus(week.today)
            self.set_focus_valign(('relative', 10))
        return super(CListBox, self).keypress(size, key)


class CalendarWalker(urwid.SimpleFocusListWalker):

    def __init__(self, pane, firstweekday=0, weeknumbers=False):
        self.firstweekday = firstweekday
        self.weeknumbers = weeknumbers
        self.pane = pane
        weeks, focus_item = self._construct_month()
        self.today = focus_item  # the item number which contains today
        urwid.SimpleFocusListWalker.__init__(self, weeks)
        self.set_focus(focus_item)

    def set_focus(self, position):
        if position == 0:
            position = self._autoprepend()
            self.today += position
        elif position + 1 == len(self):
            self._autoextend()
        return urwid.SimpleFocusListWalker.set_focus(self, position)

    def _autoextend(self):
        """appends the next month"""
        date_last_month = self[-1][1].date  # a date from the last month
        last_month = date_last_month.month
        last_year = date_last_month.year
        month = last_month % 12 + 1
        year = last_year if not last_month == 12 else last_year + 1
        weeks, _ = self._construct_month(year, month, clean_first_row=True)
        self.extend(weeks)

    def _autoprepend(self):
        """prepends the previous month

        :returns: number of weeks prepended
        :rtype: int
        """
        try:
            date_first_month = self[0][-1].date  # a date from the first month
        except AttributeError:
            # rightmost column is weeknumber
            date_first_month = self[0][-2].date
        first_month = date_first_month.month
        first_year = date_first_month.year
        if first_month == 1:
            month = 12
            year = first_year - 1
        else:
            month = first_month - 1
            year = first_year
        weeks, _ = self._construct_month(year, month, clean_last_row=True)
        weeks.reverse()
        for one in weeks:
            self.insert(0, one)
        return len(weeks)

    def _construct_week(self, week):
        """
        constructs a CColumns week from a week of datetime.date objects. Also
        prepends the month name if the first day of the month is included in
        that week.

        :param week: list of datetime.date objects
        :returns: the week as an CColumns object and True or False depending on
                  if today is in this week
        :rtype: tuple(urwid.CColumns, bool)
        """
        if 1 in [day.day for day in week]:
            month_name = calendar.month_abbr[week[-1].month].ljust(4)
        elif self.weeknumbers == 'left':
            month_name = ' {:2} '.format(getweeknumber(week[0]))
        else:
            month_name = '    '

        this_week = [(4, urwid.Text(month_name))]
        today = None
        for number, day in enumerate(week):
            if day == date.today():
                this_week.append((2, urwid.AttrMap(Date(day, self.pane),
                                                   'today', 'today focus')))
                today = number + 1
            else:
                this_week.append((2, urwid.AttrMap(Date(day, self.pane),
                                                   None, 'reveal focus')))
        if self.weeknumbers == 'right':
            this_week.append((2, urwid.Text('{:2}'.format(getweeknumber(week[0])))))

        week = DateCColumns(this_week, pane=self.pane, dividechars=1,
                            today=today)
        return week, bool(today)

    def _construct_month(self,
                         year=date.today().year,
                         month=date.today().month,
                         clean_first_row=False,
                         clean_last_row=False):
        """construct one month of DateCColumns

        :param year: the year this month is set in
        :type year: int
        :param month: the number of the month to be constructed
        :type month: int (1-12)
        :param clean_first_row: makes sure that the first element returned is
                                completely in `month` and not partly in the one
                                before (which might lead to that line occurring
                                twice
        :type clean_first_row: bool
        :param clean_last_row: makes sure that the last element returned is
                               completely in `month` and not partly in the one
                               after (which might lead to that line occurring
                               twice
        :type clean_last_row: bool
        :returns: list of DateCColumns and the number of the list element which
                  contains today (or None if it isn't in there)
        :rtype: tuple(list(dateCColumns, int or None))
        """

        plain_weeks = calendar.Calendar(
            self.firstweekday).monthdatescalendar(year, month)
        weeks = list()
        focus_item = None
        for number, week in enumerate(plain_weeks):
            week, contains_today = self._construct_week(week)
            if contains_today:
                focus_item = number
            weeks.append(week)
        if clean_first_row and \
           weeks[0][1].date.month != weeks[0][7].date.month:
            if focus_item is not None:
                focus_item = focus_item - 1
            return weeks[1:], focus_item
        elif clean_last_row and \
                weeks[-1][1].date.month != weeks[-1][7].date.month:
            return weeks[:-1], focus_item
        else:
            return weeks, focus_item


class U_Event(urwid.Text):

    def __init__(self, event, this_date=None, eventcolumn=None):
        """
        representation of an event in EventList

        :param event: the encapsulated event
        :type event: khal.event.Event
        """
        if isinstance(this_date, datetime) or not isinstance(this_date, date):
            raise ValueError('`this_date` is of type `{}`, sould be '
                             '`datetime.date`'.format(type(this_date)))
        self.event = event
        self.this_date = this_date
        self.eventcolumn = eventcolumn
        self.conf = eventcolumn.pane.conf
        super(U_Event, self).__init__(self.event.compact(self.this_date))
        self.set_title()

    @property
    def is_viewed(self):
        return self.event is self.eventcolumn.current_event

    @classmethod
    def selectable(cls):
        return True

    @property
    def uid(self):
        return self.event.calendar + '\n' + \
            str(self.event.href) + '\n' + str(self.event.etag)

    def set_title(self, mark=''):
        if self.uid in self.eventcolumn.pane.deleted:
            mark = 'D'
        self.set_text(mark + ' ' + self.event.compact(self.this_date))

    def toggle_delete(self):
        if self.event.readonly:
            self.eventcolumn.pane.window.alert(
                ('light red',
                 'Calendar {} is read-only.'.format(self.event.calendar)))
            return
        if self.uid in self.eventcolumn.pane.deleted:
            self.eventcolumn.pane.deleted.remove(self.uid)
        else:
            self.eventcolumn.pane.deleted.append(self.uid)
        self.set_title()

    def keypress(self, _, key):
        binds = self.conf['keybindings']

        if key in binds['view']:
            if self.is_viewed:
                self.eventcolumn.edit(self.event)
            else:
                self.eventcolumn.current_event = self.event
        elif key in binds['delete']:
            self.toggle_delete()
        elif key in binds['left'] + binds['up'] + binds['down']:
            if not self.conf['view']['event_view_always_visible']:
                self.eventcolumn.current_event = None
            else:
                events = self.eventcolumn.events.events
                focused = self.eventcolumn.events.list_walker.focus
                if key in binds['down'] and focused < len(events) - 1:
                    self.eventcolumn.current_event = events[focused + 1]
                if key in binds['up'] and focused > 0:
                    self.eventcolumn.current_event = events[focused - 1]

        if key in ['esc'] and self.eventcolumn.current_event:
            self.eventcolumn.current_event = None
        else:
            return key


class EventList(urwid.WidgetWrap):

    """list of events"""

    def __init__(self, eventcolumn):
        self.eventcolumn = eventcolumn
        self.events = None
        self.list_walker = None
        pile = urwid.Filler(CPile([]))
        urwid.WidgetWrap.__init__(self, pile)
        self.update()

    def update(self, this_date=date.today()):
        start = datetime.combine(this_date, time.min)
        end = datetime.combine(this_date, time.max)

        date_text = urwid.Text(
            this_date.strftime(self.eventcolumn.pane.conf['locale']['longdateformat']))
        event_column = list()
        all_day_events = self.eventcolumn.pane.collection.get_allday_by_time_range(this_date)
        events = self.eventcolumn.pane.collection.get_datetime_by_time_range(start, end)

        for event in all_day_events:
            event_column.append(
                urwid.AttrMap(U_Event(event, this_date=this_date,
                                      eventcolumn=self.eventcolumn),
                              event.color, 'reveal focus'))
        events.sort(key=lambda e: e.start)
        for event in events:
            event_column.append(
                urwid.AttrMap(U_Event(event, this_date=this_date,
                                      eventcolumn=self.eventcolumn),
                              event.color, 'reveal focus'))
        event_list = [urwid.AttrMap(event, None, 'reveal focus')
                      for event in event_column]
        event_count = len(event_list)
        if not event_list:
            event_list = [urwid.Text('no scheduled events')]
        self.list_walker = CSimpleFocusListWalker(event_list)
        pile = urwid.ListBox(self.list_walker)
        pile = urwid.Frame(pile, header=date_text)
        self._w = pile
        self.events = all_day_events + events
        return event_count


class EventColumn(urwid.WidgetWrap):

    """contains the eventlist as well as the event viewer"""

    def __init__(self, pane):
        self.pane = pane
        self.divider = urwid.Divider('─')
        self.editor = False
        self.eventcount = 0
        self._current_date = None
        self.event_width = int(self.pane.conf['view']['event_view_weighting'])

        # TODO make this switch from pile to columns depending on terminal size
        self.events = EventList(eventcolumn=self)
        self.container = CPile([self.events])
        urwid.WidgetWrap.__init__(self, self.container)

    @property
    def current_event(self):
        l = len(self.container.contents)
        assert l > 0
        if l > 2:
            return self.container.contents[-1][0].event

    @current_event.setter
    def current_event(self, event):
        while len(self.container.contents) > 1:
            self.container.contents.pop()
        if not event:
            return
        self.container.contents.append((self.divider,
                                        ('pack', None)))
        self.container.contents.append(
            (EventDisplay(self.pane.conf, event, collection=self.pane.collection),
             ('weight', self.event_width)))

    @property
    def current_date(self):
        return self._current_date

    @current_date.setter
    def current_date(self, date):
        self._current_date = date
        self.eventcount = self.events.update(date)
        self.current_event = self.current_event

        # Show first event if show event view is true
        if self.pane.conf['view']['event_view_always_visible']:
            if len(self.events.events) > 0:
                self.current_event = self.events.events[0]
            else:
                self.current_event = None

    def set_current_date(self, date):
        self.current_date = date

    def edit(self, event):
        """create an EventEditor and display it

        :param event: event to edit
        :type event: khal.event.Event
        """
        if event.readonly:
            self.pane.window.alert(
                ('light red',
                 'Calendar {} is read-only.'.format(event.calendar)))
            return

        if self.editor:
            self.pane.window.backtrack()

        assert not self.editor
        self.editor = True
        editor = EventEditor(self.pane, event)
        current_day = self.container.contents[0][0]
        new_pane = urwid.Columns([
            ('weight', 1.5, editor),
            ('weight', 1, current_day)
        ], dividechars=4, focus_column=0)
        new_pane.title = editor.title
        new_pane.get_keys = editor.get_keys

        def teardown(data):
            self.editor = False
            self.current_date = self.current_date
        self.pane.window.open(new_pane, callback=teardown)

    def new(self, date):
        """create a new event on date

        :param date: default date for new event
        :type date: datetime.date
        """
        event = aux.new_event(dtstart=date,
                              timezone=self.pane.conf['locale']['default_timezone'])

        # TODO proper default cal
        event = self.pane.collection.new_event(
            event.to_ical(), self.pane.collection.default_calendar_name)

        self.edit(event)
        self.eventcount += 1

    def selectable(self):
        return bool(self.eventcount)


class RecursionEditor(urwid.WidgetWrap):

    def __init__(self, rrule):
        # TODO: actually implement the Recursion Editor
        self.recursive = False if rrule is None else True
        self.checkRecursion = urwid.CheckBox('repeat', state=self.recursive,
                                             on_state_change=self.toggle)
        self.columns = CColumns([self.checkRecursion])
        urwid.WidgetWrap.__init__(self, self.columns)

    def toggle(self, checkbox, state):
        if len(self.columns.contents) < 2:
            text = 'Editing repitition rules is not supported yet'
            self.columns.contents.append((urwid.Text(text),
                                          self.columns.options()))


class EventDisplay(urwid.WidgetWrap):

    """showing events

    widget for displaying one event's details
    """

    def __init__(self, conf, event, collection=None):
        self.conf = conf
        self.collection = collection
        self.event = event
        divider = urwid.Divider(' ')

        lines = []
        lines.append(urwid.Columns([
            urwid.Text(event.vevent['SUMMARY']),
            urwid.Text('Calendar: ' + event.calendar)
        ], dividechars=2))

        lines.append(divider)

        # show organizer
        try:
            organizer = to_unicode(event.vevent['ORGANIZER'], 'utf-8').split(':')
            lines.append(urwid.Text(
                'Organizer: ' + organizer[len(organizer) - 1]))
        except KeyError:
            pass

        # description and location
        for key, desc in [('LOCATION', 'Location'), ('DESCRIPTION', 'Description')]:
            try:
                lines.append(urwid.Text(
                    desc + ': ' + to_unicode(event.vevent[key], 'utf-8')))
            except KeyError:
                pass

        if lines[-1] != divider:
            lines.append(divider)

        # start and end time/date
        if event.allday:
            startstr = event.start.strftime(self.conf['locale']['dateformat'])
            end = event.end - timedelta(days=1)
            endstr = end.strftime(self.conf['locale']['dateformat'])

        else:
            startstr = event.start.strftime(
                '{} {}'.format(self.conf['locale']['dateformat'],
                               self.conf['locale']['timeformat'])
            )
            if event.start.date == event.end.date:
                endstr = event.end.strftime(self.conf['locale']['timeformat'])
            else:
                endstr = event.end.strftime(
                    '{} {}'.format(self.conf['locale']['dateformat'],
                                   self.conf['locale']['timeformat'])
                )

        if startstr == endstr:
            lines.append(urwid.Text('On: ' + startstr))
        else:
            lines.append(urwid.Text('From: ' + startstr))
            lines.append(urwid.Text('To: ' + endstr))

        pile = CPile(lines)
        urwid.WidgetWrap.__init__(self, urwid.Filler(pile, valign='top'))


class EventEditor(urwid.WidgetWrap):

    """
    Widget for event Editing
    """

    def __init__(self, pane, event):
        """
        :type event: khal.event.Event
        """

        self.pane = pane
        self.event = event

        self.collection = pane.collection
        self.conf = pane.conf

        self._abort_confirmed = False

        try:
            self.description = event.vevent['DESCRIPTION']
        except KeyError:
            self.description = ''
        try:
            self.location = event.vevent['LOCATION']
        except KeyError:
            self.location = ''

        if event.allday:
            end = event.end - timedelta(days=1)
        else:
            end = event.end

        self.startendeditor = StartEndEditor(
            event.start, end, self.conf, self.pane.eventscolumn.set_current_date)
        try:
            rrule = self.event.vevent['RRULE']
        except KeyError:
            rrule = None
        self.recursioneditor = RecursionEditor(rrule)
        self.summary = Edit(edit_text=event.vevent['SUMMARY'])

        divider = urwid.Divider(' ')

        # TODO warning message if len(self.collection.writable_names) == 0

        def decorate_choice(c):
            return (c.color or '', c.name)

        self.calendar_chooser = Choice(
            [c for c in self.collection.calendars if not c.readonly],
            self.collection._calnames[self.event.calendar],
            decorate_choice
        )
        self.description = Edit(caption='Description: ',
                                edit_text=self.description)
        self.location = Edit(caption='Location: ',
                             edit_text=self.location)
        self.pile = urwid.ListBox(CSimpleFocusListWalker([
            urwid.Columns([
                self.summary,
                self.calendar_chooser
            ], dividechars=2),
            divider,
            self.description,
            self.location,
            divider,
            self.startendeditor,
            self.recursioneditor,
            divider,
            urwid.Button('Save', on_press=self.save)
        ]))

        urwid.WidgetWrap.__init__(self, self.pile)

    @property
    def title(self):  # Window title
        return 'Edit: {}'.format(self.summary.get_edit_text())

    def get_keys(self):
        return [(['arrows'], 'navigate through properties'),
                (['enter'], 'edit property'),
                (['esc'], 'abort')]

    @classmethod
    def selectable(cls):
        return True

    @property
    def changed(self):
        if self.summary.get_edit_text() != self.event.vevent['SUMMARY']:
            return True

        if self.description.get_edit_text() != \
                self.event.vevent.get('DESCRIPTION', ''):
            return True

        if self.location.get_edit_text() != \
                self.event.vevent.get('LOCATION', ''):
            return True

        if self.startendeditor.changed or self.calendar_chooser.changed:
            return True
        return False

    def update_vevent(self):
        self.event.vevent['SUMMARY'] = self.summary.get_edit_text()
        self.event.vevent['DESCRIPTION'] = self.description.get_edit_text()
        self.event.vevent['LOCATION'] = self.location.get_edit_text()

        if self.startendeditor.changed:
            # TODO look up why this is needed
            # self.event.vevent.dt = newstart would not work
            # (timezone was missing after to_ical() )
            self.event.vevent.pop('DTSTART')
            self.event.vevent.add('DTSTART', self.startendeditor.newstart)
            if self.startendeditor.allday:
                end = self.startendeditor.newend + timedelta(days=1)
            else:
                end = self.startendeditor.newend
            try:
                self.event.vevent.pop('DTEND')
                self.event.vevent.add('DTEND', end)
            except KeyError:
                self.event.vevent.pop('DURATION')
                duration = (end -
                            self.startendeditor.newstart)
                self.event.vevent.add('DURATION', duration)

        # TODO self.newaccount = self.calendar_chooser.active ?

    def save(self, button):
        """
        saves the event to the db (only when it has been changed)
        :param button: not needed, passed via the button press
        """
        # need to call this to set date backgrounds to False
        changed = self.changed
        self.update_vevent()
        if 'alert' in [self.startendeditor.bgs.startdate,
                       self.startendeditor.bgs.starttime,
                       self.startendeditor.bgs.enddate,
                       self.startendeditor.bgs.endtime]:
            self.startendeditor.refresh(None, state=self.startendeditor.allday)
            self.pile.set_focus(1)  # the startendeditor
            return

        if changed is True:
            try:
                self.event.vevent['SEQUENCE'] += 1
            except KeyError:
                self.event.vevent['SEQUENCE'] = 0

            self.event.allday = self.startendeditor.allday
            if self.event.etag is None:  # has not been saved before
                # TODO look for better way to detect this
                self.event.calendar = self.calendar_chooser.active.name
                self.collection.new(self.event)
            elif self.calendar_chooser.changed:
                self.collection.change_collection(
                    self.event,
                    self.calendar_chooser.active.name
                )
            else:
                self.collection.update(self.event)

        self._abort_confirmed = False
        self.pane.window.backtrack()

    def keypress(self, size, key):
        if key in ['esc'] and self.changed and not self._abort_confirmed:
            # TODO Use user-defined keybindings
            self.pane.window.alert(
                ('light red',
                 'Unsaved changes! Hit ESC again to discard.'))
            self._abort_confirmed = True
            return
        return super(EventEditor, self).keypress(size, key)


class ClassicView(Pane):

    """default Pane for khal

    showing a CalendarWalker on the left and the eventList + eventviewer/editor
    on the right
    """

    def __init__(self, collection, conf=None, title='',
                 description=''):
        self.init = True
        # Will be set when opening the view inside a Window
        self.window = None
        self.conf = conf
        self.collection = collection
        self.deleted = []
        self.eventscolumn = EventColumn(pane=self)
        weeks = calendar_walker(
            pane=self, firstweekday=conf['locale']['firstweekday'],
            weeknumbers=conf['locale']['weeknumbers'],
        )
        events = self.eventscolumn
        lwidth = 29 if conf['locale']['weeknumbers'] else 25
        columns = CColumns([(lwidth, weeks), events],
                           dividechars=4,
                           box_columns=[0, 1])
        Pane.__init__(self, columns, title=title, description=description)

    def render(self, size, focus=False):
        rval = super(Pane, self).render(size, focus)
        if self.init:
            # starting with today's events
            self.eventscolumn.current_date = date.today()
            self.init = False
        return rval

    def get_keys(self):
        return [(['arrows'], 'navigate through the calendar'),
                (['t'], 're-focus on today'),
                (['enter', 'tab'], 'select a date/event, show/edit event'),
                (['n'], 'create event on selected day'),
                (['d'], 'delete selected event'),
                (['q', 'esc'], 'previous pane/quit'),
                ]

    def show_date(self, date):
        self.eventscolumn.current_date = date

    def new_event(self, date):
        self.eventscolumn.new(date)

    def cleanup(self, data):
        for part in self.deleted:
            account, href, etag = part.split('\n', 2)
            self.collection.delete(href, etag, account)


def start_pane(pane, callback, program_info=''):
    """Open the user interface with the given initial pane."""
    frame = Window(footer=program_info + ' | q: quit, ?: help')
    frame.open(pane, callback)
    loop = urwid.MainLoop(frame, Window.PALETTE,
                          unhandled_input=frame.on_key_press,
                          pop_ups=True)

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
