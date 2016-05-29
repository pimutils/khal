import datetime
from textwrap import dedent

from khal.khalendar.vdir import Item

from khal.controllers import import_ics, get_list_from_str

from .aux import _get_text
from . import aux


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

event_format = '{calendar-color}{start-end-time-style:16} {title}'
event_format += '{recurse}{description-separator}{description}{calendar-color}'


class TestGetAgenda(object):
    def test_new_event(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        event = coll.new_event(event_today, aux.cal1)
        coll.new(event)
        assert ['                 a meeting :: short description\x1b[0m'] == \
            get_list_from_str(coll, aux.locale, [], format=event_format, default_timedelta='1d',
                              day_format="")

    def test_new_event_day_format(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        event = coll.new_event(event_today, aux.cal1)
        coll.new(event)
        assert ['Today\x1b[0m',
                '                 a meeting :: short description\x1b[0m'] == \
            get_list_from_str(coll, aux.locale, [], format=event_format, default_timedelta='1d',
                              day_format="{name}")

    def test_empty_recurrence(self, coll_vdirs):
        coll, vidrs = coll_vdirs
        coll.new(coll.new_event(dedent(
            'BEGIN:VEVENT\r\n'
            'UID:no_recurrences\r\n'
            'SUMMARY:No recurrences\r\n'
            'RRULE:FREQ=DAILY;COUNT=2;INTERVAL=1\r\n'
            'EXDATE:20110908T130000\r\n'
            'EXDATE:20110909T130000\r\n'
            'DTSTART:20110908T130000\r\n'
            'DTEND:20110908T170000\r\n'
            'END:VEVENT\r\n'
        ), aux.cal1))
        assert 'no events' in '\n'.join(get_list_from_str(coll, aux.locale, [],
                                        format=event_format,
                                        default_timedelta='1d')).lower()


class TestImport(object):
    def test_import(self, coll_vdirs):
        coll, vdirs = coll_vdirs
        view = {'event_format': '{title}'}
        conf = {'locale': aux.locale, 'view': view}
        import_ics(coll, conf, _get_text('event_rrule_recuid'),
                   batch=True)
        start_date = aux.BERLIN.localize(datetime.datetime(2014, 4, 30))
        end_date = aux.BERLIN.localize(datetime.datetime(2014, 9, 26))
        events = list(coll.get_localized(start_date, end_date))
        assert len(events) == 6
        events = sorted(events)
        assert events[1].start_local == aux.BERLIN.localize(datetime.datetime(2014, 7, 7, 9, 0))
        assert aux.BERLIN.localize(datetime.datetime(2014, 7, 14, 7, 0)) in \
            [ev.start for ev in events]

        import_ics(coll, conf, _get_text('event_rrule_recuid_update'),
                   batch=True)
        events = list(coll.get_localized(start_date, end_date))
        for ev in events:
            print(ev.start)
        assert len(events) == 5
        assert aux.BERLIN.localize(datetime.datetime(2014, 7, 14, 7, 0)) not in \
            [ev.start_local for ev in events]

    def test_mix_datetime_types(self, coll_vdirs):
        """
        Test importing events with mixed tz-aware and tz-naive datetimes.
        """
        coll, vdirs = coll_vdirs
        view = {'event_format': '{title}'}
        import_ics(
            coll,
            {'locale': aux.locale, 'view': view},
            _get_text('event_dt_mixed_awareness'),
            batch=True
        )
        start_date = aux.BERLIN.localize(datetime.datetime(2015, 5, 29))
        end_date = aux.BERLIN.localize(datetime.datetime(2015, 6, 3))
        events = list(coll.get_localized(start_date, end_date))
        assert len(events) == 2
        events = sorted(events)
        assert events[0].start_local == \
            aux.BERLIN.localize(datetime.datetime(2015, 5, 30, 12, 0))
        assert events[0].end_local == \
            aux.BERLIN.localize(datetime.datetime(2015, 5, 30, 16, 0))
        assert events[1].start_local == \
            aux.BERLIN.localize(datetime.datetime(2015, 6, 2, 12, 0))
        assert events[1].end_local == \
            aux.BERLIN.localize(datetime.datetime(2015, 6, 2, 16, 0))
