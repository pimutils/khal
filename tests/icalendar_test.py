import datetime as dt
import random
import textwrap

import icalendar
from freezegun import freeze_time

from khal.icalendar import new_vevent, split_ics

from .utils import LOCALE_BERLIN, _get_text, _replace_uid, normalize_component


def _get_TZIDs(lines):
    """from a list of strings, get all unique strings that start with TZID"""
    return sorted(line for line in lines if line.startswith('TZID'))


def test_normalize_component():
    assert normalize_component(textwrap.dedent("""
    BEGIN:VEVENT
    DTSTART;TZID=Europe/Berlin:20140409T093000
    END:VEVENT
    """)) != normalize_component(textwrap.dedent("""
    BEGIN:VEVENT
    DTSTART;TZID=Oyrope/Berlin:20140409T093000
    END:VEVENT
    """))


def test_new_vevent():
    with freeze_time('20220702T1400'):
        vevent = _replace_uid(new_vevent(
            LOCALE_BERLIN,
            dt.date(2022, 7, 2),
            dt.date(2022, 7, 3),
            'An Event',
            allday=True,
            repeat='weekly',
        ))
        assert vevent.to_ical().decode('utf-8') == '\r\n'.join([
            'BEGIN:VEVENT',
            'SUMMARY:An Event',
            'DTSTART;VALUE=DATE:20220702',
            'DTEND;VALUE=DATE:20220703',
            'DTSTAMP:20220702T140000Z',
            'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
            'RRULE:FREQ=WEEKLY',
            'END:VEVENT',
            ''
        ])


def test_split_ics():
    cal = _get_text('cal_lots_of_timezones')
    vevents = split_ics(cal)

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
    vevents = split_ics(cal, random_uid=True)

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
    split_ics(cal, random_uid=True, default_timezone=LOCALE_BERLIN['default_timezone'])


def test_windows_timezone(caplog):
    """Test if a windows tz format works"""
    cal = _get_text("tz_windows_format")
    split_ics(cal)
    assert "Cannot find timezone `Pacific/Auckland`" not in caplog.text


def test_split_ics_without_uid():
    cal = _get_text('without_uid')
    vevents = split_ics(cal)
    assert vevents
    vevents2 = split_ics(cal)
    assert vevents[0] == vevents2[0]
