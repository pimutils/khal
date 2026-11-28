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

"""Moving through time in ikhal: by months and years (`{` `}` `[` `]`) and to
a typed date (`g`), the same in the month column, the list and other views
"""

from __future__ import annotations

import calendar
import datetime as dt
import re

from khal.exceptions import DateTimeParseError
from khal.parse_datetime import guessdatetimefstr

# command name -> months to move
MONTH_STEPS = {"next_month": 1, "prev_month": -1, "next_year": 12, "prev_year": -12}

RELATIVE = re.compile(r"^([+-])\s*(\d+)\s*([dwmy])$")


def shift_months(day: dt.date, months: int) -> dt.date:
    """`day` moved by `months`, the same day of the month or the month's
    last day (31 Jan + 1 month: 28/29 Feb, 29 Feb + 12 months: 28 Feb)"""
    index = day.year * 12 + day.month - 1 + months
    year, month = divmod(index, 12)
    last = calendar.monthrange(year, month + 1)[1]
    return dt.date(year, month + 1, min(day.day, last))


def parse_goto(text: str, locale, today: dt.date | None = None) -> dt.date | None:
    """the date `text` means: whatever khal's command line accepts (dates in
    the configured formats, ISO dates, weekday names, today, tomorrow,
    yesterday) or an
    offset from `today` (`+3d`, `-2w`, `+1m`, `-1y`); None if it's no date"""
    today = today or dt.date.today()
    text = text.strip()
    if not text:
        return None
    match = RELATIVE.match(text.lower())
    if match:
        sign, number, unit = match.groups()
        amount = int(number) * (1 if sign == "+" else -1)
        if unit == "d":
            return today + dt.timedelta(days=amount)
        if unit == "w":
            return today + dt.timedelta(weeks=amount)
        return shift_months(today, amount * (12 if unit == "y" else 1))
    try:  # ISO dates always work
        return dt.date.fromisoformat(text)
    except ValueError:
        pass
    words = text.split()
    try:
        start, _ = guessdatetimefstr(words, locale, default_day=today, in_future=False)
    except (DateTimeParseError, ValueError, IndexError):
        return None
    if words:  # all words have to be used up
        return None
    return start.date()
