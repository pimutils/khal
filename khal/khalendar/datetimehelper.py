from datetime import date, datetime, timedelta
import logging

import dateutil.rrule
import pytz

from .. import log

logger = log.logger


class UnsupportedRecursion(Exception):
    """raised if the RRULE is not understood by dateutil.rrule"""
    pass


def expand(vevent, default_tz, href=''):
    """

    :param vevent: vevent to be expanded
    :type vevent: icalendar.cal.Event
    :param default_tz: the default timezone used when we (icalendar)
                       don't understand the embedded timezone
    :type default_tz: pytz.timezone
    :param href: the href of the vevent, used for more informative logging
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
    allday = True if not isinstance(vevent['DTSTART'].dt, datetime) else False

    # icalendar did not understand the defined timezone
    if (not allday and 'TZID' in vevent['DTSTART'].params and
            vevent['DTSTART'].dt.tzinfo is None):
        vevent['DTSTART'].dt = default_tz.localize(vevent['DTSTART'].dt)

    if 'RRULE' not in vevent.keys():
        return [(vevent['DTSTART'].dt, vevent['DTSTART'].dt + duration)]

    events_tz = None
    if getattr(vevent['DTSTART'].dt, 'tzinfo', False):
        events_tz = vevent['DTSTART'].dt.tzinfo
        vevent['DTSTART'].dt = vevent['DTSTART'].dt.astimezone(pytz.UTC)

    rrulestr = vevent['RRULE'].to_ical()
    rrule = dateutil.rrule.rrulestr(rrulestr, dtstart=vevent['DTSTART'].dt)

    if not set(['UNTIL', 'COUNT']).intersection(vevent['RRULE'].keys()):
        # rrule really doesn't like to calculate all recurrences until
        # eternity, so we only do it 15years into the future

        dtstart = vevent['DTSTART'].dt
        if isinstance(dtstart, date):
            dtstart = datetime(*list(dtstart.timetuple())[:-3])
        rrule._until = dtstart + timedelta(days=15 * 365)

    if ((not getattr(rrule._until, 'tzinfo', True)) and
            (getattr(vevent['DTSTART'].dt, 'tzinfo', False))):
                rrule._until = vevent['DTSTART'].dt.tzinfo.localize(rrule._until)
    logger.debug('calculating recurrence dates for {0}, '
                  'this might take some time.'.format(href))
    dtstartl = list(rrule)

    if len(dtstartl) == 0:
        raise UnsupportedRecursion

    if events_tz is not None:
        dtstartl = [start.astimezone(events_tz) for start in dtstartl]
    elif allday:
        dtstartl = [start.date() for start in dtstartl]

    dtstartend = [(start, start + duration) for start in dtstartl]
    return dtstartend
