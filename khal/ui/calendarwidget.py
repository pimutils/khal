# Copyright (c) 2013-2021 khal contributors
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

"""Contains a re-usable CalendarWidget for urwid.

if anything doesn't work as expected, please open an issue for khal
"""

import calendar
import datetime as dt
from collections import defaultdict
from locale import LC_ALL, LC_TIME, getlocale, setlocale

import urwid
from khal.utils import get_month_abbr_len

setlocale(LC_ALL, '')


def getweeknumber(day):
    """return iso week number for datetime.date object
    :param day: date
    :type day: datetime.date()
    :return: weeknumber
    :rtype: int
    """
    return dt.date.isocalendar(day)[1]


class DatePart(urwid.Text):

    """used in the Date widget (single digit)"""

    def __init__(self, digit):
        super().__init__(digit)

    @classmethod
    def selectable(cls):
        return True

    def keypress(self, _, key):
        return key

    def get_cursor_coords(self, size):
        return 1, 0

    def render(self, size, focus=False):
        canv = super().render(size, focus)
        if focus:
            canv = urwid.CompositeCanvas(canv)
            canv.cursor = 1, 0
        return canv


class Date(urwid.WidgetWrap):

    """used in the main calendar for dates (a number)"""

    def __init__(self, date, get_styles=None):
        dstr = str(date.day).rjust(2)
        self.halves = [urwid.AttrMap(DatePart(dstr[:1]), None, None),
                       urwid.AttrMap(DatePart(dstr[1:]), None, None)]
        self.date = date
        self._get_styles = get_styles
        super().__init__(urwid.Columns(self.halves))

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
            self.halves[0].set_focus_map({None: styles})
            self.halves[1].set_focus_map({None: styles})

    def reset_styles(self, focus=False):
        self.set_styles(self._get_styles(self.date, focus))

    @property
    def marked(self):
        if 'mark' in [self.halves[0].attr_map[None], self.halves[1].attr_map[None]]:
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
    # TODO only call on_date_change when we change our date ourselves,
    # not if it gets changed by an (external) call to set_focus_date()

    def __init__(self, widget_list, on_date_change, on_press, keybindings,
                 get_styles=None, **kwargs):
        self.on_date_change = on_date_change
        self.on_press = on_press
        self.keybindings = keybindings
        self.get_styles = get_styles
        self._init = True
        super().__init__(widget_list, **kwargs)

    def __repr__(self):
        return f'<DateCColumns from {self[1].date} to {self[7].date}>'

    def _clear_cursor(self):
        old_pos = self.focus_position
        self.contents[old_pos][0].set_styles(
            self.get_styles(self.contents[old_pos][0].date, False))

    def _set_focus_position(self, position):
        """calls on_date_change before calling super()._set_focus_position"""
        # do not call when building up the interface, lots of potentially
        # expensive calls made here
        if self._init:
            self._init = False
        else:
            self._clear_cursor()
            self.contents[position][0].set_styles(
                self.get_styles(self.contents[position][0].date, True))
            self.on_date_change(self.contents[position][0].date)
        super()._set_focus_position(position)

    def set_focus_date(self, a_date):
        for num, day in enumerate(self.contents[1:8], 1):
            if day[0].date == a_date:
                self._set_focus_position(num)
                return None
        raise ValueError('%s not found in this week' % a_date)

    def get_date_column(self, a_date):
        """return the column `a_date` is in, raises ValueError if `a_date`
           cannot be found
        """
        for num, day in enumerate(self.contents[1:8], 1):
            if day[0].date == a_date:
                return num
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

        exit_row = False  # set this, if we are leaving the current row
        old_pos = self.focus_position

        key = super().keypress(size, key)

        # make sure we don't leave the calendar
        if old_pos == 7 and key == 'right':
            self.focus_position = 1
            exit_row = True
            key = 'down'
        elif old_pos == 1 and key == 'left':
            self.focus_position = 7
            exit_row = True
            key = 'up'
        elif key in self.keybindings['view']:  # XXX make this more generic
            self.focus_position = old_pos
            key = 'right'
        elif key in ['up', 'down']:
            exit_row = True

        if exit_row:
            self._clear_cursor()

        return key


class CListBox(urwid.ListBox):
    """our custom version of ListBox containing a CalendarWalker instance

    it should contain a `CalendarWalker` instance which it autoextends on
    rendering, if needed """

    def __init__(self, walker):
        self._init = True
        self.keybindings = walker.keybindings
        self.on_press = walker.on_press
        self._marked = False
        self._pos_old = False

        super().__init__(walker)

    def render(self, size, focus=False):
        while 'bottom' in self.ends_visible(size):
            self.body._autoextend()
        if self._init:
            self.set_focus_valign('middle')
            self._init = False

        return super().render(size, focus)

    def mouse_event(self, *args):
        size, event, button, col, row, focus = args

        if event == 'mouse press' and button == 1:
            self.focus.focus.set_styles(
                self.focus.get_styles(self.body.focus_date, False))
        return super().mouse_event(*args)

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

    def _mark(self, a_date=None):
        """make sure everything between the marked entry and `a_date`
        is visually marked, and nothing else"""

        if a_date is None:
            a_date = self.body.focus_date

        def toggle(row, column):
            if self.body[row].contents[column][0].marked:
                self._mark_one(row, column)
            else:
                self._unmark_one(row, column)

        start = min(self._marked['pos'][0], self.focus_position) - 2
        stop = max(self._marked['pos'][0], self.focus_position) + 2
        for row in range(start, stop):
            for col in range(1, 8):
                if a_date > self._marked['date']:
                    if self._marked['date'] <= self._date(row, col) <= a_date:
                        self._mark_one(row, col)
                    else:
                        self._unmark_one(row, col)
                else:
                    if self._marked['date'] >= self._date(row, col) >= a_date:
                        self._mark_one(row, col)
                    else:
                        self._unmark_one(row, col)

            toggle(self.focus_position, self.focus.focus_col)
        self._pos_old = self.focus_position, self.focus.focus_col

    def _unmark_all(self):
        start = min(self._marked['pos'][0], self.focus_position, self._pos_old[0])
        end = max(self._marked['pos'][0], self.focus_position, self._pos_old[0]) + 1
        for row in range(start, end):
            for col in range(1, 8):
                self._unmark_one(row, col)

    def set_focus_date(self, a_day):
        self.focus.focus.set_styles(self.focus.get_styles(self.body.focus_date, False))
        if self._marked:
            self._unmark_all()
            self._mark(a_day)
        self.body.set_focus_date(a_day)

    def keypress(self, size, key):
        if key in self.keybindings['mark'] + ['esc'] and self._marked:
            self._unmark_all()
            self._marked = False
            return
        if key in self.keybindings['mark']:
            self._marked = {'date': self.body.focus_date,
                            'pos': (self.focus_position, self.focus.focus_col)}
        if self._marked and key in self.keybindings['other']:
            row, col = self._marked['pos']
            self._marked = {'date': self.body.focus_date,
                            'pos': (self.focus_position, self.focus.focus_col)}
            self.focus.focus_col = col
            self.focus_position = row

        if key in self.on_press:
            if self._marked:
                start = min(self.body.focus_date, self._marked['date'])
                end = max(self.body.focus_date, self._marked['date'])
            else:
                start = self.body.focus_date
                end = None
            return self.on_press[key](start, end)
        if key in self.keybindings['today'] + ['page down', 'page up']:
            # reset colors of currently focused Date widget
            self.focus.focus.set_styles(self.focus.get_styles(self.body.focus_date, False))
        if key in self.keybindings['today']:
            self.set_focus_date(dt.date.today())
            self.set_focus_valign(('relative', 10))

        key = super().keypress(size, key)
        if self._marked:
            self._mark()
        return key


class CalendarWalker(urwid.SimpleFocusListWalker):
    def __init__(self, on_date_change, on_press, keybindings, firstweekday=0,
                 weeknumbers=False, monthdisplay='firstday', get_styles=None,
                 initial=None):
        if initial is None:
            initial = dt.date.today()
        self.firstweekday = firstweekday
        self.weeknumbers = weeknumbers
        self.monthdisplay = monthdisplay
        self.on_date_change = on_date_change
        self.on_press = on_press
        self.keybindings = keybindings
        self.get_styles = get_styles
        weeks = self._construct_month(initial.year, initial.month)
        urwid.SimpleFocusListWalker.__init__(self, weeks)

    def set_focus(self, position):
        """set focus by item number"""
        while position >= len(self) - 1:
            self._autoextend()
        while position <= 0:
            no_additional_weeks = self._autoprepend()
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
        row, column = self.get_date_pos(a_day)
        self.set_focus(row)
        self[self.focus]._set_focus_position(column)

    @property
    def earliest_date(self):
        """return earliest day that is already loaded into the CalendarWidget"""
        return self[0][1].date

    @property
    def latest_date(self):
        """return latest day that is already loaded into the CalendarWidget"""
        return self[-1][7].date

    def reset_styles_range(self, min_date, max_date):
        """reset styles for all (displayed) dates between min_date and max_date"""
        minr, minc = self.get_date_pos(max(min_date, self.earliest_date))
        maxr, maxc = self.get_date_pos(min(max_date, self.latest_date))
        focus_pos = self.focus, self[self.focus].focus_col

        for row in range(minr, maxr + 1):
            for column in range(1, 8):
                focus = ((row, column) == focus_pos)
                self[row][column].reset_styles(focus)

    def get_date_pos(self, a_day):
        """get row and column where `a_day` is located

        :type: a_day: datetime.date
        :rtype: tuple(int, int)
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
            self._autoprepend()
            week_diff = int((self.focus_date - a_day).days / 7)
            new_focus = self.focus - week_diff
        for offset in [0, -1, 1]:  # we might be off by a week
            row = new_focus + offset
            try:
                if row >= len(self):
                    self._autoextend()
                column = self[row].get_date_column(a_day)
                return row, column
            except ValueError:
                pass
        # we didn't find the date we were looking for...
        raise ValueError('something is wrong')

    def _autoextend(self):
        """appends the next month"""
        date_last_month = self[-1][1].date  # a date from the last month
        last_month = date_last_month.month
        last_year = date_last_month.year
        month = last_month % 12 + 1
        year = last_year if not last_month == 12 else last_year + 1
        weeks = self._construct_month(year, month, clean_first_row=True)
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
        weeks = self._construct_month(year, month, clean_last_row=True)
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
        if self.monthdisplay == 'firstday' and 1 in (day.day for day in week):
            month_name = calendar.month_abbr[week[-1].month].ljust(4)
            attr = 'monthname'
        elif self.monthdisplay == 'firstfullweek' and week[0].day <= 7:
            month_name = calendar.month_abbr[week[-1].month].ljust(4)
            attr = 'monthname'
        elif self.weeknumbers == 'left':
            month_name = ' {:2} '.format(getweeknumber(week[0]))
            attr = 'weeknumber_left'
        else:
            month_name = '    '
            attr = None

        this_week = [(get_month_abbr_len(), urwid.AttrMap(urwid.Text(month_name), attr))]
        for _number, day in enumerate(week):
            new_date = Date(day, self.get_styles)
            this_week.append((2, new_date))
            new_date.set_styles(self.get_styles(new_date.date, False))
        if self.weeknumbers == 'right':
            this_week.append((2, urwid.AttrMap(
                urwid.Text('{:2}'.format(getweeknumber(week[0]))), 'weeknumber_right')))

        week = DateCColumns(this_week,
                            on_date_change=self.on_date_change,
                            on_press=self.on_press,
                            keybindings=self.keybindings,
                            dividechars=1,
                            get_styles=self.get_styles)
        return week

    def _construct_month(self,
                         year=dt.date.today().year,
                         month=dt.date.today().month,
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
        weeks = []
        for _number, week in enumerate(plain_weeks):
            week = self._construct_week(week)
            weeks.append(week)
        if clean_first_row and weeks[0][1].date.month != weeks[0][7].date.month:
            return weeks[1:]
        elif clean_last_row and \
                weeks[-1][1].date.month != weeks[-1][7].date.month:
            return weeks[:-1]
        else:
            return weeks


class CalendarWidget(urwid.WidgetWrap):
    def __init__(self, on_date_change, keybindings, on_press, firstweekday=0,
                 weeknumbers=False, monthdisplay='firstday', get_styles=None, initial=None):
        """
        :param on_date_change: a function that is called every time the selected
            date is changed with the newly selected date as a first (and only
            argument)
        :type on_date_change: function
        :param keybindings: bind keys to specific functionionality, keys are
            the available commands, values are lists of keys that should be
            bound to those commands. See below for the defaults.
            Available commands:
                'left', 'right', 'up', 'down': move cursor in direction
                'today': refocus on today
                'mark': toggles selection mode
        :type keybindings: dict
        :param on_press: dictonary of functions that are called when the key is
            pressed and is not already bound to one of the internal functionions
            via `keybindings`. These functions must accept two arguments, in
            normal mode the first argument is the currently selected date
            (datetime.date) and the second is `None`. When a date range is
            selected, the first argument is the earlier, the second argument
            is the later date. The function's return values are interpreted as
            pressed keys, which are handed to the widget containing the
            CalendarWidget.
        :type on_press: dict
        """
        if initial is None:
            self._initial = dt.date.today()
        else:
            self._initial = initial

        default_keybindings = {
            'left': ['left'], 'down': ['down'], 'right': ['right'], 'up': ['up'],
            'today': ['t'],
            'view': [],
            'mark': ['v'],
        }
        on_press = defaultdict(lambda: lambda x: x, on_press)
        default_keybindings.update(keybindings)
        calendar.setfirstweekday(firstweekday)

        try:
            mylocale = '.'.join(getlocale(LC_TIME))
        except TypeError:  # language code and encoding may be None
            mylocale = 'C'

        _calendar = calendar.LocaleTextCalendar(firstweekday, mylocale)
        weekheader = _calendar.formatweekheader(2)
        dnames = weekheader.split(' ')

        def _get_styles(date, focus):
            if focus:
                if date == dt.date.today():
                    return 'today focus'
                else:
                    return 'reveal focus'
            else:
                if date == dt.date.today():
                    return 'today'
                else:
                    return None
        if get_styles is None:
            get_styles = _get_styles

        if weeknumbers == 'right':
            dnames.append('#w')
        month_names_length = get_month_abbr_len()
        dnames = urwid.Columns(
            [(month_names_length, urwid.Text(' ' * month_names_length))] +
            [(2, urwid.AttrMap(urwid.Text(name), 'dayname')) for name in dnames],
            dividechars=1)
        self.walker = CalendarWalker(
            on_date_change, on_press, default_keybindings, firstweekday,
            weeknumbers, monthdisplay,
            get_styles, initial=self._initial)
        self.box = CListBox(self.walker)
        frame = urwid.Frame(self.box, header=dnames)
        urwid.WidgetWrap.__init__(self, frame)
        self.set_focus_date(self._initial)

    def focus_today(self):
        self.set_focus_date(dt.date.today())

    def reset_styles_range(self, min_date, max_date):
        self.walker.reset_styles_range(min_date, max_date)

    @classmethod
    def selectable(cls):
        return True

    @property
    def focus_date(self):
        return self.walker.focus_date

    def set_focus_date(self, a_day):
        """set the focus to `a_day`

        :type a_day: datetime.date
        """
        self.box.set_focus_date(a_day)
