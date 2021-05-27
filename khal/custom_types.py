import datetime as dt
from typing import Protocol, TypedDict, Union


class CalendarConfiguration(TypedDict):
    name: str
    path: str
    readonly: bool
    color: str
    priority: int
    ctype: str


class LocaleConfiguration(TypedDict):
    local_timezone: dt.tzinfo
    default_timezone: dt.tzinfo
    timeformat: str
    dateformat: str
    longdateformat: str
    datetimeformat: str
    longdatetimeformat: str
    weeknumbers: Union[str, bool]
    firstweekday: int
    unicode_symbols: bool


class SupportsRaw(Protocol):
    uid: str
    def raw(self) -> str: ...
