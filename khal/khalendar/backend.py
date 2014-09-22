# vim: set ts=4 sw=4 expandtab sts=4 fileencoding=utf-8:
# Copyright (c) 2013-2014 Christian Geier et al.
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

Database Layout
===============

current version number: 2
tables: version, accounts, account_$ACCOUNTNAME

version:
    version (INT): only one line: current db version

account:
    account (TEXT): name of the account
    resource (TEXT)
    ctag (TEX): *collection* tag, used to check if this account has been changed
               this last usage

$ACCOUNTNAME_m:  # as in master
    href (TEXT)
    etag (TEXT)
    vevent (TEXT): the actual vcard

$ACCOUNTNAME_d: #all day events
    # keeps start and end dates of all events, incl. recurrent dates
    dtstart (INT)
    dtend (INT)
    href (TEXT)

$ACCOUNTNAME_dt: #other events, same as above
    dtstart (INT)
    dtend (INT)
    href (TEXT)

"""

from __future__ import print_function

import calendar
import datetime
from os import makedirs, path
import sqlite3
import time

import icalendar
import pytz
import xdg.BaseDirectory

from .event import Event
from . import datetimehelper
from .. import log
from ..exceptions import Error
from .exceptions import UnsupportedRruleExceptionError, CouldNotCreateDbDir, \
    UpdateFailed

logger = log.logger

DB_VERSION = 2  # The current db layout version

# TODO fix that event/vevent mess


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
    :param local_tz: the local time zone
    :type local_tz: pytz.timezone
    :param default_tz: the default time zone
    :type default_tz: pytz.timezone
    """

    def __init__(self, calendar, db_path, local_tz, default_tz, color):
        if db_path is None:
            db_path = xdg.BaseDirectory.save_data_path('khal') + '/khal.db'
        self.db_path = path.expanduser(db_path)
        self.calendar = calendar
        self._create_dbdir()
        self.local_tz = local_tz
        self.default_tz = default_tz
        self.color = color
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._create_default_tables()
        self._check_table_version()
        self.create_account_table()

    def _create_dbdir(self):
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
                logger.fatal('failed to create {0}: {1}'.format(dbdir, error))
                raise CouldNotCreateDbDir()

    def _check_table_version(self):
        """tests for curent db Version
        if the table is still empty, insert db_version
        """
        self.cursor.execute('SELECT version FROM version')
        result = self.cursor.fetchone()
        if result is None:
            self.cursor.execute('INSERT INTO version (version) VALUES (?)',
                                (DB_VERSION, ))
            self.conn.commit()
        elif not result[0] == DB_VERSION:
            raise Exception(str(self.db_path) +
                            " is probably an invalid or outdated database.\n"
                            "You should consider to remove it and sync again.")

    def _create_default_tables(self):
        """creates version and account tables and inserts table version number
        """
        try:
            self.sql_ex('CREATE TABLE IF NOT EXISTS version (version INTEGER)')
            logger.debug("created version table")
        except Exception as error:
            logger.fatal('Failed to connect to database,'
                         'Unknown Error: {}'.format(error))
            raise
        self.conn.commit()

        try:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                account TEXT NOT NULL UNIQUE,
                resource TEXT NOT NULL,
                ctag FLOAT
                )''')
            logger.debug("created accounts table")
        except Exception as error:
            logger.fatal('Failed to connect to database,'
                         'Unknown Error: {}'.format(error))
            raise
        self.conn.commit()
        self._check_table_version()  # insert table version

    def sql_ex(self, statement, stuple='', commit=True):
        """wrapper for sql statements, does a "fetchall" """
        self.cursor.execute(statement, stuple)
        result = self.cursor.fetchall()
        if commit:
            self.conn.commit()
        return result

    def create_account_table(self):
        count_sql_s = """SELECT count(*) FROM accounts
                WHERE account = ? AND resource = ?"""
        stuple = (self.calendar, '')
        self.cursor.execute(count_sql_s, stuple)
        result = self.cursor.fetchone()

        if(result[0] != 0):
            logger.debug("tables for calendar {0} exist".format(self.calendar))
            return
        sql_s = """CREATE TABLE IF NOT EXISTS {0} (
                href TEXT UNIQUE,
                etag TEXT,
                vevent TEXT
                )""".format(self.calendar + '_m')
        self.sql_ex(sql_s)
        sql_s = '''CREATE TABLE IF NOT EXISTS {0} (
            dtstart INT,
            dtend INT,
            href TEXT ); '''.format(self.calendar + '_dt')
        self.sql_ex(sql_s)
        sql_s = '''CREATE TABLE IF NOT EXISTS {0} (
            dtstart INT,
            dtend INT,
            href TEXT ); '''.format(self.calendar + '_d')
        self.sql_ex(sql_s)
        sql_s = 'INSERT INTO accounts (account, resource) VALUES (?, ?)'
        stuple = (self.calendar, '')
        self.sql_ex(sql_s, stuple)
        logger.debug("created table for calendar {0}".format(self.calendar))

    def update(self, vevent, href, etag=''):
        """insert a new or update an existing card in the db

        This is mostly a wrapper around two SQL statements, doing some cleanup
        before.

        :param vevent: event to be inserted or updated. If this is a calendar
                       object, it will be searched for an event.
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
            raise ValueError('href may not be one')
        events = []
        if not isinstance(vevent, icalendar.cal.Event):
            ical = icalendar.Event.from_ical(vevent)
            for component in ical.walk():
                if component.name == 'VEVENT':
                    events.append(component)

        if len(events) == 0:
            logger.debug(u'Could not find event in {}'.format(ical))
            raise UpdateFailed(u'Could not find event in {}'.format(ical))

        elif len(events) > 1:
            if len(set([event['UID'] for event in events])):
                raise UnsupportedRruleExceptionError()
            else:
                raise Error('more than one event in .ics file')

        vevent = events[0]
        vevent = datetimehelper.sanitize(vevent)

        all_day_event = False

        # testing on datetime.date won't work as datetime is a child of date
        if not isinstance(vevent['DTSTART'].dt, datetime.datetime):
            all_day_event = True

        dtstartend = datetimehelper.expand(vevent,
                                           self.default_tz,
                                           href)

        for dbname in [self.calendar + '_d', self.calendar + '_dt']:
            sql_s = ('DELETE FROM {0} WHERE href == ?'.format(dbname))
            self.sql_ex(sql_s, (href, ), commit=False)

        for dtstart, dtend in dtstartend:
            if all_day_event:
                dbstart = dtstart.strftime('%Y%m%d')
                dbend = dtend.strftime('%Y%m%d')
                dbname = self.calendar + '_d'
            else:
                # TODO: extract strange (aka non Olson) TZs from params['TZID']
                # perhaps better done in event/vevent
                if dtstart.tzinfo is None:
                    dtstart = self.default_tz.localize(dtstart)
                if dtend.tzinfo is None:
                    dtend = self.default_tz.localize(dtend)

                dtstart_utc = dtstart.astimezone(pytz.UTC)
                dtend_utc = dtend.astimezone(pytz.UTC)
                dbstart = calendar.timegm(dtstart_utc.timetuple())
                dbend = calendar.timegm(dtend_utc.timetuple())
                dbname = self.calendar + '_dt'

            sql_s = ('INSERT INTO {0} '
                     '(dtstart, dtend, href) '
                     'VALUES (?, ?, ?);'.format(dbname))
            stuple = (dbstart,
                      dbend,
                      href)
            self.sql_ex(sql_s, stuple, commit=False)

        sql_s = ('INSERT OR REPLACE INTO {0} '
                 '(vevent, etag, href) '
                 'VALUES (?, ?, '
                 'COALESCE((SELECT href FROM {0} WHERE href = ?), ?)'
                 ');'.format(self.calendar + '_m'))

        stuple = (vevent.to_ical().decode('utf-8'),
                  etag,
                  href,
                  href)
        self.sql_ex(sql_s, stuple, commit=False)
        self.conn.commit()

    def get_ctag(self):
        stuple = (self.calendar, )
        sql_s = 'SELECT ctag FROM accounts WHERE account = ?'
        try:
            ctag = self.sql_ex(sql_s, stuple)[0][0]
            return ctag
        except IndexError:
            return None

    def set_ctag(self, ctag):
        stuple = (ctag, self.calendar, )
        sql_s = 'UPDATE accounts SET ctag = ? WHERE account = ?'
        self.sql_ex(sql_s, stuple)
        self.conn.commit()

    def get_etag(self, href):
        """get etag for href

        type href: str()
        return: etag
        rtype: str()
        """
        sql_s = ('SELECT etag FROM {0} WHERE href=(?);'
                 .format(self.calendar + '_m'))
        try:
            etag = self.sql_ex(sql_s, (href,))[0][0]
            return etag
        except IndexError:
            return None

    def delete(self, href, etag=None):
        """
        removes the event from the db,
        returns nothing
        :param etag: only there for compatiblity with vdirsyncer's Storage,
                     we always delete
        """
        for dbname in [self.calendar + '_d',
                       self.calendar + '_dt',
                       self.calendar + '_m']:
            sql_s = 'DELETE FROM {0} WHERE href = ? ;'.format(dbname)
            self.sql_ex(sql_s, (href, ))

    def list(self):
        """
        :returns: list of (href, etag)
        """
        return self.sql_ex('SELECT href, etag FROM {0}_m'
                           .format(self.calendar))

    def get_time_range(self, start, end, show_deleted=True):
        """returns
        :type start: datetime.datetime
        :type end: datetime.datetime
        :param show_deleted: include deleted events in returned lsit
        """
        start = time.mktime(start.timetuple())
        end = time.mktime(end.timetuple())
        sql_s = ('SELECT href, dtstart, dtend FROM {0} WHERE '
                 'dtstart >= ? AND dtstart <= ? OR '
                 'dtend >= ? AND dtend <= ? OR '
                 'dtstart <= ? AND dtend >= ?').format(self.calendar + '_dt')
        stuple = (start, end, start, end, start, end)
        result = self.sql_ex(sql_s, stuple)
        event_list = list()
        for href, start, end in result:
            start = pytz.UTC.localize(
                datetime.datetime.utcfromtimestamp(start))
            end = pytz.UTC.localize(datetime.datetime.utcfromtimestamp(end))
            event = self.get(href, start=start, end=end, color=self.color)
            event_list.append(event)
        return event_list

    def get_allday_range(self, start, end=None, show_deleted=True):
        # TODO type check on start and end
        # should be datetime.date not datetime.datetime
        strstart = start.strftime('%Y%m%d')
        if end is None:
            end = start + datetime.timedelta(days=1)
        strend = end.strftime('%Y%m%d')
        sql_s = ('SELECT href, dtstart, dtend FROM {0} WHERE '
                 'dtstart >= ? AND dtstart < ? OR '
                 'dtend > ? AND dtend <= ? OR '
                 'dtstart <= ? AND dtend > ? ').format(self.calendar + '_d')
        stuple = (strstart, strend, strstart, strend, strstart, strend)
        result = self.sql_ex(sql_s, stuple)
        event_list = list()
        for href, start, end in result:
            start = time.strptime(str(start), '%Y%m%d')
            end = time.strptime(str(end), '%Y%m%d')
            start = datetime.date(start.tm_year, start.tm_mon, start.tm_mday)
            end = datetime.date(end.tm_year, end.tm_mon, end.tm_mday)
            event = self.get(href, start=start, end=end, color=self.color)
            event_list.append(event)
        return event_list

    def get(self, href, start=None, end=None, color=None):
        """returns the Event matching href, if start and end are given, a
        specific Event from a Recursion set is returned, otherwise the Event
        returned exactly as saved in the db
        """
        sql_s = 'SELECT vevent, etag FROM {0} WHERE href=(?)'.format(
            self.calendar + '_m')
        result = self.sql_ex(sql_s, (href, ))
        return Event(result[0][0],
                     local_tz=self.local_tz,
                     default_tz=self.default_tz,
                     start=start,
                     end=end,
                     href=href,
                     calendar=self.calendar,
                     etag=result[0][1],
                     color=self.color,
                     )
