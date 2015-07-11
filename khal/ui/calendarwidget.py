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
from datetime import date

import urwid


def getweeknumber(day):
    """return iso week number for datetime.date object
    :param day: date
    :type day: datetime.date()
    :return: weeknumber
    :rtype: int
    """
    return date.isocalendar(day)[1]


class Date(urwid.Text):

    """used in the main calendar for dates (a number)"""

    def __init__(self, date, on_date_change, on_press, keybindings):
        self.date = date
        self.on_date_change = on_date_change
        self.on_press = on_press
        self.keybindings = keybindings
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
        if key in self.on_press:
            return self.on_press[key](self.date)
        else:
            return key


class DateCColumns(urwid.Columns):

    """container for one week worth of dates
    which are horizontally aligned

    TODO: rename, awful name

    focus can only move away by pressing 'TAB',
    calls 'on_date_change' on every focus change (see below for details)
    """

    def __init__(self, widget_list, on_date_change, on_press, keybindings, today=None, **kwargs):
        self.on_date_change = on_date_change
        self.on_press = on_press
        self.keybindings = keybindings
        self.today = today
        # we need the next two attributes to for attribute resetting when a
        # cell regains focus after having lost it the the events column before
        self._old_attr_map = False
        self._old_pos = 0
        super(DateCColumns, self).__init__(widget_list, focus_column=today,
                                           **kwargs)

    def __repr__(self):
        return '<DateCColumns from {} to {}>'.format(self[1].date, self[7].date)

    def _set_focus_position(self, position):
        """calls on_date_change before calling super()._set_focus_position"""

        self.on_date_change(self.contents[position][0].original_widget.date)
        super(DateCColumns, self)._set_focus_position(position)

    def set_focus_date(self, a_date):
        for num, day in enumerate(self.contents[1:8], 1):
            if day[0].original_widget.date == a_date:
                self._set_focus_position(num)
                return None
        raise ValueError('%s not found in this week' % a_date)

    focus_position = property(
        urwid.Columns._get_focus_position,
        _set_focus_position,
        doc=('Index of child widget in focus. Raises IndexError if read when '
             'CColumns is empty, or when set to an invalid index.')
    )

    def keypress(self, size, key):
        """only leave calendar area on pressing 'tab' or 'enter'"""

        if key in self.keybindings['left']:
            key = 'left'
        elif key in self.keybindings['up']:
            key = 'up'
        elif key in self.keybindings['right']:
            key = 'right'
        elif key in self.keybindings['down']:
            key = 'down'

        old_pos = self.focus_position
        key = super(DateCColumns, self).keypress(size, key)

        # make sure we don't leave the calendar
        if old_pos == 7 and key == 'right':
            self.focus_position = 1
            return 'down'
        elif old_pos == 1 and key == 'left':
            self.focus_position = 7
            return 'up'

        if key in self.keybindings['view']:  # XXX make this more generic
            self._old_attr_map = self.contents[self.focus_position][0].get_attr_map()
            self._old_pos = old_pos
            self.contents[self.focus_position][0].set_attr_map({None: 'today focus'})
            return 'right'
        elif self._old_attr_map:
            self.contents[self._old_pos][0].set_attr_map(self._old_attr_map)
            self._old_attr_map = False
        return key


class CListBox(urwid.ListBox):
    """our custom version of ListBox for containing CalendarWalker

    it should contain a `CalendarWalker` instance which it autoextends on
    rendering, if needed """

    def __init__(self, walker):
        self._init = True
        self.keybindings = walker.keybindings
        super(CListBox, self).__init__(walker)

    def render(self, size, focus=False):
        if self._init:
            while 'bottom' in self.ends_visible(size):
                self.body._autoextend()
            self.set_focus_valign('middle')
            self._init = False

        return super(CListBox, self).render(size, focus)

    def keypress(self, size, key):
        if key in self.keybindings['today']:
            self.body.set_focus(self.body.today)
            week = self.body[self.body.today]
            week.set_focus(week.today)
            self.set_focus_valign(('relative', 10))
        return super(CListBox, self).keypress(size, key)


class CalendarWalker(urwid.SimpleFocusListWalker):

    def __init__(self, on_date_change, on_press, keybindings, firstweekday=0, weeknumbers=False):
        self.firstweekday = firstweekday
        self.weeknumbers = weeknumbers
        self.on_date_change = on_date_change
        self.on_press = on_press
        self.keybindings = keybindings
        weeks, focus_item = self._construct_month()
        self.today = focus_item  # the item number which contains today
        urwid.SimpleFocusListWalker.__init__(self, weeks)
        self.set_focus(focus_item)

    def set_focus(self, position):
        """set focus by item number"""
        while position >= len(self) - 1:
            self._autoextend()
        while position <= 0:
            no_additional_weeks = self._autoprepend()
            self.today += no_additional_weeks
            position += no_additional_weeks
        return urwid.SimpleFocusListWalker.set_focus(self, position)

    @property
    def focus_date(self):
        """return the date the focus is currently set to

        :rtype: datetime.date
        """
        return self[self.focus].focus.original_widget.date

    def set_focus_date(self, a_day):
        """set the focus to `a_day`

        :type: a_day: datetime.date
        """
        # rough estimate of difference in lines, i.e. full weeks, we might be
        # off by as much as one week though
        week_diff = int((self.focus_date - a_day).days / 7)
        new_focus = self.focus - week_diff
        # in case new_focus is 1 we will later try set the focus to 0 which
        # will lead to an autoprepend which will f*ck up our estimation,
        # therefore better autoprepending anyway, even if it might not be
        # necessary
        if new_focus <= 1:
            self.set_focus(new_focus - 1)
            week_diff = int((self.focus_date - a_day).days / 7)
            new_focus = self.focus - week_diff
        for offset in [0, -1, 1]:  # we might be off by a week
            self.set_focus(new_focus + offset)
            try:
                self[self.focus].set_focus_date(a_day)
            except ValueError:
                pass
            else:
                return None
        raise ValueError('something is wrong')

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
                new_date = Date(day, self.on_date_change, self.on_press, self.keybindings)
                this_week.append((2, urwid.AttrMap(new_date, 'today', 'today focus')))
                today = number + 1
            else:
                new_date = Date(day, self.on_date_change, self.on_press, self.keybindings)
                this_week.append((2, urwid.AttrMap(new_date, None, 'reveal focus')))
        if self.weeknumbers == 'right':
            this_week.append((2, urwid.Text('{:2}'.format(getweeknumber(week[0])))))

        week = DateCColumns(this_week,
                            on_date_change=self.on_date_change,
                            on_press=self.on_press,
                            keybindings=self.keybindings,
                            dividechars=1,
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


class CalendarWidget(urwid.WidgetWrap):
    def __init__(self, on_date_change, keybindings, on_press,
                 firstweekday=0, weeknumbers=False):
        """
        on_date_change: a function that is called every time the selected date
                        is changed with the newly selected date as a first (and
                        only argument)
        keybindings: bind keys to specific functions, keys are commands (e.g.
                    movement commands, values are lists of keys that should be
                    bound to those commands. See below for the defaults.
                    Available commands:
                        'left', 'right', 'up', 'down': move cursor in direction
                        'today': refocus on today
        on_press: dict of functions that are called when the key is pressed,
                  getting the currently selected date as an argument. Their
                  return values are interpreted as pressed keys.
        """

        default_keybindings = {
            'left': ['left'], 'down': ['down'], 'right': ['right'], 'up': ['up'],
            'today': ['t'],
            'view': [],

        }
        from collections import defaultdict
        on_press = defaultdict(lambda: lambda x: x, on_press)

        default_keybindings.update(keybindings)
        calendar.setfirstweekday(firstweekday)
        dnames = calendar.weekheader(2).split(' ')
        if weeknumbers == 'right':
            dnames.append('#w')
        dnames = urwid.Columns(
            [(4, urwid.Text('    '))] + [(2, urwid.Text(name)) for name in dnames],
            dividechars=1)
        self.walker = CalendarWalker(
            on_date_change, on_press, default_keybindings, firstweekday, weeknumbers)
        box = CListBox(self.walker)
        frame = urwid.Frame(box, header=dnames)
        urwid.WidgetWrap.__init__(self, frame)

    def focus_today(self):
        self.set_focus(date.today())

    @property
    def focus_date(self):
        return self.walker.focus_date

    def set_focus_date(self, a_day):
        self.walker.set_focus_date(a_day)
