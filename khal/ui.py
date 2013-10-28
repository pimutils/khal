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
import urwid
import calendar
from datetime import date
from datetime import time
from datetime import datetime

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
    def __init__(self, widget_list, call=None, **kwargs):
        self.call = call
        super(DateColumns, self).__init__(widget_list, **kwargs)

    def _set_focus_position(self, position):
        """calls 'call' before calling super()._set_focus_position"""

        super(DateColumns, self)._set_focus_position(position)

        # since first Column is month name, focus should only be 0 during
        # construction
        if not self.contents.focus == 0:
            self.call(self.contents[position][0].original_widget.date)

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
        elif key in ['tab']:
            return 'right'
        elif old_pos == 7 and key == 'right':
            self.focus_position = 1
            return 'down'
        elif old_pos == 1 and key == 'left':
            self.focus_position = 7
            return 'up'


def construct_week(week, call=None):
    """
    :param week: list of datetime.date objects
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
    week = DateColumns(this_week, call=call, dividechars=1, focus_column=today)
    return week, bool(today)


def calendar_walker(call=None):
    """hopefully this will soon become a real "walker",
    loading new weeks as nedded"""
    lines = list()
    daynames = 'Mo Tu We Th Fr Sa Su'.split(' ')
    daynames = urwid.Columns([(4, urwid.Text('    '))] + [(2, urwid.Text(name)) for name in daynames],
                             dividechars=1)
    lines = [daynames]
    focus_item = None
    for number, week in enumerate(week_list()):
        week, contains_today = construct_week(week, call=call)
        if contains_today:
            focus_item = number + 1
        lines.append(week)

    weeks = urwid.Pile(lines, focus_item=focus_item)
    return weeks


class Event(urwid.Text):
    """representation of event in Eventlist
    """

    def __init__(self, event, this_date=None, call=None):
        self.event = event
        self.call = call
        self.this_date = this_date
        super(Event, self).__init__(self.event.compact(self.this_date))

    @classmethod
    def selectable(cls):
        return True

    def keypress(self, _, key):
        if key is 'enter':
            self.call(self.event)
        return key


class EventList(urwid.WidgetWrap):
    """list of events"""
    def __init__(self, conf=None, dbtool=None, call=None):
        self.conf = conf
        self.dbtool = dbtool
        self.call = call
        pile = urwid.Pile([])
        urwid.WidgetWrap.__init__(self, pile)
        self.update()

    def update(self, this_date=date.today()):

        start = datetime.combine(this_date, time.min)
        end = datetime.combine(this_date, time.max)

        date_text = urwid.Text(this_date.strftime(self.conf.default.longdateformat))
        event_column = list()
        all_day_events = list()
        events = list()
        for account in self.conf.sync.accounts:
            color = self.conf.accounts[account]['color']
            all_day_events += self.dbtool.get_allday_range(this_date,
                                                           account_name=account,
                                                           color=color)
            events += self.dbtool.get_time_range(start, end, account, color=color)
        for event in all_day_events:
            event_column.append(urwid.AttrMap(Event(event, this_date=this_date, call=self.call), event.color, 'reveal focus'))
        events.sort(key=lambda e: e.start)
        for event in events:
            event_column.append(urwid.AttrMap(Event(event, this_date=this_date, call=self.call), event.color, 'reveal focus'))
        event_list = [urwid.AttrMap(event, None, 'reveal focus') for event in event_column]
        pile = urwid.Pile([date_text] + event_list)
        self._w = pile


class EventViewer(urwid.WidgetWrap):
    def __init__(self, conf=None, dbtool=None):
        self.conf = conf
        self.dbtool = dbtool
        pile = urwid.Pile([])
        urwid.WidgetWrap.__init__(self, pile)

    def update(self, event):

        lines = []
        for key in event.vevent:
            lines.append(urwid.Text(key + ': ' + str(event.vevent[key])))
        pile = urwid.Pile(lines)
        self._w = pile


def interactive(conf=None, dbtool=None):
    eventviewer = EventViewer(conf=conf, dbtool=dbtool)
    events = EventList(conf=conf, dbtool=dbtool, call=eventviewer.update)
    weeks = calendar_walker(call=events.update)
    columns = urwid.Columns([(25, weeks), events, eventviewer], dividechars=2)
    fill = urwid.Filler(columns)
    events.update(date.today())  # update events column to show today's events
    urwid.MainLoop(fill, palette=palette).run()
