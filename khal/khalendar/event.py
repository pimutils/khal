# vim: set ts=4 sw=4 expandtab sts=4 fileencoding=utf-8:
# Copyright (c) 2013-2015 Christian Geier et al.
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

"""this module will the event model, hopefully soon in a cleaned up version"""

import datetime

import icalendar

from ..compat import unicode_type, bytes_type, iteritems
from .aux import to_naive_utc
from ..log import logger


class Event(object):

    """the base event class"""

    def __init__(self, ical, calendar, href=None, start=None, end=None,
                 color=None, readonly=False, unicode_symbols=True, etag=None,
                 locale=None, recuid=None):
        """
        :param ical: the icalendar VEVENT this event is based on
        :type ical: str or icalendar.cal.Event
        :param account: the account/calendar this event belongs to
        :type account: str TODO
        :param href: the href of the event, treated like a UID
        :type href: str
        :param locale: the locale settings
        :type locale: dict()
        :param start: start date[time] of this event, this will override the
                      start date from the vevent. This is useful for recurring
                      events, since we only save the original event once and
                      that original events start and end times might not be
                      *this* event's start and end time.
        :type start: datetime.date or datetime.datetime
        :param end: see :param start:
        :type end: datetime.date or datetime.datetime
        :param color: the color this event should be shown in ikhal and khal,
                      Supported color names are :
                      black, white, brown, yellow, dark grey, dark green,
                      dark blue, light grey, light green, light blue,
                      dark magenta, dark cyan, dark red, light magenta,
                      light cyan, light red
        :type color: str
        :param readonly: flag to show if this event may be modified or not
        :type readonly: bool
        :param unicode_symbols: some terminal fonts to not support fancey
                                unicode symbols, if set to False pure ascii
                                alternatives will be shown
        :type unicode_symbols: bool
        :param etag: the event's etag, will not be modified
        :type etag: str
        :param recuid: recurrence uid, mainly used for debugging
        :type recuid: str
        """
        if isinstance(ical, unicode_type):
            self.vevent = icalendar.Event.from_ical(ical)
        elif isinstance(ical, bytes_type):
            self.vevent = icalendar.Event.from_ical(ical.decode('utf-8'))
        elif isinstance(ical, icalendar.cal.Event):
            self.vevent = ical
        else:
            raise ValueError

        assert locale is not None
        self.locale = locale
        self.color = color
        self._recuid = recuid

        if href is None:
            uid = self.vevent['UID']
            href = uid + '.ics'

        # if uid is None and self.vevent.get('UID', '') == '':

        self.calendar = calendar
        self.readonly = readonly
        self.unicode_symbols = unicode_symbols
        self.etag = etag
        self.href = href

        self.allday = not isinstance(self.vevent['dtstart'].dt, datetime.datetime)

        if start is not None:
            if isinstance(self.vevent['dtstart'].dt, datetime.datetime):
                start = start.astimezone(locale['local_timezone'])
                end = end.astimezone(locale['local_timezone'])
            self.vevent['DTSTART'].dt = start

            if 'DTEND' in self.vevent.keys():
                self.vevent['DTEND'].dt = end

    @property
    def symbol_strings(self):
        if self.unicode_symbols:
            return dict(
                recurring=u'\N{Clockwise gapped circle arrow}',
                range=u'\N{Left right arrow}',
                range_end=u'\N{Rightwards arrow to bar}',
                range_start=u'\N{Rightwards arrow from bar}',
                right_arrow=u'\N{Rightwards arrow}'
            )
        else:
            return dict(
                recurring=u'R',
                range=u'<->',
                range_end=u'->|',
                range_start=u'|->',
                right_arrow=u'->'
            )

    @property
    def uid(self):
        return self.vevent['UID']

    @property
    def ident(self):
        return self.vevent['UID']

    # @uid.setter
    # def uid(self, value):
    #     self.vevent['UID'] = value

    @property
    def location(self):
        return self.vevent.get('LOCATION', None)

    @property
    def description(self):
        return self.vevent.get('DESCRIPTION', None)

    @property
    def start(self):
        start = self.vevent['DTSTART'].dt
        if self.allday:
            return start
        if start.tzinfo is None:
            start = self.locale['local_timezone'].localize(start)
        start = start.astimezone(self.locale['local_timezone'])
        return start

    @property
    def end(self):
        # TODO take care of events with neither DTEND nor DURATION
        try:
            end = self.vevent['DTEND'].dt
        except KeyError:
            duration = self.vevent['DURATION']
            end = self.start + duration.dt

        if self.allday:
            if end == self.start:
                # https://github.com/geier/khal/issues/129
                logger.warning('{} ("{}"): The event\'s end date property '
                               'contains the same value as the start date, '
                               'which is invalid as per RFC 2445. Khal will '
                               'assume this is meant to be single-day event '
                               'on {}'.format(self.href, self.summary,
                                              self.start))
                end += datetime.timedelta(days=1)
            return end

        if end.tzinfo is None:
            end = self.locale['default_timezone'].localize(end)
        end = end.astimezone(self.locale['local_timezone'])
        return end

    @property
    def summary(self):
        return self.vevent['SUMMARY']

    @property
    def recurpattern(self):
        if 'RRULE' in self.vevent:
            return self.vevent['RRULE'].to_ical()
        else:
            return None

    @property
    def recur(self):
        return 'RRULE' in self.vevent or 'RECURRENCE-ID' in self.vevent or \
            'RDATE' in self.vevent

    @property
    def raw(self):
        return self.to_ical().decode('utf-8')

    def to_ical(self):
        calendar = self._create_calendar()
        if hasattr(self.vevent['DTSTART'].dt, 'tzinfo'):
            tzs = [self.start.tzinfo]
            if (
                'DTEND' in self.vevent and
                hasattr(self.vevent['DTEND'].dt, 'tzinfo') and
                (self.vevent['DTSTART'].dt.tzinfo !=
                 self.vevent['DTEND'].dt.tzinfo)
            ):
                tzs.append(self.vevent['DTEND'].dt.tzinfo)

            for tzinfo in tzs:
                timezone = create_timezone(tzinfo, self.start)
                calendar.add_component(timezone)

        calendar.add_component(self.vevent)
        return calendar.to_ical()

    def long(self):
        """complete description of this event in text form

        :rtype: str
        :returns: event description
        """
        if self.allday:
            end = self.end - datetime.timedelta(days=1)
            if self.start == end:
                rangestr = self.start.strftime(self.locale['longdateformat'])
            else:
                if self.start.year == self.end.year:
                    startstr = self.start.strftime(self.locale['dateformat'])
                else:
                    startstr = self.start.strftime(self.locale['longdateformat'])
                endstr = end.strftime(self.locale['longdateformat'])
                rangestr = startstr + u' - ' + endstr
        else:
            # same day
            if self.start.utctimetuple()[:3] == self.end.utctimetuple()[:3]:
                starttime = self.start.strftime(self.locale['timeformat'])
                endtime = self.end.strftime(self.locale['timeformat'])
                date = self.end.strftime(self.locale['longdateformat'])
                rangestr = starttime + u'-' + endtime + u' ' + date
            else:
                startstr = self.start.strftime(self.locale['longdatetimeformat'])
                endstr = self.end.strftime(self.locale['longdatetimeformat'])
                rangestr = startstr + u' - ' + endstr
            if self.start.tzinfo.zone != self.locale['local_timezone'].zone:
                # doesn't work yet
                # TODO FIXME
                pass

        location = u'\nLocation: ' + self.location if \
            self.location is not None else u''
        description = u'\nDescription: ' + self.description if \
            self.description is not None else u''
        repitition = u'\nRepeat: ' + self.recurpattern if \
            self.recurpattern is not None else u''

        return u'{}: {}{}{}{}'.format(
            rangestr, self.summary, location, repitition, description)

    def compact(self, day, timeformat='%H:%M'):
        """
        returns a short description of the event

        :param day: print information in regards to this day, if the event
                    starts and ends on this day, the start and end time will be
                    given (only the description for all day events), otherwise
                    arrows will indicate if the events started before `day`
                    and/or lasts longer.
        :type day: datetime.date
        :return: compact description of Event
        :rtype: unicode()
        """
        try:
            if self.allday:
                return self._compact_allday(day)
            else:
                return self._compact_datetime(day, timeformat)
        except Exception as e:
            raise type(e)('Something went wrong while displaying "{}": {}'
                          .format(self.href, str(e)))

    def _compact_allday(self, day):
        if self.recur:
            recurstr = self.symbol_strings['recurring']
        else:
            recurstr = ''

        if day < self.start or day + datetime.timedelta(days=1) > self.end:
            raise ValueError('Day out of range: {}'
                             .format(dict(day=day, start=self.start,
                                          end=self.end)))
        elif self.start < day and self.end > day + datetime.timedelta(days=1):
            # event starts before and goes on longer than `day`:
            rangestr = self.symbol_strings['range']
        elif self.start < day:
            # event started before `day`
            rangestr = self.symbol_strings['range_end']
        elif self.end > day + datetime.timedelta(days=1):
            # event goes on longer than `day`
            rangestr = self.symbol_strings['range_start']
        elif self.start == self.end - datetime.timedelta(days=1) == day:
            # only on `day`
            rangestr = ''

        return ' '.join(filter(bool, (rangestr, self.summary, recurstr)))

    def _compact_datetime(self, day, timeformat='%M:%H'):
        """compact description of this event

        see compact() for description of `day`

        :return: compact description of Event
        :rtype: unicode()
        """
        if day < self.start.date() or day > self.end.date():
            raise ValueError(
                'please supply a `day` this event is scheduled on')
        start = datetime.datetime.combine(day, datetime.time.min)
        end = datetime.datetime.combine(day, datetime.time.max)
        local_start = self.locale['local_timezone'].localize(start)
        local_end = self.locale['local_timezone'].localize(end)
        if self.recur:
            recurstr = ' ' + self.symbol_strings['recurring']
        else:
            recurstr = ''

        tostr = '-'
        if self.start < local_start:
            startstr = self.symbol_strings['right_arrow'] + ' '
            tostr = ''
        else:
            startstr = self.start.strftime(timeformat)

        if self.end > local_end:
            endstr = self.symbol_strings['right_arrow'] + ' '
            tostr = ''
        else:
            endstr = self.end.strftime(timeformat)

        return (startstr + tostr + endstr +
                ': ' + self.summary + recurstr)

    def _create_calendar(self):
        """
        create the calendar

        :returns: calendar
        :rtype: icalendar.Calendar()
        """
        calendar = icalendar.Calendar()
        calendar.add('version', '2.0')
        calendar.add('prodid', '-//CALENDARSERVER.ORG//NONSGML Version 1//EN')

        return calendar


def create_timezone(tz, first_date=None, last_date=None):
    """
    create an icalendar vtimezone from a pytz.tzinfo

    :param tz: the timezone
    :type tz: pytz.tzinfo
    :param first_date: the very first datetime that needs to be included in the
    transition times, typically the DTSTART value of the (first recurring)
    event
    :type first_date: datetime.datetime
    :param last_date: the last datetime that needs to included, typically the
    end of the (very last) event (of a recursion set)
    :returns: timezone information
    :rtype: icalendar.Timezone()

    we currently have a problem here:

       pytz.timezones only carry the absolute dates of time zone transitions,
       not their RRULEs. This will a) make for rather bloated VTIMEZONE
       components, especially for long recurring events, b) we'll need to
       specify for which time range this VTIMEZONE should be generated and c)
       will not be valid for recurring events that go into eternity.

    Possible Solutions:

    As this information is not provided by pytz at all, there is no
    easy solution, we'd really need to ship another version of the OLSON DB.

    """

    # TODO last_date = None, recurring to infinity

    first_date = datetime.datetime.today() if not first_date else to_naive_utc(first_date)
    last_date = datetime.datetime.today() if not last_date else to_naive_utc(last_date)
    timezone = icalendar.Timezone()
    timezone.add('TZID', tz)

    dst = {one[2]: 'DST' in two.__repr__() for one, two in iteritems(tz._tzinfos)}

    # looking for the first and last transition time we need to include
    first_num, last_num = 0, len(tz._utc_transition_times) - 1
    first_tt = tz._utc_transition_times[0]
    last_tt = tz._utc_transition_times[-1]
    for num, dt in enumerate(tz._utc_transition_times):
        if dt > first_tt and dt < first_date:
            first_num = num
            first_tt = dt
        if dt < last_tt and dt > last_date:
            last_num = num
            last_tt = dt

    timezones = dict()
    for num in range(first_num, last_num + 1):
        name = tz._transition_info[num][2]
        if name in timezones:
            ttime = tz.fromutc(tz._utc_transition_times[num]).replace(tzinfo=None)
            if 'RDATE' in timezones[name]:
                timezones[name]['RDATE'].dts.append(
                    icalendar.prop.vDDDTypes(ttime))
            else:
                timezones[name].add('RDATE', ttime)
            continue

        if dst[name]:
            subcomp = icalendar.TimezoneDaylight()
        else:
            subcomp = icalendar.TimezoneStandard()

        subcomp.add('TZNAME', tz._transition_info[num][2])
        subcomp.add(
            'DTSTART',
            tz.fromutc(tz._utc_transition_times[num]).replace(tzinfo=None))
        subcomp.add('TZOFFSETTO', tz._transition_info[num][0])
        subcomp.add('TZOFFSETFROM', tz._transition_info[num - 1][0])
        timezones[name] = subcomp

    for subcomp in timezones.values():
        timezone.add_component(subcomp)

    return timezone
