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
use the Syncer class for syncing CalDAV resources
"""

from collections import namedtuple
from lxml import etree
import datetime
import requests
import urlparse
import logging
import icalendar


def get_random_href():
    """returns a random href"""
    import random
    tmp_list = list()
    for _ in xrange(3):
        rand_number = random.randint(0, 0x100000000)
        tmp_list.append("{0:x}".format(rand_number))
    return "-".join(tmp_list).upper()


class UploadFailed(Exception):
    """uploading the event failed"""
    pass


class NoWriteSupport(Exception):
    """write support has not been enabled"""
    pass


class Syncer(object):
    """class for interacting with a CalDAV server

    Since this relies heavily on Requests [1] its SSL verification is also
    shared by Syncer [2]. For now, only the *verify* keyword is exposed
    through this class.

    [1] http://docs.python-requests.org/
    [2] http://docs.python-requests.org/en/latest/user/advanced/

    raises:
        requests.exceptions.SSLError
        requests.exceptions.ConnectionError
        more requests.exceptions depending on the actual error
        Exception (shame on me)

    """

    def __init__(self, resource, debug='', user='', passwd='',
                 verify=True, write_support=False, auth='basic'):
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
        self.write_support = write_support
        self._settings = {'verify': verify}
        if auth == 'basic':
            self._settings['auth'] = (user, passwd,)
        if auth == 'digest':
            from requests.auth import HTTPDigestAuth
            self._settings['auth'] = HTTPDigestAuth(user, passwd)
        self._default_headers = {"User-Agent": "khal"}

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
        """gets verify from settings dict"""
        return self._settings['verify']

    @verify.setter
    def verify(self, verify):
        """set verify"""
        self._settings['verify'] = verify

    @property
    def headers(self):
        """returns the headers"""
        return dict(self._default_headers)

    def _check_write_support(self):
        """checks if user really wants his data destroyed"""
        if not self.write_support:
            raise NoWriteSupport

    def get_hel(self, start=None, end=None):
        """
        getting (href, etag) list

        type start: datetime.datetime
        type end: datetime.datetime
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

    def upload(self, vevent):
        """
        :param vevent: vevent
        :type vevent: unicode
        """
        self._check_write_support()
        calendar = icalendar.Calendar()
        calendar.add_component(icalendar.Event.from_ical(vevent))
        for _ in range(5):
            randstr = get_random_href()
            remotepath = str(self.url.resource + randstr + ".vcf")
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
