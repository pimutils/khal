# vim: set fileencoding=utf-8:
"""testing functions from the khal.aux"""
from datetime import date, datetime, time, timedelta
import textwrap

import icalendar
import pytz

from khal.aux import construct_event, guessdatetimefstr
from khal import aux
from khal.compat import to_bytes

from .aux import _get_all_vevents_file, _get_text, \
    normalize_component


def _now():
    """mock datetime.datetime.now"""
    return datetime(2014, 2, 16, 12, 0, 0, 0)


today = date.today()
tomorrow = today + timedelta(days=1)
today_s = '{0:02}{1:02}{2:02}'.format(*today.timetuple()[0:3])
tomorrow_s = '{0:02}{1:02}{2:02}'.format(*tomorrow.timetuple()[0:3])
this_year_s = str(today.year)

locale_de = {
    'timeformat': '%H:%M',
    'dateformat': '%d.%m.',
    'longdateformat': '%d.%m.%Y',
    'datetimeformat': '%d.%m. %H:%M',
    'longdatetimeformat': '%d.%m.%Y %H:%M',
    'default_timezone': pytz.timezone('Europe/Berlin'),
}


def _create_testcases(*cases):
    return [(userinput, to_bytes('\r\n'.join(output) + '\r\n', 'utf-8'))
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


test_set_format_de = _create_testcases(
    # all-day-events
    # one day only
    ('25.10.2013 Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;VALUE=DATE:20131025',
      'DTEND;VALUE=DATE:20131026',
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'END:VEVENT']),
    # 2 day
    ('15.08.2014 16.08. Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;VALUE=DATE:20140815',
      'DTEND;VALUE=DATE:20140817',  # XXX
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'END:VEVENT']),
    # end date in next year and not specified
    ('29.12.2014 03.01. Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;VALUE=DATE:20141229',
      'DTEND;VALUE=DATE:20150104',
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'END:VEVENT']),
    # end date in next year
    ('29.12.2014 03.01.2015 Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;VALUE=DATE:20141229',
      'DTEND;VALUE=DATE:20150104',
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'END:VEVENT']),
    # datetime events
    # start and end date same, no explicit end date given
    ('25.10.2013 18:00 20:00 Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T180000',
      'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T200000',
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'END:VEVENT']),
    # start and end date same, explicit end date (but no year) given
    # XXX FIXME: if no explicit year is given for the end, this_year is used
    ('25.10.2013 18:00 26.10. 20:00 Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T180000',
      'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131026T200000',
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'END:VEVENT']),
    # date ends next day, but end date not given
    ('25.10.2013 23:00 0:30 Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T230000',
      'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131026T003000',
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'END:VEVENT']),
    # only start datetime given
    ('25.10.2013 06:00 Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T060000',
      'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T070000',
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'END:VEVENT']),
    # timezone given
    ('25.10.2013 06:00 America/New_York Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      ('DTSTART;TZID=America/New_York;VALUE=DATE-TIME:'
       '20131025T060000'),
      ('DTEND;TZID=America/New_York;VALUE=DATE-TIME:'
       '20131025T070000'),
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'END:VEVENT'])
)


def test_construct_event_format_de():
    for data_list, vevent in test_set_format_de:
        event = construct_event(data_list.split(),
                                _now=_now,
                                locale=locale_de)

        assert _replace_uid(event).to_ical() == vevent


test_set_format_us = _create_testcases(
    ('12/31/1999 06:00 Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;TZID=America/New_York;VALUE=DATE-TIME:19991231T060000',
      'DTEND;TZID=America/New_York;VALUE=DATE-TIME:19991231T070000',
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'END:VEVENT']),
    ('12/18 12/20 Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;VALUE=DATE:{}1218'.format(this_year_s),
      'DTEND;VALUE=DATE:{}1221'.format(this_year_s),
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'END:VEVENT']),
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
        event = construct_event(data_list.split(),
                                _now=_now,
                                locale=locale_us)
        assert _replace_uid(event).to_ical() == vevent


test_set_format_de_complexer = _create_testcases(
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:{}T080000'.format(today_s),
      'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:{}T090000'.format(today_s),
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'END:VEVENT']),
    # today until tomorrow
    ('22:00  1:00 Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:{}T220000'.format(today_s),
      'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:{}T010000'.format(tomorrow_s),
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'END:VEVENT']),
    ('15.06. Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;VALUE=DATE:{}0615'.format(this_year_s),
      'DTEND;VALUE=DATE:{}0616'.format(this_year_s),
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'END:VEVENT']),
)


def test_construct_event_format_de_complexer():
    for data_list, vevent in test_set_format_de_complexer:
        event = construct_event(data_list.split(),
                                _now=_now,
                                locale=locale_de)
        assert _replace_uid(event).to_ical() == vevent


test_set_description = _create_testcases(
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event :: this is going to be awesome',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:{}T080000'.format(today_s),
      'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:{}T090000'.format(today_s),
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'DESCRIPTION:this is going to be awesome',
      'END:VEVENT']),
    # today until tomorrow
    ('22:00  1:00 Äwesöme Event :: Will be even better',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:{}T220000'.format(today_s),
      'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:{}T010000'.format(tomorrow_s),
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'DESCRIPTION:Will be even better',
      'END:VEVENT']),
    ('15.06. Äwesöme Event :: and again',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;VALUE=DATE:{}0615'.format(this_year_s),
      'DTEND;VALUE=DATE:{}0616'.format(this_year_s),
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'DESCRIPTION:and again',
      'END:VEVENT']),
)


def test_description():
    for data_list, vevent in test_set_description:
        event = construct_event(data_list.split(), _now=_now, locale=locale_de)
        assert _replace_uid(event).to_ical() == vevent

test_set_repeat = _create_testcases(
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:{}T080000'.format(today_s),
      'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:{}T090000'.format(today_s),
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'DESCRIPTION:please describe the event',
      'RRULE:FREQ=DAILY;UNTIL=20150605T000000',
      'END:VEVENT']))


def test_repeat():
    for data_list, vevent in test_set_repeat:
        event = construct_event(data_list.split(),
                                description='please describe the event',
                                repeat='daily',
                                until=['05.06.2015'],
                                _now=_now,
                                locale=locale_de)
        assert _replace_uid(event).to_ical() == vevent


test_set_description_and_location = _create_testcases(
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:{}T080000'.format(today_s),
      'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:{}T090000'.format(today_s),
      'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'DESCRIPTION:please describe the event',
      'LOCATION:in the office',
      'END:VEVENT']))


def test_description_and_location():
    for data_list, vevent in test_set_description_and_location:
        event = construct_event(data_list.split(),
                                description='please describe the event',
                                _now=_now,
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
