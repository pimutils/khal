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
khalendar.Calendar and CalendarCollection should be a nice, abstract interface
to a calendar (collection). Calendar operates on vdirs but uses an sqlite db
for caching (see backend if you're interested).

If you want to see how the sausage is made:
    Welcome to the sausage factory!
"""
import os
import os.path

from vdirsyncer.storage import FilesystemStorage

from . import backend
from .event import Event


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

    def __init__(self, name, dbpath, path, readonly=False, color='',
                 unicode_symbols=True, default_timezone=None,
                 local_timezone=None):

        if local_timezone is None:
            local_timezone = default_timezone  # sync time might be off by a
            # couple of hours, perhaps we should just use UTC and be done with
            # it
        self.name = name
        self.color = color
        self.path = path
        self._dbtool = backend.SQLiteDb(
            dbpath,
            default_timezone=default_timezone,
            local_timezone=local_timezone,
            debug=True)  # TODO make debug a Calendar param
        self._storage = FilesystemStorage(path, '.ics')
        self._readonly = readonly
        self._unicode_symbols = unicode_symbols
        self._default_timezone = default_timezone
        self._local_timezone = local_timezone

        if self._db_needs_update():
            self.db_update()

    def local_ctag(self):
        return os.path.getmtime(self.path)

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
        """update an event in the database

        param event: the event that should be updated
        type event: event.Event
        """
        if event.etag is None:
            self.new(event)
        else:
            self._storage.update(event.uid, event, event.etag)
            self._dbtool.update(event.vevent.to_ical(),
                                self.name,
                                event.uid,
                                etag=event.etag)

    def new(self, event):
        """save a new event to the database

        param event: the event that should be updated
        type event: event.Event
        """
        href, etag = self._storage.upload(event)
        self._dbtool.update(event.to_ical(),
                            self.name,
                            href=href,
                            etag=etag)
        self._dbtool.set_ctag(self.name, self.local_ctag())

    def _db_needs_update(self):
        if self.local_ctag() == self._dbtool.get_ctag(self.name):
            return False
        else:
            return True

    def db_update(self):
        """update the db from the vdir,

        should be called after every change to the vdir
        """
        for href, etag in self._storage.list():
            if etag != self._dbtool.get_etag(href, self.name):
                self.update_vevent(href)
        self._dbtool.set_ctag(self.name, self.local_ctag())

    def update_vevent(self, href):
        event, etag = self._storage.get(href)
        self._dbtool.update(event.raw, self.name, href=href, etag=etag,
                            ignore_invalid_items=True)

    def new_event(self, ical):
        """creates new event form ical string"""
        return Event(ical=ical, account=self.name)


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
            result.extend(one.get_by_time_range(start, end))
        return result

    def get_allday_by_time_range(self, start, end=None):
        result = list()
        for one in self.calendars:
            result.extend(one.get_allday_by_time_range(start, end))
        return result

    def get_datetime_by_time_range(self, start, end):
        result = list()
        for one in self.calendars:
            result.extend(one.get_datetime_by_time_range(start, end))
        return result

    def update(self, event):
        self._calnames[event.account].update(event)

    def new(self, event, collection=None):
        if collection:
            self._calnames[collection].new(event)
        else:
            self._calnames[event.account].new(event)

    def change_collection(self, event, new_collection):
        self._calnames[new_collection].new(event)
        # XXX TODO

    def new_event(self, ical, collection):
        """returns a new event"""
        return self._calnames[collection].new_event(ical)
