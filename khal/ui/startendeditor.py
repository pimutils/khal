# Copyright (c) 2013-2016 Christian Geier et al.
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

from datetime import datetime

import urwid

from .widgets import DateWidget, TimeWidget, NColumns, NPile, ValidatedEdit
from .calendarwidget import CalendarWidget


class DateConversionError(Exception):
    pass


class StartEnd(object):
    # TODO convert to namespace

    def __init__(self, startdate, starttime, enddate, endtime):
        """collecting some common properties"""
        self.startdate = startdate
        self.starttime = starttime
        self.enddate = enddate
        self.endtime = endtime


class CalendarPopUp(urwid.PopUpLauncher):
    def __init__(self, widget, conf, on_date_change):
        self._conf = conf
        self._on_date_change = on_date_change
        self.__super.__init__(widget)

    def keypress(self, size, key):
        if key == 'enter':
            self.open_pop_up()
        else:
            return super().keypress(size, key)

    def create_pop_up(self):
        def on_change(new_date):
            self._original_widget.set_value(new_date)
            self._on_date_change(new_date)

        keybindings = self._conf['keybindings']
        on_press = {'enter': lambda _, __: self.close_pop_up(),
                    'esc': lambda _, __: self.close_pop_up()}
        pop_up = CalendarWidget(
            on_change, keybindings, on_press,
            firstweekday=self._conf['locale']['firstweekday'],
            weeknumbers=self._conf['locale']['weeknumbers'],
            initial=self.base_widget._get_current_value())
        pop_up = urwid.LineBox(pop_up)
        return pop_up

    def get_pop_up_parameters(self):
        width = 31 if self._conf['locale']['weeknumbers'] == 'right' else 28
        return {'left': 0, 'top': 1, 'overlay_width': width, 'overlay_height': 8}


class StartEndEditor(urwid.WidgetWrap):
    """
    Wigdet for editing start and end times (of an event)

    we cannot change timezones ATM  # TODO
    pop up on strings not matching timeformat # TODO
    """

    def __init__(self, start, end, conf, on_date_change=lambda x: None):
        self.allday = not isinstance(start, datetime)
        self.conf = conf
        self.startdt = start
        self.enddt = end
        self.on_date_change = on_date_change
        self.dts = StartEnd(
            startdate=start.strftime(self.conf['locale']['longdateformat']),
            starttime=start.strftime(self.conf['locale']['timeformat']),
            enddate=end.strftime(self.conf['locale']['longdateformat']),
            endtime=end.strftime(self.conf['locale']['timeformat']))
        # this will contain the widgets for [start|end] [date|time]
        self.widgets = StartEnd(None, None, None, None)

        self.checkallday = urwid.CheckBox('Allday', state=self.allday,
                                          on_state_change=self.toggle)
        self.toggle(None, self.allday)

    def _validate_date(self, text):
        try:
            return datetime.strptime(text, self.conf['locale']['longdateformat'])
        except ValueError:
            return False

    def _validate_time(self, text):
        try:
            return datetime.strptime(text, self.conf['locale']['timeformat'])
        except ValueError:
            return False

    def _validate_end_date(self, text):
        return self._validate_date(text) and self.newstart <= self.newend

    def toggle(self, checkbox, state):
        """change from allday to datetime event

        :param checkbox: the checkbox instance that is used for toggling, gets
                         automatically passed by urwid (is not used)
        :type checkbox: checkbox
        :param state: state the event will toggle to;
                      True if allday event, False if datetime
        :type state: bool
        """
        self.allday = state
        datewidth = len(self.dts.startdate) + 7

        # startdate
        edit = ValidatedEdit(
            dateformat=self.conf['locale']['longdateformat'],
            EditWidget=DateWidget,
            validate=self._validate_date,
            caption=('', 'From: '),
            edit_text=self.dts.startdate,
            on_date_change=self.on_date_change)
        edit = CalendarPopUp(edit, self.conf, self.on_date_change)
        edit = urwid.Padding(edit, align='left', width=datewidth, left=0, right=1)
        self.widgets.startdate = edit

        # enddate
        edit = ValidatedEdit(
            dateformat=self.conf['locale']['longdateformat'],
            EditWidget=DateWidget,
            validate=self._validate_end_date,
            caption=('', 'To:   '),
            edit_text=self.dts.enddate,
            on_date_change=self.on_date_change)
        edit = CalendarPopUp(edit, self.conf, self.on_date_change)
        edit = urwid.Padding(edit, align='left', width=datewidth, left=0, right=1)
        self.widgets.enddate = edit

        if state is True:
            timewidth = 1
            self.widgets.starttime = urwid.Text('')
            self.widgets.endtime = urwid.Text('')
        elif state is False:
            timewidth = len(self.dts.starttime) + 1
            edit = ValidatedEdit(
                dateformat=self.conf['locale']['timeformat'],
                EditWidget=TimeWidget,
                validate=self._validate_time,
                edit_text=self.dts.starttime)
            edit = urwid.Padding(
                edit, align='left', width=len(self.dts.starttime) + 1, left=1)
            self.widgets.starttime = edit

            edit = ValidatedEdit(
                dateformat=self.conf['locale']['timeformat'],
                EditWidget=TimeWidget,
                validate=self._validate_time,
                edit_text=self.dts.endtime)
            edit = urwid.Padding(
                edit, align='left', width=len(self.dts.endtime) + 1, left=1)
            self.widgets.endtime = edit

        columns = NPile([
            self.checkallday,
            NColumns([(datewidth, self.widgets.startdate), (
                timewidth, self.widgets.starttime)], dividechars=1),
            NColumns(
                [(datewidth, self.widgets.enddate),
                 (timewidth, self.widgets.endtime)],
                dividechars=1)
        ], focus_item=1)
        urwid.WidgetWrap.__init__(self, columns)

    @property
    def changed(self):
        """returns True if content has been edited, False otherwise"""
        return (self.startdt != self.newstart) or (self.enddt != self.newend)

    @property
    def newstart(self):
        newstartdatetime = self._newstartdate
        if not self.checkallday.state:
            if getattr(self.startdt, 'tzinfo', None) is None:
                tzinfo = self.conf['locale']['default_timezone']
            else:
                tzinfo = self.startdt.tzinfo
            try:
                newstartdatetime = datetime.combine(newstartdatetime, self._newstarttime)
                newstartdatetime = tzinfo.localize(newstartdatetime)
            except TypeError:
                return None
        return newstartdatetime

    @property
    def _newstartdate(self):
        self.dts.startdate = self.widgets.startdate.base_widget.get_edit_text()
        return self._validate_date(self.dts.startdate)

    @property
    def _newstarttime(self):
        self.dts.starttime = self.widgets.starttime.base_widget.get_edit_text()
        return self._validate_time(self.dts.starttime).time()

    @property
    def newend(self):
        newenddatetime = self._newenddate
        if not self.checkallday.state:
            if not hasattr(self.enddt, 'tzinfo') or self.enddt.tzinfo is None:
                tzinfo = self.conf['locale']['default_timezone']
            else:
                tzinfo = self.enddt.tzinfo
            try:
                newenddatetime = datetime.combine(newenddatetime, self._newendtime)
                newenddatetime = tzinfo.localize(newenddatetime)

            except TypeError:
                return None
        return newenddatetime

    @property
    def _newenddate(self):
        self.enddate = self.widgets.enddate.base_widget.get_edit_text()
        return self._validate_date(self.enddate)

    @property
    def _newendtime(self):
        self.dts.endtime = self.widgets.endtime.base_widget.get_edit_text()
        return self._validate_time(self.dts.endtime).time()
