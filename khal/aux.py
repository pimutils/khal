# Copyright (c) 2013-2016 Christian Geier et al.
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

from calendar import isleap
from datetime import date, datetime, timedelta, time
import random
import string
import re
from time import strptime

import icalendar
import pytz

from khal.log import logger
from khal.exceptions import FatalError


def timefstr(dtime_list, timeformat):
    """converts a time (as a string) to a datetimeobject

    the date is today
    removes "used" elements of list

    :returns: datetimeobject
    """
    if len(dtime_list) == 0:
        raise ValueError()
    time_start = datetime.strptime(dtime_list[0], timeformat)
    time_start = time(*time_start.timetuple()[3:5])
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


def construct_daynames(date_):
    """
    returns weeka list of tuples of datetime objects and datenames

    :param daylist: list of dates
    :type daylist: list(datetime.date)
    :param longdateformat: format in which to print dates
    :param str
    :returns: list of names and dates
    :rtype: list((str, datetime.date))
    """
    if date_ == date.today():
        return 'Today'
    elif date_ == date.today() + timedelta(days=1):
        return 'Tomorrow'
    else:
        return date_.strftime('%A')


def calc_day(dayname):
    """converts a relative date's description to a datetime object

    :param dayname: relative day name (like 'today' or 'monday')
    :type dayname: str
    :returns: date
    :rtype: datetime.datetime
    """
    today = datetime.combine(date.today(), time.min)
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
    this_time = timefstr(dtime_list[1:], timeformat)
    dtime_list.pop(0)
    dtime_list.pop(0)  # we need to pop twice as timefstr gets a copy
    dtime = datetime.combine(day, this_time.time())
    return dtime


def guessdatetimefstr(dtime_list, locale, default_day=None):
    """
    :type dtime_list: list
    :type locale: dict
    :type default_day: datetime.datetime
    :rtype: datetime.datetime
    """
    # if now() is called as default param, mocking with freezegun won't work
    if default_day is None:
        default_day = datetime.now().date()
    # TODO rename in guessdatetimefstrLIST or something saner altogether

    def timefstr_day(dtime_list, timeformat):
        if locale['timeformat'] == '%H:%M' and dtime_list[0] == '24:00':
            a_date = datetime.combine(default_day, time(0))
            dtime_list.pop(0)
        else:
            a_date = timefstr(dtime_list, timeformat)
            a_date = datetime(*(default_day.timetuple()[:3] + a_date.timetuple()[3:5]))
        return a_date

    def datetimefwords(dtime_list, _):
        if len(dtime_list) > 0 and dtime_list[0].lower() == 'now':
            dtime_list.pop(0)
            return datetime.now()
        raise ValueError

    def datefstr_year(dtime_list, dateformat):
        """should be used if a date(time) without year is given

        we cannot use datetimefstr() here, because only time.strptime can
        parse the 29th of Feb. if no year is given

        example: dtime_list = ['17.03.', 'description']
                 dateformat = '%d.%m.'
        or     : dtime_list = ['17.03.', '16:00', 'description']
                 dateformat = '%d.%m. %H:%M'
        """
        parts = dateformat.count(' ') + 1
        dtstring = ' '.join(dtime_list[0:parts])
        dtstart = strptime(dtstring, dateformat)
        if dtstart.tm_mon == 2 and dtstart.tm_mday == 29 and not isleap(default_day.year):
            raise ValueError

        for _ in range(parts):
            dtime_list.pop(0)

        a_date = datetime(*(default_day.timetuple()[:1] + dtstart[1:5]))
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
            (datetimefwords, None, False),

    ]:
        try:
            dtstart = fun(dtime_list, dtformat)
            return dtstart, all_day
        except ValueError:
            pass
    raise ValueError()


def timedelta2str(delta):
    total_seconds = abs(delta).seconds

    seconds = total_seconds % 60
    total_seconds -= seconds
    total_minutes = total_seconds//60
    minutes = total_minutes % 60
    total_minutes -= minutes
    total_hours = total_minutes // 60
    hours = total_hours % 24
    total_hours -= hours
    days = total_hours // 24

    s = []
    if days:
        s.append(str(days) + "d")
    if hours:
        s.append(str(hours) + "h")
    if minutes:
        s.append(str(minutes) + "m")
    if seconds:
        s.append(str(seconds) + "s")

    if delta != abs(delta):
        s = ["-"+part for part in s]

    return ' '.join(s)


def guesstimedeltafstr(delta_string):
    """parses a timedelta from a string

    :param delta_string: string encoding time-delta, e.g. '1h 15m'
    :type delta_string: str
    :rtype: datetime.timedelta
    """

    tups = re.split(r'(-?\d+)', delta_string)
    if not re.match(r'^\s*$', tups[0]):
        raise ValueError('Invalid beginning of timedelta string "%s": "%s"'
                         % (delta_string, tups[0]))
    tups = tups[1:]
    res = timedelta()

    for num, unit in zip(tups[0::2], tups[1::2]):
        try:
            numint = int(num)
        except ValueError:
            raise ValueError('Invalid number in timedelta string "%s": "%s"'
                             % (delta_string, num))

        ulower = unit.lower().strip()
        if ulower == 'd' or ulower == 'day' or ulower == 'days':
            res += timedelta(days=numint)
        elif ulower == 'h' or ulower == 'hour' or ulower == 'hours':
            res += timedelta(hours=numint)
        elif (ulower == 'm' or ulower == 'minute' or ulower == 'minutes' or
              ulower == 'min'):
            res += timedelta(minutes=numint)
        elif (ulower == 's' or ulower == 'second' or ulower == 'seconds' or
              ulower == 'sec'):
            res += timedelta(seconds=numint)
        else:
            raise ValueError('Invalid unit in timedelta string "%s": "%s"'
                             % (delta_string, unit))

    return res


def guessrangefstr(daterange, locale, default_timedelta=None, first_weekday=0,
                   adjust_reasonably=False):
    """parses a range string

    :param daterange: date1 [date2 | timedelta]
    :type daterange: str or list
    :param locale:
    :rtype: (datetime, datetime)

    """

    range_list = daterange
    if isinstance(daterange, str):
        range_list = daterange.split()

    try:
        if default_timedelta is None or len(default_timedelta) == 0:
            default_timedelta = None
        else:
            default_timedelta = guesstimedeltafstr(default_timedelta)
    except ValueError:
        default_timedelta = None

    for i in reversed(range(1, len(range_list) + 1)):
        start = ' '.join(range_list[:i])
        end = ' '.join(range_list[i:])
        allday = False
        try:
            if start is None:
                start = datetime_fillin(end=False)
            elif not isinstance(start, date):
                if start.lower() == 'week':
                    today_weekday = datetime.today().weekday()
                    start = datetime.today() - timedelta(days=(today_weekday - first_weekday))
                    end = start + timedelta(days=7)
                else:
                    split = start.split(" ")
                    start, allday = guessdatetimefstr(split, locale)
                    if len(split) != 0:
                        continue

            if isinstance(end, datetime):
                pass

            elif end is None or len(end) == 0:
                if default_timedelta is not None:
                    end = start + default_timedelta
                else:
                    end = datetime_fillin(day=start)
            else:
                if end.lower() == 'eod':
                    end = datetime_fillin(day=start)
                elif end.lower() == 'week':
                    start -= timedelta(days=(start.weekday() - first_weekday))
                    end = start + timedelta(days=7)
                else:
                    try:
                        delta = guesstimedeltafstr(end)
                        end = start + delta
                    except ValueError:
                        split = end.split(" ")
                        end, end_allday = guessdatetimefstr(split, locale, default_day=start.date())
                        if len(split) != 0:
                            continue
                    end = datetime_fillin(end)

            if adjust_reasonably:
                if allday:
                    end += timedelta(days=1)
                    # test if end's year is this year, but start's year is not
                    today = datetime.today()
                    if end.year == today.year and start.year != today.year:
                        end = datetime(start.year, *end.timetuple()[1:6])

                    if end < start:
                        end = datetime(end.year + 1, *end.timetuple()[1:6])

                if end < start:
                    end = datetime(*start.timetuple()[0:3] +
                                   end.timetuple()[3:5])
                if end < start:
                    end = end + timedelta(days=1)

            return start, end, allday
        except ValueError:
            pass

    return None, None, False


def datetime_fillin(dt=None, end=True, locale=None, day=None):
    """returns a datetime that is filled in (with time etc)

    :param dt:
    :type dt: datetime or date or time if None then day is used
    :param end:
    :type end: boolean set True if time.max should be used (else min)
    :param locale:
    :type locale: if set the time will be in this locale
    :param day:
    :type day: the day to be used if just a time is passed in (else today)
    :rtype: datetime

    """
    if day is None:
        day = datetime.today()

    if isinstance(day, datetime):
        day = day.date()

    if dt is None:
        dt = day

    if isinstance(dt, time) and not isinstance(dt, datetime):
        dt = datetime.combine(day, dt)

    if isinstance(dt, date) and not isinstance(dt, datetime):
        t = time.max if end else time.min
        dt = datetime.combine(dt, t)

    if locale is not None:
        try:
            dt = locale['local_timezone'].localize(dt)
        except ValueError:
            pass

    return dt


def generate_random_uid():
    """generate a random uid

    when random isn't broken, getting a random UID from a pool of roughly 10^56
    should be good enough"""
    choice = string.ascii_uppercase + string.digits
    return ''.join([random.choice(choice) for _ in range(36)])


def rrulefstr(repeat, until, locale):
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
                    until_date = fun(until.split(' '), dformat)
                    break
                except ValueError:
                    pass
            if until_date is None:
                logger.fatal("Cannot parse until date: '{}'\nPlease have a look "
                             "at the documentation.".format(until))
                raise FatalError()
            rrule_settings['until'] = until_date

        return rrule_settings
    else:
        logger.fatal("Invalid value for the repeat option. \
                Possible values are: daily, weekly, monthly or yearly")
        raise FatalError()


def eventinfofstr(info_string, locale, default_timedelta=None,
                  adjust_reasonably=False, localize=False):
    """parses a string of the form [START [END | DELTA]] [SUMMARY] [::
    DESCRIPTION] into a dictionary with keys: dtstart, dtend, timezone, allday,
    summary, description

    :param info_string:
    :type info_string: string fitting the form
    :param locale:
    :type locale: locale
    :param default_timedelta:
    :type default_timedelta: passed on to guessrangefstr
    :param adjust_reasonably:
    :type adjust_reasonably: passed on to guessrangefstr
    :param localize:
    :type localize: boolean controls whether dates are localized in the end
    :rtype: dictionary

    """
    description = None
    if " :: " in info_string:
        info_string, description = info_string.split(' :: ')

    parts = info_string.split(' ')
    summary = None
    start = None
    end = None
    tz = None
    allday = False
    for i in reversed(range(len(parts)+1)):
        start, end, allday = guessrangefstr(' '.join(parts[0:i]), locale, default_timedelta='60m',
                                            adjust_reasonably=adjust_reasonably)
        if start is not None and end is not None:
            try:
                # next element is a valid Olson db timezone string
                tz = pytz.timezone(parts[i])
                i += 1
            except (pytz.UnknownTimeZoneError, UnicodeDecodeError, IndexError):
                tz = None
            summary = ' '.join(parts[i:])
            break
        summary = ' '.join(parts[i:])

    if start is not None and end is not None:
        if tz is None:
            tz = locale['default_timezone']

        if allday:
            start = start.date()
            end = end.date()
        else:
            if localize:
                start = tz.localize(start)
                end = tz.localize(end)

    info = {}
    info["dtstart"] = start
    info["dtend"] = end
    info["summary"] = summary if summary else None
    info["description"] = description
    info["timezone"] = tz if not allday else None
    info["allday"] = allday
    return info


def new_event(locale, dtstart=None, dtend=None, summary=None, timezone=None,
              allday=False, description=None, location=None, categories=None,
              repeat=None, until=None, alarms=None):
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
    :param allday: if set to True, we will not transform dtstart and dtend to
        datetime
    :type allday: bool
    :returns: event
    :rtype: icalendar.Event
    """

    if dtstart is None:
        raise ValueError("no start given")
    if dtend is None:
        raise ValueError("no end given")
    if summary is None:
        raise ValueError("no summary given")

    if not allday and timezone is not None:
        dtstart = timezone.localize(dtstart)
        dtend = timezone.localize(dtend)

    event = icalendar.Event()
    event.add('dtstart', dtstart)
    event.add('dtend', dtend)
    event.add('dtstamp', datetime.now())
    event.add('summary', summary)
    event.add('uid', generate_random_uid())
    # event.add('sequence', 0)

    if description:
        event.add('description', description)
    if location:
        event.add('location', location)
    if categories:
        event.add('categories', categories)
    if repeat and repeat != "none":
        rrule = rrulefstr(repeat, until, locale)
        event.add('rrule', rrule)
    if alarms:
        for alarm in alarms.split(","):
            alarm = alarm.strip()
            alarm_trig = -1 * guesstimedeltafstr(alarm)
            new_alarm = icalendar.Alarm()
            new_alarm.add('ACTION', 'DISPLAY')
            new_alarm.add('TRIGGER', alarm_trig)
            new_alarm.add('DESCRIPTION', description)
            event.add_component(new_alarm)
    return event


def ics_from_list(vevent, random_uid=False):
    """convert an iterable of icalendar.Event to an icalendar.Calendar

    :param random_uid: asign the same random UID to all events
    :type random_uid: bool
    """
    calendar = icalendar.Calendar()
    calendar.add('version', '2.0')
    calendar.add('prodid', '-//CALENDARSERVER.ORG//NONSGML Version 1//EN')
    if random_uid:
        new_uid = icalendar.vText(generate_random_uid())
    for sub_event in vevent:
        if random_uid:
            sub_event['uid'] = new_uid
        calendar.add_component(sub_event)
    return calendar
