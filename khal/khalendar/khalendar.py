# vim: set ts=4 sw=4 expandtab sts=4 fileencoding=utf-8:
# Copyright (c) 2011-2014 Christian Geier et al.
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
from .exceptions import UnsupportedFeatureError, ReadOnlyCalendarError

logger = log.logger


class Calendar(object):

    def __init__(self, name, dbpath, path, readonly=False, color='',
                 unicode_symbols=True, default_tz=None,
                 local_tz=None, debug=True):
        """
        :param name: the name of the calendar
        :type name: str
        :param dbpath: path where the local chaching db should be saved
        :type dbpath: str
        :param readonly: if True, this Calendar cannot be modified
        :type readonly: bool
        :param color: the color which this calendar's events should be
                      printed in
        :type color: str
        :param unicode_symbols: if True, unicode symbols will be used for
                                representing this calendars's events properties
        :type unicode_symbols: bool
        :param default_tz: timezone used by default
        :tpye default_tz: pytz.timezone
        :param local_tz: the timezone this calendar's event's times should be
                         shown in
        :type local_tz: pytz.timezone
        :param debug: if True, some debugging information will be printed
        :type debug: bool
        """

        self._default_tz = default_tz
        self._local_tz = default_tz if local_tz is None else local_tz
        self.name = name
        self.color = color
        self.path = os.path.expanduser(path)
        self._debug = debug
        self._dbtool = backend.SQLiteDb(
            self.name,
            dbpath,
            default_tz=self._default_tz,
            local_tz=self._local_tz,
            color=self.color,
            readonly=readonly,
            debug=self._debug)
        self._storage = FilesystemStorage(path, '.ics')
        self._readonly = readonly
        self._unicode_symbols = unicode_symbols

        if self._db_needs_update():
            self.db_update()

    def local_ctag(self):
        return os.path.getmtime(self.path)

    def get_by_time_range(self, start, end, show_deleted=False):
        return self._dbtool.get_time_range(start, end, show_deleted)

    def get_allday_by_time_range(self, start, end=None, show_deleted=False):
        return self._dbtool.get_allday_range(start, end, show_deleted)

    def get_datetime_by_time_range(self, start, end, show_deleted=False):
        return self._dbtool.get_time_range(start, end, show_deleted)

    def get_event(self, href):
        return self._dbtool.get(href)

    def update(self, event):
        """update an event in the database

        param event: the event that should be updated
        type event: event.Event
        """
        if self._readonly:
            raise ReadOnlyCalendarError()
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
        if self._readonly:
            raise ReadOnlyCalendarError()
        href, etag = self._storage.upload(event)
        event.href = href
        event.etag = etag
        try:
            self._dbtool.update(event.to_ical(),
                                href=href,
                                etag=etag)
            self._dbtool.set_ctag(self.local_ctag())
        except Exception as error:
            logger.error(
                'Failed to parse vcard {} during new in collection '
                '{}'.format(event.href, self.name))
            logger.debug(traceback.format_exc(error))

    def delete(self, event):
        """delete event from this collection
        """
        if self._readonly:
            raise ReadOnlyCalendarError()
        self._storage.delete(event.href, event.etag)
        self._dbtool.delete(event.href)

    def _db_needs_update(self):
        if self.local_ctag() == self._dbtool.get_ctag():
            return False
        else:
            return True

    def db_update(self):
        """update the db from the vdir,

        should be called after every change to the vdir
        """
        storage_hrefs = list()
        for href, etag in self._storage.list():
            storage_hrefs.append(href)
            if etag != self._dbtool.get_etag(href):
                self._update_vevent(href)
        db_hrefs = [href for href, etag in self._dbtool.list()]
        for href in set(db_hrefs) - set(storage_hrefs):
            self._dbtool.delete(href)

        self._dbtool.set_ctag(self.local_ctag())

    def _update_vevent(self, href):
        """should only be called during db_update, does not check for
        readonly"""
        event, etag = self._storage.get(href)
        try:
            self._dbtool.update(event.raw, href=href, etag=etag,
                                ignore_invalid_items=True)
            return True
        except Exception as error:
            if not isinstance(error, UnsupportedFeatureError):
                logger.exception('')
            logger.error(
                "During `update_vevent` we failed to parse vcard {}/{} with "
                "error\n\"{}\",\nthis means, that event is not available in "
                "khal."
                .format(self.name, href, error))
            return False

    def new_event(self, ical, local_tz, default_tz):
        """creates and returns (but does not insert) new event from ical
        string"""
        return Event(ical=ical, calendar=self.name, local_tz=local_tz,
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
    def writable_names(self):
        return [cal for cal in self._calnames if not self._calnames[cal]._readonly]

    @property
    def default_calendar_name(self):
        if self._default_calendar_name in self.names:
            return self._default_calendar_name
        elif len(self.writable_names) > 0:
            return self.writable_names[0]
        else:
            return self._calnames.values()[0].name

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
        self._calnames[event.calendar].update(event)

    def new(self, event, collection=None):
        if collection:
            self._calnames[collection].new(event)
        else:
            self._calnames[event.calendar].new(event)

    def delete(self, event):
        self._calnames[event.calendar].delete(event)

    def get_event(self, href, calendar):
        return self._calnames[calendar].get_event(href)

    def change_collection(self, event, new_collection):
        self._calnames[event.calendar].delete(event)
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
