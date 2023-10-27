import datetime as dt
import logging
import os
from textwrap import dedent
from time import sleep

import pytest
from freezegun import freeze_time

import khal.khalendar.exceptions
import khal.utils
from khal import icalendar as icalendar_helpers
from khal.controllers import human_formatter
from khal.khalendar import CalendarCollection
from khal.khalendar.backend import CouldNotCreateDbDir
from khal.khalendar.event import Event
from khal.khalendar.vdir import Item

from . import utils
from .utils import (
    BERLIN,
    LOCALE_BERLIN,
    LOCALE_SYDNEY,
    LONDON,
    SYDNEY,
    CollVdirType,
    DumbItem,
    _get_text,
    cal1,
    cal2,
    cal3,
    normalize_component,
)

today = dt.date.today()
yesterday = today - dt.timedelta(days=1)
tomorrow = today + dt.timedelta(days=1)

aday = dt.date(2014, 4, 9)
bday = dt.date(2014, 4, 10)

event_allday_template = """BEGIN:VEVENT
SEQUENCE:0
UID:uid3@host1.com
DTSTART;VALUE=DATE:{}
DTEND;VALUE=DATE:{}
SUMMARY:a meeting
DESCRIPTION:short description
LOCATION:LDB Lobby
END:VEVENT"""

event_today = event_allday_template.format(
    today.strftime('%Y%m%d'), tomorrow.strftime('%Y%m%d'))
item_today = Item(event_today)
SIMPLE_EVENT_UID = 'V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU'


class TestCalendar:

    def test_create(self, coll_vdirs):
        assert True

    def test_new_event(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        event = coll.create_event_from_ics(event_today, cal1)
        assert event.calendar == cal1
        coll.insert(event)
        events = list(coll.get_events_on(today))
        assert len(events) == 1
        assert events[0].color == 'dark blue'
        assert len(list(coll.get_events_on(tomorrow))) == 0
        assert len(list(coll.get_events_on(yesterday))) == 0
        assert len(list(vdirs[cal1].list())) == 1

    def test_sanity(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        mtimes = {}
        for _ in range(100):
            for cal in coll._calendars:
                mtime = coll._local_ctag(cal)
                if mtimes.get(cal):
                    assert mtimes[cal] == mtime
                else:
                    mtimes[cal] = mtime

    def test_db_needs_update(self, coll_vdirs, sleep_time):
        coll, vdirs = coll_vdirs

        print('init')
        for calendar in coll._calendars:
            print(f'{calendar}: saved ctag: {coll._local_ctag(calendar)}, '
                  f'vdir ctag: {coll._backend.get_ctag(calendar)}')
        assert len(list(vdirs[cal1].list())) == 0
        assert coll._needs_update(cal1) is False
        sleep(sleep_time)

        vdirs[cal1].upload(item_today)
        print('upload')
        for calendar in coll._calendars:
            print(f'{calendar}: saved ctag: {coll._local_ctag(calendar)}, '
                  f'vdir ctag: {coll._backend.get_ctag(calendar)}')
        assert len(list(vdirs[cal1].list())) == 1
        assert coll._needs_update(cal1) is True
        coll.update_db()
        print('updated')
        for calendar in coll._calendars:
            print(f'{calendar}: saved ctag: {coll._local_ctag(calendar)}, '
                  f'vdir ctag: {coll._backend.get_ctag(calendar)}')
        assert coll._needs_update(cal1) is False


class TestVdirsyncerCompat:
    def test_list(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        event = Event.fromString(_get_text('event_d'), calendar=cal1, locale=LOCALE_BERLIN)
        assert event.etag is None
        assert event.href is None
        coll.insert(event)
        assert event.etag is not None
        assert event.href == 'V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU.ics'
        event = Event.fromString(event_today, calendar=cal1, locale=LOCALE_BERLIN)
        coll.insert(event)
        hrefs = sorted(href for href, etag in coll._backend.list(cal1))
        assert {str(coll.get_event(href, calendar=cal1).uid) for href in hrefs} == {
            'uid3@host1.com',
            'V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU',
        }


class TestCollection:

    astart = dt.datetime.combine(aday, dt.time.min)
    aend = dt.datetime.combine(aday, dt.time.max)
    bstart = dt.datetime.combine(bday, dt.time.min)
    bend = dt.datetime.combine(bday, dt.time.max)
    astart_berlin = utils.BERLIN.localize(astart)
    aend_berlin = utils.BERLIN.localize(aend)
    bstart_berlin = utils.BERLIN.localize(bstart)
    bend_berlin = utils.BERLIN.localize(bend)

    def test_default_calendar(self, tmpdir):
        calendars = {
            'foobar': {'name': 'foobar', 'path': str(tmpdir), 'readonly': True},
            'home': {'name': 'home', 'path': str(tmpdir)},
            "Dad's Calendar": {'name': "Dad's calendar", 'path': str(tmpdir), 'readonly': True},
        }
        coll = CalendarCollection(
            calendars=calendars, locale=LOCALE_BERLIN, dbpath=':memory:',
        )
        assert coll.default_calendar_name is None
        with pytest.raises(ValueError):
            coll.default_calendar_name = "Dad's calendar"
        assert coll.default_calendar_name is None
        with pytest.raises(ValueError):
            coll.default_calendar_name = 'unknownstuff'
        assert coll.default_calendar_name is None
        coll.default_calendar_name = 'home'
        assert coll.default_calendar_name == 'home'
        assert coll.writable_names == ['home']

    def test_empty(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        start = dt.datetime.combine(today, dt.time.min)
        end = dt.datetime.combine(today, dt.time.max)
        assert list(coll.get_floating(start, end)) == []
        assert list(coll.get_localized(utils.BERLIN.localize(start),
                                       utils.BERLIN.localize(end))) == []

    def test_insert(self, coll_vdirs):
        """insert a localized event"""
        coll, vdirs = coll_vdirs
        coll.insert(
            Event.fromString(_get_text('event_dt_simple'), calendar=cal1, locale=LOCALE_BERLIN),
            cal1)
        events = list(coll.get_localized(self.astart_berlin, self.aend_berlin))
        assert len(events) == 1
        assert events[0].color == 'dark blue'
        assert events[0].calendar == cal1

        events = list(coll.get_events_on(aday))
        assert len(events) == 1
        assert events[0].color == 'dark blue'
        assert events[0].calendar == cal1

        assert len(list(vdirs[cal1].list())) == 1
        assert len(list(vdirs[cal2].list())) == 0
        assert len(list(vdirs[cal3].list())) == 0
        assert list(coll.get_floating(self.astart, self.aend)) == []

    def test_insert_d(self, coll_vdirs):
        """insert a floating event"""
        coll, vdirs = coll_vdirs
        event = Event.fromString(_get_text('event_d'), calendar=cal1, locale=LOCALE_BERLIN)
        coll.insert(event, cal1)
        events = list(coll.get_events_on(aday))
        assert len(events) == 1
        assert events[0].calendar == cal1
        assert events[0].color == 'dark blue'
        assert len(list(vdirs[cal1].list())) == 1
        assert len(list(vdirs[cal2].list())) == 0
        assert len(list(vdirs[cal3].list())) == 0
        assert list(coll.get_localized(self.bstart_berlin, self.bend_berlin)) == []

    def test_insert_d_no_value(self, coll_vdirs):
        """insert a date event with no VALUE=DATE option"""
        coll, vdirs = coll_vdirs
        coll.insert(
            Event.fromString(
                _get_text('event_d_no_value'), calendar=cal1, locale=LOCALE_BERLIN),
            cal1)
        events = list(coll.get_events_on(aday))
        assert len(events) == 1
        assert events[0].calendar == cal1
        assert len(list(vdirs[cal1].list())) == 1
        assert len(list(vdirs[cal2].list())) == 0
        assert len(list(vdirs[cal3].list())) == 0
        assert list(coll.get_localized(self.bstart_berlin, self.bend_berlin)) == []

    def test_get(self, coll_vdirs):
        """test getting an event by its href"""
        coll, vdirs = coll_vdirs
        event = Event.fromString(
            _get_text('event_dt_simple'), href='xyz.ics', calendar=cal1, locale=LOCALE_BERLIN,
        )
        coll.insert(event, cal1)
        event_from_db = coll.get_event(SIMPLE_EVENT_UID + '.ics', cal1)
        with freeze_time('2016-1-1'):
            assert normalize_component(event_from_db.raw) == \
                normalize_component(_get_text('event_dt_simple_inkl_vtimezone'))
        assert event_from_db.etag

    def test_change(self, coll_vdirs):
        """moving an event from one calendar to another"""
        coll, vdirs = coll_vdirs
        event = Event.fromString(_get_text('event_dt_simple'), calendar=cal1, locale=LOCALE_BERLIN)
        coll.insert(event, cal1)
        event = list(coll.get_events_on(aday))[0]
        assert event.calendar == cal1

        coll.change_collection(event, cal2)
        events = list(coll.get_events_on(aday))
        assert len(events) == 1
        assert events[0].calendar == cal2

    def test_update_event(self, coll_vdirs):
        """updating one event"""
        coll, vdirs = coll_vdirs
        event = Event.fromString(
            _get_text('event_dt_simple'), calendar=cal1, locale=LOCALE_BERLIN)
        coll.insert(event, cal1)
        events = coll.get_events_on(aday)
        event = list(events)[0]
        event.update_summary('really simple event')
        event.update_start_end(bday, bday)
        coll.update(event)
        events = list(coll.get_localized(self.astart_berlin, self.aend_berlin))
        assert len(events) == 0
        events = list(coll.get_floating(self.bstart, self.bend))
        assert len(events) == 1
        assert events[0].summary == 'really simple event'

    def test_newevent(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        bday = dt.datetime.combine(aday, dt.time.min)
        anend = bday + dt.timedelta(hours=1)
        event = icalendar_helpers.new_vevent(
            dtstart=bday, dtend=anend, summary="hi", timezone=utils.BERLIN,
            locale=LOCALE_BERLIN,
        )
        event = coll.create_event_from_ics(event.to_ical(), coll.default_calendar_name)
        assert event.allday is False

    def test_modify_readonly_calendar(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        coll._calendars[cal1]['readonly'] = True
        coll._calendars[cal3]['readonly'] = True
        event = Event.fromString(_get_text('event_dt_simple'), calendar=cal1, locale=LOCALE_BERLIN)

        with pytest.raises(khal.khalendar.exceptions.ReadOnlyCalendarError):
            coll.insert(event, cal1)
        with pytest.raises(khal.khalendar.exceptions.ReadOnlyCalendarError):
            # params don't really matter here
            coll.delete('href', 'eteg', cal1)

    def test_search(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        assert len(list(coll.search('Event'))) == 0
        event = Event.fromString(
            _get_text('event_dt_simple'), calendar=cal1, locale=LOCALE_BERLIN)
        coll.insert(event, cal1)
        assert len(list(coll.search('Event'))) == 1
        event = Event.fromString(
            _get_text('event_dt_floating'), calendar=cal1, locale=LOCALE_BERLIN)
        coll.insert(event, cal1)
        assert len(list(coll.search('Search for me'))) == 1
        assert len(list(coll.search('Event'))) == 2

    def test_search_recurrence_id_only(self, coll_vdirs):
        """test searching for recurring events which only have a recuid event,
        and no master"""
        coll, vdirs = coll_vdirs
        assert len(list(coll.search('Event'))) == 0
        event = Event.fromString(
            _get_text('event_dt_recuid_no_master'), calendar=cal1, locale=LOCALE_BERLIN)
        coll.insert(event, cal1)
        assert len(list(coll.search('Event'))) == 1

    def test_search_recurrence_id_only_multi(self, coll_vdirs):
        """test searching for recurring events which only have a recuid event,
        and no master"""
        coll, vdirs = coll_vdirs
        assert len(list(coll.search('Event'))) == 0
        event = Event.fromString(
            _get_text('event_dt_multi_recuid_no_master'), calendar=cal1, locale=LOCALE_BERLIN)
        coll.insert(event, cal1)
        events = sorted(coll.search('Event'))
        assert len(events) == 2
        assert human_formatter('{start} {end} {title}')(events[0].attributes(
            dt.date.today())) == '30.06. 07:30 30.06. 12:00 Arbeit\x1b[0m'
        assert human_formatter('{start} {end} {title}')(events[1].attributes(
            dt.date.today())) == '07.07. 08:30 07.07. 12:00 Arbeit\x1b[0m'

    def test_delete_two_events(self, coll_vdirs, sleep_time):
        """testing if we can delete any of two events in two different
        calendars with the same filename"""
        coll, vdirs = coll_vdirs
        event1 = Event.fromString(
            _get_text('event_dt_simple'), calendar=cal1, locale=LOCALE_BERLIN)
        event2 = Event.fromString(
            _get_text('event_dt_simple'), calendar=cal2, locale=LOCALE_BERLIN)
        coll.insert(event1, cal1)
        sleep(sleep_time)  # make sure the etags are different
        coll.insert(event2, cal2)
        etag1 = list(vdirs[cal1].list())[0][1]
        etag2 = list(vdirs[cal2].list())[0][1]
        events = list(coll.get_localized(self.astart_berlin, self.aend_berlin))
        assert len(events) == 2
        assert events[0].calendar != events[1].calendar
        for event in events:
            if event.calendar == cal1:
                assert event.etag == etag1
            if event.calendar == cal2:
                assert event.etag == etag2

    def test_delete_recuid(self, coll_vdirs: CollVdirType):
        """Testing if we can delete a recuid (add it to exdate)"""
        coll, _ = coll_vdirs
        event_str = _get_text('event_rrule_recuid')
        event = Event.fromString(event_str, calendar=cal1, locale=LOCALE_BERLIN)
        coll.insert(event, cal1)
        event = coll.get_event('event_rrule_recurrence_id.ics', cal1)

        event = coll.delete_instance(
            'event_rrule_recurrence_id.ics',
            event.etag,
            calendar=cal1,
            rec_id=BERLIN.localize(dt.datetime(2014, 7, 14, 5)),
        )
        assert 'EXDATE;TZID=Europe/Berlin:20140714T050000' in event.raw.split()

        event = coll.delete_instance(
            'event_rrule_recurrence_id.ics',
            event.etag,
            calendar=cal1,
            rec_id=BERLIN.localize(dt.datetime(2014, 7, 21, 5)),
        )
        assert 'EXDATE;TZID=Europe/Berlin:20140714T050000,20140721T050000' in event.raw.split()

    def test_invalid_timezones(self, coll_vdirs):
        """testing if we can delete any of two events in two different
        calendars with the same filename"""
        coll, vdirs = coll_vdirs
        event = Event.fromString(
            _get_text('invalid_tzoffset'), calendar=cal1, locale=LOCALE_BERLIN)
        coll.insert(event, cal1)
        events = sorted(coll.search('Event'))
        assert len(events) == 1
        assert human_formatter('{start} {end} {title}')(events[0].attributes(dt.date.today())) == \
            '02.12. 08:00 02.12. 09:30 Some event\x1b[0m'

    def test_multi_uid_vdir(self, coll_vdirs, caplog, fix_caplog, sleep_time):
        coll, vdirs = coll_vdirs
        caplog.set_level(logging.WARNING)
        sleep(sleep_time)  # Make sure we get a new ctag on upload
        vdirs[cal1].upload(DumbItem(_get_text('event_dt_multi_uid'), uid='12345'))
        coll.update_db()
        assert list(coll.search('')) == []
        messages = [rec.message for rec in caplog.records]
        assert messages[0].startswith(
            "The .ics file at foobar/12345.ics contains multiple UIDs.\n"
        )
        assert messages[1].startswith(
            "Skipping foobar/12345.ics: \nThis event will not be available in khal."
        )


class TestDbCreation:

    def test_create_db(self, tmpdir):
        vdirpath = str(tmpdir) + '/' + cal1
        os.makedirs(vdirpath, mode=0o770)
        dbdir = str(tmpdir) + '/subdir/'
        dbpath = dbdir + 'khal.db'

        assert not os.path.isdir(dbdir)
        calendars = {cal1: {'name': cal1, 'path': vdirpath}}
        CalendarCollection(calendars, dbpath=dbpath, locale=LOCALE_BERLIN)
        assert os.path.isdir(dbdir)

    def test_failed_create_db(self, tmpdir):
        dbdir = str(tmpdir) + '/subdir/'
        dbpath = dbdir + 'khal.db'
        os.chmod(str(tmpdir), 400)

        calendars = {cal1: {'name': cal1, 'path': str(tmpdir)}}
        with pytest.raises(CouldNotCreateDbDir):
            CalendarCollection(calendars, dbpath=dbpath, locale=LOCALE_BERLIN)
        os.chmod(str(tmpdir), 777)


def test_event_different_timezones(coll_vdirs, sleep_time):
    coll, vdirs = coll_vdirs
    sleep(sleep_time)  # Make sure we get a new ctag on upload
    vdirs[cal1].upload(DumbItem(_get_text('event_dt_london'), uid='12345'))
    coll.update_db()

    events = coll.get_localized(
        BERLIN.localize(dt.datetime(2014, 4, 9, 0, 0)),
        BERLIN.localize(dt.datetime(2014, 4, 9, 23, 59)),
    )
    events = list(events)
    assert len(events) == 1
    event = events[0]
    assert event.start_local == LONDON.localize(dt.datetime(2014, 4, 9, 14))
    assert event.end_local == LONDON.localize(dt.datetime(2014, 4, 9, 19))
    assert event.start == LONDON.localize(dt.datetime(2014, 4, 9, 14))
    assert event.end == LONDON.localize(dt.datetime(2014, 4, 9, 19))

    # no event scheduled on the next day
    events = coll.get_localized(
        BERLIN.localize(dt.datetime(2014, 4, 10, 0, 0)),
        BERLIN.localize(dt.datetime(2014, 4, 10, 23, 59)),
    )
    events = list(events)
    assert len(events) == 0

    # now setting the local_timezone to Sydney
    coll.locale = LOCALE_SYDNEY
    events = coll.get_localized(
        SYDNEY.localize(dt.datetime(2014, 4, 9, 0, 0)),
        SYDNEY.localize(dt.datetime(2014, 4, 9, 23, 59)),
    )
    events = list(events)
    assert len(events) == 1
    event = events[0]
    assert event.start_local == SYDNEY.localize(dt.datetime(2014, 4, 9, 23))
    assert event.end_local == SYDNEY.localize(dt.datetime(2014, 4, 10, 4))
    assert event.start == LONDON.localize(dt.datetime(2014, 4, 9, 14))
    assert event.end == LONDON.localize(dt.datetime(2014, 4, 9, 19))

    # the event spans midnight Sydney, therefor it should also show up on the
    # next day
    events = coll.get_localized(SYDNEY.localize(dt.datetime(2014, 4, 10, 0, 0)),
                                SYDNEY.localize(dt.datetime(2014, 4, 10, 23, 59)))
    events = list(events)
    assert len(events) == 1
    assert event.start_local == SYDNEY.localize(dt.datetime(2014, 4, 9, 23))
    assert event.end_local == SYDNEY.localize(dt.datetime(2014, 4, 10, 4))


def test_default_calendar(coll_vdirs, sleep_time):
    """test if an update to the vdir is detected by the CalendarCollection"""
    coll, vdirs = coll_vdirs
    vdir = vdirs['foobar']
    event = coll.create_event_from_ics(event_today, 'foobar')

    assert len(list(coll.get_events_on(today))) == 0

    sleep(sleep_time)  # Make sure we get a new ctag on upload
    vdir.upload(event)
    sleep(sleep_time)
    href, etag = list(vdir.list())[0]
    assert len(list(coll.get_events_on(today))) == 0

    coll.update_db()
    sleep(sleep_time)
    assert len(list(coll.get_events_on(today))) == 1

    vdir.delete(href, etag)
    sleep(sleep_time)
    assert len(list(coll.get_events_on(today))) == 1

    coll.update_db()
    sleep(sleep_time)
    assert len(list(coll.get_events_on(today))) == 0


def test_only_update_old_event(coll_vdirs, monkeypatch, sleep_time):
    coll, vdirs = coll_vdirs

    href_one, etag_one = vdirs[cal1].upload(coll.create_event_from_ics(dedent("""
    BEGIN:VEVENT
    UID:meeting-one
    DTSTART;VALUE=DATE:20140909
    DTEND;VALUE=DATE:20140910
    SUMMARY:first meeting
    END:VEVENT
    """), cal1))

    sleep(sleep_time)  # Make sure we get a new etag for meeting-two

    href_two, etag_two = vdirs[cal1].upload(coll.create_event_from_ics(dedent("""
    BEGIN:VEVENT
    UID:meeting-two
    DTSTART;VALUE=DATE:20140910
    DTEND;VALUE=DATE:20140911
    SUMMARY:second meeting
    END:VEVENT
    """), cal1))

    sleep(sleep_time)
    coll.update_db()
    sleep(sleep_time)
    assert not coll._needs_update(cal1)

    old_update_vevent = coll._update_vevent
    updated_hrefs = []

    def _update_vevent(href, calendar):
        updated_hrefs.append(href)
        return old_update_vevent(href, calendar)
    monkeypatch.setattr(coll, '_update_vevent', _update_vevent)

    href_three, etag_three = vdirs[cal1].upload(coll.create_event_from_ics(dedent("""
    BEGIN:VEVENT
    UID:meeting-three
    DTSTART;VALUE=DATE:20140911
    DTEND;VALUE=DATE:20140912
    SUMMARY:third meeting
    END:VEVENT
    """), cal1))
    sleep(sleep_time)

    assert coll._needs_update(cal1)
    coll.update_db()
    sleep(sleep_time)
    assert updated_hrefs == [href_three]


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


def test_birthdays(coll_vdirs_birthday, sleep_time):
    coll, vdirs = coll_vdirs_birthday
    assert list(
        coll.get_floating(dt.datetime(1971, 3, 11), dt.datetime(1971, 3, 11, 23, 59, 59))
    ) == []
    sleep(sleep_time)  # Make sure we get a new ctag on upload
    vdirs[cal1].upload(DumbItem(card, 'unix'))
    coll.update_db()
    assert 'Unix\'s 41st birthday' == list(
        coll.get_floating(dt.datetime(2012, 3, 11), dt.datetime(2012, 3, 11)))[0].summary
    assert 'Unix\'s 42nd birthday' == list(
        coll.get_floating(dt.datetime(2013, 3, 11), dt.datetime(2013, 3, 11)))[0].summary
    assert 'Unix\'s 43rd birthday' == list(
        coll.get_floating(dt.datetime(2014, 3, 11), dt.datetime(2014, 3, 11)))[0].summary


def test_birthdays_29feb(coll_vdirs_birthday, sleep_time):
    """test how we deal with birthdays on 29th of feb in leap years"""
    coll, vdirs = coll_vdirs_birthday
    sleep(sleep_time)  # Make sure we get a new ctag on upload
    vdirs[cal1].upload(DumbItem(card_29thfeb, 'leap'))
    assert coll.needs_update()
    coll.update_db()
    events = list(
        coll.get_floating(dt.datetime(2004, 1, 1, 0, 0), dt.datetime(2004, 12, 31))
    )
    assert len(events) == 1
    assert events[0].summary == 'leapyear\'s 4th birthday (29th of Feb.)'
    assert events[0].start == dt.date(2004, 2, 29)
    events = list(
        coll.get_floating(dt.datetime(2005, 1, 1, 0, 0), dt.datetime(2005, 12, 31))
    )
    assert len(events) == 1
    assert events[0].summary == 'leapyear\'s 5th birthday (29th of Feb.)'
    assert events[0].start == dt.date(2005, 3, 1)
    assert list(
        coll.get_floating(dt.datetime(2001, 1, 1), dt.datetime(2001, 12, 31))
    )[0].summary == 'leapyear\'s 1st birthday (29th of Feb.)'
    assert list(
        coll.get_floating(dt.datetime(2002, 1, 1), dt.datetime(2002, 12, 31))
    )[0].summary == 'leapyear\'s 2nd birthday (29th of Feb.)'
    assert list(
        coll.get_floating(dt.datetime(2003, 1, 1), dt.datetime(2003, 12, 31))
    )[0].summary == 'leapyear\'s 3rd birthday (29th of Feb.)'
    assert list(
        coll.get_floating(dt.datetime(2023, 1, 1), dt.datetime(2023, 12, 31))
    )[0].summary == 'leapyear\'s 23rd birthday (29th of Feb.)'
    assert events[0].start == dt.date(2005, 3, 1)


def test_birthdays_no_year(coll_vdirs_birthday, sleep_time):
    coll, vdirs = coll_vdirs_birthday
    assert list(
        coll.get_floating(dt.datetime(1971, 3, 11), dt.datetime(1971, 3, 11, 23, 59, 59))
    ) == []
    sleep(sleep_time)  # Make sure we get a new ctag on upload
    vdirs[cal1].upload(DumbItem(card_no_year, 'vcard.vcf'))
    coll.update_db()
    events = list(coll.get_floating(dt.datetime(1971, 3, 11), dt.datetime(1971, 3, 11, 23, 59, 59)))
    assert len(events) == 1
    assert 'Unix\'s birthday' == events[0].summary
