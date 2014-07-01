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

import datetime
from datetime import timedelta

import urwid


class DateTimeWidget(urwid.Edit):

    def __init__(self, dateformat, **kwargs):
        self.dateformat = dateformat
        super(DateTimeWidget, self).__init__(wrap='any', **kwargs)

    def keypress(self, size, key):
        if key == 'ctrl x':
            self.decrease()
        elif key == 'ctrl a':
            self.increase()
        else:
            return super(DateTimeWidget, self).keypress(size, key)

    def _get_dt(self):
        date = self.get_edit_text()
        return datetime.datetime.strptime(date, self.dateformat)

    def increase(self):
        try:
            date = self._get_dt() + self.timedelta
            self.set_edit_text(date.strftime(self.dateformat))
        except ValueError:
            pass

    def decrease(self):
        try:
            date = self._get_dt() - self.timedelta
            self.set_edit_text(date.strftime(self.dateformat))
        except ValueError:
            pass


class DateWidget(DateTimeWidget):
    timedelta = timedelta(days=1)


class TimeWidget(DateTimeWidget):
    timedelta = timedelta(minutes=15)
