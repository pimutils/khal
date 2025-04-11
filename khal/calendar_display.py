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

import calendar
import datetime as dt
from locale import LC_ALL, LC_TIME, getlocale, setlocale
from typing import Optional, Union

from click import style

from .khalendar import CalendarCollection
from .terminal import colored
from .utils import get_month_abbr_len

setlocale(LC_ALL, '')


def get_weekheader(firstweekday: int) -> str:
    try:
        mylocale = '.'.join(getlocale(LC_TIME))  # type: ignore
    except TypeError:
        mylocale = 'C'

    _calendar = calendar.LocaleTextCalendar(firstweekday, locale=mylocale)  # type: ignore
    return _calendar.formatweekheader(2)


def getweeknumber(date: dt.date) -> int:
    """return iso week number for datetime.date object
    :param date: date
    :return: weeknumber
    """
    return dt.date.isocalendar(date)[1]


def get_calendar_color(calendar: str, default_color: str, collection: CalendarCollection) -> str:
    """Because multi-line lambdas would be un-Pythonic
    """
    if collection._calendars[calendar]['color'] == '':
        return default_color
    return collection._calendars[calendar]['color']


def get_color_list(
    calendars: list[str],
    default_color: str,
    collection: CalendarCollection
) -> list[str]:
    """Get the list of possible colors for the day, taking into account priority"""
    dcolors = [
        (
            get_calendar_color(x, default_color, collection),
            collection._calendars[x]["priority"],
        )
        for x in calendars
    ]

    dcolors.sort(key=lambda x: x[1], reverse=True)

    maxPriority = dcolors[0][1]
    return list({x[0] for x in filter(lambda x: x[1] == maxPriority, dcolors)})


def str_highlight_day(
    day: dt.date,
    calendars: list[str],
    hmethod: Optional[str],
    default_color: str,
    multiple: str,
    multiple_on_overflow: bool,
    color: str,
    bold_for_light_color: bool,
    collection: CalendarCollection,
) -> str:
    """returns a string with day highlighted according to configuration
    """
    dstr = str(day.day).rjust(2)
    if color == '':
        dcolors = get_color_list(calendars, default_color, collection)
        if len(dcolors) > 1:
            if multiple == '' or (multiple_on_overflow and len(dcolors) == 2):
                if hmethod == "foreground" or hmethod == "fg":
                    return colored(dstr[:1], fg=dcolors[0],
                                   bold_for_light_color=bold_for_light_color) + \
                        colored(dstr[1:], fg=dcolors[1], bold_for_light_color=bold_for_light_color)
                else:
                    return colored(dstr[:1], bg=dcolors[0],
                                   bold_for_light_color=bold_for_light_color) + \
                        colored(dstr[1:], bg=dcolors[1], bold_for_light_color=bold_for_light_color)
            else:
                dcolor = multiple
        else:
            dcolor = dcolors[0] or default_color
    else:
        dcolor = color
    if dcolor != '':
        if hmethod == "foreground" or hmethod == "fg":
            return colored(dstr, fg=dcolor, bold_for_light_color=bold_for_light_color)
        else:
            return colored(dstr, bg=dcolor, bold_for_light_color=bold_for_light_color)
    return dstr


def str_week(
    week: list[dt.date],
    today: dt.date,
    collection: Optional[CalendarCollection]=None,
    hmethod: Optional[str]=None,
    default_color: str='',
    multiple: str='',
    multiple_on_overflow: bool=False,
    color: str='',
    highlight_event_days: bool=False,
    locale=None,
    bold_for_light_color: bool=True,
) -> str:
    """returns a string representing one week,
    if for day == today color is reversed

    :param week: list of 7 datetime.date objects (one week)
    :param today: the date of today
    :return: string, which if printed on terminal appears to have length 20,
             but may contain ascii escape sequences
    """
    strweek = ''
    if highlight_event_days and collection is None:
        raise ValueError(
            'if `highlight_event_days` is True, `collection` must be a CalendarCollection'
        )
    for day in week:
        if day == today:
            day_str = style(str(day.day).rjust(2), reverse=True)
        elif highlight_event_days:
            assert collection is not None
            devents = list(collection.get_calendars_on(day))
            if len(devents) > 0:
                day_str = str_highlight_day(
                    day, devents, hmethod, default_color, multiple,
                    multiple_on_overflow, color, bold_for_light_color,
                    collection,
                )
            else:
                day_str = str(day.day).rjust(2)
        else:
            day_str = str(day.day).rjust(2)
        strweek = strweek + day_str + ' '
    return strweek


def vertical_month(month: Optional[int]=None,
                   year: Optional[int]=None,
                   today: Optional[dt.date]=None,
                   weeknumber: Union[bool, str]=False,
                   count: int=3,
                   firstweekday: int=0,
                   monthdisplay: str='firstday',
                   collection=None,
                   hmethod: str='fg',
                   default_color: str='',
                   multiple: str='',
                   multiple_on_overflow: bool=False,
                   color: str='',
                   highlight_event_days: bool=False,
                   locale=None,
                   bold_for_light_color: bool=True,
                   ) -> list[str]:
    """
    returns a list() of str() of weeks for a vertical arranged calendar

    :param month: first month of the calendar,
                  if non given, current month is assumed
    :param year: year of the first month included,
                 if non given, current year is assumed
    :param today: day highlighted, if non is given, current date is assumed
    :param weeknumber: if not False the iso weeknumber will be shown for each
                       week, if weeknumber is 'right' it will be shown in its
                       own column, if it is 'left' it will be shown interleaved
                       with the month names
    :returns: calendar strings,  may also include some
              ANSI (color) escape strings
    """
    if month is None:
        month = dt.date.today().month
    if year is None:
        year = dt.date.today().year
    if today is None:
        today = dt.date.today()

    khal = []
    w_number = '  ' if weeknumber == 'right' else ''
    calendar.setfirstweekday(firstweekday)
    weekheaders = get_weekheader(firstweekday)
    month_abbr_len = get_month_abbr_len()
    khal.append(style(' ' * month_abbr_len + weekheaders + ' ' + w_number, bold=True))
    _calendar = calendar.Calendar(firstweekday)
    for _ in range(count):
        for week in _calendar.monthdatescalendar(year, month):
            if monthdisplay == 'firstday':
                new_month = len([day for day in week if day.day == 1])
            else:
                new_month = len(week if week[0].day <= 7 else [])
            strweek = str_week(week, today, collection, hmethod, default_color,
                               multiple, multiple_on_overflow, color, highlight_event_days, locale,
                               bold_for_light_color)
            if new_month:
                m_name = style(calendar.month_abbr[week[6].month].ljust(month_abbr_len), bold=True)
            elif weeknumber == 'left':
                m_name = style(str(getweeknumber(week[0])).center(month_abbr_len), bold=True)
            else:
                m_name = ' ' * month_abbr_len
            if weeknumber == 'right':
                w_number = style(f'{getweeknumber(week[0]):2}', bold=True)
            else:
                w_number = ''

            sweek = m_name + strweek + w_number
            if sweek != khal[-1]:
                khal.append(sweek)
        month = month + 1
        if month > 12:
            month = 1
            year = year + 1
    return khal
