#!/usr/bin/env python2
# coding: utf-8
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
syncs the remote database to the local db
"""

from khal import backend
from khal import caldav


def sync(conf):
    """this should probably be seperated from the class definitions"""

    syncer = caldav.Syncer(conf.account.resource,
                           user=conf.account.user,
                           passwd=conf.account.passwd,
                           write_support=conf.account.write_support,
                           verify=conf.account.verify,
                           auth=conf.account.auth)
    my_dbtool = backend.SQLiteDb(db_path=conf.sqlite.path,
                                 encoding="utf-8",
                                 errors="stricts",
                                 debug=conf.debug)
    # sync:
    vevents = syncer.get_all_vevents()

    my_dbtool.check_account_table(conf.account.name, conf.account.resource)

    for vevent in vevents:
        my_dbtool.update(vevent, conf.account.name)
