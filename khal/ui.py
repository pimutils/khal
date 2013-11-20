#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2013 Christian Geier & contributors
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

import calendar
from datetime import date
from datetime import time
from datetime import datetime

import urwid

from . import backend

palette = [('header', 'white', 'black'),
           ('reveal focus', 'black', 'dark cyan', 'standout'),
           ('today_focus', 'white', 'black', 'standout'),
           ('today', 'black', 'white', 'dark cyan'),
           ('black', 'black', ''),
           ('dark red', 'dark red', ''),
           ('dark green', 'dark green', ''),
           ('brown', 'brown', ''),
           ('dark blue', 'dark blue', ''),
           ('dark magenta', 'dark magenta', ''),
           ('dark cyan', 'dark cyan', ''),
           ('light gray', 'light gray', ''),
           ('dark gray', 'dark gray', ''),
           ('light red', 'light red', ''),
           ('light green', 'light green', ''),
           ('yellow', 'yellow', ''),
           ('light blue', 'light blue', ''),
           ('light magenta', 'light magenta', ''),
           ('light cyan', 'light cyan', ''),
           ('white', 'white', ''),
           ]


class Date(urwid.Text):
    """used in the main calendar for dates"""

    def __init__(self, date):
        self.date = date
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
        return key


def week_list(count=3):
    month = date.today().month
    year = date.today().year
    khal = list()
    for _ in range(count):
        for week in calendar.Calendar(0).monthdatescalendar(year, month):
            if week not in khal:
                khal.append(week)
        month = month + 1
        if month > 12:
            month = 1
            year = year + 1
    return khal


class DateColumns(urwid.Columns):
    """container for one week worth of dates

    focus can only move away by pressing 'TAB',
    calls 'call' on every focus change
    """
    def __init__(self, widget_list, select_date=None, **kwargs):
        self.select_date = select_date
        super(DateColumns, self).__init__(widget_list, **kwargs)

    def _set_focus_position(self, position):
        """calls 'select_date' before calling super()._set_focus_position"""

        super(DateColumns, self)._set_focus_position(position)

        # since first Column is month name, focus should only be 0 during
        # construction
        if not self.contents.focus == 0:
            self.select_date(self.contents[position][0].original_widget.date)

    focus_position = property(urwid.Columns._get_focus_position,
                              _set_focus_position, doc="""
index of child widget in focus. Raises IndexError if read when
Columns is empty, or when set to an invalid index.
""")

    def keypress(self, size, key):
        """only leave calendar area on pressing 'TAB'"""

        old_pos = self.focus_position
        super(DateColumns, self).keypress(size, key)
        if key in ['up', 'down']:  # don't know why this is needed...
            return key
        elif key in ['tab', 'enter']:
            return 'right'
        elif old_pos == 7 and key == 'right':
            self.focus_position = 1
            return 'down'
        elif old_pos == 1 and key == 'left':
            self.focus_position = 7
            return 'up'
        elif key not in ['right']:
            return key


def construct_week(week, select_date=None):
    """
    :param week: list of datetime.date objects
    :param select_date: function to call on selecting date
    returns urwid.Columns
    """
    if 1 in [day.day for day in week]:
        month_name = calendar.month_abbr[week[-1].month].ljust(4)
    else:
        month_name = '    '

    this_week = [(4, urwid.Text(month_name))]
    today = None
    for number, day in enumerate(week):
        if day == date.today():
            this_week.append((2, urwid.AttrMap(Date(day),
                                               'today', 'today_focus')))
            today = number + 1
        else:
            this_week.append((2, urwid.AttrMap(Date(day),
                                               None, 'reveal focus')))
    week = DateColumns(this_week, select_date=select_date, dividechars=1,
                       focus_column=today)
    return week, bool(today)


def calendar_walker(select_date=None):
    """hopefully this will soon become a real "walker",
    loading new weeks as nedded"""
    lines = list()
    daynames = 'Mo Tu We Th Fr Sa Su'.split(' ')
    daynames = urwid.Columns([(4, urwid.Text('    '))] + [(2, urwid.Text(name)) for name in daynames],
                             dividechars=1)
    lines = [daynames]
    focus_item = None
    for number, week in enumerate(week_list()):
        week, contains_today = construct_week(week, select_date=select_date)
        if contains_today:
            focus_item = number + 1
        lines.append(week)

    weeks = urwid.Pile(lines, focus_item=focus_item)
    return weeks


class Event(urwid.Text):
    """representation of event in Eventlist
    """

    def __init__(self, event, this_date=None, conf=None, dbtool=None,
                 eventcolumn=None):
        self.event = event
        self.this_date = this_date
        self.dbtool = dbtool
        self.conf = conf
        self.eventcolumn = eventcolumn
        self.view = False
        super(Event, self).__init__(self.event.compact(self.this_date))

    @classmethod
    def selectable(cls):
        return True

    def toggle_delete(self):
        if self.event.readonly is False:
            if self.event.status == backend.OK:
                toggle = backend.DELETED
            elif self.event.status == backend.DELETED:
                toggle = backend.OK
            elif self.event.status == backend.NEW:
                toggle = backend.NEWDELETE
            elif self.event.status == backend.NEWDELETE:
                toggle = backend.NEW
            self.event.status = toggle
            self.set_text(self.event.compact(self.this_date))
            self.dbtool.set_status(self.event.href, toggle, self.event.account)
        else:
            self.set_text('R' + self.event.compact(self.this_date))

    def keypress(self, _, key):
        if key == 'enter' and self.view is False:
            self.view = True
            self.eventcolumn.view(self.event)
        elif (key == 'enter' and self.view is True) or key == 'e':
            self.eventcolumn.edit(self.event)
        elif key == 'd':
            self.toggle_delete()
        elif key in ['left', 'up', 'down'] and self.view:
            self.eventcolumn.destroy()
        return key


class EventList(urwid.WidgetWrap):
    """list of events"""
    def __init__(self, conf=None, dbtool=None, eventcolumn=None):
        self.conf = conf
        self.dbtool = dbtool
        self.eventcolumn = eventcolumn
        pile = urwid.Pile([])
        urwid.WidgetWrap.__init__(self, pile)
        self.update()

    def update(self, this_date=date.today()):

        start = datetime.combine(this_date, time.min)
        end = datetime.combine(this_date, time.max)

        date_text = urwid.Text(
            this_date.strftime(self.conf.default.longdateformat))
        event_column = list()
        all_day_events = list()
        events = list()
        for account in self.conf.sync.accounts:
            color = self.conf.accounts[account]['color']
            readonly = self.conf.accounts[account]['readonly']
            all_day_events += self.dbtool.get_allday_range(
                this_date,
                account_name=account,
                color=color,
                readonly=readonly)
            events += self.dbtool.get_time_range(start, end, account,
                                                 color=color,
                                                 readonly=readonly)

        for event in all_day_events:
            event_column.append(
                urwid.AttrMap(Event(event,
                                    conf=self.conf,
                                    dbtool=self.dbtool,
                                    this_date=this_date,
                                    eventcolumn=self.eventcolumn),
                              event.color, 'reveal focus'))
        events.sort(key=lambda e: e.start)
        for event in events:
            event_column.append(
                urwid.AttrMap(Event(event,
                                    conf=self.conf,
                                    dbtool=self.dbtool,
                                    this_date=this_date,
                                    eventcolumn=self.eventcolumn),
                              event.color, 'reveal focus'))
        event_list = [urwid.AttrMap(event, None, 'reveal focus') for event in event_column]
        pile = urwid.Pile([date_text] + event_list)
        self._w = pile


class EventColumn(urwid.WidgetWrap):
    def __init__(self, conf=None, dbtool=None):
        self.conf = conf
        self.dbtool = dbtool
        self.editor = False

    def update(self, date):
        # TODO make this switch from pile to columns depending on terminal size
        events = EventList(conf=self.conf, dbtool=self.dbtool,
                           eventcolumn=self)
        events.update(date)
        self.container = urwid.Pile([events])
        self._w = self.container

    def view(self, event):
        self.destroy()
        self.container.contents.append(
            (EventDisplay(self.conf, self.dbtool, event),
             self.container.options()))

    def edit(self, event):
        self.destroy()
        self.editor = True
        self.container.contents.append(
            (EventEditor(self.conf, self.dbtool, event, cancel=self.destroy),
             self.container.options()))
        self.container.set_focus(1)

    def destroy(self, _=None):
        self.editor = False
        if (len(self.container.contents) > 1 and
                isinstance(self.container.contents[1][0], EventViewer)):
            self.container.contents.pop()

    @classmethod
    def selectable(cls):
        return True


class StartEndEditor(urwid.WidgetWrap):
    """
    editing start and nd times of the event

    we cannot changed timezones ATM  # TODO
    no exception on strings not matching timeformat (but errormessage) # TODO
    """

    def __init__(self, start, end, conf):
        self.conf = conf
        self.start = start
        self.end = end
        self.allday = False
        if not isinstance(start, datetime):
            self.allday = True
        self.startdate = urwid.Edit(
            caption='From: ',
            edit_text=start.strftime(self.conf.default.longdateformat))
        self.starttime = urwid.Edit(
            edit_text=start.strftime(self.conf.default.timeformat))
        self.enddate = urwid.Edit(
            caption='To: ',
            edit_text=end.strftime(self.conf.default.longdateformat))
        self.endtime = urwid.Edit(
            edit_text=end.strftime(self.conf.default.timeformat))
        self.checkallday = urwid.CheckBox('Allday', state=self.allday,
                                          on_state_change=self.toggle)
        self.toggle(None, self.allday)

    def toggle(self, checkbox, state):
        if state is True:
            self.starttime = urwid.Text('')
            self.endtime = urwid.Text('')
        elif state is False:
            self.starttime = urwid.Edit(
                edit_text=self.start.strftime(self.conf.default.timeformat))
            self.endtime = urwid.Edit(
                edit_text=self.end.strftime(self.conf.default.timeformat))
        columns = urwid.Pile([
            urwid.Columns([self.startdate, self.starttime]),
            urwid.Columns([self.enddate, self.endtime]),
            self.checkallday], focus_item=2)
        urwid.WidgetWrap.__init__(self, columns)

    @property
    def changed(self):
        """
        returns True if content has been edited, False otherwise
        """
        return not ((self.start == self.newstart) and
                    (self.end == self.newend))

    @property
    def newstart(self):
        newstartdatetime = datetime.strptime(
            self.startdate.get_edit_text(),
            self.conf.default.longdateformat).date()
        if not self.checkallday.state:
            newstarttime = datetime.strptime(
                self.starttime.get_edit_text(),
                self.conf.default.timeformat).time()
            newstartdatetime = datetime.combine(newstartdatetime, newstarttime)
            newstartdatetime = self.start.tzinfo.localize(newstartdatetime)
        return newstartdatetime

    @property
    def newend(self):
        newenddatetime = datetime.strptime(
            self.enddate.get_edit_text(),
            self.conf.default.longdateformat).date()
        if not self.checkallday.state:
            newendtime = datetime.strptime(
                self.endtime.get_edit_text(),
                self.conf.default.timeformat).time()
            newenddatetime = datetime.combine(newenddatetime, newendtime)
            newenddatetime = self.end.tzinfo.localize(newenddatetime)
        return newenddatetime


class EventViewer(urwid.WidgetWrap):
    """
    Base Class for EventEditor and EventDisplay
    """
    def __init__(self, conf, dbtool):
        self.conf = conf
        self.dbtool = dbtool
        pile = urwid.Pile([])
        urwid.WidgetWrap.__init__(self, pile)


class EventDisplay(EventViewer):
    """showing events

    widget for display one event
    """
    def __init__(self, conf, dbtool, event):
        super(EventDisplay, self).__init__(conf, dbtool)
        lines = []
        lines.append(urwid.Text(event.vevent['SUMMARY']))
        if event.allday:
            startstr = event.start.strftime(self.conf.default.dateformat)
            if event.start == event.end:
                lines.append(urwid.Text('On: ' + startstr))
            else:
                endstr = event.end.strftime(self.conf.default.dateformat)
                lines.append(
                    urwid.Text('From: ' + startstr + ' to: ' + endstr))

        else:
            startstr = event.start.strftime(self.conf.default.dateformat +
                                            ' ' + self.conf.default.timeformat)
            if event.start.date == event.end.date:
                endstr = event.end.strftime(self.conf.default.timeformat)
            else:
                endstr = event.end.strftime(self.conf.default.dateformat +
                                            ' ' +
                                            self.conf.default.timeformat)
                lines.append(urwid.Text('From: ' + startstr +
                                        ' To: ' + endstr))

        for key, desc in [('DESCRIPTION', 'Desc'), ('LOCATION', 'Loc')]:
            try:
                lines.append(urwid.Text(
                    desc + ': ' + str(event.vevent[key].encode('utf-8'))))
            except KeyError:
                pass
        pile = urwid.Pile(lines)
        self._w = pile


class EventEditor(EventViewer):
    def __init__(self, conf, dbtool, event, cancel=None):
        super(EventEditor, self).__init__(conf, dbtool)
        self.event = event
        self.cancel = cancel
        try:
            self.description = event.vevent['DESCRIPTION'].encode('utf-8')
        except KeyError:
            self.description = ''
        try:
            self.location = event.vevent['LOCATION'].encode('utf-8')
        except KeyError:
            self.location = ''

        self.startendeditor = StartEndEditor(event.start, event.end, self.conf)
        self.summary = urwid.Edit(
            edit_text=event.vevent['SUMMARY'].encode('utf-8'))
        self.description = urwid.Edit(caption='Description: ',
                                      edit_text=self.description)
        self.location = urwid.Edit(caption='Location: ',
                                   edit_text=self.location)
        cancel = urwid.Button('Cancel', on_press=self.cancel)
        save = urwid.Button('Save', on_press=self.save)
        buttons = urwid.Columns([cancel, save])

        pile = urwid.Pile([self.summary, self.startendeditor, self.description,
                           self.location, urwid.Text(''), buttons])
        self._w = pile

    @classmethod
    def selectable(cls):
        return True

    def save(self, button):
        changed = False
        if self.summary.get_edit_text() != self.event.vevent['SUMMARY']:
            self.event.vevent['SUMMARY'] = self.summary.get_edit_text()
            changed = True
        if self.description.get_edit_text() != self.description:
            self.event.vevent['DESCRIPTION'] = self.description.get_edit_text()
            changed = True
        if self.location.get_edit_text() != self.location:
            self.event.vevent['LOCATION'] = self.location.get_edit_text()
            changed = True
        if self.startendeditor.changed:
            self.event.vevent['DTSTART'].dt = self.startendeditor.newstart
            self.event.vevent['DTEND'].dt = self.startendeditor.newend
            changed = True
        if changed is True:
            try:
                self.event.vevent['SEQUENCE'] += 1
            except KeyError:
                self.event.vevent['SEQUNCE'] = 0
            if self.event.status == backend.NEW:
                status = backend.NEW
            else:
                status = backend.CHANGED
            self.dbtool.update(self.event.vevent.to_ical(),
                               self.event.account,
                               self.event.href,
                               status=status)
        self.cancel()


def exit(key):
    if key in ('q', 'Q', 'esc'):
        raise urwid.ExitMainLoop()


def interactive(conf=None, dbtool=None):
    eventscolumn = EventColumn(conf=conf, dbtool=dbtool)
    weeks = calendar_walker(select_date=eventscolumn.update)
    columns = urwid.Columns([(25, weeks), eventscolumn], dividechars=2)

    fill = urwid.Filler(columns)
    eventscolumn.update(date.today())  # showing with today's events
    urwid.MainLoop(fill, palette=palette, unhandled_input=exit).run()
