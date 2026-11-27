import datetime as dt
import os
from typing import Literal, NotRequired, Protocol, TypeAlias, TypedDict

import pytz

PathLike: TypeAlias = str | os.PathLike

WeekNumbersType: TypeAlias = Literal["left", "right", False]
MonthDisplayType: TypeAlias = Literal["firstday", "firstfullweek"]
ColorModeType: TypeAlias = Literal["256colors", "rgb"]


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
    weeknumbers: WeekNumbersType
    firstweekday: int
    unicode_symbols: bool


class SupportsRaw(Protocol):
    @property
    def uid(self) -> str | None: ...

    @property
    def raw(self) -> str: ...


EventTuple: TypeAlias = tuple[
    str,
    str,
    dt.date | dt.datetime,
    dt.date | dt.datetime,
    str,
    str,
    str,
]


class RRuleMapType(TypedDict):
    freq: str
    until: NotRequired[dt.datetime]


class EventCreationTypes(TypedDict):
    """keyword arguments for :func:`khal.icalendar.new_vevent`

    keys marked as `NotRequired` have a default value there
    """

    dtstart: dt.date
    dtend: dt.date
    summary: str
    description: NotRequired[str | None]
    allday: NotRequired[bool]
    location: NotRequired[str | None]
    categories: NotRequired[str | list[str] | None]
    repeat: NotRequired[str | None]
    until: NotRequired[str | None]
    alarms: NotRequired[str | None]
    timezone: NotRequired[pytz.BaseTzInfo | None]
    url: NotRequired[str | None]
