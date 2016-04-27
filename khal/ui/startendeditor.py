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

from datetime import datetime, time

import urwid
import pytz

from .widgets import DateWidget, TimeWidget, NColumns, NPile, ValidatedEdit, EditSelect
from .calendarwidget import CalendarWidget


class DateConversionError(Exception):
    pass


class StartEnd(object):

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
            self._get_base_widget().set_value(new_date)
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
    """Wigdet for editing start and end times (of an event)"""

    def __init__(self, start, end, conf, on_date_change=lambda x: None):
        """
        :type start: datetime.datetime
        :type end: datetime.datetime
        :param on_date_change: a callable that gets called everytime a new
            date is entered, with that new date as an argument
        """
        self.allday = not isinstance(start, datetime)
        self._tz_state = False

        self.conf = conf

        self._original_start = start
        self._original_end = end

        def separate_date_time_timezone(dtime):
            if isinstance(dtime, datetime):
                date_ = dtime.date()
                time_ = dtime.time()
                timezone_ = dtime.tzinfo
            else:
                date_ = start
                time_ = None
                timezone_ = None
            return {'date': date_, 'time': time_, 'timezone': timezone_}

        self._startdt = separate_date_time_timezone(start)
        self._enddt = separate_date_time_timezone(end)

        self.on_date_change = on_date_change
        self._datewidth = len(start.strftime(self.conf['locale']['longdateformat']))
        self._timewidth = len(start.strftime(self.conf['locale']['timeformat']))
        # this will contain the widgets for [start|end] [date|time]
        self.widgets = StartEnd(None, None, None, None)

        self.checkallday = urwid.CheckBox(
            'Allday', state=self.allday, on_state_change=self.toggle_allday)
        self.rebuild()

    def keypress(self, size, key):
        return super().keypress(size, key)

    @property
    def startdt(self):
        if self.allday and self._startdt['time'] is None:
            return self._startdt['date']
        else:
            return datetime.combine(self._startdt['date'], self._startdt['time'])

    @property
    def enddt(self):
        if self.allday and self._enddt['time'] is None:
            return self._enddt['date']
        else:
            return datetime.combine(self._enddt['date'], self._enddt['time'])


    def _validate_dt(self, startend, type_, dformat, function, text):
        try:
            getattr(self, startend)[type_] = function(datetime.strptime(text, self.conf['locale'][dformat]))
            return True
        except ValueError:
            False

    def _validate_start_time(self, text):
        return self._validate_dt('_startdt', 'time', 'timeformat', datetime.time, text)

    def _validate_start_date(self, text):
        return self._validate_dt('_startdt', 'date', 'longdateformat', datetime.date, text)

    def _validate_end_time(self, text):
        return self._validate_dt('_enddt', 'time', 'timeformat', datetime.time, text)

    def _validate_end_date(self, text):
        return self._validate_dt('_enddt', 'date', 'longdateformat', datetime.date, text)

    def toggle_allday(self, checkbox, state):
        """change from allday to datetime event

        :param checkbox: the checkbox instance that is used for toggling, gets
                         automatically passed by urwid (is not used)
        :type checkbox: checkbox
        :param state: allday-eventness of this event;
                      True if allday event, False if datetime
        :type state: bool
        """

        if self.allday is True and state is False:
            self._startdt['time'] = self._original_start.time()
            self._enddt['time'] = self._original_end.time()
        elif self.allday is False and state is True:
            self._startdt['time'] = None
            self._enddt['time'] = None
        self.allday = state
        self.rebuild()

    def toggle_tz(self, checkbox, state):
        """change from displaying the timezone chooser or not

        :param checkbox: the checkbox instance that is used for toggling, gets
                         automatically passed by urwid (is not used)
        :type checkbox: checkbox
        :param state: show timezone chooser or not
        :type state: bool

        """
        self._tz_state = state
        self.rebuild()
        self._start_edit.set_focus(3)
        if self._tz_state is False and state is True:
            self._startdt = self._get_chosen_timezone()
            self._enddt = self._get_chosen_timezone()
        elif self._tz_state is True and state is False:
            self._startdt['timezone'] = None
            self._enddt['timezone'] = None

    def rebuild(self):
        """rebuild the start/end/timezone editor"""
        datewidth = self._datewidth + 7
        # startdate
        edit = ValidatedEdit(
            dateformat=self.conf['locale']['longdateformat'],
            EditWidget=DateWidget,
            validate=self._validate_start_date,
            caption=('', 'From: '),
            edit_text=self.startdt.strftime(self.conf['locale']['longdateformat']),
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
            edit_text=self.enddt.strftime(self.conf['locale']['longdateformat']),
            on_date_change=self.on_date_change)
        edit = CalendarPopUp(edit, self.conf, self.on_date_change)
        edit = urwid.Padding(edit, align='left', width=datewidth, left=0, right=1)
        self.widgets.enddate = edit

        if self.allday is True:
            timewidth = 1
            self.widgets.starttime = urwid.Text('')
            self.widgets.endtime = urwid.Text('')
            self._tz_widget = urwid.Text('')
        elif self.allday is False:
            timewidth = self._timewidth + 1
            edit = ValidatedEdit(
                dateformat=self.conf['locale']['timeformat'],
                EditWidget=TimeWidget,
                validate=self._validate_start_time,
                edit_text=self.startdt.strftime(self.conf['locale']['timeformat']),
            )
            edit = urwid.Padding(
                edit, align='left', width=self._timewidth + 1, left=1)
            self.widgets.starttime = edit

            edit = ValidatedEdit(
                dateformat=self.conf['locale']['timeformat'],
                EditWidget=TimeWidget,
                validate=self._validate_end_time,
                edit_text=self.enddt.strftime(self.conf['locale']['timeformat']),
            )
            edit = urwid.Padding(
                edit, align='left', width=self._timewidth + 1, left=1)
            self.widgets.endtime = edit

            if self._tz_state:
                self._tz_widget = EditSelect(
                    pytz.common_timezones, str(self._startdt['timezone']), win_len=10)
            else:
                self._tz_widget = urwid.Text('')

        self._start_edit = NColumns(
            [
                (datewidth, self.widgets.startdate),
                (timewidth, self.widgets.starttime),
                (3, urwid.Text('\N{EARTH GLOBE EUROPE-AFRICA}')),
                (4, urwid.CheckBox('', state=self._tz_state, on_state_change=self.toggle_tz)),
                self._tz_widget,
            ],
            dividechars=1
        )
        self._end_edit = NColumns(
            [(datewidth, self.widgets.enddate), (timewidth, self.widgets.endtime)],
            dividechars=1)
        columns = NPile(
            [self.checkallday, self._start_edit, self._end_edit],
            focus_item=1)
        urwid.WidgetWrap.__init__(self, columns)

    def _get_chosen_timezone(self):
        import pdb; pdb.set_trace()


    @property
    def changed(self):
        """returns True if content has been edited, False otherwise"""
        return (self.startdt != self._original_start) or (self.enddt != self._original_end)

    def validate(self):
        """make sure startdt <= enddt"""
        return self.startdt <= self.enddt
