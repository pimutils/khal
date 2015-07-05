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

from ..compat import iteritems, to_unicode
from .aux import to_naive_utc, to_unix_time
from ..log import logger


class Event(object):
    """base Event class for representing a *recurring instance* of an Event

    (in case of non-recurring events this distinction is irrelevant)
    We keep a copy of the start and end time around, because for recurring
    events it might be costly to expand the recursion rules

    important distinction for AllDayEvents:
        all end times are as presented to a user, i.e. an event scheduled for
        only one day will have the same start and end date (even though the
        icalendar standard would have the end date be one day later)
    """
    allday = False

    def __init__(self, vevents, ref=None, **kwargs):
        """
        :param start: start datetime of this event instance
        :type start: datetime.date
        :param end: end datetime of this event instance in unix time
        :type end: datetime.date
        """
        if self.__class__.__name__ == 'Event':
            raise ValueError('do not initialize this class directly')
        self._vevents = vevents
        self._locale = kwargs.pop('locale', None)
        self._mutable = kwargs.pop('mutable', None)
        self.href = kwargs.pop('href', None)
        self.etag = kwargs.pop('etag', None)
        self.calendar = kwargs.pop('calendar', None)
        self.ref = ref

        start = kwargs.pop('start', None)
        end = kwargs.pop('end', None)

        if start is None:
            self._start = self._vevents[self.ref]['DTSTART'].dt
        else:
            self._start = start
        if end is None:
            try:
                self._end = self._vevents[self.ref]['DTEND'].dt
            except KeyError:
                self._end = self._start + self._vevents[self.ref]['DURATION'].dt
        else:
            self._end = end
        if kwargs:
            raise TypeError('%s are invalid keyword arguments to this function' % kwargs.keys())

    @classmethod
    def _get_type_from_vDDD(cls, start):
        """
        :type start: icalendar.prop.vDDDTypes
        :type start: icalendar.prop.vDDDTypes
        """
        if not isinstance(start.dt, datetime):
            return AllDayEvent
        if 'TZID' in start.params and isinstance(start.dt, datetime):
            return LocalizedEvent
        return FloatingEvent

    @classmethod
    def _get_type_from_date(cls, start):
        if hasattr(start, 'tzinfo') and start.tzinfo is not None:
            cls = LocalizedEvent
        elif isinstance(start, datetime):
            cls = FloatingEvent
        elif isinstance(start, date):
            cls = AllDayEvent
        return cls

    @classmethod
    def fromVEvents(cls, events_list, ref=None, **kwargs):
        """
        :type events: list
        """
        assert isinstance(events_list, list)

        vevents = dict()
        if len(events_list) == 1:
            vevents['PROTO'] = events_list[0]  # TODO set mutable = False
        else:
            for event in events_list:
                if 'RECURRENCE-ID' in event:
                    ident = str(to_unix_time(event['RECURRENCE-ID'].dt))
                    vevents[ident] = event
                else:
                    vevents['PROTO'] = event
        if ref is None:
            ref = 'PROTO'

        try:
            if type(vevents[ref]['DTSTART'].dt) != type(vevents[ref]['DTEND'].dt):
                raise ValueError('DTSTART and DTEND should be of the same type (datetime or date)')
        except KeyError:
            pass

        instcls = cls._get_type_from_vDDD(vevents[ref]['DTSTART'])
        return instcls(vevents, ref=ref, **kwargs)

    @classmethod
    def fromString(cls, event_str, ref=None, **kwargs):
        calendar_collection = icalendar.Calendar.from_ical(event_str)
        events = [item for item in calendar_collection.walk() if item.name == 'VEVENT']
        return cls.fromVEvents(events, ref, **kwargs)

    def update_start_end(self, start, end):
        """update start and end time of this event

        calling this an a recurring event will lead to the proto instance
        be set to the new start and end times

        beware, this methods performs some open heart surgerly
        """
        if type(start) != type(end):
            raise ValueError('DTSTART and DTEND should be of the same type (datetime or date)')
        self.__class__ = self._get_type_from_date(start)

        self._vevents[self.ref].pop('DTSTART')
        self._vevents[self.ref].add('DTSTART', start)
        self._start = start
        if not isinstance(end, datetime):
            end = end + timedelta(days=1)
        self._end = end
        if 'DTEND' in self._vevents[self.ref]:
            self._vevents[self.ref].pop('DTEND')
            self._vevents[self.ref].add('DTEND', end)
        else:
            self._vevents[self.ref].pop('DURATION')
            self._vevents[self.ref].add('DURATION', end - start)

    @property
    def recurring(self):
        return 'RRULE' in self._vevents[self.ref] or \
            'RECURRENCE-ID' in self._vevents[self.ref] or \
            'RDATE' in self._vevents[self.ref]

    @property
    def recurpattern(self):
        if 'RRULE' in self._vevents[self.ref]:
            return self._vevents[self.ref]['RRULE'].to_ical()
        else:
            return ''

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
        return self._start

    @property
    def end(self):
        return self._end

    @property
    def duration(self):
        try:
            return self._vevents[self.ref]['DURATION'].dt
        except KeyError:
            return self.end - self.start

    @property
    def uid(self):
        return self._vevents[self.ref]['UID']

    @property
    def organizer(self):
        try:
            return to_unicode(self._vevents[self.ref]['ORGANIZER'], 'utf-8').split(':')[-1]
        except KeyError:
            return ''

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
        tzs = list()
        for vevent in self._vevents.values():
            if hasattr(vevent['DTSTART'].dt, 'tzinfo') and vevent['DTSTART'].dt.tzinfo is not None:
                tzs.append(vevent['DTSTART'].dt.tzinfo)
            if 'DTEND' in vevent and hasattr(vevent['DTEND'].dt, 'tzinfo') and \
                    vevent['DTEND'].dt.tzinfo is not None and \
                    vevent['DTEND'].dt.tzinfo not in tzs:
                tzs.append(vevent['DTEND'].dt.tzinfo)

        for tzinfo in tzs:
            timezone = create_timezone(tzinfo, self.start)
            calendar.add_component(timezone)

        for vevent in self._vevents.values():
            calendar.add_component(vevent)
        return calendar.to_ical().decode('utf-8')

    @property
    def ident(self):
        """neeeded for vdirsyncer compat"""
        return self._vevents[self.ref]['UID']

    @property
    def summary(self):
        return self._vevents[self.ref].get('SUMMARY', '')

    def update_summary(self, summary):
        self._vevents[self.ref]['SUMMARY'] = summary

    @property
    def location(self):
        return self._vevents[self.ref].get('LOCATION', '')

    def update_location(self, location):
        self._vevents[self.ref]['LOCATION'] = location

    @property
    def description(self):
        return self._vevents[self.ref].get('DESCRIPTION', '')

    def update_description(self, description):
        self._vevents[self.ref]['DESCRIPTION'] = description

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

        comps = [startstr + tostr + endstr + ':', self.summary, self._recur_str]
        return ' '.join(filter(bool, comps))

    @property
    def event_description(self):   # XXX rename me
        """complete description of this event in text form

        :rtype: str
        :returns: event description
        """

        location = '\nLocation: ' + self.location if self.location != '' else ''
        description = '\nDescription: ' + self.description if \
            self.description != '' else ''
        repitition = '\nRepeat: ' + to_unicode(self.recurpattern) if \
            self.recurpattern != '' else ''

        return '{}: {}{}{}{}'.format(
            self._rangestr, self.summary, location, repitition, description)


class DatetimeEvent(Event):
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


class LocalizedEvent(DatetimeEvent):
    """
    see parent
    """

    @property
    def start(self):
        tz = getattr(self._vevents[self.ref]['DTSTART'].dt, 'tzinfo',
                     self._locale['default_timezone'])
        return self._start.astimezone(tz)

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


class FloatingEvent(DatetimeEvent):
    """
    """
    allday = False

    @property
    def start_local(self):
        return self._locale['local_timezone'].localize(self.start)

    @property
    def end_local(self):
        return self._locale['local_timezone'].localize(self.end)


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
