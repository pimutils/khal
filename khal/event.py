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


import datetime

import icalendar

from .status import OK, NEW, CHANGED, DELETED, NEWDELETE, CALCHANGED


class Event(object):
    def __init__(self, ical, status=0, href=None, account=None, local_tz=None,
                 default_tz=None, start=None, end=None, color=None,
                 readonly=False, unicode_symbols=True, etag=None):
        self.vevent = icalendar.Event.from_ical(ical)
        if account is None:
            raise TypeError('account must not be None')
        self.allday = True
        self.color = color
        self.status = status
        self.href = href
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

    def compact(self, day, timeformat='%H:%M'):
        if self.status == DELETED:
            status = 'D '
        elif self.status == NEWDELETE:
            status = 'X '
        elif self.status == NEW:
            status = 'N '
        elif self.status == CHANGED:
            status = 'M '
        else:
            status = ''
        if self.allday:
            compact = self._compact_allday(day)
        else:
            compact = self._compact_datetime(day, timeformat)
        return status + compact

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
