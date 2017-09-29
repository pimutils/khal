"""testing functions from the khal.utils"""
import datetime as dt
import random
import textwrap

from freezegun import freeze_time

import icalendar

from khal import utils

from .utils import (LOCALE_BERLIN, _get_text, normalize_component)


def _get_TZIDs(lines):
    """from a list of strings, get all unique strings that start with TZID"""
    return sorted((line for line in lines if line.startswith('TZID')))


def test_normalize_component():
    assert normalize_component(textwrap.dedent("""
    BEGIN:VEVENT
    DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T093000
    END:VEVENT
    """)) != normalize_component(textwrap.dedent("""
    BEGIN:VEVENT
    DTSTART;TZID=Oyrope/Berlin;VALUE=DATE-TIME:20140409T093000
    END:VEVENT
    """))


def test_split_ics():
    cal = _get_text('cal_lots_of_timezones')
    vevents = utils.split_ics(cal)

    vevents0 = vevents[0].split('\r\n')
    vevents1 = vevents[1].split('\r\n')

    part0 = _get_text('part0').split('\n')
    part1 = _get_text('part1').split('\n')

    assert _get_TZIDs(vevents0) == _get_TZIDs(part0)
    assert _get_TZIDs(vevents1) == _get_TZIDs(part1)

    assert sorted(vevents0) == sorted(part0)
    assert sorted(vevents1) == sorted(part1)


def test_split_ics_random_uid():
    random.seed(123)
    cal = _get_text('cal_lots_of_timezones')
    vevents = utils.split_ics(cal, random_uid=True)

    part0 = _get_text('part0').split('\n')
    part1 = _get_text('part1').split('\n')

    for item in icalendar.Calendar.from_ical(vevents[0]).walk():
        if item.name == 'VEVENT':
            assert item['UID'] == 'DRF0RGCY89VVDKIV9VPKA1FYEAU2GCFJIBS1'
    for item in icalendar.Calendar.from_ical(vevents[1]).walk():
        if item.name == 'VEVENT':
            assert item['UID'] == '4Q4CTV74N7UAZ618570X6CLF5QKVV9ZE3YVB'

    # after replacing the UIDs, everything should be as above
    vevents0 = vevents[0].replace('DRF0RGCY89VVDKIV9VPKA1FYEAU2GCFJIBS1', '123').split('\r\n')
    vevents1 = vevents[1].replace('4Q4CTV74N7UAZ618570X6CLF5QKVV9ZE3YVB', 'abcde').split('\r\n')

    assert _get_TZIDs(vevents0) == _get_TZIDs(part0)
    assert _get_TZIDs(vevents1) == _get_TZIDs(part1)

    assert sorted(vevents0) == sorted(part0)
    assert sorted(vevents1) == sorted(part1)


def test_split_ics_missing_timezone():
    """testing if we detect the missing timezone in splitting"""
    cal = _get_text('event_dt_local_missing_tz')
    utils.split_ics(cal, random_uid=True, default_timezone=LOCALE_BERLIN['default_timezone'])


def test_relative_timedelta_str():
    with freeze_time('2016-9-19'):
        assert utils.relative_timedelta_str(dt.date(2016, 9, 24)) == '5 days from now'
        assert utils.relative_timedelta_str(dt.date(2016, 9, 29)) == '~1 week from now'
        assert utils.relative_timedelta_str(dt.date(2017, 9, 29)) == '~1 year from now'
        assert utils.relative_timedelta_str(dt.date(2016, 7, 29)) == '~7 weeks ago'


weekheader = """[1m    Mo Tu We Th Fr Sa Su   [0m"""
today_line = """[1mToday[0m[0m"""
calendarline = (
    "[1mNov [0m[1;33m31[0m [32m 1[0m [1;33m 2[0m "
    "[1;33m 3[0m [1;33m 4[0m [32m 5[0m [32m 6[0m"
)


def test_last_reset():
    assert utils.find_last_reset(weekheader) == (31, 35, '\x1b[0m')
    assert utils.find_last_reset(today_line) == (13, 17, '\x1b[0m')
    assert utils.find_last_reset(calendarline) == (99, 103, '\x1b[0m')
    assert utils.find_last_reset('Hello World') == (-2, -1, '')


def test_last_sgr():
    assert utils.find_last_sgr(weekheader) == (0, 4, '\x1b[1m')
    assert utils.find_last_sgr(today_line) == (0, 4, '\x1b[1m')
    assert utils.find_last_sgr(calendarline) == (92, 97, '\x1b[32m')
    assert utils.find_last_sgr('Hello World') == (-2, -1, '')


def test_find_unmatched_sgr():
    assert utils.find_unmatched_sgr(weekheader) is False
    assert utils.find_unmatched_sgr(today_line) is False
    assert utils.find_unmatched_sgr(calendarline) is False
    assert utils.find_unmatched_sgr('\x1b[31mHello World') == '\x1b[31m'
    assert utils.find_unmatched_sgr('\x1b[31mHello\x1b[0m \x1b[32mWorld') == '\x1b[32m'
    assert utils.find_unmatched_sgr('foo\x1b[1;31mbar') == '\x1b[1;31m'
    assert utils.find_unmatched_sgr('\x1b[0mfoo\x1b[1;31m') == '\x1b[1;31m'


def test_color_wrap():
    text = (
        "Lorem ipsum \x1b[31mdolor sit amet, consetetur sadipscing "
        "elitr, sed diam nonumy\x1b[0m eirmod tempor"
    )
    expected = [
        "Lorem ipsum \x1b[31mdolor sit amet,\x1b[0m",
        "\x1b[31mconsetetur sadipscing elitr, sed\x1b[0m",
        "\x1b[31mdiam nonumy\x1b[0m eirmod tempor",
    ]

    assert utils.color_wrap(text, 35) == expected


def test_color_wrap_256():
    text = (
        "\x1b[38;2;17;255;0mLorem ipsum dolor sit amet, consetetur sadipscing "
        "elitr, sed diam nonumy\x1b[0m"
    )
    expected = [
        "\x1b[38;2;17;255;0mLorem ipsum\x1b[0m",
        "\x1b[38;2;17;255;0mdolor sit amet, consetetur\x1b[0m",
        "\x1b[38;2;17;255;0msadipscing elitr, sed diam\x1b[0m",
        "\x1b[38;2;17;255;0mnonumy\x1b[0m"
    ]

    assert utils.color_wrap(text, 30) == expected


def test_get_weekday_occurrence():
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 1)) == (2, 1)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 2)) == (3, 1)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 3)) == (4, 1)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 4)) == (5, 1)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 5)) == (6, 1)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 6)) == (0, 1)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 7)) == (1, 1)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 8)) == (2, 2)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 9)) == (3, 2)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 10)) == (4, 2)

    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 31)) == (4, 5)

    assert utils.get_weekday_occurrence(dt.date(2017, 5, 1)) == (0, 1)
    assert utils.get_weekday_occurrence(dt.date(2017, 5, 7)) == (6, 1)
    assert utils.get_weekday_occurrence(dt.date(2017, 5, 8)) == (0, 2)
    assert utils.get_weekday_occurrence(dt.date(2017, 5, 28)) == (6, 4)
    assert utils.get_weekday_occurrence(dt.date(2017, 5, 29)) == (0, 5)
