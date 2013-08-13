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

import datetime
import logging

from khal import backend
from khal import caldav
from khal import calendar_display
from itertools import izip_longest


class Controller(object):
    def __init__(self, conf):
        self.dbtool = backend.SQLiteDb(conf)


class Sync(Controller):
    def __init__(self, conf, sync_account_name):
        """
        :param sync_account_name: name of account which should be synced
        """
        super(Sync, self).__init__(conf)
        sync_account = conf.accounts[sync_account_name]
        self.syncer = caldav.Syncer(sync_account.resource,
                                    user=sync_account.user,
                                    passwd=sync_account.passwd,
                                    write_support=sync_account.write_support,
                                    verify=sync_account.verify,
                                    auth=sync_account.auth)
        # sync:
        logging.debug('syncing events in the next 365 days')
        href_etag_list = self.syncer.get_hel()
        need_update = self.dbtool.needs_update(sync_account_name,
                                               href_etag_list)
        logging.debug('{number} events need an update'.format(number=len(need_update)))
        vhe_list = self.syncer.get_vevents(need_update)

        for vevent, href, etag in vhe_list:
            self.dbtool.update(vevent, sync_account.name, href=href, etag=etag)


class Display(Controller):
    def __init__(self, conf):
        super(Display, self).__init__(conf)

        today = datetime.date.today()
        start = datetime.datetime.combine(today, datetime.time.min)
        end = datetime.datetime.combine(today, datetime.time.max)

        event_column = list()
        event_column.append('Today:')
        all_day_events = list()
        events = list()
        for account in conf.sync.accounts:
            all_day_events += self.dbtool.get_allday_range(today,
                                                           account_name=account)
            events += self.dbtool.get_time_range(start, end, account)
        for event in all_day_events:
            event_column.append(event.summary)
        for event in events:
            event_column.append(event.start.strftime('%H:%M') + '-' +  event.end.strftime('%H:%M') + ': ' + event.summary)


        calendar_column = calendar_display.vertical_month()
        rows = ['     '.join(one) for one in izip_longest(calendar_column, event_column, fillvalue='')]
        print '\n'.join(rows)



class NewFromString(Controller):
    def __init__(self, conf):
        super(NewFromString, self).__init__(conf)
        date_list = conf.new
        timeformat = '%H:%M'
        dateformat = '%d.%m.'
        datetimeformat = '%d.%m. %H:%M'
        DEFAULTTZ = 'Europe/Berlin'
        event = aux.construct_event(date_list,
                                    timeformat,
                                    dateformat,
                                    datetimeformat,
                                    DEFAULTTZ)
        self.dbtool.update(event,  conf.sync.accounts.pop(), status=backend.NEW, )



class Interactive(Controller):
    def __init__(self, conf):
        import ui
        super(Interactive, self).__init__(conf)
        ui.interactive(conf=conf, dbtool=self.dbtool)
