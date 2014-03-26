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
this file is name khalendar since calendar and icalendar are already taken
"""

import datetime
import logging
import traceback

import pytz

from khal import backend, caldav
from khal.status import OK, NEW, CHANGED, DELETED, NEWDELETE, CALCHANGED


class BaseCalendar(object):
    """base class for Calendar and CalendarCollection"""

    def get_by_time_range(self, start, end):
        raise NotImplementedError

    def get_allday_by_time_range(self, start, end):
        raise NotImplementedError

    def get_datetime_by_time_range(self, start, end):
        raise NotImplementedError

    def sync(self):
        raise NotImplementedError


class Calendar(object):
    def __init__(self, name, dbtool, resource, username=None, password=None,
                 auth='basic', ssl_verify=True, server_type='caldav',
                 readonly=False, color='', unicode_symbols=True,
                 default_timezone=None, local_timezone=None):

        if local_timezone is None:
            local_timezone = default_timezone  # sync time might be off by a
            # couple of hours, perhaps we should just use UTC and be done with
            # it
        self.name = name
        self.color = color

        self._resource = resource
        self._username = username
        self._password = password
        self._ssl_verify = ssl_verify
        self._server_type = server_type
        self._auth = auth
        self._dbtool = dbtool
        self._readonly = readonly
        self._unicode_symbols = unicode_symbols
        self._default_timezone = default_timezone
        self._local_timezone = local_timezone

    def get_by_time_range(self, start, end, show_deleted=False):
        return self._dbtool.get_time_range(start,
                                           end,
                                           self.name,
                                           self.color,
                                           self._readonly,
                                           self._unicode_symbols,
                                           show_deleted)

    def get_allday_by_time_range(self, start, end=None, show_deleted=False):
        return self._dbtool.get_allday_range(
            start, end, self.name, self.color, self._readonly,
            self._unicode_symbols, show_deleted)

    def get_datetime_by_time_range(self, start, end, show_deleted=False):
        return self._dbtool.get_time_range(
            start, end, self.name, self.color, self._readonly,
            self._unicode_symbols, show_deleted)

    def update(self, event):
        """update an event in the database"""
        self._dbtool.update(event.vevent.to_ical(),
                            self.name,
                            event.href,
                            etag=event.etag,
                            status=CHANGED)

    def new(self, event):
        """save a new event to the database"""
        self._dbtool.update(event.vevent.to_ical(),
                            self.name,
                            href='',
                            etag=event.etag,
                            status=NEW)

    def mark(self, status, event):
        self._dbtool.set_status(event.href, status, self.name)

    def sync(self):
        rvalue = 0
        try:
            logging.debug("starting to sync calendar `{0}`".format(self.name))
            if self._server_type == 'caldav':
                self._sync_caldav()
            elif self._server_type == 'http':
                self._sync_http()
        except Exception as error:
            logging.debug(traceback.format_exc())
            logging.critical('While syncing account `{0}` an error '
                             'occured:\n  '.format(self.name)
                             + str(error))
            rvalue += 1
        return rvalue

    def _sync_caldav(self):
        syncer = caldav.Syncer(self._resource,
                               user=self._username,
                               password=self._password,
                               verify=self._ssl_verify,
                               auth=self._auth)
        #self._dbtool.check_account_table(self.name)
        logging.debug('syncing events in the next 365 days')
        start = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        start_utc = self._local_timezone.localize(start).astimezone(pytz.UTC)
        end_utc = start_utc + datetime.timedelta(days=365)
        href_etag_list = syncer.get_hel(start=start_utc, end=end_utc)
        need_update = self._dbtool.needs_update(self.name, href_etag_list)
        logging.debug('{number} event(s) need(s) an '
                      'update'.format(number=len(need_update)))
        vhe_list = syncer.get_vevents(need_update)
        for vevent, href, etag in vhe_list:
            try:
                self._dbtool.update(vevent,
                                    self.name,
                                    href=href,
                                    etag=etag)
            except backend.UpdateFailed as error:
                logging.error(error)
        # syncing local new events
        hrefs = self._dbtool.get_new(self.name)

        logging.debug('{number} new events need to be '
                      'uploaded'.format(number=len(hrefs)))
        for href in hrefs:
            event = self._dbtool.get_vevent_from_db(href, self.name)
            (href_new, etag_new) = syncer.upload(event.vevent,
                                                 self._default_timezone)
            self._dbtool.update_href(href,
                                     href_new,
                                     self.name,
                                     status=OK)

        # syncing locally modified events
        hrefs = self._dbtool.get_changed(self.name)
        for href in hrefs:
            event = self._dbtool.get_vevent_from_db(href, self.name)
            etag = syncer.update(event.vevent, event.href, event.etag)

        # looking for events deleted on the server but still in the local db
        locale_hrefs = self._dbtool.hrefs_by_time_range(start_utc,
                                                        end_utc,
                                                        self.name)
        remote_hrefs = [href for href, _ in href_etag_list]
        may_be_deleted = list(set(locale_hrefs) - set(remote_hrefs))
        if may_be_deleted != list():
            for href in may_be_deleted:
                if syncer.test_deleted(href) and self._dbtool.get_status(href, self.name) != NEW:
                    logging.debug('removing remotely deleted event {0} from '
                                  'the local db'.format(href))
                    self._dbtool.delete(href, self.name)

    def _sync_http(self):
        """
        simple syncer to import events from .ics files
        """
        import icalendar
        self.syncer = caldav.HTTPSyncer(self._resource,
                                        user=self._username,
                                        password=self._password,
                                        verify=self._ssl_verify,
                                        auth=self._auth)
        #self._dbtool.check_account_table(self.name)
        ics = self.syncer.get_ics()
        cal = icalendar.Calendar.from_ical(ics)
        remote_uids = list()
        for component in cal.walk():
            if component.name in ['VEVENT']:
                remote_uids.append(str(component['UID']))
                try:
                    self._dbtool.update(component,
                                        self.name,
                                        href=str(component['UID']),
                                        etag='',
                                        status=OK)
                except backend.UpdateFailed as error:
                    logging.error(error)
        # events from an icalendar retrieved over stupid http have no href
        # themselves, so their uid is safed in the `href` column
        locale_uids = [uid for uid, account in self._dbtool.get_all_href_from_db([self.name])]
        remote_deleted = list(set(locale_uids) - set(remote_uids))
        if remote_deleted != list():
            for uid in remote_deleted:
                logging.debug('removing remotely deleted event {0} from '
                              'the local db'.format(uid))
                self._dbtool.delete(uid, self.name)


class CalendarCollection(object):
    def __init__(self):
        self._calnames = dict()

    @property
    def calendars(self):
        return self._calnames.values()

    def append(self, calendar):
        self._calnames[calendar.name] = calendar
        self.calendars.append(calendar)

    def get_by_time_range(self, start, end):
        result = list()
        for one in self.calendars:
            result = result + one.get_by_time_range(start, end)
        return result

    def get_allday_by_time_range(self, start, end=None):
        result = list()
        for one in self.calendars:
            result = result + one.get_allday_by_time_range(start, end)
        return result

    def get_datetime_by_time_range(self, start, end):
        result = list()
        for one in self.calendars:
            result = result + one.get_datetime_by_time_range(start, end)
        return result

    def update(self, event):
        self._calnames[event.account].update(event)

    def new(self, event):
        self._calnames[event.account].new(event)

    def change_collection(self, event, new_collection):
        self._calnames[new_collection].new(event)
        delstatus = NEWDELETE if event.status == NEW else CALCHANGED
        self._calnames[event.account].mark(delstatus, event)

    def mark(self, status, event):
        self._calnames[event.account].mark(status, event)

    def sync(self):
        rvalue = 0
        for one in self.calendars:
            rvalue += one.sync()
        return rvalue
