from datetime import date, datetime, timedelta
import icalendar
import pytz

from khal.khalendar import utils

from .utils import _get_text, _get_vevent_file

# FIXME this file is in urgent need of a clean up

BERLIN = pytz.timezone('Europe/Berlin')
BOGOTA = pytz.timezone('America/Bogota')

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
TZNAME:PST
DTSTART:20071104T020000
TZOFFSETTO:-0800
TZOFFSETFROM:-0700
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
BEGIN:DAYLIGHT
TZNAME:PDT
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
new_york = pytz.timezone('America/New_York')


def _get_vevent(event):
    ical = icalendar.Event.from_ical(event)
    for component in ical.walk():
        if component.name == 'VEVENT':
            return component


class TestExpand(object):
    dtstartend_berlin = [
        (berlin.localize(datetime(2013, 3, 1, 14, 0, )),
         berlin.localize(datetime(2013, 3, 1, 16, 0, ))),
        (berlin.localize(datetime(2013, 5, 1, 14, 0, )),
         berlin.localize(datetime(2013, 5, 1, 16, 0, ))),
        (berlin.localize(datetime(2013, 7, 1, 14, 0, )),
         berlin.localize(datetime(2013, 7, 1, 16, 0, ))),
        (berlin.localize(datetime(2013, 9, 1, 14, 0, )),
         berlin.localize(datetime(2013, 9, 1, 16, 0, ))),
        (berlin.localize(datetime(2013, 11, 1, 14, 0,)),
         berlin.localize(datetime(2013, 11, 1, 16, 0,))),
        (berlin.localize(datetime(2014, 1, 1, 14, 0, )),
         berlin.localize(datetime(2014, 1, 1, 16, 0, )))
    ]

    dtstartend_utc = [
        (datetime(2013, 3, 1, 14, 0, tzinfo=pytz.utc),
         datetime(2013, 3, 1, 16, 0, tzinfo=pytz.utc)),
        (datetime(2013, 5, 1, 14, 0, tzinfo=pytz.utc),
         datetime(2013, 5, 1, 16, 0, tzinfo=pytz.utc)),
        (datetime(2013, 7, 1, 14, 0, tzinfo=pytz.utc),
         datetime(2013, 7, 1, 16, 0, tzinfo=pytz.utc)),
        (datetime(2013, 9, 1, 14, 0, tzinfo=pytz.utc),
         datetime(2013, 9, 1, 16, 0, tzinfo=pytz.utc)),
        (datetime(2013, 11, 1, 14, 0, tzinfo=pytz.utc),
         datetime(2013, 11, 1, 16, 0, tzinfo=pytz.utc)),
        (datetime(2014, 1, 1, 14, 0, tzinfo=pytz.utc),
         datetime(2014, 1, 1, 16, 0, tzinfo=pytz.utc))
    ]

    dtstartend_float = [
        (datetime(2013, 3, 1, 14, 0),
         datetime(2013, 3, 1, 16, 0)),
        (datetime(2013, 5, 1, 14, 0),
         datetime(2013, 5, 1, 16, 0)),
        (datetime(2013, 7, 1, 14, 0),
         datetime(2013, 7, 1, 16, 0)),
        (datetime(2013, 9, 1, 14, 0),
         datetime(2013, 9, 1, 16, 0)),
        (datetime(2013, 11, 1, 14, 0),
         datetime(2013, 11, 1, 16, 0)),
        (datetime(2014, 1, 1, 14, 0),
         datetime(2014, 1, 1, 16, 0))
    ]
    dstartend = [
        (date(2013, 3, 1,),
         date(2013, 3, 2,)),
        (date(2013, 5, 1,),
         date(2013, 5, 2,)),
        (date(2013, 7, 1,),
         date(2013, 7, 2,)),
        (date(2013, 9, 1,),
         date(2013, 9, 2,)),
        (date(2013, 11, 1),
         date(2013, 11, 2)),
        (date(2014, 1, 1,),
         date(2014, 1, 2,))
    ]
    offset_berlin = [
        timedelta(0, 3600),
        timedelta(0, 7200),
        timedelta(0, 7200),
        timedelta(0, 7200),
        timedelta(0, 3600),
        timedelta(0, 3600)
    ]

    offset_utc = [
        timedelta(0, 0),
        timedelta(0, 0),
        timedelta(0, 0),
        timedelta(0, 0),
        timedelta(0, 0),
        timedelta(0, 0),
    ]

    offset_none = [None, None, None, None, None, None]

    def test_expand_dt(self):
        vevent = _get_vevent(event_dt)
        dtstart = utils.expand(vevent, berlin)
        assert dtstart == self.dtstartend_berlin
        assert [start.utcoffset()
                for start, _ in dtstart] == self.offset_berlin
        assert [end.utcoffset() for _, end in dtstart] == self.offset_berlin

    def test_expand_dtb(self):
        vevent = _get_vevent(event_dtb)
        dtstart = utils.expand(vevent, berlin)
        assert dtstart == self.dtstartend_berlin
        assert [start.utcoffset()
                for start, _ in dtstart] == self.offset_berlin
        assert [end.utcoffset() for _, end in dtstart] == self.offset_berlin

    def test_expand_dttz(self):
        vevent = _get_vevent(event_dttz)
        dtstart = utils.expand(vevent, berlin)
        assert dtstart == self.dtstartend_utc
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_utc
        assert [end.utcoffset() for _, end in dtstart] == self.offset_utc

    def test_expand_dtf(self):
        vevent = _get_vevent(event_dtf)
        dtstart = utils.expand(vevent, berlin)
        assert dtstart == self.dtstartend_float
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_none
        assert [end.utcoffset() for _, end in dtstart] == self.offset_none

    def test_expand_d(self):
        vevent = _get_vevent(event_d)
        dtstart = utils.expand(vevent, berlin)
        assert dtstart == self.dstartend

    def test_expand_dtz(self):
        vevent = _get_vevent(event_dtz)
        dtstart = utils.expand(vevent, berlin)
        assert dtstart == self.dstartend

    def test_expand_dtzb(self):
        vevent = _get_vevent(event_dtzb)
        dtstart = utils.expand(vevent, berlin)
        assert dtstart == self.dstartend

    def test_expand_invalid_exdate(self):
        """testing if we can expand an event with EXDATEs that do not much
        its RRULE"""
        vevent = _get_vevent_file('event_invalid_exdate')
        dtstartl = utils.expand(vevent, berlin)
        # TODO test for logging message
        assert dtstartl == [
            (new_york.localize(datetime(2011, 11, 12, 15, 50)),
             new_york.localize(datetime(2011, 11, 12, 17, 0))),
            (new_york.localize(datetime(2011, 11, 19, 15, 50)),
             new_york.localize(datetime(2011, 11, 19, 17, 0))),
            (new_york.localize(datetime(2011, 12, 3, 15, 50)),
             new_york.localize(datetime(2011, 12, 3, 17, 0))),
        ]


class TestExpandNoRR(object):
    dtstartend_berlin = [
        (berlin.localize(datetime(2013, 3, 1, 14, 0)),
         berlin.localize(datetime(2013, 3, 1, 16, 0))),
    ]

    dtstartend_utc = [
        (datetime(2013, 3, 1, 14, 0, tzinfo=pytz.utc),
         datetime(2013, 3, 1, 16, 0, tzinfo=pytz.utc)),
    ]

    dtstartend_float = [
        (datetime(2013, 3, 1, 14, 0),
         datetime(2013, 3, 1, 16, 0)),
    ]
    offset_berlin = [
        timedelta(0, 3600),
    ]

    offset_utc = [
        timedelta(0, 0),
    ]

    offset_none = [None]

    def test_expand_dt(self):
        vevent = _get_vevent(event_dt_norr)
        dtstart = utils.expand(vevent, berlin)
        assert dtstart == self.dtstartend_berlin
        assert [start.utcoffset()
                for start, _ in dtstart] == self.offset_berlin
        assert [end.utcoffset() for _, end in dtstart] == self.offset_berlin

    def test_expand_dtb(self):
        vevent = _get_vevent(event_dtb_norr)
        dtstart = utils.expand(vevent, berlin)
        assert dtstart == self.dtstartend_berlin
        assert [start.utcoffset()
                for start, _ in dtstart] == self.offset_berlin
        assert [end.utcoffset() for _, end in dtstart] == self.offset_berlin

    def test_expand_dttz(self):
        vevent = _get_vevent(event_dttz_norr)
        dtstart = utils.expand(vevent, berlin)
        assert dtstart == self.dtstartend_utc
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_utc
        assert [end.utcoffset() for _, end in dtstart] == self.offset_utc

    def test_expand_dtf(self):
        vevent = _get_vevent(event_dtf_norr)
        dtstart = utils.expand(vevent, berlin)
        assert dtstart == self.dtstartend_float
        assert [start.utcoffset() for start, _ in dtstart] == self.offset_none
        assert [end.utcoffset() for _, end in dtstart] == self.offset_none

    def test_expand_d(self):
        vevent = _get_vevent(event_d_norr)
        dtstart = utils.expand(vevent, berlin)
        assert dtstart == [
            (date(2013, 3, 1,),
             date(2013, 3, 2,)),
        ]

    def test_expand_dtr_exdatez(self):
        """a recurring event with an EXDATE in Zulu time while DTSTART is
        localized"""
        vevent = _get_vevent_file('event_dtr_exdatez')
        dtstart = utils.expand(vevent, berlin)
        assert len(dtstart) == 3

    def test_expand_rrule_exdate_z(self):
        """event with not understood timezone for dtstart and zulu time form
        exdate
        """
        vevent = _get_vevent_file('event_dtr_no_tz_exdatez')
        vevent = utils.sanitize(vevent, berlin, '', '')
        dtstart = utils.expand(vevent, berlin)
        assert len(dtstart) == 5
        dtstarts = [start for start, end in dtstart]
        assert dtstarts == [
            berlin.localize(datetime(2012, 4, 3, 10, 0)),
            berlin.localize(datetime(2012, 5, 3, 10, 0)),
            berlin.localize(datetime(2012, 7, 3, 10, 0)),
            berlin.localize(datetime(2012, 8, 3, 10, 0)),
            berlin.localize(datetime(2012, 9, 3, 10, 0)),
        ]

    def test_expand_rrule_notz_until_z(self):
        """event with not understood timezone for dtstart and zulu time form
        exdate
        """
        vevent = _get_vevent_file('event_dtr_notz_untilz')
        vevent = utils.sanitize(vevent, new_york, '', '')
        dtstart = utils.expand(vevent, new_york)
        assert len(dtstart) == 7
        dtstarts = [start for start, end in dtstart]
        assert dtstarts == [
            new_york.localize(datetime(2012, 7, 26, 13, 0)),
            new_york.localize(datetime(2012, 8, 9, 13, 0)),
            new_york.localize(datetime(2012, 8, 23, 13, 0)),
            new_york.localize(datetime(2012, 9, 6, 13, 0)),
            new_york.localize(datetime(2012, 9, 20, 13, 0)),
            new_york.localize(datetime(2012, 10, 4, 13, 0)),
            new_york.localize(datetime(2012, 10, 18, 13, 0)),
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
RRULE:FREQ=DAILY;UNTIL=20140220T070000;WKST=SU
END:VEVENT
"""

event_until_d_notz = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:d470ef6d08
DTSTART;VALUE=DATE:20140110
DURATION:P1D
RRULE:FREQ=WEEKLY;UNTIL=20140215;INTERVAL=1;BYDAY=FR
SUMMARY:Fri
END:VEVENT
END:VCALENDAR
"""

event_exdate_dt = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:event_exdate_dt123
DTSTAMP:20140627T162546Z
DTSTART;TZID=Europe/Berlin:20140702T190000
DTEND;TZID=Europe/Berlin:20140702T193000
SUMMARY:Test event
RRULE:FREQ=DAILY;COUNT=10
EXDATE:20140703T190000
END:VEVENT
END:VCALENDAR
"""

event_exdates_dt = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:event_exdates_dt123
DTSTAMP:20140627T162546Z
DTSTART;TZID=Europe/Berlin:20140702T190000
DTEND;TZID=Europe/Berlin:20140702T193000
SUMMARY:Test event
RRULE:FREQ=DAILY;COUNT=10
EXDATE:20140703T190000
EXDATE:20140705T190000
END:VEVENT
END:VCALENDAR
"""

event_exdatesl_dt = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:event_exdatesl_dt123
DTSTAMP:20140627T162546Z
DTSTART;TZID=Europe/Berlin:20140702T190000
DTEND;TZID=Europe/Berlin:20140702T193000
SUMMARY:Test event
RRULE:FREQ=DAILY;COUNT=10
EXDATE:20140703T190000
EXDATE:20140705T190000,20140707T190000
END:VEVENT
END:VCALENDAR
"""

latest_bug = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Reformationstag
RRULE:FREQ=YEARLY;BYMONTHDAY=31;BYMONTH=10
DTSTART;VALUE=DATE:20091031
DTEND;VALUE=DATE:20091101
END:VEVENT
END:VCALENDAR
"""

recurrence_id_with_timezone = """BEGIN:VEVENT
SUMMARY:PyCologne
DTSTART;TZID=/freeassociation.sourceforge.net/Tzfile/Europe/Berlin:20131113T190000
DTEND;TZID=/freeassociation.sourceforge.net/Tzfile/Europe/Berlin:20131113T210000
DTSTAMP:20130610T160635Z
UID:another_problem
RECURRENCE-ID;TZID=/freeassociation.sourceforge.net/Tzfile/Europe/Berlin:20131113T190000
RRULE:FREQ=MONTHLY;BYDAY=2WE;WKST=SU
TRANSP:OPAQUE
END:VEVENT
"""


class TestSpecial(object):
    """collection of strange test cases that don't fit anywhere else really"""

    def test_count(self):
        vevent = _get_vevent(vevent_count)
        dtstart = utils.expand(vevent, berlin)
        starts = [start for start, _ in dtstart]
        assert len(starts) == 18
        assert dtstart[0][0] == datetime(2014, 2, 3, 7, 0)
        assert dtstart[-1][0] == datetime(2014, 2, 20, 7, 0)

    def test_until_notz(self):
        vevent = _get_vevent(vevent_until_notz)
        dtstart = utils.expand(vevent, berlin)
        starts = [start for start, _ in dtstart]
        assert len(starts) == 18
        assert dtstart[0][0] == berlin.localize(
            datetime(2014, 2, 3, 7, 0))
        assert dtstart[-1][0] == berlin.localize(
            datetime(2014, 2, 20, 7, 0))

    def test_until_d_notz(self):
        vevent = _get_vevent(event_until_d_notz)
        dtstart = utils.expand(vevent, berlin)
        starts = [start for start, _ in dtstart]
        assert len(starts) == 6
        assert dtstart[0][0] == date(2014, 1, 10)
        assert dtstart[-1][0] == date(2014, 2, 14)

    def test_latest_bug(self):
        vevent = _get_vevent(latest_bug)
        dtstart = utils.expand(vevent, berlin)
        assert dtstart[0][0] == date(2009, 10, 31)
        assert dtstart[-1][0] == date(2037, 10, 31)

    def test_recurrence_id_with_timezone(self):
        vevent = _get_vevent(recurrence_id_with_timezone)
        dtstart = utils.expand(vevent, berlin)
        assert len(dtstart) == 1
        assert dtstart[0][0] == berlin.localize(
            datetime(2013, 11, 13, 19, 0))

    def test_event_exdate_dt(self):
        """recurring event, one date excluded via EXCLUDE"""
        vevent = _get_vevent(event_exdate_dt)
        dtstart = utils.expand(vevent, berlin)
        assert len(dtstart) == 9
        assert dtstart[0][0] == berlin.localize(
            datetime(2014, 7, 2, 19, 0))
        assert dtstart[-1][0] == berlin.localize(
            datetime(2014, 7, 11, 19, 0))

    def test_event_exdates_dt(self):
        """recurring event, two dates excluded via EXCLUDE"""
        vevent = _get_vevent(event_exdates_dt)
        dtstart = utils.expand(vevent, berlin)
        assert len(dtstart) == 8
        assert dtstart[0][0] == berlin.localize(
            datetime(2014, 7, 2, 19, 0))
        assert dtstart[-1][0] == berlin.localize(
            datetime(2014, 7, 11, 19, 0))

    def test_event_exdatesl_dt(self):
        """recurring event, three dates exclude via two EXCLUDEs"""
        vevent = _get_vevent(event_exdatesl_dt)
        dtstart = utils.expand(vevent, berlin)
        assert len(dtstart) == 7
        assert dtstart[0][0] == berlin.localize(
            datetime(2014, 7, 2, 19, 0))
        assert dtstart[-1][0] == berlin.localize(
            datetime(2014, 7, 11, 19, 0))

    def test_event_exdates_remove(self):
        """check if we can remove one more instance"""
        vevent = _get_vevent(event_exdatesl_dt)
        dtstart = utils.expand(vevent, berlin)
        assert len(dtstart) == 7

        exdate1 = pytz.UTC.localize(datetime(2014, 7, 11, 17, 0))
        utils.delete_instance(vevent, exdate1)
        dtstart = utils.expand(vevent, berlin)
        assert len(dtstart) == 6

        exdate2 = berlin.localize(datetime(2014, 7, 9, 19, 0))
        utils.delete_instance(vevent, exdate2)
        dtstart = utils.expand(vevent, berlin)
        assert len(dtstart) == 5

    def test_event_dt_rrule_invalid_until(self):
        """DTSTART and RRULE:UNTIL should be of the same type, but might not
        be"""
        vevent = _get_vevent(_get_text('event_dt_rrule_invalid_until'))
        dtstart = utils.expand(vevent, berlin)
        assert dtstart == [(date(2007, 12, 1), date(2007, 12, 2)),
                           (date(2008, 1, 1), date(2008, 1, 2)),
                           (date(2008, 2, 1), date(2008, 2, 2))]

    def test_event_dt_rrule_invalid_until2(self):
        """same as above, but now dtstart is of type date and until is datetime
        """
        vevent = _get_vevent(_get_text('event_dt_rrule_invalid_until2'))
        dtstart = utils.expand(vevent, berlin)
        assert len(dtstart) == 35
        assert dtstart[0] == (berlin.localize(datetime(2014, 4, 9, 9, 30)),
                              berlin.localize(datetime(2014, 4, 9, 10, 30)))
        assert dtstart[-1] == (berlin.localize(datetime(2014, 12, 3, 9, 30)),
                               berlin.localize(datetime(2014, 12, 3, 10, 30)))


simple_rdate = """BEGIN:VEVENT
SUMMARY:Simple Rdate
DTSTART;TZID=Europe/Berlin:20131113T190000
DTEND;TZID=Europe/Berlin:20131113T210000
UID:simple_rdate
RDATE:20131213T190000
RDATE:20140113T190000,20140213T190000
END:VEVENT
"""

rrule_and_rdate = """BEGIN:VEVENT
SUMMARY:Datetime Event
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20130301T140000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20130301T160000
RRULE:FREQ=MONTHLY;INTERVAL=2;COUNT=6
RDATE:20131213T190000
UID:datetime123
END:VEVENT"""


class TestRDate(object):
    """Testing expanding of recurrence rules"""
    def test_simple_rdate(self):
        vevent = _get_vevent(simple_rdate)
        dtstart = utils.expand(vevent, berlin)
        assert len(dtstart) == 4

    def test_rrule_and_rdate(self):
        vevent = _get_vevent(rrule_and_rdate)
        dtstart = utils.expand(vevent, berlin)
        assert len(dtstart) == 7

    def test_rrule_past(self):
        vevent = _get_vevent_file('event_r_past')
        assert vevent is not None
        dtstarts = utils.expand(vevent, berlin)
        assert len(dtstarts) == 73
        assert dtstarts[0][0] == date(1965, 4, 23)
        assert dtstarts[-1][0] == date(2037, 4, 23)

    def test_rdate_date(self):
        vevent = _get_vevent_file('event_d_rdate')
        dtstarts = utils.expand(vevent, berlin)
        assert len(dtstarts) == 4
        assert dtstarts == [(date(2015, 8, 12), date(2015, 8, 13)),
                            (date(2015, 8, 13), date(2015, 8, 14)),
                            (date(2015, 8, 14), date(2015, 8, 15)),
                            (date(2015, 8, 15), date(2015, 8, 16))]


noend_date = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:noend123
DTSTART;VALUE=DATE:20140829
SUMMARY:No DTEND
END:VEVENT
END:VCALENDAR
"""

noend_datetime = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:noend123
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140829T080000
SUMMARY:No DTEND
END:VEVENT
END:VCALENDAR
"""

instant = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:instant123
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20170113T010000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20170113T010000
SUMMARY:Really fast event
END:VEVENT
END:VCALENDAR
"""


class TestSanitize(object):

    def test_noend_date(self):
        vevent = _get_vevent(noend_date)
        vevent = utils.sanitize(vevent, berlin, '', '')
        assert vevent['DTSTART'].dt == date(2014, 8, 29)
        assert vevent['DTEND'].dt == date(2014, 8, 30)

    def test_noend_datetime(self):
        vevent = _get_vevent(noend_datetime)
        vevent = utils.sanitize(vevent, berlin, '', '')
        assert vevent['DTSTART'].dt == date(2014, 8, 29)
        assert vevent['DTEND'].dt == date(2014, 8, 30)

    def test_duration(self):
        vevent = _get_vevent_file('event_dtr_exdatez')
        vevent = utils.sanitize(vevent, berlin, '', '')

    def test_instant(self):
        vevent = _get_vevent(instant)
        assert vevent['DTEND'].dt - vevent['DTSTART'].dt == timedelta()
        vevent = utils.sanitize(vevent, berlin, '', '')
        assert vevent['DTEND'].dt - vevent['DTSTART'].dt == timedelta(hours=1)


class TestIsAware():
    def test_naive(self):
        assert utils.is_aware(datetime.now()) is False

    def test_berlin(self):
        assert utils.is_aware(BERLIN.localize(datetime.now())) is True

    def test_bogota(self):
        assert utils.is_aware(BOGOTA.localize(datetime.now())) is True

    def test_utc(self):
        assert utils.is_aware(pytz.UTC.localize(datetime.now())) is True
