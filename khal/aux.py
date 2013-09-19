#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2013 Christian Geier & contributors
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
import time
from datetime import date, datetime, timedelta
from datetime import time as dtime
import pytz
import icalendar
import string
import random


def timefstr(date_list, timeformat):
    time_start = time.strptime(date_list[0], timeformat)
    time_start = dtime(*time_start[3:5])
    day_start = date.today()
    dtstart = datetime.combine(day_start, time_start)
    date_list.pop(0)
    return dtstart


def datetimefstr(date_list, datetimeformat):
    dtstring = ' '.join(date_list[0:2])
    dtstart = time.strptime(dtstring, datetimeformat)
    if dtstart[0] == 1900:
        dtstart = datetime(date.today().timetuple()[0],
                           *dtstart[1:5])
    date_list.pop(0)
    date_list.pop(0)
    return dtstart


def datefstr(date_list, dateformat):
    dtstart = datetime.strptime(date_list[0], dateformat)
    if dtstart.year == 1900:
        dtstart = datetime(date.today().year, *dtstart.timetuple()[1:5])
    date_list.pop(0)
    return dtstart


def generate_random_uid():
    """generate a random uid, when random isn't broken, getting a
    random UID from a pool of roughly 10^56 should be good enough"""
    choice = string.ascii_uppercase + string.digits
    return ''.join([random.choice(choice) for _ in range(36)])


def construct_event(date_list, timeformat, dateformat, datetimeformat,
                    defaulttz, defaulttimelen=60, defaultdatelen=1):
    """takes a list of strings and constructs a vevent from it,
    see tests for examples"""
    all_day = False
    try:
        dtstart = timefstr(date_list, timeformat)
    except ValueError:
        try:
            dtstart = datetimefstr(date_list, datetimeformat)
        except ValueError:
            try:
                dtstart = datefstr(date_list, dateformat)
                all_day = True
            except ValueError:
                raise
    if all_day:
        try:
            dtend = datefstr(date_list, dateformat)
            dtend = dtend + timedelta(days=1)
        except ValueError:
            dtend = dtstart + timedelta(days=defaultdatelen)
    else:
        try:
            dtend = timefstr(date_list, timeformat)
        except ValueError:
            try:
                dtend = datetimefstr(date_list, datetimeformat)
            except ValueError:
                dtend = dtstart + timedelta(minutes=defaulttimelen)

    if dtend < dtstart:
        dtend = datetime(*dtstart.timetuple()[0:3] +
                         dtend.timetuple()[3:5])
    if dtend < dtstart:
        dtend = dtend + timedelta(days=1)
    if all_day:
        dtstart = dtstart.date()
        dtend = dtend.date()
    else:
        try:
            dtstart = pytz.timezone(date_list[0]).localize(dtstart)
            dtend = pytz.timezone(date_list[0]).localize(dtend)
            date_list.pop(0)
        except (pytz.UnknownTimeZoneError,  UnicodeDecodeError):
            dtstart = defaulttz.localize(dtstart)
            dtend = defaulttz.localize(dtend)

    event = icalendar.Event()
    event.add('dtstart', dtstart)
    event.add('dtend', dtend)
    event.add('summary', ' '.join(date_list))
    event.add('uid', generate_random_uid())
    return event


RTEXT = '\x1b[7m'  # reverse
NTEXT = '\x1b[0m'  # normal
BTEXT = '\x1b[1m'  # bold
RESET = '\33[0m'


def rstring(string):
    """returns string as reverse color string (ANSI escape codes)

    >>> rstring('test')
    '\\x1b[7mtest\\x1b[0m'
    """
    return RTEXT + string + NTEXT


def bstring(string):
    """returns string as bold string (ANSI escape codes)
    >>> bstring('test')
    '\\x1b[1mtest\\x1b[0m'
    """
    return BTEXT + string + NTEXT


def decode_color(colorstring):
    if colorstring == 'black':
        return '\33[30m'
    elif colorstring == 'dark red':
        return '\33[31m'
    elif colorstring == 'dark green':
        return '\33[32m'
    elif colorstring == 'brown':
        return '\33[33m'
    elif colorstring == 'dark blue':
        return '\33[34m'
    elif colorstring == 'dark magenta':
        return '\33[35m'
    elif colorstring == 'dark cyan':
        return '\33[36m'
    elif colorstring == 'white':
        return '\33[37m'
    elif colorstring == 'light grey':
        return '\33[1;37m'
    elif colorstring == 'dark grey':
        return '\33[1;30m'
    elif colorstring == 'light red':
        return '\33[1;31m'
    elif colorstring == 'light green':
        return '\33[1;32m'
    elif colorstring == 'yellow':
        return '\33[1;33m'
    elif colorstring == 'light blue':
        return '\33[1;34m'
    elif colorstring == 'light magenta':
        return '\33[1;35m'
    elif colorstring == 'light cyan':
        return '\33[1;36m'
    else:
        return ''


def colored(string, color):
    color = decode_color(color)
    return color + string + RESET
