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
from __future__ import print_function

import calendar
import datetime

from .terminal import bstring, rstring


def getweeknumber(date):
    """return iso week number for datetime.date object
    :param date: date
    :type date: datetime.date()
    :return: weeknumber
    :rtype: int
    """
    return datetime.date.isocalendar(date)[1]


def str_week(week, today):
    """returns a string representing one week,
    if for day == today colour is reversed

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
            day = rstring(str(day.day).rjust(2))
        else:
            day = str(day.day).rjust(2)
        strweek = strweek + day + ' '
    return strweek


def vertical_month(month=datetime.date.today().month,
                   year=datetime.date.today().year,
                   today=datetime.date.today(),
                   weeknumber=False,
                   count=3,
                   firstweekday=0):
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
    :returns: calendar strings,  may also include some
              ANSI (color) escape strings
    :rtype: list() of str()
    """

    khal = list()
    w_number = '    ' if weeknumber else ''
    calendar.setfirstweekday(firstweekday)
    _calendar = calendar.Calendar(firstweekday)
    khal.append(bstring('    ' + calendar.weekheader(2) + ' ' + w_number))
    for _ in range(count):
        for week in _calendar.monthdatescalendar(year, month):
            new_month = len([day for day in week if day.day == 1])
            strweek = str_week(week, today)
            if new_month:
                m_name = bstring(calendar.month_abbr[week[6].month].ljust(4))
            else:
                m_name = '    '
            w_number = bstring(
                ' ' + str(getweeknumber(week[0]))) if weeknumber else ''
            sweek = m_name + strweek + w_number
            if sweek != khal[-1]:
                khal.append(sweek)
        month = month + 1
        if month > 12:
            month = 1
            year = year + 1
    return khal
