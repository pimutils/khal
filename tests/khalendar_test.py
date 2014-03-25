import datetime

import pytest

from vdirsyncer.storage import FilesystemStorage
from vdirsyncer.storage.base import Item

from khal.khalendar import Calendar


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

calname = 'foobar'


@pytest.fixture
def cal_vdir(tmpdir):
    cal = Calendar(calname, ':memory:', str(tmpdir))
    vdir = FilesystemStorage(str(tmpdir), '.ics')
    return cal, vdir


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
        event = cal.new_event(event_today)
        assert event.account == calname
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
        event = cal.new_event(event_today)
        cal.new(event)
        assert cal._db_needs_update() is False
