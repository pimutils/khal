import datetime
import os

import pytest
import pytz

from vdirsyncer.storage import FilesystemStorage
from vdirsyncer.storage.base import Item

from khal import aux

from khal.khalendar import Calendar, CalendarCollection
from khal.khalendar.event import Event
from khal.khalendar.backend import CouldNotCreateDbDir


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

KWARGS = {
    'default_tz': pytz.timezone('Europe/Berlin'),
    'local_tz': pytz.timezone('Europe/Berlin'),
}

berlin = pytz.timezone('Europe/Berlin')


@pytest.fixture
def cal_vdir(tmpdir):
    cal = Calendar(cal1, ':memory:', str(tmpdir), **KWARGS)
    vdir = FilesystemStorage(str(tmpdir), '.ics')
    return cal, vdir


@pytest.fixture
def coll_vdirs(tmpdir):
    coll = CalendarCollection()
    vdirs = dict()
    for name in example_cals:
        path = str(tmpdir) + '/' + name
        os.makedirs(path, mode=0o770)
        coll.append(Calendar(name, ':memory:', path, **KWARGS))
        vdirs[name] = FilesystemStorage(path, '.ics')
    return coll, vdirs


class TestCalendarTest(object):

    def test_create(self, cal_vdir):
        assert True

    def test_empty(self, cal_vdir):
        cal, vdir = cal_vdir
        events = cal.get_allday_by_time_range(today)
        assert events == list()
        assert list(vdir.list()) == list()

    def test_new_event(self, cal_vdir):
        cal, vdir = cal_vdir
        event = cal.new_event(event_today, **KWARGS)
        assert event.account == cal1
        cal.new(event)
        events = cal.get_allday_by_time_range(today)
        assert len(events) == 1
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
        event = cal.new_event(event_today, **KWARGS)
        cal.new(event)
        assert cal._db_needs_update() is False

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
DTEND;VALUE=DATE:20140409
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

    def test_default_calendar(self, coll_vdirs):
        coll, vdir = coll_vdirs
        assert coll.names == ['foobar', 'work', 'private']
        assert coll.default_calendar_name == 'foobar'

    def test_default_calendar_not_readonly(self, tmpdir):
        coll = CalendarCollection()
        coll.append(Calendar('foobar', ':memory:', str(tmpdir), readonly=True, **KWARGS))
        coll.append(Calendar('home', ':memory:', str(tmpdir), **KWARGS))
        coll.append(Calendar('work', ':memory:', str(tmpdir), readonly=True, **KWARGS))
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
        event = Event(event_dt, account='foo', **KWARGS)
        coll.new(event, cal1)
        events = coll.get_datetime_by_time_range(self.astart, self.aend)
        assert len(events) == 1
        assert events[0].account == cal1

        assert len(list(vdirs[cal1].list())) == 1
        assert len(list(vdirs[cal2].list())) == 0
        assert len(list(vdirs[cal3].list())) == 0

        assert coll.get_datetime_by_time_range(self.bstart, self.bend) == []

    def test_insert_d(self, coll_vdirs):
        """insert a date event"""
        coll, vdirs = coll_vdirs

        event = Event(event_d, account='foo', **KWARGS)
        coll.new(event, cal1)
        events = coll.get_allday_by_time_range(aday)
        assert len(events) == 1
        assert events[0].account == cal1
        assert len(list(vdirs[cal1].list())) == 1
        assert len(list(vdirs[cal2].list())) == 0
        assert len(list(vdirs[cal3].list())) == 0
        assert coll.get_datetime_by_time_range(self.bstart, self.bend) == []

    def test_insert_d_no_value(self, coll_vdirs):
        """insert a date event with no VALUE=DATE option"""
        coll, vdirs = coll_vdirs

        event = Event(event_d_no_value, account='foo', **KWARGS)
        coll.new(event, cal1)
        events = coll.get_allday_by_time_range(aday)
        assert len(events) == 1
        assert events[0].account == cal1
        assert len(list(vdirs[cal1].list())) == 1
        assert len(list(vdirs[cal2].list())) == 0
        assert len(list(vdirs[cal3].list())) == 0
        assert coll.get_datetime_by_time_range(self.bstart, self.bend) == []

    def test_change(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        event = Event(event_dt, account='foo', **KWARGS)
        coll.new(event, cal1)
        event = coll.get_datetime_by_time_range(self.astart, self.aend)[0]
        assert event.account == cal1

        coll.change_collection(event, cal2)
        events = coll.get_datetime_by_time_range(self.astart, self.aend)
        assert len(events) == 1
        assert events[0].account == cal2

    def test_newevent(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        event = aux.new_event(dtstart=aday,
                              timezone=berlin)
        event = coll.new_event(
            event.to_ical(),
            coll.default_calendar_name,
            **KWARGS)
        assert event.allday is False


@pytest.fixture
def cal_dbpath(tmpdir):
    name = 'testcal'
    vdirpath = str(tmpdir) + '/' + name
    dbpath = str(tmpdir) + '/subdir/' + 'khal.db'
    cal = Calendar(name, dbpath, vdirpath, **KWARGS)

    return cal, dbpath


class TestDbCreation(object):

    def test_create_db(self, tmpdir):
        name = 'testcal'
        vdirpath = str(tmpdir) + '/' + name
        dbdir = str(tmpdir) + '/subdir/'
        dbpath = dbdir + 'khal.db'

        assert not os.path.isdir(dbdir)
        Calendar(name, dbpath, vdirpath, **KWARGS)
        assert os.path.isdir(dbdir)

    def test_failed_create_db(self, tmpdir):
        name = 'testcal'
        vdirpath = str(tmpdir) + '/' + name
        dbdir = str(tmpdir) + '/subdir/'
        dbpath = dbdir + 'khal.db'

        os.chmod(str(tmpdir), 400)

        with pytest.raises(CouldNotCreateDbDir):
            Calendar(name, dbpath, vdirpath, **KWARGS)
