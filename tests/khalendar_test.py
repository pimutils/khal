import datetime
import os
from textwrap import dedent

import pytest
import pytz

from vdirsyncer.storage.filesystem import FilesystemStorage
from vdirsyncer.storage.base import Item

from khal import aux

from khal.khalendar import Calendar, CalendarCollection
from khal.khalendar.event import Event
from khal.khalendar.backend import CouldNotCreateDbDir
import khal.khalendar.exceptions


today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)
tomorrow = today + datetime.timedelta(days=1)

event_allday_template = u"""BEGIN:VEVENT
SEQUENCE:0
UID:uid3@host1.com
DTSTART;VALUE=DATE:{}
DTEND;VALUE=DATE:{}
SUMMARY:a meeting
DESCRIPTION:short description
LOCATION:LDB Lobby
END:VEVENT"""

event_today = event_allday_template.format(today.strftime('%Y%m%d'),
                                           tomorrow.strftime('%Y%m%d'))
item_today = Item(event_today)

cal1 = 'foobar'
cal2 = 'work'
cal3 = 'private'

example_cals = [cal1, cal2, cal3]
berlin = pytz.timezone('Europe/Berlin')
locale = {'default_timezone': berlin,
          'local_timezone': berlin,
          }


@pytest.fixture
def cal_vdir(tmpdir):
    cal = Calendar(cal1, ':memory:', str(tmpdir), color='dark blue', locale=locale)
    vdir = FilesystemStorage(str(tmpdir), '.ics')
    return cal, vdir


@pytest.fixture
def coll_vdirs(tmpdir):
    coll = CalendarCollection()
    vdirs = dict()
    for name in example_cals:
        path = str(tmpdir) + '/' + name
        os.makedirs(path, mode=0o770)
        coll.append(
            Calendar(name, ':memory:', path, color='dark blue', locale=locale))
        vdirs[name] = FilesystemStorage(path, '.ics')
    coll.default_calendar_name = cal1
    return coll, vdirs


class TestCalendar(object):

    def test_create(self, cal_vdir):
        assert True

    def test_empty(self, cal_vdir):
        cal, vdir = cal_vdir
        events = cal.get_allday_by_time_range(today)
        assert events == list()
        assert list(vdir.list()) == list()

    def test_new_event(self, cal_vdir):
        cal, vdir = cal_vdir
        event = cal.new_event(event_today)
        assert event.calendar == cal1
        cal.new(event)
        events = cal.get_allday_by_time_range(today)
        assert len(events) == 1
        assert events[0].color == 'dark blue'
        events = cal.get_allday_by_time_range(tomorrow)
        assert len(events) == 0
        events = cal.get_allday_by_time_range(yesterday)
        assert len(events) == 0
        assert len(list(vdir.list())) == 1

    def test_db_needs_update(self, cal_vdir):
        cal, vdir = cal_vdir
        vdir.upload(item_today)
        cal.db_update()
        assert cal._db_needs_update() is False

    def test_db_needs_update_after_insert(self, cal_vdir):
        cal, vdir = cal_vdir
        event = cal.new_event(event_today)
        cal.new(event)
        assert cal._db_needs_update() is False


class TestVdirsyncerCompat(object):
    def test_list(self, cal_vdir):
        cal, vdir = cal_vdir
        event = Event(event_d, cal.name, locale=locale)
        cal.new(event)
        event = Event(event_today, cal.name, locale=locale)
        cal.new(event)
        hrefs = sorted(href for href, uid in cal._dbtool.list())
        assert hrefs == [
            'V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU.ics',
            'uid3@host1.com.ics'
        ]
        assert cal._dbtool.get('uid3@host1.com.ics').uid == 'uid3@host1.com'

today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)
tomorrow = today + datetime.timedelta(days=1)

aday = datetime.date(2014, 4, 9)
bday = datetime.date(2014, 4, 10)


event_allday_template = u"""BEGIN:VEVENT
SEQUENCE:0
UID:uid3@host1.com
DTSTART;VALUE=DATE:{}
DTEND;VALUE=DATE:{}
SUMMARY:a meeting
DESCRIPTION:short description
LOCATION:LDB Lobby
END:VEVENT"""


event_dt = """BEGIN:VEVENT
SUMMARY:An Event
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T093000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T103000
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""

event_d = """BEGIN:VEVENT
SUMMARY:Another Event
DTSTART;VALUE=DATE:20140409
DTEND;VALUE=DATE:20140410
DTSTAMP;VALUE=DATE-TIME:20140401T234817Z
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""

event_d_no_value = """BEGIN:VEVENT
SUMMARY:Another Event
DTSTART:20140409
DTEND:20140410
UID:V042MJ8B3SJNFXQOJL6P53OFMHJE8Z3VZWOU
END:VEVENT"""


class TestCollection(object):

    astart = datetime.datetime.combine(aday, datetime.time.min)
    aend = datetime.datetime.combine(aday, datetime.time.max)
    bstart = datetime.datetime.combine(bday, datetime.time.min)
    bend = datetime.datetime.combine(bday, datetime.time.max)

    def test_default_calendar(self, tmpdir):
        coll = CalendarCollection()
        coll.append(Calendar('foobar', ':memory:', str(tmpdir), readonly=True, locale=locale))
        coll.append(Calendar('home', ':memory:', str(tmpdir), locale=locale))
        coll.append(Calendar('work', ':memory:', str(tmpdir), readonly=True, locale=locale))
        assert coll.default_calendar_name is None
        with pytest.raises(ValueError):
            coll.default_calendar_name = 'work'
        assert coll.default_calendar_name is None
        with pytest.raises(ValueError):
            coll.default_calendar_name = 'unknownstuff'
        assert coll.default_calendar_name is None
        coll.default_calendar_name = 'home'
        assert coll.default_calendar_name == 'home'

    def test_empty(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        start = datetime.datetime.combine(today, datetime.time.min)
        end = datetime.datetime.combine(today, datetime.time.max)
        assert coll.get_allday_by_time_range(today) == list()
        assert coll.get_datetime_by_time_range(start, end) == list()

    def test_insert(self, coll_vdirs):
        """insert a datetime event"""
        coll, vdirs = coll_vdirs
        event = Event(event_dt, calendar='foo', locale=locale)
        coll.new(event, cal1)
        events = coll.get_datetime_by_time_range(self.astart, self.aend)
        assert len(events) == 1
        assert events[0].color == 'dark blue'
        assert events[0].calendar == cal1

        assert len(list(vdirs[cal1].list())) == 1
        assert len(list(vdirs[cal2].list())) == 0
        assert len(list(vdirs[cal3].list())) == 0

        assert coll.get_datetime_by_time_range(self.bstart, self.bend) == []

    def test_insert_d(self, coll_vdirs):
        """insert a date event"""
        coll, vdirs = coll_vdirs

        event = Event(event_d, calendar='foo', locale=locale)
        coll.new(event, cal1)
        events = coll.get_allday_by_time_range(aday)
        assert len(events) == 1
        assert events[0].calendar == cal1
        assert events[0].color == 'dark blue'
        assert len(list(vdirs[cal1].list())) == 1
        assert len(list(vdirs[cal2].list())) == 0
        assert len(list(vdirs[cal3].list())) == 0
        assert coll.get_datetime_by_time_range(self.bstart, self.bend) == []

    def test_insert_d_no_value(self, coll_vdirs):
        """insert a date event with no VALUE=DATE option"""
        coll, vdirs = coll_vdirs

        event = Event(event_d_no_value, calendar='foo', locale=locale)
        coll.new(event, cal1)
        events = coll.get_allday_by_time_range(aday)
        assert len(events) == 1
        assert events[0].calendar == cal1
        assert len(list(vdirs[cal1].list())) == 1
        assert len(list(vdirs[cal2].list())) == 0
        assert len(list(vdirs[cal3].list())) == 0
        assert coll.get_datetime_by_time_range(self.bstart, self.bend) == []

    def test_change(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        event = Event(event_dt, calendar='foo', locale=locale)
        coll.new(event, cal1)
        event = coll.get_datetime_by_time_range(self.astart, self.aend)[0]
        assert event.calendar == cal1

        coll.change_collection(event, cal2)
        events = coll.get_datetime_by_time_range(self.astart, self.aend)
        assert len(events) == 1
        assert events[0].calendar == cal2

    def test_newevent(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        event = aux.new_event(dtstart=aday,
                              timezone=berlin)
        event = coll.new_event(
            event.to_ical(),
            coll.default_calendar_name,
        )
        assert event.allday is False

    def test_insert_calendar_readonly(self, tmpdir):
        coll = CalendarCollection()
        coll.append(Calendar('foobar', ':memory:', str(tmpdir), readonly=True, locale=locale))
        coll.append(Calendar('home', ':memory:', str(tmpdir), locale=locale))
        coll.append(Calendar('work', ':memory:', str(tmpdir), readonly=True, locale=locale))
        event = Event(event_dt, calendar='home', locale=locale)
        with pytest.raises(khal.khalendar.exceptions.ReadOnlyCalendarError):
            coll.new(event, cal1)


@pytest.fixture
def cal_dbpath(tmpdir):
    name = 'testcal'
    vdirpath = str(tmpdir) + '/' + name
    dbpath = str(tmpdir) + '/subdir/' + 'khal.db'
    cal = Calendar(name, dbpath, vdirpath, locale=locale)

    return cal, dbpath


class TestDbCreation(object):

    def test_create_db(self, tmpdir):
        name = 'testcal'
        vdirpath = str(tmpdir) + '/' + name
        dbdir = str(tmpdir) + '/subdir/'
        dbpath = dbdir + 'khal.db'

        assert not os.path.isdir(dbdir)
        Calendar(name, dbpath, vdirpath, locale)
        assert os.path.isdir(dbdir)

    def test_failed_create_db(self, tmpdir):
        name = 'testcal'
        vdirpath = str(tmpdir) + '/' + name
        dbdir = str(tmpdir) + '/subdir/'
        dbpath = dbdir + 'khal.db'

        os.chmod(str(tmpdir), 400)

        with pytest.raises(CouldNotCreateDbDir):
            Calendar(name, dbpath, vdirpath, locale)


def test_default_calendar(cal_vdir):
    cal, vdir = cal_vdir
    event = cal.new_event(event_today)
    vdir.upload(event)
    uid, etag = list(vdir.list())[0]
    assert uid == 'uid3@host1.com.ics'
    assert len(cal.get_allday_by_time_range(today)) == 0
    cal.db_update()
    assert len(cal.get_allday_by_time_range(today)) == 1
    vdir.delete(uid, etag)
    assert len(cal.get_allday_by_time_range(today)) == 1
    cal.db_update()
    assert len(cal.get_allday_by_time_range(today)) == 0


def test_only_update_old_event(cal_vdir, monkeypatch):
    cal, vdir = cal_vdir

    href_one, etag_one = vdir.upload(cal.new_event(dedent("""
    BEGIN:VEVENT
    UID:meeting-one
    DTSTART;VALUE=DATE:20140909
    DTEND;VALUE=DATE:20140910
    SUMMARY:first meeting
    END:VEVENT
    """)))

    href_two, etag_two = vdir.upload(cal.new_event(dedent("""
    BEGIN:VEVENT
    UID:meeting-two
    DTSTART;VALUE=DATE:20140910
    DTEND;VALUE=DATE:20140911
    SUMMARY:second meeting
    END:VEVENT
    """)))

    cal.db_update()
    assert not cal._db_needs_update()

    old_update_vevent = cal._update_vevent
    updated_hrefs = []

    def _update_vevent(href):
        updated_hrefs.append(href)
        return old_update_vevent(href)
    monkeypatch.setattr(cal, '_update_vevent', _update_vevent)

    href_three, etag_three = vdir.upload(cal.new_event(dedent("""
    BEGIN:VEVENT
    UID:meeting-three
    DTSTART;VALUE=DATE:20140911
    DTEND;VALUE=DATE:20140912
    SUMMARY:third meeting
    END:VEVENT
    """)))

    assert cal._db_needs_update()
    cal.db_update()
    assert updated_hrefs == [href_three]
