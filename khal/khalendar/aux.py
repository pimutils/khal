
from datetime import datetime, timedelta
import calendar

import dateutil.rrule
import pytz

from .. import log
from ..compat import to_unicode

from .exceptions import UnsupportedRecursion

logger = log.logger


def expand(vevent, href=''):
    """
    Constructs a list of start and end dates for all recurring instances of the
    event defined in vevent.

    It considers RRULE as well as RDATE and EXDATE properties. In case of
    unsupported recursion rules an UnsupportedRecursion exception is thrown.
    If the timezone defined in vevent is not understood by icalendar,
    default_tz is used.

    :param vevent: vevent to be expanded
    :type vevent: icalendar.cal.Event
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
        vevent = sanitize_rrule(vevent)
        rrulestr = to_unicode(vevent['RRULE'].to_ical())
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
        # datutil's rrule turns dates into datetimes
        dtstartl = [start.date() if isinstance(start, datetime) else start for start in dtstartl]

    # RRULE and RDATE may specify the same date twice, it is recommended by
    # the RFC to consider this as only one instance
    dtstartl = list(set(dtstartl))
    dtstartl.sort()  # this is not necessary, but I prefer an ordered list

    dtstartend = [(start, start + duration) for start in dtstartl]
    return dtstartend


def sanitize(vevent, default_timezone, href='', calendar=''):
    """
    clean up vevents we do not understand

    Currently this only transform vevents with neither DTEND or DURATION into
    all day events lasting one day.

    :param vevent: the vevent that needs to be cleaned
    :type vevent: icalendar.cal.event
    :param default_timezone: timezone to apply to stard and/or end dates which
         were supposed to be localized but which timezone was not understood
         by icalendar
    :type timezone: pytz.timezone
    :param href: used for for logging to inform user which .ics files are
        problematic
    :type href: str
    :param calendar: used for for logging to inform user which .ics files are
        problematic
    :type calendar: str
    :returns: clean vevent
    :rtype: icalendar.cal.event
    """
    # TODO do this for everything where a TZID can appear (RDATE, EXDATE,
    # RRULE:UNTIL)
    for prop in ['DTSTART', 'DTEND', 'DUE', 'RECURRENCE-ID']:
        if prop in vevent and invalid_timezone(vevent[prop]):
            value = default_timezone.localize(vevent.pop(prop).dt)
            vevent.add(prop, value)
            logger.warn('{} has invalid or incomprehensible timezone '
                        'information in {} in {}'.format(prop, href, calendar))
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


def sanitize_rrule(vevent):
    """fix problems with RRULE:UNTIL"""
    if 'rrule' in vevent and 'UNTIL' in vevent['rrule']:
        until = vevent['rrule']['UNTIL'][0]
        dtstart = vevent['dtstart'].dt
        # DTSTART is date, UNTIL is datetime
        if not isinstance(dtstart, datetime) and isinstance(until, datetime):
            vevent['rrule']['until'] = until.date()
    return vevent


def localize_strip_tz(dates, timezone):
    """converts a list of dates to timezone, than removes tz info"""
    outdates = []
    for one_date in dates:
        if getattr(one_date, 'tzinfo', None) is not None:
            one_date = one_date.astimezone(timezone)
            one_date = one_date.replace(tzinfo=None)
        outdates.append(one_date)
    return outdates


def to_unix_time(dtime):
    """convert a datetime object to unix time in UTC (as a float)"""
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


def invalid_timezone(prop):
    """check if a icalendar property has a timezone attached we don't understand"""
    if hasattr(prop.dt, 'tzinfo') and prop.dt.tzinfo is None and 'TZID' in prop.params:
        return True
    else:
        return False


def _add_exdate(vevent, instance):
    """remove a recurrence instance from a VEVENT's RRDATE list

    :type vevent: icalendar.cal.Event
    :type instance: datetime.datetime
    """

    def dates_from_exdate(vdddlist):
        return [dts.dt for dts in vevent['EXDATE'].dts]

    if 'EXDATE' not in vevent:
        vevent.add('EXDATE', instance)
    else:
        if not isinstance(vevent['EXDATE'], list):
            exdates = dates_from_exdate(vevent['EXDATE'])
        else:
            exdates = list()
            for vddlist in vevent['EXDATE']:
                exdates.append(dates_from_exdate(vddlist))
        exdates += [instance]
        vevent.pop('EXDATE')
        vevent.add('EXDATE', exdates)


def _remove_instance(vevent, instance):
    """remove a recurrence instance from a VEVENT's RRDATE list

    :type vevent: icalendar.cal.Event
    :type instance: datetime.datetime
    """
    if isinstance(vevent['RDATE'], list):
        rdates = [leaf.dt for tree in vevent['RDATE'] for leaf in tree.dts]
    else:
        rdates = [vddd.dt for vddd in vevent['RDATE'].dts]
    rdates = [one for one in rdates if one != instance]
    vevent.pop('RDATE')
    if rdates != []:
        vevent.add('RDATE', rdates)


def delete_instance(vevent, instance):
    """remove a recurrence instance from a VEVENT's RRDATE list

    :type vevent: icalendar.cal.Event
    :type instance: datetime.datetime
    """

    if 'RDATE' in vevent and 'RRULE' in vevent:
        # TODO check where this instance is coming from and only call the
        # appropriate function
        _add_exdate(vevent, instance)
        _remove_instance(vevent, instance)
    elif 'RRULE' in vevent:
        _add_exdate(vevent, instance)
    elif 'RDATE' in vevent:
        _remove_instance(vevent, instance)
