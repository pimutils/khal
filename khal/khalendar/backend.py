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
The SQLite backend implementation.

note on naming:
  * every variable name vevent should be of type icalendar.Event
  * every variable named event should be of type khal.khalendar.Events
  * variables named vevents/events (plural) should be iterables of their
    respective types

"""
import contextlib
from datetime import datetime, timedelta
from os import makedirs, path
import sqlite3

from dateutil import parser
import icalendar
import pytz
import xdg.BaseDirectory

from .event import Event
from . import aux
from .. import log
from .exceptions import CouldNotCreateDbDir, OutdatedDbVersionError, UpdateFailed

logger = log.logger

DB_VERSION = 4  # The current db layout version

RECURRENCE_ID = 'RECURRENCE-ID'
THISANDFUTURE = 'THISANDFUTURE'
THISANDPRIOR = 'THISANDPRIOR'

DATE = 0
DATETIME = 1

PROTO = 'PROTO'


def sort_key(vevent):
    # insert the (sub) events in the right order, e.g. recurrence-id events
    # after the corresponding rrule event
    assert isinstance(vevent, icalendar.Event)  # REMOVE ME
    uid = str(vevent['UID'])
    rec_id = vevent.get(RECURRENCE_ID)
    if rec_id is None:
        return uid, 0
    rrange = rec_id.params.get('RANGE')
    if rrange == THISANDFUTURE:
        return uid, aux.to_unix_time(rec_id.dt)
    else:
        return uid, 1


class SQLiteDb(object):
    """
    This class should provide a caching database for a calendar, keeping raw
    vevents in one table but allowing to retrieve events by dates (via the help
    of some auxiliary tables)

    :param calendar: the `name` of this calendar, if the same *name* and
                     *dbpath* is given on next creation of an SQLiteDb object
                     the same tables will be used
    :type calendar: str
    :param db_path: path where this sqlite database will be saved, if this is
                    None, a place according to the XDG specifications will be
                    chosen
    :type db_path: str or None
    """

    def __init__(self, calendar, db_path, locale):
        if db_path is None:
            db_path = xdg.BaseDirectory.save_data_path(u'khal') + u'/khal.db'
        self.db_path = path.expanduser(db_path)
        self.calendar = calendar
        self._create_dbdir()
        self.locale = locale
        self._at_once = False
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._create_default_tables()
        self._check_table_version()
        self._check_calendar_exists()

    @contextlib.contextmanager
    def at_once(self):
        assert not self._at_once
        self._at_once = True
        try:
            yield self
        except:
            raise
        else:
            self.conn.commit()
        finally:
            self._at_once = False

    def _create_dbdir(self):
        """create the dbdir if it doesn't exist"""
        if self.db_path == ':memory:':
            return None
        dbdir = self.db_path.rsplit(u'/', 1)[0]
        if not path.isdir(dbdir):
            try:
                logger.debug(u'trying to create the directory for the db')
                makedirs(dbdir, mode=0o770)
                logger.debug(u'success')
            except OSError as error:
                logger.fatal(u'failed to create {0}: {1}'.format(dbdir, error))
                raise CouldNotCreateDbDir()

    def _check_table_version(self):
        """tests for curent db Version
        if the table is still empty, insert db_version
        """
        self.cursor.execute(u'SELECT version FROM version')
        result = self.cursor.fetchone()
        if result is None:
            self.cursor.execute(u'INSERT INTO version (version) VALUES (?)',
                                (DB_VERSION, ))
            self.conn.commit()
        elif not result[0] == DB_VERSION:
            raise OutdatedDbVersionError(
                str(self.db_path) +
                " is probably an invalid or outdated database.\n"
                "You should consider removing it and running khal again.")

    def _create_default_tables(self):
        """creates version and calendar tables and inserts table version number
        """
        self.cursor.execute(u'CREATE TABLE IF NOT EXISTS '
                            u'version (version INTEGER)')
        logger.debug(u"created version table")

        self.cursor.execute(u'''CREATE TABLE IF NOT EXISTS calendars (
            calendar TEXT NOT NULL UNIQUE,
            resource TEXT NOT NULL,
            ctag FLOAT
            )''')
        self.cursor.execute(u'''CREATE TABLE IF NOT EXISTS events (
                href TEXT NOT NULL,
                calendar TEXT NOT NULL,
                sequence INT,
                etag TEXT,
                item TEXT,
                primary key (href, calendar)
                );''')
        self.cursor.execute(u'''CREATE TABLE IF NOT EXISTS recs_loc (
            dtstart INT NOT NULL,
            dtend INT NOT NULL,
            href TEXT NOT NULL REFERENCES events( href ),
            rec_inst TEXT NOT NULL,
            ref TEXT NOT NULL,
            dtype INT NOT NULL,
            calendar TEXT NOT NULL,
            primary key (href, rec_inst, calendar)
            );''')
        self.cursor.execute(u'''CREATE TABLE IF NOT EXISTS recs_float (
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

    def _check_calendar_exists(self):
        """make sure an entry for the current calendar exists in `calendar`
        table
        """
        self.cursor.execute(u'''SELECT count(*) FROM calendars
                WHERE calendar = ?;''', (self.calendar,))
        result = self.cursor.fetchone()

        if result[0] != 0:
            logger.debug(u"tables for calendar {0} exist".format(self.calendar))
        else:
            sql_s = u'INSERT INTO calendars (calendar, resource) VALUES (?, ?);'
            stuple = (self.calendar, u'')
            self.sql_ex(sql_s, stuple)

    def sql_ex(self, statement, stuple=u''):
        """wrapper for sql statements, does a "fetchall" """
        self.cursor.execute(statement, stuple)
        result = self.cursor.fetchall()
        if not self._at_once:
            self.conn.commit()
        return result

    def update(self, vevent_str, href, etag=u''):
        """insert a new or update an existing card in the db

        This is mostly a wrapper around two SQL statements, doing some cleanup
        before.

        :param vevent_str: event to be inserted or updated.
                           We assume that even if it contains more than one
                           VEVENT, that they are all part of the same event and
                           all have the same UID
        :type vevent: unicode
        :param href: href of the card on the server, if this href already
                     exists in the db the card gets updated. If no href is
                     given, a random href is chosen and it is implied that this
                     card does not yet exist on the server, but will be
                     uploaded there on next sync.
        :type href: str()
        :param etag: the etag of the vcard, if this etag does not match the
                     remote etag on next sync, this card will be updated from
                     the server. For locally created vcards this should not be
                     set
        :type etag: str()
        """
        if href is None:
            raise ValueError(u'href may not be None')
        ical = icalendar.Event.from_ical(vevent_str)

        vevents = (aux.sanitize(c, self.locale['default_timezone'], href, self.calendar) for
                   c in ical.walk() if c.name == u'VEVENT')
        # Need to delete the whole event in case we are updating a
        # recurring event with an event which is either not recurring any
        # more or has EXDATEs, as those would be left in the recursion
        # tables. There are obviously better ways to achieve the same
        # result.
        self.delete(href)
        for vevent in sorted(vevents, key=sort_key):
            check_support(vevent, href, self.calendar)
            self._update_impl(vevent, href, self.calendar)

        sql_s = (u'INSERT INTO events '
                 u'(item, etag, href, calendar) '
                 u'VALUES (?, ?, ?, ?);')
        stuple = (vevent_str, etag, href, self.calendar)
        self.sql_ex(sql_s, stuple)

    def _update_impl(self, vevent, href, calendar):
        """insert `vevent` into the database

        expand `vevent`'s reccurence rules (if needed) and insert all instance
        in the respective tables
        than insert non-reccuring and original recurring (those with an RRULE
        property) events into table `events`
        """
        # TODO FIXME this function is a steaming pile of shit
        rec_id = vevent.get(RECURRENCE_ID)
        if rec_id is None:
            rrange = None
        else:
            rrange = rec_id.params.get('RANGE')

        # testing on datetime.date won't work as datetime is a child of date
        if not isinstance(vevent['DTSTART'].dt, datetime):
            dtype = DATE
        else:
            dtype = DATETIME
        if ('TZID' in vevent['DTSTART'].params and dtype == DATETIME) or \
                getattr(vevent['DTSTART'].dt, 'tzinfo', None):
            recs_table = u'recs_loc'
        else:
            recs_table = u'recs_float'

        thisandfuture = (rrange == THISANDFUTURE)
        if thisandfuture:
            start_shift, duration = calc_shift_deltas(vevent)
            start_shift = start_shift.days * 3600 * 24 + start_shift.seconds
            duration = duration.days * 3600 * 24 + duration.seconds

        dtstartend = aux.expand(vevent, href)
        if not dtstartend:
            # Does this event even have dates? Technically it is possible for
            # events to be empty/non-existent by deleting all their recurrences
            # through EXDATE.
            return

        for dtstart, dtend in dtstartend:
            if dtype == DATE:
                dbstart = aux.to_unix_time(dtstart)
                dbend = aux.to_unix_time(dtend)
                if rec_id is not None:
                    rec_inst = aux.to_unix_time(rec_id.dt)
                    ref = rec_inst
                else:
                    rec_inst = dbstart
                    ref = PROTO
            else:
                dbstart = aux.to_unix_time(dtstart)
                dbend = aux.to_unix_time(dtend)

                if rec_id is not None:
                    ref = rec_inst = str(aux.to_unix_time(rec_id.dt))
                else:
                    rec_inst = dbstart
                    ref = PROTO

            if thisandfuture:
                recs_sql_s = (
                    u'UPDATE {0} SET dtstart = rec_inst + ?, dtend = rec_inst + ?, ref = ? '
                    u'WHERE rec_inst >= ? AND href = ? AND calendar = ?;'.format(recs_table))
                stuple = (start_shift, start_shift + duration, ref, rec_inst, href, calendar)
            else:
                recs_sql_s = (
                    u'INSERT OR REPLACE INTO {0} '
                    u'(dtstart, dtend, href, ref, dtype, rec_inst, calendar)'
                    u'VALUES (?, ?, ?, ?, ?, ?, ?);'.format(recs_table))
                stuple = (dbstart, dbend, href, ref, dtype, rec_inst, self.calendar)
            self.sql_ex(recs_sql_s, stuple)
            # end of loop

    def get_ctag(self):
        stuple = (self.calendar, )
        sql_s = u'SELECT ctag FROM calendars WHERE calendar = ?;'
        try:
            ctag = self.sql_ex(sql_s, stuple)[0][0]
            return ctag
        except IndexError:
            return None

    def set_ctag(self, ctag):
        stuple = (ctag, self.calendar, )
        sql_s = u'UPDATE calendars SET ctag = ? WHERE calendar = ?;'
        self.sql_ex(sql_s, stuple)
        self.conn.commit()

    def get_etag(self, href):
        """get etag for href

        type href: str()
        return: etag
        rtype: str()
        """
        sql_s = u'SELECT etag FROM events WHERE href = ? AND calendar = ?;'
        try:
            etag = self.sql_ex(sql_s, (href, self.calendar))[0][0]
            return etag
        except IndexError:
            return None

    def delete(self, href, etag=None):
        """
        removes the event from the db,

        :param etag: only there for compatiblity with vdirsyncer's Storage,
                     we always delete
        :returns: None
        """
        for table in [u'recs_loc', u'recs_float']:
            sql_s = u'DELETE FROM {0} WHERE href = ? AND calendar = ?;'.format(table)
            self.sql_ex(sql_s, (href, self.calendar))
        sql_s = u'DELETE FROM events WHERE href = ? AND calendar = ?;'
        self.sql_ex(sql_s, (href, self.calendar))

    def list(self):
        """
        :returns: list of (href, etag)
        """
        sql_s = u'SELECT href, etag FROM events WHERE calendar = ?;'
        return list(set(self.sql_ex(sql_s, (self.calendar, ))))

    def get_time_range(self, start, end):
        """returns
        :type start: datetime.datetime
        :type end: datetime.datetime
        """
        # XXX rename get_localized_range()
        if start.tzinfo is None:
            start = self.locale['local_timezone'].localize(start)
        if end.tzinfo is None:
            end = self.locale['local_timezone'].localize(end)
        start = aux.to_unix_time(start)
        end = aux.to_unix_time(end)
        sql_s = (u'SELECT recs_loc.href, dtstart, dtend, ref, dtype FROM '
                 u'recs_loc JOIN events ON '
                 u'recs_loc.href = events.href AND '
                 u'recs_loc.calendar = events.calendar WHERE '
                 u'(dtstart >= ? AND dtstart <= ? OR '
                 u'dtend >= ? AND dtend <= ? OR '
                 u'dtstart <= ? AND dtend >= ?) AND events.calendar = ?;')
        stuple = (start, end, start, end, start, end, self.calendar)
        result = self.sql_ex(sql_s, stuple)
        for href, start, end, ref, dtype in result:
            start = pytz.UTC.localize(datetime.utcfromtimestamp(start))
            end = pytz.UTC.localize(datetime.utcfromtimestamp(end))
            event = self.get(href, start=start, end=end, ref=ref, dtype=dtype)
            yield event

    def get_allday_range(self, start):
        """
        get all allday events scheduled for day `start`

        :type start: datetime.date
        :type end: datetime.date
        """
        # XXX rename get_float_range()
        strstart = aux.to_unix_time(start)
        strend = aux.to_unix_time(start + timedelta(days=1))
        sql_s = (u'SELECT recs_float.href, dtstart, dtend, ref, dtype FROM '
                 u'recs_float JOIN events ON '
                 u'recs_float.href = events.href AND '
                 u'recs_float.calendar = events.calendar WHERE '
                 u'(dtstart >= ? AND dtstart < ? OR '
                 u'dtend > ? AND dtend <= ? OR '
                 u'dtstart <= ? AND dtend > ? ) AND events.calendar = ?;')
        stuple = (strstart, strend, strstart, strend, strstart, strend, self.calendar)
        result = self.sql_ex(sql_s, stuple)
        for href, start, end, ref, dtype in result:
            start = datetime.utcfromtimestamp(start)
            end = datetime.utcfromtimestamp(end)
            event = self.get(href, start=start, end=end, ref=ref, dtype=dtype)
            yield event

    def get_datetime_at(self, dtime):
        """return datetime events which are scheduled at `dtime`

        :param dtime: if dtime is not localized it is treated as if it were
             in UTC
        :type dtime: datetime.datetime
        """
        dtime = aux.to_unix_time(dtime)
        sql_s = (u'SELECT recs_loc.href, dtstart, dtend, ref, dtype FROM '
                 u'recs_loc JOIN events ON '
                 u'recs_loc.href = events.href AND '
                 u'recs_loc.calendar = events.calendar WHERE '
                 u'(dtstart <= ? AND dtend >= ? ) '
                 u'AND events.calendar = ?;')
        stuple = (dtime, dtime, self.calendar)
        result = self.sql_ex(sql_s, stuple)
        for href, start, end, ref, dtype in result:
            start = pytz.UTC.localize(datetime.utcfromtimestamp(start))
            end = pytz.UTC.localize(datetime.utcfromtimestamp(end))
            event = self.get(href, start=start, end=end, ref=ref, dtype=dtype)
            yield event

    def get_allday_at(self, dtime):
        """return allday events which are scheduled at `dtime`

        :type start: datetime.date
        :type end: datetime.date
        """
        if isinstance(dtime, datetime):
            dtime = dtime.date()
        dtime = aux.to_unix_time(dtime)
        sql_s = (u'SELECT recs_float.href, dtstart, dtend, ref, dtype FROM '
                 u'recs_float JOIN events ON '
                 u'recs_float.href = events.href AND '
                 u'recs_float.calendar = events.calendar WHERE '
                 u'(dtstart <= ? AND dtend >= ? )'
                 u'AND events.calendar = ?;')
        stuple = (dtime, dtime, self.calendar)
        result = self.sql_ex(sql_s, stuple)
        for href, start, end, ref, dtype in result:
            start = datetime.utcfromtimestamp(start)
            end = datetime.utcfromtimestamp(end)
            event = self.get(href, start=start, end=end, ref=ref, dtype=dtype)
            yield event

    def get(self, href, start=None, end=None, ref=None, dtype=None):
        """returns the Event matching href

        if start and end are given, a specific Event from a Recursion set is
        returned, otherwise the Event returned exactly as saved in the db
        """
        sql_s = u'SELECT href, etag, item FROM events WHERE href = ? AND calendar = ?;'
        result = self.sql_ex(sql_s, (href, self.calendar))
        href, etag, item = result[0]
        if dtype == DATE:
            start = start.date()
            end = end.date()
        return Event.fromString(item,
                                locale=self.locale,
                                href=href,
                                calendar=self.calendar,
                                etag=etag,
                                start=start,
                                end=end,
                                ref=ref,
                                )

    def search(self, search_string):
        """search for events matching `search_string`"""
        sql_s = (u'SELECT href FROM events '
                 u'WHERE item LIKE (?) and calendar = (?)')
        stuple = (u'%' + search_string + u'%', self.calendar)
        result = self.sql_ex(sql_s, stuple)
        for href, in result:
            event = self.get(href)
            yield event


def check_support(vevent, href, calendar):
    """test if all icalendar features used in this event are supported,
    raise `UpdateFailed` otherwise.
    :param vevent: event to test
    :type vevent: icalendar.cal.Event
    :param href: href of this event, only used for logging
    :type href: str
    """
    rec_id = vevent.get(RECURRENCE_ID)
    if rec_id is not None and rec_id.params.get('RANGE') == THISANDPRIOR:
        raise UpdateFailed(
            u'The parameter `THISANDPRIOR` is not (and will not be) '
            u'supported by khal (as applications supporting the latest '
            u'standard MUST NOT create those. Therefore event {} from '
            u'calendar {} will not be shown in khal'
            .format(href, calendar)
        )
    rdate = vevent.get('RDATE')
    if rdate is not None and hasattr(rdate, 'params') and rdate.params.get('VALUE') == 'PERIOD':
        raise UpdateFailed(
            u'`RDATE;VALUE=PERIOD` is currently not supported by khal. '
            u'Therefore event {} from calendar {} will not be shown in khal.\n'
            u'Please post exemplary events (please remove any private data) '
            u'to https://github.com/geier/khal/issues/152 .'
            .format(href, calendar)
        )


class SQLiteDb_Birthdays(SQLiteDb):
    def update(self, vevent, href, etag=''):
        if href is None:
            raise ValueError(u'href may not be None')
        ical = icalendar.Event.from_ical(vevent)
        vcard = ical.walk()[0]
        if 'BDAY' in vcard.keys():
            bday = vcard['BDAY']
            try:
                if bday[0:2] == u'--' and bday[3] != u'-':
                    bday = '1900' + bday[2:]
                bday = parser.parse(bday).date()
            except ValueError:
                logger.info(u'cannot parse BIRTHDAY in {} in collection '
                            u'{}'.format(href, self.calendar))
                return
            name = vcard['FN']
            event = icalendar.Event()
            event.add('dtstart', bday)
            event.add('dtend', bday + timedelta(days=1))
            event.add('summary', u'{}\'s birthday'.format(name))
            event.add('rrule', {'freq': 'YEARLY'})
            event.add('uid', href)
            event_str = event.to_ical().decode('utf-8')
            self._update_impl(event, href, self.calendar)
            sql_s = (u'INSERT INTO events (item, etag, href, calendar) VALUES (?, ?, ?, ?);')
            stuple = (event_str, etag, href, self.calendar)
            self.sql_ex(sql_s, stuple)


def calc_shift_deltas(vevent):
    """calculate an events duration and by how much its start time has shifted
    versus its recurrence-id time

    :param event: an event with an RECURRENCE-ID property
    :type event: icalendar.Event
    :returns: time shift and duration
    :rtype: (datetime.timedelta, datetime.timedelta)
    """
    assert isinstance(vevent, icalendar.Event)  # REMOVE ME
    start_shift = vevent['DTSTART'].dt - vevent['RECURRENCE-ID'].dt
    try:
        duration = vevent['DTEND'].dt - vevent['DTSTART'].dt
    except KeyError:
        duration = vevent['DURATION'].dt
    return start_shift, duration
