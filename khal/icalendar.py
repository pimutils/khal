# Copyright (c) 2013-2021 khal contributors
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

"""collection of icalendar helper functions"""

import datetime as dt
import dateutil.rrule
import icalendar
import logging
import pytz
from collections import defaultdict

from .exceptions import UnsupportedRecurrence
from .parse_datetime import guesstimedeltafstr, rrulefstr
from .utils import generate_random_uid, localize_strip_tz, to_unix_time

logger = logging.getLogger('khal')


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
    tzs = {}

    events_grouped = defaultdict(list)
    for item in cal.walk():

        # Since some events could have a Windows format timezone (e.g. 'New Zealand
        # Standard Time' for 'Pacific/Auckland' in Olson format), we convert any
        # Windows format timezones to Olson.
        if item.name == 'VTIMEZONE':
            if item['TZID'] in icalendar.windows_to_olson.WINDOWS_TO_OLSON:
                key = icalendar.windows_to_olson.WINDOWS_TO_OLSON[item['TZID']]
            else:
                key = item['TZID']
            tzs[key] = item

        if item.name == 'VEVENT':
            events_grouped[item['UID']].append(item)
        else:
            continue
    return [ics_from_list(events, tzs, random_uid, default_timezone) for uid, events in
            sorted(events_grouped.items())]


def new_event(locale, dtstart=None, dtend=None, summary=None, timezone=None,
              allday=False, description=None, location=None, categories=None,
              repeat=None, until=None, alarms=None, url=None):
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
    :param url: url of the event
    :type url: string
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
    if url:
        event.add('url', icalendar.vUri(url))
    if repeat and repeat != "none":
        rrule = rrulefstr(repeat, until, locale)
        event.add('rrule', rrule)
    if alarms:
        for alarm in alarms.split(","):
            alarm = alarm.strip()
            alarm_trig = -1 * guesstimedeltafstr(alarm)
            new_alarm = icalendar.Alarm()
            new_alarm.add('ACTION', 'DISPLAY')
            new_alarm.add('TRIGGER', alarm_trig)
            new_alarm.add('DESCRIPTION', description)
            event.add_component(new_alarm)
    return event


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
            dtstart=dtstart,
            ignoretz=True,
        )

        if rrule._until is None:
            # rrule really doesn't like to calculate all recurrences until
            # eternity, so we only do it until 2037, because a) I'm not sure
            # if python can deal with larger datetime values yet and b) pytz
            # doesn't know any larger transition times
            rrule._until = dt.datetime(2037, 12, 31)
        else:
            if events_tz and 'Z' in rrule_param.to_ical().decode():
                rrule._until = pytz.UTC.localize(
                    rrule._until).astimezone(events_tz).replace(tzinfo=None)

            # rrule._until and dtstart could be dt.date or dt.datetime. They
            # need to be the same for comparison
            testuntil = rrule._until
            if (type(dtstart) == dt.date and type(testuntil) == dt.datetime):
                testuntil = testuntil.date()
            teststart = dtstart
            if (type(testuntil) == dt.date and type(teststart) == dt.datetime):
                teststart = teststart.date()

            if testuntil < teststart:
                logger.warning(
                    '{0}: Unsupported recurrence. UNTIL is before DTSTART.\n'
                    'This event will not be available in khal.'.format(href))
                return False

        if rrule.count() == 0:
            logger.warning(
                '{0}: Recurrence defined but will never occur.\n'
                'This event will not be available in khal.'.format(href))
            return False

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


def cal_from_ics(ics):
    try:
        cal = icalendar.Calendar.from_ical(ics)
    except ValueError as error:
        if (len(error.args) > 0 and isinstance(error.args[0], str) and
                error.args[0].startswith('Offset must be less than 24 hours')):
            logger.warning(
                'Invalid timezone offset encountered, '
                'timezone information may be wrong: ' + str(error.args[0])
            )
            icalendar.vUTCOffset.ignore_exceptions = True
            cal = icalendar.Calendar.from_ical(ics)
            icalendar.vUTCOffset.ignore_exceptions = False
    return cal
