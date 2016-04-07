"""testing functions from the khal.aux"""
from datetime import date, datetime, time, timedelta
from collections import OrderedDict
import textwrap

import icalendar
import pytz
from freezegun import freeze_time

from khal.aux import construct_event, guessdatetimefstr, guesstimedeltafstr
from khal import aux
from khal.exceptions import FatalError
import pytest

from .aux import _get_all_vevents_file, _get_text, \
    normalize_component


today = date.today()
tomorrow = today + timedelta(days=1)

locale_de = {
    'timeformat': '%H:%M',
    'dateformat': '%d.%m.',
    'longdateformat': '%d.%m.%Y',
    'datetimeformat': '%d.%m. %H:%M',
    'longdatetimeformat': '%d.%m.%Y %H:%M',
    'default_timezone': pytz.timezone('Europe/Berlin'),
}


def _create_vevent(*args):
    """
    Adapt and return a default vevent for testing.

    Accepts an arbitrary amount of strings like 'DTSTART;VALUE=DATE:2013015'.
    Updates the default vevent if the key (the first word) is found and
    appends the value otherwise.
    """
    def_vevent = OrderedDict(
                     [('BEGIN', 'BEGIN:VEVENT'),
                      ('SUMMARY', 'SUMMARY:Äwesöme Event'),
                      ('DTSTART', 'DTSTART;VALUE=DATE:20131025'),
                      ('DTEND', 'DTEND;VALUE=DATE:20131026'),
                      ('DTSTAMP', 'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z'),
                      ('UID', 'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA')])

    for row in args:
        key = row.replace(':', ';').split(';')[0]
        def_vevent[key] = row

    def_vevent['END'] = 'END:VEVENT'
    return list(def_vevent.values())


def _create_testcases(*cases):
    return [(userinput, ('\r\n'.join(output) + '\r\n').encode('utf-8'))
            for userinput, output in cases]


def _replace_uid(event):
    """
    Replace an event's UID with E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA.
    """
    event.pop('uid')
    event.add('uid', 'E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA')
    return event


def test_normalize_component():
    assert normalize_component(textwrap.dedent("""
    BEGIN:VEVENT
    DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140409T093000
    END:VEVENT
    """)) != normalize_component(textwrap.dedent("""
    BEGIN:VEVENT
    DTSTART;TZID=Oyrope/Berlin;VALUE=DATE-TIME:20140409T093000
    END:VEVENT
    """))


class TestGuessDatetimefstr(object):
    tomorrow16 = datetime.combine(tomorrow, time(16, 0))

    def test_today(self):
        today13 = datetime.combine(date.today(), time(13, 0))
        assert (today13, False) == guessdatetimefstr(['today', '13:00'], locale_de)
        assert today == guessdatetimefstr(['today'], locale_de)[0].date()

    def test_tomorrow(self):
        assert (self.tomorrow16, False) == \
            guessdatetimefstr('tomorrow 16:00 16:00'.split(), locale=locale_de)

    def test_time_tomorrow(self):
        assert (self.tomorrow16, False) == \
            guessdatetimefstr('16:00'.split(), locale=locale_de, default_day=tomorrow)


class TestGuessTimedeltafstr(object):

    def test_single(self):
        assert timedelta(minutes=10) == guesstimedeltafstr('10m')

    def test_negative(self):
        assert timedelta(minutes=-10) == guesstimedeltafstr('-10m')

    def test_multi(self):
        assert timedelta(days=1, hours=-3, minutes=10) == \
            guesstimedeltafstr(' 1d -3H 10min ')

    def test_multi_nospace(self):
        assert timedelta(days=1, hours=-3, minutes=10) == \
            guesstimedeltafstr('1D-3hour10m')

    def test_garbage(self):
        with pytest.raises(ValueError):
                guesstimedeltafstr('10mbar')

    def test_moregarbage(self):
        with pytest.raises(ValueError):
                guesstimedeltafstr('foo10m')

    def test_same(self):
        assert timedelta(minutes=20) == \
            guesstimedeltafstr('10min 10minutes')


test_set_format_de = _create_testcases(
    # all-day-events
    # one day only
    ('25.10.2013 Äwesöme Event',
     _create_vevent('DTSTART;VALUE=DATE:20131025',
                    'DTEND;VALUE=DATE:20131026')),

    # 2 day
    ('15.08.2014 16.08. Äwesöme Event',
     _create_vevent('DTSTART;VALUE=DATE:20140815',
                    'DTEND;VALUE=DATE:20140817')),  # XXX

    # end date in next year and not specified
    ('29.12.2014 03.01. Äwesöme Event',
     _create_vevent('DTSTART;VALUE=DATE:20141229',
                    'DTEND;VALUE=DATE:20150104')),

    # end date in next year
    ('29.12.2014 03.01.2015 Äwesöme Event',
     _create_vevent('DTSTART;VALUE=DATE:20141229',
                    'DTEND;VALUE=DATE:20150104')),

    # datetime events
    # start and end date same, no explicit end date given
    ('25.10.2013 18:00 20:00 Äwesöme Event',
     _create_vevent(
        'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T180000',
        'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T200000')),

    # start and end date same, ends 24:00 which should be 00:00 (start) of next
    # day
    ('25.10.2013 18:00 24:00 Äwesöme Event',
     _create_vevent(
        'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T180000',
        'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131026T000000')),

    # start and end date same, explicit end date (but no year) given
    # XXX FIXME: if no explicit year is given for the end, this_year is used
    ('25.10.2013 18:00 26.10. 20:00 Äwesöme Event',
     _create_vevent(
        'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T180000',
        'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131026T200000')),

    # date ends next day, but end date not given
    ('25.10.2013 23:00 0:30 Äwesöme Event',
     _create_vevent(
        'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T230000',
        'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131026T003000')),

    # only start datetime given
    ('25.10.2013 06:00 Äwesöme Event',
     _create_vevent(
        'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T060000',
        'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T070000')),

    # timezone given
    ('25.10.2013 06:00 America/New_York Äwesöme Event',
     _create_vevent(
        'DTSTART;TZID=America/New_York;VALUE=DATE-TIME:20131025T060000',
        'DTEND;TZID=America/New_York;VALUE=DATE-TIME:20131025T070000'))
)


@freeze_time('20140216T120000')
def test_construct_event_format_de():
    for data_list, vevent in test_set_format_de:
        event = construct_event(data_list.split(),
                                locale=locale_de)

        assert _replace_uid(event).to_ical() == vevent


test_set_format_us = _create_testcases(
    ('12/31/1999 06:00 Äwesöme Event',
     _create_vevent(
        'DTSTART;TZID=America/New_York;VALUE=DATE-TIME:19991231T060000',
        'DTEND;TZID=America/New_York;VALUE=DATE-TIME:19991231T070000')),

    ('12/18 12/20 Äwesöme Event',
     _create_vevent('DTSTART;VALUE=DATE:20141218',
                    'DTEND;VALUE=DATE:20141221')),
)


def test_construct_event_format_us():
    locale_us = {
        'timeformat': '%H:%M',
        'dateformat': '%m/%d',
        'longdateformat': '%m/%d/%Y',
        'datetimeformat': '%m/%d %H:%M',
        'longdatetimeformat': '%m/%d/%Y %H:%M',
        'default_timezone': pytz.timezone('America/New_York'),
    }
    for data_list, vevent in test_set_format_us:
        with freeze_time('2014-02-16 12:00:00'):
            event = construct_event(data_list.split(), locale=locale_us)
            assert _replace_uid(event).to_ical() == vevent


test_set_format_de_complexer = _create_testcases(
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event',
     _create_vevent(
        'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140216T080000',
        'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20140216T090000')),

    # today until tomorrow
    ('22:00  1:00 Äwesöme Event',
     _create_vevent(
        'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140216T220000',
        'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20140217T010000')),

    ('15.06. Äwesöme Event',
     _create_vevent('DTSTART;VALUE=DATE:20140615',
                    'DTEND;VALUE=DATE:20140616')),
)


def test_construct_event_format_de_complexer():
    for data_list, vevent in test_set_format_de_complexer:
        with freeze_time('2014-02-16 12:00:00'):
            event = construct_event(data_list.split(), locale=locale_de)
            assert _replace_uid(event).to_ical() == vevent


test_set_leap_year = _create_testcases(
    ('29.02. Äwesöme Event',
     _create_vevent(
      'DTSTART;VALUE=DATE:20160229',
      'DTEND;VALUE=DATE:20160301',
      'DTSTAMP;VALUE=DATE-TIME:20160101T202122Z')),
)


def test_leap_year():
    for data_list, vevent in test_set_leap_year:
        with freeze_time('1999-1-1'):
            with pytest.raises(FatalError):
                event = construct_event(
                    data_list.split(), locale=locale_de)
        with freeze_time('2016-1-1 20:21:22'):
            event = construct_event(
                data_list.split(), locale=locale_de)
            assert _replace_uid(event).to_ical() == vevent


test_set_description = _create_testcases(
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event :: this is going to be awesome',
     _create_vevent(
        'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140216T080000',
        'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20140216T090000',
        'DESCRIPTION:this is going to be awesome')),

    # today until tomorrow
    ('22:00  1:00 Äwesöme Event :: Will be even better',
     _create_vevent(
        'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140216T220000',
        'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20140217T010000',
        'DESCRIPTION:Will be even better')),

    ('15.06. Äwesöme Event :: and again',
     _create_vevent('DTSTART;VALUE=DATE:20140615',
                    'DTEND;VALUE=DATE:20140616',
                    'DESCRIPTION:and again')),
)


def test_description():
    for data_list, vevent in test_set_description:
        with freeze_time('2014-02-16 12:00:00'):
            event = construct_event(data_list.split(), locale=locale_de)
            assert _replace_uid(event).to_ical() == vevent

test_set_repeat = _create_testcases(
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event',
     _create_vevent(
        'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140216T080000',
        'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20140216T090000',
        'DESCRIPTION:please describe the event',
        'RRULE:FREQ=DAILY;UNTIL=20150605T000000')))


def test_repeat():
    for data_list, vevent in test_set_repeat:
        with freeze_time('2014-02-16 12:00:00'):
            event = construct_event(data_list.split(),
                                    description='please describe the event',
                                    repeat='daily',
                                    until=['05.06.2015'],
                                    locale=locale_de)
            assert _replace_uid(event).to_ical() == vevent


test_set_alarm = _create_testcases(
    ('8:00 Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140216T080000',
      'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20140216T090000',
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'DESCRIPTION:please describe the event',
      'BEGIN:VALARM',
      'ACTION:DISPLAY',
      'DESCRIPTION:please describe the event',
      'TRIGGER:-PT23M',
      'END:VALARM',
      'END:VEVENT']))


def test_alarm():
    for data_list, vevent in test_set_alarm:
        with freeze_time('2014-02-16 12:00:00'):
            event = construct_event(data_list.split(),
                                    description='please describe the event',
                                    alarm='23m',
                                    locale=locale_de)
            assert _replace_uid(event).to_ical() == vevent


test_set_description_and_location = _create_testcases(
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event',
     _create_vevent(
        'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20140216T080000',
        'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20140216T090000',
        'DESCRIPTION:please describe the event',
        'LOCATION:in the office')))


def test_description_and_location():
    for data_list, vevent in test_set_description_and_location:
        with freeze_time('2014-02-16 12:00:00'):
            event = construct_event(data_list.split(),
                                    description='please describe the event',
                                    location='in the office',
                                    locale=locale_de)
            assert _replace_uid(event).to_ical() == vevent


class TestIcsFromList(object):

    def test_ics_from_list(self):
        vevents = _get_all_vevents_file('event_rrule_recuid')
        cal = aux.ics_from_list(list(vevents))
        assert normalize_component(cal.to_ical()) == \
            normalize_component(_get_text('event_rrule_recuid'))

    def test_ics_from_list_random_uid(self):
        vevents = _get_all_vevents_file('event_rrule_recuid')
        cal = aux.ics_from_list(list(vevents), random_uid=True)
        normalize_component(cal.to_ical())
        vevents = [item for item in cal.walk() if item.name == 'VEVENT']
        uids = set()
        for event in vevents:
            uids.add(event['UID'])
        assert len(uids) == 1
        assert event['UID'] != icalendar.vText('event_rrule_recurrence_id')
