from datetime import datetime, timedelta

import calendar
import dateutil.rrule
import pytz

from .. import log

from .exceptions import UnsupportedRecursion

logger = log.logger


def expand(vevent, default_tz, href=''):
    """
    Constructs a list of start and end dates for all recurring instances of the
    event defined in vevent.

    It considers RRULE as well as RDATE and EXDATE properties. In case of
    unsupported recursion rules an UnsupportedRecursion exception is thrown.
    If the timezone defined in vevent is not understood by icalendar,
    default_tz is used.

    :param vevent: vevent to be expanded
    :type vevent: icalendar.cal.Event
    :param default_tz: the default timezone used when we (icalendar)
                       don't understand the embedded timezone
    :type default_tz: pytz.timezone
    :param href: the href of the vevent, used for more informative logging and
                 nothing else
    :type href: str
    :returns: list of start and end (date)times of the expanded event
    :rtyped list(tuple(datetime, datetime))
    """
    # we do this now and than never care about the "real" end time again
    if 'DURATION' in vevent:
        duration = vevent['DURATION'].dt
    else:
        duration = vevent['DTEND'].dt - vevent['DTSTART'].dt

    # dateutil.rrule converts everything to datetime
    allday = not isinstance(vevent['DTSTART'].dt, datetime)

    # icalendar did not understand the defined timezone
    if (not allday and 'TZID' in vevent['DTSTART'].params and
            vevent['DTSTART'].dt.tzinfo is None):
        vevent['DTSTART'].dt = default_tz.localize(vevent['DTSTART'].dt)

    if 'RRULE' not in vevent.keys() and 'RDATE' not in vevent.keys():
        return [(vevent['DTSTART'].dt, vevent['DTSTART'].dt + duration)]

    events_tz = None
    if getattr(vevent['DTSTART'].dt, 'tzinfo', False):
        # dst causes problem while expanding the rrule, therefor we transform
        # everything to naive datetime objects and tranform back after
        # expanding
        events_tz = vevent['DTSTART'].dt.tzinfo
        vevent['DTSTART'].dt = vevent['DTSTART'].dt.replace(tzinfo=None)

    if 'RRULE' in vevent:
        rrulestr = vevent['RRULE'].to_ical()
        rrule = dateutil.rrule.rrulestr(rrulestr, dtstart=vevent['DTSTART'].dt)

        if not set(['UNTIL', 'COUNT']).intersection(vevent['RRULE'].keys()):
            # rrule really doesn't like to calculate all recurrences until
            # eternity, so we only do it until 2037, because a) I'm not sure
            # if python can deal with larger datetime values yet and b) pytz
            # doesn't know any larger transition times
            rrule._until = datetime(2037, 12, 31)

        if getattr(rrule._until, 'tzinfo', False):
            rrule._until = rrule._until.astimezone(events_tz)
            rrule._until = rrule._until.replace(tzinfo=None)

        logger.debug('calculating recurrence dates for {0}, '
                     'this might take some time.'.format(href))
        dtstartl = list(rrule)
        if len(dtstartl) == 0:
            raise UnsupportedRecursion
    else:
        dtstartl = [vevent['DTSTART'].dt]

    # include explicitly specified recursion dates
    if 'RDATE' in vevent:
        if not isinstance(vevent['RDATE'], list):
            rdates = [vevent['RDATE']]
        else:
            rdates = vevent['RDATE']
        rdates = [leaf.dt for tree in rdates for leaf in tree.dts]
        rdates = localize_strip_tz(rdates, events_tz)
        dtstartl += rdates

    # remove excluded dates
    if 'EXDATE' in vevent:
        if not isinstance(vevent['EXDATE'], list):
            exdates = [vevent['EXDATE']]
        else:
            exdates = vevent['EXDATE']
        exdates = [leaf.dt for tree in exdates for leaf in tree.dts]

        exdates = localize_strip_tz(exdates, events_tz)
        dtstartl = [start for start in dtstartl if start not in exdates]

    if events_tz is not None:
        dtstartl = [events_tz.localize(start) for start in dtstartl]
    elif allday:
        dtstartl = [start.date() for start in dtstartl]

    # RRULE and RDATE may specify the same date twice, it is recommended by
    # the RFC to consider this as only one instance
    dtstartl = list(set(dtstartl))
    dtstartl.sort()  # this is not necessary, but I prefer an ordered list

    dtstartend = [(start, start + duration) for start in dtstartl]
    return dtstartend


def sanitize(vevent):
    """
    clean up vevents we do not understand

    Currently this only transform vevents with neither DTEND or DURATION into
    all day events lasting one day.

    :param vevent: the vevent that needs to be cleaned
    :type vevent: icalendar.cal.event
    :returns: clean vevent
    :rtype: icalendar.cal.event
    """
    dtend = getattr(vevent.pop('DTEND', None), 'dt', None)
    dtstart = getattr(vevent.pop('DTSTART', None), 'dt', None)
    if dtstart is None:
        raise ValueError('Event has no start time (DTSTART).')
    dtstart, dtend = sanitize_timerange(
        dtstart, dtend, duration=vevent.get('DURATION', None))

    vevent.add('DTSTART', dtstart)
    if dtend is not None:
        vevent.add('DTEND', dtend)
    return vevent


def sanitize_timerange(dtstart, dtend, duration=None):
    '''Deal with events that have an invalid or missing DTEND, assuming the
    event just lasts one day.'''
    if dtend is None and duration is None:
        if isinstance(dtstart, datetime):
            dtstart = dtstart.date()
        dtend = dtstart + timedelta(days=1)
    elif dtend is not None:
        if dtend < dtstart:
            raise ValueError('The event\'s end time (DTEND) is older than '
                             'the event\'s start time (DTSTART).')
        elif dtend == dtstart:
            dtend += timedelta(days=1)

    return dtstart, dtend


def localize_strip_tz(dates, timezone):
    """converts a list of dates to timezone, than removes tz info"""
    outdates = []
    for one_date in dates:
        if hasattr(one_date, 'tzinfo') and one_date.tzinfo is not None:
            one_date = one_date.astimezone(timezone)
            one_date = one_date.replace(tzinfo=None)
        outdates.append(one_date)
    return outdates


def to_unix_time(dtime):
    """convert a datetime object to unix time in UTC"""
    if getattr(dtime, 'tzinfo', None) is not None:
        dtime = dtime.astimezone(pytz.UTC)
    unix_time = calendar.timegm(dtime.timetuple())
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
