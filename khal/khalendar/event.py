# Copyright (c) 2013-2016 Christian Geier et al.
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

"""this module cointains the event model, hopefully soon in a cleaned up version"""

from collections import defaultdict
from datetime import date, datetime, time, timedelta

import os
import icalendar
import pytz

from ..aux import generate_random_uid, datetime_fillin
from .aux import to_naive_utc, to_unix_time, invalid_timezone, delete_instance
from ..log import logger
from ..terminal import get_color
from click import style


class Event(object):
    """base Event class for representing a *recurring instance* of an Event

    (in case of non-recurring events this distinction is irrelevant)
    We keep a copy of the start and end time around, because for recurring
    events it might be costly to expand the recursion rules

    important distinction for AllDayEvents:
        all end times are as presented to a user, i.e. an event scheduled for
        only one day will have the same start and end date (even though the
        icalendar standard would have the end date be one day later)
    """
    allday = False

    def __init__(self, vevents, ref=None, **kwargs):
        """
        :param start: start datetime of this event instance
        :type start: datetime.date
        :param end: end datetime of this event instance in unix time
        :type end: datetime.date
        """
        if self.__class__.__name__ == 'Event':
            raise ValueError('do not initialize this class directly')
        self._vevents = vevents
        self._locale = kwargs.pop('locale', None)
        self.readonly = kwargs.pop('readonly', None)
        self.href = kwargs.pop('href', None)
        self.etag = kwargs.pop('etag', None)
        self.calendar = kwargs.pop('calendar', None)
        self.ref = ref

        start = kwargs.pop('start', None)
        end = kwargs.pop('end', None)

        if start is None:
            self._start = self._vevents[self.ref]['DTSTART'].dt
        else:
            self._start = start
        if end is None:
            try:
                self._end = self._vevents[self.ref]['DTEND'].dt
            except KeyError:
                self._end = self._start + self._vevents[self.ref]['DURATION'].dt
        else:
            self._end = end
        if kwargs:
            raise TypeError('%s are invalid keyword arguments to this function' % kwargs.keys())

    @classmethod
    def _get_type_from_vDDD(cls, start):
        """
        :type start: icalendar.prop.vDDDTypes
        :type start: icalendar.prop.vDDDTypes
        """
        if not isinstance(start.dt, datetime):
            return AllDayEvent
        if 'TZID' in start.params or start.dt.tzinfo is not None:
            return LocalizedEvent
        return FloatingEvent

    @classmethod
    def _get_type_from_date(cls, start):
        if hasattr(start, 'tzinfo') and start.tzinfo is not None:
            cls = LocalizedEvent
        elif isinstance(start, datetime):
            cls = FloatingEvent
        elif isinstance(start, date):
            cls = AllDayEvent
        return cls

    @classmethod
    def fromVEvents(cls, events_list, ref=None, **kwargs):
        """
        :type events: list
        """
        assert isinstance(events_list, list)

        vevents = dict()
        if len(events_list) == 1:
            vevents['PROTO'] = events_list[0]  # TODO set mutable = False
        else:
            for event in events_list:
                if 'RECURRENCE-ID' in event:
                    if invalid_timezone(event['RECURRENCE-ID']):
                        default_timezone = kwargs['locale']['default_timezone']
                        recur_id = default_timezone.localize(event['RECURRENCE-ID'].dt)
                        ident = str(to_unix_time(recur_id))
                    else:
                        ident = str(to_unix_time(event['RECURRENCE-ID'].dt))
                    vevents[ident] = event
                else:
                    vevents['PROTO'] = event
        if ref is None:
            ref = 'PROTO'

        try:
            if type(vevents[ref]['DTSTART'].dt) != type(vevents[ref]['DTEND'].dt):  # flake8: noqa
                raise ValueError('DTSTART and DTEND should be of the same type (datetime or date)')
        except KeyError:
            pass

        if kwargs.get('start'):
            instcls = cls._get_type_from_date(kwargs.get('start'))
        else:
            instcls = cls._get_type_from_vDDD(vevents[ref]['DTSTART'])
        return instcls(vevents, ref=ref, **kwargs)

    @classmethod
    def fromString(cls, event_str, ref=None, **kwargs):
        calendar_collection = icalendar.Calendar.from_ical(event_str)
        events = [item for item in calendar_collection.walk() if item.name == 'VEVENT']
        return cls.fromVEvents(events, ref, **kwargs)

    def __lt__(self, other):
        start = self.start_local
        other_start = other.start_local
        if isinstance(start, date) and not isinstance(start, datetime):
            start = datetime.combine(start, time.min)

        if isinstance(other_start, date) and not isinstance(other_start, datetime):
            other_start = datetime.combine(other_start, time.max)

        start = start.replace(tzinfo=None)
        other_start = other_start.replace(tzinfo=None)
        try:
            return start <= other_start
        except TypeError:
            raise ValueError('Cannot compare events {} and {}'.format(start, other_start))

    def update_start_end(self, start, end):
        """update start and end time of this event

        calling this an a recurring event will lead to the proto instance
        be set to the new start and end times

        beware, this methods performs some open heart surgerly
        """
        if type(start) != type(end):  # flake8: noqa
            raise ValueError('DTSTART and DTEND should be of the same type (datetime or date)')
        self.__class__ = self._get_type_from_date(start)

        self._vevents[self.ref].pop('DTSTART')
        self._vevents[self.ref].add('DTSTART', start)
        self._start = start
        if not isinstance(end, datetime):
            end = end + timedelta(days=1)
        self._end = end
        if 'DTEND' in self._vevents[self.ref]:
            self._vevents[self.ref].pop('DTEND')
            self._vevents[self.ref].add('DTEND', end)
        else:
            self._vevents[self.ref].pop('DURATION')
            self._vevents[self.ref].add('DURATION', end - start)

    @property
    def recurring(self):
        return 'RRULE' in self._vevents[self.ref] or \
            'RECURRENCE-ID' in self._vevents[self.ref] or \
            'RDATE' in self._vevents[self.ref]

    @property
    def recurpattern(self):
        if 'RRULE' in self._vevents[self.ref]:
            return self._vevents[self.ref]['RRULE'].to_ical().decode('utf-8')
        else:
            return ''

    @property
    def recurobject(self):
        if 'RRULE' in self._vevents[self.ref]:
            return self._vevents[self.ref]['RRULE']
        else:
            return icalendar.vRecur()

    def update_rrule(self, rrule):
        self._vevents['PROTO'].pop('RRULE')
        if rrule is not None:
            self._vevents['PROTO'].add('RRULE', rrule)

    @property
    def recurrence_id(self):
        """return the "original" start date of this event (i.e. their recurrence-id)
        """
        if self.ref == 'PROTO':
            return self.start
        else:
            return pytz.UTC.localize(datetime.utcfromtimestamp(int(self.ref)))

    def increment_sequence(self):
        """update the SEQUENCE number, call before saving this event"""
        # TODO we might want to do this automatically in raw() everytime
        # the event has changed, this will f*ck up the tests though
        try:
            self._vevents[self.ref]['SEQUENCE'] += 1
        except KeyError:
            self._vevents[self.ref]['SEQUENCE'] = 0

    @property
    def symbol_strings(self):
        if self._locale['unicode_symbols']:
            return dict(
                recurring='\N{Clockwise gapped circle arrow}',
                range='\N{Left right arrow}',
                range_end='\N{Rightwards arrow to bar}',
                range_start='\N{Rightwards arrow from bar}',
                right_arrow='\N{Rightwards arrow}'
            )
        else:
            return dict(
                recurring='R',
                range='<->',
                range_end='->|',
                range_start='|->',
                right_arrow='->'
            )

    @property
    def start_local(self):
        """self.start() localized to local timezone"""
        return self.start

    @property
    def end_local(self):
        """self.end() localized to local timezone"""
        return self.end

    @property
    def start(self):
        """this should return the start date(time) as saved in the event"""
        return self._start

    @property
    def end(self):
        """this should return the end date(time) as saved in the event or
        implicitly defined by start and duration"""
        return self._end

    @property
    def duration(self):
        try:
            return self._vevents[self.ref]['DURATION'].dt
        except KeyError:
            return self.end - self.start

    @property
    def uid(self):
        return self._vevents[self.ref]['UID']

    @property
    def organizer(self):
        if 'ORGANIZER' not in self._vevents[self.ref]:
            return ''
        organizer = self._vevents[self.ref]['ORGANIZER']
        cn = organizer.params.get('CN', '')
        email = organizer.split(':')[-1]
        if cn:
            return '{} ({})'.format(cn, email)
        else:
            return email

    @staticmethod
    def _create_calendar():
        """
        create the calendar

        :returns: calendar
        :rtype: icalendar.Calendar()
        """
        calendar = icalendar.Calendar()
        calendar.add('version', '2.0')
        calendar.add('prodid', '-//CALENDARSERVER.ORG//NONSGML Version 1//EN')
        return calendar

    @property
    def raw(self):
        """needed for vdirsyncer comat

        return text
        """
        calendar = self._create_calendar()
        tzs = list()
        for vevent in self._vevents.values():
            if hasattr(vevent['DTSTART'].dt, 'tzinfo') and vevent['DTSTART'].dt.tzinfo is not None:
                tzs.append(vevent['DTSTART'].dt.tzinfo)
            if 'DTEND' in vevent and hasattr(vevent['DTEND'].dt, 'tzinfo') and \
                    vevent['DTEND'].dt.tzinfo is not None and \
                    vevent['DTEND'].dt.tzinfo not in tzs:
                tzs.append(vevent['DTEND'].dt.tzinfo)

        for tzinfo in tzs:
            if tzinfo == pytz.UTC:
                continue
            timezone = create_timezone(tzinfo, self.start)
            calendar.add_component(timezone)

        for vevent in self._vevents.values():
            calendar.add_component(vevent)
        return calendar.to_ical().decode('utf-8')

    def export_ics(self, path):
        """export event as ICS
        """
        export_path = os.path.expanduser(path)
        with open(export_path, 'w') as fh:
            fh.write(self.raw)

    @property
    def ident(self):
        """neeeded for vdirsyncer compat"""
        return self._vevents[self.ref]['UID']

    @property
    def summary(self):
        bday = self._vevents[self.ref].get('x-birthday', None)
        if bday:
            number = self.start_local.year - int(bday[:4])
            name = self._vevents[self.ref].get('x-fname', None)
            return '{name}\'s {number}th birthday'.format(name=name, number=number)
        else:
            return self._vevents[self.ref].get('SUMMARY', '')

    def update_summary(self, summary):
        self._vevents[self.ref]['SUMMARY'] = summary

    @staticmethod
    def _can_handle_alarm(alarm):
        """
        Decides whether we can handle a certain alarm.
        """
        return alarm.get('ACTION') == 'DISPLAY' and isinstance(alarm.get('TRIGGER').dt, timedelta)

    @property
    def alarms(self):
        """
        Returns a list of all alarms in th original event that we can handle. Unknown types of
        alarms are ignored.
        """
        return [(a.get('TRIGGER').dt, a.get('DESCRIPTION'))
                for a in self._vevents[self.ref].subcomponents
                if a.name == 'VALARM' and self._can_handle_alarm(a)]

    def update_alarms(self, alarms):
        """
        Replaces all alarms in the event that can be handled with the ones provided.
        """
        components = self._vevents[self.ref].subcomponents
        # remove all alarms that we can handle from the subcomponents
        components = [c for c in components
                      if not (c.name == 'VALARM' and self._can_handle_alarm(c))]
        # add all alarms we could handle from the input
        for alarm in alarms:
            new = icalendar.Alarm()
            new.add('ACTION', 'DISPLAY')
            new.add('TRIGGER', alarm[0])
            new.add('DESCRIPTION', alarm[1])
            components.append(new)
        self._vevents[self.ref].subcomponents = components

    @property
    def location(self):
        return self._vevents[self.ref].get('LOCATION', '')

    def update_location(self, location):
        self._vevents[self.ref]['LOCATION'] = location

    @property
    def categories(self):
        return self._vevents[self.ref].get('CATEGORIES', '')

    def update_categories(self, categories):
        if categories.strip():
            self._vevents[self.ref]['CATEGORIES'] = categories
        else:
            self._vevents[self.ref].pop('CATEGORIES', False)

    @property
    def description(self):
        return self._vevents[self.ref].get('DESCRIPTION', '')

    def update_description(self, description):
        self._vevents[self.ref]['DESCRIPTION'] = description

    @property
    def _recur_str(self):
        if self.recurring:
            recurstr = self.symbol_strings['recurring']
        else:
            recurstr = ''
        return recurstr

    def relative_to(self, day, full=False):
        """
        returns a short description of the event, with start and end
        relative to `day`

        print information in regards to this day, if the event starts and ends
        on this day, the start and end time will be given (only the description
        for all day events), otherwise arrows will indicate if the events
        started before `day` and/or lasts longer.

        :param day: the date the description is relative to
        :type day: datetime.date
        :return: compact description of Event
        :rtype: unicode()
        """
        if isinstance(day, datetime) or not isinstance(day, date):
            raise ValueError('`this_date` is of type `{}`, should be '
                             '`datetime.date`'.format(type(day)))

        day_start = self._locale['local_timezone'].localize(datetime.combine(day, time.min))
        day_end = self._locale['local_timezone'].localize(datetime.combine(day, time.max))

        tostr = '-'
        if self.start_local < day_start:
            startstr = self.symbol_strings['right_arrow'] + ' '
            tostr = ''
        else:
            startstr = self.start_local.strftime(self._locale['timeformat'])

        start_of_next_day = day_start + timedelta(days=1)
        if (self.end_local == start_of_next_day and self._locale['timeformat'] == '%H:%M'):
            endstr = '24:00'
        elif self.end_local > day_end:
            endstr = self.symbol_strings['right_arrow'] + ' '
            tostr = ''
        else:
            endstr = self.end_local.strftime(self._locale['timeformat'])

        body = self.summary
        if full:
            if self.description.strip() != '':
                body += ', ' + self.description.strip()
            if self.location.strip() != '':
                body += ', ' + self.location.strip()
            if self.categories.strip() != '':
                body += ', ' + self.categories.strip()

        comps = [startstr + tostr + endstr + ':', body, self._recur_str]
        return ' '.join(filter(bool, comps))

    def format(self, format_string, relative_to, env={}, colors=True):
        """
        :param colors: determines if colors codes should be printed or not
        :type colors: bool
        """
        attributes = defaultdict(str)
        try:
            relative_to_start, relative_to_end = relative_to
        except TypeError:
            relative_to_start = relative_to
            relative_to_end = relative_to

        # TODO make sure relative_to is always date or (date, date)
        if isinstance(relative_to_end, datetime):
            relative_to_end = relative_to_end.date()
        if isinstance(relative_to_start, datetime):
            relative_to_start = relative_to_start.date()

        day_start = datetime_fillin(relative_to_start, end=False, locale=self._locale)
        day_end = datetime_fillin(relative_to_end, locale=self._locale)
        self_start = datetime_fillin(self.start_local, locale=self._locale, end=False)
        self_end = datetime_fillin(self.end_local, locale=self._locale)

        allday = isinstance(self, AllDayEvent)

        attributes["start"] = self_start.strftime(self._locale['datetimeformat'])
        attributes["start-long"] = self_start.strftime(self._locale['longdatetimeformat'])
        attributes["start-date"] = self_start.strftime(self._locale['dateformat'])
        attributes["start-date-long"] = self_start.strftime(self._locale['longdateformat'])
        attributes["start-time"] = self_start.strftime(self._locale['timeformat'])

        attributes["end"] = self_end.strftime(self._locale['datetimeformat'])
        attributes["end-long"] = self_end.strftime(self._locale['longdatetimeformat'])
        attributes["end-date"] = self_end.strftime(self._locale['dateformat'])
        attributes["end-date-long"] = self_end.strftime(self._locale['longdateformat'])
        attributes["end-time"] = self_end.strftime(self._locale['timeformat'])

        # should only have time attributes at this point (start/end)
        full = {}
        for attr in attributes:
            full[attr + "-full"] = attributes[attr]
        attributes.update(full)

        if allday:
            attributes["start"] = attributes["start-date"]
            attributes["start-long"] = attributes["start-date-long"]
            attributes["start-time"] = ""
            attributes["end"] = attributes["end-date"]
            attributes["end-long"] = attributes["end-date-long"]
            attributes["end-time"] = ""

        tostr = ""
        if self_start < day_start:
            attributes["start-style"] = self.symbol_strings["right_arrow"]
        elif self_start == day_start:
            attributes["start-style"] = self.symbol_strings['range_start']
        else:
            attributes["start-style"] = attributes["start-time"]
            tostr = "-"

        midnight_end = day_end.time() == time.max and self_end.time() == time.min and\
                       self_end.date() - timedelta(days=1) == day_end.date()
        if self_end == day_end or midnight_end:
            attributes["end-style"] = self.symbol_strings["range_end"]
            tostr = ""
        elif self_end > day_end:
            attributes["end-style"] = self.symbol_strings["right_arrow"]
            tostr = ""
        else:
            attributes["end-style"] = attributes["end-time"]

        attributes["to-style"] = tostr
        if self_start < day_start and self_end > day_end:
            attributes["start-end-time-style"] = self.symbol_strings["range"]
        elif allday:
            if self_start == day_start:
                attributes["start-end-time-style"] = attributes["start-style"]
                if self_end == day_end:
                    attributes["start-end-time-style"] = ''
            elif self_end == day_end:
                attributes["start-end-time-style"] = attributes["end-style"]
            else:
                attributes["start-end-time-style"] = ""
        else:
            attributes["start-end-time-style"] = attributes["start-style"] + \
                attributes["to-style"] + attributes["end-style"]

        attributes["recurse"] = self._recur_str
        attributes["repeat-pattern"] = self.recurpattern
        attributes["title"] = self.summary
        attributes["description"] = self.description.strip()
        attributes["description-separator"] = ""
        if attributes["description"]:
            attributes["description-separator"] = " :: "
        attributes["location"] = self.location.strip()
        attributes["all-day"] = allday
        attributes["categories"] = self.categories

        if "calendars" in env and self.calendar in env["calendars"]:
            cal = env["calendars"][self.calendar]
            attributes["calendar-color"] = get_color(cal.get('color', ''))
            attributes["calendar"] = cal.get("displayname", self.calendar)

        if colors:
            color_styles = {"reset": style("", reset=True), "bold": style("", bold=True, reset=False)}
            for c in ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]:
                color_styles[c] = style("", reset=False, fg=c)
                color_styles[c + "-bold"] = style("", reset=False, fg=c, bold=True)
            attributes.update(color_styles)
        try:
            return format_string.format(**attributes) + attributes["reset"]
        except (KeyError, IndexError):
            raise KeyError("cannot format event with: %s" % format_string)

    @property
    def event_description(self):   # XXX rename me
        """complete description of this event in text form

        :rtype: str
        :returns: event description
        """

        location = '\nLocation: ' + self.location if self.location != '' else ''
        description = '\nDescription: ' + self.description if \
            self.description != '' else ''
        categories = '\nCategories: ' + self.categories if self.categories != '' else ''
        repitition = '\nRepeat: ' + self.recurpattern if \
            self.recurpattern != '' else ''

        return '{}: {}{}{}{}'.format(
            self._rangestr, self.summary, location, categories, repitition, description)

    def duplicate(self):
        """duplicate this event's PROTO event

        :rtype: Event
        """
        new_uid = generate_random_uid()
        vevent = self._vevents['PROTO'].copy()
        vevent['SEQUENCE'] = 0
        vevent['UID'] = icalendar.vText(new_uid)
        vevent['SUMMARY'] = icalendar.vText(vevent['SUMMARY'] + ' Copy')
        event = self.fromVEvents([vevent])
        event.calendar = self.calendar
        return event

    def delete_instance(self, instance):
        """delete an instance from this event"""
        assert self.recurring
        delete_instance(self._vevents['PROTO'], instance)

        # in case the instance we want to delete is specified as a RECURRENCE-ID
        # event, we should delete that as well
        to_pop = list()
        for key in self._vevents:
            if key == 'PROTO':
                continue
            try:
                if self._vevents[key].get('RECURRENCE-ID').dt == instance:
                    to_pop.append(key)
            except TypeError:  # localized/floating datetime mismatch
                continue
        for key in to_pop:
            self._vevents.pop(key)


class DatetimeEvent(Event):
    @property
    def _rangestr(self):
        # same day
        if self.start_local.utctimetuple()[:3] == self.end_local.utctimetuple()[:3]:
            starttime = self.start_local.strftime(self._locale['timeformat'])
            endtime = self.end_local.strftime(self._locale['timeformat'])
            datestr = self.end_local.strftime(self._locale['longdateformat'])
            rangestr = starttime + '-' + endtime + ' ' + datestr
        else:
            startstr = self.start_local.strftime(self._locale['longdatetimeformat'])
            endstr = self.end_local.strftime(self._locale['longdatetimeformat'])
            rangestr = startstr + ' - ' + endstr
        return rangestr


class LocalizedEvent(DatetimeEvent):
    """
    see parent
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        starttz = getattr(self._vevents[self.ref]['DTSTART'].dt, 'tzinfo', None)
        if starttz is None:
            starttz = self._locale['default_timezone']
        try:
            endtz = getattr(self._vevents[self.ref]['DTEND'].dt, 'tzinfo', None)
        except KeyError:
            endtz = starttz
        if endtz is None:
            endtz = self._locale['default_timezone']
        try:
            self._start = self._start.astimezone(starttz)
            self._end = self._end.astimezone(endtz)
        except ValueError:
            self._start = starttz.localize(self._start)
            self._end = endtz.localize(self._end)

    @property
    def start_local(self):
        """
        see parent
        """
        return self.start.astimezone(self._locale['local_timezone'])

    @property
    def end_local(self):
        """
        see parent
        """
        return self.end.astimezone(self._locale['local_timezone'])


class FloatingEvent(DatetimeEvent):
    """
    """
    allday = False

    @property
    def start_local(self):
        return self._locale['local_timezone'].localize(self.start)

    @property
    def end_local(self):
        return self._locale['local_timezone'].localize(self.end)


class AllDayEvent(Event):
    allday = True

    @property
    def end(self):
        end = super(AllDayEvent, self).end
        if end == self.start:
            # https://github.com/pimutils/khal/issues/129
            logger.warning('{} ("{}"): The event\'s end date property '
                           'contains the same value as the start date, '
                           'which is invalid as per RFC 2445. Khal will '
                           'assume this is meant to be single-day event '
                           'on {}'.format(self.href, self.summary, self.start))
            end += timedelta(days=1)
        return end - timedelta(days=1)

    def relative_to(self, day, full=False):
        if self.start > day or self.end < day:
            raise ValueError('Day out of range: {}'
                             .format(dict(day=day, start=self.start,
                                          end=self.end)))
        elif self.start < day and self.end > day:
            # event starts before and goes on longer than `day`:
            rangestr = self.symbol_strings['range']
        elif self.start < day:
            # event started before `day`
            rangestr = self.symbol_strings['range_end']
        elif self.end > day:
            # event goes on longer than `day`
            rangestr = self.symbol_strings['range_start']
        elif self.start == self.end == day:
            # only on `day`
            rangestr = ''

        body = self.summary
        if full:
            if self.description.strip() != '':
                body += ', ' + self.description.strip()
            if self.categories.strip() != '':
                body += ', ' + self.categories.strip()
            if self.location.strip() != '':
                body += ', ' + self.location.strip()

        return ' '.join(filter(bool, (rangestr, body, self._recur_str)))

    @property
    def _rangestr(self):
        if self.start_local == self.end_local:
            rangestr = self.start_local.strftime(self._locale['longdateformat'])
        else:
            if self.start_local.year == self.end_local.year:
                startstr = self.start_local.strftime(self._locale['dateformat'])
            else:
                startstr = self.start_local.strftime(self._locale['longdateformat'])
            endstr = self.end_local.strftime(self._locale['longdateformat'])
            rangestr = startstr + ' - ' + endstr
        return rangestr


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

    first_date = datetime.today() if not first_date else to_naive_utc(first_date)
    last_date = datetime.today() if not last_date else to_naive_utc(last_date)
    timezone = icalendar.Timezone()
    timezone.add('TZID', tz)

    dst = {
        one[2]: 'DST' in two.__repr__()
        for one, two in iter(tz._tzinfos.items())
    }
    bst = {
        one[2]: 'BST' in two.__repr__()
        for one, two in iter(tz._tzinfos.items())
    }

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

        if dst[name] or bst[name]:
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


class EventStandIn():
    def __init__(self, calendar):
        self.calendar = calendar
        self.color = None
        self.unicode_symbols = None
        self.readonly = None
