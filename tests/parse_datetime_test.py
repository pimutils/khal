import datetime as dt
from collections import OrderedDict

import pytest
from freezegun import freeze_time

from khal.exceptions import DateTimeParseError, FatalError
from khal.icalendar import new_vevent
from khal.parse_datetime import (
    construct_daynames,
    eventinfofstr,
    guessdatetimefstr,
    guessrangefstr,
    guesstimedeltafstr,
    timedelta2str,
    weekdaypstr,
)

from .utils import (
    LOCALE_BERLIN,
    LOCALE_FLOATING,
    LOCALE_NEW_YORK,
    _replace_uid,
    normalize_component,
)


def _create_testcases(*cases):
    return [(userinput, ('\r\n'.join(output) + '\r\n').encode('utf-8'))
            for userinput, output in cases]


def _construct_event(info, locale,
                     defaulttimelen=60, defaultdatelen=1, description=None,
                     location=None, categories=None, repeat=None, until=None,
                     alarm=None, **kwargs):
    info = eventinfofstr(' '.join(info), locale,
                         default_event_duration=dt.timedelta(hours=1),
                         default_dayevent_duration=dt.timedelta(days=1),
                         adjust_reasonably=True,
                         )
    if description is not None:
        info["description"] = description
    event = new_vevent(
        locale=locale, location=location,
        categories=categories, repeat=repeat, until=until,
        alarms=alarm,
        **info)
    return event


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
         ('DTSTAMP', 'DTSTAMP:20140216T120000Z'),
         ('UID', 'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA')])

    for row in args:
        key = row.replace(':', ';').split(';')[0]
        def_vevent[key] = row

    def_vevent['END'] = 'END:VEVENT'
    return list(def_vevent.values())


class TestTimeDelta2Str:

    def test_single(self):
        assert timedelta2str(dt.timedelta(minutes=10)) == '10m'

    def test_negative(self):
        assert timedelta2str(dt.timedelta(minutes=-10)) == '-10m'

    def test_days(self):
        assert timedelta2str(dt.timedelta(days=2)) == '2d'

    def test_multi(self):
        assert timedelta2str(
            dt.timedelta(days=6, hours=-3, minutes=10, seconds=-3)
        ) == '5d 21h 9m 57s'


def test_weekdaypstr():
    for string, weekdayno in [
            ('monday', 0),
            ('tue', 1),
            ('wednesday', 2),
            ('thursday', 3),
            ('fri', 4),
            ('saturday', 5),
            ('sun', 6),
    ]:
        assert weekdaypstr(string) == weekdayno


def test_weekdaypstr_invalid():
    with pytest.raises(ValueError):
        weekdaypstr('foobar')


def test_construct_daynames():
    with freeze_time('2016-9-19'):
        assert construct_daynames(dt.date(2016, 9, 19)) == 'Today'
        assert construct_daynames(dt.date(2016, 9, 20)) == 'Tomorrow'
        assert construct_daynames(dt.date(2016, 9, 21)) == 'Wednesday'


class TestGuessDatetimefstr:

    @freeze_time('2016-9-19T8:00')
    def test_today(self):
        assert (dt.datetime(2016, 9, 19, 13), False) == \
            guessdatetimefstr(['today', '13:00'], LOCALE_BERLIN)
        assert dt.date.today() == guessdatetimefstr(['today'], LOCALE_BERLIN)[0].date()

    @freeze_time('2016-9-19T8:00')
    def test_tomorrow(self):
        assert (dt.datetime(2016, 9, 20, 16), False) == \
            guessdatetimefstr('tomorrow 16:00 16:00'.split(), locale=LOCALE_BERLIN)

    @freeze_time('2016-9-19T8:00')
    def test_time_tomorrow(self):
        assert (dt.datetime(2016, 9, 20, 16), False) == \
            guessdatetimefstr(
                '16:00'.split(), locale=LOCALE_BERLIN, default_day=dt.date(2016, 9, 20))

    @freeze_time('2016-9-19T8:00')
    def test_time_yesterday(self):
        assert (dt.datetime(2016, 9, 18, 16), False) == guessdatetimefstr(
            'Yesterday 16:00'.split(),
            locale=LOCALE_BERLIN,
            default_day=dt.datetime.today())

    @freeze_time('2016-9-19')
    def test_time_weekday(self):
        assert (dt.datetime(2016, 9, 23, 16), False) == guessdatetimefstr(
            'Friday 16:00'.split(),
            locale=LOCALE_BERLIN,
            default_day=dt.datetime.today())

    @freeze_time('2016-9-19 17:53')
    def test_time_now(self):
        assert (dt.datetime(2016, 9, 19, 17, 53), False) == guessdatetimefstr(
            'now'.split(), locale=LOCALE_BERLIN, default_day=dt.datetime.today())

    @freeze_time('2016-12-30 17:53')
    def test_long_not_configured(self):
        """long version is not configured, but short contains the year"""
        locale = {
            'timeformat': '%H:%M',
            'dateformat': '%Y-%m-%d',
            'longdateformat': '',
            'datetimeformat': '%Y-%m-%d %H:%M',
            'longdatetimeformat': '',
        }
        assert (dt.datetime(2017, 1, 1), True) == guessdatetimefstr(
            '2017-1-1'.split(), locale=locale, default_day=dt.datetime.today())
        assert (dt.datetime(2017, 1, 1, 16, 30), False) == guessdatetimefstr(
            '2017-1-1 16:30'.split(), locale=locale, default_day=dt.datetime.today())

    @freeze_time('2016-12-30 17:53')
    def test_short_format_contains_year(self):
        """if the non long versions of date(time)format contained a year, the
        current year would be used instead of the given one, see #545"""
        locale = {
            'timeformat': '%H:%M',
            'dateformat': '%Y-%m-%d',
            'longdateformat': '%Y-%m-%d',
            'datetimeformat': '%Y-%m-%d %H:%M',
            'longdatetimeformat': '%Y-%m-%d %H:%M',
        }
        assert (dt.datetime(2017, 1, 1), True) == guessdatetimefstr(
            '2017-1-1'.split(), locale=locale, default_day=dt.datetime.today())
        assert (dt.datetime(2017, 1, 1, 16, 30), False) == guessdatetimefstr(
            '2017-1-1 16:30'.split(), locale=locale, default_day=dt.datetime.today())


class TestGuessTimedeltafstr:

    def test_single(self):
        assert dt.timedelta(minutes=10) == guesstimedeltafstr('10m')

    def test_seconds(self):
        assert dt.timedelta(seconds=10) == guesstimedeltafstr('10s')

    def test_single_plus(self):
        assert dt.timedelta(minutes=10) == guesstimedeltafstr('+10m')

    def test_seconds_plus(self):
        assert dt.timedelta(seconds=10) == guesstimedeltafstr('+10s')

    def test_days_plus(self):
        assert dt.timedelta(days=10) == guesstimedeltafstr('+10days')

    def test_negative(self):
        assert dt.timedelta(minutes=-10) == guesstimedeltafstr('-10m')

    def test_multi(self):
        assert dt.timedelta(days=1, hours=-3, minutes=10) == \
            guesstimedeltafstr(' 1d -3H 10min ')

    def test_multi_plus(self):
        assert dt.timedelta(days=1, hours=3, minutes=10) == \
            guesstimedeltafstr(' 1d +3H 10min ')

    def test_multi_plus_minus(self):
        assert dt.timedelta(days=0, hours=21, minutes=10) == \
            guesstimedeltafstr('+1d -3H 10min ')

    def test_multi_nospace(self):
        assert dt.timedelta(days=1, hours=-3, minutes=10) == \
            guesstimedeltafstr('1D-3hour10m')

    def test_garbage(self):
        with pytest.raises(ValueError):
            guesstimedeltafstr('10mbar')

    def test_moregarbage(self):
        with pytest.raises(ValueError):
            guesstimedeltafstr('foo10m')

    def test_same(self):
        assert dt.timedelta(minutes=20) == \
            guesstimedeltafstr('10min 10minutes')


class TestGuessRangefstr:

    @freeze_time('2016-9-19')
    def test_today(self):
        assert (dt.datetime(2016, 9, 19, 13), dt.datetime(2016, 9, 19, 14), False) == \
            guessrangefstr('13:00 14:00', locale=LOCALE_BERLIN)
        assert (dt.datetime(2016, 9, 19), dt.datetime(2016, 9, 21), True) == \
            guessrangefstr('today tomorrow', LOCALE_BERLIN)

    @freeze_time('2016-9-19 16:34')
    def test_tomorrow(self):
        # XXX remove this funtionality, we shouldn't support this anyway
        assert (dt.datetime(2016, 9, 19), dt.datetime(2016, 9, 21, 16), True) == \
            guessrangefstr('today tomorrow 16:00', locale=LOCALE_BERLIN)

    @freeze_time('2016-9-19 13:34')
    def test_time_tomorrow(self):
        assert (dt.datetime(2016, 9, 19, 16), dt.datetime(2016, 9, 19, 17), False) == \
            guessrangefstr('16:00', locale=LOCALE_BERLIN)
        assert (dt.datetime(2016, 9, 19, 16), dt.datetime(2016, 9, 19, 17), False) == \
            guessrangefstr('16:00 17:00', locale=LOCALE_BERLIN)

    def test_start_and_end_date(self):
        assert (dt.datetime(2016, 1, 1), dt.datetime(2017, 1, 2), True) == \
            guessrangefstr('1.1.2016 1.1.2017', locale=LOCALE_BERLIN)

    def test_start_and_no_end_date(self):
        assert (dt.datetime(2016, 1, 1), dt.datetime(2016, 1, 2), True) == \
            guessrangefstr('1.1.2016', locale=LOCALE_BERLIN)

    def test_start_and_end_date_time(self):
        assert (dt.datetime(2016, 1, 1, 10), dt.datetime(2017, 1, 1, 22), False) == \
            guessrangefstr(
                '1.1.2016 10:00 1.1.2017 22:00', locale=LOCALE_BERLIN)

    def test_start_and_eod(self):
        start, end = dt.datetime(2016, 1, 1, 10), dt.datetime(2016, 1, 1, 23, 59, 59, 999999)
        assert (start, end, False) == guessrangefstr('1.1.2016 10:00 eod', locale=LOCALE_BERLIN)

    def test_start_and_week(self):
        assert (dt.datetime(2015, 12, 28), dt.datetime(2016, 1, 5), True) == \
            guessrangefstr('1.1.2016 week', locale=LOCALE_BERLIN)

    def test_start_and_delta_1d(self):
        assert (dt.datetime(2016, 1, 1), dt.datetime(2016, 1, 2), True) == \
            guessrangefstr('1.1.2016 1d', locale=LOCALE_BERLIN)

    def test_start_and_delta_3d(self):
        assert (dt.datetime(2016, 1, 1), dt.datetime(2016, 1, 4), True) == \
            guessrangefstr('1.1.2016 3d', locale=LOCALE_BERLIN)

    def test_start_dt_and_delta(self):
        assert (dt.datetime(2016, 1, 1, 10), dt.datetime(2016, 1, 4, 10), False) == \
            guessrangefstr('1.1.2016 10:00 3d', locale=LOCALE_BERLIN)

    def test_start_allday_and_delta_datetime(self):
        with pytest.raises(FatalError):
            guessrangefstr('1.1.2016 3d3m', locale=LOCALE_BERLIN)

    def test_start_zero_day_delta(self):
        with pytest.raises(FatalError):
            guessrangefstr('1.1.2016 0d', locale=LOCALE_BERLIN)

    @freeze_time('20160216')
    def test_week(self):
        assert (dt.datetime(2016, 2, 15), dt.datetime(2016, 2, 23), True) == \
            guessrangefstr('week', locale=LOCALE_BERLIN)

    def test_invalid(self):
        with pytest.raises(DateTimeParseError):
            guessrangefstr('3d', locale=LOCALE_BERLIN)
        with pytest.raises(DateTimeParseError):
            guessrangefstr('35.1.2016', locale=LOCALE_BERLIN)
        with pytest.raises(DateTimeParseError):
            guessrangefstr('1.1.2016 2x', locale=LOCALE_BERLIN)
        with pytest.raises(DateTimeParseError):
            guessrangefstr('1.1.2016x', locale=LOCALE_BERLIN)
        with pytest.raises(DateTimeParseError):
            guessrangefstr('xxx yyy zzz', locale=LOCALE_BERLIN)

    @freeze_time('2016-12-30 17:53')
    def test_short_format_contains_year(self):
        """if the non long versions of date(time)format contained a year, the
        current year would be used instead of the given one, see #545

        same as above, but for guessrangefstr
        """
        locale = {
            'timeformat': '%H:%M',
            'dateformat': '%Y-%m-%d',
            'longdateformat': '%Y-%m-%d',
            'datetimeformat': '%Y-%m-%d %H:%M',
            'longdatetimeformat': '%Y-%m-%d %H:%M',
        }
        assert (dt.datetime(2017, 1, 1), dt.datetime(2017, 1, 2), True) == \
            guessrangefstr('2017-1-1 2017-1-1', locale=locale)


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
         'DTSTART;TZID=Europe/Berlin:20131025T180000',
         'DTEND;TZID=Europe/Berlin:20131025T200000')),

    # start and end date same, ends 24:00 which should be 00:00 (start) of next
    # day
    ('25.10.2013 18:00 24:00 Äwesöme Event',
     _create_vevent(
         'DTSTART;TZID=Europe/Berlin:20131025T180000',
         'DTEND;TZID=Europe/Berlin:20131026T000000')),

    # start and end date same, explicit end date (but no year) given
    ('25.10.2013 18:00 26.10. 20:00 Äwesöme Event',
     _create_vevent(
         'DTSTART;TZID=Europe/Berlin:20131025T180000',
         'DTEND;TZID=Europe/Berlin:20131026T200000')),

    ('30.12.2013 18:00 2.1. 20:00 Äwesöme Event',
     _create_vevent(
         'DTSTART;TZID=Europe/Berlin:20131230T180000',
         'DTEND;TZID=Europe/Berlin:20140102T200000')),

    # only start date given (no year, past day and month)
    ('25.01. 18:00 20:00 Äwesöme Event',
     _create_vevent(
         'DTSTART;TZID=Europe/Berlin:20150125T180000',
         'DTEND;TZID=Europe/Berlin:20150125T200000')),

    # date ends next day, but end date not given
    ('25.10.2013 23:00 0:30 Äwesöme Event',
     _create_vevent(
         'DTSTART;TZID=Europe/Berlin:20131025T230000',
         'DTEND;TZID=Europe/Berlin:20131026T003000')),

    ('2.2. 23:00 0:30 Äwesöme Event',
     _create_vevent(
         'DTSTART;TZID=Europe/Berlin:20150202T230000',
         'DTEND;TZID=Europe/Berlin:20150203T003000')),

    # only start datetime given
    ('25.10.2013 06:00 Äwesöme Event',
     _create_vevent(
         'DTSTART;TZID=Europe/Berlin:20131025T060000',
         'DTEND;TZID=Europe/Berlin:20131025T070000')),

    # timezone given
    ('25.10.2013 06:00 America/New_York Äwesöme Event',
     _create_vevent(
         'DTSTART;TZID=America/New_York:20131025T060000',
         'DTEND;TZID=America/New_York:20131025T070000'))
)


@freeze_time('20140216T120000')
def test_construct_event_format_de():
    for data_list, vevent_expected in test_set_format_de:
        vevent = _construct_event(data_list.split(), locale=LOCALE_BERLIN)
        assert _replace_uid(vevent).to_ical() == vevent_expected


test_set_format_us = _create_testcases(
    ('1999/12/31-06:00 Äwesöme Event',
     _create_vevent(
         'DTSTART;TZID=America/New_York:19991231T060000',
         'DTEND;TZID=America/New_York:19991231T070000')),

    ('2014/12/18 2014/12/20 Äwesöme Event',
     _create_vevent('DTSTART;VALUE=DATE:20141218',
                    'DTEND;VALUE=DATE:20141221')),
)


@freeze_time('2014-02-16 12:00:00')
def test__construct_event_format_us():
    for data_list, vevent in test_set_format_us:
        event = _construct_event(data_list.split(), locale=LOCALE_NEW_YORK)
        assert _replace_uid(event).to_ical() == vevent


test_set_format_de_complexer = _create_testcases(
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event',
     _create_vevent(
         'DTSTART;TZID=Europe/Berlin:20140216T080000',
         'DTEND;TZID=Europe/Berlin:20140216T090000')),

    # today until tomorrow
    ('22:00  1:00 Äwesöme Event',
     _create_vevent(
         'DTSTART;TZID=Europe/Berlin:20140216T220000',
         'DTEND;TZID=Europe/Berlin:20140217T010000')),

    # other timezone
    ('22:00 1:00 Europe/London Äwesöme Event',
     _create_vevent(
         'DTSTART;TZID=Europe/London:20140216T220000',
         'DTEND;TZID=Europe/London:20140217T010000')),

    ('15.06. Äwesöme Event',
     _create_vevent('DTSTART;VALUE=DATE:20140615',
                    'DTEND;VALUE=DATE:20140616')),
)


@freeze_time('2014-02-16 12:00:00')
def test__construct_event_format_de_complexer():
    for data_list, vevent in test_set_format_de_complexer:
        event = _construct_event(data_list.split(), locale=LOCALE_BERLIN)
        assert _replace_uid(event).to_ical() == vevent


test_set_leap_year = _create_testcases(
    ('29.02. Äwesöme Event',
     _create_vevent(
         'DTSTART;VALUE=DATE:20160229',
         'DTEND;VALUE=DATE:20160301',
         'DTSTAMP:20160101T202122Z')),
)


def test_leap_year():
    for data_list, vevent in test_set_leap_year:
        with freeze_time('1999-1-1'):
            with pytest.raises(DateTimeParseError):
                event = _construct_event(data_list.split(), locale=LOCALE_BERLIN)
        with freeze_time('2016-1-1 20:21:22'):
            event = _construct_event(data_list.split(), locale=LOCALE_BERLIN)
            assert _replace_uid(event).to_ical() == vevent


test_set_description = _create_testcases(
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event :: this is going to be awesome',
     _create_vevent(
         'DTSTART;TZID=Europe/Berlin:20140216T080000',
         'DTEND;TZID=Europe/Berlin:20140216T090000',
         'DESCRIPTION:this is going to be awesome')),

    # today until tomorrow
    ('22:00  1:00 Äwesöme Event :: Will be even better',
     _create_vevent(
         'DTSTART;TZID=Europe/Berlin:20140216T220000',
         'DTEND;TZID=Europe/Berlin:20140217T010000',
         'DESCRIPTION:Will be even better')),

    ('15.06. Äwesöme Event :: and again',
     _create_vevent('DTSTART;VALUE=DATE:20140615',
                    'DTEND;VALUE=DATE:20140616',
                    'DESCRIPTION:and again')),
)


def test_description():
    for data_list, vevent in test_set_description:
        with freeze_time('2014-02-16 12:00:00'):
            event = _construct_event(data_list.split(), locale=LOCALE_BERLIN)
            assert _replace_uid(event).to_ical() == vevent


test_set_repeat_floating = _create_testcases(
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event',
     _create_vevent(
         'DTSTART:20140216T080000',
         'DTEND:20140216T090000',
         'DESCRIPTION:please describe the event',
         'RRULE:FREQ=DAILY;UNTIL=20150604T000000')))


def test_repeat_floating():
    for data_list, vevent in test_set_repeat_floating:
        with freeze_time('2014-02-16 12:00:00'):
            event = _construct_event(data_list.split(),
                                     description='please describe the event',
                                     repeat='daily',
                                     until='04.06.2015',
                                     locale=LOCALE_FLOATING)
            assert normalize_component(_replace_uid(event).to_ical()) == \
                normalize_component(vevent)


test_set_repeat_localized = _create_testcases(
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event',
     _create_vevent(
         'DTSTART;TZID=Europe/Berlin:20140216T080000',
         'DTEND;TZID=Europe/Berlin:20140216T090000',
         'DESCRIPTION:please describe the event',
         'RRULE:FREQ=DAILY;UNTIL=20150604T230000Z')))


def test_repeat_localized():
    for data_list, vevent in test_set_repeat_localized:
        with freeze_time('2014-02-16 12:00:00'):
            event = _construct_event(data_list.split(),
                                     description='please describe the event',
                                     repeat='daily',
                                     until='05.06.2015',
                                     locale=LOCALE_BERLIN)
            assert normalize_component(_replace_uid(event).to_ical()) == \
                normalize_component(vevent)


test_set_alarm = _create_testcases(
    ('8:00 Äwesöme Event',
     ['BEGIN:VEVENT',
      'SUMMARY:Äwesöme Event',
      'DTSTART;TZID=Europe/Berlin:20140216T080000',
      'DTEND;TZID=Europe/Berlin:20140216T090000',
      'DTSTAMP:20140216T120000Z',
      'UID:E41JRQX2DB4P1AQZI86BAT7NHPBHPRIIHQKA',
      'DESCRIPTION:please describe the event',
      'BEGIN:VALARM',
      'ACTION:DISPLAY',
      'DESCRIPTION:please describe the event',
      'TRIGGER:-PT23M',
      'END:VALARM',
      'END:VEVENT']))


@freeze_time('2014-02-16 12:00:00')
def test_alarm():
    for data_list, vevent in test_set_alarm:
        event = _construct_event(data_list.split(),
                                 description='please describe the event',
                                 alarm='23m',
                                 locale=LOCALE_BERLIN)
        assert _replace_uid(event).to_ical() == vevent


test_set_description_and_location_and_categories = _create_testcases(
    # now events where the start date has to be inferred, too
    # today
    ('8:00 Äwesöme Event',
     _create_vevent(
         'DTSTART;TZID=Europe/Berlin:20140216T080000',
         'DTEND;TZID=Europe/Berlin:20140216T090000',
         'CATEGORIES:boring meeting',
         'DESCRIPTION:please describe the event',
         'LOCATION:in the office')))


@freeze_time('2014-02-16 12:00:00')
def test_description_and_location_and_categories():
    for data_list, vevent in test_set_description_and_location_and_categories:
        event = _construct_event(data_list.split(),
                                 description='please describe the event',
                                 location='in the office',
                                 categories=['boring meeting'],
                                 locale=LOCALE_BERLIN)
        assert _replace_uid(event).to_ical() == vevent
