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

import calendar
from datetime import date
from locale import getlocale, setlocale, LC_ALL

import urwid

setlocale(LC_ALL, '')


def getweeknumber(day):
    """return iso week number for datetime.date object
    :param day: date
    :type day: datetime.date()
    :return: weeknumber
    :rtype: int
    """
    return date.isocalendar(day)[1]


class DatePart(urwid.Text):

    """used in the Date widget (single digit)"""

    def __init__(self, digit):
        super(DatePart, self).__init__(digit)

    @classmethod
    def selectable(cls):
        return True

    def keypress(self, _, key):
        return key


class Date(urwid.WidgetWrap):

    """used in the main calendar for dates (a number)"""

    def __init__(self, date, get_styles=None):
        dstr = str(date.day).rjust(2)
        self.halves = [urwid.AttrMap(DatePart(dstr[:1]), None, None),
                       urwid.AttrMap(DatePart(dstr[1:]), None, None)]
        self.date = date
        self._get_styles = get_styles
        super(Date, self).__init__(urwid.Columns(self.halves))

    def set_styles(self, styles):
        """If single string, sets the same style for both halves, if two
        strings, sets different style for each half.
        """
        if type(styles) is tuple:
            self.halves[0].set_attr_map({None: styles[0]})
            self.halves[1].set_attr_map({None: styles[1]})
            self.halves[0].set_focus_map({None: styles[0]})
            self.halves[1].set_focus_map({None: styles[1]})
        else:
            self.halves[0].set_attr_map({None: styles})
            self.halves[1].set_attr_map({None: styles})
            self.halves[1].set_focus_map({None: styles})
            self.halves[0].set_focus_map({None: styles})

    def reset_styles(self):
        self.set_styles(self._get_styles(self.date, False))

    @property
    def marked(self):
        if u'mark' in [self.halves[0].attr_map[None], self.halves[1].attr_map[None]]:
            return True
        else:
            return False

    @classmethod
    def selectable(cls):
        return True

    def keypress(self, _, key):
        return key


class DateCColumns(urwid.Columns):

    """container for one week worth of dates
    which are horizontally aligned

    TODO: rename, awful name

    focus can only move away by pressing 'TAB',
    calls 'on_date_change' on every focus change (see below for details)
    """

    def __init__(self, widget_list, on_date_change, on_press, keybindings,
                 today=None, get_styles=None, **kwargs):
        self.on_date_change = on_date_change
        self.on_press = on_press
        self.keybindings = keybindings
        self.today = today
        self.get_styles = get_styles
        # we need the next two attributes to for attribute resetting when a
        # cell regains focus after having lost it the the events column before
        self._old_attr_map = False
        self._old_pos = 0
        self._init = True
        super(DateCColumns, self).__init__(widget_list, focus_column=today,
                                           **kwargs)

    def __repr__(self):
        return '<DateCColumns from {} to {}>'.format(self[1].date, self[7].date)

    def _set_focus_position(self, position):
        """calls on_date_change before calling super()._set_focus_position"""
        # do not call when building up the interface, lots of potentially
        # expensive calls made here
        if self._init:
            self._init = False
        else:
            self.contents[position][0].set_styles(
                self.get_styles(self.contents[position][0].date, True))
            self.on_date_change(self.contents[position][0].date)
        super(DateCColumns, self)._set_focus_position(position)

    def set_focus_date(self, a_date):
        for num, day in enumerate(self.contents[1:8], 1):
            if day[0].date == a_date:
                self._set_focus_position(num)
                return None
        raise ValueError('%s not found in this week' % a_date)

    focus_position = property(
        urwid.Columns._get_focus_position,
        _set_focus_position,
        doc=(u'Index of child widget in focus. Raises IndexError if read when '
             u'CColumns is empty, or when set to an invalid index.')
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
            self.contents[old_pos][0].set_styles(
                self.get_styles(self.contents[old_pos][0].date, False))
            self.focus_position = 1
            self.contents[self.focus_position][0].set_styles(
                self.get_styles(self.contents[self.focus_position][0].date, False))
            return 'down'
        elif old_pos == 1 and key == 'left':
            self.contents[old_pos][0].set_styles(
                self.get_styles(self.contents[old_pos][0].date, False))
            self.focus_position = 7
            self.contents[self.focus_position][0].set_styles(
                self.get_styles(self.contents[self.focus_position][0].date, False))
            return 'up'

        if key in self.keybindings['view']:  # XXX make this more generic
            self._old_pos = old_pos
            self.contents[old_pos][0].set_styles(
                self.get_styles(self.contents[old_pos][0].date, True))
            return 'right'

        if old_pos != self.focus_position:
            self.contents[old_pos][0].set_styles(
                self.get_styles(self.contents[old_pos][0].date, False))
            self.contents[self.focus_position][0].set_styles(
                self.get_styles(self.contents[self.focus_position][0].date, True))

        if key in ['up', 'down']:
            self.contents[old_pos][0].set_styles(
                self.get_styles(self.contents[old_pos][0].date, False))

        return key


class CListBox(urwid.ListBox):
    """our custom version of ListBox for containing CalendarWalker

    it should contain a `CalendarWalker` instance which it autoextends on
    rendering, if needed """

    def __init__(self, walker):
        self._init = True
        self.keybindings = walker.keybindings
        self.on_press = walker.on_press
        self._marked = False
        self._pos_old = False

        super(CListBox, self).__init__(walker)

    def render(self, size, focus=False):
        if self._init:
            while 'bottom' in self.ends_visible(size):
                self.body._autoextend()
            self.set_focus_valign('middle')
            self._init = False

        return super(CListBox, self).render(size, focus)

    def _date(self, row, column):
        """return the date at row `row` and  column `column`"""
        return self.body[row].contents[column][0].date

    def _unmark_one(self, row, column):
        """remove attribute *mark* from the date at row `row` and column `column`
        returning it to the attributes defined by self._get_color()
        """
        self.body[row].contents[column][0].reset_styles()

    def _mark_one(self, row, column):
        """set attribute *mark* on the date at row `row` and column `column`"""
        self.body[row].contents[column][0].set_styles('mark')

    def _mark(self):
        """make sure everything between the marked entry and the curently
        selected date is visually marked, and nothing else"""
        def toggle(row, column):
            if self.body[row].contents[column][0].marked:
                self._mark_one(row, column)
            else:
                self._unmark_one(row, column)

        start = min(self._marked['pos'][0], self.focus_position) - 2
        stop = max(self._marked['pos'][0], self.focus_position) + 2
        for row in range(start, stop):
            for col in range(1, 8):
                if self.body.focus_date > self._marked['date']:
                    if self._marked['date'] <= self._date(row, col) <= self.body.focus_date:
                        self._mark_one(row, col)
                    else:
                        self._unmark_one(row, col)
                else:
                    if self._marked['date'] >= self._date(row, col) >= self.body.focus_date:
                        self._mark_one(row, col)
                    else:
                        self._unmark_one(row, col)

            toggle(self.focus_position, self.focus.focus_col)
        self._pos_old = self.focus_position, self.focus.focus_col

    def _unmark_all(self):
        start = min(self._marked['pos'][0], self._pos_old[0])
        end = max(self._marked['pos'][0], self._pos_old[0]) + 1
        for row in range(start, end):
            for col in range(1, 8):
                self._unmark_one(row, col)

    def keypress(self, size, key):
        if key in self.keybindings['mark'] + ['esc'] and self._marked:
                self._unmark_all()
                self._marked = False
                return
        if key in self.keybindings['mark']:
            self._marked = {'date': self.body.focus_date,
                            'pos': (self.focus_position, self.focus.focus_col)}

        if key in self.on_press:
            if self._marked:
                start = min(self.body.focus_date, self._marked['date'])
                end = max(self.body.focus_date, self._marked['date'])
            else:
                start = self.body.focus_date
                end = None
            return self.on_press[key](start, end)
        if key in self.keybindings['today']:
            # reset colors of currently focused Date widget
            self.focus.focus.set_styles(
                self.focus.get_styles(self.body.focus_date, False))

            self.body.set_focus(self.body.today)
            week = self.body[self.body.today]
            week.set_focus(week.today)
            self.set_focus_valign(('relative', 10))

        key = super(CListBox, self).keypress(size, key)
        if self._marked:
            self._mark()
        return key


class CalendarWalker(urwid.SimpleFocusListWalker):

    def __init__(self, on_date_change, on_press, keybindings, firstweekday=0,
                 weeknumbers=False, get_styles=None):
        self.firstweekday = firstweekday
        self.weeknumbers = weeknumbers
        self.on_date_change = on_date_change
        self.on_press = on_press
        self.keybindings = keybindings
        self.get_styles = get_styles
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
        return self[self.focus].focus.date

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
            attr = 'monthname'
        elif self.weeknumbers == 'left':
            month_name = ' {:2} '.format(getweeknumber(week[0]))
            attr = 'weeknumber'
        else:
            month_name = '    '
            attr = None

        this_week = [(4, urwid.AttrMap(urwid.Text(month_name), attr))]
        today = None
        for number, day in enumerate(week):
            new_date = Date(day, self.get_styles)
            if day == date.today():
                this_week.append((2, new_date))
                new_date.set_styles(self.get_styles(new_date.date, True))
                today = number + 1
            else:
                this_week.append((2, new_date))
                new_date.set_styles(self.get_styles(new_date.date, False))
        if self.weeknumbers == 'right':
            this_week.append((2, urwid.Text('{:2}'.format(getweeknumber(week[0])))))

        week = DateCColumns(this_week,
                            on_date_change=self.on_date_change,
                            on_press=self.on_press,
                            keybindings=self.keybindings,
                            dividechars=1,
                            today=today,
                            get_styles=self.get_styles)
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
        if clean_first_row and weeks[0][1].date.month != weeks[0][7].date.month:
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
                 firstweekday=0, weeknumbers=False, get_styles=None):
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
                        'mark': toggles selection mode
        on_press: dict of functions that are called when the key is pressed.
            These functions must accept at least two argument. In the normal
            case the first argument is the currently selected date (datetime.date)
            and the second is *None*. When a date range is selected, the first
            argument is the earlier and the second argument is the later date.
            The function's return values are interpreted as pressed keys.
        """

        default_keybindings = {
            'left': ['left'], 'down': ['down'], 'right': ['right'], 'up': ['up'],
            'today': ['t'],
            'view': [],
            'mark': ['v'],
        }
        from collections import defaultdict
        on_press = defaultdict(lambda: lambda x: x, on_press)

        default_keybindings.update(keybindings)
        calendar.setfirstweekday(firstweekday)

        try:
            mylocale = '.'.join(getlocale())
        except TypeError:  # language code and encoding may be None
            mylocale = 'C'

        _calendar = calendar.LocaleTextCalendar(firstweekday, mylocale)
        weekheader = _calendar.formatweekheader(2)
        dnames = weekheader.split(' ')

        def _get_styles(date, focus):
            if focus:
                if date == date.today():
                    return 'today focus'
                else:
                    return 'reveal focus'
            else:
                if date == date.today():
                    return 'today'
                else:
                    return None
        if get_styles is None:
            get_styles = _get_styles

        if weeknumbers == 'right':
            dnames.append('#w')
        dnames = urwid.Columns(
            [(4, urwid.Text('    '))] +
            [(2, urwid.AttrMap(urwid.Text(name), 'dayname')) for name in dnames],
            dividechars=1)
        self.walker = CalendarWalker(
            on_date_change, on_press, default_keybindings, firstweekday, weeknumbers,
            get_styles)
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
