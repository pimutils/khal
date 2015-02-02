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
from .. import log
from .exceptions import UnsupportedFeatureError, ReadOnlyCalendarError, \
    UpdateFailed

logger = log.logger


def create_directory(path):
    if not os.path.isdir(path):
        if os.path.exists(path):
            raise RuntimeError('{} is not a directory.'.format(path))
        os.makedirs(path, mode=0o750)


class Calendar(object):

    def __init__(self, name, dbpath, path, readonly=False, color='',
                 unicode_symbols=True, locale=None):
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
        :param locale: the locale settings
        :type locale: dict()
        """
        self._locale = locale

        self.name = name
        self.color = color
        self.path = os.path.expanduser(path)
        self._dbtool = backend.SQLiteDb(self.name, dbpath, locale=self._locale)
        create_directory(path)
        self._storage = FilesystemStorage(path, '.ics')
        self._readonly = readonly
        self._unicode_symbols = unicode_symbols

        if self._db_needs_update():
            self.db_update()

    def _cover_event(self, event):
        event.color = self.color
        event.readonly = self._readonly
        event.unicode_symbols = self._unicode_symbols
        return event

    def local_ctag(self):
        return os.path.getmtime(self.path)

    def get_allday_by_time_range(self, start, end=None):
        return [self._cover_event(event) for event in
                self._dbtool.get_allday_range(start, end)]

    def get_datetime_by_time_range(self, start, end):
        return [self._cover_event(event) for event in
                self._dbtool.get_time_range(start, end)]

    def get_event(self, href):
        return self._cover_event(self._dbtool.get(href))

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
            self._storage.update(event.href, event, event.etag)
            self._dbtool.update(event.vevent.to_ical(),
                                event.href,
                                etag=event.etag)

    def new(self, event):
        """save a new event to the database

        param event: the event that should be updated
        type event: event.Event
        """
        if self._readonly:
            raise ReadOnlyCalendarError()
        event.href, event.etag = self._storage.upload(event)
        self._dbtool.update(event.to_ical(), event.href, event.etag)
        self._dbtool.set_ctag(self.local_ctag())

    def delete(self, href, etag):
        """delete event from this collection
        """
        if self._readonly:
            raise ReadOnlyCalendarError()
        self._storage.delete(href, etag)
        self._dbtool.delete(href)

    def _db_needs_update(self):
        if self.local_ctag() == self._dbtool.get_ctag():
            return False
        else:
            return True

    def db_update(self):
        """update the db from the vdir,

        should be called after every change to the vdir
        """
        db_hrefs = set(href for href, etag in self._dbtool.list())
        storage_hrefs = set()

        with self._dbtool.at_once():
            for href, etag in self._storage.list():
                storage_hrefs.add(href)
                dbetag = self._dbtool.get_etag(href)
                if etag != dbetag:
                    logger.debug('Updating {} because {} != {}'
                                 .format(href, etag, dbetag))
                    self._update_vevent(href)
            for href in db_hrefs - storage_hrefs:
                self._dbtool.delete(href)

            self._dbtool.set_ctag(self.local_ctag())

    def _update_vevent(self, href):
        """should only be called during db_update, does not check for
        readonly"""
        event, etag = self._storage.get(href)
        try:
            self._dbtool.update(event.raw, href=href, etag=etag)
            return True
        except Exception as e:
            if not isinstance(e, (UpdateFailed, UnsupportedFeatureError)):
                logger.exception('Unknown exception happened.')
            logger.warning(
                'Skipping {}/{}: {}\n'
                'This event will not be available in khal.'
                .format(self.name, href, str(e))
            )
            return False

    def new_event(self, ical):
        """creates and returns (but does not insert) new event from ical
        string"""
        return Event(ical=ical, calendar=self.name, locale=self._locale)


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
        return [cal for cal in self._calnames
                if not self._calnames[cal]._readonly]

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

    def delete(self, href, etag, calendar):
        self._calnames[calendar].delete(href, etag)

    def get_event(self, href, calendar):
        return self._calnames[calendar].get_event(href)

    def change_collection(self, event, new_collection):
        href, etag, calendar = event.href, event.etag, event.calendar
        self._calnames[new_collection].new(event)
        self._calnames[calendar].delete(href, etag)

    def new_event(self, ical, collection):
        """returns a new event"""
        return self._calnames[collection].new_event(ical)

    def _db_needs_update(self):
        any([one._db_needs_update() for one in self.calendars])

    def db_update(self):
        for one in self.calendars:
            one.db_update()
