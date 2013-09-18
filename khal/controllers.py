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

import logging
import datetime
import pytz

from khal import aux
from khal import backend
from khal import caldav
from khal import calendar_display
from khal.aux import bstring
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
        self.dbtool.check_account_table(sync_account_name)
        # syncing remote to local:
        logging.debug('syncing events in the next 365 days')
        start = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        start_utc = conf.default.local_timezone.localize(start).astimezone(pytz.UTC)
        href_etag_list = self.syncer.get_hel(start=start_utc)
        need_update = self.dbtool.needs_update(sync_account_name,
                                               href_etag_list)
        logging.debug('{number} event(s) need(s) an '
                      'update'.format(number=len(need_update)))
        vhe_list = self.syncer.get_vevents(need_update)

        for vevent, href, etag in vhe_list:
            try:
                self.dbtool.update(vevent,
                                   sync_account.name,
                                   href=href,
                                   etag=etag)
            except backend.UpdateFailed as error:
                logging.error(error)
        # syncing local new events
        hrefs = self.dbtool.get_new(sync_account.name)

        logging.debug('{number} new events need to be '
                      'uploaded'.format(number=len(hrefs)))
        try:
            for href in hrefs:
                event = self.dbtool.get_vevent_from_db(href, sync_account.name)
                (href_new, etag_new) = self.syncer.upload(event.vevent)
                self.dbtool.update_href(href,
                                        href_new,
                                        sync_account.name,
                                        status=backend.OK)
        except caldav.NoWriteSupport:
            logging.info('failed to upload a new event, '
                         'you need to enable write support to use this feature'
                         ', see the documentation.')


class Display(Controller):
    def __init__(self, conf):
        super(Display, self).__init__(conf)

        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        daylist = [(today, 'Today:'), (tomorrow, 'Tomorrow:')]
        event_column = list()
        for day, dayname in daylist:
            start = datetime.datetime.combine(day, datetime.time.min)
            end = datetime.datetime.combine(day, datetime.time.max)

            event_column.append(bstring(dayname))
            all_day_events = list()
            events = list()
            for account in conf.sync.accounts:
                color = aux.color_maker(conf.accounts[account]['color'])
                all_day_events += self.dbtool.get_allday_range(
                    day, account_name=account, color=color)
                events += self.dbtool.get_time_range(start, end, account,
                                                     color=color)
            for event in all_day_events:
                event_column.append(event.summary)
            events.sort(key=lambda e: e.start)
            for event in events:
                event_column.append(event.compact(day))

        calendar_column = calendar_display.vertical_month()
        rows = ['     '.join(one) for one in izip_longest(calendar_column, event_column, fillvalue='')]
        print '\n'.join(rows).encode('utf-8')


class NewFromString(Controller):
    def __init__(self, conf):
        super(NewFromString, self).__init__(conf)
        date_list = conf.new
        timeformat = '%H:%M'
        dateformat = '%d.%m.'
        datetimeformat = '%d.%m. %H:%M'
        event = aux.construct_event(date_list,
                                    timeformat,
                                    dateformat,
                                    datetimeformat,
                                    conf.default.local_timezone)
        self.dbtool.update(event, conf.sync.accounts.pop(), status=backend.NEW)


class Interactive(Controller):
    def __init__(self, conf):
        from khal import ui
        super(Interactive, self).__init__(conf)
        ui.interactive(conf=conf, dbtool=self.dbtool)
