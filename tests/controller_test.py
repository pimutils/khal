import datetime
import os

import pytest
import pytz

from vdirsyncer.storage import FilesystemStorage
from vdirsyncer.storage.base import Item


from khal.khalendar import Calendar, CalendarCollection
from khal.controllers import get_agenda


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

dateformat = '%d.%m.%Y'
longdateformat = '%d.%m.%Y %H:%M'


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

    def test_new_event(self, cal_vdir):
        cal, vdir = cal_vdir
        event = cal.new_event(event_today, **KWARGS)
        cal.new(event)
        assert ['\x1b[1mToday:\x1b[0m', 'a meeting'] == \
            get_agenda(cal, dateformat, longdateformat)
