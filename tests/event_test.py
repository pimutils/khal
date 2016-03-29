from datetime import datetime, date, timedelta

import pytest
import pytz
from freezegun import freeze_time

from icalendar import vRecur

from khal.khalendar.event import Event, AllDayEvent, LocalizedEvent, FloatingEvent

from .aux import normalize_component, _get_text


BERLIN = pytz.timezone('Europe/Berlin')
# the lucky people in Bogota don't know the pain that is DST
BOGOTA = pytz.timezone('America/Bogota')

LOCALE = {
    'default_timezone': BERLIN,
    'local_timezone': BERLIN,
    'dateformat': '%d.%m.',
    'timeformat': '%H:%M',
    'longdateformat': '%d.%m.%Y',
    'datetimeformat': '%d.%m. %H:%M',
    'longdatetimeformat': '%d.%m.%Y %H:%M',
    'unicode_symbols': True,
}
BOGOTA_LOCALE = LOCALE.copy()
BOGOTA_LOCALE['local_timezone'] = BOGOTA
BOGOTA_LOCALE['default_timezone'] = BOGOTA
MIXED_LOCALE = LOCALE.copy()
MIXED_LOCALE['local_timezone'] = BOGOTA
EVENT_KWARGS = {'calendar': 'foobar', 'locale': LOCALE}


def test_no_initialization():
    with pytest.raises(ValueError):
        Event('', '')


def test_invalid_keyword_argument():
    with pytest.raises(TypeError):
        Event.fromString(_get_text('event_dt_simple'), keyword='foo')


def test_raw_dt():
    event_dt = _get_text('event_dt_simple')
    start = BERLIN.localize(datetime(2014, 4, 9, 9, 30))
    end = BERLIN.localize(datetime(2014, 4, 9, 10, 30))
    event = Event.fromString(event_dt, start=start, end=end, **EVENT_KWARGS)
    with freeze_time('2016-1-1'):
        assert normalize_component(event.raw) == \
            normalize_component(_get_text('event_dt_simple_inkl_vtimezone'))
    assert event.relative_to(date(2014, 4, 9)) == '09:30-10:30: An Event'

    event = Event.fromString(event_dt, **EVENT_KWARGS)
    assert event.relative_to(date(2014, 4, 9)) == '09:30-10:30: An Event'
    assert event.event_description == '09:30-10:30 09.04.2014: An Event'
    assert event.recurring is False
    assert event.duration == timedelta(hours=1)
    assert event.uid == 'V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU'
    assert event.ident == 'V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU'
    assert event.organizer == ''


def test_update_simple():
    event = Event.fromString(_get_text('event_dt_simple'), **EVENT_KWARGS)
    event_updated = Event.fromString(_get_text('event_dt_simple_updated'), **EVENT_KWARGS)
    event.update_summary('A not so simple Event')
    event.update_description('Everything has changed')
    event.update_location('anywhere')
    assert normalize_component(event.raw) == normalize_component(event_updated.raw)


def test_raw_d():
    event_d = _get_text('event_d')
    event = Event.fromString(event_d, **EVENT_KWARGS)
    assert event.raw.split('\r\n') == _get_text('cal_d').split('\n')
    assert event.relative_to(date(2014, 4, 9)) == 'An Event'
    assert event.event_description == '09.04.2014: An Event'


def test_update_sequence():
    event = Event.fromString(_get_text('event_dt_simple'), **EVENT_KWARGS)
    event.increment_sequence()
    assert event._vevents['PROTO']['SEQUENCE'] == 0
    event.increment_sequence()
    assert event._vevents['PROTO']['SEQUENCE'] == 1


def test_event_organizer():
    event = _get_text('event_dt_duration')
    event = Event.fromString(event, **EVENT_KWARGS)
    assert event.organizer == 'Frank Nord (frank@nord.tld)'


def test_transform_event():
    """test if transformation between different event types works"""
    event_d = _get_text('event_d')
    event = Event.fromString(event_d, **EVENT_KWARGS)
    assert isinstance(event, AllDayEvent)
    start = BERLIN.localize(datetime(2014, 4, 9, 9, 30))
    end = BERLIN.localize(datetime(2014, 4, 9, 10, 30))
    event.update_start_end(start, end)
    assert isinstance(event, LocalizedEvent)
    assert event.event_description == '09:30-10:30 09.04.2014: An Event'
    analog_event = Event.fromString(_get_text('event_dt_simple'), **EVENT_KWARGS)
    assert normalize_component(event.raw) == normalize_component(analog_event.raw)

    with pytest.raises(ValueError):
        event.update_start_end(start, date(2014, 4, 9))


def test_update_event_d():
    event_d = _get_text('event_d')
    event = Event.fromString(event_d, **EVENT_KWARGS)
    event.update_start_end(date(2014, 4, 20), date(2014, 4, 22))
    assert event.event_description == '20.04. - 22.04.2014: An Event'
    assert 'DTSTART;VALUE=DATE:20140420' in event.raw.split('\r\n')
    assert 'DTEND;VALUE=DATE:20140423' in event.raw.split('\r\n')


def test_update_event_duration():
    event_dur = _get_text('event_dt_duration')
    event = Event.fromString(event_dur, **EVENT_KWARGS)
    assert event.start == BERLIN.localize(datetime(2014, 4, 9, 9, 30))
    assert event.end == BERLIN.localize(datetime(2014, 4, 9, 10, 30))
    assert event.duration == timedelta(hours=1)
    event.update_start_end(BERLIN.localize(datetime(2014, 4, 9, 8, 0)),
                           BERLIN.localize(datetime(2014, 4, 9, 12, 0)))
    assert event.start == BERLIN.localize(datetime(2014, 4, 9, 8, 0))
    assert event.end == BERLIN.localize(datetime(2014, 4, 9, 12, 0))
    assert event.duration == timedelta(hours=4)


def test_dt_two_tz():
    event_dt_two_tz = _get_text('event_dt_two_tz')
    cal_dt_two_tz = _get_text('cal_dt_two_tz')

    event = Event.fromString(event_dt_two_tz, **EVENT_KWARGS)
    with freeze_time('2016-02-16 12:00:00'):
        assert normalize_component(cal_dt_two_tz) == normalize_component(event.raw)

    # local (Berlin) time!
    assert event.relative_to(date(2014, 4, 9)) == '09:30-16:30: An Event'
    assert event.event_description == '09:30-16:30 09.04.2014: An Event'


def test_event_dt_duration():
    """event has no end, but duration"""
    event_dt_duration = _get_text('event_dt_duration')
    event = Event.fromString(event_dt_duration, **EVENT_KWARGS)
    assert event.relative_to(date(2014, 4, 9)) == '09:30-10:30: An Event'
    assert event.end == BERLIN.localize(datetime(2014, 4, 9, 10, 30))
    assert event.event_description == '09:30-10:30 09.04.2014: An Event'


def test_event_dt_floating():
    """start and end time have no timezone, i.e. a floating event"""
    event_str = _get_text('event_dt_floating')
    event = Event.fromString(event_str, **EVENT_KWARGS)
    assert isinstance(event, FloatingEvent)
    assert event.relative_to(date(2014, 4, 9)) == '09:30-10:30: An Event'
    assert event.event_description == '09:30-10:30 09.04.2014: An Event'
    assert event.start == datetime(2014, 4, 9, 9, 30)
    assert event.end == datetime(2014, 4, 9, 10, 30)
    assert event.start_local == BERLIN.localize(datetime(2014, 4, 9, 9, 30))
    assert event.end_local == BERLIN.localize(datetime(2014, 4, 9, 10, 30))

    event = Event.fromString(event_str, calendar='foobar', locale=MIXED_LOCALE)
    assert event.start == datetime(2014, 4, 9, 9, 30)
    assert event.end == datetime(2014, 4, 9, 10, 30)
    assert event.start_local == BOGOTA.localize(datetime(2014, 4, 9, 9, 30))
    assert event.end_local == BOGOTA.localize(datetime(2014, 4, 9, 10, 30))


def test_event_dt_tz_missing():
    """localized event DTSTART;TZID=foo, but VTIMEZONE components missing"""
    event_str = _get_text('event_dt_local_missing_tz')
    event = Event.fromString(event_str, **EVENT_KWARGS)
    assert event.start == BERLIN.localize(datetime(2014, 4, 9, 9, 30))
    assert event.end == BERLIN.localize(datetime(2014, 4, 9, 10, 30))
    assert event.start_local == BERLIN.localize(datetime(2014, 4, 9, 9, 30))
    assert event.end_local == BERLIN.localize(datetime(2014, 4, 9, 10, 30))

    event = Event.fromString(event_str, calendar='foobar', locale=MIXED_LOCALE)
    assert event.start == BERLIN.localize(datetime(2014, 4, 9, 9, 30))
    assert event.end == BERLIN.localize(datetime(2014, 4, 9, 10, 30))
    assert event.start_local == BOGOTA.localize(datetime(2014, 4, 9, 2, 30))
    assert event.end_local == BOGOTA.localize(datetime(2014, 4, 9, 3, 30))


def test_event_dt_rr():
    event_dt_rr = _get_text('event_dt_rr')
    event = Event.fromString(event_dt_rr, **EVENT_KWARGS)
    assert event.recurring is True
    desc = '09:30-10:30: An Event ⟳'
    assert event.relative_to(date(2014, 4, 9)) == desc
    assert event.event_description == \
        '09:30-10:30 09.04.2014: An Event\nRepeat: FREQ=DAILY;COUNT=10'


def test_event_d_rr():
    event_d_rr = _get_text('event_d_rr')
    event = Event.fromString(event_d_rr, **EVENT_KWARGS)
    assert event.recurring is True
    desc = 'Another Event ⟳'
    assert event.relative_to(date(2014, 4, 9)) == desc
    assert event.event_description == '09.04.2014: Another Event\nRepeat: FREQ=DAILY;COUNT=10'

    start = date(2014, 4, 10)
    end = date(2014, 4, 11)
    event = Event.fromString(event_d_rr, start=start, end=end, **EVENT_KWARGS)
    assert event.recurring is True
    desc = 'Another Event ⟳'
    assert event.relative_to(date(2014, 4, 10)) == desc
    assert event.event_description == '10.04.2014: Another Event\nRepeat: FREQ=DAILY;COUNT=10'


def test_event_rd():
    event_dt_rd = _get_text('event_dt_rd')
    event = Event.fromString(event_dt_rd, **EVENT_KWARGS)
    assert event.recurring is True


def test_event_d_long():
    event_d_long = _get_text('event_d_long')
    event = Event.fromString(event_d_long, **EVENT_KWARGS)
    with pytest.raises(ValueError):
        event.relative_to(date(2014, 4, 8))
    assert event.relative_to(date(2014, 4, 9)) == '↦ Another Event'
    assert event.relative_to(date(2014, 4, 10)) == '↔ Another Event'
    assert event.relative_to(date(2014, 4, 11)) == '⇥ Another Event'
    with pytest.raises(ValueError):
        event.relative_to(date(2014, 4, 12))
    assert event.event_description == '09.04. - 11.04.2014: Another Event'


def test_event_dt_long():
    event_dt_long = _get_text('event_dt_long')
    event = Event.fromString(event_dt_long, **EVENT_KWARGS)
    assert event.relative_to(date(2014, 4, 9)) == '09:30→ : An Event'
    # FIXME ugly! replace with one arrow
    assert event.relative_to(date(2014, 4, 10)) == '→ → : An Event'
    assert event.relative_to(date(2014, 4, 12)) == '→ 10:30: An Event'
    assert event.event_description == '09.04.2014 09:30 - 12.04.2014 10:30: An Event'


def test_event_no_dst():
    """test the creation of a corect VTIMEZONE for timezones with no dst"""
    event_no_dst = _get_text('event_no_dst')
    cal_no_dst = _get_text('cal_no_dst')
    event = Event.fromString(event_no_dst, calendar='foobar', locale=BOGOTA_LOCALE)
    assert normalize_component(event.raw) == normalize_component(cal_no_dst)
    assert event.event_description == '09:30-10:30 09.04.2014: An Event'


def test_event_raw_UTC():
    """test .raw() on events which are localized in UTC"""
    event_utc = _get_text('event_dt_simple_zulu')
    event = Event.fromString(event_utc, **EVENT_KWARGS)
    assert event.raw == '\r\n'.join([
        '''BEGIN:VCALENDAR''',
        '''VERSION:2.0''',
        '''PRODID:-//CALENDARSERVER.ORG//NONSGML Version 1//EN''',
        '''BEGIN:VEVENT''',
        '''SUMMARY:An Event''',
        '''DTSTART:20140409T093000Z''',
        '''DTEND:20140409T103000Z''',
        '''DTSTAMP;VALUE=DATE-TIME:20140401T234817Z''',
        '''UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU''',
        '''END:VEVENT''',
        '''END:VCALENDAR\r\n'''])


def test_dtend_equals_dtstart():
    event = Event.fromString(_get_text('event_d_same_start_end'),
                             calendar='foobar', locale=LOCALE)
    assert event.end == event.start


def test_multi_uid():
    """test for support for events with consist of several sub events with
    the same uid"""
    orig_event_str = _get_text('event_rrule_recuid')
    event = Event.fromString(orig_event_str, **EVENT_KWARGS)
    for line in orig_event_str.split('\n'):
        assert line in event.raw.split('\r\n')


def test_recur():
    event = Event.fromString(_get_text('event_dt_rr'), **EVENT_KWARGS)
    assert event.recurring is True
    assert event.recurpattern == 'FREQ=DAILY;COUNT=10'
    assert event.recurobject == vRecur({'COUNT': [10], 'FREQ': ['DAILY']})


def test_type_inference():
    event = Event.fromString(_get_text('event_dt_simple'), **EVENT_KWARGS)
    assert type(event) == LocalizedEvent
    event = Event.fromString(_get_text('event_dt_simple_zulu'), **EVENT_KWARGS)
    assert type(event) == LocalizedEvent


def test_duplicate_event():
    event = Event.fromString(_get_text('event_dt_simple'), **EVENT_KWARGS)
    dupe = event.duplicate()
    assert dupe._vevents['PROTO']['UID'].to_ical() != 'V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU'


def test_remove_instance_from_rrule():
    """removing an instance from a recurring event"""
    event = Event.fromString(_get_text('event_dt_rr'), **EVENT_KWARGS)
    event.delete_instance(datetime(2014, 4, 10, 9, 30))
    assert 'EXDATE:20140410T093000' in event.raw.split('\r\n')
    event.delete_instance(datetime(2014, 4, 12, 9, 30))
    assert 'EXDATE:20140410T093000,20140412T093000' in event.raw.split('\r\n')


def test_remove_instance_from_rdate():
    """removing an instance from a recurring event"""
    event = Event.fromString(_get_text('event_dt_rd'), **EVENT_KWARGS)
    assert 'RDATE' in event.raw
    event.delete_instance(datetime(2014, 4, 10, 9, 30))
    assert 'RDATE' not in event.raw


def test_remove_instance_from_two_rdate():
    """removing an instance from a recurring event which has two RDATE props"""
    event = Event.fromString(_get_text('event_dt_two_rd'), **EVENT_KWARGS)
    assert event.raw.count('RDATE') == 2
    event.delete_instance(datetime(2014, 4, 10, 9, 30))
    assert event.raw.count('RDATE') == 1
    assert 'RDATE:20140411T093000,20140412T093000' in event.raw.split('\r\n')


def test_remove_instance_from_recuid():
    """remove an istane from an event which is specified via an additional VEVENT
    with the same UID (which we call `recuid` here"""
    event = Event.fromString(_get_text('event_rrule_recuid'), **EVENT_KWARGS)
    assert event.raw.split('\r\n').count('UID:event_rrule_recurrence_id') == 2
    event.delete_instance(BERLIN.localize(datetime(2014, 7, 7, 7, 0)))
    assert event.raw.split('\r\n').count('UID:event_rrule_recurrence_id') == 1
    assert 'EXDATE;TZID=Europe/Berlin:20140707T070000' in event.raw.split('\r\n')
