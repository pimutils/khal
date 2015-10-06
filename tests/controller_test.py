import datetime
import os
from textwrap import dedent

import pytest
import pytz

from vdirsyncer.storage.filesystem import FilesystemStorage
from vdirsyncer.storage.base import Item


from khal.khalendar import Calendar, CalendarCollection
from khal.controllers import get_agenda, import_ics

from .aux import _get_text


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

BERLIN = pytz.timezone('Europe/Berlin')

locale = {'default_timezone': BERLIN,
          'local_timezone': BERLIN,
          'dateformat': '%d.%m.%Y',
          'timeformat': '%H:%M',
          'longdateformat': '%d.%m.%Y %H:%M',
          }


@pytest.fixture
def cal_vdir(tmpdir):
    cal = Calendar(cal1, ':memory:', str(tmpdir), locale=locale)
    vdir = FilesystemStorage(str(tmpdir), '.ics')
    return cal, vdir


@pytest.fixture
def coll_vdirs(tmpdir):
    coll = CalendarCollection(locale=locale)
    vdirs = dict()
    for name in example_cals:
        path = str(tmpdir) + '/' + name
        os.makedirs(path, mode=0o770)
        coll.append(Calendar(name, ':memory:', path, locale=locale))
        vdirs[name] = FilesystemStorage(path, '.ics')
    coll.default_calendar_name = cal1
    return coll, vdirs


class TestGetAgenda(object):
    def test_new_event(self, cal_vdir):
        cal, vdir = cal_vdir
        event = cal.new_event(event_today)
        cal.new(event)
        assert ['\x1b[1mToday:\x1b[0m', 'a meeting'] == \
            get_agenda(cal, locale)

    def test_empty_recurrence(self, cal_vdir):
        cal, vdir = cal_vdir
        cal.new(cal.new_event(dedent(
            u'BEGIN:VEVENT\r\n'
            u'UID:no_recurrences\r\n'
            u'SUMMARY:No recurrences\r\n'
            u'RRULE:FREQ=DAILY;COUNT=2;INTERVAL=1\r\n'
            u'EXDATE:20110908T130000\r\n'
            u'EXDATE:20110909T130000\r\n'
            u'DTSTART:20110908T130000\r\n'
            u'DTEND:20110908T170000\r\n'
            u'END:VEVENT\r\n'
        )))
        assert 'no events' in '\n'.join(get_agenda(
            cal, locale,
            dates=[datetime.date(2011, 9, 8),
                   datetime.date(2011, 9, 9)]
        )).lower()


class TestImport(object):
    def test_import(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        import_ics(coll, {'locale': locale}, _get_text('event_rrule_recuid'),
                   batch=True)
        start_date = datetime.datetime(2014, 4, 30)
        end_date = datetime.datetime(2014, 9, 26)
        events = coll.get_datetime_by_time_range(start_date, end_date)
        assert len(events) == 6
        events = sorted(events)
        assert events[1].start_local == BERLIN.localize(datetime.datetime(2014, 7, 7, 9, 0))
        assert BERLIN.localize(datetime.datetime(2014, 7, 14, 7, 0)) in [ev.start for ev in events]

        import_ics(coll, {'locale': locale}, _get_text('event_rrule_recuid_update'),
                   batch=True)
        events = coll.get_datetime_by_time_range(start_date, end_date)
        for ev in events:
            print(ev.start)
        assert len(events) == 5
        assert BERLIN.localize(datetime.datetime(2014, 7, 14, 7, 0)) not in \
            [ev.start_local for ev in events]
