#!/usr/bin/env python2
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
import textwrap

from khal import aux, calendar_display
from khal import __version__, __productname__
from .terminal import bstring, colored, get_terminal_size, merge_columns


class Display(object):

    def __init__(self, collection, firstweekday=0, encoding='utf-8'):
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        daylist = [(today, 'Today:'), (tomorrow, 'Tomorrow:')]
        event_column = list()

        term_width, _ = get_terminal_size()
        lwidth = 25
        rwidth = term_width - lwidth - 4

        for day, dayname in daylist:
            # TODO unify allday and datetime events
            start = datetime.datetime.combine(day, datetime.time.min)
            end = datetime.datetime.combine(day, datetime.time.max)

            event_column.append(bstring(dayname))

            all_day_events = collection.get_allday_by_time_range(day)
            events = collection.get_datetime_by_time_range(start, end)
            for event in all_day_events:
                desc = textwrap.wrap(event.compact(day), rwidth)
                event_column.extend([colored(d, event.color) for d in desc])

            events.sort(key=lambda e: e.start)
            for event in events:
                desc = textwrap.wrap(event.compact(day), rwidth)
                event_column.extend([colored(d, event.color) for d in desc])

        calendar_column = calendar_display.vertical_month(
            firstweekday=firstweekday)

        rows = merge_columns(calendar_column, event_column)
        print('\n'.join(rows).encode(encoding))


class NewFromString(object):

    def __init__(self, collection, conf):
        date_list = conf.new
        event = aux.construct_event(date_list,
                                    conf.default.timeformat,
                                    conf.default.dateformat,
                                    conf.default.longdateformat,
                                    conf.default.datetimeformat,
                                    conf.default.longdatetimeformat,
                                    conf.default.local_timezone,
                                    encoding=conf.default.encoding)
        # TODO proper default calendar
        event = collection.new_event(event, conf.active_calendars.pop())

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
