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

from datetime import date, datetime, timedelta
import re

import urwid

from ..compat import unicode_type


def delete_last_word(text, number=1):
    """delete last `number` of words from text"""
    words = re.findall(r"[\w]+|[^\w\s]", text, re.UNICODE)
    for one in range(1, number + 1):
        text = text.rstrip()
        if text == '':
            return text
        text = text[:len(text) - len(words[-one])]
    return text


class CEdit(urwid.Edit):
    def keypress(self, size, key):
        if key == 'ctrl w':
            self._delete_word()
        else:
            return super(CEdit, self).keypress(size, key)

    def _delete_word(self):
        """delete word before cursor"""
        text = unicode_type(self.get_edit_text())
        f_text = delete_last_word(text[:self.edit_pos])
        self.set_edit_text(f_text + text[self.edit_pos:])
        self.set_edit_pos(len(f_text))


class DateTimeWidget(CEdit):

    def __init__(self, dateformat, on_date_change=lambda x: None, **kwargs):
        self.dateformat = dateformat
        self.on_date_change = on_date_change
        super(DateTimeWidget, self).__init__(wrap='any', **kwargs)

    def keypress(self, size, key):
        if key == 'ctrl x':
            self.decrease()
        elif key == 'ctrl a':
            self.increase()
        else:
            if key in ['up', 'down', 'right', 'left', 'tab']:
                try:
                    new_date = self._get_current_dtype()
                except ValueError:
                    pass
                else:
                    self.on_date_change(new_date)
            return super(DateTimeWidget, self).keypress(size, key)


    def increase(self):
        """call to increase the datefield by self.timedelta"""
        self._crease(self.dtype.__add__)

    def decrease(self):
        """call to decrease the datefield by self.timedelta"""
        self._crease(self.dtype.__sub__)

    def _crease(self, fun):
        """common implementation for `self.increase` and `self.decrease`"""
        try:
            new_date = fun(self._get_current_dtype(), self.timedelta)
            self.on_date_change(new_date)
            self.set_edit_text(new_date.strftime(self.dateformat))
        except ValueError:
            pass


class DateWidget(DateTimeWidget):
    dtype = date
    timedelta = timedelta(days=1)

    def _get_current_dtype(self):
        date_str = self.get_edit_text()
        return datetime.strptime(date_str, self.dateformat).date()


class TimeWidget(DateTimeWidget):
    dtype = datetime
    timedelta = timedelta(minutes=15)

    def _get_current_dtype(self):
        date_str = self.get_edit_text()
        return datetime.strptime(date_str, self.dateformat)
