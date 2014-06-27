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
import traceback

from vdirsyncer.storage import FilesystemStorage

from . import backend
from .event import Event
from .. import log

logger = log.logger


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
                 unicode_symbols=True, default_tz=None,
                 local_tz=None, debug=True):

        self._default_tz = default_tz
        self._local_tz = default_tz if local_tz is None else local_tz
        self.name = name
        self.color = color
        self.path = path
        self._debug = debug
        self._dbtool = backend.SQLiteDb(
            dbpath,
            default_tz=self._default_tz,
            local_tz=self._local_tz,
            debug=self._debug)
        self._storage = FilesystemStorage(path, '.ics')
        self._readonly = readonly
        self._unicode_symbols = unicode_symbols

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

    def get_event(self, href):
        return self._dbtool.get_vevent_from_db(
            href, self.name, color=self.color, readonly=self._readonly,
            unicode_symbols=self._unicode_symbols)

    def update(self, event):
        """update an event in the database

        param event: the event that should be updated
        type event: event.Event
        """
        if event.etag is None:
            self.new(event)
        else:
            try:
                self._storage.update(event.href, event, event.etag)
                self._dbtool.update(event.vevent.to_ical(),
                                    self.name,
                                    event.href,
                                    etag=event.etag)
            except Exception as error:
                logger.error('Failed to parse vcard {} from collection {} '
                             'during update'.format(event.href, self.name))
                logger.debug(traceback.format_exc(error))

    def new(self, event):
        """save a new event to the database

        param event: the event that should be updated
        type event: event.Event
        """
        href, etag = self._storage.upload(event)
        event.href = href
        event.etag = etag
        try:
            self._dbtool.update(event.to_ical(),
                                self.name,
                                href=href,
                                etag=etag)
            self._dbtool.set_ctag(self.name, self.local_ctag())
        except Exception as error:
            logger.error(
                'Failed to parse vcard {} during new in collection '
                '{}'.format(event.href, self.name))
            logger.debug(traceback.format_exc(error))

    def delete(self, event):
        """delete event from this collection
        """
        self._storage.delete(event.href, event.etag)
        self._dbtool.delete(event.href, event.account)

    def _db_needs_update(self):
        if self.local_ctag() == self._dbtool.get_ctag(self.name):
            return False
        else:
            return True

    def db_update(self):
        """update the db from the vdir,

        should be called after every change to the vdir
        """
        status = True
        for href, etag in self._storage.list():
            if etag != self._dbtool.get_etag(href, self.name):
                status = status and self.update_vevent(href)
        if status:
            self._dbtool.set_ctag(self.name, self.local_ctag())

    def update_vevent(self, href):
        event, etag = self._storage.get(href)
        try:
            self._dbtool.update(event.raw, self.name, href=href, etag=etag,
                                ignore_invalid_items=True)
            return True
        except Exception as error:
            logger.error(
                'Failed to parse vcard {} during '
                'update_vevent in collection ''{}'.format(href, self.name))
            logger.debug(traceback.format_exc(error))
            return False

    def new_event(self, ical, local_tz, default_tz):
        """creates new event form ical string"""
        return Event(ical=ical, account=self.name, local_tz=local_tz,
                     default_tz=default_tz)


class CalendarCollection(object):

    def __init__(self):
        self._calnames = dict()
        self._default_calendar_name = None

    @property
    def calendars(self):
        return self._calnames.values()

    @property
    def names(self):
        return self._calnames.keys()

    @property
    def default_calendar_name(self):
        if self._default_calendar_name in self.names:
            return self._default_calendar_name
        else:
            return self.names[0]

    def append(self, calendar):
        self._calnames[calendar.name] = calendar
        self.calendars.append(calendar)

    def get_by_time_range(self, start, end):
        events = list()
        for one in self.calendars:
            events.extend(one.get_by_time_range(start, end))

        return events

    def get_allday_by_time_range(self, start, end=None):
        events = list()
        for one in self.calendars:
            events.extend(one.get_allday_by_time_range(start, end))
        return events

    def get_datetime_by_time_range(self, start, end):
        events = list()
        for one in self.calendars:
            events.extend(one.get_datetime_by_time_range(start, end))
        return events

    def update(self, event):
        self._calnames[event.account].update(event)

    def new(self, event, collection=None):
        if collection:
            self._calnames[collection].new(event)
        else:
            self._calnames[event.account].new(event)

    def delete(self, event):
        self._calnames[event.account].delete(event)

    def get_event(self, href, account):
        return self._calnames[account].get_event(href)

    def change_collection(self, event, new_collection):
        self._calnames[event.account].delete(event)
        self._calnames[new_collection].new(event)
        # TODO would be better to first add to new collection, then delete
        # currently not possible since new modifies event.etag

    def new_event(self, ical, collection, local_tz, default_tz):
        """returns a new event"""
        return self._calnames[collection].new_event(ical, local_tz, default_tz)

    def _db_needs_update(self):
        any([one._db_needs_update() for one in self.calendars])

    def db_update(self):
        for one in self.calendars:
            one.db_update()
