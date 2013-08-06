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

account_$ACCOUNTNAME:
    href (TEXT)
    uid (TEXT)
    etag (TEXT)
    start (INT): start date of event (unix time)
    end (INT): start date of event (unix time)
    all_day (INT): 1 if event is 'all day event', 0 otherwise
    status (INT): status of this card, see below for meaning
    vevent (TEXT): the actual vcard

"""

from __future__ import print_function

try:
    import xdg.BaseDirectory
    import sys
    import sqlite3
    import logging
    import pytz
    import time
    from os import path

except ImportError, error:
    print(error)
    sys.exit(1)

default_time_zone = 'Europe/Berlin'

OK = 0  # not touched since last sync
NEW = 1  # new card, needs to be created on the server
CHANGED = 2  # properties edited or added (news to be pushed to server)
DELETED = 9  # marked for deletion (needs to be deleted on server)


class SQLiteDb(object):
    """Querying the addressbook database

    the type() of parameters named "account" should be something like str()
    and of parameters named "accountS" should be an iterable like list()
    """

    def __init__(self,
                 db_path=None,
                 encoding="utf-8",
                 errors="strict",
                 debug=False):
        if db_path is None:
            db_path = xdg.BaseDirectory.save_data_path('pycard') + 'abook.db'
        self.db_path = path.expanduser(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.encoding = encoding
        self.errors = errors
        self.debug = debug
        self._create_default_tables()
        self._check_table_version()

    def __del__(self):
        self.conn.close()

    def search(self, search_string, accounts):
        """returns list of ids from db matching search_string"""
        stuple = ('%' + search_string + '%', )
        result = list()
        for account in accounts:
            sql_s = 'SELECT href FROM {0} WHERE vcard LIKE (?)'.format(account)
            hrefs = self.sql_ex(sql_s, stuple)
            result = result + ([(href[0], account) for href in hrefs])
        return result

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
            self.cursor.execute('INSERT INTO version (version) VALUES (?)', stuple)
            self.conn.commit()
        elif not result[0] == database_version:
            raise Exception(str(self.db_path) +
                            " is probably an invalid or outdated database.\n"
                            "You should consider to remove it and sync again.")

    def _create_default_tables(self):
        """creates version and account tables and instert table version number
        """
        try:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS version ( version INTEGER )''')
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

    def sql_ex(self, statement, stuple=''):
        """wrapper for sql statements, does a "fetchall" """
        self.cursor.execute(statement, stuple)
        result = self.cursor.fetchall()
        self.conn.commit()
        return result

    def check_account_table(self, account_name, resource):
        sql_s = """CREATE TABLE IF NOT EXISTS {0} (
                uid TEXT NOT NULL UNIQUE,
                href TEXT,
                etag TEXT,
                start INT,
                end INT,
                status INT NOT NULL,
                vevent TEXT
                )""".format(account_name)
        self.sql_ex(sql_s)
        sql_s = 'INSERT INTO accounts (account, resource) VALUES (?, ?)'
        self.sql_ex(sql_s, (account_name, resource))
        logging.debug("created {0} table".format(account_name))

    def needs_update(self, href, account_name, etag=''):
        """checks if we need to update this vcard

        :param href: href of vcard
        :type href: str()
        :param etag: etag of vcard
        :type etag: str()
        :return: True or False
        """
        stuple = (href,)
        sql_s = 'SELECT etag FROM {0} WHERE href = ?'.format(account_name)
        result = self.sql_ex(sql_s, stuple)
        if len(result) is 0:
            return True
        elif etag != result[0][0]:
            return True
        else:
            return False

    def update(self, vevent, account_name, href='', etag='', status=OK):
        """insert a new or update an existing card in the db

        :param vcard: vcard to be inserted or updated
        :type vcard: icalendar.cal.Event or unicode() (an actual vcard)
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
                      BACKEND.DELETED

        """
        all_day_event = False
        try:
            if (vevent['DTSTART'].params['VALUE'] == 'DATE'):
                all_day_event = True
        except KeyError:
            pass
        if not all_day_event:

            def fix_timezone(identifier):
                dtstart = vevent[identifier]
                if dtstart.dt.tzinfo is None:
                    # in case timezone information looks like this:
                    # /freeassociation.sourceforge.net/Tzfile/Europe/Amsterdam
                    try:
                        timezone = '/'.join(dtstart.params['TZID'].split('/')[-2:])
                    except KeyError:
                        timezone = default_time_zone
                    timezone = pytz.timezone(timezone)
                    dtstart.dt = timezone.localize(dtstart.dt)
                return dtstart.dt.astimezone(pytz.UTC)

            try:
                dtstart_utc = fix_timezone('DTSTART')
                cstart = int(time.mktime(dtstart_utc.timetuple()))
                try:
                    dtend_utc = fix_timezone('DTEND')
                except KeyError:
                    dtend_utc = dtstart_utc + vevent['DURATION'].dt
                cend = int(time.mktime(dtend_utc.timetuple()))
            except:
                print(vevent.to_ical())
                import ipdb; ipdb.set_trace()


            sql_s = ('INSERT INTO {0} '
                     '(uid, start, end, status, vevent) '
                     'VALUES (?, ?, ?, ?, ?);'.format(account_name))
            stuple = (str(vevent['UID']), cstart, cend, 0, vevent.to_ical().decode('utf-8'))
            self.sql_ex(sql_s, stuple)





    def update_href(self, old_href, new_href, account_name, etag='', status=OK):
        """updates old_href to new_href, can also alter etag and status,
        see update() for an explanation of these parameters"""
        stuple = (new_href, etag, status, old_href)
        sql_s = 'UPDATE {0} SET href = ?, etag = ?, status = ? \
             WHERE href = ?;'.format(account_name)
        self.sql_ex(sql_s, stuple)

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
        self.sql_ex('DELETE FROM {0} WHERE href=(?)'.format(account_name), stuple)

    def get_all_href_from_db(self, accounts):
        """returns a list with all hrefs
        """
        result = list()
        for account in accounts:
            hrefs = self.sql_ex('SELECT href FROM {0} ORDER BY fname COLLATE NOCASE'.format(account))
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

#    def get_names_href_from_db(self, searchstring=None):
#        """
#        :return: list of tuples(name, href) of all entries from the db
#        """
#        if searchstring is None:
#            return self.sql_ex('SELECT fname, href FROM {0} '
#                               'ORDER BY name'.format(self.account))
#        else:
#            hrefs = self.search(searchstring)
#            temp = list()
#            for href in hrefs:
#                try:
#                    sql_s = 'SELECT fname, href FROM {0} WHERE href =(?)'.format(self.account)
#                    result = self.sql_ex(sql_s, (href, ))
#                    temp.append(result[0])
#                except IndexError as error:
#                    print(href)
#                    print(error)
#            return temp

    def get_vcard_from_db(self, href, account_name):
        """returns a VCard()
        """
        sql_s = 'SELECT vcard FROM {0} WHERE href=(?)'.format(account_name)
        result = self.sql_ex(sql_s, (href, ))
        vcard = model.vcard_from_string(result[0][0])
        vcard.href = href
        vcard.account = account_name
        return vcard

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
        sql_s = 'SELECT href, etag FROM {0} WHERE status == (?)'.format(account_name)
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
