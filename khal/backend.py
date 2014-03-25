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
The SQLite backend implementation.

Database Layout
===============

current version number: 1
tables: version, accounts, account_$ACCOUNTNAME

version:
    version (INT): only one line: current db version

account:
    account (TEXT): name of the account
    resource (TEXT)
    last_sync (TEXT)
    etag (TEX)

$ACCOUNTNAME_m:  # as in master
    href (TEXT)
    uid (TEXT)
    etag (TEXT)
    start (INT): start date of event (unix time)
    end (INT): start date of event (unix time)
    all_day (INT): 1 if event is 'all day event', 0 otherwise
    status (INT): status of this card, see below for meaning
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
import logging
from os import path
import sys
import sqlite3
import time

import dateutil.rrule
import icalendar
import pytz
import xdg.BaseDirectory

from .event import Event
from .status import OK, NEW, CHANGED, DELETED, NEWDELETE, CALCHANGED


# TODO fix that event/vevent mess


class UpdateFailed(Exception):
    """raised if update not possible"""
    pass


class SQLiteDb(object):
    """Querying the addressbook database

    the type() of parameters named "account" should be something like str()
    and of parameters named "accountS" should be an iterable like list()
    """

    def __init__(self, conf):

        db_path = conf.sqlite.path
        if db_path is None:
            db_path = xdg.BaseDirectory.save_data_path('khal') + '/khal.db'
        self.db_path = path.expanduser(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.debug = conf.debug
        self._create_default_tables()
        self._check_table_version()
        self.conf = conf
        self._accounts = []

    def __del__(self):
        self.conn.close()

    def _dump(self, account):
        """return table self.account, used for testing"""
        sql_s = 'SELECT * FROM {0}'.format(account + '_m')
        result = self.sql_ex(sql_s)
        return result

    def _check_table_version(self):
        """tests for curent db Version
        if the table is still empty, insert db_version
        """
        database_version = 1  # the current db VERSION
        self.cursor.execute('SELECT version FROM version')
        result = self.cursor.fetchone()
        if result is None:
            stuple = (database_version, )  # database version db Version
            self.cursor.execute('INSERT INTO version (version) VALUES (?)',
                                stuple)
            self.conn.commit()
        elif not result[0] == database_version:
            raise Exception(str(self.db_path) +
                            " is probably an invalid or outdated database.\n"
                            "You should consider to remove it and sync again.")

    def _create_default_tables(self):
        """creates version and account tables and inserts table version number
        """
        try:
            self.sql_ex('CREATE TABLE IF NOT EXISTS version (version INTEGER)')
            logging.debug("created version table")
        except Exception as error:
            sys.stderr.write('Failed to connect to database,'
                             'Unknown Error: ' + str(error) + "\n")
        self.conn.commit()

        try:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                account TEXT NOT NULL UNIQUE,
                resource TEXT NOT NULL,
                last_sync TEXT,
                ctag TEXT
                )''')
            logging.debug("created accounts table")
        except Exception as error:
            sys.stderr.write('Failed to connect to database,'
                             'Unknown Error: ' + str(error) + "\n")
        self.conn.commit()
        self._check_table_version()  # insert table version

    def _check_account(self, account):
        if account in self._accounts:
            return
        else:
            self.create_account_table(account)
            self._accounts.append(account)

    def sql_ex(self, statement, stuple='', commit=True):
        """wrapper for sql statements, does a "fetchall" """
        self.cursor.execute(statement, stuple)
        result = self.cursor.fetchall()
        if commit:
            self.conn.commit()
        return result

    def create_account_table(self, account):
        count_sql_s = """SELECT count(*) FROM accounts
                WHERE account = ? AND resource = ?"""
        stuple = (account,
                  self.conf.accounts[account].resource)
        self.cursor.execute(count_sql_s, stuple)
        result = self.cursor.fetchone()

        if(result[0] != 0):
            return
        sql_s = """CREATE TABLE IF NOT EXISTS {0} (
                href TEXT UNIQUE,
                etag TEXT,
                status INT NOT NULL,
                vevent TEXT
                )""".format(account + '_m')
        self.sql_ex(sql_s)
        sql_s = '''CREATE TABLE IF NOT EXISTS {0} (
            dtstart INT,
            dtend INT,
            href TEXT ); '''.format(account + '_dt')
        self.sql_ex(sql_s)
        sql_s = '''CREATE TABLE IF NOT EXISTS {0} (
            dtstart INT,
            dtend INT,
            href TEXT ); '''.format(account + '_d')
        self.sql_ex(sql_s)
        sql_s = 'INSERT INTO accounts (account, resource) VALUES (?, ?)'
        stuple = (account, self.conf.accounts[account].resource)
        self.sql_ex(sql_s, stuple)
        logging.debug("made sure tables for {0} exists".format(account))

    def needs_update(self, account, href_etag_list):
        """checks if we need to update this vcard
        :param account: account
        :param account: string
        :param href_etag_list: list of tuples of (hrefs and etags)
        :return: list of hrefs that need an update
        """
        self._check_account(account)
        needs_update = list()
        for href, etag in href_etag_list:
            stuple = (href,)
            sql_s = 'SELECT etag FROM {0} WHERE href = ?'.format(account + '_m')
            result = self.sql_ex(sql_s, stuple)
            if not result or etag != result[0][0]:
                needs_update.append(href)
        return needs_update

    def update(self, vevent, account, href='', etag='', status=OK):
        """insert a new or update an existing card in the db

        This is mostly a wrapper around two SQL statements, doing some cleanup
        before.

        :param vcard: vcard to be inserted or updated
        :type vcard: unicode
        :param href: href of the card on the server, if this href already
                     exists in the db the card gets updated. If no href is
                     given, a random href is chosen and it is implied that this
                     card does not yet exist on the server, but will be
                     uploaded there on next sync.
        :type href: str()
        :param etag: the etga of the vcard, if this etag does not match the
                     remote etag on next sync, this card will be updated from
                     the server. For locally created vcards this should not be
                     set
        :type etag: str()
        :param status: status of the vcard
                       * OK: card is in sync with remote server
                       * NEW: card is not yet on the server, this needs to be
                              set for locally created vcards
                       * CHANGED: card locally changed, will be updated on the
                                  server on next sync (if remote card has not
                                  changed since last sync)
                       * DELETED: card locally delete, will also be deleted on
                                  one the server on next sync (if remote card
                                  has not changed)
        :type status: one of backend.OK, backend.NEW, backend.CHANGED,
                      backend.DELETED


        """
        self._check_account(account)
        if not isinstance(vevent, icalendar.cal.Event):
            ical = icalendar.Event.from_ical(vevent)
            for component in ical.walk():
                if component.name == 'VEVENT':
                    vevent = component
        all_day_event = False
        if href == '' or href is None:
            href = get_random_href()
        if 'VALUE' in vevent['DTSTART'].params:
            if vevent['DTSTART'].params['VALUE'] == 'DATE':
                all_day_event = True

        dtstart = vevent['DTSTART'].dt

        if 'RRULE' in vevent.keys():
            rrulestr = vevent['RRULE'].to_ical()
            rrule = dateutil.rrule.rrulestr(rrulestr, dtstart=dtstart)
            today = datetime.datetime.today()
            if hasattr(dtstart, 'tzinfo') and dtstart.tzinfo is not None:
                # would be better to check if self is all day event
                today = self.conf.default.default_timezone.localize(today)
            if not set(['UNTIL', 'COUNT']).intersection(vevent['RRULE'].keys()):
                # rrule really doesn't like to calculate all recurrences until
                # eternity
                rrule._until = today + datetime.timedelta(days=15 * 365)
            logging.debug('calculating recurrence dates for {0}, '
                          'this might take some time.'.format(href))
            dtstartl = list(rrule)
            if len(dtstartl) == 0:
                raise UpdateFailed('Unsupported recursion rule for event '
                                   '{0}:\n{1}'.format(href, vevent.to_ical()))

            if 'DURATION' in vevent.keys():
                duration = vevent['DURATION'].dt
            else:
                duration = vevent['DTEND'].dt - vevent['DTSTART'].dt
            dtstartend = [(start, start + duration) for start in dtstartl]
        else:
            if 'DTEND' in vevent.keys():
                dtend = vevent['DTEND'].dt
            else:
                dtend = vevent['DTSTART'].dt + vevent['DURATION'].dt
            dtstartend = [(dtstart, dtend)]

        for dbname in [account + '_d', account + '_dt']:
            sql_s = ('DELETE FROM {0} WHERE href == ?'.format(dbname))
            self.sql_ex(sql_s, (href, ), commit=False)

        for dtstart, dtend in dtstartend:
            if all_day_event:
                dbstart = dtstart.strftime('%Y%m%d')
                dbend = dtend.strftime('%Y%m%d')
                dbname = account + '_d'
            else:
                # TODO: extract strange (aka non Olson) TZs from params['TZID']
                # perhaps better done in event/vevent
                if dtstart.tzinfo is None:
                    dtstart = self.conf.default.default_timezone.localize(dtstart)
                if dtend.tzinfo is None:
                    dtend = self.conf.default.default_timezone.localize(dtend)

                dtstart_utc = dtstart.astimezone(pytz.UTC)
                dtend_utc = dtend.astimezone(pytz.UTC)
                dbstart = calendar.timegm(dtstart_utc.timetuple())
                dbend = calendar.timegm(dtend_utc.timetuple())
                dbname = account + '_dt'

            sql_s = ('INSERT INTO {0} '
                     '(dtstart, dtend, href) '
                     'VALUES (?, ?, ?);'.format(dbname))
            stuple = (dbstart,
                      dbend,
                      href)
            self.sql_ex(sql_s, stuple, commit=False)

        sql_s = ('INSERT OR REPLACE INTO {0} '
                 '(status, vevent, etag, href) '
                 'VALUES (?, ?, ?, '
                 'COALESCE((SELECT href FROM {0} WHERE href = ?), ?)'
                 ');'.format(account + '_m'))

        stuple = (status,
                  vevent.to_ical().decode('utf-8'),
                  etag,
                  href,
                  href)
        self.sql_ex(sql_s, stuple, commit=False)
        self.conn.commit()

    def update_href(self, oldhref, newhref, account, etag='', status=OK):
        """updates old_href to new_href, can also alter etag and status,
        see update() for an explanation of these parameters"""
        self._check_account(account)
        stuple = (newhref, etag, status, oldhref)
        sql_s = 'UPDATE {0} SET href = ?, etag = ?, status = ? \
             WHERE href = ?;'.format(account + '_m')
        self.sql_ex(sql_s, stuple)
        for dbname in [account + '_d', account + '_dt']:
            sql_s = 'UPDATE {0} SET href = ? WHERE href = ?;'.format(dbname)
            self.sql_ex(sql_s, (newhref, oldhref))

    def href_exists(self, href, account):
        """returns True if href already exists in db

        :param href: href
        :type href: str()
        :returns: True or False
        """
        self._check_account(account)
        sql_s = 'SELECT href FROM {0} WHERE href = ?;'.format(account)
        if len(self.sql_ex(sql_s, (href, ))) == 0:
            return False
        else:
            return True

    def get_etag(self, href, account):
        """get etag for href

        type href: str()
        return: etag
        rtype: str()
        """
        self._check_account(account)
        sql_s = 'SELECT etag FROM {0} WHERE href=(?);'.format(account + '_m')
        etag = self.sql_ex(sql_s, (href,))[0][0]
        return etag

    def delete(self, href, account):
        """
        removes the event from the db,
        returns nothing
        """
        self._check_account(account)
        for dbname in [account + '_d', account + '_dt', account + '_m']:
            sql_s = 'DELETE FROM {0} WHERE href = ? ;'.format(dbname)
            self.sql_ex(sql_s, (href, ))

    def get_all_href_from_db(self, accounts):
        """returns a list with all hrefs
        """
        result = list()
        for account in accounts:
            self._check_account(account)
            hrefs = self.sql_ex('SELECT href FROM {0}'.format(account + '_m'))
            result = result + [(href[0], account) for href in hrefs]
        return result

    def get_all_href_from_db_not_new(self, accounts):
        """returns list of all not new hrefs"""
        result = list()
        for account in accounts:
            self._check_account(account)
            sql_s = 'SELECT href FROM {0} WHERE status != (?)'.format(account + '_m')
            stuple = (NEW,)
            hrefs = self.sql_ex(sql_s, stuple)
            result = result + [(href[0], account) for href in hrefs]
        return result

    def get_time_range(self, start, end, account, color='', readonly=False,
                       unicode_symbols=True, show_deleted=True):
        """returns
        :type start: datetime.datetime
        :type end: datetime.datetime
        :param deleted: include deleted events in returned lsit
        """
        self._check_account(account)
        start = time.mktime(start.timetuple())
        end = time.mktime(end.timetuple())
        sql_s = ('SELECT href, dtstart, dtend FROM {0} WHERE '
                 'dtstart >= ? AND dtstart <= ? OR '
                 'dtend >= ? AND dtend <= ? OR '
                 'dtstart <= ? AND dtend >= ?').format(account + '_dt')
        stuple = (start, end, start, end, start, end)
        result = self.sql_ex(sql_s, stuple)
        event_list = list()
        for href, start, end in result:
            start = pytz.UTC.localize(datetime.datetime.utcfromtimestamp(start))
            end = pytz.UTC.localize(datetime.datetime.utcfromtimestamp(end))
            event = self.get_vevent_from_db(href, account,
                                            start=start, end=end,
                                            color=color,
                                            readonly=readonly,
                                            unicode_symbols=unicode_symbols)
            if show_deleted or event.status not in [DELETED, CALCHANGED, NEWDELETE]:
                event_list.append(event)

        return event_list

    def get_allday_range(self, start, end=None, account=None,
                         color='', readonly=False, unicode_symbols=True, show_deleted=True):
        self._check_account(account)
        if account is None:
            raise Exception('need to specify an account')
        strstart = start.strftime('%Y%m%d')
        if end is None:
            end = start + datetime.timedelta(days=1)
        strend = end.strftime('%Y%m%d')
        sql_s = ('SELECT href, dtstart, dtend FROM {0} WHERE '
                 'dtstart >= ? AND dtstart < ? OR '
                 'dtend > ? AND dtend <= ? OR '
                 'dtstart <= ? AND dtend > ? ').format(account + '_d')
        stuple = (strstart, strend, strstart, strend, strstart, strend)
        result = self.sql_ex(sql_s, stuple)
        event_list = list()
        for href, start, end in result:
            start = time.strptime(str(start), '%Y%m%d')
            end = time.strptime(str(end), '%Y%m%d')
            start = datetime.date(start.tm_year, start.tm_mon, start.tm_mday)
            end = datetime.date(end.tm_year, end.tm_mon, end.tm_mday)
            vevent = self.get_vevent_from_db(href, account,
                                             start=start, end=end,
                                             color=color,
                                             readonly=readonly,
                                             unicode_symbols=unicode_symbols)
            if show_deleted or vevent.status not in [DELETED, CALCHANGED, NEWDELETE]:
                event_list.append(vevent)
        return event_list

    def hrefs_by_time_range_datetime(self, start, end, account, color=''):
        """returns
        :type start: datetime.datetime
        :type end: datetime.datetime
        """
        self._check_account(account)
        start = time.mktime(start.timetuple())
        end = time.mktime(end.timetuple())
        sql_s = ('SELECT href FROM {0} WHERE '
                 'dtstart >= ? AND dtstart <= ? OR '
                 'dtend >= ? AND dtend <= ? OR '
                 'dtstart <= ? AND dtend >= ?').format(account + '_dt')
        stuple = (start, end, start, end, start, end)
        result = self.sql_ex(sql_s, stuple)
        return [one[0] for one in result]

    def hrefs_by_time_range_date(self, start, end=None, account=None):
        self._check_account(account)
        if account is None:
            raise Exception('need to specify an account')
        strstart = start.strftime('%Y%m%d')
        if end is None:
            end = start + datetime.timedelta(days=1)
        strend = end.strftime('%Y%m%d')
        sql_s = ('SELECT href FROM {0} WHERE '
                 'dtstart >= ? AND dtstart < ? OR '
                 'dtend > ? AND dtend <= ? OR '
                 'dtstart <= ? AND dtend > ? ').format(account + '_d')
        stuple = (strstart, strend, strstart, strend, strstart, strend)
        result = self.sql_ex(sql_s, stuple)
        return [one[0] for one in result]

    def hrefs_by_time_range(self, start, end, account):
        return list(set(self.hrefs_by_time_range_date(start, end, account) +
                    self.hrefs_by_time_range_datetime(start, end, account)))

    def get_vevent_from_db(self, href, account, start=None, end=None,
                           readonly=False, color=lambda x: x,
                           unicode_symbols=True):
        """returns the Event matching href, if start and end are given, a
        specific Event from a Recursion set is returned, the Event as saved in
        the db

        All other parameters given to this function are handed over to the
        Event.
        """
        self._check_account(account)
        sql_s = 'SELECT vevent, status, etag FROM {0} WHERE href=(?)'.format(account + '_m')
        result = self.sql_ex(sql_s, (href, ))
        return Event(result[0][0],
                     local_tz=self.conf.default.local_timezone,
                     default_tz=self.conf.default.default_timezone,
                     start=start,
                     end=end,
                     color=color,
                     href=href,
                     account=account,
                     status=result[0][1],
                     readonly=readonly,
                     etag=result[0][2],
                     unicode_symbols=unicode_symbols)

    def get_changed(self, account):
        """returns list of hrefs of locally edited vevents
        """
        self._check_account(account)
        sql_s = 'SELECT href FROM {0} WHERE status == (?)'.format(account + '_m')
        result = self.sql_ex(sql_s, (CHANGED, ))
        return [row[0] for row in result]

    def get_new(self, account):
        """returns list of hrefs of locally added vcards
        """
        self._check_account(account)
        sql_s = 'SELECT href FROM {0} WHERE status == (?)'.format(account + '_m')
        result = self.sql_ex(sql_s, (NEW, ))
        return [row[0] for row in result]

    def get_marked_delete(self, account):
        """returns list of tuples (hrefs, etags) of locally deleted vcards
        """
        self._check_account(account)
        sql_s = ('SELECT href, etag FROM {0} WHERE status == '
                 '(?)'.format(account + '_m'))
        result = self.sql_ex(sql_s, (DELETED, ))
        return result

    def mark_delete(self, href, account):
        """marks the entry as to be deleted on server on next sync
        """
        self._check_account(account)
        sql_s = 'UPDATE {0} SET STATUS = ? WHERE href = ?'.format(account + '_m')
        self.sql_ex(sql_s, (DELETED, href, ))

    def set_status(self, href, status, account):
        """sets the status of vcard
        """
        self._check_account(account)
        sql_s = 'UPDATE {0} SET STATUS = ? WHERE href = ?'.format(account + '_m')
        self.sql_ex(sql_s, (status, href, ))

    def reset_flag(self, href, account):
        """
        resets the status for a given href to 0 (=not edited locally)
        """
        self._check_account(account)
        sql_s = 'UPDATE {0} SET status = ? WHERE href = ?'.format(account + '_m')
        self.sql_ex(sql_s, (OK, href, ))

    def get_status(self, href, account):
        """
        gets the status of the event associated with href in `account`
        """
        self._check_account(account)
        sql_s = 'SELECT status FROM {0} WHERE href = (?)'.format(account + '_m')
        return self.sql_ex(sql_s, (href, ))[0][0]


def get_random_href():
    """returns a random href
    """
    import random
    tmp_list = list()
    for _ in xrange(3):
        rand_number = random.randint(0, 0x100000000)
        tmp_list.append("{0:x}".format(rand_number))
    return "-".join(tmp_list).upper()
