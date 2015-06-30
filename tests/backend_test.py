
import pytest
import pytz

from datetime import date, datetime, timedelta
import icalendar

from khal.khalendar import backend
from khal.compat import unicode_type
from khal.khalendar.exceptions import OutdatedDbVersionError, UpdateFailed

from .aux import _get_text

berlin = pytz.timezone('Europe/Berlin')
locale = {'local_timezone': berlin, 'default_timezone': berlin}


def test_new_db_version():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    backend.DB_VERSION += 1
    with pytest.raises(OutdatedDbVersionError):
        dbi._check_table_version()


def test_event_rrule_recurrence_id():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    assert dbi.list() == list()
    events = dbi.get_time_range(datetime(2014, 6, 30, 0, 0), datetime(2014, 7, 26, 0, 0))
    assert list(events) == list()
    dbi.update(_get_text('event_rrule_recuid'), href='12345.ics', etag='abcd')
    assert dbi.list() == [('12345.ics', 'abcd')]
    events = dbi.get_time_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    events = sorted(events, key=lambda x: x.start)
    assert len(events) == 6

    assert events[0].start == berlin.localize(datetime(2014, 6, 30, 7, 0))
    assert events[1].start == berlin.localize(datetime(2014, 7, 7, 9, 0))
    assert events[2].start == berlin.localize(datetime(2014, 7, 14, 7, 0))
    assert events[3].start == berlin.localize(datetime(2014, 7, 21, 7, 0))
    assert events[4].start == berlin.localize(datetime(2014, 7, 28, 7, 0))
    assert events[5].start == berlin.localize(datetime(2014, 8, 4, 7, 0))

    assert dbi

event_rrule_recurrence_id_reverse = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RECURRENCE-ID:20140707T050000Z
DTSTART;TZID=Europe/Berlin:20140707T090000
DTEND;TZID=Europe/Berlin:20140707T140000
END:VEVENT
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;COUNT=6
DTSTART;TZID=Europe/Berlin:20140630T070000
DTEND;TZID=Europe/Berlin:20140630T120000
END:VEVENT
END:VCALENDAR
"""


def test_event_rrule_recurrence_id_reverse():
    """as icalendar elements can be saved in arbitrary order, we also have to
    deal with `reverse` ordered icalendar files
    """
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    assert dbi.list() == list()
    events = dbi.get_time_range(datetime(2014, 6, 30, 0, 0), datetime(2014, 7, 26, 0, 0))
    assert list(events) == list()
    dbi.update(event_rrule_recurrence_id_reverse, href='12345.ics', etag='abcd')
    assert dbi.list() == [('12345.ics', 'abcd')]
    events = dbi.get_time_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    events = sorted(events, key=lambda x: x.start)
    assert len(events) == 6

    assert events[0].start == berlin.localize(datetime(2014, 6, 30, 7, 0))
    assert events[1].start == berlin.localize(datetime(2014, 7, 7, 9, 0))
    assert events[2].start == berlin.localize(datetime(2014, 7, 14, 7, 0))
    assert events[3].start == berlin.localize(datetime(2014, 7, 21, 7, 0))
    assert events[4].start == berlin.localize(datetime(2014, 7, 28, 7, 0))
    assert events[5].start == berlin.localize(datetime(2014, 8, 4, 7, 0))


def test_event_rrule_recurrence_id_update_with_exclude():
    """
    test if updates work as they should. The updated event has the extra
    RECURRENCE-ID event removed and one recurrence date excluded via EXDATE
    """
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    dbi.update(_get_text('event_rrule_recuid'), href='12345.ics', etag='abcd')
    dbi.update(_get_text('event_rrule_recuid_update'), href='12345.ics', etag='abcd')
    events = dbi.get_time_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    events = sorted(events, key=lambda x: x.start)
    assert len(events) == 5
    assert events[0].start == berlin.localize(datetime(2014, 6, 30, 7, 0))
    assert events[1].start == berlin.localize(datetime(2014, 7, 7, 7, 0))
    assert events[2].start == berlin.localize(datetime(2014, 7, 21, 7, 0))
    assert events[3].start == berlin.localize(datetime(2014, 7, 28, 7, 0))
    assert events[4].start == berlin.localize(datetime(2014, 8, 4, 7, 0))


def test_event_delete():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    assert dbi.list() == list()
    events = dbi.get_time_range(datetime(2014, 6, 30, 0, 0), datetime(2014, 7, 26, 0, 0))
    assert list(events) == list()
    dbi.update(event_rrule_recurrence_id_reverse, href='12345.ics', etag='abcd')
    assert dbi.list() == [('12345.ics', 'abcd')]
    events = dbi.get_time_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    assert len(list(events)) == 6
    dbi.delete('12345.ics')
    events = dbi.get_time_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    assert len(list(events)) == 0


event_rrule_this_and_prior = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;UNTIL=20140806T060000Z
DTSTART;TZID=Europe/Berlin:20140630T070000
DTEND;TZID=Europe/Berlin:20140630T120000
END:VEVENT
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RECURRENCE-ID;RANGE=THISANDPRIOR:20140707T050000Z
DTSTART;TZID=Europe/Berlin:20140707T090000
DTEND;TZID=Europe/Berlin:20140707T140000
END:VEVENT
END:VCALENDAR
"""


def test_this_and_prior():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    with pytest.raises(UpdateFailed):
        dbi.update(event_rrule_this_and_prior, href='12345.ics', etag='abcd')

event_rrule_this_and_future_temp = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;UNTIL=20140806T060000Z
DTSTART;TZID=Europe/Berlin:20140630T070000
DTEND;TZID=Europe/Berlin:20140630T120000
END:VEVENT
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit (lang)
RECURRENCE-ID;RANGE=THISANDFUTURE:20140707T050000Z
DTSTART;TZID=Europe/Berlin:{0}
DTEND;TZID=Europe/Berlin:{1}
END:VEVENT
END:VCALENDAR
"""

event_rrule_this_and_future = \
    event_rrule_this_and_future_temp.format('20140707T090000', '20140707T180000')


def test_event_rrule_this_and_future():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    dbi.update(event_rrule_this_and_future, href='12345.ics', etag='abcd')
    assert dbi.list() == [('12345.ics', 'abcd')]
    events = dbi.get_time_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    events = sorted(events, key=lambda x: x.start)
    assert len(events) == 6

    assert events[0].start == berlin.localize(datetime(2014, 6, 30, 7, 0))
    assert events[1].start == berlin.localize(datetime(2014, 7, 7, 9, 0))
    assert events[2].start == berlin.localize(datetime(2014, 7, 14, 9, 0))
    assert events[3].start == berlin.localize(datetime(2014, 7, 21, 9, 0))
    assert events[4].start == berlin.localize(datetime(2014, 7, 28, 9, 0))
    assert events[5].start == berlin.localize(datetime(2014, 8, 4, 9, 0))

    assert events[0].end == berlin.localize(datetime(2014, 6, 30, 12, 0))
    assert events[1].end == berlin.localize(datetime(2014, 7, 7, 18, 0))
    assert events[2].end == berlin.localize(datetime(2014, 7, 14, 18, 0))
    assert events[3].end == berlin.localize(datetime(2014, 7, 21, 18, 0))
    assert events[4].end == berlin.localize(datetime(2014, 7, 28, 18, 0))
    assert events[5].end == berlin.localize(datetime(2014, 8, 4, 18, 0))

    assert unicode_type(events[0].vevent['SUMMARY']) == u'Arbeit'
    for event in events[1:]:
        assert unicode_type(event.vevent['SUMMARY']) == u'Arbeit (lang)'


event_rrule_this_and_future_multi_day_shift = \
    event_rrule_this_and_future_temp.format('20140708T090000', '20140709T150000')


def test_event_rrule_this_and_future_multi_day_shift():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    dbi.update(event_rrule_this_and_future_multi_day_shift, href='12345.ics', etag='abcd')
    assert dbi.list() == [('12345.ics', 'abcd')]
    events = dbi.get_time_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    events = sorted(events, key=lambda x: x.start)
    assert len(events) == 6

    assert events[0].start == berlin.localize(datetime(2014, 6, 30, 7, 0))
    assert events[1].start == berlin.localize(datetime(2014, 7, 8, 9, 0))
    assert events[2].start == berlin.localize(datetime(2014, 7, 15, 9, 0))
    assert events[3].start == berlin.localize(datetime(2014, 7, 22, 9, 0))
    assert events[4].start == berlin.localize(datetime(2014, 7, 29, 9, 0))
    assert events[5].start == berlin.localize(datetime(2014, 8, 5, 9, 0))

    assert events[0].end == berlin.localize(datetime(2014, 6, 30, 12, 0))
    assert events[1].end == berlin.localize(datetime(2014, 7, 9, 15, 0))
    assert events[2].end == berlin.localize(datetime(2014, 7, 16, 15, 0))
    assert events[3].end == berlin.localize(datetime(2014, 7, 23, 15, 0))
    assert events[4].end == berlin.localize(datetime(2014, 7, 30, 15, 0))
    assert events[5].end == berlin.localize(datetime(2014, 8, 6, 15, 0))

    assert unicode_type(events[0].vevent['SUMMARY']) == u'Arbeit'
    for event in events[1:]:
        assert unicode_type(event.vevent['SUMMARY']) == u'Arbeit (lang)'

event_rrule_this_and_future_allday_temp = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event_rrule_recurrence_id_allday
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;UNTIL=20140806
DTSTART;VALUE=DATE:20140630
DTEND;VALUE=DATE:20140701
END:VEVENT
BEGIN:VEVENT
UID:event_rrule_recurrence_id_allday
SUMMARY:Arbeit (lang)
RECURRENCE-ID;RANGE=THISANDFUTURE;VALUE=DATE:20140707
DTSTART;VALUE=DATE:{}
DTEND;VALUE=DATE:{}
END:VEVENT
END:VCALENDAR
"""

event_rrule_this_and_future_allday = \
    event_rrule_this_and_future_allday_temp.format(20140708, 20140709)


def get_allday_range(dbi, start, end):
    """get all events between start and end (inclusive)

    :type start: datetime.date
    :type end: datetime.date
    """
    events = list()
    this_date = start
    while this_date < end:
        events.extend(dbi.get_allday_range(this_date))
        this_date += timedelta(days=1)
    events = sorted(events, key=lambda x: x.start)
    return events


def test_event_rrule_this_and_future_allday():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    dbi.update(event_rrule_this_and_future_allday,
               href='rrule_this_and_future_allday.ics', etag='abcd')
    assert dbi.list() == [('rrule_this_and_future_allday.ics', 'abcd')]
    events = get_allday_range(dbi, date(2014, 4, 30), date(2014, 9, 26))
    assert len(events) == 6

    assert events[0].start == date(2014, 6, 30)
    assert events[1].start == date(2014, 7, 8)
    assert events[2].start == date(2014, 7, 15)
    assert events[3].start == date(2014, 7, 22)
    assert events[4].start == date(2014, 7, 29)
    assert events[5].start == date(2014, 8, 5)

    assert events[0].end == date(2014, 7, 1)
    assert events[1].end == date(2014, 7, 9)
    assert events[2].end == date(2014, 7, 16)
    assert events[3].end == date(2014, 7, 23)
    assert events[4].end == date(2014, 7, 30)
    assert events[5].end == date(2014, 8, 6)

    assert unicode_type(events[0].vevent['SUMMARY']) == u'Arbeit'
    for event in events[1:]:
        assert unicode_type(event.vevent['SUMMARY']) == u'Arbeit (lang)'


def test_event_rrule_this_and_future_allday_prior():
    event_rrule_this_and_future_allday_prior = \
        event_rrule_this_and_future_allday_temp.format(20140705, 20140706)
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    dbi.update(event_rrule_this_and_future_allday_prior,
               href='rrule_this_and_future_allday.ics', etag='abcd')
    assert dbi.list() == [('rrule_this_and_future_allday.ics', 'abcd')]
    events = get_allday_range(dbi, date(2014, 4, 30), date(2014, 9, 26))

    assert len(events) == 6

    assert events[0].start == date(2014, 6, 30)
    assert events[1].start == date(2014, 7, 5)
    assert events[2].start == date(2014, 7, 12)
    assert events[3].start == date(2014, 7, 19)
    assert events[4].start == date(2014, 7, 26)
    assert events[5].start == date(2014, 8, 2)

    assert events[0].end == date(2014, 7, 1)
    assert events[1].end == date(2014, 7, 6)
    assert events[2].end == date(2014, 7, 13)
    assert events[3].end == date(2014, 7, 20)
    assert events[4].end == date(2014, 7, 27)
    assert events[5].end == date(2014, 8, 3)

    assert unicode_type(events[0].vevent['SUMMARY']) == u'Arbeit'
    for event in events[1:]:
        assert unicode_type(event.vevent['SUMMARY']) == u'Arbeit (lang)'


event_rrule_multi_this_and_future_allday = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event_multi_rrule_recurrence_id_allday
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;UNTIL=20140806
DTSTART;VALUE=DATE:20140630
DTEND;VALUE=DATE:20140701
END:VEVENT
BEGIN:VEVENT
UID:event_multi_rrule_recurrence_id_allday
SUMMARY:Arbeit (neu)
RECURRENCE-ID;RANGE=THISANDFUTURE;VALUE=DATE:20140721
DTSTART;VALUE=DATE:20140717
DTEND;VALUE=DATE:20140718
END:VEVENT
BEGIN:VEVENT
UID:event_multi_rrule_recurrence_id_allday
SUMMARY:Arbeit (lang)
RECURRENCE-ID;RANGE=THISANDFUTURE;VALUE=DATE:20140707
DTSTART;VALUE=DATE:20140712
DTEND;VALUE=DATE:20140714
END:VEVENT
END:VCALENDAR"""


def test_event_rrule_multi_this_and_future_allday():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    dbi.update(event_rrule_multi_this_and_future_allday,
               href='event_rrule_multi_this_and_future_allday.ics', etag='abcd')
    assert dbi.list() == [('event_rrule_multi_this_and_future_allday.ics', 'abcd')]
    events = get_allday_range(dbi, start=date(2014, 4, 30), end=date(2014, 9, 26))
    # we are getting two events twice, because they last for two days
    assert len(events) == 8

    assert events[0].start == date(2014, 6, 30)
    assert events[1].start == date(2014, 7, 12)
    assert events[2].start == date(2014, 7, 12)
    assert events[3].start == date(2014, 7, 17)
    assert events[4].start == date(2014, 7, 19)
    assert events[5].start == date(2014, 7, 19)
    assert events[6].start == date(2014, 7, 24)
    assert events[7].start == date(2014, 7, 31)

    assert events[0].end == date(2014, 7, 1)
    assert events[1].end == date(2014, 7, 14)
    assert events[2].end == date(2014, 7, 14)
    assert events[3].end == date(2014, 7, 18)
    assert events[4].end == date(2014, 7, 21)
    assert events[5].end == date(2014, 7, 21)
    assert events[6].end == date(2014, 7, 25)
    assert events[7].end == date(2014, 8, 1)

    assert unicode_type(events[0].vevent['SUMMARY']) == u'Arbeit'
    for event in events[1:3] + events[4:6]:
        assert unicode_type(event.vevent['SUMMARY']) == u'Arbeit (lang)'
    for event in events[3:4] + events[6:]:
        assert unicode_type(event.vevent['SUMMARY']) == u'Arbeit (neu)'


master = """BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;UNTIL=20140806T060000Z
DTSTART;TZID=Europe/Berlin:20140630T070000
DTEND;TZID=Europe/Berlin:20140630T120000
END:VEVENT"""

recuid_this_future = icalendar.Event.from_ical("""BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RECURRENCE-ID;RANGE=THISANDFUTURE:20140707T050000Z
DTSTART;TZID=Europe/Berlin:20140707T090000
DTEND;TZID=Europe/Berlin:20140707T140000
END:VEVENT""")

recuid_this_future_duration = icalendar.Event.from_ical("""BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RECURRENCE-ID;RANGE=THISANDFUTURE:20140707T050000Z
DTSTART;TZID=Europe/Berlin:20140707T090000
DURATION:PT4H30M
END:VEVENT""")


def test_calc_shift_deltas():
    assert (timedelta(hours=2), timedelta(hours=5)) == \
        backend.calc_shift_deltas(recuid_this_future)
    assert (timedelta(hours=2), timedelta(hours=4, minutes=30)) == \
        backend.calc_shift_deltas(recuid_this_future_duration)

event_a = """BEGIN:VEVENT
UID:123
SUMMARY:event a
RRULE:FREQ=WEEKLY;UNTIL=20140806T060000Z
DTSTART;TZID=Europe/Berlin:20140630T070000
DTEND;TZID=Europe/Berlin:20140630T120000
END:VEVENT"""

event_b = """BEGIN:VEVENT
UID:123
SUMMARY:event b
RRULE:FREQ=WEEKLY;UNTIL=20140806T060000Z
DTSTART;TZID=Europe/Berlin:20140630T070000
DTEND;TZID=Europe/Berlin:20140630T120000
END:VEVENT"""


def test_two_calendars_same_uid(tmpdir):
    dbpath = str(tmpdir) + '/khal.db'
    dba = backend.SQLiteDb('home', dbpath, locale=locale)
    dbb = backend.SQLiteDb('work', dbpath, locale=locale)
    assert dba.list() == []
    assert dbb.list() == []
    dba.update(event_a, href='12345.ics', etag='abcd')
    assert dba.list() == [('12345.ics', 'abcd')]
    assert dbb.list() == []
    dbb.update(event_b, href='12345.ics', etag='abcd')
    assert dba.list() == [('12345.ics', 'abcd')]
    assert dbb.list() == [('12345.ics', 'abcd')]
    events_a = list(dba.get_time_range(datetime(2014, 6, 30, 0, 0), datetime(2014, 7, 26, 0, 0)))
    events_b = list(dbb.get_time_range(datetime(2014, 6, 30, 0, 0), datetime(2014, 7, 26, 0, 0)))
    assert len(events_a) == 4
    assert len(events_b) == 4
    dba.delete('12345.ics')
    events_a = list(dba.get_time_range(datetime(2014, 6, 30, 0, 0), datetime(2014, 7, 26, 0, 0)))
    events_b = list(dbb.get_time_range(datetime(2014, 6, 30, 0, 0), datetime(2014, 7, 26, 0, 0)))
    assert len(events_a) == 0
    assert len(events_b) == 4
    assert dba.list() == []
    assert dbb.list() == [('12345.ics', 'abcd')]


def test_update_one_should_not_affect_others(tmpdir):
    """test if an THISANDFUTURE param effects other events as well"""
    dbpath = str(tmpdir) + '/khal.db'
    db = backend.SQLiteDb('home', dbpath, locale=locale)
    db.update(_get_text('event_d'), href='first')
    events = db.get_allday_range(start=date(2015, 4, 9))
    assert len(list(events)) == 1
    db.update(event_rrule_multi_this_and_future_allday, href='second')
    events = db.get_allday_range(start=date(2015, 4, 9))
    assert len(list(events)) == 1


event_rdate_period = """BEGIN:VEVENT
SUMMARY:RDATE period
DTSTART:19961230T020000Z
DTEND:19961230T060000Z
UID:rdate_period
RDATE;VALUE=PERIOD:19970101T180000Z/19970102T070000Z,19970109T180000Z/PT5H30M
END:VEVENT"""


supported_events = [
    event_a, event_b, event_rrule_this_and_future,
    event_rrule_this_and_future_allday,
    event_rrule_this_and_future_multi_day_shift
]


def test_check_support():
    ical = icalendar.Calendar.from_ical(event_rrule_this_and_prior)
    for cal_str in supported_events:
        ical = icalendar.Calendar.from_ical(cal_str)
        [backend.check_support(event, '', '') for event in ical.walk()]

    ical = icalendar.Calendar.from_ical(event_rrule_this_and_prior)
    with pytest.raises(UpdateFailed):
        [backend.check_support(event, '', '') for event in ical.walk()]

    ical = icalendar.Calendar.from_ical(event_rdate_period)
    with pytest.raises(UpdateFailed):
        [backend.check_support(event, '', '') for event in ical.walk()]


card = """BEGIN:VCARD
VERSION:3.0
FN:Unix
BDAY:19710311
END:VCARD
"""

card_no_year = """BEGIN:VCARD
VERSION:3.0
FN:Unix
BDAY:--0311
END:VCARD
"""

card_does_not_parse = """BEGIN:VCARD
VERSION:3.0
FN:Unix
BDAY:x
END:VCARD
"""


def test_birthdays(tmpdir):
    dbpath = str(tmpdir) + '/khal.db'
    db = backend.SQLiteDb_Birthdays('home', dbpath, locale=locale)
    assert list(db.get_allday_range(date(1971, 3, 11))) == list()
    db.update(card, 'unix.vcf')
    events = list(db.get_allday_range(date(1971, 3, 11)))
    assert len(events) == 1
    assert unicode_type(events[0].vevent['SUMMARY']) == u'Unix\'s birthday'


def test_birthdays_no_year(tmpdir):
    dbpath = str(tmpdir) + '/khal.db'
    db = backend.SQLiteDb_Birthdays('home', dbpath, locale=locale)
    assert list(db.get_allday_range(date(1971, 3, 11))) == list()
    db.update(card_no_year, 'unix.vcf')
    events = list(db.get_allday_range(date(1971, 3, 11)))
    assert len(events) == 1
    assert unicode_type(events[0].vevent['SUMMARY']) == u'Unix\'s birthday'


def test_birthday_does_not_parse(tmpdir):
    dbpath = str(tmpdir) + '/khal.db'
    db = backend.SQLiteDb_Birthdays('home', dbpath, locale=locale)
    assert list(db.get_allday_range(date(1971, 3, 11))) == list()
    db.update(card_does_not_parse, 'unix.vcf')
    events = list(db.get_allday_range(date(1971, 3, 11)))
    assert len(events) == 0
