# Copyright (c) 2013-2017 Christian Geier et al.
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
import datetime
from locale import getlocale, setlocale, LC_ALL, LC_TIME

from click import style

from .terminal import colored
from .utils import get_month_abbr_len


setlocale(LC_ALL, '')


def get_weekheader(firstweekday):
    try:
        mylocale = '.'.join(getlocale(LC_TIME))
    except TypeError:
        mylocale = 'C'

    _calendar = calendar.LocaleTextCalendar(firstweekday, locale=mylocale)
    return _calendar.formatweekheader(2)


def getweeknumber(date):
    """return iso week number for datetime.date object
    :param date: date
    :type date: datetime.date()
    :return: weeknumber
    :rtype: int
    """
    return datetime.date.isocalendar(date)[1]


def get_event_color(event, default_color):
    """Because multi-line lambdas would be un-Pythonic
    """
    if event.color == '':
        return default_color
    return event.color


def str_highlight_day(day, devents, hmethod, default_color, multiple, color, bold_for_light_color):
    """returns a string with day highlighted according to configuration
    """
    dstr = str(day.day).rjust(2)
    if color == '':
        dcolors = list(set(map(lambda x: get_event_color(x, default_color), devents)))
        if len(dcolors) > 1:
            if multiple == '':
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
            if devents[0].color == '':
                dcolor = default_color
            else:
                dcolor = devents[0].color
    else:
        dcolor = color
    if dcolor != '':
        if hmethod == "foreground" or hmethod == "fg":
            return colored(dstr, fg=dcolor, bold_for_light_color=bold_for_light_color)
        else:
            return colored(dstr, bg=dcolor, bold_for_light_color=bold_for_light_color)
    return dstr


def str_week(week, today, collection=None,
             hmethod=None, default_color=None, multiple=None, color=None,
             highlight_event_days=False, locale=None, bold_for_light_color=True):
    """returns a string representing one week,
    if for day == today color is reversed

    :param week: list of 7 datetime.date objects (one week)
    :type day: list()
    :param today: the date of today
    :type today: datetime.date
    :return: string, which if printed on terminal appears to have length 20,
             but may contain ascii escape sequences
    :rtype: str
    """
    strweek = ''
    for day in week:
        if day == today:
            day = style(str(day.day).rjust(2), reverse=True)
        elif highlight_event_days:
            devents = list(collection.get_events_on(day, minimal=True))
            if len(devents) > 0:
                day = str_highlight_day(day, devents, hmethod, default_color,
                                        multiple, color, bold_for_light_color)
            else:
                day = str(day.day).rjust(2)
        else:
            day = str(day.day).rjust(2)
        strweek = strweek + day + ' '
    return strweek


def vertical_month(month=None,
                   year=None,
                   today=None,
                   weeknumber=False,
                   count=3,
                   firstweekday=0,
                   collection=None,
                   hmethod='fg',
                   default_color='',
                   multiple='',
                   color='',
                   highlight_event_days=False,
                   locale=None,
                   bold_for_light_color=True):
    """
    returns a list() of str() of weeks for a vertical arranged calendar

    :param month: first month of the calendar,
                  if non given, current month is assumed
    :type month: int
    :param year: year of the first month included,
                 if non given, current year is assumed
    :type year: int
    :param today: day highlighted, if non is given, current date is assumed
    :type today: datetime.date()
    :param weeknumber: if not False the iso weeknumber will be shown for each
                       week, if weeknumber is 'right' it will be shown in its
                       own column, if it is 'left' it will be shown interleaved
                       with the month names
    :type weeknumber: str/bool
    :returns: calendar strings,  may also include some
              ANSI (color) escape strings
    :rtype: list() of str()
    """
    if month is None:
        month = datetime.date.today().month
    if year is None:
        year = datetime.date.today().year
    if today is None:
        today = datetime.date.today()

    khal = list()
    w_number = '  ' if weeknumber == 'right' else ''
    calendar.setfirstweekday(firstweekday)
    weekheaders = get_weekheader(firstweekday)
    month_abbr_len = get_month_abbr_len()
    khal.append(style(' ' * month_abbr_len + weekheaders + ' ' + w_number, bold=True))
    _calendar = calendar.Calendar(firstweekday)
    for _ in range(count):
        for week in _calendar.monthdatescalendar(year, month):
            new_month = len([day for day in week if day.day == 1])
            strweek = str_week(week, today, collection, hmethod, default_color,
                               multiple, color, highlight_event_days, locale, bold_for_light_color)
            if new_month:
                m_name = style(calendar.month_abbr[week[6].month].ljust(month_abbr_len), bold=True)
            elif weeknumber == 'left':
                m_name = style(str(getweeknumber(week[0])).center(month_abbr_len), bold=True)
            else:
                m_name = ' ' * month_abbr_len
            if weeknumber == 'right':
                w_number = style('{:2}'.format(getweeknumber(week[0])), bold=True)
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
