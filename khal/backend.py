#!/usr/bin/env python2
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2013 Christian Geier & contributors
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

current version number: 9
tables: version, accounts, account_$ACCOUNTNAME

version:
    version (INT): only one line: current db version

account:
    account (TEXT): name of the account
    resource (TEXT)
    last_sync (TEXT)
    etag (TEX)

$ACCOUNTNAME:
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

try:
    import datetime
    import icalendar
    import xdg.BaseDirectory
    import sys
    import sqlite3
    import logging
    import pytz
    import time
    from os import path
    import dateutil.rrule
    from model import Event

except ImportError, error:
    print(error)
    sys.exit(1)

default_time_zone = 'Europe/Berlin'
DEFAULTTZ = 'Europe/Berlin'

OK = 0  # not touched since last sync
NEW = 1  # new card, needs to be created on the server
CHANGED = 2  # properties edited or added (news to be pushed to server)
DELETED = 9  # marked for deletion (needs to be deleted on server)


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
            db_path = xdg.BaseDirectory.save_data_path('pycard') + 'abook.db'
        self.db_path = path.expanduser(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.debug = conf.debug
        self._create_default_tables()
        self._check_table_version()
        self.conf = conf

        for account in self.conf.sync.accounts:
            self.check_account_table(account,
                                     self.conf.accounts[account].resource)

    def __del__(self):
        self.conn.close()

    def _dump(self, account_name):
        """return table self.account, used for testing"""
        sql_s = 'SELECT * FROM {0}'.format(account_name)
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
        """creates version and account tables and instert table version number
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
                account TEXT NOT NULL,
                resource TEXT NOT NULL,
                last_sync TEXT,
                etag TEXT
                )''')
            logging.debug("created accounts table")
        except Exception as error:
            sys.stderr.write('Failed to connect to database,'
                             'Unknown Error: ' + str(error) + "\n")
        self.conn.commit()
        self._check_table_version()  # insert table version

    def sql_ex(self, statement, stuple='', commit=True):
        """wrapper for sql statements, does a "fetchall" """
        self.cursor.execute(statement, stuple)
        result = self.cursor.fetchall()
        if commit:
            self.conn.commit()
        return result

    def check_account_table(self, account_name, resource):

        sql_s = """CREATE TABLE IF NOT EXISTS {0} (
                href TEXT,
                etag TEXT,
                status INT NOT NULL,
                vevent TEXT
                )""".format(account_name)
        self.sql_ex(sql_s)
        sql_s = '''CREATE TABLE IF NOT EXISTS {0} (
            dtstart INT,
            dtend INT,
            href TEXT ); '''.format(account_name + '_dt')
        self.sql_ex(sql_s)
        sql_s = '''CREATE TABLE IF NOT EXISTS {0} (
            dtstart INT,
            dtend INT,
            href TEXT ); '''.format(account_name + '_d')
        self.sql_ex(sql_s)
        sql_s = 'INSERT INTO accounts (account, resource) VALUES (?, ?)'
        self.sql_ex(sql_s, (account_name, resource))
        logging.debug("created {0} table".format(account_name))

    def needs_update(self, account_name, href_etag_list):
        """checks if we need to update this vcard
        :param account_name: account_name
        :param account_name: string
        :param href_etag_list: list of tuples of (hrefs and etags)
        :return: list of hrefs that need an update
        """
        needs_update = list()
        for href, etag in href_etag_list:
            stuple = (href,)
            sql_s = 'SELECT etag FROM {0} WHERE href = ?'.format(account_name)
            result = self.sql_ex(sql_s, stuple)
            if not result or etag != result[0][0]:
                needs_update.append(href)
        return needs_update

    def update(self, vevent, account_name, href='', etag='', status=OK):
        """insert a new or update an existing card in the db

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
        if not isinstance(vevent, icalendar.cal.Event):
            calendar = icalendar.Event.from_ical(vevent)
            for component in calendar.walk():
                if component.name == 'VEVENT':
                    vevent = component
        all_day_event = False
        if href is '':
            href = get_random_href()
        if 'VALUE' in vevent['DTSTART'].params:
            if vevent['DTSTART'].params['VALUE'] == 'DATE':
                all_day_event = True

        sql_s = ('INSERT OR REPLACE INTO {0} '
                 '(status, vevent, etag, href) '
                 'VALUES (?, ?, ?, '
                 'COALESCE((SELECT href FROM {0} WHERE href = ?), ?)'
                 ');'.format(account_name))

        stuple = (status,
                  vevent.to_ical().decode('utf-8'),
                  etag,
                  href,
                  href)
        self.sql_ex(sql_s, stuple, commit=False)

        dtstart = vevent['DTSTART'].dt
        if 'RRULE' in vevent.keys():
            rrulestr = vevent['RRULE'].to_ical()
            rrule = dateutil.rrule.rrulestr(rrulestr, dtstart=dtstart)
            rrule._until = (datetime.datetime.today() +
                            datetime.timedelta(days=15 * 265))
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
        for dbname in [account_name + '_d', account_name + '_dt']:
            sql_s = ('DELETE FROM {0} WHERE href == ?'.format(dbname))
            self.sql_ex(sql_s, (href, ), commit=False)
        for dtstart, dtend in dtstartend:
            if all_day_event:
                dbstart = dtstart.strftime('%Y%m%d')
                dbend = dtend.strftime('%Y%m%d')
                dbname = account_name + '_d'
            else:
                # TODO: extract stange (aka non Olson) TZs from params['TZID']
                # perhaps better done in model/vevent
                if dtstart.tzinfo is None:
                    dtstart = pytz.timezone(DEFAULTTZ).localize(dtstart)
                if dtend.tzinfo is None:
                    dtend = pytz.timezone(DEFAULTTZ).localize(dtend)

                dtstart_utc = dtstart.astimezone(pytz.UTC)
                dtend_utc = dtend.astimezone(pytz.UTC)

                dbstart = int(time.mktime(dtstart_utc.timetuple()))
                dbend = int(time.mktime(dtend_utc.timetuple()))
                dbname = account_name + '_dt'

            sql_s = ('INSERT INTO {0} '
                     '(dtstart, dtend, href) '
                     'VALUES (?, ?, ?);'.format(dbname))
            stuple = (dbstart,
                      dbend,
                      href)
            self.sql_ex(sql_s, stuple, commit=False)
        self.conn.commit()

    def update_href(self, oldhref, newhref, account_name, etag='', status=OK):
        """updates old_href to new_href, can also alter etag and status,
        see update() for an explanation of these parameters"""
        stuple = (newhref, etag, status, oldhref)
        sql_s = 'UPDATE {0} SET href = ?, etag = ?, status = ? \
             WHERE href = ?;'.format(account_name)
        self.sql_ex(sql_s, stuple)
        for dbname in [account_name + '_d', account_name + '_dt']:
            sql_s = 'UPDATE {0} SET href = ? WHERE href = ?;'.format(dbname)
            self.sql_ex(sql_s, (newhref, oldhref))

    def href_exists(self, href, account_name):
        """returns True if href already exist in db

        :param href: href
        :type href: str()
        :returns: True or False
        """
        sql_s = 'SELECT href FROM {0} WHERE href = ?;'.format(account_name)
        if len(self.sql_ex(sql_s, (href, ))) == 0:
            return False
        else:
            return True

    def get_etag(self, href, account_name):
        """get etag for href

        type href: str()
        return: etag
        rtype: str()
        """
        sql_s = 'SELECT etag FROM {0} WHERE href=(?);'.format(account_name)
        etag = self.sql_ex(sql_s, (href,))[0][0]
        return etag

    def delete_vcard_from_db(self, href, account_name):
        """
        removes the whole vcard,
        returns nothing
        """
        stuple = (href, )
        logging.debug("locally deleting " + str(href))
        self.sql_ex('DELETE FROM {0} WHERE href=(?)'.format(account_name),
                    stuple)

    def get_all_href_from_db(self, accounts):
        """returns a list with all hrefs
        """
        result = list()
        for account in accounts:
            hrefs = self.sql_ex('SELECT href FROM {0} ORDER BY fname '
                                'COLLATE NOCASE'.format(account))
            result = result + [(href[0], account) for href in hrefs]
        return result

    def get_all_href_from_db_not_new(self, accounts):
        """returns list of all not new hrefs"""
        result = list()
        for account in accounts:
            sql_s = 'SELECT href FROM {0} WHERE status != (?)'.format(account)
            stuple = (NEW,)
            hrefs = self.sql_ex(sql_s, stuple)
            result = result + [(href[0], account) for href in hrefs]
        return result

    def get_time_range(self, start, end, account_name):
        """returns
        :type start: datetime.datetime
        :type end: datetime.datetime
        """
        start = time.mktime(start.timetuple())
        end = time.mktime(end.timetuple())
        sql_s = ('SELECT href, dtstart, dtend FROM {0} WHERE '
                 'dtstart >= ? AND dtstart <= ? OR '
                 'dtend >= ? AND dtend <= ? OR '
                 'dtstart <= ? AND dtend >= ?').format(account_name + '_dt')
        stuple = (start, end, start, end, start, end)
        result = self.sql_ex(sql_s, stuple)
        event_list = list()
        for href, dtstart, dtend in result:
            vevent = self.get_vevent_from_db(href, account_name)
            event_list.append(Event(vevent))

        return event_list

    def get_allday_range(self, start, end=None, account_name=None):
        if account_name is None:
            raise Exception('need to specify an account_name')
        strstart = start.strftime('%Y%m%d')
        if end is None:
            end = start + datetime.timedelta(days=1)
        strend = end.strftime('%Y%m%d')
        sql_s = ('SELECT href, dtstart, dtend FROM {0} WHERE '
                 'dtstart >= ? AND dtstart < ? OR '
                 'dtend > ? AND dtend <= ? OR '
                 'dtstart <= ? AND dtend > ? ').format(account_name + '_d')
        stuple = (strstart, strend, strstart, strend, strstart, strend)
        result = self.sql_ex(sql_s, stuple)
        event_list = list()
        for href, dtstart, dtend in result:
            vevent = self.get_vevent_from_db(href, account_name)
            event_list.append(Event(vevent))
        return event_list

    def get_vevent_from_db(self, href, account_name):
        """returns a VCard()
        """
        sql_s = 'SELECT vevent FROM {0} WHERE href=(?)'.format(account_name)
        result = self.sql_ex(sql_s, (href, ))
        return result[0][0]

    def get_changed(self, account_name):
        """returns list of hrefs of locally edited vcards
        """
        sql_s = 'SELECT href FROM {0} WHERE status == (?)'.format(account_name)
        result = self.sql_ex(sql_s, (CHANGED, ))
        return [row[0] for row in result]

    def get_new(self, account_name):
        """returns list of hrefs of locally added vcards
        """
        sql_s = 'SELECT href FROM {0} WHERE status == (?)'.format(account_name)
        result = self.sql_ex(sql_s, (NEW, ))
        return [row[0] for row in result]

    def get_marked_delete(self, account_name):
        """returns list of tuples (hrefs, etags) of locally deleted vcards
        """
        sql_s = ('SELECT href, etag FROM {0} WHERE status == '
                 '(?)'.format(account_name))
        result = self.sql_ex(sql_s, (DELETED, ))
        return result

    def mark_delete(self, href, account_name):
        """marks the entry as to be deleted on server on next sync
        """
        sql_s = 'UPDATE {0} SET STATUS = ? WHERE href = ?'.format(account_name)
        self.sql_ex(sql_s, (DELETED, href, ))

    def reset_flag(self, href, account_name):
        """
        resets the status for a given href to 0 (=not edited locally)
        """
        sql_s = 'UPDATE {0} SET status = ? WHERE href = ?'.format(account_name)
        self.sql_ex(sql_s, (OK, href, ))


def get_random_href():
    """returns a random href
    """
    import random
    tmp_list = list()
    for _ in xrange(3):
        rand_number = random.randint(0, 0x100000000)
        tmp_list.append("{0:x}".format(rand_number))
    return "-".join(tmp_list).upper()
