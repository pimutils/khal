from datetime import datetime, timedelta
import logging

import dateutil.rrule
import pytz


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

    # icalendar did not understand the defined timezone
    if ('TZID' in vevent['DTSTART'].params and
            vevent['DTSTART'].dt.tzinfo is None):
        vevent['DTSTART'].dt = default_tz.localize(vevent['DTSTART'].dt)

    if 'RRULE' not in vevent.keys():
        return [(vevent['DTSTART'].dt, vevent['DTSTART'].dt + duration)]

    events_tz = None
    if (hasattr(vevent['DTSTART'].dt, 'tzinfo') and
            vevent['DTSTART'].dt.tzinfo is not None):
        events_tz = vevent['DTSTART'].dt.tzinfo
        vevent['DTSTART'].dt = vevent['DTSTART'].dt.astimezone(pytz.UTC)

    # dateutil.rrule converts everything to datetime
    allday = True if not isinstance(vevent['DTSTART'].dt, datetime) else False

    rrulestr = vevent['RRULE'].to_ical()
    rrule = dateutil.rrule.rrulestr(rrulestr, dtstart=vevent['DTSTART'].dt)
    if not set(['UNTIL', 'COUNT']).intersection(vevent['RRULE'].keys()):
        # rrule really doesn't like to calculate all recurrences until
        # eternity, so we only do it 15years into the future
        rrule._until = vevent['DTSTART'].dt + timedelta(days=15 * 365)
    if (rrule._until is not None and
            rrule._until.tzinfo is None and
            vevent['DTSTART'].dt.tzinfo is not None):
        rrule._until = vevent['DTSTART'].dt.tzinfo.localize(rrule._until)
    logging.debug('calculating recurrence dates for {0}, '
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
