# vim: set ts=4 sw=4 expandtab sts=4 fileencoding=utf-8:
# Copyright (c) 2011-2014 Christian Geier et al.
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
#

from click import echo

import datetime
import logging
import sys
import textwrap

from khal import aux, calendar_display
from khal.khalendar.exceptions import ReadOnlyCalendarError
from khal.exceptions import FatalError
from khal.khalendar.event import Event
from khal import __version__, __productname__
from khal.log import logger
from .terminal import bstring, colored, get_terminal_size, merge_columns


def construct_daynames(daylist, longdateformat):
    """returns a list of tuples of datetime objects and datenames

    :param daylist: list of dates
    :type daylist: list(datetime.date)
    :param longdateformat: format in which to print dates
    :param str
    :returns: list of names and dates
    :rtype: list((str, datetime.date))
    """
    for date in daylist:
        if date == datetime.date.today():
            yield (date, u'Today:')
        elif date == datetime.date.today() + datetime.timedelta(days=1):
            yield (date, u'Tomorrow:')
        else:
            yield (date, date.strftime(longdateformat))


def get_agenda(collection, dateformat, longdateformat, dates=[],
               days=None, events=None, width=45):
    """returns a list of events scheduled for all days in daylist

    included are header "rows"
    :param collection:
    :type collection: khalendar.CalendarCollection
    :param dates: a list of all dates for which the events should be return,
                    including what should be printed as a header
    :type collection: list(str)
    :returns: a list to be printed as the agenda for the given days
    :rtype: list(str)

    """
    assert not (days is not None and events is not None)
    event_column = list()

    if days is None:
        days = 2

    if len(dates) == 0:
        dates = [datetime.date.today()]
    else:
        try:
            dates = [aux.datefstr(date, dateformat, longdateformat)
                     for date in dates]
        except aux.InvalidDate as error:
            logging.fatal(error)
            sys.exit(1)

    if days is not None:
        daylist = [date + datetime.timedelta(days=one) for one in range(days) for date in dates]
        daylist.sort()

    daylist = construct_daynames(daylist, longdateformat)

    for day, dayname in daylist:
        # TODO unify allday and datetime events
        start = datetime.datetime.combine(day, datetime.time.min)
        end = datetime.datetime.combine(day, datetime.time.max)

        all_day_events = collection.get_allday_by_time_range(day)
        events = collection.get_datetime_by_time_range(start, end)
        if len(events) == 0 and len(all_day_events) == 0:
            continue

        event_column.append(bstring(dayname))
        for event in all_day_events:
            desc = textwrap.wrap(event.compact(day), width)
            event_column.extend([colored(d, event.color) for d in desc])

        events.sort(key=lambda e: e.start)

        for event in events:
            desc = textwrap.wrap(event.compact(day), width)
            event_column.extend([colored(d, event.color) for d in desc])

    if event_column == []:
        event_column = [bstring('No events')]
    return event_column


class Calendar(object):

    def __init__(self, collection, date=[], firstweekday=0, encoding='utf-8',
                 **kwargs):
        term_width, _ = get_terminal_size()
        lwidth = 25
        rwidth = term_width - lwidth - 4
        event_column = get_agenda(collection, dates=date, width=rwidth,
                                  **kwargs)
        calendar_column = calendar_display.vertical_month(
            firstweekday=firstweekday)

        rows = merge_columns(calendar_column, event_column)
        echo('\n'.join(rows).encode(encoding))


class Agenda(object):

    def __init__(self, collection, date=None, firstweekday=0, encoding='utf-8',
                 **kwargs):
        term_width, _ = get_terminal_size()
        event_column = get_agenda(collection, dates=date, width=term_width,
                                  **kwargs)
        echo('\n'.join(event_column).encode(encoding))


class NewFromString(object):

    def __init__(self, collection, conf, date_list):
        try:
            event = aux.construct_event(
                date_list,
                **conf['locale'])
        except FatalError:
            sys.exit(1)
        event = Event(event,
                      collection.default_calendar_name,
                      local_tz=conf['locale']['local_timezone'],
                      default_tz=conf['locale']['default_timezone'],
                      )

        try:
            collection.new(event)
        except ReadOnlyCalendarError:
            logger.fatal('ERROR: Cannot modify calendar "{}" as it is '
                         'read-only'.format(collection.default_calendar_name))
            sys.exit(1)


class Interactive(object):

    def __init__(self, collection, conf):
        import ui
        pane = ui.ClassicView(collection,
                              conf,
                              title='select an event',
                              description='do something')
        ui.start_pane(pane, pane.cleanup,
                      header=u'{0} v{1}'.format(__productname__, __version__))
