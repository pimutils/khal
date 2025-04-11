# Copyright (c) 2013-2022 khal contributors
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
from locale import LC_ALL, LC_TIME, getlocale, setlocale
from typing import Any, Callable, Literal, Optional, TypedDict, Union

import urwid

from khal.utils import get_month_abbr_len


# Some custom types
class MarkType(TypedDict):
    date: dt.date
    pos: tuple[int, int]
OnPressType = dict[str, Callable[[dt.date, Optional[dt.date]], Optional[str]]]
GetStylesSignature = Callable[[dt.date, bool], Optional[Union[str, tuple[str, str]]]]


setlocale(LC_ALL, '')


def getweeknumber(day: dt.date) -> int:
    """return iso week number for datetime.date object
    :param day: date
    :return: weeknumber
    """
    return dt.date.isocalendar(day)[1]


class DatePart(urwid.Text):

    """used in the Date widget (single digit)"""

    def __init__(self, digit: str) -> None:
        super().__init__(digit)

    @classmethod
    def selectable(cls: type) -> bool:
        return True

    def keypress(self, size: tuple[int], key: str) -> str:
        return key

    def get_cursor_coords(self, size: tuple[int]) -> tuple[int, int]:
        return 1, 0

    def render(self, size: tuple[int], focus: bool=False) -> urwid.Canvas:
        canv = super().render(size, focus)
        if focus:
            canv = urwid.CompositeCanvas(canv)
            canv.cursor = 1, 0
        return canv


class Date(urwid.WidgetWrap):

    """used in the main calendar for dates (a number)"""

    def __init__(self, date: dt.date, get_styles: GetStylesSignature) -> None:
        dstr = str(date.day).rjust(2)
        self.halves = [urwid.AttrMap(DatePart(dstr[:1]), None, None),
                       urwid.AttrMap(DatePart(dstr[1:]), None, None)]
        self.date = date
        self._get_styles = get_styles
        super().__init__(urwid.Columns(self.halves))

    def set_styles(self, styles: Union[None, str, tuple[str, str]]) -> None:
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

    def reset_styles(self, focus: bool=False) -> None:
        self.set_styles(self._get_styles(self.date, focus))

    @property
    def marked(self) -> bool:
        if 'mark' in [self.halves[0].attr_map[None], self.halves[1].attr_map[None]]:
            return True
        else:
            return False

    @classmethod
    def selectable(cls) -> bool:
        return True

    def keypress(self, _: Any, key: str) -> str:
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

    def __init__(self,
                 widget_list,
                 on_date_change: Callable[[dt.date], None],
                 on_press: OnPressType,
                 keybindings: dict[str, list[str]],
                 get_styles: GetStylesSignature,
                 **kwargs) -> None:
        self.on_date_change = on_date_change
        self.on_press = on_press
        self.keybindings = keybindings
        self.get_styles = get_styles
        self._init: bool = True
        super().__init__(widget_list, **kwargs)

    def __repr__(self) -> str:
        return f'<DateCColumns from {self[1].date} to {self[7].date}>'

    def _clear_cursor(self) -> None:
        old_pos: int = self.focus_position
        self.contents[old_pos][0].set_styles(
            self.get_styles(self.contents[old_pos][0].date, False))

    @property
    def focus_position(self) -> int:
        """returns the current focus position"""
        return urwid.Columns.focus_position.fget(self)

    @focus_position.setter
    def focus_position(self, position: int) -> None:
        """calls on_date_change before setting super().focus_position"""
        # do not call when building up the interface, lots of potentially
        # expensive calls made here
        if self._init:
            self._init = False
        else:
            self._clear_cursor()
            self.contents[position][0].set_styles(
                self.get_styles(self.contents[position][0].date, True))
            self.on_date_change(self.contents[position][0].date)
        urwid.Columns.focus_position.fset(self, position)

    def set_focus_date(self, a_date: dt.date) -> None:
        for num, day in enumerate(self.contents[1:8], 1):
            if day[0].date == a_date:
                self.focus_position = num
                return None
        raise ValueError('%s not found in this week' % a_date)

    def get_date_column(self, a_date: dt.date) -> int:
        """return the column `a_date` is in, raises ValueError if `a_date`
           cannot be found
        """
        for num, day in enumerate(self.contents[1:8], 1):
            if day[0].date == a_date:
                return num
        raise ValueError('%s not found in this week' % a_date)

    def keypress(self, size: tuple[int], key: str) -> str:
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
        elif key in self.keybindings['view']:  # TODO make this more generic
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

    def __init__(self, walker: 'CalendarWalker') -> None:
        self._init: bool = True
        self.keybindings = walker.keybindings
        self.on_press = walker.on_press
        self._marked: Optional[MarkType] = None
        self._pos_old: Optional[tuple[int, int]] = None
        self.body: 'CalendarWalker'
        super().__init__(walker)

    @property
    def focus_position(self) -> int:
        return super().focus_position

    @focus_position.setter
    def focus_position(self, position: int) -> None:
        super().set_focus(position)

    def render(self, size: tuple[int], focus: bool=False) -> urwid.Canvas:
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

    def _date(self, row: int, column: int) -> dt.date:
        """return the date at row `row` and  column `column`"""
        return self.body[row].contents[column][0].date

    def _unmark_one(self, row: int, column: int) -> None:
        """remove attribute *mark* from the date at row `row` and column `column`
        returning it to the attributes defined by self._get_color()
        """
        self.body[row].contents[column][0].reset_styles()

    def _mark_one(self, row: int, column: int) -> None:
        """set attribute *mark* on the date at row `row` and column `column`"""
        self.body[row].contents[column][0].set_styles('mark')

    def _mark(self, a_date: Optional[dt.date]=None) -> None:
        """make sure everything between the marked entry and `a_date`
        is visually marked, and nothing else"""

        assert self._marked is not None

        if a_date is None:
            a_date = self.body.focus_date

        def toggle(row: int, column: int) -> None:
            """toggle the mark attribute on the date at row `row` and column
            `column`"""
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

    def _unmark_all(self) -> None:
        """remove attribute *mark* from all dates"""
        if self._marked and self._pos_old:
            start = min(self._marked['pos'][0], self.focus_position, self._pos_old[0])
            end = max(self._marked['pos'][0], self.focus_position, self._pos_old[0]) + 1
            for row in range(start, end):
                for col in range(1, 8):
                    self._unmark_one(row, col)

    def set_focus_date(self, a_day: dt.date) -> None:
        """set focus to the date `a_day`"""
        self.focus.focus.set_styles(self.focus.get_styles(self.body.focus_date, False))
        if self._marked:
            self._unmark_all()
            self._mark(a_day)
        self.body.set_focus_date(a_day)

    def keypress(self, size: bool, key: str) -> Optional[str]:
        if key in self.keybindings['mark'] + ['esc'] and self._marked:
            self._unmark_all()
            self._marked = None
            return None
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
    def __init__(self,
                 on_date_change: Callable[[dt.date], None],
                 on_press: dict[str, Callable[[dt.date, Optional[dt.date]], Optional[str]]],
                 keybindings: dict[str, list[str]],
                 get_styles: GetStylesSignature,
                 firstweekday: int = 0,
                 weeknumbers: Literal['left', 'right', False]=False,
                 monthdisplay: Literal['firstday', 'firstfullweek']='firstday',
                 initial: Optional[dt.date]=None,
                 ) -> None:
        self.firstweekday = firstweekday
        self.weeknumbers = weeknumbers
        self.monthdisplay = monthdisplay
        self.on_date_change = on_date_change
        self.on_press = on_press
        self.keybindings = keybindings
        self.get_styles = get_styles
        self.reset(initial)

    def reset(self, initial: Optional[dt.date]=None) -> None:
        if initial is None:
            initial = dt.date.today()
        weeks = self._construct_month(initial.year, initial.month)
        urwid.SimpleFocusListWalker.__init__(self, weeks)

    def set_focus(self, position: int) -> None:
        """set focus by item number"""
        while position >= len(self) - 1:
            self._autoextend()
        while position <= 0:
            no_additional_weeks = self._autoprepend()
            position += no_additional_weeks
        urwid.SimpleFocusListWalker.set_focus(self, position)

    def days_to_next_already_loaded(self, day: dt.date) -> int:
        """return the number of weeks from the focus to the next week that is already loaded"""
        if len(self) == 0:
            return 0
        elif self.earliest_date <= day <= self.latest_date:
            return 0
        elif day <= self.earliest_date:
            return (self.earliest_date - day).days
        elif self.latest_date <= day:
            return (day - self.latest_date).days
        else:
            raise ValueError("This should not happen")

    @property
    def focus_date(self) -> dt.date:
        """return the date the focus is currently set to"""
        return self[self.focus].focus.date

    def set_focus_date(self, a_day: dt.date) -> None:
        """set the focus to `a_day`"""
        if self.days_to_next_already_loaded(a_day) > 200:   # arbitrary number
            self.reset(a_day)
        row, column = self.get_date_pos(a_day)
        self.set_focus(row)
        self[self.focus].focus_position = (column)

    @property
    def earliest_date(self) -> dt.date:
        """return earliest day that is already loaded into the CalendarWidget"""
        return self[0][1].date

    @property
    def latest_date(self) -> dt.date:
        """return latest day that is already loaded into the CalendarWidget"""
        return self[-1][7].date

    def reset_styles_range(self, min_date: dt.date, max_date: dt.date) -> None:
        """reset styles for all (displayed) dates between min_date and max_date"""
        minr, minc = self.get_date_pos(max(min_date, self.earliest_date))
        maxr, maxc = self.get_date_pos(min(max_date, self.latest_date))
        focus_pos = self.focus, self[self.focus].focus_col

        for row in range(minr, maxr + 1):
            for column in range(1, 8):
                focus = ((row, column) == focus_pos)
                self[row][column].reset_styles(focus)

    def get_date_pos(self, a_day: dt.date) -> tuple[int, int]:
        """get row and column where `a_day` is located"""
        # rough estimate of difference in lines, i.e. full weeks, we might be
        # off by as much as one week though
        week_diff = int((self.focus_date - a_day).days / 7)
        new_focus = self.focus - week_diff
        # in case new_focus is 1 we will later try set the focus to 0 which
        # will lead to an autoprepend which will f*ck up our estimation,
        # therefore better autoprepending anyway, even if it might not be
        # necessary
        while new_focus <= 1:
            self._autoprepend()
            week_diff = int((self.focus_date - a_day).days / 7)
            new_focus = self.focus - week_diff
        for offset in [0, -1, 1]:  # we might be off by a week
            row = new_focus + offset
            try:
                while row >= len(self):
                    self._autoextend()
                column = self[row].get_date_column(a_day)
                return row, column
            except (ValueError, IndexError):
                pass
        # we didn't find the date we were looking for...
        raise ValueError('something is wrong')

    def _autoextend(self) -> None:
        """appends the next month"""
        date_last_month = self[-1][1].date  # a date from the last month
        last_month = date_last_month.month
        last_year = date_last_month.year
        month = last_month % 12 + 1
        year = last_year if not last_month == 12 else last_year + 1
        weeks = self._construct_month(year, month, clean_first_row=True)
        self.extend(weeks)

    def _autoprepend(self) -> int:
        """prepends the previous month

        :returns: number of weeks prepended
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

    def _construct_week(self, week: list[dt.date]) -> DateCColumns:
        """
        constructs a CColumns week from a week of datetime.date objects. Also
        prepends the month name if the first day of the month is included in
        that week.

        :param week: list of datetime.date objects
        :returns: the week as an CColumns object
        """
        if self.monthdisplay == 'firstday' and 1 in (day.day for day in week):
            month_name = calendar.month_abbr[week[-1].month].ljust(4)
            attr = 'monthname'
        elif self.monthdisplay == 'firstfullweek' and week[0].day <= 7:
            month_name = calendar.month_abbr[week[-1].month].ljust(4)
            attr = 'monthname'
        elif self.weeknumbers == 'left':
            month_name = f' {getweeknumber(week[0]):2} '
            attr = 'weeknumber_left'
        else:
            month_name = '    '
            attr = None

        this_week: list[tuple[int, Union[Date, urwid.AttrMap]]]
        this_week = [(get_month_abbr_len(), urwid.AttrMap(urwid.Text(month_name), attr))]
        for _number, day in enumerate(week):
            new_date = Date(day, self.get_styles)
            this_week.append((2, new_date))
            new_date.set_styles(self.get_styles(new_date.date, False))
        if self.weeknumbers == 'right':
            this_week.append((2, urwid.AttrMap(
                urwid.Text(f'{getweeknumber(week[0]):2}'), 'weeknumber_right')))

        week = DateCColumns(this_week,
                            on_date_change=self.on_date_change,
                            on_press=self.on_press,
                            keybindings=self.keybindings,
                            dividechars=1,
                            get_styles=self.get_styles)
        return week

    def _construct_month(self,
                         year: int=dt.date.today().year,
                         month: int=dt.date.today().month,
                         clean_first_row: bool=False,
                         clean_last_row: bool=False,
                         ) -> list[DateCColumns]:
        """construct one month of DateCColumns

        :param year: the year this month is set in
        :param month: the number of the month to be constructed
        :param clean_first_row: if set, makes sure that the first element
           returned is completely in `month` and not partly in the one before
           (which might lead to that line occurring twice
        :param clean_last_row: if set, makes sure that the last element returned
            is completely in `month` and not partly in the one after (which
            might lead to that line occurring twice)
        :returns: list of DateCColumns and the number of the list element which
                  contains today (or None if it isn't in there)
        """

        plain_weeks = calendar.Calendar(self.firstweekday).monthdatescalendar(year, month)
        weeks = []
        for _number, week in enumerate(plain_weeks):
            weeks.append(self._construct_week(week))
        if clean_first_row and weeks[0][1].date.month != weeks[0][7].date.month:
            return weeks[1:]
        elif clean_last_row and weeks[-1][1].date.month != weeks[-1][7].date.month:
            return weeks[:-1]
        else:
            return weeks


class CalendarWidget(urwid.WidgetWrap):
    def __init__(self,
                 on_date_change: Callable[[dt.date], None],
                 keybindings: dict[str, list[str]],
                 on_press: Optional[OnPressType]=None,
                 firstweekday: int=0,
                 weeknumbers: Literal['left', 'right', False]=False,
                 monthdisplay: Literal['firstday', 'firstfullweek']='firstday',
                 get_styles: Optional[GetStylesSignature]=None,
                 initial: Optional[dt.date]=None,
                 ) -> None:
        """A calendar widget that can be used in urwid applications

        :param on_date_change: a function that is called every time the selected
            date is changed with the newly selected date as an argument
        :param keybindings: bind keys to specific functionionality, keys are
            the available commands, values are lists of keys that should be
            bound to those commands. See below for the defaults.
            Available commands:
                'left', 'right', 'up', 'down': move cursor in that direction
                'today': refocus on today
                'mark': toggles selection mode
                'other': toggles between selecting the earlier and the later end
                         of a selection
                'view': returns the key `right` to the widget containing the
                        CalendarWidget
        :param on_press: dictonary of functions that are called when the key is
            pressed and is not already bound to one of the internal functions
            via `keybindings`. These functions must accept two arguments, in
            normal mode the first argument is the currently selected date
            (datetime.date) and the second is `None`. When a date range is
            selected, the first argument is the earlier, the second argument
            is the later date. The function's return values are interpreted as
            pressed keys, which are handed to the widget containing the
            CalendarWidget.
        :param firstweekday: the first day of the week, 0 for Monday, 6 for
        :param weeknumbers: display weeknumbers on the left or right side of
           the calendar.
        :param monthdisplay: display the month name in the row of the 1st of the
           month or in the first row that only contains days of the current month.
        :param get_styles: a function that returns a list of styles for a given date
        :param initial: the date that is selected when the widget is first rendered
        """
        if initial is None:
            self._initial = dt.date.today()
        else:
            self._initial = initial

        if on_press is None:
            on_press = {}

        default_keybindings: dict[str, list[str]] = {
            'left': ['left'], 'down': ['down'], 'right': ['right'], 'up': ['up'],
            'today': ['t'],
            'view': [],
            'mark': ['v'],
            'other': ['%'],
        }

        default_keybindings.update(keybindings)
        calendar.setfirstweekday(firstweekday)

        try:
            mylocale: str = '.'.join(getlocale(LC_TIME))  # type: ignore
        except TypeError:  # language code and encoding may be None
            mylocale = 'C'

        _calendar = calendar.LocaleTextCalendar(firstweekday, mylocale)  # type: ignore
        weekheader = _calendar.formatweekheader(2)
        dnames = weekheader.split(' ')

        def _get_styles(date: dt.date, focus: bool) -> Optional[str]:
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
        cnames = urwid.Columns(
            [(month_names_length, urwid.Text(' ' * month_names_length))] +
            [(2, urwid.AttrMap(urwid.Text(name), 'dayname')) for name in dnames],
            dividechars=1)
        self.walker = CalendarWalker(
            on_date_change=on_date_change,
            on_press=on_press,
            keybindings=default_keybindings,
            firstweekday=firstweekday,
            weeknumbers=weeknumbers,
            monthdisplay=monthdisplay,
            get_styles=get_styles,
            initial=self._initial,
        )
        self.box = CListBox(self.walker)
        frame = urwid.Frame(self.box, header=cnames)
        urwid.WidgetWrap.__init__(self, frame)
        self.set_focus_date(self._initial)

    def focus_today(self) -> None:
        self.set_focus_date(dt.date.today())

    def reset_styles_range(self, min_date: dt.date, max_date: dt.date) -> None:
        self.walker.reset_styles_range(min_date, max_date)

    @classmethod
    def selectable(cls) -> bool:
        return True

    @property
    def focus_date(self) -> dt.date:
        return self.walker.focus_date

    def set_focus_date(self, a_day: dt.date) -> None:
        """set the focus to `a_day`"""
        self.box.set_focus_date(a_day)
