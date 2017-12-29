# Copyright (c) 2013-2017 Christian Geier et al.
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

"""collection of utility functions"""


import datetime as dt
import logging
import random
import re
import string
from calendar import month_abbr, timegm
from collections import defaultdict
from textwrap import wrap

import dateutil.rrule
import icalendar
import khal.parse_datetime as parse_datetime  # TODO get this out of here
import pytz

from .exceptions import UnsupportedRecurrence

logger = logging.getLogger('khal')


def generate_random_uid():
    """generate a random uid

    when random isn't broken, getting a random UID from a pool of roughly 10^56
    should be good enough"""
    choice = string.ascii_uppercase + string.digits
    return ''.join([random.choice(choice) for _ in range(36)])


def new_event(locale, dtstart=None, dtend=None, summary=None, timezone=None,
              allday=False, description=None, location=None, categories=None,
              repeat=None, until=None, alarms=None):
    """create a new event

    :param dtstart: starttime of that event
    :type dtstart: datetime
    :param dtend: end time of that event, if this is a *date*, this value is
        interpreted as being the last date the event is scheduled on, i.e.
        the VEVENT DTEND will be *one day later*
    :type dtend: datetime
    :param summary: description of the event, used in the SUMMARY property
    :type summary: unicode
    :param timezone: timezone of the event (start and end)
    :type timezone: pytz.timezone
    :param allday: if set to True, we will not transform dtstart and dtend to
        datetime
    :type allday: bool
    :returns: event
    :rtype: icalendar.Event
    """

    if dtstart is None:
        raise ValueError("no start given")
    if dtend is None:
        raise ValueError("no end given")
    if summary is None:
        raise ValueError("no summary given")

    if not allday and timezone is not None:
        dtstart = timezone.localize(dtstart)
        dtend = timezone.localize(dtend)

    event = icalendar.Event()
    event.add('dtstart', dtstart)
    event.add('dtend', dtend)
    event.add('dtstamp', dt.datetime.now())
    event.add('summary', summary)
    event.add('uid', generate_random_uid())
    # event.add('sequence', 0)

    if description:
        event.add('description', description)
    if location:
        event.add('location', location)
    if categories:
        event.add('categories', categories)
    if repeat and repeat != "none":
        rrule = parse_datetime.rrulefstr(repeat, until, locale)
        event.add('rrule', rrule)
    if alarms:
        for alarm in alarms.split(","):
            alarm = alarm.strip()
            alarm_trig = -1 * parse_datetime.guesstimedeltafstr(alarm)
            new_alarm = icalendar.Alarm()
            new_alarm.add('ACTION', 'DISPLAY')
            new_alarm.add('TRIGGER', alarm_trig)
            new_alarm.add('DESCRIPTION', description)
            event.add_component(new_alarm)
    return event


def split_ics(ics, random_uid=False, default_timezone=None):
    """split an ics string into several according to VEVENT's UIDs

    and sort the right VTIMEZONEs accordingly
    ignores all other ics components
    :type ics: str
    :param random_uid: assign random uids to all events
    :type random_uid: bool
    :rtype list:
    """
    cal = cal_from_ics(ics)
    tzs = {item['TZID']: item for item in cal.walk() if item.name == 'VTIMEZONE'}

    events_grouped = defaultdict(list)
    for item in cal.walk():
        if item.name == 'VEVENT':
            events_grouped[item['UID']].append(item)
        else:
            continue
    return [ics_from_list(events, tzs, random_uid, default_timezone) for uid, events in
            sorted(events_grouped.items())]


def ics_from_list(events, tzs, random_uid=False, default_timezone=None):
    """convert an iterable of icalendar.Events to an icalendar.Calendar

    :params events: list of events all with the same uid
    :type events: list(icalendar.cal.Event)
    :param random_uid: assign random uids to all events
    :type random_uid: bool
    :param tzs: collection of timezones
    :type tzs: dict(icalendar.cal.Vtimzone
    """
    calendar = icalendar.Calendar()
    calendar.add('version', '2.0')
    calendar.add(
        'prodid', '-//PIMUTILS.ORG//NONSGML khal / icalendar //EN'
    )

    if random_uid:
        new_uid = generate_random_uid()

    needed_tz, missing_tz = set(), set()
    for sub_event in events:
        sub_event = sanitize(sub_event, default_timezone=default_timezone)
        if random_uid:
            sub_event['UID'] = new_uid
        # icalendar round-trip converts `TZID=a b` to `TZID="a b"` investigate, file bug XXX
        for prop in ['DTSTART', 'DTEND', 'DUE', 'EXDATE', 'RDATE', 'RECURRENCE-ID', 'DUE']:
            if isinstance(sub_event.get(prop), list):
                items = sub_event.get(prop)
            else:
                items = [sub_event.get(prop)]

            for item in items:
                if not (hasattr(item, 'dt') or hasattr(item, 'dts')):
                    continue
                # if prop is a list, all items have the same parameters
                datetime_ = item.dts[0].dt if hasattr(item, 'dts') else item.dt

                if not hasattr(datetime_, 'tzinfo'):
                    continue

                # check for datetimes' timezones which are not understood by
                # icalendar
                if datetime_.tzinfo is None and 'TZID' in item.params and \
                        item.params['TZID'] not in missing_tz:
                    logger.warning(
                        'Cannot find timezone `{}` in .ics file, using default timezone. '
                        'This can lead to erroneous time shifts'.format(item.params['TZID'])
                    )
                    missing_tz.add(item.params['TZID'])
                elif datetime_.tzinfo and datetime_.tzinfo != pytz.UTC and \
                        datetime_.tzinfo not in needed_tz:
                    needed_tz.add(datetime_.tzinfo)

    for tzid in needed_tz:
        if str(tzid) in tzs:
            calendar.add_component(tzs[str(tzid)])
        else:
            logger.warning(
                'Cannot find timezone `{}` in .ics file, this could be a bug, '
                'please report this issue at http://github.com/pimutils/khal/.'.format(tzid))
    for sub_event in events:
        calendar.add_component(sub_event)
    return calendar.to_ical().decode('utf-8')


RESET = '\x1b[0m'

ansi_reset = re.compile(r'\x1b\[0m')
ansi_sgr = re.compile(r'\x1b\['
                      '(?!0m)'  # negative lookahead, don't match 0m
                      '([0-9]+;?)+'
                      'm')


def find_last_reset(string):
    for match in re.finditer(ansi_reset, string):
        pass
    try:
        return match.start(), match.end(), match.group(0)
    except UnboundLocalError:
        return -2, -1, ''


def find_last_sgr(string):
    for match in re.finditer(ansi_sgr, string):
        pass
    try:
        return match.start(), match.end(), match.group(0)
    except UnboundLocalError:
        return -2, -1, ''


def find_unmatched_sgr(string):
    reset_pos, _, _ = find_last_reset(string)
    sgr_pos, _, sgr = find_last_sgr(string)
    if sgr_pos > reset_pos:
        return sgr
    else:
        return False


def color_wrap(text, width=70):
    """A variant of wrap that takes SGR codes (somewhat) into account.

    This doesn't actually adjust the length, but makes sure that
    lines that enable some attribues also contain a RESET, and also adds
    that code to the next line
    """
    # TODO we really want to ignore all SGR codes when measuring the width
    lines = wrap(text, width)
    for num, _ in enumerate(lines):
        sgr = find_unmatched_sgr(lines[num])
        if sgr:
            lines[num] += RESET
            if num != len(lines):
                lines[num + 1] = sgr + lines[num + 1]
    return lines


def get_weekday_occurrence(day):
    """Calculate how often this weekday has already occurred in a given month.

    :type day: datetime.date
    :returns: weekday (0=Monday, ..., 6=Sunday), occurrence
    :rtype: tuple(int, int)
    """
    xthday = 1 + (day.day - 1) // 7
    return day.weekday(), xthday


def get_month_abbr_len():
    """Calculate the number of characters we need to display the month
    abbreviated name. It depends on the locale.
    """
    return max(len(month_abbr[i]) for i in range(1, 13)) + 1


def expand(vevent, href=''):
    """
    Constructs a list of start and end dates for all recurring instances of the
    event defined in vevent.

    It considers RRULE as well as RDATE and EXDATE properties. In case of
    unsupported recursion rules an UnsupportedRecurrence exception is thrown.

    If the vevent contains a RECURRENCE-ID property, no expansion is done,
    the function still returns a tuple of start and end (date)times.

    :param vevent: vevent to be expanded
    :type vevent: icalendar.cal.Event
    :param href: the href of the vevent, used for more informative logging and
                 nothing else
    :type href: str
    :returns: list of start and end (date)times of the expanded event
    :rtype: list(tuple(datetime, datetime))
    """
    # we do this now and than never care about the "real" end time again
    if 'DURATION' in vevent:
        duration = vevent['DURATION'].dt
    else:
        duration = vevent['DTEND'].dt - vevent['DTSTART'].dt

    # if this vevent has a RECURRENCE_ID property, no expansion will be
    # performed
    expand = not bool(vevent.get('RECURRENCE-ID'))

    events_tz = getattr(vevent['DTSTART'].dt, 'tzinfo', None)
    allday = not isinstance(vevent['DTSTART'].dt, dt.datetime)

    def sanitize_datetime(date):
        if allday and isinstance(date, dt.datetime):
            date = date.date()
        if events_tz is not None:
            date = events_tz.localize(date)
        return date

    rrule_param = vevent.get('RRULE')
    if expand and rrule_param is not None:
        vevent = sanitize_rrule(vevent)

        # dst causes problem while expanding the rrule, therefore we transform
        # everything to naive datetime objects and transform back after
        # expanding
        # See https://github.com/dateutil/dateutil/issues/102
        dtstart = vevent['DTSTART'].dt
        if events_tz:
            dtstart = dtstart.replace(tzinfo=None)

        rrule = dateutil.rrule.rrulestr(
            rrule_param.to_ical().decode(),
            dtstart=dtstart
        )

        if rrule._until is None:
            # rrule really doesn't like to calculate all recurrences until
            # eternity, so we only do it until 2037, because a) I'm not sure
            # if python can deal with larger datetime values yet and b) pytz
            # doesn't know any larger transition times
            rrule._until = dt.datetime(2037, 12, 31)
        elif getattr(rrule._until, 'tzinfo', None):
            rrule._until = rrule._until \
                .astimezone(events_tz) \
                .replace(tzinfo=None)

        rrule = map(sanitize_datetime, rrule)

        logger.debug('calculating recurrence dates for {}, this might take some time.'.format(href))

        # RRULE and RDATE may specify the same date twice, it is recommended by
        # the RFC to consider this as only one instance
        dtstartl = set(rrule)
        if not dtstartl:
            raise UnsupportedRecurrence()
    else:
        dtstartl = {vevent['DTSTART'].dt}

    def get_dates(vevent, key):
        # TODO replace with get_all_properties
        dates = vevent.get(key)
        if dates is None:
            return
        if not isinstance(dates, list):
            dates = [dates]

        dates = (leaf.dt for tree in dates for leaf in tree.dts)
        dates = localize_strip_tz(dates, events_tz)
        return map(sanitize_datetime, dates)

    # include explicitly specified recursion dates
    if expand:
        dtstartl.update(get_dates(vevent, 'RDATE') or ())

    # remove excluded dates
    if expand:
        for date in get_dates(vevent, 'EXDATE') or ():
            try:
                dtstartl.remove(date)
            except KeyError:
                logger.warning(
                    'In event {}, excluded instance starting at {} not found, '
                    'event might be invalid.'.format(href, date))

    dtstartend = [(start, start + duration) for start in dtstartl]
    # not necessary, but I prefer deterministic output
    dtstartend.sort()
    return dtstartend


def assert_only_one_uid(cal: icalendar.Calendar):
    """assert the all VEVENTs in cal have the same UID"""
    uids = set()
    for item in cal.walk():
        if item.name == 'VEVENT':
            uids.add(item['UID'])
    if len(uids) > 1:
        return False
    else:
        return True


def sanitize(vevent, default_timezone, href='', calendar=''):
    """
    clean up vevents we do not understand

    :param vevent: the vevent that needs to be cleaned
    :type vevent: icalendar.cal.Event
    :param default_timezone: timezone to apply to start and/or end dates which
         were supposed to be localized but which timezone was not understood
         by icalendar
    :type timezone: pytz.timezone
    :param href: used for logging to inform user which .ics files are
        problematic
    :type href: str
    :param calendar: used for logging to inform user which .ics files are
        problematic
    :type calendar: str
    :returns: clean vevent
    :rtype: icalendar.cal.Event
    """
    # convert localized datetimes with timezone information we don't
    # understand to the default timezone
    # TODO do this for everything where a TZID can appear (RDATE, EXDATE)
    for prop in ['DTSTART', 'DTEND', 'DUE', 'RECURRENCE-ID']:
        if prop in vevent and invalid_timezone(vevent[prop]):
            timezone = vevent[prop].params.get('TZID')
            value = default_timezone.localize(vevent.pop(prop).dt)
            vevent.add(prop, value)
            logger.warning(
                "{} localized in invalid or incomprehensible timezone `{}` in {}/{}. "
                "This could lead to this event being wrongly displayed."
                "".format(prop, timezone, calendar, href)
            )

    vdtstart = vevent.pop('DTSTART', None)
    vdtend = vevent.pop('DTEND', None)
    dtstart = getattr(vdtstart, 'dt', None)
    dtend = getattr(vdtend, 'dt', None)

    # event with missing DTSTART
    if dtstart is None:
        raise ValueError('Event has no start time (DTSTART).')
    dtstart, dtend = sanitize_timerange(
        dtstart, dtend, duration=vevent.get('DURATION', None))

    vevent.add('DTSTART', dtstart)
    if dtend is not None:
        vevent.add('DTEND', dtend)
    return vevent


def sanitize_timerange(dtstart, dtend, duration=None):
    '''return sensible dtstart and end for events that have an invalid or
    missing DTEND, assuming the event just lasts one hour.'''

    if isinstance(dtstart, dt.datetime) and isinstance(dtend, dt.datetime):
        if dtstart.tzinfo and not dtend.tzinfo:
            logger.warning(
                "Event end time has no timezone. "
                "Assuming it's the same timezone as the start time"
            )
            dtend = dtstart.tzinfo.localize(dtend)
        if not dtstart.tzinfo and dtend.tzinfo:
            logger.warning(
                "Event start time has no timezone. "
                "Assuming it's the same timezone as the end time"
            )
            dtstart = dtend.tzinfo.localize(dtstart)

    if dtend is None and duration is None:
        if isinstance(dtstart, dt.datetime):
            dtstart = dtstart.date()
        dtend = dtstart + dt.timedelta(days=1)
    elif dtend is not None:
        if dtend < dtstart:
            raise ValueError('The event\'s end time (DTEND) is older than '
                             'the event\'s start time (DTSTART).')
        elif dtend == dtstart:
            logger.warning(
                "Event start time and end time are the same. "
                "Assuming the event's duration is one hour."
            )
            dtend += dt.timedelta(hours=1)

    return dtstart, dtend


def sanitize_rrule(vevent):
    """fix problems with RRULE:UNTIL"""
    if 'rrule' in vevent and 'UNTIL' in vevent['rrule']:
        until = vevent['rrule']['UNTIL'][0]
        dtstart = vevent['dtstart'].dt
        # DTSTART is date, UNTIL is datetime
        if not isinstance(dtstart, dt.datetime) and isinstance(until, dt.datetime):
            vevent['rrule']['until'] = until.date()
    return vevent


def localize_strip_tz(dates, timezone):
    """converts a list of dates to timezone, than removes tz info"""
    for one_date in dates:
        if getattr(one_date, 'tzinfo', None) is not None:
            one_date = one_date.astimezone(timezone)
            one_date = one_date.replace(tzinfo=None)
        yield one_date


def to_unix_time(dtime):
    """convert a datetime object to unix time in UTC (as a float)"""
    if getattr(dtime, 'tzinfo', None) is not None:
        dtime = dtime.astimezone(pytz.UTC)
    unix_time = timegm(dtime.timetuple())
    return unix_time


def to_naive_utc(dtime):
    """convert a datetime object to UTC and than remove the tzinfo, if
    datetime is naive already, return it
    """
    if not hasattr(dtime, 'tzinfo') or dtime.tzinfo is None:
        return dtime

    dtime_utc = dtime.astimezone(pytz.UTC)
    dtime_naive = dtime_utc.replace(tzinfo=None)
    return dtime_naive


def invalid_timezone(prop):
    """check if an icalendar property has a timezone attached we don't understand"""
    if hasattr(prop.dt, 'tzinfo') and prop.dt.tzinfo is None and 'TZID' in prop.params:
        return True
    else:
        return False


def _get_all_properties(vevent, prop):
    """Get all properties from a vevent, even if there are several entries

    example input:
    EXDATE:1234,4567
    EXDATE:7890

    returns: [1234, 4567, 7890]

    :type vevent: icalendar.cal.Event
    :type prop: str
    """
    if prop not in vevent:
        return list()
    if isinstance(vevent[prop], list):
        rdates = [leaf.dt for tree in vevent[prop] for leaf in tree.dts]
    else:
        rdates = [vddd.dt for vddd in vevent[prop].dts]
    return rdates


def delete_instance(vevent, instance):
    """remove a recurrence instance from a VEVENT's RRDATE list or add it
    to the EXDATE list

    :type vevent: icalendar.cal.Event
    :type instance: datetime.datetime
    """
    # TODO check where this instance is coming from and only call the
    # appropriate function
    if 'RRULE' in vevent:
        exdates = _get_all_properties(vevent, 'EXDATE')
        exdates += [instance]
        vevent.pop('EXDATE')
        vevent.add('EXDATE', exdates)
    if 'RDATE' in vevent:
        rdates = [one for one in _get_all_properties(vevent, 'RDATE') if one != instance]
        vevent.pop('RDATE')
        if rdates != []:
            vevent.add('RDATE', rdates)


def is_aware(dtime):
    """test if a datetime instance is timezone aware"""
    if dtime.tzinfo is not None and dtime.tzinfo.utcoffset(dtime) is not None:
        return True
    else:
        return False


def relative_timedelta_str(day):
    """Converts the timespan from `day` to today into a human readable string.

    :type day: datetime.date
    :rtype: str
    """
    days = (day - dt.date.today()).days
    if days < 0:
        direction = 'ago'
    else:
        direction = 'from now'
    approx = ''
    if abs(days) < 7:
        unit = 'day'
        count = abs(days)
    elif abs(days) < 365:
        unit = 'week'
        count = int(abs(days) / 7)
        if abs(days) % 7 != 0:
            approx = '~'
    else:
        unit = 'year'
        count = int(abs(days) / 365)
        if abs(days) % 365 != 0:
            approx = '~'
    if count > 1:
        unit += 's'

    return '{approx}{count} {unit} {direction}'.format(
        approx=approx,
        count=count,
        unit=unit,
        direction=direction,
    )


def sort_key(vevent):
    """helper function to determine order of VEVENTS
    so that recurrence-id events come after the corresponding rrule event, etc
    :param vevent: icalendar.Event
    :rtype: tuple(str, int)
    """
    assert isinstance(vevent, icalendar.Event)
    uid = str(vevent['UID'])
    rec_id = vevent.get('RECURRENCE-ID')
    if rec_id is None:
        return uid, 0
    rrange = rec_id.params.get('RANGE')
    if rrange == 'THISANDFUTURE':
        return uid, to_unix_time(rec_id.dt)
    else:
        return uid, 1


def get_wrapped_text(widget):
    return widget.original_widget.get_edit_text()


def cal_from_ics(ics):
    try:
        cal = icalendar.Calendar.from_ical(ics)
    except ValueError as error:
        if (len(error.args) > 0 and isinstance(error.args[0], str) and
                error.args[0].startswith('Offset must be less than 24 hours')):
            logger.warn(
                'Invalid timezone offset encountered, '
                'timezone information may be wrong: ' + str(error.args[0])
            )
            icalendar.vUTCOffset.ignore_exceptions = True
            cal = icalendar.Calendar.from_ical(ics)
            icalendar.vUTCOffset.ignore_exceptions = False
    return cal
