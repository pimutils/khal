# vim: set fileencoding=utf-8:
from datetime import date, datetime, timedelta
import random

import pytz

from khal.aux import construct_event


def _now():
    return datetime(2014, 2, 16, 12, 0, 0, 0)


today = date.today()
tomorrow = today + timedelta(days=1)
today_s = '{0:02}{1:02}{2:02}'.format(*today.timetuple()[0:3])
tomorrow_s = '{0:02}{1:02}{2:02}'.format(*tomorrow.timetuple()[0:3])
this_year_s = str(today.year)

test_set_format_de = [
    # all-day-events
    # one day only
    ('25.10.2013 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;VALUE=DATE:20131025',
                  'DTEND;VALUE=DATE:20131026',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    # 2 day
    ('15.08.2014 16.08. Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;VALUE=DATE:20140815',
                  'DTEND;VALUE=DATE:20140817',  # XXX
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    # end date in next year and not specified
    ('29.12.2014 03.01. Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;VALUE=DATE:20141229',
                  'DTEND;VALUE=DATE:20150104',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    # end date in next year
    ('29.12.2014 03.01.2015 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;VALUE=DATE:20141229',
                  'DTEND;VALUE=DATE:20150104',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    # datetime events
    # start and end date same, no explicit end date given
    ('25.10.2013 18:00 20:00 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T180000',
                  'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T200000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    # start and end date same, explicit end date (but no year) given
    #('25.10.2013 18:00 26.10. 20:00 Äwesöme Event',   # XXX FIXME: if no explicit year is given for the end, this_year is used
    #'\r\n'.join(['BEGIN:VEVENT',
                 #'SUMMARY:Äwesöme Event',
                 #'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T180000',
                 #'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131026T200000',
                 #'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                 #'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                 #'END:VEVENT',
                 #''])),
    # date ends next day, but end date not given
    ('25.10.2013 23:00 0:30 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T230000',
                  'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131026T003000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    # only start datetime given
    ('25.10.2013 06:00 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T060000',
                  'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T070000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    # timezone given
    ('25.10.2013 06:00 America/New_York Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=America/New_York;VALUE=DATE-TIME:20131025T060000',
                  'DTEND;TZID=America/New_York;VALUE=DATE-TIME:20131025T070000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
]


def test_construct_event_format_de():
    timeformat = '%H:%M'
    dateformat = '%d.%m.'
    longdateformat = '%d.%m.%Y'
    datetimeformat = '%d.%m. %H:%M'
    longdatetimeformat = '%d.%m.%Y %H:%M'
    DEFAULTTZ = pytz.timezone('Europe/Berlin')
    for data_list, vevent in test_set_format_de:
        random.seed(1)
        event = construct_event(data_list.split(),
                                timeformat=timeformat,
                                dateformat=dateformat,
                                longdateformat=longdateformat,
                                datetimeformat=datetimeformat,
                                longdatetimeformat=longdatetimeformat,
                                defaulttz=DEFAULTTZ,
                                _now=_now).to_ical()
        assert event == vevent


test_set_format_us = [
    ('12/31/1999 06:00 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=America/New_York;VALUE=DATE-TIME:19991231T060000',
                  'DTEND;TZID=America/New_York;VALUE=DATE-TIME:19991231T070000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',

                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  ''])),
    ('12/18 12/20 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;VALUE=DATE:{0}1218',
                  'DTEND;VALUE=DATE:{0}1221',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  '']).format(this_year_s)),
]


def test_construct_event_format_us():
    timeformat = '%H:%M'
    dateformat = '%m/%d'
    longdateformat = '%m/%d/%Y'
    datetimeformat = '%m/%d %H:%M'
    longdatetimeformat = '%m/%d/%Y %H:%M'
    DEFAULTTZ = pytz.timezone('America/New_York')
    for data_list, vevent in test_set_format_us:
        random.seed(1)
        event = construct_event(data_list.split(),
                                timeformat=timeformat,
                                dateformat=dateformat,
                                longdateformat=longdateformat,
                                datetimeformat=datetimeformat,
                                longdatetimeformat=longdatetimeformat,
                                defaulttz=DEFAULTTZ,
                                _now=_now).to_ical()
        assert event == vevent


test_set_format_de_complexer = [
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:{0}T080000',
                  'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:{0}T090000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  '']).format(today_s)),
    # today until tomorrow
    ('22:00  1:00 Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:{0}T220000',
                  'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:{1}T010000',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  '']).format(today_s, tomorrow_s)),
    ('15.06. Äwesöme Event',
     '\r\n'.join(['BEGIN:VEVENT',
                  'SUMMARY:Äwesöme Event',
                  'DTSTART;VALUE=DATE:{0}0615',
                  'DTEND;VALUE=DATE:{0}0616',
                  'DTSTAMP;VALUE=DATE-TIME:20140216T120000Z',
                  'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                  'END:VEVENT',
                  '']).format(this_year_s)),
]


def test_construct_event_format_de_complexer():
    timeformat = '%H:%M'
    dateformat = '%d.%m.'
    longdateformat = '%d.%m.%Y'
    datetimeformat = '%d.%m. %H:%M'
    longdatetimeformat = '%d.%m.%Y %H:%M'
    DEFAULTTZ = pytz.timezone('Europe/Berlin')
    for data_list, vevent in test_set_format_de_complexer:
        random.seed(1)
        event = construct_event(data_list.split(),
                                timeformat=timeformat,
                                dateformat=dateformat,
                                longdateformat=longdateformat,
                                datetimeformat=datetimeformat,
                                longdatetimeformat=longdatetimeformat,
                                defaulttz=DEFAULTTZ,
                                _now=_now).to_ical()
        assert event == vevent
