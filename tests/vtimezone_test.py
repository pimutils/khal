import datetime as dt

import pytz
from packaging import version

from khal.khalendar.event import create_timezone

berlin = pytz.timezone('Europe/Berlin')
bogota = pytz.timezone('America/Bogota')

atime = dt.datetime(2014, 10, 28, 10, 10)
btime = dt.datetime(2016, 10, 28, 10, 10)


def test_berlin():
    vberlin_std = b'\r\n'.join(
        [b'BEGIN:STANDARD',
         b'DTSTART:20141026T020000',
         b'TZNAME:CET',
         b'TZOFFSETFROM:+0200',
         b'TZOFFSETTO:+0100',
         b'END:STANDARD',
         ])

    vberlin_dst = b'\r\n'.join(
        [b'BEGIN:DAYLIGHT',
         b'DTSTART:20150329T030000',
         b'TZNAME:CEST',
         b'TZOFFSETFROM:+0100',
         b'TZOFFSETTO:+0200',
         b'END:DAYLIGHT',
         ])

    vberlin = create_timezone(berlin, atime, atime).to_ical()
    assert b'TZID:Europe/Berlin' in vberlin
    assert vberlin_std in vberlin
    assert vberlin_dst in vberlin


def test_berlin_rdate():
    vberlin_std = b'\r\n'.join(
        [b'BEGIN:STANDARD',
         b'DTSTART:20141026T020000',
         b'RDATE:20151025T020000,20161030T020000',
         b'TZNAME:CET',
         b'TZOFFSETFROM:+0200',
         b'TZOFFSETTO:+0100',
         b'END:STANDARD',
         ])

    vberlin_dst = b'\r\n'.join(
        [b'BEGIN:DAYLIGHT',
         b'DTSTART:20150329T030000',
         b'RDATE:20160327T030000',
         b'TZNAME:CEST',
         b'TZOFFSETFROM:+0100',
         b'TZOFFSETTO:+0200',
         b'END:DAYLIGHT',
         ])

    vberlin = create_timezone(berlin, atime, btime).to_ical()
    assert b'TZID:Europe/Berlin' in vberlin
    assert vberlin_std in vberlin
    assert vberlin_dst in vberlin


def test_bogota():
    vbogota = [b'BEGIN:VTIMEZONE',
               b'TZID:America/Bogota',
               b'BEGIN:STANDARD',
               b'DTSTART:19930206T230000',
               b'TZNAME:COT',
               b'TZOFFSETFROM:-0400',
               b'TZOFFSETTO:-0500',
               b'END:STANDARD',
               b'END:VTIMEZONE',
               b'']
    if version.parse(pytz.__version__) > version.Version('2017.1'):
        vbogota[4] = b'TZNAME:-05'
        if version.parse(pytz.__version__) < version.Version('2022.7'):
            vbogota.insert(4, b'RDATE:20380118T221407')

    assert create_timezone(bogota, atime, atime).to_ical().split(b'\r\n') == vbogota
