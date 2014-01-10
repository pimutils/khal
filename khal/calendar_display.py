#!/usr/bin/env python2
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

import argparse
import calendar
import datetime
import doctest

from khal.aux import bstring, rstring


def getweeknumber(date):
    """return iso week number for datetime.date object
    >>> getweeknumber(datetime.date(2012,12,12))
    50

    :param date: date
    :type date: datetime.date()
    :return: weeknumber
    :rtype: int
    """
    return datetime.date.isocalendar(date)[1]


def str_week(week, today):
    """returns a string representing one week,
    if for day == today colour is reversed

    :param week: list of 6 datetime.date objects (one week)
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


def print_month(month=datetime.date.today().month,
                year=datetime.date.today().year,
                today=datetime.date.today()):
    """returns a single month calendar, current date highlighted,
       much like cal(1) or python calendar.prmonth
    """
    khal = ''
    mycal = calendar.Calendar(0)  # 0: week starts on monday
    month_name = calendar.month_name[month] + ' ' + str(year)
    khal = month_name.center(20) + '\n'
    khal = khal + bstring('Mo Tu We Th Fr Sa Su') + '\n'
    for mday, wday in mycal.itermonthdays2(year, month):
        if mday == 0:
            mday = ''
        elif mday == today.day and month == today.month and year == today.year:
            mday = rstring(str(mday).rjust(2))
        khal = khal + str(mday).rjust(2) + ' '
        if wday % 7 == 6:
            khal = khal + '\n'
    khal = khal + '\n'
    return khal


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

    >>> vertical_month(month=12, year=2011, today=datetime.date(2011,12,12))
    ['\\x1b[1m    Mo Tu We Th Fr Sa Su\\x1b[0m ', '\\x1b[1mDec \\x1b[0m28 29 30  1  2  3  4 ', '     5  6  7  8  9 10 11 ', '    \\x1b[7m12\\x1b[0m 13 14 15 16 17 18 ', '    19 20 21 22 23 24 25 ', '\\x1b[1mJan \\x1b[0m26 27 28 29 30 31  1 ', '     2  3  4  5  6  7  8 ', '     9 10 11 12 13 14 15 ', '    16 17 18 19 20 21 22 ', '    23 24 25 26 27 28 29 ', '\\x1b[1mFeb \\x1b[0m30 31  1  2  3  4  5 ', '     6  7  8  9 10 11 12 ', '    13 14 15 16 17 18 19 ', '    20 21 22 23 24 25 26 ', '\\x1b[1mMar \\x1b[0m27 28 29  1  2  3  4 ']

    """
    khal = list()
    w_number = '    ' if weeknumber else ''
    calendar.setfirstweekday(firstweekday)
    khal.append(bstring('    ' + calendar.weekheader(2) + ' ' + w_number))
    for _ in range(count):
        for week in calendar.Calendar(firstweekday).monthdatescalendar(year, month):
            new_month = len([day for day in week if day.day == 1])
            strweek = str_week(week, today)
            if new_month:
                m_name = bstring(calendar.month_abbr[week[6].month].ljust(4))
            else:
                m_name = '    '
            w_number = bstring(' ' + str(getweeknumber(week[0]))) if weeknumber else ''
            sweek = m_name + strweek + w_number
            if sweek != khal[-1]:
                khal.append(sweek)
        month = month + 1
        if month > 12:
            month = 1
            year = year + 1
    return khal


def config_parser():
    carg_parser = argparse.ArgumentParser(
        description='displaying calendar like cal(1)')
    carg_parser.add_argument('-v', '--version', action='version',
                             version='0.1')
    carg_parser.add_argument('-w', action='store_true', dest='no_week',
                             default=False, help='do NOT display weeknumber')
    carg_parser.add_argument('-m', action='store', dest='month_number',
                             default=3, type=int,
                             help='number of months to print, default: 3')
    args = vars(carg_parser.parse_args())
    return args

#print(print_month())
#print(print_month(month=12, year=2011, today=datetime.date(2011, 12, 1)))
#print(print_month(month=7, year=2012))
#print(vertical_month(month=12, year=2011))

if __name__ == '__main__':
    doctest.testmod()
    args = config_parser()
    print('\n'.join(vertical_month(weeknumber=(not args['no_week']),
                                   count=args['month_number'])))
