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

import icalendar
from click import confirm, echo, style, prompt
from vdirsyncer.utils.vobject import Item

import datetime
import itertools
import logging
import sys
import textwrap

from khal import aux, calendar_display
from khal.compat import to_unicode
from khal.khalendar.exceptions import ReadOnlyCalendarError, DuplicateUid
from khal.exceptions import InvalidDate, FatalError
from khal.khalendar.event import Event
from khal import __version__, __productname__
from khal.log import logger
from .terminal import colored, get_terminal_size, merge_columns


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


def get_agenda(collection, locale, dates=None, firstweekday=0,
               days=None, events=None, width=45, full=False, show_all_days=False):
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
        dates = [datetime.date.today()]
    else:
        try:
            dates = [
                aux.guessdatetimefstr([date], locale)[0].date()
                if not isinstance(date, datetime.date) else date
                for date in dates
            ]
        except InvalidDate as error:
            logging.fatal(error)
            sys.exit(1)

    if days is not None:
        daylist = [date + datetime.timedelta(days=one)
                   for one in range(days) for date in dates]
        daylist.sort()

    daylist = construct_daynames(daylist, locale['longdateformat'])
    localize = locale['local_timezone'].localize

    for day, dayname in daylist:
        start = localize(datetime.datetime.combine(day, datetime.time.min))
        end = localize(datetime.datetime.combine(day, datetime.time.max))

        # TODO unify allday and datetime events
        all_day_events = collection.get_allday_by_time_range(day)
        events = collection.get_datetime_by_time_range(start, end)
        if len(events) == 0 and len(all_day_events) == 0 and not show_all_days:
            continue

        event_column.append(style(dayname, bold=True))
        events.sort(key=lambda e: e.start)
        for event in itertools.chain(all_day_events, events):
            lines = list()
            items = event.relative_to(day, full).splitlines()
            for item in items:
                lines += textwrap.wrap(item, width)
            event_column.extend([colored(line, event.color) for line in lines])

    if event_column == []:
        event_column = [style(u'No events', bold=True)]
    return event_column


def calendar(collection, date=None, firstweekday=0, encoding='utf-8', locale=None,
             weeknumber=False, show_all_days=False, conf=None,
             hmethod='fg',
             default_color='',
             multiple='',
             color='',
             highlight_event_days=0,
             full=False,
             **kwargs):
    if date is None:
        date = [datetime.datetime.today()]

    term_width, _ = get_terminal_size()
    lwidth = 25
    rwidth = term_width - lwidth - 4
    event_column = get_agenda(
        collection, locale, dates=date, width=rwidth,
        show_all_days=show_all_days, full=full, **kwargs)
    calendar_column = calendar_display.vertical_month(
        firstweekday=firstweekday, weeknumber=weeknumber,
        collection=collection,
        hmethod=hmethod,
        default_color=default_color,
        multiple=multiple,
        color=color,
        highlight_event_days=highlight_event_days,
        locale=locale)
    rows = merge_columns(calendar_column, event_column)
    # XXX: Generate this as a unicode in the first place, rather than
    # casting it.
    echo(u'\n'.join(rows).encode(encoding))


def agenda(collection, date=None, encoding='utf-8',
           show_all_days=False, full=False, **kwargs):
    term_width, _ = get_terminal_size()
    event_column = get_agenda(collection, dates=date, width=term_width,
                              show_all_days=show_all_days, full=full, **kwargs)
    # XXX: Generate this as a unicode in the first place, rather than
    # casting it.
    echo(to_unicode(u'\n'.join(event_column), encoding))


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
                          title=u'select an event',
                          description=u'do something')
    ui.start_pane(
        pane, pane.cleanup,
        program_info=u'{0} v{1}'.format(__productname__, __version__)
    )


def import_ics(collection, conf, ics, batch=False, random_uid=False):
    """
    :param batch: setting this to True will insert without asking for approval,
                  even when an event with the same uid already exists
    :type batch: bool
    """
    vevents = aux.split_ics(ics, random_uid)
    for vevent in vevents:
        import_event(vevent, collection, conf['locale'], batch)


def import_event(vevent, collection, locale, batch, format=None, env=None):
    """import one event into collection, let user choose the collection

    :type vevent: list of vevents, which can be more than one VEVENT, i.e., the
        same UID, i.e., one "master" event and (optionally) 1+ RECURRENCE-ID events
    :type vevent: list(str)
    """
    # print all sub-events
    if not batch:
        for item in icalendar.Calendar.from_ical(vevent).walk():
            if item.name == 'VEVENT':
                event = Event.fromVEvents(
                    [item], calendar=collection.default_calendar_name, locale=locale)
                echo(event.event_description)

    # get the calendar to insert into
    if batch or len(collection.writable_names) == 1:
        calendar_name = collection.writable_names[0]
    else:
        calendar_names = sorted(collection.writable_names)
        choices = ', '.join(
            ['{}({})'.format(name, num) for num, name in enumerate(calendar_names)])
        while True:
            value = prompt(
                u"Which calendar do you want to import to? (unique prefixes are fine)\n"
                u"{}".format(choices),
                default=collection.default_calendar_name,
            )
            try:
                calendar_name = calendar_names[int(value)]
                break
            except (ValueError, IndexError):
                matches = [x for x in collection.writable_names if x.startswith(value)]
                if len(matches) == 1:
                    calendar_name = matches[0]
                    break
            echo(u'invalid choice')

    if batch or confirm(u"Do you want to import this event into `{}`?".format(calendar_name)):
        try:
            collection.new(Item(vevent), collection=calendar_name)
        except DuplicateUid:
            if batch or confirm(
                    u"An event with the same UID already exists. Do you want to update it?"):
                collection.force_update(Item(vevent), collection=calendar_name)
            else:
                logger.warn(u"Not importing event with UID `{}`".format(event.uid))
