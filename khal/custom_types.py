import datetime as dt
import os
from typing import Literal, Optional, Protocol, TypedDict, Union

import pytz


class CalendarConfiguration(TypedDict):
    name: str
    path: str
    readonly: bool
    color: str
    priority: int
    ctype: str
    addresses: str


class LocaleConfiguration(TypedDict):
    local_timezone: pytz.BaseTzInfo
    default_timezone: pytz.BaseTzInfo
    timeformat: str
    dateformat: str
    longdateformat: str
    datetimeformat: str
    longdatetimeformat: str
    weeknumbers: Union[str, bool]
    firstweekday: int
    unicode_symbols: bool


class SupportsRaw(Protocol):
    @property
    def uid(self) -> Optional[str]:
        ...

    @property
    def raw(self) -> str:
        ...


# set this to TypeAlias once we support that python version (PEP613)
EventTuple = tuple[
    str,
    str,
    Union[dt.date, dt.datetime],
    Union[dt.date, dt.datetime],
    str,
    str,
    str,
]


# Only need for RRuleMapType
class RRuleMapBase(TypedDict):
    freq: str


class RRuleMapType(RRuleMapBase, total=False):
    # not required keys go in here
    # TODO remove if either `NotRequired` is supported by mypy or the oldest
    # python we support is 3.11 (see PEP 655)
    until: dt.datetime


class EventCreationTypes(TypedDict):
    dtstart: dt.date
    dtend: dt.date
    summary: str
    description: str
    allday: bool
    location: Optional[str]
    categories: Optional[Union[str, list[str]]]
    repeat: Optional[str]
    until: str
    alarms: str
    timezone: pytz.BaseTzInfo
    url: str


PathLike = Union[str, os.PathLike]

WeekNumbersType = Literal['left', 'right', False]
MonthDisplayType = Literal['firstday', 'firstfullweek']
