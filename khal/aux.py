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

"""this module contains some helper functions converting strings or list of
strings to date(time) or event objects"""

from .compat import to_unicode

from datetime import time as dtime
from datetime import date, datetime, timedelta
from collections import defaultdict
import random
import string

import icalendar
import pytz

from khal.log import logger
from khal.exceptions import FatalError


def timefstr(dtime_list, timeformat):
    """
    converts a time (as a string) to a datetimeobject

    the date is today

    removes "used" elements of list

    :returns: datetimeobject
    """
    if len(dtime_list) == 0:
        raise ValueError()
    time_start = datetime.strptime(dtime_list[0], timeformat)
    time_start = dtime(*time_start.timetuple()[3:5])
    day_start = date.today()
    dtstart = datetime.combine(day_start, time_start)
    dtime_list.pop(0)
    return dtstart


def datetimefstr(dtime_list, dtformat):
    """
    converts a datetime (as one or several string elements of a list) to
    a datetimeobject

    removes "used" elements of list

    :returns: a datetime
    :rtype: datetime.datetime
    """
    parts = dtformat.count(' ') + 1
    dtstring = ' '.join(dtime_list[0:parts])
    dtstart = datetime.strptime(dtstring, dtformat)
    for _ in range(parts):
        dtime_list.pop(0)
    return dtstart


def weekdaypstr(dayname):
    """converts an (abbreviated) dayname to a number (mon=0, sun=6)

    :param dayname: name of abbreviation of the day
    :type dayname: str
    :return: number of the day in a week
    :rtype: int
    """

    if dayname in ['monday', 'mon']:
        return 0
    if dayname in ['tuesday', 'tue']:
        return 1
    if dayname in ['wednesday', 'wed']:
        return 2
    if dayname in ['thursday', 'thu']:
        return 3
    if dayname in ['friday', 'fri']:
        return 4
    if dayname in ['saturday', 'sat']:
        return 5
    if dayname in ['sunday', 'sun']:
        return 6
    raise ValueError('invalid weekday name `%s`' % dayname)


def calc_day(dayname):
    """converts a relative date's description to a datetime object

    :param dayname: relative day name (like 'today' or 'monday')
    :type dayname: str
    :returns: date
    :rtype: datetime.datetime
    """
    today = datetime.today()
    dayname = dayname.lower()
    if dayname == 'today':
        return today
    if dayname == 'tomorrow':
        return today + timedelta(days=1)

    wday = weekdaypstr(dayname)
    days = (wday - today.weekday()) % 7
    days = 7 if days == 0 else days
    day = today + timedelta(days=days)
    return day


def datefstr_weekday(dtime_list, _):
    """interprets first element of a list as a relative date and removes that
    element

    :param dtime_list: event descrpition in list form
    :type dtime_list: list
    :returns: date
    :rtype: datetime.datetime

    """
    if len(dtime_list) == 0:
        raise ValueError()
    day = calc_day(dtime_list[0])
    dtime_list.pop(0)
    return day


def datetimefstr_weekday(dtime_list, timeformat):
    if len(dtime_list) == 0:
        raise ValueError()
    day = calc_day(dtime_list[0])
    time = timefstr(dtime_list[1:], timeformat)
    dtime_list.pop(0)
    dtime_list.pop(0)  # we need to pop twice as timefstr gets a copy
    dtime = datetime.combine(day, time.time())
    return dtime


def guessdatetimefstr(dtime_list, locale, default_day=datetime.today()):
    """
    :type dtime_list: list
    :type locale: dict
    :type default_day: datetime.datetime
    :rtype: datetime.datetime
    """
    # TODO rename in guessdatetimefstrLIST or something saner altogether
    def timefstr_day(dtime_list, timeformat):
        a_date = timefstr(dtime_list, timeformat)
        a_date = datetime(*(default_day.timetuple()[:3] + a_date.timetuple()[3:5]))
        return a_date

    def datefstr_year(dtime_list, dateformat):
        a_date = datetimefstr(dtime_list, dateformat)
        a_date = datetime(*(default_day.timetuple()[:1] + a_date.timetuple()[1:5]))
        return a_date

    dtstart = None
    for fun, dtformat, all_day in [
            (datefstr_year, locale['datetimeformat'], False),
            (datetimefstr, locale['longdatetimeformat'], False),
            (timefstr_day, locale['timeformat'], False),
            (datetimefstr_weekday, locale['timeformat'], False),
            (datefstr_year, locale['dateformat'], True),
            (datetimefstr, locale['longdateformat'], True),
            (datefstr_weekday, None, True),

    ]:
        try:
            dtstart = fun(dtime_list, dtformat)
            return dtstart, all_day
        except ValueError:
            pass
    raise ValueError()


def generate_random_uid():
    """generate a random uid

    when random isn't broken, getting a random UID from a pool of roughly 10^56
    should be good enough"""
    choice = string.ascii_uppercase + string.digits
    return ''.join([random.choice(choice) for _ in range(36)])


def construct_event(dtime_list, locale,
                    defaulttimelen=60, defaultdatelen=1, encoding='utf-8',
                    description=None, location=None, repeat=None, until=None,
                    _now=datetime.now, **kwargs):
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
    # TODO remove if this survives for some time in the wild without getting any reports
    first_type = type(dtime_list[0])
    try:
        for part in dtime_list:
            assert first_type == type(part)
    except AssertionError:
        logger.error(
            "An internal error occured, please report the below error message "
            "to khal's developers at https://github.com/geier/khal/issues or "
            "via email at khal@lostpackets.de")
        logger.error(u' '.join(['{} ({})'.format(part, type(part)) for part in dtime_list]))

    today = datetime.today()
    try:
        dtstart, all_day = guessdatetimefstr(dtime_list, locale)
    except ValueError:
        logger.fatal("Cannot parse: '{}'\nPlease have a look at "
                     "the documentation.".format(' '.join(dtime_list)))
        raise FatalError()

    try:
        dtend, _ = guessdatetimefstr(dtime_list, locale, dtstart)
    except ValueError:
        if all_day:
            dtend = dtstart + timedelta(days=defaultdatelen - 1)
        else:
            dtend = dtstart + timedelta(minutes=defaulttimelen)

    if all_day:
        dtend += timedelta(days=1)
        # test if dtend's year is this year, but dtstart's year is not
        if dtend.year == today.year and dtstart.year != today.year:
            dtend = datetime(dtstart.year, *dtend.timetuple()[1:6])

        if dtend < dtstart:
            dtend = datetime(dtend.year + 1, *dtend.timetuple()[1:6])

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
            dtstart = pytz.timezone(dtime_list[0]).localize(dtstart)
            dtend = pytz.timezone(dtime_list[0]).localize(dtend)
            dtime_list.pop(0)
        except (pytz.UnknownTimeZoneError, UnicodeDecodeError):
            dtstart = locale['default_timezone'].localize(dtstart)
            dtend = locale['default_timezone'].localize(dtend)

    event = icalendar.Event()
    text = to_unicode(' '.join(dtime_list), encoding)
    if not description or not location:
        summary = text.split(' :: ', 1)[0]
        try:
            description = text.split(' :: ', 1)[1]
        except IndexError:
            pass
    else:
        summary = text

    if description:
        event.add('description', description)
    if location:
        event.add('location', location)
    if repeat and repeat != "none":
        if repeat in ["daily", "weekly", "monthly", "yearly"]:
            rrule_settings = {'freq': repeat}
            if until:
                until_date = None
                for fun, dformat in [(datetimefstr, locale['datetimeformat']),
                                     (datetimefstr, locale['longdatetimeformat']),
                                     (timefstr, locale['timeformat']),
                                     (datetimefstr, locale['dateformat']),
                                     (datetimefstr, locale['longdateformat'])]:
                    try:
                        until_date = fun(until, dformat)
                        break
                    except ValueError:
                        pass
                if until_date is None:
                    logger.fatal("Cannot parse until date: '{}'\nPlease have a look "
                                 "at the documentation.".format(until))
                    raise FatalError()
                rrule_settings['until'] = until_date

            event.add('rrule', rrule_settings)
        else:
            logger.fatal("Invalid value for the repeat option. \
                    Possible values are: daily, weekly, monthly or yearly")
            raise FatalError()

    event.add('dtstart', dtstart)
    event.add('dtend', dtend)
    event.add('dtstamp', _now())
    event.add('summary', summary)
    event.add('uid', generate_random_uid())  # TODO add proper UID
    return event


def new_event(dtstart=None, dtend=None, summary=None, timezone=None,
              _now=datetime.now, allday=False):
    """create a new event

    :param dtstart: starttime of that event
    :type dtstart: datetime
    :param dtend: end time of that event, if this is a *date*, this value is
        interpreted as being the last date the event is scheduled on, i.e.
        the VEVENT DTEND will be *one day later*
    :type dtend: datetime
    :param summary: description of the event, used in the SUMMARY property
    :type summary: unicode
    :param timezone: timezone of the event (start and end)
    :type timezone: pytz.timezone
    :param _now: a function that return now, used for testing
    :param allday: if set to True, we will not transform dtstart and dtend to
        datetime
    ::type allday: bool
    :returns: event
    :rtype: icalendar.Event
    """
    now = datetime.now().timetuple()
    now = datetime(now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour)
    inonehour = now + timedelta(minutes=60)
    if dtstart is None:
        dtstart = inonehour
    elif isinstance(dtstart, date) and not allday:
        time_start = inonehour.time()
        dtstart = datetime.combine(dtstart, time_start)

    if dtend is None:
        dtend = dtstart + timedelta(minutes=60)
    if allday:
        dtend += timedelta(days=1)
    if summary is None:
        summary = ''
    if timezone is not None:
        dtstart = timezone.localize(dtstart)
        dtend = timezone.localize(dtend)
    event = icalendar.Event()
    event.add('dtstart', dtstart)
    event.add('dtend', dtend)
    event.add('dtstamp', _now())
    event.add('summary', summary)
    event.add('uid', generate_random_uid())
    event.add('sequence', 0)
    return event


def split_ics(ics, random_uid=False):
    """split an ics string into several according to VEVENT's UIDs

    and sort the right VTIMEZONEs accordingly
    ignores all other ics components
    :type ics: str
    :param random_uid: assign random uids to all events
    :type random_uid: bool
    :rtype list:
    """
    cal = icalendar.Calendar.from_ical(ics)
    tzs = {item['TZID']: item for item in cal.walk() if item.name == 'VTIMEZONE'}

    events_grouped = defaultdict(list)
    for item in cal.walk():
        if item.name == 'VEVENT':
            events_grouped[item['UID']].append(item)
        else:
            continue
    return [ics_from_list(events, tzs, random_uid) for uid, events in
            sorted(events_grouped.items())]


def ics_from_list(events, tzs, random_uid=False):
    """convert an iterable of icalendar.Events to an icalendar.Calendar

    :params events: list of events all with the same uid
    :type events: list(icalendar.cal.Event)
    :param random_uid: assign random uids to all events
    :type random_uid: bool
    :param tzs: collection of timezones
    :type tzs: dict(icalendar.cal.Vtimzone
    """
    calendar = icalendar.Calendar()
    calendar.add('version', '2.0')
    calendar.add('prodid', '-//CALENDARSERVER.ORG//NONSGML Version 1//EN')

    if random_uid:
        new_uid = generate_random_uid()

    needed_tz, missing_tz = set(), set()
    for sub_event in events:
        if random_uid:
            sub_event['UID'] = new_uid
        # icalendar round-trip converts `TZID=a b` to `TZID="a b"` investigate, file bug XXX
        for prop in ['DTSTART', 'DTEND', 'DUE', 'EXDATE', 'RDATE', 'RECURRENCE-ID', 'DUE']:
            if isinstance(sub_event.get(prop), list):
                items = sub_event.get(prop)
            else:
                items = [sub_event.get(prop)]

            for item in items:
                if not (hasattr(item, 'dt') or hasattr(item, 'dts')):
                    continue
                # if prop is a list, all items have the same parameters
                datetime_ = item.dts[0].dt if hasattr(item, 'dts') else item.dt

                if not hasattr(datetime_, 'tzinfo'):
                    continue

                # check for datetimes' timezones which are not understood by
                # icalendar
                if datetime_.tzinfo is None and 'TZID' in item.params and \
                        item.params['TZID'] not in missing_tz:
                    logger.warn(
                        'Cannot find timezone `{}` in .ics file, using default timezone. '
                        'This can lead to erroneous time shifts'.format(item.params['TZID'])
                    )
                    missing_tz.add(item.params['TZID'])
                elif datetime_.tzinfo != pytz.UTC:
                    needed_tz.add(datetime_.tzinfo)

    for tzid in needed_tz:
        if str(tzid) in tzs:
            calendar.add_component(tzs[str(tzid)])
        else:
            logger.warn(
                'Cannot find timezone `{}` in .ics file, this could be a bug, '
                'please report this issue at http://github.com/pimutils/khal/.'.format(tzid))
    for sub_event in events:
        calendar.add_component(sub_event)
    return calendar.to_ical().decode('utf-8')
