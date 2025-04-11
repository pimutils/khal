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
The SQLite backend implementation.
"""

import contextlib
import datetime as dt
import logging
import sqlite3
from collections.abc import Iterable, Iterator
from enum import IntEnum
from os import makedirs, path
from typing import Any, Optional, Union

import icalendar
import icalendar.cal
import pytz
from dateutil import parser

from .. import utils
from ..custom_types import EventTuple, LocaleConfiguration
from ..icalendar import assert_only_one_uid, cal_from_ics
from ..icalendar import expand as expand_vevent
from ..icalendar import sanitize as sanitize_vevent
from ..icalendar import sort_key as sort_vevent_key
from .exceptions import CouldNotCreateDbDir, NonUniqueUID, OutdatedDbVersionError, UpdateFailed

logger = logging.getLogger('khal')

DB_VERSION = 5  # The current db layout version

RECURRENCE_ID = 'RECURRENCE-ID'
THISANDFUTURE = 'THISANDFUTURE'
THISANDPRIOR = 'THISANDPRIOR'

PROTO = 'PROTO'


class EventType(IntEnum):
    DATE = 0
    DATETIME = 1


class SQLiteDb:
    """
    This class should provide a caching database for a calendar, keeping raw
    vevents in one table and allowing to retrieve them by dates (via the help
    of some auxiliary tables)

    :param calendar: names of calendars to select from, those are used as
        additional itentifiers together with event's uids. Each (uid, calendar)
        combination should be unique.
    :param db_path: path where this sqlite database will be saved, if this is
        None, a place according to the XDG specifications will be chosen
    """

    def __init__(self,
                 calendars: Iterable[str],
                 db_path: Optional[str],
                 locale: LocaleConfiguration,
                 ) -> None:
        assert db_path is not None
        self.calendars: list[str] = list(calendars)
        self.db_path = path.expanduser(db_path)
        self._create_dbdir()
        self.locale = locale
        self._at_once: bool = False
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._create_default_tables()
        self._check_calendars_exists()
        self._check_table_version()

    @contextlib.contextmanager
    def at_once(self) -> Iterator['SQLiteDb']:
        assert not self._at_once
        self._at_once = True
        try:
            yield self
        except:  # noqa
            raise
        else:
            self.conn.commit()
        finally:
            self._at_once = False

    def _create_dbdir(self) -> None:
        """create the dbdir if it doesn't exist"""
        if self.db_path == ':memory:':
            return None
        dbdir = self.db_path.rsplit('/', 1)[0]
        if not path.isdir(dbdir):
            try:
                logger.debug('trying to create the directory for the db')
                makedirs(dbdir, mode=0o770)
                logger.debug('success')
            except OSError as error:
                logger.critical(f'failed to create {dbdir}: {error}')
                raise CouldNotCreateDbDir()

    def _check_table_version(self) -> None:
        """tests for current db Version
        if the table is still empty, insert db_version
        """
        self.cursor.execute('SELECT version FROM version')
        result = self.cursor.fetchone()
        if result is None:
            self.cursor.execute('INSERT INTO version (version) VALUES (?)',
                                (DB_VERSION, ))
            self.conn.commit()
        elif not result[0] == DB_VERSION:
            raise OutdatedDbVersionError(
                str(self.db_path) +
                " is probably an invalid or outdated database.\n"
                "You should consider removing it and running khal again.")

    def _create_default_tables(self) -> None:
        """creates version and calendar tables and inserts table version number
        """
        self.cursor.execute('CREATE TABLE IF NOT EXISTS '
                            'version (version INTEGER)')
        logger.debug("created version table")

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS calendars (
            calendar TEXT NOT NULL UNIQUE,
            resource TEXT NOT NULL,
            ctag TEXT
            )''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS events (
                href TEXT NOT NULL,
                calendar TEXT NOT NULL,
                sequence INT,
                etag TEXT,
                item TEXT,
                primary key (href, calendar)
                );''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS recs_loc (
            dtstart INT NOT NULL,
            dtend INT NOT NULL,
            href TEXT NOT NULL REFERENCES events( href ),
            rec_inst TEXT NOT NULL,
            ref TEXT NOT NULL,
            dtype INT NOT NULL,
            calendar TEXT NOT NULL,
            primary key (href, rec_inst, calendar)
            );''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS recs_float (
            dtstart INT NOT NULL,
            dtend INT NOT NULL,
            href TEXT NOT NULL REFERENCES events( href ),
            rec_inst TEXT NOT NULL,
            ref TEXT NOT NULL,
            dtype INT NOT NULL,
            calendar TEXT NOT NULL,
            primary key (href, rec_inst, calendar)
            );''')
        self.conn.commit()

    def _check_calendars_exists(self) -> None:
        """make sure an entry for the current calendar exists in `calendar`
        table
        """
        for cal in self.calendars:
            self.cursor.execute('''SELECT count(*) FROM calendars WHERE calendar = ?;''', (cal,))
            result = self.cursor.fetchone()

            if result[0] != 0:
                logger.debug(f"tables for calendar {cal} exist")
            else:
                sql_s = 'INSERT INTO calendars (calendar, resource) VALUES (?, ?);'
                stuple = (cal, '')
                self.sql_ex(sql_s, stuple)

    def sql_ex(self, statement: str, stuple: tuple) -> list:
        """wrapper for sql statements, does a "fetchall" """
        self.cursor.execute(statement, stuple)
        result = self.cursor.fetchall()
        if not self._at_once:
            self.conn.commit()
        return result

    def update(self,
               vevent_str: str,
               href: str,
               etag: str='',
               calendar: Optional[str]=None,
               ) -> None:
        """insert a new or update an existing event into the db

        This is mostly a wrapper around two SQL statements, doing some cleanup
        before.

        :param vevent_str: event to be inserted or updated.
            We assume that even if it contains more than one VEVENT, that they
            are all part of the same event and all have the same UID
        :param href: href of the card on the server, if this href already
            exists in the db the card gets updated. If no href is given, a
            random href is chosen and it is implied that this card does not yet
            exist on the server, but will be uploaded there on next sync.
        :param etag: the etag of the vcard, if this etag does not match the
            remote etag on next sync, this card will be updated from the server.
            For locally created vcards this should not be set
        """
        assert calendar is not None
        assert href is not None
        ical = cal_from_ics(vevent_str)
        check_for_errors(ical, calendar, href)
        if not assert_only_one_uid(ical):
            logger.warning(
                f"The .ics file at {calendar}/{href} contains multiple UIDs.\n"
                "This should not occur in vdir .ics files.\n"
                "If you didn't edit the file by hand, please report a bug "
                "at https://github.com/pimutils/khal/issues .\n"
                "If you want to import it, please use `khal import FILE`."
            )
            raise NonUniqueUID
        vevents = (sanitize_vevent(c, self.locale['default_timezone'], href, calendar) for
                   c in ical.walk() if c.name == 'VEVENT')
        # Need to delete the whole event in case we are updating a
        # recurring event with an event which is either not recurring any
        # more or has EXDATEs, as those would be left in the recursion
        # tables. There are obviously better ways to achieve the same
        # result.
        self.delete(href, calendar=calendar)
        for vevent in sorted(vevents, key=sort_vevent_key):
            check_for_errors(vevent, calendar, href)
            check_support(vevent, href, calendar)
            self._update_impl(vevent, href, calendar)

        sql_s = ('INSERT INTO events (item, etag, href, calendar) VALUES (?, ?, ?, ?);')
        stuple = (vevent_str, etag, href, calendar)
        self.sql_ex(sql_s, stuple)

    def update_vcf_dates(self, vevent_str: str, href: str, etag: str='',
                         calendar: Optional[str]=None) -> None:
        """insert events from a vcard into the db

        This is will parse BDAY, ANNIVERSARY, X-ANNIVERSARY and X-ABDATE fields.
        It will also look for any X-ABLABEL fields associated with an X-ABDATE
        and use that in the event description.

        :param vevent_str: contact (vcard) to be parsed.
        :param href: href of the card on the server, if this href already
            exists in the db the card gets updated. If no href is given, a
            random href is chosen and it is implied that this card does not yet
            exist on the server, but will be uploaded there on next sync.
        :param etag: the etag of the vcard, if this etag does not match the
            remote etag on next sync, this card will be updated from the server.
            For locally created vcards this should not be set
        """
        assert calendar is not None
        assert href is not None
        # Delete all event entries for this contact
        self.deletelike(href + '%', calendar=calendar)
        ical = cal_from_ics(vevent_str)
        vcard = ical.walk()[0]
        for key in vcard.keys():
            if key in ['BDAY', 'X-ANNIVERSARY', 'ANNIVERSARY'] or key.endswith('X-ABDATE'):
                date = vcard[key]
                uuid = vcard.get('UID')
                if isinstance(date, list):
                    logger.warning(
                        f'Vcard {href} in collection {calendar} has more than one '
                        f'{key}, will be skipped and not be available in khal.'
                    )
                    continue
                try:
                    if date[0:2] == '--' and date[3] != '-':
                        date = '1900' + date[2:]
                        orig_date = False
                    else:
                        orig_date = True
                    date = parser.parse(date).date()
                except ValueError:
                    logger.warning(
                        f'cannot parse {key} in {href} in collection {calendar}')
                    continue
                if 'FN' in vcard:
                    name = vcard['FN']
                else:
                    n = vcard['N'].split(';')
                    name = ' '.join([n[1], n[2], n[0]])
                vevent = icalendar.Event()
                vevent.add('dtstart', date)
                vevent.add('dtend', date + dt.timedelta(days=1))
                if date.month == 2 and date.day == 29:  # leap year
                    vevent.add('rrule', {'freq': 'YEARLY', 'BYYEARDAY': 60})
                else:
                    vevent.add('rrule', {'freq': 'YEARLY'})
                description = get_vcard_event_description(vcard, key)
                if orig_date:
                    if key == 'BDAY':
                        xtag = 'x-birthday'
                    elif key.endswith('ANNIVERSARY'):
                        xtag = 'x-anniversary'
                    else:
                        xtag = 'x-abdate'
                        vevent.add('x-ablabel', description)
                    vevent.add(xtag,
                               f'{date.year:04}{date.month:02}{date.day:02}')
                    vevent.add('x-fname', name)
                vevent.add('summary',
                           f'{name}\'s {description}')
                vevent.add('uid', href + key)
                vevent_str = vevent.to_ical().decode('utf-8')
                self._update_impl(vevent, href + key, calendar)
                sql_s = ('INSERT INTO events (item, etag, href, calendar)'
                         ' VALUES (?, ?, ?, ?);')
                stuple = (vevent_str, etag, href + key, calendar)
                try:
                    self.sql_ex(sql_s, stuple)
                except sqlite3.IntegrityError as error:
                    raise UpdateFailed('Database integrity error creating birthday event '
                                       f'on {date} for contact {name} (UID: {uuid}): '
                                       f'{error}')

    def _update_impl(self, vevent: icalendar.cal.Event, href: str, calendar: str) -> None:
        """insert `vevent` into the database

        expand `vevent`'s recurrence rules (if needed) and insert all instance
        in the respective tables
        than insert non-recurring and original recurring (those with an RRULE
        property) events into table `events`
        """
        # TODO FIXME this function is a steaming pile of shit
        rec_id = vevent.get(RECURRENCE_ID)
        if rec_id is None:
            rrange = None
        else:
            rrange = rec_id.params.get('RANGE')

        # testing on datetime.date won't work as datetime is a child of date
        if not isinstance(vevent['DTSTART'].dt, dt.datetime):
            dtype = EventType.DATE
        else:
            dtype = EventType.DATETIME
        if ('TZID' in vevent['DTSTART'].params and dtype == EventType.DATETIME) or \
                getattr(vevent['DTSTART'].dt, 'tzinfo', None):
            recs_table = 'recs_loc'
        else:
            recs_table = 'recs_float'

        thisandfuture = (rrange == THISANDFUTURE)
        if thisandfuture:
            start_shift, duration = calc_shift_deltas(vevent)
            start_shift_seconds = start_shift.days * 3600 * 24 + start_shift.seconds
            duration_seconds = duration.days * 3600 * 24 + duration.seconds

        dtstartend = expand_vevent(vevent, href)
        if not dtstartend:
            # Does this event even have dates? Technically it is possible for
            # events to be empty/non-existent by deleting all their recurrences
            # through EXDATE.
            return

        for dtstart, dtend in dtstartend:
            if dtype == EventType.DATE:
                dbstart = utils.to_unix_time(dtstart)
                dbend = utils.to_unix_time(dtend)
            else:
                dbstart = utils.to_unix_time(dtstart)
                dbend = utils.to_unix_time(dtend)

            if rec_id is not None:
                ref = rec_inst = str(utils.to_unix_time(rec_id.dt))
            else:
                rec_inst = str(dbstart)
                ref = PROTO

            if thisandfuture:
                recs_sql_s = (
                    f'UPDATE {recs_table} SET dtstart = rec_inst + ?, dtend = rec_inst + ?, '
                    'ref = ? WHERE rec_inst >= ? AND href = ? AND calendar = ?;')
                stuple_f = (
                    start_shift_seconds, start_shift_seconds + duration_seconds,
                    ref, rec_inst, href, calendar,
                )
                self.sql_ex(recs_sql_s, stuple_f)
            else:
                recs_sql_s = (
                    f'INSERT OR REPLACE INTO {recs_table} '
                    '(dtstart, dtend, href, ref, dtype, rec_inst, calendar)'
                    'VALUES (?, ?, ?, ?, ?, ?, ?);')
                stuple_n = (dbstart, dbend, href, ref, dtype, rec_inst, calendar)
                self.sql_ex(recs_sql_s, stuple_n)

    def get_ctag(self, calendar: str) -> Optional[str]:
        stuple = (calendar, )
        sql_s = 'SELECT ctag FROM calendars WHERE calendar = ?;'
        try:
            ctag = self.sql_ex(sql_s, stuple)[0][0]
            return ctag
        except IndexError:
            return None

    def set_ctag(self, ctag: str, calendar: str) -> None:
        stuple = (ctag, calendar, )
        sql_s = 'UPDATE calendars SET ctag = ? WHERE calendar = ?;'
        self.sql_ex(sql_s, stuple)
        self.conn.commit()

    def get_etag(self, href: str, calendar: str) -> Optional[str]:
        """get etag for href

        return: etag
        """
        sql_s = 'SELECT etag FROM events WHERE href = ? AND calendar = ?;'
        try:
            etag = self.sql_ex(sql_s, (href, calendar))[0][0]
            return etag
        except IndexError:
            return None

    def delete(self, href: str, etag: Any=None, calendar: str='') -> None:
        """
        removes the event from the db,

        :param etag: only there for compatibility with vdirsyncer's Storage,
                     we always delete
        """
        assert calendar != ''
        for table in ['recs_loc', 'recs_float']:
            sql_s = f'DELETE FROM {table} WHERE href = ? AND calendar = ?;'
            self.sql_ex(sql_s, (href, calendar))
        sql_s = 'DELETE FROM events WHERE href = ? AND calendar = ?;'
        self.sql_ex(sql_s, (href, calendar))

    def deletelike(self, href: str, etag: Any=None, calendar: str='') -> None:
        """
        removes events from the db that match an SQL 'like' statement,

        :param href: The pattern of hrefs to delete. May contain SQL wildcards
                     like '%'
        :param etag: only there for compatibility with vdirsyncer's Storage,
                     we always delete
        """
        assert calendar != ''
        for table in ['recs_loc', 'recs_float']:
            sql_s = f'DELETE FROM {table} WHERE href LIKE ? AND calendar = ?;'
            self.sql_ex(sql_s, (href, calendar))
        sql_s = 'DELETE FROM events WHERE href LIKE ? AND calendar = ?;'
        self.sql_ex(sql_s, (href, calendar))

    def list(self, calendar: str) -> list[tuple[str, str]]:
        """ list all events in `calendar`

        used for testing
        :returns: list of (href, etag)
        """
        sql_s = 'SELECT href, etag FROM events WHERE calendar = ?;'
        return list(set(self.sql_ex(sql_s, (calendar, ))))

    def get_localized_calendars(self, start: dt.datetime, end: dt.datetime) -> Iterable[str]:
        assert start.tzinfo is not None
        assert end.tzinfo is not None
        start_u = utils.to_unix_time(start)
        end_u = utils.to_unix_time(end)
        sql_s = (
            'SELECT events.calendar FROM '
            'recs_loc JOIN events ON '
            'recs_loc.href = events.href AND '
            'recs_loc.calendar = events.calendar WHERE '
            '(dtstart >= ? AND dtstart <= ? OR '
            'dtend > ? AND dtend <= ? OR '
            'dtstart <= ? AND dtend >= ?) AND events.calendar in ({0}) '
            'ORDER BY dtstart')
        stuple = tuple(
            [start_u, end_u, start_u, end_u, start_u, end_u] + list(self.calendars))  # type: ignore
        result = self.sql_ex(sql_s.format(','.join(["?"] * len(self.calendars))), stuple)
        for calendar in result:
            yield calendar[0]  # result is always an iterable, even if getting only one item

    def get_localized(self, start: dt.datetime, end: dt.datetime) -> Iterable[EventTuple]:
        assert start.tzinfo is not None
        assert end.tzinfo is not None
        start_timestamp = utils.to_unix_time(start)
        end_timestamp = utils.to_unix_time(end)
        sql_s = (
            'SELECT item, recs_loc.href, dtstart, dtend, ref, etag, dtype, events.calendar '
            'FROM recs_loc JOIN events ON '
            'recs_loc.href = events.href AND '
            'recs_loc.calendar = events.calendar WHERE '
            '(dtstart >= ? AND dtstart <= ? OR '
            'dtend > ? AND dtend <= ? OR '
            'dtstart <= ? AND dtend >= ?) AND '
            # insert as many "?" as we have configured calendars
            f'events.calendar in ({",".join("?" * len(self.calendars))}) '
            'ORDER BY dtstart')
        stuple = (
            start_timestamp,
            end_timestamp,
            start_timestamp,
            end_timestamp,
            start_timestamp,
            end_timestamp,
        ) + tuple(self.calendars)
        result = self.sql_ex(sql_s, stuple)
        for item, href, start_timestamp, end_timestamp, ref, etag, _dtype, calendar in result:
            start = pytz.UTC.localize(dt.datetime.utcfromtimestamp(start_timestamp))
            end = pytz.UTC.localize(dt.datetime.utcfromtimestamp(end_timestamp))
            yield item, href, start, end, ref, etag, calendar

    def get_floating_calendars(self, start: dt.datetime, end: dt.datetime) -> Iterable[str]:
        assert start.tzinfo is None
        assert end.tzinfo is None
        start_u = utils.to_unix_time(start)
        end_u = utils.to_unix_time(end)
        sql_s = (
            'SELECT events.calendar FROM '
            'recs_float JOIN events ON '
            'recs_float.href = events.href AND '
            'recs_float.calendar = events.calendar WHERE '
            '(dtstart >= ? AND dtstart < ? OR '
            'dtend > ? AND dtend <= ? OR '
            'dtstart <= ? AND dtend > ? ) AND events.calendar in ({0}) '
            'ORDER BY dtstart')
        stuple = tuple(
            [start_u, end_u, start_u, end_u, start_u, end_u] + list(self.calendars))  # type: ignore
        result = self.sql_ex(sql_s.format(','.join(["?"] * len(self.calendars))), stuple)
        for calendar in result:
            yield calendar[0]

    def get_floating(self, start: dt.datetime, end: dt.datetime) -> Iterable[EventTuple]:
        """return floating events between `start` and `end`"""
        assert start.tzinfo is None
        assert end.tzinfo is None
        start_dt: Union[dt.datetime, dt.date]
        end_dt: Union[dt.datetime, dt.date]

        start_u = utils.to_unix_time(start)
        end_u = utils.to_unix_time(end)
        sql_s = (
            'SELECT item, recs_float.href, dtstart, dtend, ref, etag, dtype, events.calendar '
            'FROM recs_float JOIN events ON '
            'recs_float.href = events.href AND '
            'recs_float.calendar = events.calendar WHERE '
            '(dtstart >= ? AND dtstart < ? OR '
            'dtend > ? AND dtend <= ? OR '
            'dtstart <= ? AND dtend > ? ) AND events.calendar in ({0}) '
            'ORDER BY dtstart')
        stuple = tuple(
            [start_u, end_u, start_u, end_u, start_u, end_u] + list(self.calendars))  # type: ignore
        result = self.sql_ex(sql_s.format(','.join(["?"] * len(self.calendars))), stuple)
        for item, href, start_s, end_s, ref, etag, dtype, calendar in result:
            start_dt = dt.datetime.utcfromtimestamp(start_s)
            end_dt = dt.datetime.utcfromtimestamp(end_s)
            if dtype == EventType.DATE:
                start_dt = start_dt.date()
                end_dt = end_dt.date()
            yield item, href, start_dt, end_dt, ref, etag, calendar

    def get(self, href: str, calendar: str) -> str:
        """returns the ical string matching href and calendar"""
        assert calendar is not None
        sql_s = 'SELECT item, etag FROM events WHERE href = ? AND calendar = ?;'
        item, etag = self.sql_ex(sql_s, (href, calendar))[0]
        return item

    def get_with_etag(self, href: str, calendar: str) -> tuple[str, str]:
        """returns the ical string and its etag matching href and calendar"""
        assert calendar is not None
        sql_s = 'SELECT item, etag FROM events WHERE href = ? AND calendar = ?;'
        item, etag = self.sql_ex(sql_s, (href, calendar))[0]
        return item, etag

    def search(self, search_string: str) \
            -> Iterable[tuple[str, str, dt.date, dt.date, str, str, str]]:
        """search for events matching `search_string`"""
        sql_s = (
            'SELECT item, recs_loc.href, dtstart, dtend, ref, etag, dtype, events.calendar '
            'FROM recs_loc JOIN events ON '
            'recs_loc.href = events.href AND '
            'recs_loc.calendar = events.calendar '
            'WHERE item LIKE (?) and events.calendar in ({0});'
        )
        stuple = tuple([f'%{search_string}%'] + list(self.calendars))
        result = self.sql_ex(sql_s.format(','.join(["?"] * len(self.calendars))), stuple)
        for item, href, start, end, ref, etag, dtype, calendar in result:
            start = pytz.UTC.localize(dt.datetime.utcfromtimestamp(start))
            end = pytz.UTC.localize(dt.datetime.utcfromtimestamp(end))
            if dtype == EventType.DATE:
                start = start.date()
                end = end.date()
            yield item, href, start, end, ref, etag, calendar

        sql_s = (
            'SELECT item, recs_float.href, dtstart, dtend, ref, etag, dtype, events.calendar '
            'FROM recs_float JOIN events ON '
            'recs_float.href = events.href AND '
            'recs_float.calendar = events.calendar '
            'WHERE item LIKE (?) and events.calendar in ({0});'
        )
        stuple = tuple([f'%{search_string}%'] + list(self.calendars))
        result = self.sql_ex(sql_s.format(','.join(["?"] * len(self.calendars))), stuple)
        for item, href, start, end, ref, etag, dtype, calendar in result:
            start = dt.datetime.utcfromtimestamp(start)
            end = dt.datetime.utcfromtimestamp(end)
            if dtype == EventType.DATE:
                start = start.date()
                end = end.date()
            yield item, href, start, end, ref, etag, calendar


def check_support(vevent: icalendar.cal.Event, href: str, calendar: str) -> None:
    """test if all icalendar features used in this event are supported,
    raise `UpdateFailed` otherwise.
    :param vevent: event to test
    :param href: href of this event, only used for logging
    """
    rec_id = vevent.get(RECURRENCE_ID)

    if rec_id is not None and rec_id.params.get('RANGE') == THISANDPRIOR:
        raise UpdateFailed(
            'The parameter `THISANDPRIOR` is not (and will not be) '
            'supported by khal (as applications supporting the latest '
            f'standard MUST NOT create those. Therefore event {href} from '
            f'calendar {calendar} will not be shown in khal'
        )
    rdate = vevent.get('RDATE')
    if rdate is not None and hasattr(rdate, 'params') and rdate.params.get('VALUE') == 'PERIOD':
        raise UpdateFailed(
            '`RDATE;VALUE=PERIOD` is currently not supported by khal. '
            f'Therefore event {href} from calendar {calendar} will not be shown in khal.\n'
            'Please post exemplary events (please remove any private data) '
            'to https://github.com/pimutils/khal/issues/152 .'
        )


def check_for_errors(component: icalendar.cal.Component, calendar: str, href: str) -> None:
    """checking if component.errors exists, is not empty and if so warn the user"""
    if hasattr(component, 'errors') and component.errors:
        logger.error(
            f'Errors occurred when parsing {calendar}/{href} for '
            'the following reasons:')
        for error in component.errors:
            logger.error(error)
        logger.error('This might lead to this event being shown wrongly or not at all.')


def calc_shift_deltas(vevent: icalendar.Event) -> tuple[dt.timedelta, dt.timedelta]:
    """calculate an event's duration and by how much its start time has shifted
    versus its recurrence-id time

    :param event: an event with a RECURRENCE-ID property
    """
    assert isinstance(vevent, icalendar.Event)  # REMOVE ME
    start_shift = vevent['DTSTART'].dt - vevent['RECURRENCE-ID'].dt
    try:
        duration = vevent['DTEND'].dt - vevent['DTSTART'].dt
    except KeyError:
        duration = vevent['DURATION'].dt
    return start_shift, duration


def get_vcard_event_description(vcard: icalendar.cal.Component, key: str) -> str:
    if key == 'BDAY':
        return 'birthday'
    elif key.endswith('ANNIVERSARY'):
        return 'anniversary'
    elif key.endswith('X-ABDATE'):
        desc_key = key[:-8] + 'X-ABLABEL'
        if desc_key in vcard.keys():
            return vcard[desc_key]
        else:
            desc_key = key[:-8] + 'X-ABLabel'
            if desc_key in vcard.keys():
                return vcard[desc_key]
            else:
                return 'custom event from vcard'
    else:
        return 'unknown event from vcard'
