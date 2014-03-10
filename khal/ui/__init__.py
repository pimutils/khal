#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
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

from .. import aux
from ..event import Event
from ..status import OK, NEW, CHANGED, NEWNOTSAVED, DELETED, NEWDELETE, CALCHANGED


from base import Pane, Window, CColumns, CPile, CSimpleFocusListWalker


class DateConversionError(Exception):
    pass


class AccountList(urwid.WidgetWrap):
    """used as the popup in the AccountChooser popup"""
    signals = ['close']

    def __init__(self, accounts, account_chooser):
        self.account_chooser = account_chooser
        acc_list = []
        for one in accounts:
            button = urwid.Button(one, on_press=self.set_account,
                                  user_data=one)

            acc_list.append(button)
        pile = CPile(acc_list)
        fill = urwid.Filler(pile)
        self.__super.__init__(urwid.AttrMap(fill, 'popupbg'))

    def set_account(self, button, account):
        self.account_chooser.account = account
        self._emit("close")


class AccountChooser(urwid.PopUpLauncher):
    """show current account and lets user choose another account

    does NOT handle the actual moving of an event to another account"""
    def __init__(self, active_account, accounts):
        self.active_account = active_account
        self.original_account = active_account
        self.accounts = accounts
        self.button = urwid.Button(active_account)
        self.__super.__init__(self.button)
        urwid.connect_signal(self.button, 'click',
                             lambda button: self.open_pop_up())

    def create_pop_up(self):
        pop_up = AccountList(self.accounts, self)
        urwid.connect_signal(pop_up, 'close',
                             lambda button: self.close_pop_up())
        return pop_up

    def get_pop_up_parameters(self):
        return {'left': 0,
                'top': 1,
                'overlay_width': 32,
                'overlay_height': len(self.accounts)}

    @property
    def changed(self):
        if self.active_account == self.original_account:
            return False
        else:
            return True

    @property
    def account(self):
        return self.active_account

    @account.setter
    def account(self, account):
        self.active_account = account
        self.button = urwid.Button(self.active_account)
        self.__super.__init__(self.button)
        urwid.connect_signal(self.button, 'click',
                             lambda button: self.open_pop_up())


class Date(urwid.Text):
    """used in the main calendar for dates (a number)"""

    def __init__(self, date, view):
        self.date = date
        self.view = view
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
        if key in ['n']:
            self.view.new_event(self.date)
            return 'tab'  # TODO return next
        else:
            return key


class DateCColumns(CColumns):
    """container for one week worth of dates
    which are horizontally aligned

    TODO: rename, awful name

    focus can only move away by pressing 'TAB',
    calls 'view.show_date' on every focus change (see below for details)
    """
    def __init__(self, widget_list, view=None, **kwargs):
        self.view = view
        super(DateCColumns, self).__init__(widget_list, **kwargs)

    def _set_focus_position(self, position):
        """calls view.show_date before calling super()._set_focus_position"""

        super(DateCColumns, self)._set_focus_position(position)

        # since first Column is month name, focus should only be 0 during
        # construction
        if not self.contents.focus == 0:
            self.view.show_date(self.contents[position][0].original_widget.date)

    focus_position = property(CColumns._get_focus_position,
                              _set_focus_position, doc="""
index of child widget in focus. Raises IndexError if read when
CColumns is empty, or when set to an invalid index.
""")

    def keypress(self, size, key):
        """only leave calendar area on pressing 'TAB'"""

        old_pos = self.focus_position
        key = super(DateCColumns, self).keypress(size, key)
        if key in ['tab', 'enter']:
            return 'right'
        elif old_pos == 7 and key == 'right':
            self.focus_position = 1
            return 'down'
        elif old_pos == 1 and key == 'left':
            self.focus_position = 7
            return 'up'
        elif key not in ['right']:
            return key
        else:
            return key


def calendar_walker(view, firstweekday=0):
    """hopefully this will soon become a real "walker",
    loading new weeks as needed"""
    calendar.setfirstweekday(firstweekday)
    dnames = calendar.weekheader(2).split(' ')
    dnames = CColumns(
        [(4, urwid.Text('    '))] + [(2, urwid.Text(name)) for name in dnames],
        dividechars=1)

    weeks = CalendarWalker(view=view, firstweekday=firstweekday)
    box = urwid.ListBox(weeks)
    frame = urwid.Frame(box, header=dnames)
    return frame


class CalendarWalker(urwid.SimpleFocusListWalker):
    def __init__(self, view, firstweekday=0):
        self.firstweekday = firstweekday
        self.view = view
        weeks, focus_item = self._construct_month()
        urwid.SimpleFocusListWalker.__init__(self, weeks)
        self.set_focus(focus_item)

    def set_focus(self, position):
        if position == 0:
            position = self._autoprepend()
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
        date_first_month = self[0][-1].date  # a date from the first month
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
        constructs a CColumns week from a week of datetime.date objects. Also prepends the month name
        if the first day of the month is included in that week.

        :param week: list of datetime.date objects
        :returns: the week as an CColumns object and True or False depending on
                  if today is in this week
        :rtype: tuple(urwid.CColumns, bool)
        """
        if 1 in [day.day for day in week]:
            month_name = calendar.month_abbr[week[-1].month].ljust(4)
        else:
            month_name = '    '

        this_week = [(4, urwid.Text(month_name))]
        today = None
        for number, day in enumerate(week):
            if day == date.today():
                this_week.append((2, urwid.AttrMap(Date(day, self.view),
                                                   'today', 'today_focus')))
                today = number + 1
            else:
                this_week.append((2, urwid.AttrMap(Date(day, self.view),
                                                   None, 'reveal focus')))
        week = DateCColumns(this_week, view=self.view, dividechars=1,
                            focus_column=today)
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
        :param clean_first_row: makes sure that the first element returned is completely in `month` and
                                not partly in the one before (which might lead to that line occurring
                                twice
        :type clean_first_row: bool
        :param clean_last_row: makes sure that the last element returned is completely in `month` and
                                not partly in the one after (which might lead to that line occurring
                                twice
        :type clean_last_row: bool
        :returns: list of DateCColumns and the number of the list element which
                  contains today (or None if it isn't in there)
        :rtype: tuple(list(dateCColumns, int or None))
        """

        plain_weeks = calendar.Calendar(self.firstweekday).monthdatescalendar(year, month)
        weeks = list()
        focus_item = None
        for number, week in enumerate(plain_weeks):
            week, contains_today = self._construct_week(week)
            if contains_today:
                focus_item = number
            weeks.append(week)
        if clean_first_row and weeks[0][1].date.month != weeks[0][7].date.month:
            if focus_item is not None:
                focus_item = focus_item - 1
            return weeks[1:], focus_item
        elif clean_last_row and weeks[-1][1].date.month != weeks[-1][7].date.month:
            return weeks[:-1], focus_item
        else:
            return weeks, focus_item


class U_Event(urwid.Text):
    def __init__(self, event, this_date=None, conf=None,
                 eventcolumn=None):
        """
        representation of an event in EventList

        :param event: the encapsulated event
        :type event: khal.event.Event
        """

        self.event = event
        self.this_date = this_date
        self.conf = conf
        self.eventcolumn = eventcolumn
        self.view = False
        super(U_Event, self).__init__(self.event.compact(self.this_date))

    @classmethod
    def selectable(cls):
        return True

    def toggle_delete(self):
        if self.event.readonly is False:
            # TODO update for NEWNOTSAVED
            if self.event.status == OK:
                toggle = DELETED
            elif self.event.status == DELETED:
                toggle = OK
            elif self.event.status == NEW:
                toggle = NEWDELETE
            elif self.event.status == NEWDELETE:
                toggle = NEW
            else:
                toggle = DELETED
            self.event.status = toggle
            self.set_text(self.event.compact(self.this_date))
            self.eventcolumn.collection.mark(toggle, self.event)
        else:
            self.set_text('RO' + self.event.compact(self.this_date))

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
    def __init__(self, conf=None, collection=None, eventcolumn=None):
        self.conf = conf
        self.collection = collection
        self.eventcolumn = eventcolumn
        pile = urwid.Filler(CPile([]))
        urwid.WidgetWrap.__init__(self, pile)
        self.update()

    def update(self, this_date=date.today()):

        start = datetime.combine(this_date, time.min)
        end = datetime.combine(this_date, time.max)

        date_text = urwid.Text(
            this_date.strftime(self.conf.default.longdateformat))
        event_column = list()
        all_day_events = self.collection.get_allday_by_time_range(this_date)
        events = self.collection.get_datetime_by_time_range(start, end)

        for event in all_day_events:
            event_column.append(
                urwid.AttrMap(U_Event(event,
                                      conf=self.conf,
                                      this_date=this_date,
                                      eventcolumn=self.eventcolumn),
                              event.color, 'reveal focus'))
        events.sort(key=lambda e: e.start)
        for event in events:
            event_column.append(
                urwid.AttrMap(U_Event(event,
                                      conf=self.conf,
                                      this_date=this_date,
                                      eventcolumn=self.eventcolumn),
                              event.color, 'reveal focus'))
        event_list = [urwid.AttrMap(event, None, 'reveal focus') for event in event_column]
        event_count = len(event_list)
        if not event_list:
            event_list = [urwid.Text('no scheduled events')]
        pile = urwid.ListBox(CSimpleFocusListWalker(event_list))
        pile = urwid.Frame(pile, header=date_text)
        self._w = pile
        return event_count


class EventColumn(urwid.WidgetWrap):
    """contains the eventlist as well as the event viewer/editor"""
    def __init__(self, conf=None, collection=None):
        self.conf = conf
        self.collection = collection
        self.divider = urwid.Divider('-')
        self.editor = False
        self.date = None
        self.eventcount = 0

    def update(self, date):
        """create an EventList populated with Events for `date` and display it
        """
        self.date = date
        # TODO make this switch from pile to columns depending on terminal size
        events = EventList(conf=self.conf, collection=self.collection, eventcolumn=self)
        self.eventcount = events.update(date)
        self.container = CPile([events])
        self._w = self.container

    def view(self, event):
        """
        show an event's details

        :param event: event to view
        :type event: khal.event.Event
        """
        self.destroy()
        self.container.contents.append((self.divider,
                                        ('pack', None)))
                                        #self.container.options()))
        self.container.contents.append(
            (EventDisplay(self.conf, event, collection=self.collection),
             self.container.options()))

    def edit(self, event):
        """create an EventEditor and display it

        :param event: event to edit
        :type event: khal.event.Event
        """
        self.destroy()
        self.editor = True
        #self.container.contents.append((self.divider,
                                        #self.container.options()))
        self.container.contents.append((self.divider,
                                        ('pack', None)))
        self.container.contents.append(
            (EventEditor(self.conf, event, collection=self.collection, cancel=self.destroy),
             self.container.options()))
        self.container.set_focus(2)

    def destroy(self, _=None, refresh=False):
        """
        if an EventViewer or EventEditor is displayed, remove it
        """
        if refresh and not self.date is None:
            self.update(self.date)
        self.editor = False
        if (len(self.container.contents) > 2 and
                isinstance(self.container.contents[2][0], EventViewer)):
            self.container.contents.pop()
            self.container.contents.pop()

    def new(self, date):
        """create a new event on date

        :param date: default date for new event
        :type date: datetime.date
        """
        event = aux.new_event(dtstart=date,
                              timezone=self.conf.default.default_timezone)
        event = Event(ical=event.to_ical(), status=NEWNOTSAVED,
                      account=list(self.conf.sync.accounts)[-1])
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


class StartEndEditor(urwid.WidgetWrap):
    """
    editing start and nd times of the event

    we cannot change timezones ATM  # TODO
    pop up on strings not matching timeformat # TODO
    """

    def __init__(self, start, end, conf):
        self.conf = conf
        self.startdt = start
        self.enddt = end
        # TODO cleanup
        self.startdate = self.startdt.strftime(self.conf.default.longdateformat)
        self.starttime = self.startdt.strftime(self.conf.default.timeformat)
        self.enddate = self.enddt.strftime(self.conf.default.longdateformat)
        self.endtime = self.enddt.strftime(self.conf.default.timeformat)
        self.startdate_bg = 'edit'
        self.starttime_bg = 'edit'
        self.enddate_bg = 'edit'
        self.endtime_bg = 'edit'
        self.startdatewidget = None
        self.starttimewidget = None
        self.enddatewidget = None
        self.endtimewidget = None
        self.allday = False
        if not isinstance(start, datetime):
            self.allday = True

        self.checkallday = urwid.CheckBox('Allday', state=self.allday,
                                          on_state_change=self.toggle)
        self.toggle(None, self.allday)

    def toggle(self, checkbox, state):
        """change from allday to datetime event

        :param checkbox: the checkbox instance that is used for toggling, gets
                         automatically passed by urwid (is not used)
        :type checkbox: checkbox
        :param state: True if allday event, False if datetime
        :type state: bool
        """
        self.allday = state
        datewidth = len(self.startdate) + 7

        edit = urwid.Edit(caption=('', 'From: '), edit_text=self.startdate, wrap='any')
        edit = urwid.AttrMap(edit, self.startdate_bg, 'editcp', )
        edit = urwid.Padding(edit, align='left', width=datewidth, left=0, right=1)
        self.startdatewidget = edit

        edit = urwid.Edit(caption=('', 'To:   '), edit_text=self.enddate, wrap='any')
        edit = urwid.AttrMap(edit, self.enddate_bg, 'editcp', )
        edit = urwid.Padding(edit, align='left', width=datewidth, left=0, right=1)
        self.enddatewidget = edit
        if state is True:
            timewidth = 1
            self.starttimewidget = urwid.Text('')
            self.endtimewidget = urwid.Text('')
        elif state is False:
            timewidth = len(self.starttime) + 1
            edit = urwid.Edit(edit_text=self.starttime, wrap='any')
            edit = urwid.AttrMap(edit, self.starttime_bg, 'editcp', )
            edit = urwid.Padding(edit, align='left', width=len(self.starttime) + 1, left=1)
            self.starttimewidget = edit

            edit = urwid.Edit(edit_text=self.endtime, wrap='any')
            edit = urwid.AttrMap(edit, self.endtime_bg, 'editcp', )
            edit = urwid.Padding(edit, align='left', width=len(self.endtime) + 1, left=1)
            self.endtimewidget = edit

        columns = CPile([
            CColumns([(datewidth, self.startdatewidget), (timewidth, self.starttimewidget)], dividechars=1),
            CColumns([(datewidth, self.enddatewidget), (timewidth, self.endtimewidget)], dividechars=1),
            self.checkallday], focus_item=2)
        urwid.WidgetWrap.__init__(self, columns)

    @property
    def changed(self):
        """
        returns True if content has been edited, False otherwise
        """
        return ((self.startdt != self.newstart) or
                (self.enddt != self.newend))

    @property
    def newstart(self):
        newstartdatetime = self._newstartdate
        if not self.checkallday.state:
            if not hasattr(self.startdt, 'tzinfo') or self.startdt.tzinfo is None:
                tzinfo = self.conf.default.default_timezone
            else:
                tzinfo = self.startdt.tzinfo
            try:
                newstarttime = self._newstarttime
                newstartdatetime = datetime.combine(newstartdatetime, newstarttime)
                newstartdatetime = tzinfo.localize(newstartdatetime)
            except TypeError:
                return None
        return newstartdatetime

    @property
    def _newstartdate(self):
        try:
            self.startdate = self.startdatewidget.original_widget.original_widget.get_edit_text()
            newstartdate = datetime.strptime(
                self.startdate,
                self.conf.default.longdateformat).date()
            self.startdate_bg = 'edit'
            return newstartdate
        except ValueError:
            self.startdate_bg = 'alert'
            return None

    @property
    def _newstarttime(self):
        try:
            self.starttime = self.starttimewidget.original_widget.original_widget.get_edit_text()
            newstarttime = datetime.strptime(
                self.starttime,
                self.conf.default.timeformat).time()
            self.starttime_bg = 'edit'
            return newstarttime
        except ValueError:
            self.starttime_bg = 'alert'
            return None

    @property
    def newend(self):
        newenddatetime = self._newenddate
        if not self.checkallday.state:
            if not hasattr(self.enddt, 'tzinfo') or self.enddt.tzinfo is None:
                tzinfo = self.conf.default.default_timezone
            else:
                tzinfo = self.enddt.tzinfo
            try:
                newendtime = self._newendtime
                newenddatetime = datetime.combine(newenddatetime, newendtime)
                newenddatetime = tzinfo.localize(newenddatetime)
            except TypeError:
                return None
        return newenddatetime

    @property
    def _newenddate(self):
        try:
            self.enddate = self.enddatewidget.original_widget.original_widget.get_edit_text()
            newenddate = datetime.strptime(
                self.enddate,
                self.conf.default.longdateformat).date()
            self.enddate_bg = 'edit'
            return newenddate
        except ValueError:
            self.enddate_bg = 'alert'
            return None

    @property
    def _newendtime(self):
        try:
            self.endtime = self.endtimewidget.original_widget.original_widget.get_edit_text()
            newendtime = datetime.strptime(
                self.endtime,
                self.conf.default.timeformat).time()
            self.endtime_bg = 'edit'
            return newendtime
        except ValueError:
            self.endtime_bg = 'alert'
            return None


class EventViewer(urwid.WidgetWrap):
    """
    Base Class for EventEditor and EventDisplay
    """
    def __init__(self, conf, collection):
        self.conf = conf
        self.collection = collection
        pile = CPile([])
        urwid.WidgetWrap.__init__(self, pile)


class EventDisplay(EventViewer):
    """showing events

    widget for displaying one event's details
    """
    def __init__(self, conf, event, collection=None):
        super(EventDisplay, self).__init__(conf, collection)
        lines = []
        lines.append(urwid.Text(event.vevent['SUMMARY']))

        # start and end time/date
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

        # resource
        lines.append(urwid.Text('Calendar: ' + event.account))

        # description and location
        for key, desc in [('DESCRIPTION', 'Desc'), ('LOCATION', 'Loc')]:
            try:
                lines.append(urwid.Text(
                    desc + ': ' + str(event.vevent[key].encode('utf-8'))))
            except KeyError:
                pass

        pile = CPile(lines)
        self._w = urwid.Filler(pile, valign='top')


class EventEditor(EventViewer):
    """
    Widget for event Editing
    """
    def __init__(self, conf, event, collection=None, cancel=None):
        """
        :type event: khal.event.Event
        :param cancel: to be executed on pressing the cancel button
        :type cancel: function/method
        """
        super(EventEditor, self).__init__(conf, collection)
        self.event = event
        self.cancel = cancel
        try:
            self.description = event.vevent['DESCRIPTION']
        except KeyError:
            self.description = u''
        try:
            self.location = event.vevent['LOCATION']
        except KeyError:
            self.location = u''

        self.startendeditor = StartEndEditor(event.start, event.end, self.conf)
        try:
            rrule = self.event.vevent['RRULE']
        except KeyError:
            rrule = None
        self.recursioneditor = RecursionEditor(rrule)
        self.summary = urwid.Edit(
            edit_text=event.vevent['SUMMARY'])
        self.accountchooser = AccountChooser(self.event.account,
                                             self.conf.sync.accounts)
        accounts = CColumns([(9, urwid.Text(u'Calendar: ')),
                             self.accountchooser])
        self.description = urwid.Edit(caption=u'Description: ',
                                      edit_text=self.description)
        self.location = urwid.Edit(caption=u'Location: ',
                                   edit_text=self.location)
        cancel = urwid.Button(u'Cancel', on_press=self.cancel)
        save = urwid.Button(u'Save', on_press=self.save)
        buttons = CColumns([cancel, save])

        self.pile = urwid.ListBox(CSimpleFocusListWalker(
            [self.summary,
             accounts,
             self.startendeditor,
             self.recursioneditor, self.description,
             self.location, urwid.Text(''), buttons
             ]))

        self._w = self.pile

    @classmethod
    def selectable(cls):
        return True

    @property
    def changed(self):
        # TODO refactor
        changed = False
        if self.summary.get_edit_text() != self.event.vevent['SUMMARY']:
            changed = True

        key = 'DESCRIPTION'
        if ((key in self.event.vevent and self.description.get_edit_text() != self.event.vevent[key]) or
                self.description.get_edit_text() != ''):
            changed = True

        key = 'LOCATION'
        if ((key in self.event.vevent and self.description.get_edit_text() != self.event.vevent[key]) or
                self.location.get_edit_text() != ''):
            changed = True

        if self.startendeditor.changed:
            changed = True
        if self.accountchooser.changed:
            changed = True
        return changed

    def update(self):
        changed = False
        if self.summary.get_edit_text() != self.event.vevent['SUMMARY']:
            self.event.vevent['SUMMARY'] = self.summary.get_edit_text()
            changed = True

        for key, prop in [('DESCRIPTION', self.description), ('LOCATION', self.location)]:
            if ((key in self.event.vevent and prop.get_edit_text() != self.event.vevent[key]) or
                    prop.get_edit_text() != ''):
                self.event.vevent[key] = prop.get_edit_text()
                changed = True

        if self.startendeditor.changed:
            # TODO look up why this is needed
            # self.event.vevent.dt = newstart would not work
            # (timezone was missing after to_ical() )
            self.event.vevent.pop('DTSTART')
            self.event.vevent.add('DTSTART', self.startendeditor.newstart)
            try:
                self.event.vevent.pop('DTEND')
                self.event.vevent.add('DTEND', self.startendeditor.newend)
            except KeyError:
                self.event.vevent.pop('DURATION')
                duration = (self.startendeditor.newend -
                            self.startendeditor.newstart)
                self.event.vevent.add('DURATION', duration)

            changed = True
        if self.accountchooser.changed:
            changed = True
            # TODO self.newaccount = self.accountchooser.account ?
        return changed

    def save(self, button):
        """
        saves the event to the db (only when it has been changed)
        :param button: not needed, passed via the button press
        """
        changed = self.changed  # need to call this to set date backgrounds to False
        self.update()
        if 'alert' in [self.startendeditor.startdate_bg,
                       self.startendeditor.starttime_bg,
                       self.startendeditor.enddate_bg,
                       self.startendeditor.endtime_bg]:
            self.startendeditor.toggle(None, state=self.startendeditor.allday)
            self.pile.set_focus(1)  # the startendeditor
            return
        if changed is True:
            try:
                self.event.vevent['SEQUENCE'] += 1
            except KeyError:
                self.event.vevent['SEQUENCE'] = 0

            if self.event.status == NEWNOTSAVED:
                self.collection.new(self.event)
            elif self.accountchooser.changed:
                self.collection.change_collection(self.event,
                                                  self.accountchooser.account)
            else:
                self.collection.update(self.event)

        self.cancel(refresh=True)

    def keypress(self, size, key):
        if key in ['esc']:
            if self.changed:
                return
            else:
                self.cancel()
                return
        key = super(EventEditor, self).keypress(size, key)
        if key in ['left', 'up']:
            return
        else:
            return key


class ClassicView(Pane):
    """default Pane for khal

    showing a CalendarWalker on the left and the eventList + eventviewer/editor
    on the right
    """
    def __init__(self, collection, conf=None, title=u'',
                 description=u''):
        self.collection = collection
        self.eventscolumn = EventColumn(conf=conf, collection=collection)
        weeks = calendar_walker(view=self, firstweekday=conf.default.firstweekday)
        events = self.eventscolumn
        columns = CColumns([(25, weeks), events],
                           dividechars=2, box_columns=[0, 1])
        self.eventscolumn.update(date.today())  # showing with today's events
        Pane.__init__(self, columns, title=title, description=description)

    def get_keys(self):
        return [(['arrows'], 'navigate through the calendar'),
                (['enter'], 'select a date'),
                (['q'], 'quit')
                ]

    def show_date(self, date):
        self.eventscolumn.update(date)

    def new_event(self, date):
        self.eventscolumn.new(date)


def start_pane(pane, header=''):
    """Open the user interface with the given initial pane."""
    frame = Window(header=header,
                   footer='arrows: navigate, enter: select, q: quit, ?: help')
    frame.open(pane)
    loop = urwid.MainLoop(frame, Window.PALETTE,
                          unhandled_input=frame.on_key_press,
                          pop_ups=True)
    loop.run()
