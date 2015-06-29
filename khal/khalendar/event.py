# vim: set ts=4 sw=4 expandtab sts=4 fileencoding=utf-8:
# Copyright (c) 2013-2015 Christian Geier et al.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""this module cointains the event model, hopefully soon in a cleaned up version"""

from __future__ import unicode_literals

from datetime import date, datetime, time, timedelta

import icalendar

from ..compat import unicode_type, bytes_type, iteritems, to_unicode
from .aux import to_naive_utc
from ..log import logger


class Event(object):
    """base Event class

    important distinction for AllDayEvents:
        all end times are as presented to a user, i.e. an event scheduled for
        only one day will have the same start and end date (even though the
        icalendar standard would have the end date be one day later)
    """
    def __init__(self, vevent, href, etag, locale, rec_inst, calendar, mutable=True):
        if self.__class__.__name__ == 'Event':
            raise ValueError('do not initialize this class directly')
        self._vevent = vevent
        self._locale = locale
        self._mutable = mutable
        self._rec_inst = rec_inst
        self.href = href
        self.etag = etag
        self.allday = False
        self.calendar = calendar

    @classmethod
    def _get_type(cls, start, end):
        if hasattr(start, 'tzinfo') ^ hasattr(end, 'tzinfo'):
            raise ValueError('DTSTART and DTEND should be of the same type (localized or floating)')
        # TODO deal with events which have tzinfo, but is set to None
        if isinstance(start, datetime) != isinstance(end, datetime):
            raise ValueError('DTSTART and DTEND should be of the same type (datetime or date)')

        if hasattr(start, 'tzinfo'):
            cls = LocalizedEvent
        elif isinstance(start, datetime):
            cls = FloatingEvent
        elif isinstance(start, date):
            cls = AllDayEvent
        return cls

    @classmethod
    def fromString(cls, event_str, href, etag, locale, calendar=None,
                   mutable=True, rec_inst=None):
        calendar_collection = icalendar.Calendar.from_ical(event_str)
        events = [item for item in calendar_collection.walk() if item.name == 'VEVENT']
        if len(events) > 1:
            # TODO deal with all repeating events
            raise NotImplementedError()
        else:
            vevent = events[0]

        start = vevent['DTSTART'].dt
        try:
            end = vevent['DTEND'].dt
        except KeyError:
            end = start
        cls = cls._get_type(start, end)
        return cls(vevent, href=href, etag=etag, locale=locale, rec_inst=rec_inst,
                   calendar=calendar, mutable=mutable)

    def update_start_end(self, start, end):
        """update start and end time of this event

        beware, this methods performs some open heart surgerly
        """
        self.__class__ = self._get_type(start, end)

        # TODO look up why this is needed
        # self.event.vevent.dt = newstart would not work
        # (timezone was missing after to_ical() )
        self._vevent.pop('DTSTART')
        self._vevent.add('DTSTART', start)
        if not isinstance(end, datetime):
            end = end + timedelta(days=1)
        try:
            self._vevent.pop('DTEND')
            self._vevent.add('DTEND', end)
        except KeyError:
            self._vevent.pop('DURATION')
            duration = (end - start)
            self._vevent.add('DURATION', duration)

    @property
    def recurring(self):
        return 'RRULE' in self._vevent or 'RECURRENCE-ID' in self._vevent or \
            'RDATE' in self._vevent

    @property
    def recurpattern(self):
        if 'RRULE' in self._vevent:
            return self._vevent['RRULE'].to_ical()
        else:
            return None

    @property
    def symbol_strings(self):
        if self._locale['unicode_symbols']:
            return dict(
                recurring='\N{Clockwise gapped circle arrow}',
                range='\N{Left right arrow}',
                range_end='\N{Rightwards arrow to bar}',
                range_start='\N{Rightwards arrow from bar}',
                right_arrow='\N{Rightwards arrow}'
            )
        else:
            return dict(
                recurring='R',
                range='<->',
                range_end='->|',
                range_start='|->',
                right_arrow='->'
            )

    @property
    def start_local(self):
        return self.start

    @property
    def end_local(self):
        return self.end

    @property
    def start(self):
        return self._vevent['DTSTART'].dt

    @property
    def end(self):
        try:
            end = self._vevent['DTEND'].dt
        except KeyError:
            duration = self._vevent['DURATION']
            end = self.start + duration.dt
        return end

    @property
    def uid(self):
        return self._vevent['UID']

    @staticmethod
    def _create_calendar():
        """
        create the calendar

        :returns: calendar
        :rtype: icalendar.Calendar()
        """
        calendar = icalendar.Calendar()
        calendar.add('version', '2.0')
        calendar.add('prodid', '-//CALENDARSERVER.ORG//NONSGML Version 1//EN')
        return calendar

    @property
    def raw(self):
        """needed for vdirsyncer comat

        return text
        """
        calendar = self._create_calendar()
        if hasattr(self._vevent['DTSTART'].dt, 'tzinfo'):
            tzs = [self.start.tzinfo]
            if (
                'DTEND' in self._vevent and
                hasattr(self._vevent['DTEND'].dt, 'tzinfo') and
                (self._vevent['DTSTART'].dt.tzinfo !=
                 self._vevent['DTEND'].dt.tzinfo)
            ):
                tzs.append(self._vevent['DTEND'].dt.tzinfo)

            for tzinfo in tzs:
                timezone = create_timezone(tzinfo, self.start)
                calendar.add_component(timezone)

        calendar.add_component(self._vevent)
        return calendar.to_ical().decode('utf-8')

    @property
    def ident(self):
        """neeeded for vdirsyncer compat"""
        return self._vevent['UID']

    @property
    def summary(self):
        return self._vevent.get('SUMMARY', None)

    @property
    def location(self):
        return self._vevent.get('LOCATION', None)

    @property
    def description(self):
        return self._vevent.get('DESCRIPTION', None)

    @property
    def _recur_str(self):
        if self.recurring:
            recurstr = self.symbol_strings['recurring']
        else:
            recurstr = ''
        return recurstr

    def relative_to(self, day):
        """
        returns a short description of the event, with start and end
        relative to `day`

        print information in regards to this day, if the event starts and ends
        on this day, the start and end time will be given (only the description
        for all day events), otherwise arrows will indicate if the events
        started before `day` and/or lasts longer.

        :param day: the date the description is relative to
        :type day: datetime.date
        :return: compact description of Event
        :rtype: unicode()
        """
        if isinstance(day, datetime) or not isinstance(day, date):
            raise ValueError('`this_date` is of type `{}`, should be '
                             '`datetime.date`'.format(type(day)))
        if day < self.start.date() or day > self.end.date():
            raise ValueError(
                'please supply a `day` this event is scheduled on')

        day_start = self._locale['local_timezone'].localize(datetime.combine(day, time.min))
        day_end = self._locale['local_timezone'].localize(datetime.combine(day, time.max))

        tostr = '-'
        if self.start_local < day_start:
            startstr = self.symbol_strings['right_arrow'] + ' '
            tostr = ''
        else:
            startstr = self.start_local.strftime(self._locale['timeformat'])

        if self.end_local > day_end:
            endstr = self.symbol_strings['right_arrow'] + ' '
            tostr = ''
        else:
            endstr = self.end_local.strftime(self._locale['timeformat'])

        return ' '.join(filter(bool, [startstr + tostr + endstr + ':', self.summary, self._recur_str]))

    @property
    def event_description(self):   # XXX rename me
        """complete description of this event in text form

        :rtype: str
        :returns: event description
        """

        location = '\nLocation: ' + self.location if \
            self.location is not None else ''
        description = '\nDescription: ' + self.description if \
            self.description is not None else ''
        repitition = '\nRepeat: ' + to_unicode(self.recurpattern) if \
            self.recurpattern is not None else ''

        return '{}: {}{}{}{}'.format(
            self._rangestr, self.summary, location, repitition, description)


class LocalizedEvent(Event):
    """
    see parent
    """
    @property
    def start_local(self):
        """
        see parent
        """
        if self.start.tzinfo is None:
            start = self._locale['default_timezone'].localize(self.start)
        else:
            start = self.start
        return start.astimezone(self._locale['local_timezone'])

    @property
    def end_local(self):
        """
        see parent
        """
        if self.end.tzinfo is None:
            end = self._locale['default_timezone'].localize(self.end)
        else:
            end = self.end
        return end.astimezone(self._locale['local_timezone'])

    @property
    def _rangestr(self):
        # same day
        if self.start_local.utctimetuple()[:3] == self.end_local.utctimetuple()[:3]:
            starttime = self.start_local.strftime(self._locale['timeformat'])
            endtime = self.end_local.strftime(self._locale['timeformat'])
            datestr = self.end_local.strftime(self._locale['longdateformat'])
            rangestr = starttime + '-' + endtime + ' ' + datestr
        else:
            startstr = self.start_local.strftime(self._locale['longdatetimeformat'])
            endstr = self.end_local.strftime(self._locale['longdatetimeformat'])
            rangestr = startstr + ' - ' + endstr
        return rangestr


class FloatingEvent(Event):
    """
    """
    allday = False


class AllDayEvent(Event):
    allday = True

    @property
    def end(self):
        end = super(AllDayEvent, self).end
        if end == self.start:
            # https://github.com/geier/khal/issues/129
            logger.warning('{} ("{}"): The event\'s end date property '
                           'contains the same value as the start date, '
                           'which is invalid as per RFC 2445. Khal will '
                           'assume this is meant to be single-day event '
                           'on {}'.format(self.href, self.summary,
                                          self.start))
            end += timedelta(days=1)
        return end - timedelta(days=1)

    def relative_to(self, day):
        if self.start > day or self.end < day:
            raise ValueError('Day out of range: {}'
                             .format(dict(day=day, start=self.start,
                                          end=self.end)))
        elif self.start < day and self.end > day:
            # event starts before and goes on longer than `day`:
            rangestr = self.symbol_strings['range']
        elif self.start < day:
            # event started before `day`
            rangestr = self.symbol_strings['range_end']
        elif self.end > day:
            # event goes on longer than `day`
            rangestr = self.symbol_strings['range_start']
        elif self.start == self.end == day:
            # only on `day`
            rangestr = ''
        return ' '.join(filter(bool, (rangestr, self.summary, self._recur_str)))

    @property
    def _rangestr(self):
        if self.start_local == self.end_local:
            rangestr = self.start_local.strftime(self._locale['longdateformat'])
        else:
            if self.start_local.year == self.end_local.year:
                startstr = self.start_local.strftime(self._locale['dateformat'])
            else:
                startstr = self.start_local.strftime(self._locale['longdateformat'])
            endstr = self.end_local.strftime(self._locale['longdateformat'])
            rangestr = startstr + ' - ' + endstr
        return rangestr


def create_timezone(tz, first_date=None, last_date=None):
    """
    create an icalendar vtimezone from a pytz.tzinfo

    :param tz: the timezone
    :type tz: pytz.tzinfo
    :param first_date: the very first datetime that needs to be included in the
    transition times, typically the DTSTART value of the (first recurring)
    event
    :type first_date: datetime.datetime
    :param last_date: the last datetime that needs to included, typically the
    end of the (very last) event (of a recursion set)
    :returns: timezone information
    :rtype: icalendar.Timezone()

    we currently have a problem here:

       pytz.timezones only carry the absolute dates of time zone transitions,
       not their RRULEs. This will a) make for rather bloated VTIMEZONE
       components, especially for long recurring events, b) we'll need to
       specify for which time range this VTIMEZONE should be generated and c)
       will not be valid for recurring events that go into eternity.

    Possible Solutions:

    As this information is not provided by pytz at all, there is no
    easy solution, we'd really need to ship another version of the OLSON DB.

    """

    # TODO last_date = None, recurring to infinity

    first_date = datetime.today() if not first_date else to_naive_utc(first_date)
    last_date = datetime.today() if not last_date else to_naive_utc(last_date)
    timezone = icalendar.Timezone()
    timezone.add('TZID', tz)

    dst = {one[2]: 'DST' in two.__repr__() for one, two in iteritems(tz._tzinfos)}
    bst = {one[2]: 'BST' in two.__repr__() for one, two in iteritems(tz._tzinfos)}

    # looking for the first and last transition time we need to include
    first_num, last_num = 0, len(tz._utc_transition_times) - 1
    first_tt = tz._utc_transition_times[0]
    last_tt = tz._utc_transition_times[-1]
    for num, dt in enumerate(tz._utc_transition_times):
        if dt > first_tt and dt < first_date:
            first_num = num
            first_tt = dt
        if dt < last_tt and dt > last_date:
            last_num = num
            last_tt = dt

    timezones = dict()
    for num in range(first_num, last_num + 1):
        name = tz._transition_info[num][2]
        if name in timezones:
            ttime = tz.fromutc(tz._utc_transition_times[num]).replace(tzinfo=None)
            if 'RDATE' in timezones[name]:
                timezones[name]['RDATE'].dts.append(
                    icalendar.prop.vDDDTypes(ttime))
            else:
                timezones[name].add('RDATE', ttime)
            continue

        if dst[name] or bst[name]:
            subcomp = icalendar.TimezoneDaylight()
        else:
            subcomp = icalendar.TimezoneStandard()

        subcomp.add('TZNAME', tz._transition_info[num][2])
        subcomp.add(
            'DTSTART',
            tz.fromutc(tz._utc_transition_times[num]).replace(tzinfo=None))
        subcomp.add('TZOFFSETTO', tz._transition_info[num][0])
        subcomp.add('TZOFFSETFROM', tz._transition_info[num - 1][0])
        timezones[name] = subcomp

    for subcomp in timezones.values():
        timezone.add_component(subcomp)

    return timezone
