# Copyright (c) 2013-2022 khal contributors
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
CalendarCollection should enable modifying and querying a collection of
calendars. Each calendar is defined by the contents of a vdir, but uses an
SQLite db for caching (see backend if you're interested).
"""
import datetime as dt
import itertools
import logging
import os
import os.path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union  # noqa

from ..custom_types import CalendarConfiguration, EventCreationTypes, LocaleConfiguration
from ..icalendar import new_vevent
from . import backend
from .event import Event
from .exceptions import (
    DuplicateUid,
    EtagMissmatch,
    NonUniqueUID,
    ReadOnlyCalendarError,
    UnsupportedFeatureError,
    UpdateFailed,
)
from .vdir import (
    AlreadyExistingError,
    CollectionNotFoundError,
    Vdir,
    WrongEtagError,
    get_etag_from_file,
)

logger = logging.getLogger('khal')


class CalendarCollection:
    """CalendarCollection allows access to various calendars stored in vdirs

    all calendars are cached in an sqlitedb for performance reasons"""

    def __init__(self,
                 calendars: dict[str, CalendarConfiguration],
                 hmethod: str='fg',
                 default_color: str='',
                 multiple: str='',
                 multiple_on_overflow: bool=False,
                 color: str='',
                 priority: int=10,
                 highlight_event_days: bool=False,
                 locale: Optional[LocaleConfiguration]=None,
                 dbpath: Optional[str]=None,
                 ) -> None:
        assert locale
        assert dbpath is not None
        assert calendars is not None

        self._calendars: dict[str, CalendarConfiguration] = calendars
        self._default_calendar_name: Optional[str] = None
        self._storages: dict[str, Vdir] = {}
        file_ext: str

        for name, calendar in self._calendars.items():
            ctype = calendar.get('ctype', 'calendar')
            if ctype == 'calendar':
                file_ext = '.ics'
            elif ctype == 'birthdays':
                file_ext = '.vcf'
            else:
                raise ValueError('ctype must be either `calendar` or `birthdays`')
            try:
                self._storages[name] = Vdir(calendar['path'], file_ext)
            except CollectionNotFoundError:
                os.makedirs(calendar['path'])
                logger.info(f"created non-existing vdir {calendar['path']}")
                self._storages[name] = Vdir(calendar['path'], file_ext)

        self.hmethod = hmethod
        self.default_color = default_color
        self.multiple = multiple
        self.multiple_on_overflow = multiple_on_overflow
        self.color = color
        self.priority = priority
        self.highlight_event_days = highlight_event_days
        self._locale = locale
        self._backend = backend.SQLiteDb(self.names, dbpath, self._locale)
        self._last_ctags: dict[str, str] = {}
        self.update_db()

    @property
    def writable_names(self) -> list[str]:
        return [c for c in self._calendars if not self._calendars[c].get('readonly', False)]

    @property
    def calendars(self) -> Iterable[CalendarConfiguration]:
        return self._calendars.values()

    @property
    def names(self) -> Iterable[str]:
        return self._calendars.keys()

    @property
    def default_calendar_name(self) -> Optional[str]:
        return self._default_calendar_name

    @default_calendar_name.setter
    def default_calendar_name(self, default: str) -> None:
        if default is None:
            self._default_calendar_name = default
        elif default not in self.names:
            raise ValueError(f'Unknown calendar: {default}')

        readonly = self._calendars[default].get('readonly', False)

        if not readonly:
            self._default_calendar_name = default
        else:
            raise ValueError(
                f'Calendar "{default}" is read-only and cannot be used as default')

    def _local_ctag(self, calendar: str) -> str:
        return get_etag_from_file(self._calendars[calendar]['path'])

    def get_floating(self, start: dt.datetime, end: dt.datetime) -> Iterable[Event]:
        for args in self._backend.get_floating(start, end):
            yield self._construct_event(*args)

    def get_localized(self, start: dt.datetime, end: dt.datetime) -> Iterable[Event]:
        for args in self._backend.get_localized(start, end):
            yield self._construct_event(*args)

    def get_events_on(self, day: dt.date) -> Iterable[Event]:
        """return all events on `day`"""
        start = dt.datetime.combine(day, dt.time.min)
        end = dt.datetime.combine(day, dt.time.max)
        floating_events = self.get_floating(start, end)
        localize = self._locale['local_timezone'].localize
        localized_events = self.get_localized(localize(start), localize(end))
        return itertools.chain(localized_events, floating_events)

    def get_calendars_on(self, day: dt.date) -> list[str]:
        start = dt.datetime.combine(day, dt.time.min)
        end = dt.datetime.combine(day, dt.time.max)
        localize = self._locale['local_timezone'].localize
        calendars = itertools.chain(
            self._backend.get_floating_calendars(start, end),
            self._backend.get_localized_calendars(localize(start), localize(end)),
        )
        return list(set(calendars))

    def update(self, event: Event) -> None:
        """update `event` in vdir and db"""
        assert event.etag is not None
        assert event.calendar is not None
        assert event.href is not None
        assert event.raw is not None
        if self._calendars[event.calendar]['readonly']:
            raise ReadOnlyCalendarError()
        with self._backend.at_once():
            event.etag = self._storages[event.calendar].update(event.href, event, event.etag)
            self._backend.update(event.raw, event.href, event.etag, calendar=event.calendar)
            self._backend.set_ctag(self._local_ctag(event.calendar), calendar=event.calendar)

    def force_update(self, event: Event, collection: Optional[str]=None) -> None:
        """update `event` even if an event with the same uid/href already exists"""
        href: str
        calendar = collection if collection is not None else event.calendar
        assert calendar is not None
        if self._calendars[calendar]['readonly']:
            raise ReadOnlyCalendarError()

        with self._backend.at_once():
            try:
                href, etag = self._storages[calendar].upload(event)
            except AlreadyExistingError as error:
                href = error.existing_href
                _, etag = self._storages[calendar].get(href)
                etag = self._storages[calendar].update(href, event, etag)
            self._backend.update(event.raw, href, etag, calendar=calendar)
            self._backend.set_ctag(self._local_ctag(calendar), calendar=calendar)

    def insert(self, event: Event, collection: Optional[str]=None) -> None:
        """Insert a new event to the vdir and the database

        The event will get a new href and etag properties. If ``collection`` is
        ``None``, then ``event.calendar`` must be defined.

        :param event: the event to be inserted.
        """
        # TODO FIXME not all `event`s are actually of type Event, we also uptade
        # with vdir.Items. Those don't have an .href or .etag property which we
        # than attach anyway. Works, but pretty ugly and any type checker will
        # complain.
        calendar = collection if collection is not None else event.calendar
        assert calendar is not None
        if hasattr(event, 'etag'):
            assert not event.etag
        if self._calendars[calendar]['readonly']:
            raise ReadOnlyCalendarError()

        with self._backend.at_once():
            try:
                event.href, event.etag = self._storages[calendar].upload(event)
            except AlreadyExistingError as Error:
                href = getattr(Error, 'existing_href', None)
                raise DuplicateUid(href)
            self._backend.update(event.raw, event.href, event.etag, calendar=calendar)
            self._backend.set_ctag(self._local_ctag(calendar), calendar=calendar)

    def delete(self, href: str, etag: Optional[str], calendar: str) -> None:
        """Delete an event specified by `href` from `calendar`"""
        if self._calendars[calendar]['readonly']:
            raise ReadOnlyCalendarError()
        try:
            self._storages[calendar].delete(href, etag)
        except WrongEtagError:
            raise EtagMissmatch()
        self._backend.delete(href, calendar=calendar)

    def delete_instance(self,
                        href: str,
                        etag: Optional[str],
                        calendar: str,
                        rec_id: dt.datetime,
                        ) -> Event:
        """Delete a recurrence instance from an event specified by `href` from `calendar`

        returns the updated event
        """
        if self._calendars[calendar]['readonly']:
            raise ReadOnlyCalendarError()
        event = self.get_event(href, calendar)
        if etag and etag != event.etag:
            raise EtagMissmatch()

        event.delete_instance(rec_id)
        self.update(event)
        return event

    def get_event(self, href: str, calendar: str) -> Event:
        """get an event by its href from the datatbase"""
        event_str, etag = self._backend.get_with_etag(href, calendar)
        return self._construct_event(event_str, etag=etag, href=href, calendar=calendar)

    def _construct_event(self,
                         item: str,
                         href: str,
                         start: Optional[Union[dt.datetime, dt.date]] = None,
                         end: Optional[Union[dt.datetime, dt.date]] = None,
                         ref: str='PROTO',
                         etag: Optional[str]=None,
                         calendar: Optional[str]=None,
                         ) -> Event:
        assert calendar is not None
        event = Event.fromString(
            item,
            locale=self._locale,
            href=href,
            calendar=calendar,
            etag=etag,
            start=start,
            end=end,
            ref=ref,
            color=self._calendars[calendar]['color'],
            readonly=self._calendars[calendar]['readonly'],
            addresses=self._calendars[calendar]['addresses'],
        )
        return event

    def change_collection(self, event: Event, new_collection: str) -> None:
        """Moves `event` to a new collection (calendar)"""
        href, etag, calendar = event.href, event.etag, event.calendar
        event.etag = None
        self.insert(event, new_collection)
        assert href is not None
        assert calendar is not None
        self.delete(href, etag, calendar=calendar)

    def create_event_from_ics(self,
                              ical: str,
                              calendar_name: str,
                              etag: Optional[str]=None,
                              href: Optional[str]=None,
                              ) -> Event:
        """creates and returns (but does not insert) a new event from ical
        string"""
        calendar = calendar_name or self.writable_names[0]
        return Event.fromString(ical, locale=self._locale, calendar=calendar, etag=etag, href=href)

    def create_event_from_dict(self,
                               event_dict: EventCreationTypes,
                               calendar_name: Optional[str] = None,
                               ) -> Event:
        """Creates an Event from the method's arguments
        """
        vevent = new_vevent(locale=self._locale, **event_dict)
        calendar_name = calendar_name or self.default_calendar_name or self.writable_names[0]
        assert calendar_name is not None
        return self.create_event_from_ics(vevent.to_ical(), calendar_name)

    def update_db(self) -> None:
        """update the db from the vdir,

        should be called after every change to the vdir
        """
        for calendar in self._calendars:
            if self._needs_update(calendar, remember=True):
                self._db_update(calendar)

    def needs_update(self) -> bool:
        """Check if you need to call update_db.

        This could either be the case because the vdirs were changed externally,
        or another instance of khal updated the caching db already.
        """
        # TODO is it a good idea to munch both use cases together?
        # in case another instance of khal has updated the db, we only need
        # to get new events, but # update_db() takes potentially a long time to return
        # but then the code (in ikhal's refresh code) would need to look like
        # this:
        #
        # update_ui = False
        # if collection.needs_update():
        #   collection.update_db()
        #   update_ui = True
        # if collection.needs_refresh() or update_ui:
        #   do_the_update()
        #
        # and the API would be made even uglier than it already is...
        for calendar in self._calendars:
            if self._needs_update(calendar) or \
                    self._last_ctags[calendar] != self._local_ctag(calendar):
                return True
        return False

    def _needs_update(self, calendar: str, remember: bool=False) -> bool:
        """checks if the db for the given calendar needs an update"""
        local_ctag = self._local_ctag(calendar)
        if remember:
            self._last_ctags[calendar] = local_ctag
        return local_ctag != self._backend.get_ctag(calendar)

    def _db_update(self, calendar: str) -> None:
        """implements the actual db update on a per calendar base"""
        local_ctag = self._local_ctag(calendar)
        db_hrefs = {href for href, etag in self._backend.list(calendar)}
        storage_hrefs: set[str] = set()
        bdays = self._calendars[calendar].get('ctype') == 'birthdays'

        with self._backend.at_once():
            for href, etag in self._storages[calendar].list():
                storage_hrefs.add(href)
                db_etag = self._backend.get_etag(href, calendar=calendar)
                if etag != db_etag:
                    logger.debug(f'Updating {href} because {etag} != {db_etag}')
                    self._update_vevent(href, calendar=calendar)
            for href in db_hrefs - storage_hrefs:
                if bdays:
                    for sh in storage_hrefs:
                        if href.startswith(sh):
                            break
                    else:
                        self._backend.delete(href, calendar=calendar)
                else:
                    self._backend.delete(href, calendar=calendar)
            self._backend.set_ctag(local_ctag, calendar=calendar)
            self._last_ctags[calendar] = local_ctag

    def _update_vevent(self, href: str, calendar: str) -> bool:
        """should only be called during db_update, only updates the db,
        does not check for readonly"""
        event, etag = self._storages[calendar].get(href)
        try:
            if self._calendars[calendar].get('ctype') == 'birthdays':
                update = self._backend.update_vcf_dates
            else:
                update = self._backend.update
            update(event.raw, href=href, etag=etag, calendar=calendar)
            return True
        except Exception as e:
            if not isinstance(e, (UpdateFailed, UnsupportedFeatureError, NonUniqueUID)):
                logger.exception('Unknown exception happened.')
            logger.warning(
                f'Skipping {calendar}/{href}: {str(e)}\n'
                'This event will not be available in khal.')
            return False

    def search(self, search_string: str) -> Iterable[Event]:
        """search for the db for events matching `search_string`"""
        return (self._construct_event(*args) for args in self._backend.search(search_string))

    def get_day_styles(self, day: dt.date, focus: bool) -> Optional[Union[str, tuple[str, str]]]:
        calendars = self.get_calendars_on(day)
        if len(calendars) == 0:
            return None
        if self.color != '':
            return 'highlight_days_color'
        if len(calendars) == 1:
            return 'calendar ' + calendars[0]
        if self.multiple != '' and not (self.multiple_on_overflow and len(calendars) == 2):
            return 'highlight_days_multiple'
        return ('calendar ' + calendars[0], 'calendar ' + calendars[1])

    def get_styles(self, date: dt.date, focus: bool) -> Optional[Union[str, tuple[str, str]]]:
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
