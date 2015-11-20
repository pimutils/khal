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

from datetime import datetime

import urwid

from .widgets import DateWidget, TimeWidget


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
        # and these are their background colors
        self.bgs = StartEnd('edit', 'edit', 'edit', 'edit')

        self.checkallday = urwid.CheckBox('Allday', state=self.allday,
                                          on_state_change=self.toggle)
        self.toggle(None, self.allday)

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

        edit = DateWidget(
            self.conf['locale']['longdateformat'],
            caption=('', 'From: '), edit_text=self.dts.startdate,
            on_date_change=self.on_date_change)
        edit = urwid.AttrMap(edit, self.bgs.startdate, 'editcp', )
        edit = urwid.Padding(
            edit, align='left', width=datewidth, left=0, right=1)
        self.widgets.startdate = edit

        edit = DateWidget(
            self.conf['locale']['longdateformat'],
            caption=('', 'To:   '), edit_text=self.dts.enddate)
        edit = urwid.AttrMap(edit, self.bgs.enddate, 'editcp', )
        edit = urwid.Padding(
            edit, align='left', width=datewidth, left=0, right=1)
        self.widgets.enddate = edit
        if state is True:
            timewidth = 1
            self.widgets.starttime = urwid.Text('')
            self.widgets.endtime = urwid.Text('')
        elif state is False:
            timewidth = len(self.dts.starttime) + 1
            edit = TimeWidget(
                self.conf['locale']['timeformat'],
                edit_text=self.dts.starttime)
            edit = urwid.AttrMap(edit, self.bgs.starttime, 'editcp', )
            edit = urwid.Padding(
                edit, align='left', width=len(self.dts.starttime) + 1, left=1)
            self.widgets.starttime = edit

            edit = TimeWidget(
                self.conf['locale']['timeformat'],
                edit_text=self.dts.endtime)
            edit = urwid.AttrMap(edit, self.bgs.endtime, 'editcp', )
            edit = urwid.Padding(
                edit, align='left', width=len(self.dts.endtime) + 1, left=1)
            self.widgets.endtime = edit

        columns = urwid.Pile([
            self.checkallday,
            urwid.Columns([(datewidth, self.widgets.startdate), (
                timewidth, self.widgets.starttime)], dividechars=1),
            urwid.Columns(
                [(datewidth, self.widgets.enddate),
                 (timewidth, self.widgets.endtime)],
                dividechars=1)
        ], focus_item=1)
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
            if getattr(self.startdt, 'tzinfo', None) is None:
                tzinfo = self.conf['locale']['default_timezone']
            else:
                tzinfo = self.startdt.tzinfo
            try:
                newstarttime = self._newstarttime
                newstartdatetime = datetime.combine(
                    newstartdatetime, newstarttime)
                newstartdatetime = tzinfo.localize(newstartdatetime)
            except TypeError:
                return None
        return newstartdatetime

    @property
    def _newstartdate(self):
        try:
            self.dts.startdate = \
                self.widgets.startdate. \
                original_widget.original_widget.get_edit_text()

            newstartdate = datetime.strptime(
                self.dts.startdate,
                self.conf['locale']['longdateformat']).date()
            self.bgs.startdate = 'edit'
            return newstartdate
        except ValueError:
            self.bgs.startdate = 'alert'
            return None

    @property
    def _newstarttime(self):
        try:
            self.dts.starttime = \
                self.widgets.starttime. \
                original_widget.original_widget.get_edit_text()

            newstarttime = datetime.strptime(
                self.dts.starttime,
                self.conf['locale']['timeformat']).time()
            self.bgs.startime = 'edit'
            return newstarttime
        except ValueError:
            self.bgs.starttime = 'alert'
            return None

    @property
    def newend(self):
        newenddatetime = self._newenddate
        if not self.checkallday.state:
            if not hasattr(self.enddt, 'tzinfo') or self.enddt.tzinfo is None:
                tzinfo = self.conf['locale']['default_timezone']
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
            self.dts.enddate = self.widgets.enddate. \
                original_widget.original_widget.get_edit_text()

            newenddate = datetime.strptime(
                self.dts.enddate,
                self.conf['locale']['longdateformat']).date()
            self.bgs.enddate = 'edit'
            return newenddate
        except ValueError:
            self.bgs.enddate = 'alert'
            return None

    @property
    def _newendtime(self):
        try:
            self.endtime = self.widgets.endtime. \
                original_widget.original_widget.get_edit_text()

            newendtime = datetime.strptime(
                self.endtime,
                self.conf['locale']['timeformat']).time()
            self.bgs.endtime = 'edit'
            return newendtime
        except ValueError:
            self.bgs.endtime = 'alert'
            return None
