# Copyright (c) 2013-2016 Christian Geier et al.
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

import icalendar
from click import confirm, echo, style, prompt
from vdirsyncer.utils.vobject import Item

from collections import defaultdict
from shutil import get_terminal_size

from datetime import date, datetime, timedelta
import logging
import sys
import textwrap


from khal import aux, calendar_display
from khal.khalendar.exceptions import ReadOnlyCalendarError, DuplicateUid
from khal.exceptions import InvalidDate, FatalError
from khal.khalendar.event import Event
from khal.khalendar.backend import sort_key
from khal import __version__, __productname__
from khal.log import logger
from .terminal import colored, merge_columns


def construct_daynames(daylist, longdateformat):
    """returns a list of tuples of datetime objects and datenames

    :param daylist: list of dates
    :type daylist: list(datetime.date)
    :param longdateformat: format in which to print dates
    :param str
    :returns: list of names and dates
    :rtype: list((str, datetime.date))
    """
    for day in daylist:
        if day == date.today():
            yield (day, 'Today:')
        elif day == date.today() + timedelta(days=1):
            yield (day, 'Tomorrow:')
        else:
            yield (day, day.strftime(longdateformat))


def get_agenda(collection, locale, dates=None, firstweekday=0, days=None, events=None, width=45,
               week=False, full=False, show_all_days=False, bold_for_light_color=True,):
    """returns a list of events scheduled for all days in daylist

    included are header "rows"
    :param collection:
    :type collection: khalendar.CalendarCollection
    :param dates: a list of all dates for which the events should be return,
                    including what should be printed as a header
    :type collection: list(str)
    :param show_all_days: True if all days must be shown, event without event
    :type show_all_days: Boolean
    :returns: a list to be printed as the agenda for the given days
    :rtype: list(str)

    """
    event_column = list()

    if days is None:
        days = 2

    if dates is None or len(dates) == 0:
        dates = [date.today()]
    else:
        try:
            dates = [
                aux.guessdatetimefstr([day], locale)[0].date()
                if not isinstance(day, date) else day
                for day in dates
            ]
        except InvalidDate as error:
            logging.fatal(error)
            sys.exit(1)

    if week:
        dates = [d - timedelta((d.weekday() - firstweekday) % 7)
                 for d in dates]
        days = 7

    if days is not None:
        daylist = [day + timedelta(days=one)
                   for one in range(days) for day in dates]
        daylist.sort()

    daylist = construct_daynames(daylist, locale['longdateformat'])

    for day, dayname in daylist:
        events = sorted(collection.get_events_on(day))
        if not events and not show_all_days:
            continue

        if event_column:
            event_column.append('')
        event_column.append(style(dayname, bold=True))
        for event in events:
            lines = list()
            items = event.relative_to(day, full).splitlines()
            for item in items:
                lines += textwrap.wrap(item, width)
            event_column.extend(
                [colored(line, event.color, bold_for_light_color=bold_for_light_color)
                 for line in lines]
            )

    if event_column == []:
        event_column = [style('No events', bold=True)]
    return event_column


def calendar(collection, dates=None, firstweekday=0, encoding='utf-8', locale=None,
             weeknumber=False, show_all_days=False, conf=None,
             hmethod='fg',
             default_color='',
             multiple='',
             color='',
             highlight_event_days=0,
             week=False,
             full=False,
             bold_for_light_color=True,
             **kwargs):
    if dates is None:
        dates = [datetime.today()]

    term_width, _ = get_terminal_size()
    lwidth = 25
    rwidth = term_width - lwidth - 4
    event_column = get_agenda(
        collection, locale, dates=dates, width=rwidth,
        show_all_days=show_all_days, week=week, full=full,
        bold_for_light_color=bold_for_light_color, **kwargs)
    calendar_column = calendar_display.vertical_month(
        firstweekday=firstweekday, weeknumber=weeknumber,
        collection=collection,
        hmethod=hmethod,
        default_color=default_color,
        multiple=multiple,
        color=color,
        highlight_event_days=highlight_event_days,
        locale=locale,
        bold_for_light_color=bold_for_light_color)
    rows = merge_columns(calendar_column, event_column)
    echo('\n'.join(rows))


def agenda(collection, dates=None, encoding='utf-8', show_all_days=False, full=False,
           week=False, bold_for_light_color=True, **kwargs):
    term_width, _ = get_terminal_size()
    event_column = get_agenda(collection, dates=dates, width=term_width,
                              show_all_days=show_all_days, full=full, week=week,

                              bold_for_light_color=bold_for_light_color, **kwargs)
    # XXX: Generate this as a unicode in the first place, rather than
    # casting it.
    echo('\n'.join(event_column))


def new_from_string(collection, calendar_name, conf, date_list, location=None, repeat=None,
                    until=None, alarm=None):
    """construct a new event from a string and add it"""
    try:
        event = aux.construct_event(
            date_list,
            location=location,
            repeat=repeat,
            until=until,
            alarm=alarm,
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
        calendar_name = collection.writable_names[0]
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
                matches = [x for x in collection.writable_names if x.startswith(value)]
                if len(matches) == 1:
                    calendar_name = matches[0]
                    break
            echo('invalid choice')

    if batch or confirm(u"Do you want to import this event into `{}`?"
                        u"".format(calendar_name)):
        ics = aux.ics_from_list(vevent, random_uid)
        try:
            collection.new(Item(ics.to_ical().decode('utf-8')), collection=calendar_name)
        except DuplicateUid:
            if batch or confirm(u"An event with the same UID already exists. "
                                u"Do you want to update it?"):
                collection.force_update(
                    Item(ics.to_ical().decode('utf-8')), collection=calendar_name)
            else:
                logger.warn(u"Not importing event with UID `{}`".format(event.uid))
