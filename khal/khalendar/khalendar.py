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
"""
import datetime
import os
import os.path

from vdirsyncer.storage.filesystem import FilesystemStorage
from vdirsyncer.exceptions import AlreadyExistingError

from . import backend
from .event import Event
from .. import log
from .exceptions import CouldNotCreateDbDir, UnsupportedFeatureError, \
    ReadOnlyCalendarError, UpdateFailed, DuplicateUid

logger = log.logger


def create_directory(path):
    if not os.path.isdir(path):
        if os.path.exists(path):
            raise RuntimeError('{} is not a directory.'.format(path))
        try:
            os.makedirs(path, mode=0o750)
        except OSError as error:
            logger.fatal('failed to create {0}: {1}'.format(path, error))
            raise CouldNotCreateDbDir()


class Calendar(object):

    def __init__(self, name, dbpath, path, readonly=False, color='',
                 unicode_symbols=True, locale=None, ctype='calendar'):
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
        create_directory(path)
        if ctype == 'calendar':
            self._dbtool = backend.SQLiteDb(
                self.name, dbpath, locale=self._locale)
            file_ext = '.ics'
        elif ctype == 'birthdays':
            self._dbtool = backend.SQLiteDb_Birthdays(
                self.name, dbpath, locale=self._locale)
            file_ext = '.vcf'
        else:
            raise ValueError('ctype must be either `calendar` or `birthdays`')
        self._storage = FilesystemStorage(path, file_ext)
        self._readonly = readonly
        self._unicode_symbols = unicode_symbols

        if self._db_needs_update():
            self.db_update()

    @property
    def readonly(self):
        return self._readonly

    def _cover_event(self, event):
        event.color = self.color
        event.readonly = self._readonly
        event.unicode_symbols = self._unicode_symbols
        return event

    def local_ctag(self):
        return os.path.getmtime(self.path)

    def get_allday_by_time_range(self, start):
        return [self._cover_event(event) for event in
                self._dbtool.get_allday_range(start)]

    def get_datetime_by_time_range(self, start, end):
        return [self._cover_event(event) for event in
                self._dbtool.get_time_range(start, end)]

    def get_events_at(self, dtime=datetime.datetime.now()):
        """return events which are scheduled at `dtime`"""
        events = list()
        events.extend(self._dbtool.get_allday_at(dtime))
        events.extend(self._dbtool.get_datetime_at(dtime))
        return [self._cover_event(event) for event in events]

    def get_event(self, href):
        return self._cover_event(self._dbtool.get(href))

    def update(self, event):
        """update an event in vdir storage and in the database

        param event: the event that should be updated
        type event: event.Event
        """
        assert event.etag
        if self._readonly:
            raise ReadOnlyCalendarError()

        with self._dbtool.at_once():
            event.etag = self._storage.update(event.href, event, event.etag)
            self._dbtool.update(event.raw, event.href, event.etag)
            self._dbtool.set_ctag(self.local_ctag())

    def force_update(self, event):
        # FIXME after the next vdirsyncer release, that check function is
        # not needed than
        # AlreadyExistingError now knows the conflicting events uid
        def check(self, item):
            """check if this an event with this item's uid already exists"""
            try:
                # FIXME remove on next vdirsyncer release
                href = self._deterministic_href(item)
            except AttributeError:
                href = self._get_href(item.uid)
            if not self.has(href):
                return None, None
            else:
                return href, self.get(href)[1]

        if self._readonly:
            raise ReadOnlyCalendarError()
        with self._dbtool.at_once():
            href, etag = check(self._storage, event)
            if href is None:
                self.new(event)
            else:
                etag = self._storage.update(href, event, etag)
                self._dbtool.update(event.raw, href, etag)
                self._dbtool.set_ctag(self.local_ctag())

    def new(self, event):
        """save a new event to the vdir and the database

        param event: the event that should be updated
        type event: event.Event
        """
        if hasattr(event, 'etag'):
            assert not event.etag
        if self._readonly:
            raise ReadOnlyCalendarError()

        with self._dbtool.at_once():

            try:
                href, etag = self._storage.upload(event)
            except AlreadyExistingError as Error:
                href = getattr(Error, 'existing_href', None)
                raise DuplicateUid(href)
            self._dbtool.update(event.raw, href, etag)
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
        """should only be called during db_update, only updates the db,
        does not check for readonly"""
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
        return Event.fromString(ical, locale=self._locale, calendar=self.name)

    def search(self, search_string):
        return [self._cover_event(event) for event in
                self._dbtool.search(search_string)]


class CalendarCollection(object):

    def __init__(self, hmethod='fg',
                 default_color='',
                 multiple='',
                 color='',
                 highlight_event_days=0,
                 locale=None):
        self._calnames = dict()
        self._default_calendar_name = None
        self.hmethod = hmethod
        self.default_color = default_color
        self.multiple = multiple
        self.color = color
        self.highlight_event_days = highlight_event_days
        self.locale = locale
        self.localize = self.locale['local_timezone'].localize

    @property
    def writable_names(self):
        return [c.name for c in self.calendars if not c.readonly]

    @property
    def calendars(self):
        return self._calnames.values()

    @property
    def names(self):
        return self._calnames.keys()

    @property
    def default_calendar_name(self):
        return self._default_calendar_name

    @default_calendar_name.setter
    def default_calendar_name(self, default):
        if default is None:
            self._default_calendar_name = default
        elif default not in self.names:
            raise ValueError('Unknown calendar: {}'
                             .format(default))

        readonly = self._calnames[default].readonly

        if not readonly:
            self._default_calendar_name = default
        else:
            raise ValueError('Default calendar is read-only: {}'
                             .format(default))

    def append(self, calendar):
        """append a new khalendar to this collection"""
        self._calnames[calendar.name] = calendar

    def get_allday_by_time_range(self, start):
        events = list()
        for one in self.calendars:
            events.extend(one.get_allday_by_time_range(start))
        return events

    def get_datetime_by_time_range(self, start, end):
        events = list()
        for one in self.calendars:
            events.extend(one.get_datetime_by_time_range(start, end))
        return events

    def get_events_at(self, dtime=datetime.datetime.now()):
        if dtime is None:
            dtime = datetime.datetime.now()
        events = list()
        for one in self.calendars:
            events.extend(one.get_events_at(dtime))
        return events

    def update(self, event):
        self._calnames[event.calendar].update(event)

    def force_update(self, event, collection=None):
        if collection:
            self._calnames[collection].force_update(event)
        else:
            self._calnames[event.calendar].force_update(event)

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
        event.etag = None
        self._calnames[new_collection].new(event)
        self._calnames[calendar].delete(href, etag)

    def new_event(self, ical, collection):
        """returns a new event"""
        return self._calnames[collection or self.writable_names[0]].new_event(ical)

    def _db_needs_update(self):
        any([one._db_needs_update() for one in self.calendars])

    def db_update(self):
        for one in self.calendars:
            one.db_update()

    def search(self, search_string):
        events = list()
        for one in self.calendars:
            events.extend(one.search(search_string))
        return events

    def get_event_color(self, event):
        """Because multi-line lambdas would be un-Pythonic
        """
        if event.color == '':
            return self.default_color
        return event.color

    def get_day_styles(self, day, focus):
        start = self.localize(datetime.datetime.combine(day, datetime.time.min))
        end = self.localize(datetime.datetime.combine(day, datetime.time.max))
        devents = self.get_datetime_by_time_range(start, end) + \
            self.get_allday_by_time_range(day)
        if len(devents) == 0:
            return None
        prefix = ''
        if self.hmethod == 'bg' or self.hmethod == 'background':
            prefix = 'bg '
        if self.color != '':
            return prefix + self.color
        dcolors = list(set(map(lambda x: self.get_event_color(x), devents)))
        if len(dcolors) == 1:
            if devents[0].color == '':
                return prefix + self.default_color
            else:
                return prefix + devents[0].color
        if self.multiple != '':
            return prefix + self.multiple
        return (prefix + dcolors[0], prefix + dcolors[1])

    def get_styles(self, date, focus):
        if focus:
            if date == date.today():
                return 'today focus'
            else:
                return 'reveal focus'
        else:
            if date == date.today():
                return 'today'
            else:
                if self.highlight_event_days:
                    return self.get_day_styles(date, focus)
                else:
                    return None
