# vim: set ts=4 sw=4 expandtab sts=4 fileencoding=utf-8:
# Copyright (c) 2013-2015 Christian Geier et al.
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

from __future__ import unicode_literals

import icalendar
from click import confirm, echo, style, prompt
from vdirsyncer.utils.vobject import Item

from collections import defaultdict

import datetime
import itertools
import sys
import textwrap

from khal import aux, calendar_display
from khal.compat import to_unicode
from khal.khalendar.exceptions import ReadOnlyCalendarError, DuplicateUid
from khal.exceptions import FatalError
from khal.khalendar.event import Event
from khal.khalendar.backend import sort_key
from khal import __version__, __productname__
from khal.log import logger
from .terminal import colored, get_terminal_size, merge_columns


def construct_dayname(date, longdateformat):
    """Returns the date's name to use for the UI

    :param date:
    :type date: datetime.date
    :param longdateformat: format in which to print dates
    :param str
    :returns: list of names and dates
    :rtype: list((str, datetime.date))
    """

    if date == datetime.date.today():
        return 'Today:'
    elif date == datetime.date.today() + datetime.timedelta(days=1):
        return 'Tomorrow:'
    else:
        return date.strftime(longdateformat)


def get_agenda(collection, locale, dates=None, firstweekday=0, width=45,
               days=None, events=None, show_all_days=False):
    """returns a list of events scheduled for all days in daylist

    included are header "rows"
    :param collection:
    :type collection: khalendar.CalendarCollection
    :param show_all_days: True if all days must be shown, event without event
    :type show_all_days: Boolean
    :returns: a list to be printed as the agenda for the given days
    :rtype: list(str)
    :param events: How many events should be shown. Default infinite.
    :param days: How many days should be shown. Default infinite.
    :param dates: Which dates should be shown. Default all in the future.

    """
    today = datetime.date.today()
    if not dates:
        dates = (today + datetime.timedelta(days=x) for x in itertools.count())
    else:
        dates = [aux.guessdatetimefstr([date], locale)[0].date()
                 if not isinstance(date, datetime.date) else date
                 for date in dates]
    if days:
        dates = itertools.islice(dates, days)
    if not events:
        events = float('inf')

    for date in dates:
        start = datetime.datetime.combine(date, datetime.time.min)
        end = datetime.datetime.combine(date, datetime.time.max)

        # TODO unify allday and datetime events
        all_day_events = collection.get_allday_by_time_range(date)
        date_events = collection.get_datetime_by_time_range(start, end)
        if not date_events and not all_day_events and not show_all_days:
            continue

        yield style(construct_dayname(date, locale['longdateformat']), bold=True)

        date_events.sort(key=lambda e: e.start)
        for event in itertools.chain(all_day_events, date_events):
            desc = textwrap.wrap(event.relative_to(date), width)

            for d in desc:
                yield colored(d, event.color)
                events -= 1
                if events == 0:
                    return


def calendar(collection, date=None, firstweekday=0, encoding='utf-8',
             weeknumber=False, show_all_days=False, **kwargs):
    if date is None:
        date = [datetime.datetime.today()]

    term_width, _ = get_terminal_size()
    lwidth = 25
    rwidth = term_width - lwidth - 4
    event_column = get_agenda(
        collection, dates=date, width=rwidth, show_all_days=show_all_days,
        **kwargs)
    calendar_column = calendar_display.vertical_month(
        firstweekday=firstweekday, weeknumber=weeknumber)

    rows = merge_columns(calendar_column, event_column)
    # XXX: Generate this as a unicode in the first place, rather than
    # casting it.
    echo('\n'.join(rows).encode(encoding))


def agenda(collection, encoding='utf-8',
           show_all_days=False, **kwargs):
    term_width, _ = get_terminal_size()
    event_column = get_agenda(collection, width=term_width,
                              show_all_days=show_all_days, **kwargs)
    # XXX: Generate this as a unicode in the first place, rather than
    # casting it.
    for piece in event_column:
        echo(to_unicode(piece, encoding))


def new_from_string(collection, calendar_name, conf, date_list, location=None, repeat=None,
                    until=None):
    """construct a new event from a string and add it"""
    try:
        event = aux.construct_event(
            date_list,
            location=location,
            repeat=repeat,
            until=until,
            locale=conf['locale'])
    except FatalError:
        sys.exit(1)
    event = Event.fromVEvents(
        [event], calendar=calendar_name, locale=conf['locale'])

    try:
        collection.new(event)
    except ReadOnlyCalendarError:
        logger.fatal('ERROR: Cannot modify calendar "{}" as it is '
                     'read-only'.format(calendar_name))
        sys.exit(1)
    if conf['default']['print_new'] == 'event':
        echo(event.event_description)
    elif conf['default']['print_new'] == 'path':
        path = collection._calnames[event.calendar].path + event.href
        echo(path.encode(conf['locale']['encoding']))


def interactive(collection, conf):
    """start the interactive user interface"""
    from . import ui
    pane = ui.ClassicView(collection,
                          conf,
                          title='select an event',
                          description='do something')
    ui.start_pane(
        pane, pane.cleanup,
        program_info='{0} v{1}'.format(__productname__, __version__)
    )


def import_ics(collection, conf, ics, batch=False, random_uid=False):
    """
    :param batch: setting this to True will insert without asking for approval,
                  even when an event with the same uid already exists
    :type batch: bool
    """
    cal = icalendar.Calendar.from_ical(ics)
    events = [item for item in cal.walk() if item.name == 'VEVENT']
    events_grouped = defaultdict(list)
    for event in events:
        events_grouped[event['UID']].append(event)

    vevents = list()
    for uid in events_grouped:
        vevents.append(sorted(events_grouped[uid], key=sort_key))
    for vevent in vevents:
        import_event(vevent, collection, conf['locale'], batch, random_uid)


def import_event(vevent, collection, locale, batch, random_uid):
    """import one event into collection, let user choose the collection"""

    # print all sub-events
    for sub_event in vevent:
        if not batch:
            event = Event.fromVEvents(
                [sub_event], calendar=collection.default_calendar_name, locale=locale)
            echo(event.event_description)

    # get the calendar to insert into
    if batch or len(collection.writable_names) == 1:
        calendar_name = collection.default_calendar_name
    else:
        choice = list()
        for num, name in enumerate(collection.writable_names):
            choice.append('{}({})'.format(name, num))
        choice = ', '.join(choice)
        while True:
            value = prompt('Which calendar do you want to import to? \n'
                           '{}'.format(choice), default=collection.default_calendar_name)
            try:
                number = int(value)
                calendar_name = collection.writable_names[number]
                break
            except (ValueError, IndexError):
                matches = filter(lambda x: x.startswith(value), collection.writable_names)
                if len(matches) == 1:
                    calendar_name = matches[0]
                    break
            echo('invalid choice')

    if batch or confirm("Do you want to import this event into `{}`?"
                        "".format(calendar_name)):
        ics = aux.ics_from_list(vevent, random_uid)
        try:
            collection.new(
                Item(ics.to_ical().decode('utf-8')),
                collection=calendar_name)
        except DuplicateUid:
            if batch or confirm("An event with the same UID already exists. "
                                "Do you want to update it?"):
                collection.force_update(
                    Item(ics.to_ical().decode('utf-8')),
                    collection=calendar_name)
            else:
                logger.warn("Not importing event with UID `{}`".format(event.uid))
