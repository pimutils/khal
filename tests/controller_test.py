import datetime as dt
from textwrap import dedent

import pytest
from freezegun import freeze_time

from khal import exceptions
from khal.controllers import import_ics, khal_list, start_end_from_daterange
from khal.khalendar.vdir import Item

from . import utils
from .utils import _get_text

today = dt.date.today()
yesterday = today - dt.timedelta(days=1)
tomorrow = today + dt.timedelta(days=1)

event_allday_template = """BEGIN:VEVENT
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

event_format = '{calendar-color}{start-end-time-style:16} {title}'
event_format += '{repeat-symbol}{description-separator}{description}{calendar-color}'

conf = {'locale': utils.LOCALE_BERLIN,
        'default': {'timedelta': dt.timedelta(days=2), 'show_all_days': False}
        }


class TestGetAgenda:
    def test_new_event(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        event = coll.create_event_from_ics(event_today, utils.cal1)
        coll.insert(event)
        assert ['                 a meeting :: short description\x1b[0m'] == \
            khal_list(coll, [], conf, agenda_format=event_format, day_format="")

    def test_new_event_day_format(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        event = coll.create_event_from_ics(event_today, utils.cal1)
        coll.insert(event)
        assert ['Today\x1b[0m',
                '                 a meeting :: short description\x1b[0m'] == \
            khal_list(coll, [], conf, agenda_format=event_format, day_format="{name}")

    def test_agenda_default_day_format(self, coll_vdirs):
        with freeze_time('2016-04-10 12:33'):
            today = dt.date.today()
            event_today = event_allday_template.format(
                today.strftime('%Y%m%d'), tomorrow.strftime('%Y%m%d'))
            coll, vdirs = coll_vdirs
            event = coll.create_event_from_ics(event_today, utils.cal1)
            coll.insert(event)
            out = khal_list(
                coll, conf=conf, agenda_format=event_format, datepoint=[])
            assert [
                '\x1b[1m10.04.2016 12:33\x1b[0m\x1b[0m',
                '↦                a meeting :: short description\x1b[0m'] == out

    def test_agenda_fail(self, coll_vdirs):
        with freeze_time('2016-04-10 12:33'):
            coll, vdirs = coll_vdirs
            with pytest.raises(exceptions.FatalError):
                khal_list(coll, conf=conf, agenda_format=event_format, datepoint=['xyz'])
            with pytest.raises(exceptions.FatalError):
                khal_list(coll, conf=conf, agenda_format=event_format, datepoint=['today'])

    def test_empty_recurrence(self, coll_vdirs):
        coll, vidrs = coll_vdirs
        coll.insert(coll.create_event_from_ics(dedent(
            'BEGIN:VEVENT\r\n'
            'UID:no_recurrences\r\n'
            'SUMMARY:No recurrences\r\n'
            'RRULE:FREQ=DAILY;COUNT=2;INTERVAL=1\r\n'
            'EXDATE:20110908T130000\r\n'
            'EXDATE:20110909T130000\r\n'
            'DTSTART:20110908T130000\r\n'
            'DTEND:20110908T170000\r\n'
            'END:VEVENT\r\n'
        ), utils.cal1))
        assert '\n'.join(khal_list(coll, [], conf,
                         agenda_format=event_format, day_format="{name}")).lower() == ''


class TestImport:
    def test_import(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        view = {'event_format': '{title}'}
        conf = {'locale': utils.LOCALE_BERLIN, 'view': view}
        import_ics(coll, conf, _get_text('event_rrule_recuid'), batch=True)
        start_date = utils.BERLIN.localize(dt.datetime(2014, 4, 30))
        end_date = utils.BERLIN.localize(dt.datetime(2014, 9, 26))
        events = list(coll.get_localized(start_date, end_date))
        assert len(events) == 6
        events = sorted(events)
        assert events[1].start_local == utils.BERLIN.localize(dt.datetime(2014, 7, 7, 9, 0))
        assert utils.BERLIN.localize(dt.datetime(2014, 7, 14, 7, 0)) in \
            [ev.start for ev in events]

        import_ics(coll, conf, _get_text('event_rrule_recuid_update'), batch=True)
        events = list(coll.get_localized(start_date, end_date))
        for ev in events:
            print(ev.start)
            assert ev.calendar == 'foobar'
        assert len(events) == 5
        assert utils.BERLIN.localize(dt.datetime(2014, 7, 14, 7, 0)) not in \
            [ev.start_local for ev in events]

    def test_mix_datetime_types(self, coll_vdirs):
        """
        Test importing events with mixed tz-aware and tz-naive datetimes.
        """
        coll, vdirs = coll_vdirs
        view = {'event_format': '{title}'}
        import_ics(
            coll,
            {'locale': utils.LOCALE_BERLIN, 'view': view},
            _get_text('event_dt_mixed_awareness'),
            batch=True
        )
        start_date = utils.BERLIN.localize(dt.datetime(2015, 5, 29))
        end_date = utils.BERLIN.localize(dt.datetime(2015, 6, 3))
        events = list(coll.get_localized(start_date, end_date))
        assert len(events) == 2
        events = sorted(events)
        assert events[0].start_local == \
            utils.BERLIN.localize(dt.datetime(2015, 5, 30, 12, 0))
        assert events[0].end_local == \
            utils.BERLIN.localize(dt.datetime(2015, 5, 30, 16, 0))
        assert events[1].start_local == \
            utils.BERLIN.localize(dt.datetime(2015, 6, 2, 12, 0))
        assert events[1].end_local == \
            utils.BERLIN.localize(dt.datetime(2015, 6, 2, 16, 0))


def test_start_end():
    with freeze_time('2016-04-10'):
        start = dt.datetime(2016, 4, 10, 0, 0)
        end = dt.datetime(2016, 4, 11, 0, 0)
        assert (start, end) == start_end_from_daterange(('today',), locale=utils.LOCALE_BERLIN)


def test_start_end_default_delta():
    with freeze_time('2016-04-10'):
        start = dt.datetime(2016, 4, 10, 0, 0)
        end = dt.datetime(2016, 4, 11, 0, 0)
        assert (start, end) == start_end_from_daterange(('today',), utils.LOCALE_BERLIN)


def test_start_end_delta():
    with freeze_time('2016-04-10'):
        start = dt.datetime(2016, 4, 10, 0, 0)
        end = dt.datetime(2016, 4, 12, 0, 0)
        assert (start, end) == start_end_from_daterange(('today', '2d'), utils.LOCALE_BERLIN)


def test_start_end_empty():
    with freeze_time('2016-04-10'):
        start = dt.datetime(2016, 4, 10, 0, 0)
        end = dt.datetime(2016, 4, 11, 0, 0)
        assert (start, end) == start_end_from_daterange([], utils.LOCALE_BERLIN)


def test_start_end_empty_default():
    with freeze_time('2016-04-10'):
        start = dt.datetime(2016, 4, 10, 0, 0)
        end = dt.datetime(2016, 4, 13, 0, 0)
        assert (start, end) == start_end_from_daterange(
            [], utils.LOCALE_BERLIN,
            default_timedelta_date=dt.timedelta(days=3),
            default_timedelta_datetime=dt.timedelta(hours=1),
        )
