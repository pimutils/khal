# Copyright (c) 2013-2022 khal contributors
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

"""This module contains the event model with all relevant subclasses and some
helper functions."""

import datetime as dt
import logging
import os
from typing import Callable, Optional, Union

import icalendar
import icalendar.cal
import icalendar.prop
import pytz
from click import style
from pytz.tzinfo import StaticTzInfo

from ..custom_types import LocaleConfiguration
from ..exceptions import FatalError
from ..icalendar import cal_from_ics, delete_instance, invalid_timezone
from ..parse_datetime import timedelta2str
from ..plugins import FORMATTERS
from ..utils import generate_random_uid, is_aware, to_naive_utc, to_unix_time

logger = logging.getLogger('khal')


class Event:
    """base Event class for representing a *recurring instance* of an Event

    (in case of non-recurring events this distinction is irrelevant)
    We keep a copy of this instances start and end time around, because for recurring
    events it might be costly to expand the recursion rules

    important distinction for AllDayEvents:
        all end times are as presented to a user, i.e. an event scheduled for
        only one day will have the same start and end date (even though the
        icalendar standard would have the end date be one day later)
    """
    allday: bool = False

    def __init__(self,
                 vevents: dict[str, icalendar.Event],
                 locale: LocaleConfiguration,
                 ref: Optional[str] = None,
                 readonly: bool = False,
                 href: Optional[str] = None,
                 etag: Optional[str] = None,
                 calendar: Optional[str] = None,
                 color: Optional[str] = None,
                 start: Optional[dt.datetime] = None,
                 end: Optional[dt.datetime] = None,
                 addresses: Optional[list[str]] =None,
                 ):
        """
        :param start: start datetime of this event instance
        :param end: end datetime of this event instance
        """
        if self.__class__.__name__ == 'Event':
            raise ValueError('do not initialize this class directly')
        if ref is None:
            raise ValueError('ref should not be None')
        self._vevents = vevents
        self.ref = ref
        self._locale = locale
        self.readonly = readonly
        self.href = href
        self.etag = etag
        self.calendar = calendar if calendar else ''
        self.color = color
        self._start: dt.datetime
        self._end: dt.datetime
        self.addresses = addresses if addresses else []

        if start is None:
            self._start = self._vevents[self.ref]['DTSTART'].dt
        else:
            self._start = start
        if end is None:
            try:
                self._end = self._vevents[self.ref]['DTEND'].dt
            except KeyError:
                try:
                    self._end = self._start + self._vevents[self.ref]['DURATION'].dt
                except KeyError:
                    self._end = self._start + dt.timedelta(days=1)
        else:
            self._end = end

    @classmethod
    def _get_type_from_vDDD(cls, start: icalendar.prop.vDDDTypes) -> type:
        """infere the type of the class from the START type of the event"""
        if not isinstance(start.dt, dt.datetime):
            return AllDayEvent
        if 'TZID' in start.params or start.dt.tzinfo is not None:
            return LocalizedEvent
        return FloatingEvent

    @classmethod
    def _get_type_from_date(cls, start: dt.datetime) -> type['Event']:
        if hasattr(start, 'tzinfo') and start.tzinfo is not None:
            cls = LocalizedEvent
        elif isinstance(start, dt.datetime):
            cls = FloatingEvent
        elif isinstance(start, dt.date):
            cls = AllDayEvent
        return cls

    @classmethod
    def fromVEvents(cls,
                    events_list: list[icalendar.Event],
                    ref: Optional[str]=None,
                    start: Optional[dt.datetime]=None,
                    **kwargs) -> 'Event':
        assert isinstance(events_list, list)

        vevents = {}
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
            ref = 'PROTO' if ref in vevents.keys() else list(vevents.keys())[0]
        try:
            if type(vevents[ref]['DTSTART'].dt) != type(vevents[ref]['DTEND'].dt):  # noqa: E721
                raise ValueError('DTSTART and DTEND should be of the same type (datetime or date)')
        except KeyError:
            pass

        if start:
            instcls = cls._get_type_from_date(start)
        else:
            instcls = cls._get_type_from_vDDD(vevents[ref]['DTSTART'])
        return instcls(vevents, ref=ref, start=start, **kwargs)

    @classmethod
    def fromString(cls, ics: str, ref=None, **kwargs) -> 'Event':
        calendar_collection = cal_from_ics(ics)
        events = [item for item in calendar_collection.walk() if item.name == 'VEVENT']
        return cls.fromVEvents(events, ref, **kwargs)

    def __lt__(self, other: 'Event') -> bool:
        start = self.start_local
        other_start = other.start_local
        if isinstance(start, dt.date) and not isinstance(start, dt.datetime):
            start = dt.datetime.combine(start, dt.time.min)

        if isinstance(other_start, dt.date) and not isinstance(other_start, dt.datetime):
            other_start = dt.datetime.combine(other_start, dt.time.min)

        start = start.replace(tzinfo=None)
        other_start = other_start.replace(tzinfo=None)

        if start == other_start:
            end = self.end_local
            other_end = other.end_local
            if isinstance(end, dt.date) and not isinstance(end, dt.datetime):
                end = dt.datetime.combine(end, dt.time.min)

            if isinstance(other_end, dt.date) and not isinstance(other_end, dt.datetime):
                other_end = dt.datetime.combine(other_end, dt.time.min)

            end = end.replace(tzinfo=None)
            other_end = other_end.replace(tzinfo=None)

            if end == other_end:
                return self.summary < other.summary

            try:
                return end < other_end
            except TypeError:
                raise ValueError(f'Cannot compare events {end} and {other_end}')

        try:
            return start < other_start
        except TypeError:
            raise ValueError(f'Cannot compare events {start} and {other_start}')

    def update_start_end(self, start: dt.datetime, end: dt.datetime) -> None:
        """update start and end time of this event

        calling this on a recurring event will lead to the proto instance
        be set to the new start and end times

        beware, this methods performs some open heart surgery
        """
        if type(start) != type(end):
            raise ValueError('DTSTART and DTEND should be of the same type (datetime or date)')
        self.__class__ = self._get_type_from_date(start)

        self._vevents[self.ref].pop('DTSTART')
        self._vevents[self.ref].add('DTSTART', start)
        self._start = start
        if not isinstance(end, dt.datetime):
            end = end + dt.timedelta(days=1)
        self._end = end
        if 'DTEND' in self._vevents[self.ref]:
            self._vevents[self.ref].pop('DTEND')
            self._vevents[self.ref].add('DTEND', end)
        else:
            self._vevents[self.ref].pop('DURATION')
            self._vevents[self.ref].add('DURATION', end - start)

    @property
    def recurring(self) -> bool:
        try:
            rval = 'RRULE' in self._vevents[self.ref] or \
                'RECURRENCE-ID' in self._vevents[self.ref] or \
                'RDATE' in self._vevents[self.ref]
        except KeyError:
            logger.fatal(
                f"The event at {self.href} might be broken. You might want to "
                "file an issue at https://github.com/pimutils/khal/issues"
            )
            raise
        else:
            return rval

    @property
    def recurpattern(self) -> str:
        if 'RRULE' in self._vevents[self.ref]:
            return self._vevents[self.ref]['RRULE'].to_ical().decode('utf-8')
        else:
            return ''

    @property
    def recurobject(self) -> icalendar.vRecur:
        if 'RRULE' in self._vevents[self.ref]:
            return self._vevents[self.ref]['RRULE']
        else:
            return icalendar.vRecur()

    def update_rrule(self, rrule: str) -> None:
        self._vevents['PROTO'].pop('RRULE')
        if rrule is not None:
            self._vevents['PROTO'].add('RRULE', rrule)

    @property
    def recurrence_id(self) -> Union[dt.datetime, str]:
        """return the "original" start date of this event (i.e. their recurrence-id)
        """
        if self.ref == 'PROTO':
            return self.start
        else:
            return pytz.UTC.localize(dt.datetime.utcfromtimestamp(int(self.ref)))

    def increment_sequence(self) -> None:
        """update the SEQUENCE number, call before saving this event"""
        # TODO we might want to do this automatically in raw() everytime
        # the event has changed, this will f*ck up the tests though
        try:
            self._vevents[self.ref]['SEQUENCE'] += 1
        except KeyError:
            self._vevents[self.ref]['SEQUENCE'] = 0

    @property
    def symbol_strings(self) -> dict[str, str]:
        if self._locale['unicode_symbols']:
            return {
                'recurring': '\N{Clockwise gapped circle arrow}',
                'alarming': '\N{Alarm clock}',
                'range': '\N{Left right arrow}',
                'range_end': '\N{Rightwards arrow to bar}',
                'range_start': '\N{Rightwards arrow from bar}',
                'right_arrow': '\N{Rightwards arrow}',
                'cancelled': '\N{Cross mark}',
                'confirmed': '\N{Heavy check mark}',
                'tentative': '?',
                'declined': '\N{Cross mark}',
                'accepted': '\N{Heavy check mark}',
            }
        else:
            return {
                'recurring': '(R)',
                'alarming': '(A)',
                'range': '<->',
                'range_end': '->|',
                'range_start': '|->',
                'right_arrow': '->',
                'cancelled': 'X',
                'confirmed': 'V',
                'tentative': '?',
                'declined': 'X',
                'accepted': 'V',
            }

    @property
    def start_local(self) -> dt.datetime:
        """self.start() localized to local timezone"""
        return self.start

    @property
    def end_local(self) -> dt.datetime:
        """self.end() localized to local timezone"""
        return self.end

    @property
    def start(self) -> dt.datetime:
        """this should return the start date(time) as saved in the event"""
        return self._start

    @property
    def end(self) -> dt.datetime:
        """this should return the end date(time) as saved in the event or
        implicitly defined by start and duration"""
        return self._end

    @property
    def duration(self) -> dt.timedelta:
        try:
            return self._vevents[self.ref]['DURATION'].dt
        except KeyError:
            return self.end - self.start

    @property
    def uid(self) -> str:
        return self._vevents[self.ref]['UID']

    @property
    def organizer(self) -> str:
        if 'ORGANIZER' not in self._vevents[self.ref]:
            return ''
        organizer = self._vevents[self.ref]['ORGANIZER']
        cn = organizer.params.get('CN', '')
        email = organizer.split(':')[-1]
        if cn:
            return f'{cn} ({email})'
        else:
            return email

    @property
    def url(self) -> str:
        if 'URL' not in self._vevents[self.ref]:
            return ''
        return self._vevents[self.ref]['URL']

    def update_url(self, url: str) -> None:
        if url:
            self._vevents[self.ref]['URL'] = url
        else:
            self._vevents[self.ref].pop('URL')

    @staticmethod
    def _create_calendar() -> icalendar.Calendar:
        """create the calendar"""
        calendar = icalendar.Calendar()
        calendar.add('version', '2.0')
        calendar.add(
            'prodid', '-//PIMUTILS.ORG//NONSGML khal / icalendar //EN'
        )
        return calendar

    @property
    def raw(self) -> str:
        """Creates a VCALENDAR containing VTIMEZONEs
        """
        calendar = self._create_calendar()
        tzs = []
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

    def export_ics(self, path: str) -> None:
        """export event as ICS
        """
        export_path = os.path.expanduser(path)
        with open(export_path, 'w') as fh:
            fh.write(self.raw)

    @property
    def summary(self) -> str:
        description = None
        date = self._vevents[self.ref].get('x-birthday', None)
        if date:
            description = 'birthday'
        else:
            date = self._vevents[self.ref].get('x-anniversary', None)
            if date:
                description = 'anniversary'
            else:
                date = self._vevents[self.ref].get('x-abdate', None)
                if date:
                    description = self._vevents[self.ref].get('x-ablabel', 'custom event')

        if date:
            number = self.start_local.year - int(date[:4])
            name = self._vevents[self.ref].get('x-fname', None)
            if int(date[4:6]) == 2 and int(date[6:8]) == 29:
                leap = ' (29th of Feb.)'
            else:
                leap = ''
            if (number - 1) % 10 == 0 and number != 11:
                suffix = 'st'
            elif (number - 2) % 10 == 0 and number != 12:
                suffix = 'nd'
            elif (number - 3) % 10 == 0 and number != 13:
                suffix = 'rd'
            else:
                suffix = 'th'
            return f'{name}\'s {number}{suffix} {description}{leap}'
        else:
            return self._vevents[self.ref].get('SUMMARY', '')

    def update_summary(self, summary: str) -> None:
        self._vevents[self.ref]['SUMMARY'] = summary

    @staticmethod
    def _can_handle_alarm(alarm) -> bool:
        """
        Decides whether we can handle a certain alarm.
        """
        return alarm.get('ACTION') == 'DISPLAY' and \
            isinstance(alarm.get('TRIGGER').dt, dt.timedelta)

    @property
    def alarms(self) -> list[tuple[dt.timedelta, str]]:
        """
        Returns a list of all alarms in th original event that we can handle. Unknown types of
        alarms are ignored.
        """
        return [(a.get('TRIGGER').dt, a.get('DESCRIPTION'))
                for a in self._vevents[self.ref].subcomponents
                if a.name == 'VALARM' and self._can_handle_alarm(a)]

    def update_alarms(self, alarms: list[tuple[dt.timedelta, str]]) -> None:
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
    def location(self) -> str:
        return self._vevents[self.ref].get('LOCATION', '')

    def update_location(self, location: str) -> None:
        if location:
            self._vevents[self.ref]['LOCATION'] = location
        else:
            self._vevents[self.ref].pop('LOCATION')

    @property
    def attendees(self) -> str:
        addresses = self._vevents[self.ref].get('ATTENDEE', [])
        if not isinstance(addresses, list):
            addresses = [addresses, ]
        return ", ".join([address.split(':')[-1]
                          for address in addresses])

    def update_attendees(self, attendees: list[str]):
        assert isinstance(attendees, list)
        attendees = [a.strip().lower() for a in attendees if a != ""]
        if len(attendees) > 0:
            # first check for overlaps in existing attendees.
            # Existing vCalAddress objects will be copied, non-existing
            # vCalAddress objects will be created and appended.
            old_attendees = self._vevents[self.ref].get('ATTENDEE', [])
            unchanged_attendees = []
            vCalAddresses = []
            for attendee in attendees:
                for old_attendee in old_attendees:
                    old_email = old_attendee.lstrip("MAILTO:").lower()
                    if attendee == old_email:
                        vCalAddresses.append(old_attendee)
                        unchanged_attendees.append(attendee)
            for attendee in [a for a in attendees if a not in unchanged_attendees]:
                item = icalendar.prop.vCalAddress(f'MAILTO:{attendee}')
                item.params['ROLE'] = icalendar.prop.vText('REQ-PARTICIPANT')
                item.params['PARTSTAT'] = icalendar.prop.vText('NEEDS-ACTION')
                item.params['CUTYPE'] = icalendar.prop.vText('INDIVIDUAL')
                item.params['RSVP'] = icalendar.prop.vText('TRUE')
                # TODO use khard here to receive full information from email address
                vCalAddresses.append(item)

            self._vevents[self.ref]['ATTENDEE'] = vCalAddresses
        else:
            self._vevents[self.ref].pop('ATTENDEE')

    @property
    def categories(self) -> str:
        try:
            return self._vevents[self.ref].get('CATEGORIES', '').to_ical().decode('utf-8')
        except AttributeError:
            return ''

    def update_categories(self, categories: list[str]) -> None:
        assert isinstance(categories, list)
        categories = [c.strip() for c in categories if c != ""]
        self._vevents[self.ref].pop('CATEGORIES', False)
        if categories:
            self._vevents[self.ref].add('CATEGORIES', categories)

    @property
    def description(self) -> str:
        return self._vevents[self.ref].get('DESCRIPTION', '')

    def update_description(self, description: str):
        if description:
            self._vevents[self.ref]['DESCRIPTION'] = description
        else:
            self._vevents[self.ref].pop('DESCRIPTION')

    @property
    def _recur_str(self) -> str:
        if self.recurring:
            recurstr = ' ' + self.symbol_strings['recurring']
        else:
            recurstr = ''
        return recurstr

    @property
    def _alarm_str(self) -> str:
        if self.alarms:
            alarmstr = ' ' + self.symbol_strings['alarming']
        else:
            alarmstr = ''
        return alarmstr

    @property
    def _status_str(self) -> str:
        if self.status == 'CANCELLED':
            statusstr = self.symbol_strings['cancelled']
        elif self.status == 'TENTATIVE':
            statusstr = self.symbol_strings['tentative']
        elif self.status == 'CONFIRMED':
            statusstr = self.symbol_strings['confirmed']
        else:
            statusstr = ''
        return statusstr

    @property
    def _partstat_str(self) -> str:
        partstat = self.partstat
        if partstat == 'ACCEPTED':
            partstatstr = self.symbol_strings['accepted']
        elif partstat == 'TENTATIVE':
            partstatstr = self.symbol_strings['tentative']
        elif partstat == 'DECLINED':
            partstatstr = self.symbol_strings['declined']
        else:
            partstatstr = ''
        return partstatstr

    def attributes(
            self,
            relative_to: Union[tuple[dt.date, dt.date], dt.date],
            env=None,
            colors: bool=True,
    ):
        """
        :param colors: determines if colors codes should be printed or not
        """
        env = env or {}

        attributes = {}
        if isinstance(relative_to, tuple):
            relative_to_start, relative_to_end = relative_to
        else:
            relative_to_start = relative_to_end = relative_to

        if isinstance(relative_to_end, dt.datetime):
            relative_to_end = relative_to_end.date()
        if isinstance(relative_to_start, dt.datetime):
            relative_to_start = relative_to_start.date()

        if isinstance(self.start_local, dt.datetime):
            start_local_datetime = self.start_local
            end_local_datetime = self.end_local
        else:
            start_local_datetime = self._locale['local_timezone'].localize(
                dt.datetime.combine(self.start, dt.time.min))
            end_local_datetime = self._locale['local_timezone'].localize(
                dt.datetime.combine(self.end, dt.time.min))

        day_start = self._locale['local_timezone'].localize(
            dt.datetime.combine(relative_to_start, dt.time.min),
        )
        day_end = self._locale['local_timezone'].localize(
            dt.datetime.combine(relative_to_end, dt.time.max),
        )
        next_day_start = day_start + dt.timedelta(days=1)

        allday = isinstance(self, AllDayEvent)

        attributes["start"] = self.start_local.strftime(self._locale['datetimeformat'])
        attributes["start-long"] = self.start_local.strftime(self._locale['longdatetimeformat'])
        attributes["start-date"] = self.start_local.strftime(self._locale['dateformat'])
        attributes["start-date-long"] = self.start_local.strftime(self._locale['longdateformat'])
        attributes["start-time"] = self.start_local.strftime(self._locale['timeformat'])

        attributes["end"] = self.end_local.strftime(self._locale['datetimeformat'])
        attributes["end-long"] = self.end_local.strftime(self._locale['longdatetimeformat'])
        attributes["end-date"] = self.end_local.strftime(self._locale['dateformat'])
        attributes["end-date-long"] = self.end_local.strftime(self._locale['longdateformat'])
        attributes["end-time"] = self.end_local.strftime(self._locale['timeformat'])

        attributes["duration"] = timedelta2str(self.duration)

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
        if self.start_local.timetuple() < relative_to_start.timetuple():
            attributes["start-style"] = self.symbol_strings["right_arrow"]
        elif self.start_local.timetuple() == relative_to_start.timetuple():
            attributes["start-style"] = self.symbol_strings['range_start']
        else:
            attributes["start-style"] = attributes["start-time"]
            tostr = "-"

        if end_local_datetime in [day_end, next_day_start]:
            if self._locale["timeformat"] == '%H:%M':
                attributes["end-style"] = '24:00'
                tostr = '-'
            else:
                attributes["end-style"] = self.symbol_strings["range_end"]
                tostr = ""
        elif end_local_datetime > day_end:
            attributes["end-style"] = self.symbol_strings["right_arrow"]
            tostr = ""
        else:
            attributes["end-style"] = attributes["end-time"]

        if self.start < self.end:
            attributes["to-style"] = '-'
        else:
            attributes["to-style"] = ''

        if start_local_datetime < day_start and end_local_datetime > day_end:
            attributes["start-end-time-style"] = self.symbol_strings["range"]
        else:
            attributes["start-end-time-style"] = attributes["start-style"] + \
                tostr + attributes["end-style"]

        if allday:
            if self.start == self.end:
                attributes['start-end-time-style'] = ''
            elif self.start == relative_to_start and self.end > relative_to_end:
                attributes['start-end-time-style'] = self.symbol_strings['range_start']
            elif self.start < relative_to_start and self.end > relative_to_end:
                attributes['start-end-time-style'] = self.symbol_strings['range']
            elif self.start < relative_to_start and self.end == relative_to_end:
                attributes['start-end-time-style'] = self.symbol_strings['range_end']
            else:
                attributes['start-end-time-style'] = ''

        if allday:
            attributes['end-necessary'] = ''
            attributes['end-necessary-long'] = ''
            if self.start_local != self.end_local:
                attributes['end-necessary'] = attributes['end-date']
                attributes['end-necessary-long'] = attributes['end-date-long']
        else:
            attributes['end-necessary'] = attributes['end-time']
            attributes['end-necessary-long'] = attributes['end-time']
            if self.start_local.date() != self.end_local.date():
                attributes['end-necessary'] = attributes['end']
                attributes['end-necessary-long'] = attributes['end-long']

        attributes["repeat-symbol"] = self._recur_str
        attributes["repeat-pattern"] = self.recurpattern
        attributes["alarm-symbol"] = self._alarm_str
        attributes["status-symbol"] = self._status_str
        attributes["partstat-symbol"] = self._partstat_str
        attributes["title"] = self.summary
        attributes["organizer"] = self.organizer.strip()

        formatters = FORMATTERS.values()
        if len(formatters) == 1:
            fmt: Callable[[str], str] = list(formatters)[0]
        else:
            def fmt(s: str) -> str: return s.strip()

        attributes["description"] = fmt(self.description)
        attributes["description-separator"] = ""
        if attributes["description"]:
            attributes["description-separator"] = " :: "
        attributes["location"] = self.location.strip()
        attributes["attendees"] = self.attendees
        attributes["all-day"] = str(allday)
        attributes["categories"] = self.categories
        attributes['uid'] = self.uid
        attributes['url'] = self.url
        attributes['url-separator'] = ""
        if attributes['url']:
            attributes['url-separator'] = " :: "

        if "calendars" in env and self.calendar in env["calendars"]:
            cal = env["calendars"][self.calendar]
            attributes["calendar-color"] = cal.get('color', '')
            attributes["calendar"] = cal.get("displayname", self.calendar)
        else:
            attributes["calendar-color"] = attributes["calendar"] = ''
            attributes["calendar"] = self.calendar

        if colors:
            attributes['reset'] = style('', reset=True)
            attributes['bold'] = style('', bold=True, reset=False)
            for c in ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]:
                attributes[c] = style("", reset=False, fg=c)
                attributes[c + "-bold"] = style("", reset=False, fg=c, bold=True)
        else:
            attributes['reset'] = attributes['bold'] = ''
            for c in ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]:
                attributes[c] = attributes[c + '-bold'] = ''

        attributes['nl'] = '\n'
        attributes['tab'] = '\t'
        attributes['bell'] = '\a'

        attributes['status'] = self.status + ' ' if self.status else ''
        attributes['cancelled'] = 'CANCELLED ' if self.status == 'CANCELLED' else ''
        return attributes

    def duplicate(self) -> 'Event':
        """duplicate this event's PROTO event"""
        new_uid = generate_random_uid()
        vevent = self._vevents['PROTO'].copy()
        vevent['SEQUENCE'] = 0
        vevent['UID'] = icalendar.vText(new_uid)
        vevent['SUMMARY'] = icalendar.vText(vevent['SUMMARY'] + ' Copy')
        event = self.fromVEvents([vevent], locale=self._locale)
        event.calendar = self.calendar
        event._locale = self._locale
        return event

    def delete_instance(self, instance: dt.datetime) -> None:
        """delete an instance from this event

        we don't check, if that instance is an instance of the recurrence rules
        defined in the event
        """
        assert self.recurring
        delete_instance(self._vevents['PROTO'], instance)

        # in case the instance we want to delete is specified as a RECURRENCE-ID
        # event, we should delete that as well
        to_pop = []
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

    @property
    def status(self) -> str:
        return self._vevents[self.ref].get('STATUS', '')

    @property
    def partstat(self) -> Optional[str]:
        for attendee in self._vevents[self.ref].get('ATTENDEE', []):
            for address in self.addresses:
                if attendee == 'mailto:' + address:
                    return attendee.params.get('PARTSTAT', '')
        return None


class DatetimeEvent(Event):
    pass


class LocalizedEvent(DatetimeEvent):
    """
    see parent
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        try:
            starttz = getattr(self._vevents[self.ref]['DTSTART'].dt, 'tzinfo', None)
        except KeyError:
            msg = (
                f"Cannot understand event {kwargs.get('href')} from "
                f"calendar {kwargs.get('calendar')}, you might want to file an issue at "
                "https://github.com/pimutils/khal/issues"
            )
            logger.fatal(msg)
            raise FatalError(  # because in ikhal you won't see the logger's output
                msg
            )

        if starttz is None:
            starttz = self._locale['default_timezone']
        try:
            endtz = getattr(self._vevents[self.ref]['DTEND'].dt, 'tzinfo', None)
        except KeyError:
            endtz = starttz
        if endtz is None:
            endtz = self._locale['default_timezone']

        if is_aware(self._start):
            self._start = self._start.astimezone(starttz)
        else:
            self._start = starttz.localize(self._start)

        if is_aware(self._end):
            self._end = self._end.astimezone(endtz)
        else:
            self._end = endtz.localize(self._end)

    @property
    def start_local(self) -> dt.datetime:
        """
        see parent
        """
        return self.start.astimezone(self._locale['local_timezone'])

    @property
    def end_local(self) -> dt.datetime:
        """
        see parent
        """
        return self.end.astimezone(self._locale['local_timezone'])


class FloatingEvent(DatetimeEvent):
    """
    """
    allday: bool = False

    @property
    def start_local(self) -> dt.datetime:
        return self._locale['local_timezone'].localize(self.start)

    @property
    def end_local(self) -> dt.datetime:
        return self._locale['local_timezone'].localize(self.end)


class AllDayEvent(Event):
    allday: bool = True

    @property
    def end(self) -> dt.datetime:
        end = super().end
        if end == self.start:
            # https://github.com/pimutils/khal/issues/129
            logger.warning(f'{self.href} ("{self.summary}"): The event\'s end '
                           'date property contains the same value as the start '
                           'date, which is invalid as per RFC 5545. Khal will '
                           'assume this is meant to be a single-day event on '
                           f'{self.start}')
            end += dt.timedelta(days=1)
        return end - dt.timedelta(days=1)

    @property
    def duration(self) -> dt.timedelta:
        try:
            return self._vevents[self.ref]['DURATION'].dt
        except KeyError:
            return self.end - self.start + dt.timedelta(days=1)


def create_timezone(
    tz: pytz.BaseTzInfo,
    first_date: Optional[dt.datetime]=None,
    last_date: Optional[dt.datetime]=None
) -> icalendar.Timezone:
    """
    create an icalendar vtimezone from a pytz.tzinfo object

    :param tz: the timezone
    :param first_date: the very first datetime that needs to be included in the
    transition times, typically the DTSTART value of the (first recurring)
    event
    :param last_date: the last datetime that needs to included, typically the
    end of the (very last) event (of a recursion set)
    :returns: timezone information

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
    if isinstance(tz, StaticTzInfo):
        return _create_timezone_static(tz)

    # TODO last_date = None, recurring to infinity

    first_date = dt.datetime.today() if not first_date else to_naive_utc(first_date)
    last_date = first_date + dt.timedelta(days=1) if not last_date else to_naive_utc(last_date)
    timezone = icalendar.Timezone()
    timezone.add('TZID', tz)

    dst = {
        one[2]: 'DST' in two.__repr__()
        for one, two in iter(tz._tzinfos.items())  # type: ignore
    }
    bst = {
        one[2]: 'BST' in two.__repr__()
        for one, two in iter(tz._tzinfos.items())  # type: ignore
    }

    # looking for the first and last transition time we need to include
    first_num, last_num = 0, len(tz._utc_transition_times) - 1  # type: ignore
    first_tt = tz._utc_transition_times[0]  # type: ignore
    last_tt = tz._utc_transition_times[-1]  # type: ignore
    for num, transtime in enumerate(tz._utc_transition_times):  # type: ignore
        if first_date > transtime > first_tt:
            first_num = num
            first_tt = transtime
        if last_tt > transtime > last_date:
            last_num = num
            last_tt = transtime

    timezones: dict[str, icalendar.Component] = {}
    for num in range(first_num, last_num + 1):
        name = tz._transition_info[num][2]  # type: ignore
        if name in timezones:
            ttime = tz.fromutc(tz._utc_transition_times[num]).replace(tzinfo=None)  # type: ignore
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

        subcomp.add('TZNAME', tz._transition_info[num][2])  # type: ignore
        subcomp.add(
            'DTSTART',
            tz.fromutc(tz._utc_transition_times[num]).replace(tzinfo=None))  # type: ignore
        subcomp.add('TZOFFSETTO', tz._transition_info[num][0])  # type: ignore
        subcomp.add('TZOFFSETFROM', tz._transition_info[num - 1][0])  # type: ignore
        timezones[name] = subcomp

    for subcomp in timezones.values():
        timezone.add_component(subcomp)

    return timezone


def _create_timezone_static(tz: StaticTzInfo) -> icalendar.Timezone:
    """create an icalendar vtimezone from a StaticTzInfo

    :param tz: the timezone
    :returns: timezone information
    """
    timezone = icalendar.Timezone()
    timezone.add('TZID', tz)
    subcomp = icalendar.TimezoneStandard()
    subcomp.add('TZNAME', tz)
    subcomp.add('DTSTART', dt.datetime(1601, 1, 1))
    subcomp.add('RDATE', dt.datetime(1601, 1, 1))
    subcomp.add('TZOFFSETTO', tz._utcoffset)  # type: ignore
    subcomp.add('TZOFFSETFROM', tz._utcoffset)  # type: ignore
    timezone.add_component(subcomp)
    return timezone
