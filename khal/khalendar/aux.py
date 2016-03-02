
from datetime import datetime, timedelta
import calendar

import dateutil.rrule
import pytz

from .. import log

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

    events_tz = getattr(vevent['DTSTART'].dt, 'tzinfo', None)
    allday = not isinstance(vevent['DTSTART'].dt, datetime)

    def sanitize_datetime(date):
        if allday and isinstance(date, datetime):
            date = date.date()
        if events_tz is not None:
            date = events_tz.localize(date)
        return date

    rrule_param = vevent.get('RRULE')
    if rrule_param is not None:
        vevent = sanitize_rrule(vevent)

        # dst causes problem while expanding the rrule, therefore we transform
        # everything to naive datetime objects and tranform back after
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
            rrule._until = datetime(2037, 12, 31)
        elif getattr(rrule._until, 'tzinfo', None):
            rrule._until = rrule._until \
                .astimezone(events_tz) \
                .replace(tzinfo=None)

        rrule = map(sanitize_datetime, rrule)

        logger.debug('calculating recurrence dates for {0}, '
                     'this might take some time.'.format(href))

        # RRULE and RDATE may specify the same date twice, it is recommended by
        # the RFC to consider this as only one instance
        dtstartl = set(rrule)
        if not dtstartl:
            raise UnsupportedRecursion()
    else:
        dtstartl = {vevent['DTSTART'].dt}

    def get_dates(vevent, key):
        dates = vevent.get(key)
        if dates is None:
            return
        if not isinstance(dates, list):
            dates = [dates]

        dates = (leaf.dt for tree in dates for leaf in tree.dts)
        dates = localize_strip_tz(dates, events_tz)
        return map(sanitize_datetime, dates)

    # include explicitly specified recursion dates
    dtstartl.update(get_dates(vevent, 'RDATE') or ())

    # remove excluded dates
    for date in get_dates(vevent, 'EXDATE') or ():
        dtstartl.remove(date)

    dtstartend = [(start, start + duration) for start in dtstartl]
    # not necessary, but I prefer deterministic output
    dtstartend.sort()
    return dtstartend


def sanitize(vevent, default_timezone, href='', calendar=''):
    """
    clean up vevents we do not understand

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
    # convert localized datetimes with timezone information we don't
    # understand to the default timezone
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
    '''return sensible dtstart and end for events that have an invalid or
    missing DTEND, assuming the event just lasts one day.'''

    if isinstance(dtstart, datetime) and isinstance(dtend, datetime):
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
    for one_date in dates:
        if getattr(one_date, 'tzinfo', None) is not None:
            one_date = one_date.astimezone(timezone)
            one_date = one_date.replace(tzinfo=None)
        yield one_date


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
