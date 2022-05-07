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

"""collection of utility functions"""


import datetime as dt
import random
import re
import string
from calendar import month_abbr, timegm
from textwrap import wrap
from typing import Iterator, List, Optional, Tuple

import pytz


def generate_random_uid() -> str:
    """generate a random uid

    when random isn't broken, getting a random UID from a pool of roughly 10^56
    should be good enough"""
    choice = string.ascii_uppercase + string.digits
    return ''.join([random.choice(choice) for _ in range(36)])


RESET = '\x1b[0m'

ansi_reset = re.compile(r'\x1b\[0m')
ansi_sgr = re.compile(r'\x1b\['
                      '(?!0m)'  # negative lookahead, don't match 0m
                      '([0-9]+;?)+'
                      'm')


def find_last_reset(string: str) -> Tuple[int, int, str]:
    for match in re.finditer(ansi_reset, string):  # noqa B007: this is actually used below.
        pass
    try:
        return match.start(), match.end(), match.group(0)
    except UnboundLocalError:
        return -2, -1, ''


def find_last_sgr(string: str) -> Tuple[int, int, str]:
    for match in re.finditer(ansi_sgr, string):  # noqa B007: this is actually used below.
        pass
    try:
        return match.start(), match.end(), match.group(0)
    except UnboundLocalError:
        return -2, -1, ''


def find_unmatched_sgr(string: str) -> Optional[str]:
    reset_pos, _, _ = find_last_reset(string)
    sgr_pos, _, sgr = find_last_sgr(string)
    if sgr_pos > reset_pos:
        return sgr
    else:
        return None


def color_wrap(text: str, width: int = 70) -> List[str]:
    """A variant of wrap that takes SGR codes (somewhat) into account.

    This doesn't actually adjust the length, but makes sure that
    lines that enable some attribues also contain a RESET, and also adds
    that code to the next line
    """
    # TODO we really want to ignore all SGR codes when measuring the width
    lines = wrap(text, width)
    for num, _ in enumerate(lines):
        sgr = find_unmatched_sgr(lines[num])
        if sgr is not None:
            lines[num] += RESET
            if (num + 1) < len(lines):
                lines[num + 1] = sgr + lines[num + 1]
    return lines


def get_weekday_occurrence(day: dt.date) -> Tuple[int, int]:
    """Calculate how often this weekday has already occurred in a given month.

    :returns: weekday (0=Monday, ..., 6=Sunday), occurrence
    """
    xthday = 1 + (day.day - 1) // 7
    return day.weekday(), xthday


def get_month_abbr_len() -> int:
    """Calculate the number of characters we need to display the month
    abbreviated name. It depends on the locale.
    """
    return max(len(month_abbr[i]) for i in range(1, 13)) + 1


def localize_strip_tz(dates: List[dt.datetime], timezone: dt.tzinfo) -> Iterator[dt.datetime]:
    """converts a list of dates to timezone, than removes tz info"""
    for one_date in dates:
        if getattr(one_date, 'tzinfo', None) is not None:
            one_date = one_date.astimezone(timezone)
            one_date = one_date.replace(tzinfo=None)
        yield one_date


def to_unix_time(dtime: dt.datetime) -> float:
    """convert a datetime object to unix time in UTC (as a float)"""
    if getattr(dtime, 'tzinfo', None) is not None:
        dtime = dtime.astimezone(pytz.UTC)
    unix_time = timegm(dtime.timetuple())
    return unix_time


def to_naive_utc(dtime: dt.datetime) -> dt.datetime:
    """convert a datetime object to UTC and than remove the tzinfo, if
    datetime is naive already, return it
    """
    if not hasattr(dtime, 'tzinfo') or dtime.tzinfo is None:
        return dtime

    dtime_utc = dtime.astimezone(pytz.UTC)
    dtime_naive = dtime_utc.replace(tzinfo=None)
    return dtime_naive


def is_aware(dtime: dt.datetime) -> bool:
    """test if a datetime instance is timezone aware"""
    if dtime.tzinfo is not None and dtime.tzinfo.utcoffset(dtime) is not None:
        return True
    else:
        return False


def relative_timedelta_str(day: dt.date) -> str:
    """Converts the timespan from `day` to today into a human readable string.
    """
    days = (day - dt.date.today()).days
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


def get_wrapped_text(widget):
    return widget.original_widget.get_edit_text()
