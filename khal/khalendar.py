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


"""
this file is name khalendar since calendar and icalendar are already taken
"""
import logging
import os
import os.path


from khal.status import OK, NEW, CHANGED, DELETED, NEWDELETE, CALCHANGED


class BaseCalendar(object):
    """base class for Calendar and CalendarCollection"""

    def get_by_time_range(self, start, end):
        raise NotImplementedError

    def get_allday_by_time_range(self, start, end):
        raise NotImplementedError

    def get_datetime_by_time_range(self, start, end):
        raise NotImplementedError

    def sync(self):
        raise NotImplementedError


class Calendar(object):
    def __init__(self, name, dbtool, path, readonly=False, color='',
                 unicode_symbols=True, default_timezone=None,
                 local_timezone=None):

        if local_timezone is None:
            local_timezone = default_timezone  # sync time might be off by a
            # couple of hours, perhaps we should just use UTC and be done with
            # it
        self.name = name
        self.color = color
        self.path = path
        self._dbtool = dbtool
        self._readonly = readonly
        self._unicode_symbols = unicode_symbols
        self._default_timezone = default_timezone
        self._local_timezone = local_timezone

        if self._db_needs_update():
            self.db_update()

    def get_by_time_range(self, start, end, show_deleted=False):
        return self._dbtool.get_time_range(start,
                                           end,
                                           self.name,
                                           self.color,
                                           self._readonly,
                                           self._unicode_symbols,
                                           show_deleted)

    def get_allday_by_time_range(self, start, end=None, show_deleted=False):
        return self._dbtool.get_allday_range(
            start, end, self.name, self.color, self._readonly,
            self._unicode_symbols, show_deleted)

    def get_datetime_by_time_range(self, start, end, show_deleted=False):
        return self._dbtool.get_time_range(
            start, end, self.name, self.color, self._readonly,
            self._unicode_symbols, show_deleted)

    def update(self, event):
        """update an event in the database"""
        self._dbtool.update(event.vevent.to_ical(),
                            self.name,
                            event.href,
                            etag=event.etag,
                            status=CHANGED)

    def new(self, event):
        """save a new event to the database"""
        self._dbtool.update(event.vevent.to_ical(),
                            self.name,
                            href='',
                            etag=event.etag,
                            status=NEW)

    def mark(self, status, event):
        self._dbtool.set_status(event.href, status, self.name)

    def _db_needs_update(self):
        mtime = os.path.getmtime(self.path)
        if mtime == self._dbtool.get_ctag(self.name):
            return False
        else:
            return True

    def db_update(self):
        files = os.listdir(self.path)
        for filename in files:
            mtime = os.path.getmtime(self.path + filename)
            if mtime != self._dbtool.get_etag(filename, self.name):
                self.update_vevent(filename)

        self._dbtool.set_ctag(self.name, os.path.getmtime(self.path))

    def update_vevent(self, filename):
        with open(self.path + filename) as eventfile:
            logging.warning('updating {0}'.format(filename))
            event = ''.join(eventfile.readlines())
        mtime = os.path.getmtime(self.path + filename)
        self._dbtool.update(event, self.name, href=filename, etag=mtime)


class CalendarCollection(object):
    def __init__(self):
        self._calnames = dict()

    @property
    def calendars(self):
        return self._calnames.values()

    def append(self, calendar):
        self._calnames[calendar.name] = calendar
        self.calendars.append(calendar)

    def get_by_time_range(self, start, end):
        result = list()
        for one in self.calendars:
            result = result + one.get_by_time_range(start, end)
        return result

    def get_allday_by_time_range(self, start, end=None):
        result = list()
        for one in self.calendars:
            result = result + one.get_allday_by_time_range(start, end)
        return result

    def get_datetime_by_time_range(self, start, end):
        result = list()
        for one in self.calendars:
            result = result + one.get_datetime_by_time_range(start, end)
        return result

    def update(self, event):
        self._calnames[event.account].update(event)

    def new(self, event):
        self._calnames[event.account].new(event)

    def change_collection(self, event, new_collection):
        self._calnames[new_collection].new(event)
        delstatus = NEWDELETE if event.status == NEW else CALCHANGED
        self._calnames[event.account].mark(delstatus, event)

    def mark(self, status, event):
        self._calnames[event.account].mark(status, event)

    def sync(self):
        rvalue = 0
        for one in self.calendars:
            rvalue += one.sync()
        return rvalue
