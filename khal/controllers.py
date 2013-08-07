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
from khal import calendar_display
from itertools import izip_longest
import datetime
import time

class Controller(object):
    def __init__(self, conf):
        self.dbtool = backend.SQLiteDb(db_path=conf.sqlite.path,
                                       encoding="utf-8",
                                       errors="stricts",
                                       debug=conf.debug)

class Sync(Controller):
    def __init__(self, conf):
        super(Sync, self).__init__(conf)
        self.syncer = caldav.Syncer(conf.account.resource,
                             user=conf.account.user,
                             passwd=conf.account.passwd,
                             write_support=conf.account.write_support,
                             verify=conf.account.verify,
                             auth=conf.account.auth)
        # sync:
        vevents = self.syncer.get_all_vevents()
        self.dbtool.check_account_table(conf.account.name, conf.account.resource)
        for vevent in vevents:
            self.dbtool.update(vevent, conf.account.name)


class Display(Controller):
    def __init__(self, conf):
        super(Display, self).__init__(conf)

        today = datetime.date.today()
        start = datetime.datetime.combine(today, datetime.time.min)
        end = datetime.datetime.combine(today, datetime.time.max)

        event_column = list()
        event_column.append('Today:')
        for account in conf.sync.accounts:
            events = self.dbtool.get_time_range(start, end, account)
            for event in events:
                event_column.append(event.start.strftime('%H:%M') + '-' +  event.end.strftime('%H:%M') + ': ' + event.summary)

        calendar_column = calendar_display.vertical_month()
        rows = ['     '.join(one) for one in izip_longest(calendar_column, event_column, fillvalue='')]
        print '\n'.join(rows)



