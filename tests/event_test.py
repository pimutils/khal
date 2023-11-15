import datetime as dt

import pytest
import pytz
from freezegun import freeze_time
from hypothesis import event, given
from hypothesis.strategies import datetimes
from icalendar import Parameters, vCalAddress, vRecur, vText
from packaging import version

from khal.controllers import human_formatter
from khal.khalendar.event import AllDayEvent, Event, FloatingEvent, LocalizedEvent, create_timezone

from .utils import (
    BERLIN,
    BOGOTA,
    GMTPLUS3,
    LOCALE_BERLIN,
    LOCALE_BOGOTA,
    LOCALE_MIXED,
    NEW_YORK,
    _get_text,
    normalize_component,
)

EVENT_KWARGS = {'calendar': 'foobar', 'locale': LOCALE_BERLIN}

LIST_FORMAT = '{calendar-color}{cancelled}{start-end-time-style} {title}{repeat-symbol}'
LIST_FORMATTER = human_formatter(LIST_FORMAT)
SEARCH_FORMAT = '{calendar-color}{cancelled}{start-long}{to-style}' + \
    '{end-necessary-long} {title}{repeat-symbol}'
CALENDAR_FORMAT = ('{calendar-color}{cancelled}{start-end-time-style} ({calendar}) '
                   '{title} [{location}]{repeat-symbol}')
CALENDAR_FORMATTER = human_formatter(CALENDAR_FORMAT)
SEARCH_FORMATTER = human_formatter(SEARCH_FORMAT)


def test_no_initialization():
    with pytest.raises(ValueError):
        Event('', '')


def test_invalid_keyword_argument():
    with pytest.raises(TypeError):
        Event.fromString(_get_text('event_dt_simple'), keyword='foo')


def test_raw_dt():
    event_dt = _get_text('event_dt_simple')
    start = BERLIN.localize(dt.datetime(2014, 4, 9, 9, 30))
    end = BERLIN.localize(dt.datetime(2014, 4, 9, 10, 30))
    event = Event.fromString(event_dt, start=start, end=end, **EVENT_KWARGS)
    with freeze_time('2016-1-1'):
        assert normalize_component(event.raw) == \
            normalize_component(_get_text('event_dt_simple_inkl_vtimezone'))

    event = Event.fromString(event_dt, **EVENT_KWARGS)
    assert LIST_FORMATTER(event.attributes(
        dt.date(2014, 4, 9))) == '09:30-10:30 An Event\x1b[0m'
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == \
        '09.04.2014 09:30-10:30 An Event\x1b[0m'
    assert event.recurring is False
    assert event.duration == dt.timedelta(hours=1)
    assert event.uid == 'V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU'
    assert event.organizer == ''


def test_calendar_in_format():
    """test if the calendar is included in event.format() if specified in the FORMAT

    see #1121
    """
    event_dt = _get_text('event_dt_simple')
    start = BERLIN.localize(dt.datetime(2014, 4, 9, 9, 30))
    end = BERLIN.localize(dt.datetime(2014, 4, 9, 10, 30))
    event = Event.fromString(event_dt, start=start, end=end, **EVENT_KWARGS)
    assert CALENDAR_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == \
        '09:30-10:30 (foobar) An Event []\x1b[0m'


def test_update_simple():
    event = Event.fromString(_get_text('event_dt_simple'), **EVENT_KWARGS)
    event_updated = Event.fromString(_get_text('event_dt_simple_updated'), **EVENT_KWARGS)
    event.update_summary('A not so simple Event')
    event.update_description('Everything has changed')
    event.update_location('anywhere')
    event.update_categories(['meeting'])
    assert normalize_component(event.raw) == normalize_component(event_updated.raw)


def test_add_url():
    event = Event.fromString(_get_text('event_dt_simple'), **EVENT_KWARGS)
    event.update_url('https://github.com/pimutils/khal')
    assert 'URL:https://github.com/pimutils/khal' in event.raw


def test_get_url():
    event = Event.fromString(_get_text('event_dt_url'), **EVENT_KWARGS)
    assert event.url == "https://github.com/pimutils/khal"


def test_no_end():
    """reading an event with neither DTEND nor DURATION"""
    event = Event.fromString(_get_text('event_dt_no_end'), **EVENT_KWARGS)
    # TODO make sure the event also gets converted to an all day event, as we
    # usually do
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 4, 12))) == \
        '16.01.2016 08:00-17.01.2016 08:00 Test\x1b[0m'


def test_do_not_save_empty_location():
    event = Event.fromString(_get_text('event_dt_simple'), **EVENT_KWARGS)
    event.update_location('')
    assert 'LOCATION' not in event.raw


def test_do_not_save_empty_description():
    event = Event.fromString(_get_text('event_dt_simple'), **EVENT_KWARGS)
    event.update_description('')
    assert 'DESCRIPTION' not in event.raw


def test_do_not_save_empty_url():
    event = Event.fromString(_get_text('event_dt_simple'), **EVENT_KWARGS)
    event.update_url('')
    assert 'URL' not in event.raw


def test_remove_existing_location_if_set_to_empty():
    event = Event.fromString(_get_text('event_dt_simple_updated'), **EVENT_KWARGS)
    event.update_location('')
    assert 'LOCATION' not in event.raw


def test_remove_existing_description_if_set_to_empty():
    event = Event.fromString(_get_text('event_dt_simple_updated'), **EVENT_KWARGS)
    event.update_description('')
    assert 'DESCRIPTION' not in event.raw


def test_remove_existing_url_if_set_to_empty():
    event = Event.fromString(_get_text('event_dt_url'), **EVENT_KWARGS)
    event.update_url('')
    assert 'URL' not in event.raw


def test_update_remove_categories():
    event = Event.fromString(_get_text('event_dt_simple_updated'), **EVENT_KWARGS)
    event_nocat = Event.fromString(_get_text('event_dt_simple_nocat'), **EVENT_KWARGS)
    event.update_categories([])
    assert normalize_component(event.raw) == normalize_component(event_nocat.raw)


def test_raw_d():
    event_d = _get_text('event_d')
    event = Event.fromString(event_d, **EVENT_KWARGS)
    assert event.raw.split('\r\n') == _get_text('cal_d').split('\n')
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == ' An Event\x1b[0m'
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == '09.04.2014 An Event\x1b[0m'


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
    start = BERLIN.localize(dt.datetime(2014, 4, 9, 9, 30))
    end = BERLIN.localize(dt.datetime(2014, 4, 9, 10, 30))
    event.update_start_end(start, end)
    assert isinstance(event, LocalizedEvent)
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == '09:30-10:30 An Event\x1b[0m'
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == \
        '09.04.2014 09:30-10:30 An Event\x1b[0m'
    analog_event = Event.fromString(_get_text('event_dt_simple'), **EVENT_KWARGS)
    assert normalize_component(event.raw) == normalize_component(analog_event.raw)

    with pytest.raises(ValueError):
        event.update_start_end(start, dt.date(2014, 4, 9))


def test_update_event_d():
    event_d = _get_text('event_d')
    event = Event.fromString(event_d, **EVENT_KWARGS)
    event.update_start_end(dt.date(2014, 4, 20), dt.date(2014, 4, 22))
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 20))) == '↦ An Event\x1b[0m'
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 21))) == '↔ An Event\x1b[0m'
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 22))) == '⇥ An Event\x1b[0m'
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 4, 20))) == \
        '20.04.2014-22.04.2014 An Event\x1b[0m'
    assert 'DTSTART;VALUE=DATE:20140420' in event.raw.split('\r\n')
    assert 'DTEND;VALUE=DATE:20140423' in event.raw.split('\r\n')


def test_update_event_duration():
    event_dur = _get_text('event_dt_duration')
    event = Event.fromString(event_dur, **EVENT_KWARGS)
    assert event.start == BERLIN.localize(dt.datetime(2014, 4, 9, 9, 30))
    assert event.end == BERLIN.localize(dt.datetime(2014, 4, 9, 10, 30))
    assert event.duration == dt.timedelta(hours=1)
    event.update_start_end(BERLIN.localize(dt.datetime(2014, 4, 9, 8, 0)),
                           BERLIN.localize(dt.datetime(2014, 4, 9, 12, 0)))
    assert event.start == BERLIN.localize(dt.datetime(2014, 4, 9, 8, 0))
    assert event.end == BERLIN.localize(dt.datetime(2014, 4, 9, 12, 0))
    assert event.duration == dt.timedelta(hours=4)


def test_dt_two_tz():
    event_dt_two_tz = _get_text('event_dt_two_tz')
    cal_dt_two_tz = _get_text('cal_dt_two_tz')

    event = Event.fromString(event_dt_two_tz, **EVENT_KWARGS)
    with freeze_time('2016-02-16 12:00:00'):
        assert normalize_component(cal_dt_two_tz) == normalize_component(event.raw)

    assert event.start == BERLIN.localize(dt.datetime(2014, 4, 9, 9, 30))
    assert event.end == NEW_YORK.localize(dt.datetime(2014, 4, 9, 10, 30))
    # local (Berlin) time!
    assert event.start_local == BERLIN.localize(dt.datetime(2014, 4, 9, 9, 30))
    assert event.end_local == BERLIN.localize(dt.datetime(2014, 4, 9, 16, 30))
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == '09:30-16:30 An Event\x1b[0m'
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == \
        '09.04.2014 09:30-16:30 An Event\x1b[0m'


def test_event_dt_duration():
    """event has no end, but duration"""
    event_dt_duration = _get_text('event_dt_duration')
    event = Event.fromString(event_dt_duration, **EVENT_KWARGS)
    assert event.start == BERLIN.localize(dt.datetime(2014, 4, 9, 9, 30))
    assert event.end == BERLIN.localize(dt.datetime(2014, 4, 9, 10, 30))
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == '09:30-10:30 An Event\x1b[0m'
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == \
        '09.04.2014 09:30-10:30 An Event\x1b[0m'
    assert human_formatter('{duration}')(event.attributes(
        relative_to=dt.date.today())) == '1h\x1b[0m'


def test_event_dt_floating():
    """start and end time have no timezone, i.e. a floating event"""
    event_str = _get_text('event_dt_floating')
    event = Event.fromString(event_str, **EVENT_KWARGS)
    assert isinstance(event, FloatingEvent)
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == '09:30-10:30 An Event\x1b[0m'
    assert human_formatter('{duration}')(event.attributes(
        relative_to=dt.date.today())) == '1h\x1b[0m'
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == \
        '09.04.2014 09:30-10:30 An Event\x1b[0m'
    assert event.start == dt.datetime(2014, 4, 9, 9, 30)
    assert event.end == dt.datetime(2014, 4, 9, 10, 30)
    assert event.start_local == BERLIN.localize(dt.datetime(2014, 4, 9, 9, 30))
    assert event.end_local == BERLIN.localize(dt.datetime(2014, 4, 9, 10, 30))

    event = Event.fromString(event_str, calendar='foobar', locale=LOCALE_MIXED)
    assert event.start == dt.datetime(2014, 4, 9, 9, 30)
    assert event.end == dt.datetime(2014, 4, 9, 10, 30)
    assert event.start_local == BOGOTA.localize(dt.datetime(2014, 4, 9, 9, 30))
    assert event.end_local == BOGOTA.localize(dt.datetime(2014, 4, 9, 10, 30))


def test_event_dt_tz_missing():
    """localized event DTSTART;TZID=foo, but VTIMEZONE components missing"""
    event_str = _get_text('event_dt_local_missing_tz')
    event = Event.fromString(event_str, **EVENT_KWARGS)
    assert event.start == BERLIN.localize(dt.datetime(2014, 4, 9, 9, 30))
    assert event.end == BERLIN.localize(dt.datetime(2014, 4, 9, 10, 30))
    assert event.start_local == BERLIN.localize(dt.datetime(2014, 4, 9, 9, 30))
    assert event.end_local == BERLIN.localize(dt.datetime(2014, 4, 9, 10, 30))
    assert human_formatter('{duration}')(event.attributes(
        relative_to=dt.date.today())) == '1h\x1b[0m'

    event = Event.fromString(event_str, calendar='foobar', locale=LOCALE_MIXED)
    assert event.start == BERLIN.localize(dt.datetime(2014, 4, 9, 9, 30))
    assert event.end == BERLIN.localize(dt.datetime(2014, 4, 9, 10, 30))
    assert event.start_local == BOGOTA.localize(dt.datetime(2014, 4, 9, 2, 30))
    assert event.end_local == BOGOTA.localize(dt.datetime(2014, 4, 9, 3, 30))


def test_event_dt_rr():
    event_dt_rr = _get_text('event_dt_rr')
    event = Event.fromString(event_dt_rr, **EVENT_KWARGS)
    assert event.recurring is True

    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == '09:30-10:30 An Event ⟳\x1b[0m'
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == \
        '09.04.2014 09:30-10:30 An Event ⟳\x1b[0m'
    assert human_formatter('{repeat-pattern}')(event.attributes(dt.date(2014, 4, 9))
                                               ) == 'FREQ=DAILY;COUNT=10\x1b[0m'


def test_event_d_rr():
    event_d_rr = _get_text('event_d_rr')
    event = Event.fromString(event_d_rr, **EVENT_KWARGS)
    assert event.recurring is True
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == ' Another Event ⟳\x1b[0m'
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == \
        '09.04.2014 Another Event ⟳\x1b[0m'
    assert human_formatter('{repeat-pattern}')(event.attributes(dt.date(2014, 4, 9))
                                               ) == 'FREQ=DAILY;COUNT=10\x1b[0m'

    start = dt.date(2014, 4, 10)
    end = dt.date(2014, 4, 11)
    event = Event.fromString(event_d_rr, start=start, end=end, **EVENT_KWARGS)
    assert event.recurring is True
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 10))) == ' Another Event ⟳\x1b[0m'
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 4, 10))) == \
        '10.04.2014 Another Event ⟳\x1b[0m'


def test_event_rd():
    event_dt_rd = _get_text('event_dt_rd')
    event = Event.fromString(event_dt_rd, **EVENT_KWARGS)
    assert event.recurring is True


def test_status_confirmed():
    event = Event.fromString(_get_text('event_dt_status_confirmed'), **EVENT_KWARGS)
    assert event.status == 'CONFIRMED'
    FORMAT_CALENDAR = ('{calendar-color}{status-symbol}{start-end-time-style} ({calendar}) '
                       '{title} [{location}]{repeat-symbol}')

    assert human_formatter(FORMAT_CALENDAR)(event.attributes(dt.date(2014, 4, 9))) == \
        '✔09:30-10:30 (foobar) An Event []\x1b[0m'

def test_event_d_long():
    event_d_long = _get_text('event_d_long')
    event = Event.fromString(event_d_long, **EVENT_KWARGS)
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == '↦ Another Event\x1b[0m'
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 10))) == '↔ Another Event\x1b[0m'
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 11))) == '⇥ Another Event\x1b[0m'
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 12))) == ' Another Event\x1b[0m'
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 4, 16))) == \
        '09.04.2014-11.04.2014 Another Event\x1b[0m'
    assert human_formatter('{duration}')(event.attributes(
        relative_to=dt.date(2014, 4, 11))) == '3d\x1b[0m'


def test_event_d_two_days():
    event_d_long = _get_text('event_d_long')
    event = Event.fromString(event_d_long, **EVENT_KWARGS)
    event.update_start_end(dt.date(2014, 4, 9), dt.date(2014, 4, 10))
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == '↦ Another Event\x1b[0m'
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 10))) == '⇥ Another Event\x1b[0m'
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 12))) == ' Another Event\x1b[0m'
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 4, 10))) == \
        '09.04.2014-10.04.2014 Another Event\x1b[0m'


def test_event_dt_long():
    event_dt_long = _get_text('event_dt_long')
    event = Event.fromString(event_dt_long, **EVENT_KWARGS)

    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 9))) == '09:30→ An Event\x1b[0m'
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 10))) == '↔ An Event\x1b[0m'
    assert LIST_FORMATTER(event.attributes(dt.date(2014, 4, 12))) == '→10:30 An Event\x1b[0m'
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 4, 10))) == \
        '09.04.2014 09:30-12.04.2014 10:30 An Event\x1b[0m'


def test_event_no_dst():
    """test the creation of a corect VTIMEZONE for timezones with no dst"""
    event_no_dst = _get_text('event_no_dst')
    cal_no_dst = _get_text('cal_no_dst')
    event = Event.fromString(event_no_dst, calendar='foobar', locale=LOCALE_BOGOTA)
    if version.parse(pytz.__version__) > version.Version('2017.1'):
        if version.parse(pytz.__version__) < version.Version('2022.7'):
            cal_no_dst = cal_no_dst.replace(
                'TZNAME:COT',
                'RDATE:20380118T221407\r\nTZNAME:-05'
            )
        else:
            cal_no_dst = cal_no_dst.replace(
                'TZNAME:COT',
                'TZNAME:-05'
            )

    assert normalize_component(event.raw) == normalize_component(cal_no_dst)
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 4, 10))) == \
        '09.04.2014 09:30-10:30 An Event\x1b[0m'


def test_event_raw_UTC():
    """test .raw() on events which are localized in UTC"""
    event_utc = _get_text('event_dt_simple_zulu')
    event = Event.fromString(event_utc, **EVENT_KWARGS)
    assert event.raw == '\r\n'.join([
        '''BEGIN:VCALENDAR''',
        '''VERSION:2.0''',
        '''PRODID:-//PIMUTILS.ORG//NONSGML khal / icalendar //EN''',
        '''BEGIN:VEVENT''',
        '''SUMMARY:An Event''',
        '''DTSTART:20140409T093000Z''',
        '''DTEND:20140409T103000Z''',
        '''DTSTAMP:20140401T234817Z''',
        '''UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU''',
        '''END:VEVENT''',
        '''END:VCALENDAR\r\n'''])


def test_zulu_events():
    """test if events in Zulu time are correctly recognized as localized events"""
    event = Event.fromString(_get_text('event_dt_simple_zulu'), **EVENT_KWARGS)
    assert type(event) == LocalizedEvent
    assert event.start_local == BERLIN.localize(dt.datetime(2014, 4, 9, 11, 30))


def test_dtend_equals_dtstart():
    event = Event.fromString(_get_text('event_d_same_start_end'),
                             calendar='foobar', locale=LOCALE_BERLIN)
    assert event.end == event.start


def test_multi_uid():
    """test for support for events with consist of several sub events with
    the same uid"""
    orig_event_str = _get_text('event_rrule_recuid')
    event = Event.fromString(orig_event_str, **EVENT_KWARGS)
    for line in orig_event_str.split('\n'):
        assert line in event.raw.split('\r\n')


def test_cancelled_instance():
    orig_event_str = _get_text('event_rrule_recuid_cancelled')
    event = Event.fromString(orig_event_str, ref='1405314000', **EVENT_KWARGS)
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 7, 14))) == \
        'CANCELLED 14.07.2014 07:00-12:00 Arbeit ⟳\x1b[0m'
    event = Event.fromString(orig_event_str, ref='PROTO', **EVENT_KWARGS)
    assert SEARCH_FORMATTER(event.attributes(dt.date(2014, 7, 14))) == \
        '30.06.2014 07:00-12:00 Arbeit ⟳\x1b[0m'


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
    event.delete_instance(dt.datetime(2014, 4, 10, 9, 30))
    assert 'EXDATE:20140410T093000' in event.raw.split('\r\n')
    event.delete_instance(dt.datetime(2014, 4, 12, 9, 30))
    assert 'EXDATE:20140410T093000,20140412T093000' in event.raw.split('\r\n')


def test_remove_instance_from_rdate():
    """removing an instance from a recurring event"""
    event = Event.fromString(_get_text('event_dt_rd'), **EVENT_KWARGS)
    assert 'RDATE' in event.raw
    event.delete_instance(dt.datetime(2014, 4, 10, 9, 30))
    assert 'RDATE' not in event.raw


def test_remove_instance_from_two_rdate():
    """removing an instance from a recurring event which has two RDATE props"""
    event = Event.fromString(_get_text('event_dt_two_rd'), **EVENT_KWARGS)
    assert event.raw.count('RDATE') == 2
    event.delete_instance(dt.datetime(2014, 4, 10, 9, 30))
    assert event.raw.count('RDATE') == 1
    assert 'RDATE:20140411T093000,20140412T093000' in event.raw.split('\r\n')


def test_remove_instance_from_recuid():
    """remove an istance from an event which is specified via an additional VEVENT
    with the same UID (which we call `recuid` here"""
    event = Event.fromString(_get_text('event_rrule_recuid'), **EVENT_KWARGS)
    assert event.raw.split('\r\n').count('UID:event_rrule_recurrence_id') == 2
    event.delete_instance(BERLIN.localize(dt.datetime(2014, 7, 7, 7, 0)))
    assert event.raw.split('\r\n').count('UID:event_rrule_recurrence_id') == 1
    assert 'EXDATE;TZID=Europe/Berlin:20140707T070000' in event.raw.split('\r\n')


def test_format_24():
    """test if events ending at 00:00/24:00 are displayed as ending the day
    before"""
    event_dt = _get_text('event_dt_simple')
    start = BERLIN.localize(dt.datetime(2014, 4, 9, 19, 30))
    end = BERLIN.localize(dt.datetime(2014, 4, 10))
    event = Event.fromString(event_dt, **EVENT_KWARGS)
    event.update_start_end(start, end)
    format_ = '{start-end-time-style} {title}{repeat-symbol}'
    assert human_formatter(format_)(event.attributes(dt.date(2014, 4, 9))
                                    ) == '19:30-24:00 An Event\x1b[0m'


def test_invalid_format_string():
    event_dt = _get_text('event_dt_simple')
    event = Event.fromString(event_dt, **EVENT_KWARGS)
    format_ = '{start-end-time-style} {title}{foo}'
    with pytest.raises(KeyError):
        human_formatter(format_)(event.attributes(dt.date(2014, 4, 9)))


def test_format_colors():
    event = Event.fromString(_get_text('event_dt_simple'), **EVENT_KWARGS)
    format_ = '{red}{title}{reset}'
    assert human_formatter(format_)(event.attributes(dt.date(2014, 4, 9))
                                    ) == '\x1b[31mAn Event\x1b[0m\x1b[0m'
    assert human_formatter(format_, colors=False)(
        event.attributes(dt.date(2014, 4, 9), colors=False)) == 'An Event'


def test_event_alarm():
    event = Event.fromString(_get_text('event_dt_simple'), **EVENT_KWARGS)
    assert event.alarms == []
    event.update_alarms([(dt.timedelta(-1, 82800), 'new event')])
    assert event.alarms == [(dt.timedelta(-1, 82800), vText('new event'))]


def test_event_attendees():
    event = Event.fromString(_get_text('event_dt_simple'), **EVENT_KWARGS)
    assert event.attendees == ""
    event.update_attendees(["this-does@not-exist.de", ])
    assert event.attendees == "this-does@not-exist.de"
    assert isinstance(event._vevents[event.ref].get('ATTENDEE', []), list)
    assert isinstance(event._vevents[event.ref].get('ATTENDEE', [])[0], vCalAddress)
    assert str(event._vevents[event.ref].get('ATTENDEE', [])[0]) == "MAILTO:this-does@not-exist.de"

    event.update_attendees(["this-does@not-exist.de", "also-does@not-exist.de"])
    assert event.attendees == "this-does@not-exist.de, also-does@not-exist.de"

    assert isinstance(event._vevents[event.ref].get('ATTENDEE', []), list)
    assert len(event._vevents[event.ref].get('ATTENDEE', [])) == 2
    assert isinstance(event._vevents[event.ref].get('ATTENDEE', [])[0], vCalAddress)

    # test if parameters from existing vCalAddress objects will be preserved
    new_address = vCalAddress("MAILTO:mail.address@not-exist.de")
    new_address.params = Parameters(
        {'CN': 'Real Name',
         'PARTSTAT': 'NEEDS-ACTION',
         'ROLE': 'REQ-PARTICIPANT',
         'RSVP': 'TRUE'}
    )
    event._vevents[event.ref]['ATTENDEE'] = [new_address, ]
    event.update_attendees(["another.mailaddress@not-exist.de", "mail.address@not-exist.de"])
    assert event.attendees == "mail.address@not-exist.de, another.mailaddress@not-exist.de"
    address = [a for a in event._vevents[event.ref].get('ATTENDEE', [])
               if str(a) == "MAILTO:mail.address@not-exist.de"]
    assert len(address) == 1
    address = address[0]
    assert address.params.get('CN', None) is not None
    assert address.params['CN'] == "Real Name"


def test_create_timezone_static():
    gmt = pytz.timezone('Etc/GMT-8')
    assert create_timezone(gmt).to_ical().split() == [
        b'BEGIN:VTIMEZONE',
        b'TZID:Etc/GMT-8',
        b'BEGIN:STANDARD',
        b'DTSTART:16010101T000000',
        b'RDATE:16010101T000000',
        b'TZNAME:Etc/GMT-8',
        b'TZOFFSETFROM:+0800',
        b'TZOFFSETTO:+0800',
        b'END:STANDARD',
        b'END:VTIMEZONE',
    ]
    event_dt = _get_text('event_dt_simple')
    start = GMTPLUS3.localize(dt.datetime(2014, 4, 9, 9, 30))
    end = GMTPLUS3.localize(dt.datetime(2014, 4, 9, 10, 30))
    event = Event.fromString(event_dt, **EVENT_KWARGS)
    event.update_start_end(start, end)
    with freeze_time('2016-1-1'):
        assert normalize_component(event.raw) == normalize_component(
            """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//PIMUTILS.ORG//NONSGML khal / icalendar //EN
BEGIN:VTIMEZONE
TZID:Etc/GMT+3
BEGIN:STANDARD
DTSTART:16010101T000000
RDATE:16010101T000000
TZNAME:Etc/GMT+3
TZOFFSETFROM:-0300
TZOFFSETTO:-0300
END:STANDARD
END:VTIMEZONE
BEGIN:VEVENT
SUMMARY:An Event
DTSTART;TZID=Etc/GMT+3:20140409T093000
DTEND;TZID=Etc/GMT+3:20140409T103000
DTSTAMP:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT
END:VCALENDAR"""
        )


def test_sort_date_vs_datetime():
    event1 = Event.fromString(_get_text('event_d'), **EVENT_KWARGS)
    event2 = Event.fromString(_get_text('event_dt_floating'), **EVENT_KWARGS)
    assert event1 < event2


def test_sort_event_start():
    event_dt = _get_text('event_dt_simple')
    start = BERLIN.localize(dt.datetime(2014, 4, 9, 9, 45))
    end = BERLIN.localize(dt.datetime(2014, 4, 9, 10, 30))
    event1 = Event.fromString(event_dt, **EVENT_KWARGS)
    event2 = Event.fromString(event_dt, start=start, end=end, **EVENT_KWARGS)
    assert event1 < event2


def test_sort_event_end():
    event_dt = _get_text('event_dt_simple')
    start = BERLIN.localize(dt.datetime(2014, 4, 9, 9, 30))
    end = BERLIN.localize(dt.datetime(2014, 4, 9, 10, 45))
    event1 = Event.fromString(event_dt, **EVENT_KWARGS)
    event2 = Event.fromString(event_dt, start=start, end=end, **EVENT_KWARGS)
    assert event1 < event2


def test_sort_event_summary():
    event_dt = _get_text('event_dt_simple')
    event1 = Event.fromString(event_dt, **EVENT_KWARGS)
    event2 = Event.fromString(event_dt, **EVENT_KWARGS)
    event2.update_summary("ZZZ")
    assert event1 < event2


def test_create_timezone_in_future():
    """Events too far into the future (after the next DST transition) used
    to be created with invalid timezones"""
    with freeze_time('2019-03-31'):
        assert create_timezone(
            pytz.timezone('Europe/Amsterdam'),
            dt.datetime(2022, 1, 1, 18, 0)).to_ical().split() == [
                b'BEGIN:VTIMEZONE',
                b'TZID:Europe/Amsterdam',
                b'BEGIN:STANDARD',
                b'DTSTART:20211031T020000',
                b'TZNAME:CET',
                b'TZOFFSETFROM:+0200',
                b'TZOFFSETTO:+0100',
                b'END:STANDARD',
                b'BEGIN:DAYLIGHT',
                b'DTSTART:20220327T030000',
                b'TZNAME:CEST',
                b'TZOFFSETFROM:+0100',
                b'TZOFFSETTO:+0200',
                b'END:DAYLIGHT',
                b'END:VTIMEZONE']


now = dt.datetime.now()
min_value = now - dt.timedelta(days=3560)
max_value = now + dt.timedelta(days=3560)
AMSTERDAM = pytz.timezone('Europe/Amsterdam')


@given(datetimes(min_value=min_value, max_value=max_value),
       datetimes(min_value=min_value, max_value=max_value))
def test_timezone_creation_with_arbitrary_dates(freeze_ts, event_time):
    """test if for arbitrary dates from the current date we produce a valid VTIMEZONE"""
    event(f'freeze_ts == event_time: {freeze_ts == event_time}')
    with freeze_time(freeze_ts):
        vtimezone = create_timezone(AMSTERDAM, event_time).to_ical().decode('utf-8')
    assert len(vtimezone) > 14
    assert 'BEGIN:STANDARD' in vtimezone
    assert 'BEGIN:DAYLIGHT' in vtimezone


def test_parameters_description():
    """test if we support DESCRIPTION properties with parameters"""
    event = Event.fromString(_get_text('event_dt_description'), **EVENT_KWARGS)
    assert event.description == (
        'Hey, \n\nJust setting aside some dedicated time to talk about redacted.'
    )

def test_partstat():
    FORMAT_CALENDAR = (
        '{calendar-color}{partstat-symbol}{status-symbol}{start-end-time-style} ({calendar}) '
        '{title} [{location}]{repeat-symbol}'
    )

    event = Event.fromString(
        _get_text('event_dt_partstat'), addresses=['jdoe@example.com'], **EVENT_KWARGS)
    assert event.partstat == 'ACCEPTED'
    assert human_formatter(FORMAT_CALENDAR)(event.attributes(dt.date(2014, 4, 9))) == \
        '✔09:30-10:30 (foobar) An Event []\x1b[0m'

    event = Event.fromString(
        _get_text('event_dt_partstat'), addresses=['another@example.com'], **EVENT_KWARGS)
    assert event.partstat == 'DECLINED'
    assert human_formatter(FORMAT_CALENDAR)(event.attributes(dt.date(2014, 4, 9))) == \
        '❌09:30-10:30 (foobar) An Event []\x1b[0m'

    event = Event.fromString(
        _get_text('event_dt_partstat'), addresses=['jqpublic@example.com'], **EVENT_KWARGS)
    assert event.partstat == 'ACCEPTED'
    assert human_formatter(FORMAT_CALENDAR)(event.attributes(dt.date(2014, 4, 9))) == \
        '✔09:30-10:30 (foobar) An Event []\x1b[0m'

@pytest.mark.xfail
def test_partstat_deligated():
    event = Event.fromString(
        _get_text('event_dt_partstat'), addresses=['hcabot@example.com'], **EVENT_KWARGS)
    assert event.partstat == 'ACCEPTED'

    event = Event.fromString(
        _get_text('event_dt_partstat'), addresses=['iamboss@example.com'], **EVENT_KWARGS)
    assert event.partstat == 'ACCEPTED'
