from datetime import datetime as datetime
import pytz
from khal.khalendar.event import create_timezone

berlin = pytz.timezone('Europe/Berlin')
bogota = pytz.timezone('America/Bogota')

atime = datetime(2014, 10, 28, 10, 10)
btime = datetime(2016, 10, 28, 10, 10)


def test_berlin():
    vberlin = ['BEGIN:VTIMEZONE',
               'TZID:Europe/Berlin',
               'BEGIN:STANDARD',
               'DTSTART;VALUE=DATE-TIME:20141026T020000',
               'TZNAME:CET',
               'TZOFFSETFROM:+0200',
               'TZOFFSETTO:+0100',
               'END:STANDARD',
               'BEGIN:DAYLIGHT',
               'DTSTART;VALUE=DATE-TIME:20150329T030000',
               'TZNAME:CEST',
               'TZOFFSETFROM:+0100',
               'TZOFFSETTO:+0200',
               'END:DAYLIGHT',
               'END:VTIMEZONE',
               ''
               ]

    assert create_timezone(berlin, atime, atime).to_ical().split('\r\n') == vberlin


def test_berlin_rdate():
    vberlin = ['BEGIN:VTIMEZONE',
               'TZID:Europe/Berlin',
               'BEGIN:STANDARD',
               'DTSTART;VALUE=DATE-TIME:20141026T020000',
               'RDATE:20151025T020000,20161030T020000',
               'TZNAME:CET',
               'TZOFFSETFROM:+0200',
               'TZOFFSETTO:+0100',
               'END:STANDARD',
               'BEGIN:DAYLIGHT',
               'DTSTART;VALUE=DATE-TIME:20150329T030000',
               'RDATE:20160327T030000',
               'TZNAME:CEST',
               'TZOFFSETFROM:+0100',
               'TZOFFSETTO:+0200',
               'END:DAYLIGHT',
               'END:VTIMEZONE',
               ''
               ]

    assert create_timezone(berlin, atime, btime).to_ical().split('\r\n') == vberlin


def test_bogota():
    vbogota = ['BEGIN:VTIMEZONE',
               'TZID:America/Bogota',
               'BEGIN:STANDARD',
               'DTSTART;VALUE=DATE-TIME:19930403T230000',
               'TZNAME:COT',
               'TZOFFSETFROM:-0400',
               'TZOFFSETTO:-0500',
               'END:STANDARD',
               'END:VTIMEZONE',
               ''
               ]
    assert create_timezone(bogota, atime, atime).to_ical().split('\r\n') == vbogota
