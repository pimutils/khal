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

from datetime import date, datetime, timedelta
from datetime import time as dtime
import random
import string
import time

import icalendar
import pytz


def timefstr(date_list, timeformat):
    """
    converts a time (as a string) to a datetimeobject

    the date is today

    removes "used" elements of list

    :returns: datetimeobject
    """
    time_start = time.strptime(date_list[0], timeformat)
    time_start = dtime(*time_start[3:5])
    day_start = date.today()
    dtstart = datetime.combine(day_start, time_start)
    date_list.pop(0)
    return dtstart


def datetimefstr(date_list, datetimeformat, longdatetimeformat,
                 inferyear=None):
    """
    converts a datetime (as one or several string elements of a list) to
    a datetimeobject

    if no year is given, the current year is used

    removes "used" elements of list

    :param intferyear: year to which should be used if datetimeformat is used
    :type inferyear: int

    :returns: a datetime
    :rtype: datetime.datetime
    """
    try:
        # including year
        parts = longdatetimeformat.count(' ') + 1
        dtstring = ' '.join(date_list[0:parts])
        dtstart = datetime.strptime(dtstring, longdatetimeformat)
    except ValueError:
        # without year
        parts = datetimeformat.count(' ') + 1
        dtstring = ' '.join(date_list[0:parts])
        dtstart = datetime.strptime(dtstring, datetimeformat)
        if dtstart.timetuple()[0] == 1900:
            if inferyear is None:
                dtstart = datetime(date.today().timetuple()[0],
                                   *dtstart.timetuple()[1:5])
            else:
                dtstart = datetime(inferyear,
                                   *dtstart.timetuple()[1:5])
        # if start date lies in the past use next year
        # if dtstart < datetime.today():
        #     dtstart = datetime(dtstart.timetuple()[0] + 1,
        #                        *dtstart.timetuple()[1:6])
    for _ in range(parts):
        date_list.pop(0)
    return dtstart


def datefstr(datestr, dateformat, longdateformat):
    """
    converts a date as a string to datetime.date

    if no year is given, the current year is used

    :returns: a date
    :rtype: datetime.date
    """
    try:
        # including year
        dtstart = datetime.strptime(datestr, longdateformat)
    except ValueError:
        # without year
        try:
            dtstart = datetime.strptime(datestr, dateformat)
            if dtstart.timetuple()[0] == 1900:
                dtstart = datetime(date.today().timetuple()[0],
                                   *dtstart.timetuple()[1:5])
        except ValueError:
            raise InvalidDate(
                '"{}" does not look like a valid date'.format(datestr))
    return dtstart.date()


def generate_random_uid():
    """generate a random uid, when random isn't broken, getting a
    random UID from a pool of roughly 10^56 should be good enough"""
    choice = string.ascii_uppercase + string.digits
    return ''.join([random.choice(choice) for _ in range(36)])


def construct_event(date_list, timeformat, dateformat, longdateformat,
                    datetimeformat, longdatetimeformat, defaulttz,
                    defaulttimelen=60, defaultdatelen=1, encoding='utf-8',
                    _now=datetime.now):
    """takes a list of strings and constructs a vevent from it

    :param encoding: the encoding of your terminal, should be a valid encoding
    :type encoding: str
    :param _now: function that returns now, used for testing

    the parts of the list can be either of these:
        * datetime datetime description
            start and end datetime specified, if no year is given, this year
            is used, if the second datetime has no year, the same year as for
            the first datetime object will be used, unless that would make
            the event end before it begins, in which case the next year is
            used
        * datetime time description
            end date will be same as start date, unless that would make the
            event end before it has started, then the next day is used as
            end date
        * datetime description
            event will last for defaulttime
        * time time description
            event starting today at the first time and ending today at the
            second time, unless that would make the event end before it has
            started, then the next day is used as end date
        * time description
            event starting today at time, lasting for the default length
        * date date description
            all day event starting on the first and ending on the last event
        * date description
            all day event starting at given date and lasting for default length

    datetime should match datetimeformat or longdatetimeformat
    time should match timeformat

    where description is the unused part of the list
    see tests for examples

    """
    today = datetime.today()

    all_day = False

    # looking for start datetime
    try:
        # first two elements are a date and a time
        dtstart = datetimefstr(date_list, datetimeformat, longdatetimeformat)
    except ValueError:
        try:
            # first element is a time
            dtstart = timefstr(date_list, timeformat)
        except ValueError:
            try:
                # first element is a date (and since second isn't a time this
                # is an all-day-event
                dtstart = datetimefstr(date_list, dateformat, longdateformat)
                all_day = True
            except ValueError:
                raise

    # now looking for the end
    if all_day:
        try:
            # second element must be a date, too
            dtend = datetimefstr(date_list, dateformat, longdateformat)
            dtend = dtend + timedelta(days=1)
        except ValueError:
            # if it isn't we expect it to be the summary and use defaultdatelen
            # as event length
            dtend = dtstart + timedelta(days=defaultdatelen)
        # test if dtend's year is this year, but dtstart's year is not
        if dtend.year == today.year and dtstart.year != today.year:
            dtend = datetime(dtstart.year, *dtend.timetuple()[1:6])

        if dtend < dtstart:
            dtend = datetime(dtend.year + 1, *dtend.timetuple()[1:6])

    else:
        try:
            # next element datetime
            dtend = datetimefstr(date_list, datetimeformat, longdatetimeformat,
                                 dtstart.year)
        except ValueError:
            try:
                # next element time only
                dtend = timefstr(date_list, timeformat)
                dtend = datetime(
                    *(dtstart.timetuple()[:3] + dtend.timetuple()[3:5]))
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
            # next element is a valid Olson db timezone string
            dtstart = pytz.timezone(date_list[0]).localize(dtstart)
            dtend = pytz.timezone(date_list[0]).localize(dtend)
            date_list.pop(0)
        except (pytz.UnknownTimeZoneError, UnicodeDecodeError):
            dtstart = defaulttz.localize(dtstart)
            dtend = defaulttz.localize(dtend)

    event = icalendar.Event()
    text = ' '.join(date_list).decode(encoding)
    summary = text.split(' :: ', 1)[0]

    try:
        description = text.split(' :: ', 1)[1]
        event.add('description', description)
    except IndexError:
        pass

    event.add('dtstart', dtstart)
    event.add('dtend', dtend)
    event.add('dtstamp', _now())
    event.add('summary', summary)
    event.add('uid', generate_random_uid())
    return event


def new_event(dtstart=None, dtend=None, summary=None, timezone=None,
              _now=datetime.now):
    """create a new event

    :param dtstart: starttime of that event
    :type dtstart: datetime
    :param dtend: end time of that event
    :type dtend: datetime
    :param summary: description of the event, used in the SUMMARY property
    :type summary: unicode
    :param timezone: timezone of the event (start and end)
    :type timezone: pytz.timezone
    :param _now: a function that return now, used for testing
    :returns: event
    :rtype: icalendar.Event
    """
    now = datetime.now().timetuple()
    now = datetime(now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour)
    inonehour = now + timedelta(minutes=60)
    if dtstart is None:
        dtstart = inonehour
    elif isinstance(dtstart, date):
        time_start = inonehour.time()
        dtstart = datetime.combine(dtstart, time_start)

    if dtend is None:
        dtend = dtstart + timedelta(minutes=60)
    if summary is None:
        summary = 'New Event'
    if timezone is not None:
        dtstart = timezone.localize(dtstart)
        dtend = timezone.localize(dtend)
    event = icalendar.Event()
    event.add('dtstart', dtstart)
    event.add('dtend', dtend)
    event.add('dtstamp', _now())
    event.add('summary', summary)
    event.add('uid', generate_random_uid())
    return event


class InvalidDate(Exception):
    pass
