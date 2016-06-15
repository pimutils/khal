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

from datetime import date, timedelta, datetime
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
from .terminal import merge_columns


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


def format_day(day, format_string, locale, attributes=None):
    if attributes is None:
        attributes = {}

    attributes["date"] = day.strftime(locale['dateformat'])
    attributes["date-long"] = day.strftime(locale['longdateformat'])

    attributes["name"] = list(aux.construct_daynames((day,)))[0][1]

    colors = {"reset": style("", reset=True), "bold": style("", bold=True, reset=False)}
    for c in ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]:
        colors[c] = style("", reset=False, fg=c)
        colors[c + "-bold"] = style("", reset=False, fg=c, bold=True)
    attributes.update(colors)
    try:
        return format_string.format(**attributes) + colors["reset"]
    except (KeyError, IndexError):
        raise KeyError("cannot format day with: %s" % format_string)


def calendar(collection, format=None, notstarted=False, once=False, daterange=None,
             day_format=None,
             locale=None,
             conf=None,
             firstweekday=0,
             weeknumber=False,
             hmethod='fg',
             default_color='',
             multiple='',
             color='',
             highlight_event_days=0,
             full=False,
             bold_for_light_color=True,
             **kwargs):
    td = None
    if conf is not None:
        if format is None:
            format = conf['view']['agenda_event_format']
        if day_format is None:
            day_format = conf['view']['agenda_day_format']
        td = conf['default']['timedelta']

    term_width, _ = get_terminal_size()
    lwidth = 25
    rwidth = term_width - lwidth - 4
    event_column = get_list_from_str(collection, format=format,
                                     day_format=day_format,
                                     daterange=daterange, locale=locale,
                                     once=once, notstarted=notstarted,
                                     default_timedelta=td, width=rwidth,
                                     **kwargs)
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


def get_list_from_str(collection, locale, daterange, notstarted=False,
                      format=None, day_format=None, once=False,
                      default_timedelta=None, env=None, **kwargs):
    """returns a list of events scheduled in between `daterange`.

    :param collection:
    :type collection: khalendar.CalendarCollection
    :param locale: locale settings
    :type locale: dict
    :param daterange: an iterable of strings that describes `daterange`
    :type daterange: tuple
    :param notstarted: True if each event should start after start (instead of
        be active between start and end)
    :type nostarted: bool
    :param format: a format string that can be used in python string formatting
    :type format: str
    :param once: True if each event should only appear once
    :type once: bool
    :param default_timedelta: default length of datetimerange that should be
        reported on
    :type default_timedelta:
    :returns: a list to be printed as the agenda for the given datetime range
    :rtype: list(str)
    """
    if len(daterange) == 0:
        start = aux.datetime_fillin(end=False)
        if default_timedelta is None:
            end = aux.datetime_fillin(day=start)
        else:
            try:
                end = start + aux.guesstimedeltafstr(default_timedelta)
            except ValueError as e:
                logging.fatal(e)
                sys.exit(1)

    else:
        try:
            start, end = aux.guessrangefstr(
                daterange, locale, default_timedelta=default_timedelta)

            if start is None or end is None:
                raise InvalidDate('Invalid date range: "%s"' % (' '.join(daterange)))

        except InvalidDate as error:
                logging.fatal(error)
                sys.exit(1)

    event_column = []
    if once:
        kwargs["seen"] = set()
    if env is None:
        env = {}
    while start < end:
        day_end = aux.datetime_fillin(start.date())
        if start.date() == end.date():
            day_end = end
        current_events = get_list(collection, locale=locale, format=format, start=start,
                                  end=day_end, notstarted=notstarted, env=env, **kwargs)
        if current_events:
            event_column.append(format_day(start, day_format, locale))
        event_column.extend(current_events)
        start = aux.datetime_fillin(start.date(), end=False) + timedelta(days=1)
    if event_column == []:
        event_column = [style('No events', bold=True)]
    return event_column


def get_list(collection, locale, start, end, format=None, notstarted=False, env=None, width=None,
             seen=None):
    """returns a list of events scheduled between start and end. Start and end
    are strings or datetimes (of some kind).

    :param collection:
    :type collection: khalendar.CalendarCollection

    :param start: the start datetime
    :param end: the end datetime
    :param format: a format string that can be used in python string formatting
    :type  format: str
    :param env: a collection of "static" values like calendar names and color
    :type env: dict
    :param nostarted: True if each event should start after start (instead of
    be active between start and end)
    :type nostarted: Boolean
    :format:
    :returns: a list to be printed as the agenda for the given days
    :rtype: list(str)

    """
    event_list = []
    if env is None:
        env = {}

    start_local = aux.datetime_fillin(start, end=False, locale=locale)
    end_local = aux.datetime_fillin(end, locale=locale)

    start = start_local.replace(tzinfo=None)
    end = end_local.replace(tzinfo=None)

    events = sorted(collection.get_localized(start_local, end_local))
    events_float = sorted(collection.get_floating(start, end))
    events = sorted(events + events_float)
    for event in events:
        event_start = aux.datetime_fillin(event.start, end=False, locale=locale)
        if not (notstarted and event_start.replace(tzinfo=None) < start):
            if seen is None or event.uid not in seen:
                try:
                    event_string = event.format(format, relative_to=(start, end), env=env)
                except KeyError as e:
                    logging.fatal(e)
                    sys.exit(1)

                if width:
                    event_list += textwrap.wrap(event_string, width)
                else:
                    event_list.append(event_string)
                if seen is not None:
                    seen.add(event.uid)

    return event_list


def khal_list(collection, daterange, conf=None, format=None, day_format=None,
              once=False, notstarted=False, **kwargs):
    """list all events in `daterange`"""
    td = None
    if conf is not None:
        if format is None:
            format = conf['view']['agenda_event_format']
        td = conf['default']['timedelta']
        if day_format is None:
            day_format = conf['view']['agenda_day_format']

    event_column = get_list_from_str(
        collection, format=format, day_format=day_format, daterange=daterange,
        once=once, notstarted=notstarted, default_timedelta=td, **kwargs)

    echo('\n'.join(event_column))


def new_from_string(collection, calendar_name, conf, date_list, location=None,
                    categories=None, repeat=None, until=None, alarm=None,
                    format=None):
    """construct a new event from a string and add it"""
    try:
        event = aux.construct_event(
            date_list,
            location=location,
            categories=categories,
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
        if format is None:
            format = conf['view']['event_format']
        echo(event.format(format, datetime.now()))
    elif conf['default']['print_new'] == 'path':
        path = collection._calnames[event.calendar].path + event.href
        echo(path)


def interactive(collection, conf):
    """start the interactive user interface"""
    from . import ui
    pane = ui.ClassicView(collection,
                          conf,
                          title='select an event',
                          description='do something')
    ui.start_pane(
        pane, pane.cleanup,
        program_info='{0} v{1}'.format(__productname__, __version__),
        quit_keys=conf['keybindings']['quit'],

    )


def import_ics(collection, conf, ics, batch=False, random_uid=False, format=None):
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

    if format is None:
        format = conf['view']['event_format']

    vevents = list()
    for uid in events_grouped:
        vevents.append(sorted(events_grouped[uid], key=sort_key))
    for vevent in vevents:
        import_event(vevent, collection, conf['locale'], batch, random_uid, format)


def import_event(vevent, collection, locale, batch, random_uid, format=None):
    """import one event into collection, let user choose the collection"""

    # print all sub-events
    for sub_event in vevent:
        if not batch:
            event = Event.fromVEvents(
                [sub_event], calendar=collection.default_calendar_name, locale=locale)
            echo(event.format(format, datetime.now()))

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
