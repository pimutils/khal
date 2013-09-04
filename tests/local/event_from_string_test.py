# vim: set fileencoding=utf-8:
from khal.aux import construct_event
import random
import pytz


test_set = [('15.08. 16.08. Äwesöme Event',  # 2 day all-day
             '\r\n'.join(['BEGIN:VEVENT',
                          'SUMMARY:Äwesöme Event',
                          'DTSTART;VALUE=DATE:20130815',
                          'DTEND;VALUE=DATE:20130817',
                          'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                          'END:VEVENT',
                          ''])),
            ('25.10. 18:00 20:00 Äwesöme Event',
             '\r\n'.join(['BEGIN:VEVENT',
                          'SUMMARY:Äwesöme Event',
                          'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T180000',
                          'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T200000',
                          'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                          'END:VEVENT',
                          ''])),
            ('25.10. 18:00 26.10. 20:00 Äwesöme Event',
             '\r\n'.join(['BEGIN:VEVENT',
                          'SUMMARY:Äwesöme Event',
                          'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T180000',
                          'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131026T200000',
                          'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                          'END:VEVENT',
                          ''])),
            ('25.10. 23:00 0:30 Äwesöme Event',
             '\r\n'.join(['BEGIN:VEVENT',
                          'SUMMARY:Äwesöme Event',
                          'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T230000',
                          'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131026T003000',
                          'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                          'END:VEVENT',
                          ''])),
            ('25.10. Äwesöme Event',
             '\r\n'.join(['BEGIN:VEVENT',
                          'SUMMARY:Äwesöme Event',
                          'DTSTART;VALUE=DATE:20131025',
                          'DTEND;VALUE=DATE:20131026',
                          'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                          'END:VEVENT',
                          ''])),
            ('25.10. 06:00 Äwesöme Event',
             '\r\n'.join(['BEGIN:VEVENT',
                          'SUMMARY:Äwesöme Event',
                          'DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T060000',
                          'DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20131025T070000',
                          'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
                          'END:VEVENT',
                          ''])),
            ]


timeformat = '%H:%M'
dateformat = '%d.%m.'
datetimeformat = '%d.%m. %H:%M'
DEFAULTTZ = pytz.timezone('Europe/Berlin')


def test_construct_event():
    for data_list, vevent in test_set:
        random.seed(1)
        assert construct_event(data_list.split(),
                               timeformat,
                               dateformat,
                               datetimeformat,
                               DEFAULTTZ).to_ical() == vevent
