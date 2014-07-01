# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
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

import datetime
import logging
import sys
import textwrap

from khal import aux, calendar_display
from khal import __version__, __productname__
from .terminal import bstring, colored, get_terminal_size, merge_columns


def get_agenda(collection, dateformat, longdateformat, dates=[], width=45):
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
    event_column = list()

    if dates == []:
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        daylist = [(today, 'Today:'), (tomorrow, 'Tomorrow:')]
    else:
        try:
            daylist = [aux.datefstr(date, dateformat, longdateformat)
                       for date in dates]
        except aux.InvalidDate as error:
            logging.fatal(error)
            sys.exit(1)
        daynames = [date.strftime(longdateformat) for date in daylist]

        daylist = zip(daylist, daynames)

    for day, dayname in daylist:
        # TODO unify allday and datetime events
        start = datetime.datetime.combine(day, datetime.time.min)
        end = datetime.datetime.combine(day, datetime.time.max)

        event_column.append(bstring(dayname))

        all_day_events = collection.get_allday_by_time_range(day)
        events = collection.get_datetime_by_time_range(start, end)
        for event in all_day_events:
            desc = textwrap.wrap(event.compact(day), width)
            event_column.extend([colored(d, event.color) for d in desc])

        events.sort(key=lambda e: e.start)
        for event in events:
            desc = textwrap.wrap(event.compact(day), width)
            event_column.extend([colored(d, event.color) for d in desc])
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
        print('\n'.join(rows).encode(encoding))


class Agenda(object):

    def __init__(self, collection, date=None, firstweekday=0, encoding='utf-8',
                 **kwargs):
        term_width, _ = get_terminal_size()
        event_column = get_agenda(collection, dates=date, width=term_width,
                                  **kwargs)
        print('\n'.join(event_column).encode(encoding))


class NewFromString(object):

    def __init__(self, collection, conf, date_list):
        event = aux.construct_event(date_list,
                                    conf.locale.timeformat,
                                    conf.locale.dateformat,
                                    conf.locale.longdateformat,
                                    conf.locale.datetimeformat,
                                    conf.locale.longdatetimeformat,
                                    conf.locale.local_timezone,
                                    encoding=conf.locale.encoding)
        event = collection.new_event(event,
                                     collection.default_calendar_name,
                                     conf.locale.local_timezone,
                                     conf.locale.default_timezone,
                                     )

        collection.new(event)


class Interactive(object):

    def __init__(self, collection, conf):
        import ui
        pane = ui.ClassicView(collection,
                              conf,
                              title='select an event',
                              description='do something')
        ui.start_pane(pane, pane.cleanup,
                      header=u'{0} v{1}'.format(__productname__, __version__))
