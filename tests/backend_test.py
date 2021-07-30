import datetime as dt
from operator import itemgetter

import icalendar
import pkg_resources
import pytest
from khal.khalendar import backend
from khal.khalendar.exceptions import OutdatedDbVersionError, UpdateFailed

from .utils import BERLIN, LOCALE_BERLIN, _get_text

calname = 'home'


def test_new_db_version():
    dbi = backend.SQLiteDb(calname, ':memory:', locale=LOCALE_BERLIN)
    backend.DB_VERSION += 1
    with pytest.raises(OutdatedDbVersionError):
        dbi._check_table_version()


def test_event_rrule_recurrence_id():
    dbi = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    assert dbi.list(calname) == []
    events = dbi.get_localized(
        BERLIN.localize(dt.datetime(2014, 6, 30, 0, 0)),
        BERLIN.localize(dt.datetime(2014, 8, 26, 0, 0)),
    )
    assert list(events) == []
    dbi.update(_get_text('event_rrule_recuid'), href='12345.ics', etag='abcd', calendar=calname)
    assert dbi.list(calname) == [('12345.ics', 'abcd')]
    events = dbi.get_localized(
        BERLIN.localize(dt.datetime(2014, 6, 30, 0, 0)),
        BERLIN.localize(dt.datetime(2014, 8, 26, 0, 0)),
    )
    events = sorted(events, key=itemgetter(2))
    assert len(events) == 6

    # start
    assert events[0][2] == BERLIN.localize(dt.datetime(2014, 6, 30, 7, 0))
    assert events[1][2] == BERLIN.localize(dt.datetime(2014, 7, 7, 9, 0))
    assert events[2][2] == BERLIN.localize(dt.datetime(2014, 7, 14, 7, 0))
    assert events[3][2] == BERLIN.localize(dt.datetime(2014, 7, 21, 7, 0))
    assert events[4][2] == BERLIN.localize(dt.datetime(2014, 7, 28, 7, 0))
    assert events[5][2] == BERLIN.localize(dt.datetime(2014, 8, 4, 7, 0))

    calendars = dbi.get_localized_calendars(
        BERLIN.localize(dt.datetime(2014, 6, 30, 0, 0)),
        BERLIN.localize(dt.datetime(2014, 8, 26, 0, 0)),
    )
    calendars = list(calendars)
    assert len(calendars) == 6


def test_event_rrule_recurrence_id_invalid_tzid():
    dbi = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    dbi.update(_get_text('event_rrule_recuid_invalid_tzid'), href='12345.ics', etag='abcd',
               calendar=calname)
    events = dbi.get_localized(
        BERLIN.localize(dt.datetime(2014, 4, 30, 0, 0)),
        BERLIN.localize(dt.datetime(2014, 9, 26, 0, 0)))
    events = sorted(events, key=itemgetter(2))
    assert len(events) == 6

    assert events[0][2] == BERLIN.localize(dt.datetime(2014, 6, 30, 7, 0))
    assert events[1][2] == BERLIN.localize(dt.datetime(2014, 7, 7, 9, 0))
    assert events[2][2] == BERLIN.localize(dt.datetime(2014, 7, 14, 7, 0))
    assert events[3][2] == BERLIN.localize(dt.datetime(2014, 7, 21, 7, 0))
    assert events[4][2] == BERLIN.localize(dt.datetime(2014, 7, 28, 7, 0))
    assert events[5][2] == BERLIN.localize(dt.datetime(2014, 8, 4, 7, 0))


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
    dbi = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    assert dbi.list(calname) == []
    events = dbi.get_localized(
        BERLIN.localize(dt.datetime(2014, 6, 30, 0, 0)),
        BERLIN.localize(dt.datetime(2014, 8, 26, 0, 0)))
    assert list(events) == []
    dbi.update(event_rrule_recurrence_id_reverse, href='12345.ics', etag='abcd', calendar=calname)
    assert dbi.list(calname) == [('12345.ics', 'abcd')]
    events = dbi.get_localized(
        BERLIN.localize(dt.datetime(2014, 6, 30, 0, 0)),
        BERLIN.localize(dt.datetime(2014, 8, 26, 0, 0)))
    events = sorted(events, key=itemgetter(2))
    assert len(events) == 6

    assert events[0][2] == BERLIN.localize(dt.datetime(2014, 6, 30, 7, 0))
    assert events[1][2] == BERLIN.localize(dt.datetime(2014, 7, 7, 9, 0))
    assert events[2][2] == BERLIN.localize(dt.datetime(2014, 7, 14, 7, 0))
    assert events[3][2] == BERLIN.localize(dt.datetime(2014, 7, 21, 7, 0))
    assert events[4][2] == BERLIN.localize(dt.datetime(2014, 7, 28, 7, 0))
    assert events[5][2] == BERLIN.localize(dt.datetime(2014, 8, 4, 7, 0))


def test_event_rrule_recurrence_id_update_with_exclude():
    """
    test if updates work as they should. The updated event has the extra
    RECURRENCE-ID event removed and one recurrence date excluded via EXDATE
    """
    dbi = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    dbi.update(_get_text('event_rrule_recuid'), href='12345.ics', etag='abcd', calendar=calname)
    dbi.update(_get_text('event_rrule_recuid_update'),
               href='12345.ics', etag='abcd', calendar=calname)
    events = dbi.get_localized(BERLIN.localize(dt.datetime(2014, 4, 30, 0, 0)),
                               BERLIN.localize(dt.datetime(2014, 9, 26, 0, 0)))
    events = sorted(events, key=itemgetter(2))
    assert len(events) == 5
    assert events[0][2] == BERLIN.localize(dt.datetime(2014, 6, 30, 7, 0))
    assert events[1][2] == BERLIN.localize(dt.datetime(2014, 7, 7, 7, 0))
    assert events[2][2] == BERLIN.localize(dt.datetime(2014, 7, 21, 7, 0))
    assert events[3][2] == BERLIN.localize(dt.datetime(2014, 7, 28, 7, 0))
    assert events[4][2] == BERLIN.localize(dt.datetime(2014, 8, 4, 7, 0))


def test_event_recuid_no_master():
    """
    test for events which have a RECUID component, but the master event is
    not present in the same file
    """
    dbi = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    dbi.update(_get_text('event_dt_recuid_no_master'),
               href='12345.ics', etag='abcd', calendar=calname)
    events = dbi.get_floating(
        dt.datetime(2017, 3, 1, 0, 0), dt.datetime(2017, 4, 1, 0, 0),
    )
    events = sorted(events, key=itemgetter(2))
    assert len(events) == 1
    assert events[0][2] == dt.datetime(2017, 3, 29, 16)
    assert events[0][3] == dt.datetime(2017, 3, 29, 16, 25)
    assert 'SUMMARY:Infrastructure Planning' in events[0][0]


def test_event_recuid_rrule_no_master():
    """
    test for events which have a RECUID and a RRULE component, but the master event is
    not present in the same file
    """
    dbi = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    dbi.update(
        _get_text('event_dt_multi_recuid_no_master'),
        href='12345.ics', etag='abcd', calendar=calname,
    )
    events = dbi.get_floating(
        dt.datetime(2010, 1, 1, 0, 0), dt.datetime(2020, 1, 1, 0, 0),
    )
    events = sorted(events, key=itemgetter(2))
    assert len(list(events)) == 2
    assert events[0][2] == dt.datetime(2014, 6, 30, 7, 30)
    assert events[0][3] == dt.datetime(2014, 6, 30, 12, 0)
    assert events[1][2] == dt.datetime(2014, 7, 7, 8, 30)
    assert events[1][3] == dt.datetime(2014, 7, 7, 12, 0)
    events = dbi.search('VEVENT')
    assert len(list(events)) == 2


def test_no_valid_timezone():
    dbi = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    dbi.update(_get_text('event_dt_local_missing_tz'),
               href='12345.ics', etag='abcd', calendar=calname)
    events = dbi.get_localized(BERLIN.localize(dt.datetime(2014, 4, 9, 0, 0)),
                               BERLIN.localize(dt.datetime(2014, 4, 10, 0, 0)))
    events = sorted(events)
    assert len(events) == 1
    event = events[0]
    assert event[2] == BERLIN.localize(dt.datetime(2014, 4, 9, 9, 30))
    assert event[3] == BERLIN.localize(dt.datetime(2014, 4, 9, 10, 30))


def test_event_delete():
    dbi = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    assert dbi.list(calname) == []
    events = dbi.get_localized(BERLIN.localize(dt.datetime(2014, 6, 30, 0, 0)),
                               BERLIN.localize(dt.datetime(2014, 8, 26, 0, 0)))
    assert list(events) == []
    dbi.update(event_rrule_recurrence_id_reverse, href='12345.ics', etag='abcd', calendar=calname)
    assert dbi.list(calname) == [('12345.ics', 'abcd')]
    events = dbi.get_localized(BERLIN.localize(dt.datetime(2014, 6, 30, 0, 0)),
                               BERLIN.localize(dt.datetime(2014, 9, 26, 0, 0)))
    assert len(list(events)) == 6
    dbi.delete('12345.ics', calendar=calname)
    events = dbi.get_localized(BERLIN.localize(dt.datetime(2014, 6, 30, 0, 0)),
                               BERLIN.localize(dt.datetime(2014, 9, 26, 0, 0)))
    assert len(list(events)) == 0


event_rrule_this_and_prior = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event_rrule_recurrence_id_this_and_prior
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;UNTIL=20140806T060000Z
DTSTART;TZID=Europe/Berlin:20140630T070000
DTEND;TZID=Europe/Berlin:20140630T120000
END:VEVENT
BEGIN:VEVENT
UID:event_rrule_recurrence_id_this_and_prior
SUMMARY:Arbeit
RECURRENCE-ID;RANGE=THISANDPRIOR:20140707T050000Z
DTSTART;TZID=Europe/Berlin:20140707T090000
DTEND;TZID=Europe/Berlin:20140707T140000
END:VEVENT
END:VCALENDAR
"""


def test_this_and_prior():
    """we do not support THISANDPRIOR, therefore this should fail"""
    dbi = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    with pytest.raises(UpdateFailed):
        dbi.update(event_rrule_this_and_prior, href='12345.ics', etag='abcd', calendar=calname)


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
    dbi = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    dbi.update(event_rrule_this_and_future, href='12345.ics', etag='abcd', calendar=calname)
    assert dbi.list(calname) == [('12345.ics', 'abcd')]
    events = dbi.get_localized(BERLIN.localize(dt.datetime(2014, 4, 30, 0, 0)),
                               BERLIN.localize(dt.datetime(2014, 9, 26, 0, 0)))
    events = sorted(events, key=itemgetter(2))
    assert len(events) == 6

    assert events[0][2] == BERLIN.localize(dt.datetime(2014, 6, 30, 7, 0))
    assert events[1][2] == BERLIN.localize(dt.datetime(2014, 7, 7, 9, 0))
    assert events[2][2] == BERLIN.localize(dt.datetime(2014, 7, 14, 9, 0))
    assert events[3][2] == BERLIN.localize(dt.datetime(2014, 7, 21, 9, 0))
    assert events[4][2] == BERLIN.localize(dt.datetime(2014, 7, 28, 9, 0))
    assert events[5][2] == BERLIN.localize(dt.datetime(2014, 8, 4, 9, 0))

    assert events[0][3] == BERLIN.localize(dt.datetime(2014, 6, 30, 12, 0))
    assert events[1][3] == BERLIN.localize(dt.datetime(2014, 7, 7, 18, 0))
    assert events[2][3] == BERLIN.localize(dt.datetime(2014, 7, 14, 18, 0))
    assert events[3][3] == BERLIN.localize(dt.datetime(2014, 7, 21, 18, 0))
    assert events[4][3] == BERLIN.localize(dt.datetime(2014, 7, 28, 18, 0))
    assert events[5][3] == BERLIN.localize(dt.datetime(2014, 8, 4, 18, 0))

    assert 'SUMMARY:Arbeit\n' in events[0][0]
    for _num, event in enumerate(events[1:]):
        assert 'SUMMARY:Arbeit (lang)\n' in event[0]


event_rrule_this_and_future_multi_day_shift = \
    event_rrule_this_and_future_temp.format('20140708T090000', '20140709T150000')


def test_event_rrule_this_and_future_multi_day_shift():
    dbi = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    dbi.update(event_rrule_this_and_future_multi_day_shift,
               href='12345.ics', etag='abcd', calendar=calname)
    assert dbi.list(calname) == [('12345.ics', 'abcd')]
    events = dbi.get_localized(BERLIN.localize(dt.datetime(2014, 4, 30, 0, 0)),
                               BERLIN.localize(dt.datetime(2014, 9, 26, 0, 0)))
    events = sorted(events, key=itemgetter(2))
    assert len(events) == 6

    assert events[0][2] == BERLIN.localize(dt.datetime(2014, 6, 30, 7, 0))
    assert events[1][2] == BERLIN.localize(dt.datetime(2014, 7, 8, 9, 0))
    assert events[2][2] == BERLIN.localize(dt.datetime(2014, 7, 15, 9, 0))
    assert events[3][2] == BERLIN.localize(dt.datetime(2014, 7, 22, 9, 0))
    assert events[4][2] == BERLIN.localize(dt.datetime(2014, 7, 29, 9, 0))
    assert events[5][2] == BERLIN.localize(dt.datetime(2014, 8, 5, 9, 0))

    assert events[0][3] == BERLIN.localize(dt.datetime(2014, 6, 30, 12, 0))
    assert events[1][3] == BERLIN.localize(dt.datetime(2014, 7, 9, 15, 0))
    assert events[2][3] == BERLIN.localize(dt.datetime(2014, 7, 16, 15, 0))
    assert events[3][3] == BERLIN.localize(dt.datetime(2014, 7, 23, 15, 0))
    assert events[4][3] == BERLIN.localize(dt.datetime(2014, 7, 30, 15, 0))
    assert events[5][3] == BERLIN.localize(dt.datetime(2014, 8, 6, 15, 0))

    assert 'SUMMARY:Arbeit\n' in events[0][0]
    for event in events[1:]:
        assert 'SUMMARY:Arbeit (lang)\n' in event[0]


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


def test_event_rrule_this_and_future_allday():
    dbi = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    dbi.update(event_rrule_this_and_future_allday,
               href='rrule_this_and_future_allday.ics', etag='abcd', calendar=calname)
    assert dbi.list(calname) == [('rrule_this_and_future_allday.ics', 'abcd')]
    events = list(dbi.get_floating(dt.datetime(2014, 4, 30, 0, 0), dt.datetime(2014, 9, 27, 0, 0)))
    assert len(events) == 6

    assert events[0][2] == dt.date(2014, 6, 30)
    assert events[1][2] == dt.date(2014, 7, 8)
    assert events[2][2] == dt.date(2014, 7, 15)
    assert events[3][2] == dt.date(2014, 7, 22)
    assert events[4][2] == dt.date(2014, 7, 29)
    assert events[5][2] == dt.date(2014, 8, 5)

    assert events[0][3] == dt.date(2014, 7, 1)
    assert events[1][3] == dt.date(2014, 7, 9)
    assert events[2][3] == dt.date(2014, 7, 16)
    assert events[3][3] == dt.date(2014, 7, 23)
    assert events[4][3] == dt.date(2014, 7, 30)
    assert events[5][3] == dt.date(2014, 8, 6)

    assert 'SUMMARY:Arbeit\n' in events[0][0]
    for event in events[1:]:
        assert 'SUMMARY:Arbeit (lang)\n' in event[0]


def test_event_rrule_this_and_future_allday_prior():
    event_rrule_this_and_future_allday_prior = \
        event_rrule_this_and_future_allday_temp.format(20140705, 20140706)
    dbi = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    dbi.update(event_rrule_this_and_future_allday_prior,
               href='rrule_this_and_future_allday.ics', etag='abcd', calendar=calname)
    assert dbi.list(calname) == [('rrule_this_and_future_allday.ics', 'abcd')]
    events = list(dbi.get_floating(dt.datetime(2014, 4, 30, 0, 0), dt.datetime(2014, 9, 27, 0, 0)))

    assert len(events) == 6

    assert events[0][2] == dt.date(2014, 6, 30)
    assert events[1][2] == dt.date(2014, 7, 5)
    assert events[2][2] == dt.date(2014, 7, 12)
    assert events[3][2] == dt.date(2014, 7, 19)
    assert events[4][2] == dt.date(2014, 7, 26)
    assert events[5][2] == dt.date(2014, 8, 2)

    assert events[0][3] == dt.date(2014, 7, 1)
    assert events[1][3] == dt.date(2014, 7, 6)
    assert events[2][3] == dt.date(2014, 7, 13)
    assert events[3][3] == dt.date(2014, 7, 20)
    assert events[4][3] == dt.date(2014, 7, 27)
    assert events[5][3] == dt.date(2014, 8, 3)

    assert 'SUMMARY:Arbeit\n' in events[0][0]
    for event in events[1:]:
        assert 'SUMMARY:Arbeit (lang)\n' in event[0]


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
    dbi = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    dbi.update(event_rrule_multi_this_and_future_allday,
               href='event_rrule_multi_this_and_future_allday.ics', etag='abcd', calendar=calname)
    assert dbi.list(calname) == [('event_rrule_multi_this_and_future_allday.ics', 'abcd')]
    events = sorted(
        dbi.get_floating(dt.datetime(2014, 4, 30, 0, 0), dt.datetime(2014, 9, 27, 0, 0)),
    )
    assert len(events) == 6

    assert events[0][2] == dt.date(2014, 6, 30)
    assert events[1][2] == dt.date(2014, 7, 12)
    assert events[2][2] == dt.date(2014, 7, 17)
    assert events[3][2] == dt.date(2014, 7, 19)
    assert events[4][2] == dt.date(2014, 7, 24)
    assert events[5][2] == dt.date(2014, 7, 31)

    assert events[0][3] == dt.date(2014, 7, 1)
    assert events[1][3] == dt.date(2014, 7, 14)
    assert events[2][3] == dt.date(2014, 7, 18)
    assert events[3][3] == dt.date(2014, 7, 21)
    assert events[4][3] == dt.date(2014, 7, 25)
    assert events[5][3] == dt.date(2014, 8, 1)

    assert 'SUMMARY:Arbeit\n' in events[0][0]
    for event in [events[1], events[3]]:
        assert 'SUMMARY:Arbeit (lang)\n' in event[0]
    for event in [events[2], events[4], events[5]]:
        assert 'SUMMARY:Arbeit (neu)\n' in event[0]


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
    assert (dt.timedelta(hours=2), dt.timedelta(hours=5)) == \
        backend.calc_shift_deltas(recuid_this_future)
    assert (dt.timedelta(hours=2), dt.timedelta(hours=4, minutes=30)) == \
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


def test_two_calendars_same_uid():
    home = 'home'
    work = 'work'
    dbi = backend.SQLiteDb([home, work], ':memory:', locale=LOCALE_BERLIN)
    assert dbi.list(home) == []
    assert dbi.list(work) == []
    dbi.update(event_a, href='12345.ics', etag='abcd', calendar=home)
    assert dbi.list(home) == [('12345.ics', 'abcd')]
    assert dbi.list(work) == []
    dbi.update(event_b, href='12345.ics', etag='abcd', calendar=work)
    assert dbi.list(home) == [('12345.ics', 'abcd')]
    assert dbi.list(work) == [('12345.ics', 'abcd')]
    dbi.calendars = [home]
    events_a = list(dbi.get_localized(BERLIN.localize(dt.datetime(2014, 6, 30, 0, 0)),
                                      BERLIN.localize(dt.datetime(2014, 7, 26, 0, 0))))
    dbi.calendars = [work]
    events_b = list(dbi.get_localized(BERLIN.localize(dt.datetime(2014, 6, 30, 0, 0)),
                                      BERLIN.localize(dt.datetime(2014, 7, 26, 0, 0))))
    assert len(events_a) == 4
    assert len(events_b) == 4
    dbi.calendars = [work, home]
    events_c = list(dbi.get_localized(BERLIN.localize(dt.datetime(2014, 6, 30, 0, 0)),
                                      BERLIN.localize(dt.datetime(2014, 7, 26, 0, 0))))
    assert len(events_c) == 8
    # count events from a given calendar
    assert [event[6] for event in events_c].count(home) == 4
    assert [event[6] for event in events_c].count(work) == 4

    dbi.delete('12345.ics', calendar=home)
    dbi.calendars = [home]
    events_a = list(dbi.get_localized(BERLIN.localize(dt.datetime(2014, 6, 30, 0, 0)),
                                      BERLIN.localize(dt.datetime(2014, 7, 26, 0, 0))))
    dbi.calendars = [work]
    events_b = list(dbi.get_localized(BERLIN.localize(dt.datetime(2014, 6, 30, 0, 0)),
                                      BERLIN.localize(dt.datetime(2014, 7, 26, 0, 0))))
    assert len(events_a) == 0
    assert len(events_b) == 4
    dbi.calendars = [work, home]
    events_c = list(dbi.get_localized(BERLIN.localize(dt.datetime(2014, 6, 30, 0, 0)),
                                      BERLIN.localize(dt.datetime(2014, 7, 26, 0, 0))))
    assert [event[6] for event in events_c].count('home') == 0
    assert [event[6] for event in events_c].count('work') == 4
    assert dbi.list(home) == []
    assert dbi.list(work) == [('12345.ics', 'abcd')]


def test_update_one_should_not_affect_others():
    """test if an THISANDFUTURE param effects other events as well"""
    db = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    db.update(_get_text('event_d_15'), href='first', calendar=calname)
    events = db.get_floating(dt.datetime(2015, 4, 9, 0, 0), dt.datetime(2015, 4, 10, 0, 0))
    assert len(list(events)) == 1
    db.update(event_rrule_multi_this_and_future_allday, href='second', calendar=calname)
    events = list(db.get_floating(dt.datetime(2015, 4, 9, 0, 0), dt.datetime(2015, 4, 10, 0, 0)))
    assert len(events) == 1


def test_no_dtend():
    """test support for events with no dtend"""
    db = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    db.update(_get_text('event_dt_no_end'), href='event_dt_no_end', calendar=calname)
    events = db.get_localized(
        BERLIN.localize(dt.datetime(2016, 1, 16, 0, 0)),
        BERLIN.localize(dt.datetime(2016, 1, 17, 0, 0)),
    )
    event = list(events)[0]
    assert event[2] == BERLIN.localize(dt.datetime(2016, 1, 16, 8, 0))
    assert event[3] == BERLIN.localize(dt.datetime(2016, 1, 16, 9, 0))


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
    for cal_str in supported_events:
        ical = icalendar.Calendar.from_ical(cal_str)
        [backend.check_support(event, '', '') for event in ical.walk()]

    ical = icalendar.Calendar.from_ical(event_rrule_this_and_prior)
    with pytest.raises(UpdateFailed):
        [backend.check_support(event, '', '') for event in ical.walk()]

    # icalendar 3.9.2 changed how it deals with unsupported components
    if pkg_resources.get_distribution('icalendar').parsed_version \
       <= pkg_resources.parse_version('3.9.1'):
        ical = icalendar.Calendar.from_ical(event_rdate_period)
        with pytest.raises(UpdateFailed):
            [backend.check_support(event, '', '') for event in ical.walk()]


def test_check_support_rdate_no_values():
    """check if `check_support` doesn't choke on events with an RDATE property
    without a VALUE parameter"""
    ical = icalendar.Calendar.from_ical(_get_text('event_rdate_no_value'))
    [backend.check_support(event, '', '') for event in ical.walk()]


card = """BEGIN:VCARD
VERSION:3.0
FN:Unix
BDAY:19710311
END:VCARD
"""

card_29thfeb = """BEGIN:VCARD
VERSION:3.0
FN:leapyear
BDAY:20000229
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

card_no_fn = """BEGIN:VCARD
VERSION:3.0
N:Ritchie;Dennis;MacAlistair;;
BDAY:19410909
END:VCARD
"""

card_two_birthdays = """BEGIN:VCARD
VERSION:3.0
N:Ritchie;Dennis;MacAlistair;;
BDAY:19410909
BDAY:--0311
END:VCARD
"""

card_anniversary = """BEGIN:VCARD
VERSION:3.0
FN:Unix
X-ANNIVERSARY:19710311
END:VCARD
"""

card_abdate = """BEGIN:VCARD
VERSION:3.0
FN:Unix
ITEM1.X-ABDATE:19710311
ITEM1.X-ABLabel:spouse's birthday
END:VCARD
"""

card_abdate_nolabel = """BEGIN:VCARD
VERSION:3.0
FN:Unix
ITEM1.X-ABDATE:19710311
END:VCARD
"""

card_v3 = """BEGIN:VCARD
VERSION:3.0
FN:Unix
BDAY:1971-03-11
END:VCARD
"""

day = dt.date(1971, 3, 11)
start = dt.datetime.combine(day, dt.time.min)
end = dt.datetime.combine(day, dt.time.max)


def test_birthdays():
    db = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    assert list(db.get_floating(start, end)) == []
    db.update_vcf_dates(card, 'unix.vcf', calendar=calname)
    events = list(db.get_floating(start, end))
    assert len(events) == 1
    assert 'SUMMARY:Unix\'s birthday' in events[0][0]

    events = list(
        db.get_floating(
            dt.datetime(2016, 3, 11, 0, 0),
            dt.datetime(2016, 3, 11, 23, 59, 59, 999)))
    assert 'SUMMARY:Unix\'s birthday' in events[0][0]


def test_birthdays_update():
    """test if we can update a birthday"""
    db = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    db.update_vcf_dates(card, 'unix.vcf', calendar=calname)
    db.update_vcf_dates(card, 'unix.vcf', calendar=calname)


def test_birthdays_no_fn():
    db = backend.SQLiteDb(['home'], ':memory:', locale=LOCALE_BERLIN)
    assert list(db.get_floating(dt.datetime(1941, 9, 9, 0, 0),
                                dt.datetime(1941, 9, 9, 23, 59, 59, 9999))) == []
    db.update_vcf_dates(card_no_fn, 'unix.vcf', calendar=calname)
    events = list(db.get_floating(dt.datetime(1941, 9, 9, 0, 0),
                                  dt.datetime(1941, 9, 9, 23, 59, 59, 9999)))
    assert len(events) == 1
    assert 'SUMMARY:Dennis MacAlistair Ritchie\'s birthday' in events[0][0]


def test_birthday_does_not_parse():
    db = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    assert list(db.get_floating(start, end)) == []
    db.update_vcf_dates(card_does_not_parse, 'unix.vcf', calendar=calname)
    events = list(db.get_floating(start, end))
    assert len(events) == 0


def test_vcard_two_birthdays():
    db = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    assert list(db.get_floating(start, end)) == []
    db.update_vcf_dates(card_two_birthdays, 'unix.vcf', calendar=calname)
    events = list(db.get_floating(start, end))
    assert len(events) == 0


def test_anniversary():
    db = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    assert list(db.get_floating(start, end)) == []
    db.update_vcf_dates(card_anniversary, 'unix.vcf', calendar=calname)
    events = list(db.get_floating(start, end))
    assert len(events) == 1
    assert 'SUMMARY:Unix\'s anniversary' in events[0][0]

    events = list(
        db.get_floating(
            dt.datetime(2016, 3, 11, 0, 0),
            dt.datetime(2016, 3, 11, 23, 59, 59, 999)))
    assert 'SUMMARY:Unix\'s anniversary' in events[0][0]


def test_abdate():
    db = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    assert list(db.get_floating(start, end)) == []
    db.update_vcf_dates(card_abdate, 'unix.vcf', calendar=calname)
    events = list(db.get_floating(start, end))
    assert len(events) == 1
    assert 'SUMMARY:Unix\'s spouse\'s birthday' in events[0][0]

    events = list(
        db.get_floating(
            dt.datetime(2016, 3, 11, 0, 0),
            dt.datetime(2016, 3, 11, 23, 59, 59, 999)))
    assert 'SUMMARY:Unix\'s spouse\'s birthday' in events[0][0]


def test_abdate_nolabel():
    db = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    assert list(db.get_floating(start, end)) == []
    db.update_vcf_dates(card_abdate_nolabel, 'unix.vcf', calendar=calname)
    events = list(db.get_floating(start, end))
    assert len(events) == 1
    assert 'SUMMARY:Unix\'s custom event from vcard' in events[0][0]

    events = list(
        db.get_floating(
            dt.datetime(2016, 3, 11, 0, 0),
            dt.datetime(2016, 3, 11, 23, 59, 59, 999)))
    assert 'SUMMARY:Unix\'s custom event from vcard' in events[0][0]


def test_birthday_v3():
    db = backend.SQLiteDb([calname], ':memory:', locale=LOCALE_BERLIN)
    assert list(db.get_floating(start, end)) == []
    db.update_vcf_dates(card_v3, 'unix.vcf', calendar=calname)
    events = list(db.get_floating(start, end))
    assert len(events) == 1
    assert 'SUMMARY:Unix\'s birthday' in events[0][0]

    events = list(
        db.get_floating(
            dt.datetime(2016, 3, 11, 0, 0),
            dt.datetime(2016, 3, 11, 23, 59, 59, 999)))
    assert 'SUMMARY:Unix\'s birthday' in events[0][0]
