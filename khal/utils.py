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

"""this module contains some helper functions converting strings or list of
strings to date(time) or event objects"""

from calendar import isleap, month_abbr
from collections import defaultdict
from datetime import date, datetime, timedelta, time
import random
import string
import re
from time import strptime
from textwrap import wrap

import icalendar
import pytz

from khal.log import logger
from khal.exceptions import FatalError
from .khalendar.utils import sanitize


def timefstr(dtime_list, timeformat):
    """converts the first item of a list (a time as a string) to a datetimeobject

    where the date is today and the time is given by a string
    removes "used" elements of list

    :type dtime_list: list(str)
    :type timeformat: str
    :rtype: datetime.datetime
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
    """converts datetime.date into a string description

    either `Today`, `Tomorrow` or name of weekday.
    """
    if date_ == date.today():
        return 'Today'
    elif date_ == date.today() + timedelta(days=1):
        return 'Tomorrow'
    else:
        return date_.strftime('%A')


def relative_timedelta_str(day):
    """Converts the timespan from `day` to today into a human readable string.

    :type day: datetime.date
    :rtype: str
    """
    days = (day - date.today()).days
    if days < 0:
        direction = 'ago'
    else:
        direction = 'from now'
    approx = ''
    if abs(days) < 7:
        unit = 'day'
        count = abs(days)
    elif abs(days) < 365:
        unit = 'week'
        count = int(abs(days) / 7)
        if abs(days) % 7 != 0:
            approx = '~'
    else:
        unit = 'year'
        count = int(abs(days) / 365)
        if abs(days) % 365 != 0:
            approx = '~'
    if count > 1:
        unit += 's'

    return '{approx}{count} {unit} {direction}'.format(
        approx=approx,
        count=count,
        unit=unit,
        direction=direction,
    )


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
    if dayname == 'yesterday':
        return today - timedelta(days=1)

    wday = weekdaypstr(dayname)
    days = (wday - today.weekday()) % 7
    days = 7 if days == 0 else days
    day = today + timedelta(days=days)
    return day


def datefstr_weekday(dtime_list, _):
    """interprets first element of a list as a relative date and removes that
    element

    :param dtime_list: event description in list form
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
    for fun, dtformat, all_day, shortformat in [
            (datefstr_year, locale['datetimeformat'], False, True),
            (datetimefstr, locale['longdatetimeformat'], False, False),
            (timefstr_day, locale['timeformat'], False, False),
            (datetimefstr_weekday, locale['timeformat'], False, False),
            (datefstr_year, locale['dateformat'], True, True),
            (datetimefstr, locale['longdateformat'], True, False),
            (datefstr_weekday, None, True, False),
            (datetimefwords, None, False, False),
    ]:
        if shortformat and '97' in datetime(1997, 10, 11).strftime(dtformat):
            continue
        try:
            dtstart = fun(dtime_list, dtformat)
        except ValueError:
            pass
        else:
            return dtstart, all_day
    raise ValueError()


def timedelta2str(delta):
    # we deliberately ignore any subsecond deltas
    total_seconds = int(abs(delta).total_seconds())

    seconds = total_seconds % 60
    total_seconds -= seconds
    total_minutes = total_seconds // 60
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
        s = ["-" + part for part in s]

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


def guessrangefstr(daterange, locale, adjust_reasonably=False,
                   default_timedelta_date=timedelta(days=1),
                   default_timedelta_datetime=timedelta(hours=1),
                   ):
    """parses a range string

    :param daterange: date1 [date2 | timedelta]
    :type daterange: str or list
    :param locale:
    :returns: start and end of the date(time) range  and if
        this is an all-day time range or not,
        **NOTE**: the end is *exclusive* if this is an allday event
    :rtype: (datetime, datetime, bool)

    """
    range_list = daterange
    if isinstance(daterange, str):
        range_list = daterange.split(' ')

    if range_list == ['week']:
        today_weekday = datetime.today().weekday()
        start = datetime.today() - timedelta(days=(today_weekday - locale['firstweekday']))
        end = start + timedelta(days=8)
        return start, end, True

    for i in reversed(range(1, len(range_list) + 1)):
        start = ' '.join(range_list[:i])
        end = ' '.join(range_list[i:])
        allday = False
        try:
            # figuring out start
            split = start.split(" ")
            start, allday = guessdatetimefstr(split, locale)
            if len(split) != 0:
                continue

            # and end
            if len(end) == 0:
                if allday:
                    end = start + default_timedelta_date
                else:
                    end = start + default_timedelta_datetime
            elif end.lower() == 'eod':
                    end = datetime.combine(start.date(), time.max)
            elif end.lower() == 'week':
                start -= timedelta(days=(start.weekday() - locale['firstweekday']))
                end = start + timedelta(days=8)
            else:
                try:
                    delta = guesstimedeltafstr(end)
                    if allday and delta.total_seconds() % (3600 * 24):
                        # TODO better error class, no logging in here
                        logger.fatal(
                            "Cannot give delta containing anything but whole days for allday events"
                        )
                        raise FatalError()
                    elif delta.total_seconds() == 0:
                        logger.fatal(
                            "Events that last no time are not allowed"
                        )
                        raise FatalError()

                    end = start + delta
                except ValueError:
                    split = end.split(" ")
                    end, end_allday = guessdatetimefstr(split, locale, default_day=start.date())
                    if len(split) != 0:
                        continue
                    if allday:
                        end += timedelta(days=1)

            if adjust_reasonably:
                if allday:
                    # test if end's year is this year, but start's year is not
                    today = datetime.today()
                    if end.year == today.year and start.year != today.year:
                        end = datetime(start.year, *end.timetuple()[1:6])

                    if end < start:
                        end = datetime(end.year + 1, *end.timetuple()[1:6])

                if end < start:
                    end = datetime(*start.timetuple()[0:3] + end.timetuple()[3:5])
                if end < start:
                    end = end + timedelta(days=1)
            return start, end, allday
        except ValueError:
            pass

    raise ValueError('Could not parse `{}` as a daterange'.format(daterange))


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


def eventinfofstr(info_string, locale, adjust_reasonably=False, localize=False):
    """parses a string of the form START [END | DELTA] [TIMEZONE] [SUMMARY] [::
    DESCRIPTION] into a dictionary with keys: dtstart, dtend, timezone, allday,
    summary, description

    :param info_string:
    :type info_string: string fitting the form
    :param locale:
    :type locale: locale
    :param adjust_reasonably:
    :type adjust_reasonably: passed on to guessrangefstr
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
    for i in reversed(range(1, len(parts) + 1)):
        try:
            start, end, allday = guessrangefstr(
                ' '.join(parts[0:i]), locale,
                adjust_reasonably=adjust_reasonably,
            )
        except ValueError:
            continue
        if start is not None and end is not None:
            try:
                # next element is a valid Olson db timezone string
                tz = pytz.timezone(parts[i])
                i += 1
            except (pytz.UnknownTimeZoneError, UnicodeDecodeError, IndexError):
                tz = None
            summary = ' '.join(parts[i:])
            break

    if start is None or end is None:
        raise ValueError('Could not parse `{}`'.format(info_string))

    if tz is None:
        tz = locale['default_timezone']

    if allday:
        start = start.date()
        end = end.date()

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


def split_ics(ics, random_uid=False, default_timezone=None):
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


def ics_from_list(events, tzs, random_uid=False, default_timezone=None):
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
    calendar.add(
        'prodid', '-//PIMUTILS.ORG//NONSGML khal / icalendar //EN'
    )

    if random_uid:
        new_uid = generate_random_uid()

    needed_tz, missing_tz = set(), set()
    for sub_event in events:
        sub_event = sanitize(sub_event, default_timezone=default_timezone)
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
                    logger.warning(
                        'Cannot find timezone `{}` in .ics file, using default timezone. '
                        'This can lead to erroneous time shifts'.format(item.params['TZID'])
                    )
                    missing_tz.add(item.params['TZID'])
                elif datetime_.tzinfo and datetime_.tzinfo != pytz.UTC and \
                        datetime_.tzinfo not in needed_tz:
                    needed_tz.add(datetime_.tzinfo)

    for tzid in needed_tz:
        if str(tzid) in tzs:
            calendar.add_component(tzs[str(tzid)])
        else:
            logger.warning(
                'Cannot find timezone `{}` in .ics file, this could be a bug, '
                'please report this issue at http://github.com/pimutils/khal/.'.format(tzid))
    for sub_event in events:
        calendar.add_component(sub_event)
    return calendar.to_ical().decode('utf-8')


RESET = '\x1b[0m'

ansi_reset = re.compile(r'\x1b\[0m')
ansi_sgr = re.compile(r'\x1b\['
                      '(?!0m)'  # negative lookahead, don't match 0m
                      '([0-9]+;?)+'
                      'm')


def find_last_reset(string):
    for match in re.finditer(ansi_reset, string):
        pass
    try:
        return match.start(), match.end(), match.group(0)
    except UnboundLocalError:
        return -2, -1, ''


def find_last_sgr(string):
    for match in re.finditer(ansi_sgr, string):
        pass
    try:
        return match.start(), match.end(), match.group(0)
    except UnboundLocalError:
        return -2, -1, ''


def find_unmatched_sgr(string):
    reset_pos, _, _ = find_last_reset(string)
    sgr_pos, _, sgr = find_last_sgr(string)
    if sgr_pos > reset_pos:
        return sgr
    else:
        return False


def color_wrap(text, width=70):
    """A variant of wrap that takes SGR codes (somewhat) into account.

    This doesn't actually adjust the length, but makes sure that
    lines that enable some attribues also contain a RESET, and also adds
    that code to the next line
    """
    # TODO we really want to ignore all SGR codes when measuring the width
    lines = wrap(text, width)
    for num, _ in enumerate(lines):
        sgr = find_unmatched_sgr(lines[num])
        if sgr:
            lines[num] += RESET
            if num != len(lines):
                lines[num + 1] = sgr + lines[num + 1]
    return lines


def get_weekday_occurrence(day):
    """Calculate how often this weekday has already occurred in a given month.

    :type day: datetime.date
    :returns: weekday (0=Monday, ..., 6=Sunday), occurrence
    :rtype: tuple(int, int)
    """
    xthday = 1 + (day.day - 1) // 7
    return day.weekday(), xthday


def get_month_abbr_len():
    """Calculate the number of characters we need to display the month
    abbreviated name. It depends on the locale.
    """
    return max(len(month_abbr[i]) for i in range(1, 13)) + 1
