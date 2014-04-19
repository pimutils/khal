import datetime
import icalendar

import pytest
import pytz

from khal.khalendar import datetimehelper

# datetime
event_dt = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Datetime Event
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20130301T140000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20130301T160000
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=6
UID:datetime123
END:VEVENT
END:VCALENDAR"""

event_dt_norr = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Datetime Event
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20130301T140000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20130301T160000
UID:datetime123
END:VEVENT
END:VCALENDAR"""

# datetime zulu (in utc time)
event_dttz = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Datetime Zulu Event
DTSTART;VALUE=DATE-TIME:20130301T140000Z
DTEND;VALUE=DATE-TIME:20130301T160000Z
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=6
UID:datetimezulu123
END:VEVENT
END:VCALENDAR"""

event_dttz_norr = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Datetime Zulu Event
DTSTART;VALUE=DATE-TIME:20130301T140000Z
DTEND;VALUE=DATE-TIME:20130301T160000Z
UID:datetimezulu123
END:VEVENT
END:VCALENDAR"""

# datetime floating (no time zone information)
event_dtf = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Datetime floating Event
DTSTART;VALUE=DATE-TIME:20130301T140000
DTEND;VALUE=DATE-TIME:20130301T160000
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=6
UID:datetimefloating123
END:VEVENT
END:VCALENDAR"""

event_dtf_norr = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Datetime floating Event
DTSTART;VALUE=DATE-TIME:20130301T140000
DTEND;VALUE=DATE-TIME:20130301T160000
UID:datetimefloating123
END:VEVENT
END:VCALENDAR"""

# datetime broken (as in we don't understand the timezone information)
event_dtb = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VTIMEZONE
TZID:/freeassociation.sourceforge.net/Tzfile/Europe/Berlin
X-LIC-LOCATION:Europe/Berlin
BEGIN:STANDARD
TZNAME:CET
DTSTART:19701027T030000
RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
END:STANDARD
BEGIN:DAYLIGHT
TZNAME:CEST
DTSTART:19700331T020000
RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=3
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
UID:broken123
DTSTART;TZID=/freeassociation.sourceforge.net/Tzfile/Europe/Berlin:20130301T140000
DTEND;TZID=/freeassociation.sourceforge.net/Tzfile/Europe/Berlin:20130301T160000
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=6
TRANSP:OPAQUE
SEQUENCE:2
SUMMARY:Broken Event
END:VEVENT
END:VCALENDAR
"""

event_dtb_norr = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VTIMEZONE
TZID:/freeassociation.sourceforge.net/Tzfile/Europe/Berlin
X-LIC-LOCATION:Europe/Berlin
BEGIN:STANDARD
TZNAME:CET
DTSTART:19701027T030000
RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
END:STANDARD
BEGIN:DAYLIGHT
TZNAME:CEST
DTSTART:19700331T020000
RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=3
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
UID:broken123
DTSTART;TZID=/freeassociation.sourceforge.net/Tzfile/Europe/Berlin:20130301T140000
DTEND;TZID=/freeassociation.sourceforge.net/Tzfile/Europe/Berlin:20130301T160000
TRANSP:OPAQUE
SEQUENCE:2
SUMMARY:Broken Event
END:VEVENT
END:VCALENDAR
"""

# all day (date) event
event_d = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
UID:date123
DTSTART;VALUE=DATE:20130301
DTEND;VALUE=DATE:20130302
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=6
SUMMARY:Event
END:VEVENT
END:VCALENDAR
"""

# all day (date) event with timezone information
event_dtz = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
UID:datetz123
DTSTART;TZID=Berlin/Europe;VALUE=DATE:20130301
DTEND;TZID=Berlin/Europe;VALUE=DATE:20130302
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=6
SUMMARY:Event
END:VEVENT
END:VCALENDAR
"""

event_dtzb = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VTIMEZONE
TZID:Pacific Time (US & Canada), Tijuana
BEGIN:STANDARD
DTSTART:20071104T020000
TZOFFSETTO:-0800
TZOFFSETFROM:-0700
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:20070311T020000
TZOFFSETTO:-0700
TZOFFSETFROM:-0800
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
DTSTART;VALUE=DATE;TZID="Pacific Time (US & Canada), Tijuana":20130301
DTEND;VALUE=DATE;TZID="Pacific Time (US & Canada), Tijuana":20130302
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=6
SUMMARY:Event
UID:eventdtzb123
END:VEVENT
END:VCALENDAR
"""

event_d_norr = """BEGIN:VCALENDAR
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
UID:date123
DTSTART;VALUE=DATE:20130301
DTEND;VALUE=DATE:20130302
SUMMARY:Event
END:VEVENT
END:VCALENDAR
"""
berlin = pytz.timezone('Europe/Berlin')


def _get_vevent(event):
    ical = icalendar.Event.from_ical(event)
    for component in ical.walk():
        if component.name == 'VEVENT':
            return component


class TestExpand(object):
    dtstartend_berlin = [
        (datetime.datetime(2013, 3, 1, 14, 0, tzinfo=berlin),
         datetime.datetime(2013, 3, 1, 16, 0, tzinfo=berlin)),
        (datetime.datetime(2013, 5, 1, 14, 0, tzinfo=berlin),
         datetime.datetime(2013, 5, 1, 16, 0, tzinfo=berlin)),
        (datetime.datetime(2013, 7, 1, 14, 0, tzinfo=berlin),
         datetime.datetime(2013, 7, 1, 16, 0, tzinfo=berlin)),
        (datetime.datetime(2013, 9, 1, 14, 0, tzinfo=berlin),
         datetime.datetime(2013, 9, 1, 16, 0, tzinfo=berlin)),
        (datetime.datetime(2013, 11, 1, 14, 0, tzinfo=berlin),
         datetime.datetime(2013, 11, 1, 16, 0, tzinfo=berlin)),
        (datetime.datetime(2014, 1, 1, 14, 0, tzinfo=berlin),
         datetime.datetime(2014, 1, 1, 16, 0, tzinfo=berlin))
    ]

    dtstartend_utc = [
        (datetime.datetime(2013, 3, 1, 14, 0, tzinfo=pytz.utc),
         datetime.datetime(2013, 3, 1, 16, 0, tzinfo=pytz.utc)),
        (datetime.datetime(2013, 5, 1, 14, 0, tzinfo=pytz.utc),
         datetime.datetime(2013, 5, 1, 16, 0, tzinfo=pytz.utc)),
        (datetime.datetime(2013, 7, 1, 14, 0, tzinfo=pytz.utc),
         datetime.datetime(2013, 7, 1, 16, 0, tzinfo=pytz.utc)),
        (datetime.datetime(2013, 9, 1, 14, 0, tzinfo=pytz.utc),
         datetime.datetime(2013, 9, 1, 16, 0, tzinfo=pytz.utc)),
        (datetime.datetime(2013, 11, 1, 14, 0, tzinfo=pytz.utc),
         datetime.datetime(2013, 11, 1, 16, 0, tzinfo=pytz.utc)),
        (datetime.datetime(2014, 1, 1, 14, 0, tzinfo=pytz.utc),
         datetime.datetime(2014, 1, 1, 16, 0, tzinfo=pytz.utc))
    ]

    dtstartend_float = [
        (datetime.datetime(2013, 3, 1, 14, 0),
         datetime.datetime(2013, 3, 1, 16, 0)),
        (datetime.datetime(2013, 5, 1, 14, 0),
         datetime.datetime(2013, 5, 1, 16, 0)),
        (datetime.datetime(2013, 7, 1, 14, 0),
         datetime.datetime(2013, 7, 1, 16, 0)),
        (datetime.datetime(2013, 9, 1, 14, 0),
         datetime.datetime(2013, 9, 1, 16, 0)),
        (datetime.datetime(2013, 11, 1, 14, 0),
         datetime.datetime(2013, 11, 1, 16, 0)),
        (datetime.datetime(2014, 1, 1, 14, 0),
         datetime.datetime(2014, 1, 1, 16, 0))
    ]
    dstartend = [
        (datetime.date(2013, 3, 1,),
         datetime.date(2013, 3, 2,)),
        (datetime.date(2013, 5, 1,),
         datetime.date(2013, 5, 2,)),
        (datetime.date(2013, 7, 1,),
         datetime.date(2013, 7, 2,)),
        (datetime.date(2013, 9, 1,),
         datetime.date(2013, 9, 2,)),
        (datetime.date(2013, 11, 1),
         datetime.date(2013, 11, 2)),
        (datetime.date(2014, 1, 1,),
         datetime.date(2014, 1, 2,))
        ]
    offset_berlin = [
        datetime.timedelta(0, 3600),
        datetime.timedelta(0, 7200),
        datetime.timedelta(0, 7200),
        datetime.timedelta(0, 7200),
        datetime.timedelta(0, 3600),
        datetime.timedelta(0, 3600)
    ]

    offset_utc = [
        datetime.timedelta(0, 0),
        datetime.timedelta(0, 0),
        datetime.timedelta(0, 0),
        datetime.timedelta(0, 0),
        datetime.timedelta(0, 0),
        datetime.timedelta(0, 0),
    ]

    offset_none = [None, None, None, None, None, None]

    def test_expand_dt(self):
        vevent = _get_vevent(event_dt)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_berlin
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_berlin
        assert [end.utcoffset() for _, end in dtstart] == self.offset_berlin

    def test_expand_dtb(self):
        vevent = _get_vevent(event_dtb)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_berlin
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_berlin
        assert [end.utcoffset() for _, end in dtstart] == self.offset_berlin

    def test_expand_dttz(self):
        vevent = _get_vevent(event_dttz)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_utc
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_utc
        assert [end.utcoffset() for _, end in dtstart] == self.offset_utc

    def test_expand_dtf(self):
        vevent = _get_vevent(event_dtf)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_float
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_none
        assert [end.utcoffset() for _, end in dtstart] == self.offset_none

    def test_expand_d(self):
        vevent = _get_vevent(event_d)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dstartend

    def test_expand_dtz(self):
        vevent = _get_vevent(event_dtz)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dstartend

    def test_expand_dtzb(self):
        vevent = _get_vevent(event_dtzb)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dstartend


class TestExpandNoRR(object):
    dtstartend_berlin = [
        (datetime.datetime(2013, 3, 1, 14, 0, tzinfo=berlin),
         datetime.datetime(2013, 3, 1, 16, 0, tzinfo=berlin)),
    ]

    dtstartend_utc = [
        (datetime.datetime(2013, 3, 1, 14, 0, tzinfo=pytz.utc),
         datetime.datetime(2013, 3, 1, 16, 0, tzinfo=pytz.utc)),
    ]

    dtstartend_float = [
        (datetime.datetime(2013, 3, 1, 14, 0),
         datetime.datetime(2013, 3, 1, 16, 0)),
    ]
    offset_berlin = [
        datetime.timedelta(0, 3600),
    ]

    offset_utc = [
        datetime.timedelta(0, 0),
    ]

    offset_none = [None]

    def test_expand_dt(self):
        vevent = _get_vevent(event_dt_norr)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_berlin
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_berlin
        assert [end.utcoffset() for _, end in dtstart] == self.offset_berlin

    def test_expand_dtb(self):
        vevent = _get_vevent(event_dtb_norr)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_berlin
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_berlin
        assert [end.utcoffset() for _, end in dtstart] == self.offset_berlin

    def test_expand_dttz(self):
        vevent = _get_vevent(event_dttz_norr)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_utc
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_utc
        assert [end.utcoffset() for _, end in dtstart] == self.offset_utc

    def test_expand_dtf(self):
        vevent = _get_vevent(event_dtf_norr)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == self.dtstartend_float
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_none
        assert [end.utcoffset() for _, end in dtstart] == self.offset_none

    def test_expand_d(self):
        vevent = _get_vevent(event_d_norr)
        dtstart = datetimehelper.expand(vevent, berlin)
        assert dtstart == [
            (datetime.date(2013, 3, 1,),
             datetime.date(2013, 3, 2,)),
        ]


vevent_until_notz = """BEGIN:VEVENT
SUMMARY:until 20. Februar
DTSTART;TZID=Europe/Berlin:20140203T070000
DTEND;TZID=Europe/Berlin:20140203T090000
UID:until_notz
RRULE:FREQ=DAILY;UNTIL=20140220T060000Z;WKST=SU
END:VEVENT
"""

vevent_count = """BEGIN:VEVENT
SUMMARY:until 20. Februar
DTSTART:20140203T070000
DTEND:20140203T090000
UID:until_notz
RRULE:FREQ=DAILY;UNTIL=20140220;WKST=SU
END:VEVENT
"""

class TestSpecial(object):
    @pytest.mark.xfail(reason='')
    def test_count(self):
        vevent = _get_vevent(vevent_count)
        dtstart = datetimehelper.expand(vevent, berlin)
        starts = [start for start, _ in dtstart]
        assert len(starts) == 18
        assert dtstart[0][0] == datetime.datetime(2014, 2, 3, 7, 0)
        assert dtstart[-1][0] == datetime.datetime(2014, 2, 20, 7, 0)

    def test_until_notz(self):
        vevent = _get_vevent(vevent_until_notz)
        dtstart = datetimehelper.expand(vevent, berlin)
        starts = [start for start, _ in dtstart]
        assert len(starts) == 18
        assert dtstart[0][0] == datetime.datetime(2014, 2, 3, 7, 0, tzinfo=berlin)
        assert dtstart[-1][0] == datetime.datetime(2014, 2, 20, 7, 0, tzinfo=berlin)
