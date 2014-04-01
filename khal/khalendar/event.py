#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
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

"""this module will the event model, hopefully soon in a cleaned up version"""

import datetime

import icalendar
from icalendar.tools import UIDGenerator


class Event(object):
    """the base event class"""
    def __init__(self, ical, uid=None, account=None, local_tz=None,
                 default_tz=None, start=None, end=None, color=None,
                 readonly=False, unicode_symbols=True, etag=None):

        if isinstance(ical, basestring):
            self.vevent = icalendar.Event.from_ical(ical)
        elif isinstance(ical, icalendar.cal.Event):
            self.vevent = ical

        if account is None:
            raise TypeError('account must not be None')

        self.allday = True
        self.color = color

        if uid is None and self.vevent.get('UID', '') == '':
            self.uid = UIDGenerator().uid().to_ical()

        self.account = account
        self.readonly = readonly
        self.unicode_symbols = unicode_symbols
        self.etag = etag

        if unicode_symbols:
            self.recurstr = u' \N{Clockwise gapped circle arrow}'
            self.rangestr = u'\N{Left right arrow} '
            self.rangestopstr = u'\N{Rightwards arrow to bar} '
            self.rangestartstr = u'\N{Rightwards arrow from bar} '
        else:
            self.recurstr = u' R'
            self.rangestr = u' <->'
            self.rangestopstr = u' ->|'
            self.rangestartstr = u' |->'

        if start is not None:
            if isinstance(self.vevent['dtstart'].dt, datetime.datetime):
                self.allday = False  # TODO detect allday even if start is None
                start = start.astimezone(local_tz)
                end = end.astimezone(local_tz)
            self.vevent['DTSTART'].dt = start
        if start is not None:
            if 'DTEND' in self.vevent.keys():
                self.vevent['DTEND'].dt = end
        self.local_tz = local_tz
        self.default_tz = default_tz

    @property
    def uid(self):
        return self.vevent['UID']

    @uid.setter
    def uid(self, value):
        self.vevent['UID'] = value

    @property
    def start(self):
        start = self.vevent['DTSTART'].dt

        if self.allday:
            return start
        if start.tzinfo is None:
            start = self.default_tz.localize(start)
        start = start.astimezone(self.local_tz)
        return start

    @property
    def end(self):
        # TODO take care of events with neither DTEND nor DURATION
        try:
            end = self.vevent['DTEND'].dt
        except KeyError:
            duration = self.vevent['DURATION']
            end = self.start + duration.dt
        if self.allday:
            return end
        if end.tzinfo is None:
            end = self.default_tz.localize(end)
        end = end.astimezone(self.local_tz)
        return end

    @property
    def summary(self):
        return self.vevent['SUMMARY']

    @property
    def recur(self):
        return 'RRULE' in self.vevent.keys()

    @property
    def raw(self):
        return self.to_ical()

    def to_ical(self):
        calendar = self._create_calendar()

        if hasattr(self.start, 'tzinfo'):
            tzs = [self.start.tzinfo]
            if self.end.tzinfo != self.start.tzinfo:
                tzs.append(self.end.tzinfo)
            for tzinfo in tzs:
                timezone = self._create_timezone(tzinfo)
                calendar.add_component(timezone)

        calendar.add_component(self.vevent)
        return calendar.to_ical()

    def compact(self, day, timeformat='%H:%M'):
        if self.allday:
            compact = self._compact_allday(day)
        else:
            compact = self._compact_datetime(day, timeformat)
        return compact

    def _compact_allday(self, day):
        if 'RRULE' in self.vevent.keys():
            recurstr = self.recurstr
        else:
            recurstr = ''
        if self.start < day and self.end > day + datetime.timedelta(days=1):
            # event started in the past and goes on longer than today:
            rangestr = self.rangestr
            pass
        elif self.start < day:
            # event started in past
            rangestr = self.rangestopstr
            pass

        elif self.end > day + datetime.timedelta(days=1):
            # event goes on longer than today
            rangestr = self.rangestartstr
        else:
            rangestr = ''
        return rangestr + self.summary + recurstr

    def _compact_datetime(self, day, timeformat='%M:%H'):
        """compact description of this event

        TODO: explain day param

        :param day:
        :type day: datetime.date

        :return: compact description of Event
        :rtype: unicode()
        """
        start = datetime.datetime.combine(day, datetime.time.min)
        end = datetime.datetime.combine(day, datetime.time.max)
        local_start = self.local_tz.localize(start)
        local_end = self.local_tz.localize(end)
        if 'RRULE' in self.vevent.keys():
            recurstr = u' ⟳'
        else:
            recurstr = ''
        tostr = '-'
        if self.start < local_start:
            startstr = u'→ '
            tostr = ''
        else:
            startstr = self.start.strftime(timeformat)
        if self.end > local_end:
            endstr = u' → '
            tostr = ''
        else:
            endstr = self.end.strftime(timeformat)

        return startstr + tostr + endstr + ': ' + self.summary + recurstr

    def _create_calendar(self):
        """
        create the calendar

        :returns: calendar
        :rtype: icalendar.Calendar()
        """
        calendar = icalendar.Calendar()
        calendar.add('version', '2.0')
        calendar.add('prodid', '-//CALENDARSERVER.ORG//NONSGML Version 1//EN')

        return calendar

    def _create_timezone(self, tz):
        """
        create an icalendar timezone from a pytz.tzinfo

        :param tz: the timezone
        :type tz: pytz.tzinfo
        :returns: timezone information set
        :rtype: icalendar.Timezone()
        """
        timezone = icalendar.Timezone()
        timezone.add('TZID', tz)

        # FIXME should match year of the event, not this year
        daylight, standard = [(num, dt) for num, dt in enumerate(tz._utc_transition_times) if dt.year == datetime.datetime.today().year]

        timezone_daylight = icalendar.TimezoneDaylight()
        timezone_daylight.add('TZNAME', tz._transition_info[daylight[0]][2])
        timezone_daylight.add('DTSTART', daylight[1])
        timezone_daylight.add('TZOFFSETFROM', tz._transition_info[daylight[0]][0])
        timezone_daylight.add('TZOFFSETTO', tz._transition_info[standard[0]][0])

        timezone_standard = icalendar.TimezoneStandard()
        timezone_standard.add('TZNAME', tz._transition_info[standard[0]][2])
        timezone_standard.add('DTSTART', standard[1])
        timezone_standard.add('TZOFFSETFROM', tz._transition_info[standard[0]][0])
        timezone_standard.add('TZOFFSETTO', tz._transition_info[daylight[0]][0])

        timezone.add_component(timezone_daylight)
        timezone.add_component(timezone_standard)

        return timezone
