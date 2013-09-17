#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2013 Christian Geier & contributors
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


import icalendar
import datetime


class Event(object):
    def __init__(self, ical, local_tz=None, default_tz=None,
                 start=None, end=None):
        self.vevent = icalendar.Event.from_ical(ical)
        self.allday = True
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
        # TODO take care of events with no DTEND but DURATION and neither DTEND
        # nor DURATION
        end = self.vevent['DTEND'].dt
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

    def compact(self, day):
        if self.allday:
            return self._compact_allday(day)
        else:
            return self._compact_datetime(day)

    def _compact_allday(self, day):
        if 'RRULE' in self.vevent.keys():
            recurstr = u' ⟳'
        else:
            recurstr = ''
        return self.summary + recurstr

    def _compact_datetime(self, day):
        """compact description of this event

        TODO: explain day param

        :param day:
        :type day: datetime.date

        :return: compact decsription of Event
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
            startstr = self.start.strftime('%H:%M')
        if self.end > local_end:
            endstr = u' → '
            tostr = ''
        else:
            endstr = self.end.strftime('%H:%M')

        return startstr + tostr + endstr + ': ' + self.summary + recurstr
