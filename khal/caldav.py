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
use the Syncer class for syncing CalDAV resources
"""

from collections import namedtuple
import datetime
try:
    import urlparse
except ImportError:
    from urllib import parse as urlparse
import logging

import icalendar
from lxml import etree
import requests


def get_random_href():
    """returns a random href

    :returns: a random href
    :rtype: str
    """
    import random
    tmp_list = list()
    for _ in xrange(3):
        rand_number = random.randint(0, 0x100000000)
        tmp_list.append("{0:x}".format(rand_number))
    return "-".join(tmp_list).upper()


class UploadFailed(Exception):
    """uploading the event failed"""
    pass


class HTTPSyncer(object):
    """class for getting an ics file from an http(s) url

    mostly a wrapper around requests.get, being instantiated the same way
    as (CalDAV)Syncer"""
    def __init__(self, resource, debug='', user='', password='',
                 verify=True, auth='basic'):
        #shutup urllib3
        urllog = logging.getLogger('requests.packages.urllib3.connectionpool')
        urllog.setLevel(logging.CRITICAL)
        urllog = logging.getLogger('urllib3.connectionpool')
        urllog.setLevel(logging.CRITICAL)

        split_url = urlparse.urlparse(resource)
        url_tuple = namedtuple('url', 'resource base path')
        self.url = url_tuple(resource,
                             split_url.scheme + '://' + split_url.netloc,
                             split_url.path)
        self.debug = debug
        self.session = requests.session()
        self._settings = {'verify': verify}
        if auth == 'basic':
            self._settings['auth'] = (user, password,)
        if auth == 'digest':
            from requests.auth import HTTPDigestAuth
            self._settings['auth'] = HTTPDigestAuth(user, password)
        self._default_headers = {"User-Agent": "khal"}

    def get_ics(self):
        headers = self._default_headers
        response = self.session.request('GET',
                                        self.url.resource,
                                        headers=headers,
                                        **self._settings)

        response.raise_for_status()   # raises error on not 2XX HTTP status
        return response.content.decode('utf-8')


class Syncer(object):
    """class for interacting with a CalDAV server

    Since this relies heavily on Requests [1] its SSL verification is also
    shared by Syncer [2]. For now, only the *verify* keyword is exposed
    through this class.

    [1] http://docs.python-requests.org/
    [2] http://docs.python-requests.org/en/latest/user/advanced/

    :param resource: the remote CalDAV resource
    :type resource: str
    :param debug: enable debugging
    :type debug: bool
    :param user: user name for accessing the CalDAV resource
    :type user: str
    :param password: password for accessing the CalDAV resource
    :type password: str
    :param verify: should a https connection be verifiey or not
    :type param: bool
    :param auth: which http authentication is used, supported are 'basic'
                 and 'digest'
    :type param: str

    :raises: requests.exceptions.SSLError
    :raises: requests.exceptions.ConnectionError
    :raises: more requests.exceptions depending on the actual error
    :raises: Exception (shame on me)

    """

    def __init__(self, resource, debug='', user='', password='',
                 verify=True, auth='basic'):
        """
        """
        #shutup urllib3
        urllog = logging.getLogger('requests.packages.urllib3.connectionpool')
        urllog.setLevel(logging.CRITICAL)
        urllog = logging.getLogger('urllib3.connectionpool')
        urllog.setLevel(logging.CRITICAL)

        split_url = urlparse.urlparse(resource)
        url_tuple = namedtuple('url', 'resource base path')
        self.url = url_tuple(resource,
                             split_url.scheme + '://' + split_url.netloc,
                             split_url.path)
        self.debug = debug
        self.session = requests.session()
        self._settings = {'verify': verify}
        if auth == 'basic':
            self._settings['auth'] = (user, password,)
        if auth == 'digest':
            from requests.auth import HTTPDigestAuth
            self._settings['auth'] = HTTPDigestAuth(user, password)
        self._default_headers = {"User-Agent": "khal"}
        self._default_headers["Content-Type"] = "application/xml; charset=UTF-8"

        headers = self.headers
        headers['Depth'] = '1'
        response = self.session.request('OPTIONS',
                                        self.url.resource,
                                        headers=headers,
                                        **self._settings)

        response.raise_for_status()   # raises error on not 2XX HTTP status
        if response.headers['DAV'].count('calendar-access') == 0:
            raise Exception("URL is not a CalDAV resource")

    @property
    def verify(self):
        """gets verify from settings dict

        :returns: True or False
        :rtype: bool
        """
        return self._settings['verify']

    @verify.setter
    def verify(self, verify):
        """set verify

        :param verify: True or False
        :type verify: bool
        """
        self._settings['verify'] = verify

    @property
    def headers(self):
        """returns the default headers for all CalDAV requests

        :returns: headers
        :rtype: dict
        """
        return dict(self._default_headers)

    def get_hel(self, start=None, end=None):
        """
        getting (href, etag) list

        :param start: start date
        :type start: datetime.datetime
        :param end: end date
        :type end: datetime.datetime
        :returns: list of (href, etags) tuples
        :rtype: list(tuple(str, str))
        """
        hel = list()
        if start is None:
            start = datetime.datetime.utcnow()
        if end is None:
            end = start + datetime.timedelta(days=365)
        sstart = start.strftime('%Y%m%dT%H%M%SZ')
        send = end.strftime('%Y%m%dT%H%M%SZ')
        body = """<?xml version="1.0" encoding="utf-8" ?>
<C:calendar-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:prop>
    <D:getetag/>
  </D:prop>
  <C:filter>
    <C:comp-filter name="VCALENDAR">
      <C:comp-filter name="VEVENT">
        <C:time-range start="{start}"
                        end="{end}"/>
      </C:comp-filter>
    </C:comp-filter>
  </C:filter>
</C:calendar-query>""".format(start=sstart, end=send)

        response = self.session.request('REPORT',
                                        self.url.resource,
                                        data=body,
                                        headers=self.headers,
                                        **self._settings)
        response.raise_for_status()
        root = etree.XML(response.text.encode(response.encoding))
        for element in root.iter('{DAV:}response'):
            etag = element.find('{DAV:}propstat').find('{DAV:}prop').find('{DAV:}getetag').text
            href = element.find('{DAV:}href').text
            hel.append((href, etag))
        return hel

    def get_vevents(self, hrefs):
        """
        gets events by hrefs

        :param hrefs: hrefs to fetch
        :type hrefs: list
        :returns: list of tuples(vevent, href, etag)
        """
        if hrefs == list():
            return list()
        empty_body = """<?xml version="1.0" encoding="utf-8" ?>
<C:calendar-multiget xmlns:D="DAV:"
                     xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:prop>
    <D:getetag/>
    <C:calendar-data/>
  </D:prop>
{hrefs}
</C:calendar-multiget>"""
        href_xml = ["<D:href>{href}</D:href>".format(href=href) for href in hrefs]
        href_xml = '\n'.join(href_xml)
        body = empty_body.format(hrefs=href_xml)
        response = self.session.request('REPORT',
                                        self.url.resource,
                                        data=body,
                                        headers=self.headers,
                                        **self._settings)
        response.raise_for_status()
        root = etree.XML(response.text.encode(response.encoding))
        vhe = list()

        for element in root.iter('{DAV:}response'):
            href = element.find('{DAV:}href').text
            vevent = element.find('{DAV:}propstat').find('{DAV:}prop').find('{urn:ietf:params:xml:ns:caldav}calendar-data').text
            etag = element.find('{DAV:}propstat').find('{DAV:}prop').find('{DAV:}getetag').text
            vhe.append((vevent, href, etag))
        return vhe

    def test_deleted(self, href):
        """
        test if event is still on server

        :param href: href to test
        :type hrefs: str
        :returns: True or False
        """
        empty_body = """<?xml version="1.0" encoding="utf-8" ?>
<C:calendar-multiget xmlns:D="DAV:"
                     xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:prop>
    <D:getetag/>
    <C:calendar-data/>
  </D:prop>
{hrefs}
</C:calendar-multiget>"""
        href_xml = ["<D:href>{href}</D:href>".format(href=href) for href in [href, ]]
        href_xml = '\n'.join(href_xml)
        body = empty_body.format(hrefs=href_xml)

        response = self.session.request('REPORT',
                                        self.url.resource,
                                        data=body,
                                        headers=self.headers,
                                        **self._settings)
        try:
            response.raise_for_status()
        except requests.HTTPError:
            # some CalDAV servers, i.e. at least SabreDAV as deployed by
            # fruux.com, return 404 if an event is deleted
            #
            if response.status_code == 404:
                return True
            else:
                raise

        root = etree.XML(response.text.encode(response.encoding))
        vhe = list()
        for element in root.iter('{DAV:}response'):
            try:
                href = element.find('{DAV:}href').text
                vevent = element.find('{DAV:}propstat').find('{DAV:}prop').find('{urn:ietf:params:xml:ns:caldav}calendar-data').text
                etag = element.find('{DAV:}propstat').find('{DAV:}prop').find('{DAV:}getetag').text
                vhe.append((vevent, href, etag))
            except AttributeError:
                continue
        if not vhe:
            return True
        return False


    def _create_calendar(self):
        """
        create the calendar

        :returns: calendar
        :rtype: icalendar.Calendar()
        """
        calendar = icalendar.Calendar()
        calendar.add('version','2.0')
        calendar.add('prodid','-//CALENDARSERVER.ORG//NONSGML Version 1//EN')

        return calendar

    def _create_timezone(self, tz):
        """
        create an icalendar timezone from a pytz.tzinfo

        :param tz: the timezone
        :type tz: pytz.tzinfo
        :returns: timezone information set
        :rtype: icalendar.Timezone()
        """
        timezone = icalendar.Timezone()
        timezone.add('TZID', tz)

        # FIXME should match year of the event, not this year
        daylight, standard = [(num, dt) for num, dt in enumerate(tz._utc_transition_times) if dt.year == datetime.datetime.today().year]

        timezone_daylight = icalendar.TimezoneDaylight()
        timezone_daylight.add('TZNAME', tz._transition_info[daylight[0]][2])
        timezone_daylight.add('DTSTART', daylight[1])
        timezone_daylight.add('TZOFFSETFROM', tz._transition_info[daylight[0]][0])
        timezone_daylight.add('TZOFFSETTO', tz._transition_info[standard[0]][0])

        timezone_standard = icalendar.TimezoneStandard()
        timezone_standard.add('TZNAME', tz._transition_info[standard[0]][2])
        timezone_standard.add('DTSTART', standard[1])
        timezone_standard.add('TZOFFSETFROM', tz._transition_info[standard[0]][0])
        timezone_standard.add('TZOFFSETTO', tz._transition_info[daylight[0]][0])

        timezone.add_component(timezone_daylight)
        timezone.add_component(timezone_standard)

        return timezone

    def upload(self, vevent, default_timezone):
        """
        uploads a new event to the server

        :param default_timezone:
        :type default_timezone:
        :param vevent: the event to upload
        :type vevent: icalendar.cal.Event
        :returns: new url of the event and its etag
        :rtype: tuple(str, str)
        """
        calendar = self._create_calendar()
        timezone = self._create_timezone(default_timezone)  # FIXME
        calendar.add_component(timezone)
        calendar.add_component(vevent)

        for _ in range(5):
            randstr = get_random_href()
            remotepath = str(self.url.resource + randstr + ".ics")
            headers = self.headers
            headers['content-type'] = 'text/calendar'
            headers['If-None-Match'] = '*'
            response = requests.put(remotepath,
                                    data=calendar.to_ical(),
                                    headers=headers,
                                    **self._settings)

            if response.ok:
                parsed_url = urlparse.urlparse(remotepath)
                if ('etag' not in response.headers.keys()
                        or response.headers['etag'] is None):
                    etag = ''
                else:
                    etag = response.headers['etag']

                return (parsed_url.path, etag)
        response.raise_for_status()

    def update(self, vevent, href, etag):
        """
        updates a modified event on the server

        :param vevent: the event to upload
        :type vevent: icalendar.cal.Event
        :param href: the href of the event
        :type href: str
        :param etag: etag of the event
        :type etag: str
        :returns: new etag (if the server returns it)
        :rtype: str or None
        """
        calendar = self._create_calendar()
        if hasattr(vevent['DTSTART'].dt, 'tzinfo'):  # FIXME as most other timezone related stuff
            timezone = self._create_timezone(vevent['DTSTART'].dt.tzinfo)
            calendar.add_component(timezone)
        calendar.add_component(vevent)

        remotepath = str(self.url.base + href)
        headers = self.headers
        headers['content-type'] = 'text/calendar'
        headers['If-Match'] = etag
        response = requests.put(remotepath,
                                data=calendar.to_ical(),
                                headers=headers,
                                **self._settings)
        response.raise_for_status()

        if 'etag' in response.headers.keys():
            return response.headers['etag']
        else:
            return None
