# vim: set fileencoding=utf-8 :

import datetime
import textwrap

import pytest
import pytz

from khal.khalendar.event import Event

from .aux import normalize_component


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

berlin = pytz.timezone('Europe/Berlin')
# the lucky people in Bogota don't know the pain that is DST
bogota = pytz.timezone('America/Bogota')

today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)
tomorrow = today + datetime.timedelta(days=1)

event_allday_template = u"""BEGIN:VEVENT
SEQUENCE:0
UID:uid3@host1.com
DTSTART;VALUE=DATE:{}
DTEND;VALUE=DATE:{}
SUMMARY:a meeting
DESCRIPTION:short description
LOCATION:LDB Lobby
END:VEVENT"""


event_dt = """BEGIN:VEVENT
SUMMARY:An Event
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T093000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T103000
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""

cal_dt = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CALENDARSERVER.ORG//NONSGML Version 1//EN
BEGIN:VTIMEZONE
TZID:Europe/Berlin
BEGIN:STANDARD
RDATE:20151025T020000
DTSTART;VALUE=DATE-TIME:20141026T020000
TZNAME:CET
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
END:STANDARD
BEGIN:DAYLIGHT
DTSTART;VALUE=DATE-TIME:20140330T030000
RDATE:20150329T030000
TZNAME:CEST
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
SUMMARY:An Event
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T093000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T103000
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT
END:VCALENDAR
""".strip()

cal_dt_cet = [b'BEGIN:STANDARD',
              b'DTSTART;VALUE=DATE-TIME:20141026T020000',
              b'TZNAME:CET',
              b'TZOFFSETFROM:+0200',
              b'TZOFFSETTO:+0100',
              b'END:STANDARD'
              ]

cal_dt_cest = [b'BEGIN:DAYLIGHT',
               b'DTSTART;VALUE=DATE-TIME:20140330T030000',
               b'RDATE:20150329T030000',
               b'TZNAME:CEST',
               b'TZOFFSETFROM:+0100',
               b'TZOFFSETTO:+0200',
               b'END:DAYLIGHT',
               ]

event_dt_two_tz = """BEGIN:VEVENT
SUMMARY:An Event
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T093000
DTEND;TZID=America/New_York;VALUE=DATE-TIME:20140409T103000
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""

cal_dt_two_tz = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CALENDARSERVER.ORG//NONSGML Version 1//EN
BEGIN:VTIMEZONE
TZID:Europe/Berlin
BEGIN:STANDARD
DTSTART;VALUE=DATE-TIME:20141026T020000
TZNAME:CET
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
RDATE:20151025T020000
END:STANDARD
BEGIN:DAYLIGHT
DTSTART;VALUE=DATE-TIME:20140330T030000
RDATE:20150329T030000
TZNAME:CEST
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VTIMEZONE
TZID:America/New_York
BEGIN:STANDARD
DTSTART;VALUE=DATE-TIME:20141102T010000
RDATE:20151101T010000
TZNAME:EST
TZOFFSETFROM:-0400
TZOFFSETTO:-0500
END:STANDARD
BEGIN:DAYLIGHT
DTSTART;VALUE=DATE-TIME:20140309T030000
RDATE:20150308T030000
TZNAME:EDT
TZOFFSETFROM:-0500
TZOFFSETTO:-0400
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
SUMMARY:An Event
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T093000
DTEND;TZID=America/New_York;VALUE=DATE-TIME:20140409T103000
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT
END:VCALENDAR
""".strip()

event_no_dst = """
BEGIN:VEVENT
SUMMARY:An Event
DTSTART;TZID=America/Bogota;VALUE=DATE-TIME:20140409T093000
DTEND;TZID=America/Bogota;VALUE=DATE-TIME:20140409T103000
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:event_no_dst
END:VEVENT
"""
cal_no_dst = u"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CALENDARSERVER.ORG//NONSGML Version 1//EN
BEGIN:VTIMEZONE
TZID:America/Bogota
BEGIN:STANDARD
DTSTART;VALUE=DATE-TIME:19930403T230000
TZNAME:COT
TZOFFSETFROM:-0400
TZOFFSETTO:-0500
END:STANDARD
END:VTIMEZONE
BEGIN:VEVENT
SUMMARY:An Event
DTSTART;TZID=America/Bogota;VALUE=DATE-TIME:20140409T093000
DTEND;TZID=America/Bogota;VALUE=DATE-TIME:20140409T103000
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:event_no_dst
END:VEVENT
END:VCALENDAR
""".split('\n')

event_dt_duration = """BEGIN:VEVENT
SUMMARY:An Event
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T093000
DURATION:PT1H0M0S
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""

event_dt_no_tz = """BEGIN:VEVENT
SUMMARY:An Event
DTSTART;VALUE=DATE-TIME:20140409T093000
DTEND;VALUE=DATE-TIME:20140409T103000
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""

event_dt_rr = """BEGIN:VEVENT
SUMMARY:An Event
DTSTART;VALUE=DATE-TIME:20140409T093000
DTEND;VALUE=DATE-TIME:20140409T103000
RRULE:FREQ=DAILY;COUNT=10
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""

event_dt_rd = """BEGIN:VEVENT
SUMMARY:An Event
DTSTART;VALUE=DATE-TIME:20140409T093000
DTEND;VALUE=DATE-TIME:20140409T103000
RDATE;VALUE=DATE-TIME:20140410T093000
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""

event_dt_long = """BEGIN:VEVENT
SUMMARY:An Event
DTSTART;VALUE=DATE-TIME:20140409T093000
DTEND;VALUE=DATE-TIME:20140412T103000
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""

event_d = """BEGIN:VEVENT
SUMMARY:Another Event
DTSTART;VALUE=DATE:20140409
DTEND;VALUE=DATE:20140410
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""

event_d_long = """BEGIN:VEVENT
SUMMARY:Another Event
DTSTART;VALUE=DATE:20140409
DTEND;VALUE=DATE:20140412
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""

event_d_rr = """BEGIN:VEVENT
SUMMARY:Another Event
DTSTART;VALUE=DATE:20140409
DTEND;VALUE=DATE:20140410
RRULE:FREQ=DAILY;COUNT=10
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""

cal_d = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CALENDARSERVER.ORG//NONSGML Version 1//EN
BEGIN:VEVENT
SUMMARY:Another Event
DTSTART;VALUE=DATE:20140409
DTEND;VALUE=DATE:20140410
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT
END:VCALENDAR
""".split('\n')

locale = {
    'default_timezone': berlin,
    'local_timezone': berlin,
    'dateformat': '%d.%m.',
    'timeformat': '%H:%M',
    'longdateformat': '%d.%m.%Y',
    'datetimeformat': '%d.%m. %H:%M',
    'longdatetimeformat': '%d.%m.%Y %H:%M',
}
event_kwargs = {'calendar': 'foobar', 'locale': locale}


def test_raw_dt():
    event = Event(event_dt, **event_kwargs)
    assert normalize_component(event.raw) == normalize_component(cal_dt)
    assert event.compact(datetime.date(2014, 4, 9)) == u'09:30-10:30: An Event'

    event = Event(event_dt, unicode_symbols=False, **event_kwargs)
    assert event.compact(datetime.date(2014, 4, 9)) == u'09:30-10:30: An Event'
    assert event.long() == u'09:30-10:30 09.04.2014: An Event'
    assert event.recur is False


def test_raw_d():
    event = Event(event_d, **event_kwargs)
    assert event.raw.split('\r\n') == cal_d
    assert event.compact(datetime.date(2014, 4, 9)) == u'Another Event'
    assert event.long() == u'09.04.2014: Another Event'


def test_dt_two_tz():
    event = Event(event_dt_two_tz, **event_kwargs)
    assert normalize_component(cal_dt_two_tz) == normalize_component(event.raw)

    # local (Berlin) time!
    assert event.compact(datetime.date(2014, 4, 9)) == u'09:30-16:30: An Event'
    assert event.long() == u'09:30-16:30 09.04.2014: An Event'


def test_event_dt_duration():
    """event has no end, but duration"""
    event = Event(event_dt_duration, **event_kwargs)
    assert event.compact(datetime.date(2014, 4, 9)) == u'09:30-10:30: An Event'
    assert event.end == berlin.localize(datetime.datetime(2014, 4, 9, 10, 30))
    assert event.long() == u'09:30-10:30 09.04.2014: An Event'


def test_event_dt_no_tz():
    """start and end time of no timezone"""
    event = Event(event_dt_no_tz, **event_kwargs)
    assert event.compact(datetime.date(2014, 4, 9)) == u'09:30-10:30: An Event'
    assert event.long() == u'09:30-10:30 09.04.2014: An Event'


def test_event_rr():
    event = Event(event_dt_rr, **event_kwargs)
    assert event.recur is True
    assert event.compact(datetime.date(2014, 4, 9)) == u'09:30-10:30: An Event ⟳'
    assert event.long() == u'09:30-10:30 09.04.2014: An Event\nRepeat: FREQ=DAILY;COUNT=10'
    event = Event(event_d_rr, **event_kwargs)
    assert event.recur is True
    assert event.compact(datetime.date(2014, 4, 9)) == u'Another Event ⟳'
    assert event.long() == u'09.04.2014: Another Event\nRepeat: FREQ=DAILY;COUNT=10'


def test_event_rd():
    event = Event(event_dt_rd, **event_kwargs)
    assert event.recur is True


def test_event_d_long():
    event = Event(event_d_long, **event_kwargs)
    with pytest.raises(ValueError):
        event.compact(datetime.date(2014, 4, 8))
    assert event.compact(datetime.date(2014, 4, 9)) == u'↦ Another Event'
    assert event.compact(datetime.date(2014, 4, 10)) == u'↔ Another Event'
    assert event.compact(datetime.date(2014, 4, 11)) == u'⇥ Another Event'
    with pytest.raises(ValueError):
        event.compact(datetime.date(2014, 4, 12))
    assert event.long() == u'09.04. - 11.04.2014: Another Event'


def test_event_dt_long():
    event = Event(event_dt_long, **event_kwargs)
    with pytest.raises(ValueError):
        event.compact(datetime.date(2014, 4, 8))
    assert event.compact(datetime.date(2014, 4, 9)) == u'09:30→ : An Event'
    # FIXME ugly! replace with one arrow
    assert event.compact(datetime.date(2014, 4, 10)) == u'→ → : An Event'
    assert event.compact(datetime.date(2014, 4, 12)) == u'→ 10:30: An Event'
    with pytest.raises(ValueError):
        event.compact(datetime.date(2014, 4, 13))
    assert event.long() == u'09.04.2014 09:30 - 12.04.2014 10:30: An Event'


def test_event_no_dst():
    """test the creation of a corect VTIMEZONE for timezones with no dst"""
    bogota_locale = locale.copy()
    bogota_locale['local_timezone'] = bogota
    bogota_locale['default_timezone'] = bogota

    event = Event(event_no_dst, calendar='foobar', locale=bogota_locale)
    assert event.raw.split('\r\n') == cal_no_dst
    assert event.long() == u'09:30-10:30 09.04.2014: An Event'


def test_dtend_equals_dtstart():
    text = textwrap.dedent("""
        BEGIN:VEVENT
        CREATED:20141112T153944Z
        DESCRIPTION:asdf
        DTEND;VALUE=DATE:20141127
        DTSTAMP:20141112T153944Z
        DTSTART;VALUE=DATE:20141127
        LAST-MODIFIED:20141112T153944Z
        SEQUENCE:0
        SUMMARY:asdfevent
        UID:937569nfv37689g
        END:VEVENT
        """)

    event = Event(text, calendar='foobar', locale=locale)
    assert event.end - event.start == datetime.timedelta(days=1)
