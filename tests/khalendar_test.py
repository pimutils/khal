from datetime import datetime, date, timedelta, time
import os
from time import sleep
from textwrap import dedent

import pytest

from vdirsyncer.storage.base import Item

import khal.aux
from khal.khalendar import CalendarCollection
from khal.khalendar.event import Event
from khal.khalendar.backend import CouldNotCreateDbDir
import khal.khalendar.exceptions
from .aux import _get_text, cal1, cal2, cal3, normalize_component
from . import aux

from freezegun import freeze_time

today = date.today()
yesterday = today - timedelta(days=1)
tomorrow = today + timedelta(days=1)

event_allday_template = u"""BEGIN:VEVENT
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


class TestCalendar(object):

    def test_create(self, coll_vdirs):
        assert True

    def test_new_event(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        event = coll.new_event(event_today, cal1)
        assert event.calendar == cal1
        coll.new(event)
        events = list(coll.get_events_on(today))
        assert len(events) == 1
        assert events[0].color == 'dark blue'
        assert len(list(coll.get_events_on(tomorrow))) == 0
        assert len(list(coll.get_events_on(yesterday))) == 0
        assert len(list(vdirs[cal1].list())) == 1

    def test_sanity(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        mtimes = dict()
        for i in range(100):
            for cal in coll._calendars:
                mtime = os.path.getmtime(coll._calendars[cal]['path'])
                if mtimes.get(cal):
                    assert mtimes[cal] == mtime
                else:
                    mtimes[cal] = mtime

    def test_db_needs_update(self, coll_vdirs):
        coll, vdirs = coll_vdirs

        print('init')
        for calendar in coll._calendars:
            print('{}: saved ctag: {}, vdir ctag: {}'.format(
                calendar, coll._local_ctag(calendar), coll._backend.get_ctag(calendar)))
        assert len(list(vdirs[cal1].list())) == 0
        assert coll._needs_update(cal1) is False
        sleep(0.01)

        vdirs[cal1].upload(item_today)
        print('upload')
        for calendar in coll._calendars:
            print('{}: saved ctag: {}, vdir ctag: {}'.format(
                calendar, coll._local_ctag(calendar), coll._backend.get_ctag(calendar)))
        assert len(list(vdirs[cal1].list())) == 1
        assert coll._needs_update(cal1) is True
        coll.update_db()
        print('updated')
        for calendar in coll._calendars:
            print('{}: saved ctag: {}, vdir ctag: {}'.format(
                calendar, coll._local_ctag(calendar), coll._backend.get_ctag(calendar)))
        assert coll._needs_update(cal1) is False


class TestVdirsyncerCompat(object):
    def test_list(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        event = Event.fromString(event_d, calendar=cal1, locale=aux.locale)
        coll.new(event)
        event = Event.fromString(event_today, calendar=cal1, locale=aux.locale)
        coll.new(event)
        hrefs = sorted(href for href, uid in coll._backend.list(cal1))
        assert set(str(coll._backend.get(href, calendar=cal1).uid) for href in hrefs) == set((
            'uid3@host1.com',
            'V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU',
        ))

aday = date(2014, 4, 9)
bday = date(2014, 4, 10)


event_dt = _get_text('event_dt_simple')
event_d = _get_text('event_d')
event_d_no_value = _get_text('event_d_no_value')


class TestCollection(object):

    astart = datetime.combine(aday, time.min)
    aend = datetime.combine(aday, time.max)
    bstart = datetime.combine(bday, time.min)
    bend = datetime.combine(bday, time.max)
    astart_berlin = aux.BERLIN.localize(astart)
    aend_berlin = aux.BERLIN.localize(aend)
    bstart_berlin = aux.BERLIN.localize(bstart)
    bend_berlin = aux.BERLIN.localize(bend)

    def test_default_calendar(self, tmpdir):
        calendars = {
            'foobar': {'name': 'foobar', 'path': str(tmpdir), 'readonly': True},
            'home': {'name': 'home', 'path': str(tmpdir)},
            'work': {'name': 'work', 'path': str(tmpdir), 'readonly': True},
        }
        coll = CalendarCollection(calendars=calendars, locale=aux.locale, dbpath=':memory:')
        assert coll.default_calendar_name is None
        with pytest.raises(ValueError):
            coll.default_calendar_name = 'work'
        assert coll.default_calendar_name is None
        with pytest.raises(ValueError):
            coll.default_calendar_name = 'unknownstuff'
        assert coll.default_calendar_name is None
        coll.default_calendar_name = 'home'
        assert coll.default_calendar_name == 'home'
        assert coll.writable_names == ['home']

    def test_empty(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        start = datetime.combine(today, time.min)
        end = datetime.combine(today, time.max)
        assert list(coll.get_floating(start, end)) == list()
        assert list(coll.get_localized(aux.BERLIN.localize(start),
                                       aux.BERLIN.localize(end))) == list()

    def test_insert(self, coll_vdirs):
        """insert a localized event"""
        coll, vdirs = coll_vdirs
        event = Event.fromString(event_dt, calendar=cal1, locale=aux.locale)
        coll.new(event, cal1)
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
        event = Event.fromString(event_d, calendar=cal1, locale=aux.locale)
        coll.new(event, cal1)
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

        event = Event.fromString(event_d_no_value, calendar=cal1, locale=aux.locale)
        coll.new(event, cal1)
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
        event = Event.fromString(event_dt, href='xyz.ics', calendar=cal1, locale=aux.locale)
        coll.new(event, cal1)
        event_from_db = coll.get_event(SIMPLE_EVENT_UID + '.ics', cal1)
        with freeze_time('2016-1-1'):
            assert normalize_component(event_from_db.raw) == \
                normalize_component(_get_text('event_dt_simple_inkl_vtimezone'))

    def test_change(self, coll_vdirs):
        """moving an event from one calendar to another"""
        coll, vdirs = coll_vdirs
        event = Event.fromString(event_dt, calendar=cal1, locale=aux.locale)
        coll.new(event, cal1)
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
            _get_text('event_dt_simple'), calendar=cal1, locale=aux.locale)
        coll.new(event, cal1)
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
        event = khal.aux.new_event(dtstart=aday, timezone=aux.BERLIN)
        event = coll.new_event(event.to_ical(), coll.default_calendar_name)
        assert event.allday is False

    def test_modify_readonly_calendar(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        coll._calendars[cal1]['readonly'] = True
        coll._calendars[cal3]['readonly'] = True
        event = Event.fromString(event_dt, calendar=cal1, locale=aux.locale)

        with pytest.raises(khal.khalendar.exceptions.ReadOnlyCalendarError):
            coll.new(event, cal1)
        with pytest.raises(khal.khalendar.exceptions.ReadOnlyCalendarError):
            # params don't really matter here
            coll.delete('href', 'eteg', cal1)

    def test_search(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        assert len(list(coll.search('Event'))) == 0
        event = Event.fromString(
            _get_text('event_dt_simple'), calendar=cal1, locale=aux.locale)
        coll.new(event, cal1)
        assert len(list(coll.search('Event'))) == 1

    def test_get_events_at(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        a_time = aux.BERLIN.localize(datetime(2014, 4, 9, 10))
        b_time = aux.BERLIN.localize(datetime(2014, 4, 9, 11))
        assert len(list(coll.get_events_at(a_time))) == 0
        event = Event.fromString(
            _get_text('event_dt_simple'), calendar=cal1, locale=aux.locale)
        coll.new(event, cal1)
        assert len(list(coll.get_events_at(a_time))) == 1
        assert len(list(coll.get_events_at(b_time))) == 0

    def test_delete_two_events(self, coll_vdirs):
            """testing if we can delete any of two events in two different
            calendars with the same filename"""
            coll, vdirs = coll_vdirs
            event1 = Event.fromString(_get_text('event_dt_simple'),
                                      calendar=cal1, locale=aux.locale)
            event2 = Event.fromString(_get_text('event_dt_simple'),
                                      calendar=cal2, locale=aux.locale)
            coll.new(event1, cal1)
            sleep(0.1)  # make sure the etags are different
            coll.new(event2, cal2)
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


class TestDbCreation(object):

    def test_create_db(self, tmpdir):
        vdirpath = str(tmpdir) + '/' + cal1
        os.makedirs(vdirpath, mode=0o770)
        dbdir = str(tmpdir) + '/subdir/'
        dbpath = dbdir + 'khal.db'

        assert not os.path.isdir(dbdir)
        calendars = {cal1: {'name': cal1, 'path': vdirpath}}
        CalendarCollection(calendars, dbpath=dbpath, locale=aux.locale)
        assert os.path.isdir(dbdir)

    def test_failed_create_db(self, tmpdir):
        dbdir = str(tmpdir) + '/subdir/'
        dbpath = dbdir + 'khal.db'
        os.chmod(str(tmpdir), 400)

        calendars = {cal1: {'name': cal1, 'path': str(tmpdir)}}
        with pytest.raises(CouldNotCreateDbDir):
            CalendarCollection(calendars, dbpath=dbpath, locale=aux.locale)


def test_default_calendar(coll_vdirs):
    """test if an update to the vdir is detected by the CalendarCollection"""
    coll, vdirs = coll_vdirs
    vdir = vdirs['foobar']
    event = coll.new_event(event_today, 'foobar')
    vdir.upload(event)
    sleep(0.01)
    href, etag = list(vdir.list())[0]
    assert len(list(coll.get_events_on(today))) == 0
    coll.update_db()
    sleep(0.01)
    assert len(list(coll.get_events_on(today))) == 1
    vdir.delete(href, etag)
    sleep(0.01)
    assert len(list(coll.get_events_on(today))) == 1
    coll.update_db()
    sleep(0.01)
    assert len(list(coll.get_events_on(today))) == 0


def test_only_update_old_event(coll_vdirs, monkeypatch):
    coll, vdirs = coll_vdirs

    href_one, etag_one = vdirs[cal1].upload(coll.new_event(dedent("""
    BEGIN:VEVENT
    UID:meeting-one
    DTSTART;VALUE=DATE:20140909
    DTEND;VALUE=DATE:20140910
    SUMMARY:first meeting
    END:VEVENT
    """), cal1))

    href_two, etag_two = vdirs[cal1].upload(coll.new_event(dedent("""
    BEGIN:VEVENT
    UID:meeting-two
    DTSTART;VALUE=DATE:20140910
    DTEND;VALUE=DATE:20140911
    SUMMARY:second meeting
    END:VEVENT
    """), cal1))

    sleep(0.01)
    coll.update_db()
    sleep(0.01)
    assert not coll._needs_update(cal1)

    old_update_vevent = coll._update_vevent
    updated_hrefs = []

    def _update_vevent(href, calendar):
        updated_hrefs.append(href)
        return old_update_vevent(href, calendar)
    monkeypatch.setattr(coll, '_update_vevent', _update_vevent)

    href_three, etag_three = vdirs[cal1].upload(coll.new_event(dedent("""
    BEGIN:VEVENT
    UID:meeting-three
    DTSTART;VALUE=DATE:20140911
    DTEND;VALUE=DATE:20140912
    SUMMARY:third meeting
    END:VEVENT
    """), cal1))
    sleep(0.01)

    assert coll._needs_update(cal1)
    coll.update_db()
    sleep(0.01)
    assert updated_hrefs == [href_three]
