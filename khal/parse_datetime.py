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

"""this module contains some helper functions converting strings or list of
strings to date(time) or event objects"""

import datetime as dt
import logging
import re
from calendar import isleap
from time import strptime
from typing import Any, Callable, Optional, Union

import pytz

from khal.exceptions import DateTimeParseError, FatalError

from .custom_types import LocaleConfiguration, RRuleMapType

logger = logging.getLogger('khal')


def timefstr(dtime_list: list[str], timeformat: str) -> dt.datetime:
    """converts the first item of a list (a time as a string) to a datetimeobject

    where the date is today and the time is given by a string
    removes "used" elements of list.
    """
    if len(dtime_list) == 0:
        raise ValueError()
    datetime_start = dt.datetime.strptime(dtime_list[0], timeformat)
    time_start = dt.time(*datetime_start.timetuple()[3:5])
    day_start = dt.date.today()
    dtstart = dt.datetime.combine(day_start, time_start)
    dtime_list.pop(0)
    return dtstart


def datetimefstr(
    dtime_list: list[str],
    dateformat: str,
    default_day: Optional[dt.date]=None,
    infer_year: bool=True,
    in_future: bool=True,
) -> dt.datetime:
    """converts a datetime (as one or several string elements of a list) to
    a datetimeobject, if infer_year is True, use the `default_day`'s year as
    the year of the return datetimeobject,

    removes "used" elements of list

    example: dtime_list = ['17.03.', 'description']
             dateformat = '%d.%m.'
    or     : dtime_list = ['17.03.', '16:00', 'description']
             dateformat = '%d.%m. %H:%M'
    """
    # if now() is called as default param, mocking with freezegun won't work
    now = dt.datetime.now()
    if default_day is None:
        default_day = now.date()
    parts = dateformat.count(' ') + 1
    dtstring = ' '.join(dtime_list[0:parts])
    # only time.strptime can parse the 29th of Feb. if no year is given
    dtstart_struct = strptime(dtstring, dateformat)
    if infer_year and dtstart_struct.tm_mon == 2 and dtstart_struct.tm_mday == 29 and \
            not isleap(default_day.year):
        raise ValueError

    for _ in range(parts):
        item = dtime_list.pop(0)
        if ' ' in item:
            logger.warn('detected a space in datetime specification, this can lead to errors.')
            logger.warn('Make sure not to quote your datetime specification.')

    if infer_year:
        dtstart = dt.datetime(*(default_day.timetuple()[:1] + dtstart_struct[1:5]))
        if in_future and dtstart < now:
            dtstart = dtstart.replace(year=dtstart.year + 1)
        if dtstart.date() < default_day:
            dtstart = dtstart.replace(year=default_day.year + 1)
        return dtstart
    else:
        return dt.datetime(*dtstart_struct[:5])


def weekdaypstr(dayname: str) -> int:
    """converts an (abbreviated) dayname to a number (mon=0, sun=6)

    :param dayname: name of abbreviation of the day
    :return: number of the day in a week
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


def construct_daynames(date_: dt.date) -> str:
    """converts datetime.date into a string description

    either `Today`, `Tomorrow` or name of weekday.
    """
    if date_ == dt.date.today():
        return 'Today'
    elif date_ == dt.date.today() + dt.timedelta(days=1):
        return 'Tomorrow'
    else:
        return date_.strftime('%A')


def calc_day(dayname: str) -> dt.datetime:
    """converts a relative date's description to a datetime object

    :param dayname: relative day name (like 'today' or 'monday')
    :returns: date
    """
    today = dt.datetime.combine(dt.date.today(), dt.time.min)
    dayname = dayname.lower()
    if dayname == 'today':
        return today
    if dayname == 'tomorrow':
        return today + dt.timedelta(days=1)
    if dayname == 'yesterday':
        return today - dt.timedelta(days=1)

    wday = weekdaypstr(dayname)
    days = (wday - today.weekday()) % 7
    days = 7 if days == 0 else days
    day = today + dt.timedelta(days=days)
    return day


def datefstr_weekday(dtime_list: list[str], timeformat: str, infer_year: bool) -> dt.datetime:
    """interprets first element of a list as a relative date and removes that
    element

    :param dtime_list: event description in list form
    :param timeformat: only here for compat reasons (having the same function signature)

    :returns: date
    """
    if len(dtime_list) == 0:
        raise ValueError()
    day = calc_day(dtime_list[0])
    dtime_list.pop(0)
    return day


def datetimefstr_weekday(dtime_list: list[str], timeformat: str, infer_year: bool) -> dt.datetime:
    """
    :param infer_year: only here for compat reasons (having the same function signature)
    """
    if len(dtime_list) == 0:
        raise ValueError()
    day = calc_day(dtime_list[0])
    this_time = timefstr(dtime_list[1:], timeformat)
    dtime_list.pop(0)
    dtime_list.pop(0)  # we need to pop twice as timefstr gets a copy
    dtime = dt.datetime.combine(day, this_time.time())
    return dtime


def guessdatetimefstr(
    dtime_list: list[str],
    locale: LocaleConfiguration,
    default_day: Optional[dt.date]=None,
    in_future=True,
) -> tuple[dt.datetime, bool]:
    """
    :param in_future: if set, shortdate(time) events will be set in the future
    """
    # if now() is called as default param, mocking with freezegun won't work
    day = default_day or dt.datetime.now().date()
    # TODO rename in guessdatetimefstrLIST or something saner altogether

    def timefstr_day(dtime_list: list[str], timeformat: str, infer_year: bool) -> dt.datetime:
        if locale['timeformat'] == '%H:%M' and dtime_list[0] == '24:00':
            a_date = dt.datetime.combine(day, dt.time(0))
            dtime_list.pop(0)
        else:
            a_date = timefstr(dtime_list, timeformat)
            a_date = dt.datetime(*(day.timetuple()[:3] + a_date.timetuple()[3:5]))
        return a_date

    def datetimefwords(dtime_list: list[str], _: str, infer_year: bool) -> dt.datetime:
        if len(dtime_list) > 0 and dtime_list[0].lower() == 'now':
            dtime_list.pop(0)
            return dt.datetime.now()
        raise ValueError

    def datefstr_year(dtime_list: list[str], dtformat: str, infer_year: bool) -> dt.datetime:
        return datetimefstr(dtime_list, dtformat, day, infer_year, in_future)

    dtstart = None
    fun: Callable[[list[str], str, bool], dt.datetime]
    dtformat: str
    all_day: bool
    infer_year: bool
    for fun, dtformat, all_day, infer_year in [
            (datefstr_year, locale['datetimeformat'], False, True),
            (datefstr_year, locale['longdatetimeformat'], False, False),
            (timefstr_day, locale['timeformat'], False, False),
            (datetimefstr_weekday, locale['timeformat'], False, False),
            (datefstr_year, locale['dateformat'], True, True),
            (datefstr_year, locale['longdateformat'], True, False),
            (datefstr_weekday, '', True, False),
            (datetimefwords, '', False, False),
    ]:
        # if a `short` format contains a year, treat it as a `long` format
        if infer_year and '97' in dt.datetime(1997, 10, 11).strftime(dtformat):
            infer_year = False
        try:
            dtstart = fun(dtime_list, dtformat, infer_year=infer_year)
        except (ValueError, DateTimeParseError):
            pass
        else:
            return dtstart, all_day
    raise DateTimeParseError(
        f"Could not parse \"{dtime_list}\".\nPlease check your configuration "
        "or run `khal printformats` to see if this does match your configured "
        "[long](date|time|datetime)format.\nIf you suspect a bug, please "
        "file an issue at https://github.com/pimutils/khal/issues/ "
    )


def timedelta2str(delta: dt.timedelta) -> str:
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


def guesstimedeltafstr(delta_string: str) -> dt.timedelta:
    """parses a timedelta from a string

    :param delta_string: string encoding time-delta, e.g. '1h 15m'
    """

    tups = re.split(r'(-?\+?\d+)', delta_string)
    if not re.match(r'^\s*$', tups[0]):
        raise ValueError(f'Invalid beginning of timedelta string "{delta_string}": "{tups[0]}"')
    tups = tups[1:]
    res = dt.timedelta()

    for num, unit in zip(tups[0::2], tups[1::2]):
        try:
            if num[0] == '+':
                num = num[1:]
            numint = int(num)
        except ValueError:
            raise DateTimeParseError(
                f'Invalid number in timedelta string "{delta_string}": "{num}"')

        ulower = unit.lower().strip()
        if ulower == 'd' or ulower == 'day' or ulower == 'days':
            res += dt.timedelta(days=numint)
        elif ulower == 'h' or ulower == 'hour' or ulower == 'hours':
            res += dt.timedelta(hours=numint)
        elif (ulower == 'm' or ulower == 'minute' or ulower == 'minutes' or
              ulower == 'min'):
            res += dt.timedelta(minutes=numint)
        elif (ulower == 's' or ulower == 'second' or ulower == 'seconds' or
              ulower == 'sec'):
            res += dt.timedelta(seconds=numint)
        else:
            raise ValueError(f'Invalid unit in timedelta string "{delta_string}": "{unit}"')

    return res


def guessrangefstr(daterange: Union[str, list[str]],
                   locale: LocaleConfiguration,
                   default_timedelta_date: dt.timedelta=dt.timedelta(days=1),
                   default_timedelta_datetime: dt.timedelta=dt.timedelta(hours=1),
                   adjust_reasonably: bool=False,
                   ) -> tuple[dt.datetime, dt.datetime, bool]:
    """parses a range string

    :param daterange: date1 [date2 | timedelta]
    :param locale:
    :returns: start and end of the date(time) range  and if
        this is an all-day time range or not,
        **NOTE**: the end is *exclusive* if this is an allday event
    """
    range_list = daterange
    if isinstance(daterange, str):
        range_list = daterange.split(' ')
        assert isinstance(range_list, list)

    if range_list == ['week']:
        today_weekday = dt.datetime.today().weekday()
        startdt = dt.datetime.today() - dt.timedelta(days=(today_weekday - locale['firstweekday']))
        enddt = startdt + dt.timedelta(days=8)
        return startdt, enddt, True

    for i in reversed(range(1, len(range_list) + 1)):
        startstr = ' '.join(range_list[:i])
        endstr = ' '.join(range_list[i:])
        allday = False
        try:
            # figuring out start
            split = startstr.split(" ")
            start, allday = guessdatetimefstr(split, locale)
            if len(split) != 0:
                continue

            # and end
            if len(endstr) == 0:
                if allday:
                    end = start + default_timedelta_date
                else:
                    end = start + default_timedelta_datetime
            elif endstr.lower() == 'eod':
                end = dt.datetime.combine(start.date(), dt.time.max)
            elif endstr.lower() == 'week':
                start -= dt.timedelta(days=(start.weekday() - locale['firstweekday']))
                end = start + dt.timedelta(days=8)
            else:
                try:
                    delta = guesstimedeltafstr(endstr)
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
                except (ValueError, DateTimeParseError):
                    split = endstr.split(" ")
                    end, end_allday = guessdatetimefstr(
                        split, locale, default_day=start.date(), in_future=False)
                    if len(split) != 0:
                        continue
                    if allday:
                        end += dt.timedelta(days=1)

            if adjust_reasonably:
                if allday:
                    # test if end's year is this year, but start's year is not
                    today = dt.datetime.today()
                    if end.year == today.year and start.year != today.year:
                        end = dt.datetime(start.year, *end.timetuple()[1:6])

                    if end < start:
                        end = dt.datetime(end.year + 1, *end.timetuple()[1:6])

                if end < start:
                    end = dt.datetime(*start.timetuple()[0:3] + end.timetuple()[3:5])
                if end < start:
                    end = end + dt.timedelta(days=1)
            return start, end, allday
        except (ValueError, DateTimeParseError):
            pass

    raise DateTimeParseError(
        f"Could not parse \"{daterange}\".\nPlease check your configuration or "
        "run `khal printformats` to see if this does match your configured "
        "[long](date|time|datetime)format.\nIf you suspect a bug, please "
        "file an issue at https://github.com/pimutils/khal/issues/ "
    )


def rrulefstr(repeat: str,
              until: str,
              locale: LocaleConfiguration,
              timezone: Optional[dt.tzinfo],
              ) -> RRuleMapType:
    if repeat in ["daily", "weekly", "monthly", "yearly"]:
        rrule_settings: RRuleMapType = {'freq': repeat}
        if until:
            until_dt, _ = guessdatetimefstr(until.split(' '), locale)
            if timezone:
                rrule_settings['until'] = until_dt.\
                    replace(tzinfo=timezone).\
                    astimezone(pytz.UTC)
            else:
                rrule_settings['until'] = until_dt
        return rrule_settings
    else:
        logger.fatal("Invalid value for the repeat option. \
                Possible values are: daily, weekly, monthly or yearly")
        raise FatalError()


def eventinfofstr(info_string: str,
                  locale: LocaleConfiguration,
                  default_event_duration: dt.timedelta,
                  default_dayevent_duration: dt.timedelta,
                  adjust_reasonably: bool=False,
                  ) -> dict[str, Any]:
    """parses a string of the form START [END | DELTA] [TIMEZONE] [SUMMARY] [::
    DESCRIPTION] into a dictionary with keys: dtstart, dtend, timezone, allday,
    summary, description
    """
    description = None
    if " :: " in info_string:
        info_string, description = info_string.split(' :: ')

    parts = info_string.split(' ')
    summary = None
    start: Optional[Union[dt.datetime, dt.date]] = None
    end: Optional[Union[dt.datetime, dt.date]] = None
    tz: Optional[pytz.BaseTzInfo] = None
    allday: bool = False
    for i in reversed(range(1, len(parts) + 1)):
        try:
            start, end, allday = guessrangefstr(
                ' '.join(parts[0:i]), locale,
                default_timedelta_datetime=default_event_duration,
                default_timedelta_date=default_dayevent_duration,
                adjust_reasonably=adjust_reasonably,
            )
        except (ValueError, DateTimeParseError):
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
        raise DateTimeParseError(
            f"Could not parse \"{info_string}\".\nPlease check your "
            "configuration or run `khal printformats` to see if this does "
            "match your configured [long](date|time|datetime)format.\nIf you "
            "suspect a bug, please file an issue at "
            "https://github.com/pimutils/khal/issues/ "
        )

    if tz is None:
        tz = locale['default_timezone']

    if allday:
        assert isinstance(start, dt.datetime)
        assert isinstance(end, dt.datetime)
        start = start.date()
        end = end.date()

    info: dict[str, Any] = {}
    info["dtstart"] = start
    info["dtend"] = end
    info["summary"] = summary if summary else None
    info["description"] = description
    info["timezone"] = tz if not allday else None
    info["allday"] = allday
    return info
