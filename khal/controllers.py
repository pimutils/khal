# Copyright (c) 2013-2022 khal contributors
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

import datetime as dt
import logging
import os
import re
import textwrap
from collections import OrderedDict, defaultdict
from shutil import get_terminal_size
from typing import Callable, Optional

import pytz
from click import confirm, echo, prompt, style

from khal import __productname__, __version__, calendar_display, parse_datetime
from khal.custom_types import (
    EventCreationTypes,
    LocaleConfiguration,
    MonthDisplayType,
    WeekNumbersType,
)
from khal.exceptions import DateTimeParseError, FatalError
from khal.khalendar import CalendarCollection
from khal.khalendar.event import Event
from khal.khalendar.exceptions import DuplicateUid, ReadOnlyCalendarError

from .exceptions import ConfigurationError
from .icalendar import cal_from_ics, split_ics
from .icalendar import sort_key as sort_vevent_key
from .khalendar.vdir import Item
from .parse_datetime import timedelta2str
from .terminal import merge_columns
from .utils import human_formatter, json_formatter

logger = logging.getLogger('khal')


def format_day(day: dt.date, format_string: str, locale, attributes=None):
    if attributes is None:
        attributes = {}

    attributes["date"] = day.strftime(locale['dateformat'])
    attributes["date-long"] = day.strftime(locale['longdateformat'])

    attributes["name"] = parse_datetime.construct_daynames(day)

    colors = {"reset": style("", reset=True), "bold": style("", bold=True, reset=False)}
    for c in ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]:
        colors[c] = style("", reset=False, fg=c)
        colors[c + "-bold"] = style("", reset=False, fg=c, bold=True)
    attributes.update(colors)
    try:
        return format_string.format(**attributes) + colors["reset"]
    except (KeyError, IndexError):
        raise KeyError("cannot format day with: %s" % format_string)


def calendar(
    collection: CalendarCollection,
    agenda_format=None,
    notstarted: bool=False,
    once=False,
    daterange=None,
    day_format=None,
    locale=None,
    conf=None,
    firstweekday: int=0,
    weeknumber: WeekNumbersType=False,
    monthdisplay: MonthDisplayType='firstday',
    hmethod: str='fg',
    default_color: str='',
    multiple='',
    multiple_on_overflow: bool=False,
    color='',
    highlight_event_days=0,
    full=False,
    bold_for_light_color: bool=True,
    env=None,
    ):

    term_width, _ = get_terminal_size()
    lwidth = 27 if conf['locale']['weeknumbers'] == 'right' else 25
    rwidth = term_width - lwidth - 4

    try:
        start, end = start_end_from_daterange(
            daterange, locale,
            default_timedelta_date=conf['default']['timedelta'],
            default_timedelta_datetime=conf['default']['timedelta'],
        )
    except ValueError as error:
        raise FatalError(error)

    event_column = khal_list(
        collection,
        daterange,
        conf=conf,
        agenda_format=agenda_format,
        day_format=day_format,
        once=once,
        notstarted=notstarted,
        width=rwidth,
        env=env,
    )
    if not event_column:
        event_column = [style('No events', bold=True)]
    month_count = (end.year - start.year) * 12 + end.month - start.month + 1
    calendar_column = calendar_display.vertical_month(
        month=start.month,
        year=start.year,
        count=max(conf['view']['min_calendar_display'], month_count),
        firstweekday=firstweekday, weeknumber=weeknumber,
        monthdisplay=monthdisplay,
        collection=collection,
        hmethod=hmethod,
        default_color=default_color,
        multiple=multiple,
        multiple_on_overflow=multiple_on_overflow,
        color=color,
        highlight_event_days=highlight_event_days,
        locale=locale,
        bold_for_light_color=bold_for_light_color)
    return merge_columns(calendar_column, event_column, width=lwidth)


def start_end_from_daterange(
    daterange: list[str],
    locale: LocaleConfiguration,
    default_timedelta_date: dt.timedelta=dt.timedelta(days=1),
    default_timedelta_datetime: dt.timedelta=dt.timedelta(hours=1),
):
    """
    convert a string description of a daterange into start and end datetime

    if no description is given, return (today, today + default_timedelta_date)

    :param daterange: an iterable of strings that describes `daterange`
    :param locale: locale settings
    """
    if not daterange:
        start = dt.datetime(*dt.date.today().timetuple()[:3])
        end = start + default_timedelta_date
    else:
        start, end, allday = parse_datetime.guessrangefstr(
            daterange, locale, default_timedelta_date=default_timedelta_date,
            default_timedelta_datetime=default_timedelta_datetime,
        )
    return start, end


def get_events_between(
    collection: CalendarCollection,
    locale: dict,
    start: dt.datetime,
    end: dt.datetime,
    formatter: Callable,
    notstarted: bool,
    env: dict,
    original_start: dt.datetime,
    seen=None,
    colors: bool = True,
) -> list[str]:
    """returns a list of events scheduled between start and end. Start and end
    are strings or datetimes (of some kind).

    :param collection:
    :param locale:
    :param start: the start datetime
    :param end: the end datetime
    :param formatter: the formatter (see :class:`.utils.human_formatter`)
    :param nostarted: True if each event should start after start (instead of
      be active between start and end)
    :param env: a collection of "static" values like calendar names and color
    :param original_start: start datetime to compare against of notstarted is set
    :param seen:
    :param colors:
    :returns: a list to be printed as the agenda for the given days
    """
    assert not (notstarted and not original_start)

    event_list = []
    if env is None:
        env = {}
    assert start
    assert end
    start_local = locale['local_timezone'].localize(start)
    end_local = locale['local_timezone'].localize(end)

    start = start_local.replace(tzinfo=None)
    end = end_local.replace(tzinfo=None)

    events = sorted(collection.get_localized(start_local, end_local))
    events_float = sorted(collection.get_floating(start, end))
    events = sorted(events + events_float)
    for event in events:
        # yes the logic could be simplified, but I believe it's easier
        # to understand what's going on here this way
        if notstarted:
            if event.allday and event.start < original_start.date():
                continue
            elif not event.allday and event.start_local < original_start:
                continue
        if seen is not None and event.uid in seen:
            continue

        try:
            event_attributes = event.attributes(relative_to=(start, end), env=env, colors=colors)
        except KeyError as error:
            raise FatalError(error)

        event_list.append(event_attributes)
        if seen is not None:
            seen.add(event.uid)

    return formatter(event_list)


def khal_list(
    collection,
    daterange: Optional[list[str]] = None,
    conf: Optional[dict] = None,
    agenda_format=None,
    day_format: Optional[str]=None,
    once=False,
    notstarted: bool = False,
    width: Optional[int] = None,
    env=None,
    datepoint=None,
    json: Optional[list] = None,
):
    """returns a list of all events in `daterange`"""
    assert daterange is not None or datepoint is not None
    assert conf is not None

    # because empty strings are also Falsish
    if agenda_format is None:
        agenda_format = conf['view']['agenda_event_format']

    if json:
        formatter = json_formatter(json)
        colors = False
    else:
        formatter = human_formatter(agenda_format, width)
        colors = True

    if daterange is not None:
        if day_format is None:
            day_format = conf['view']['agenda_day_format']
        start, end = start_end_from_daterange(
            daterange, conf['locale'],
            default_timedelta_date=conf['default']['timedelta'],
            default_timedelta_datetime=conf['default']['timedelta'],
        )
        logger.debug(f'Getting all events between {start} and {end}')

    elif datepoint is not None:
        if not datepoint:
            datepoint = ['now']
        try:
            # hand over a copy of the `datepoint` so error reporting works
            # (we pop from that list in guessdatetimefstr())
            start, allday = parse_datetime.guessdatetimefstr(
                list(datepoint), conf['locale'], dt.date.today(),
            )
        except (ValueError, IndexError):
            raise FatalError(f"Invalid value of {' '.join(datepoint)} for a datetime")
        if allday:
            logger.debug(f'Got date {start}')
            raise FatalError('Please supply a datetime, not a date.')
        end = start + dt.timedelta(seconds=1)
        if day_format is None:
            day_format = style(
                start.strftime(conf['locale']['longdatetimeformat']),
                bold=True,
            )
        logger.debug(f'Getting all events between {start} and {end}')

    event_column: list[str] = []
    once = set() if once else None
    if env is None:
        env = {}

    original_start = conf['locale']['local_timezone'].localize(start)
    while start < end:
        if start.date() == end.date():
            day_end = end
        else:
            day_end = dt.datetime.combine(start.date(), dt.time.max)
        current_events = get_events_between(
            collection, locale=conf['locale'], formatter=formatter, start=start,
            end=day_end, notstarted=notstarted, original_start=original_start,
            env=env,
            seen=once,
            colors=colors,
        )
        if day_format and (conf['default']['show_all_days'] or current_events) and not json:
            if len(event_column) != 0 and conf['view']['blank_line_before_day']:
                event_column.append('')
            event_column.append(format_day(start.date(), day_format, conf['locale']))
        event_column.extend(current_events)
        start = dt.datetime(*start.date().timetuple()[:3]) + dt.timedelta(days=1)

    return event_column


def new_interactive(collection, calendar_name, conf, info, location=None,
                    categories=None, repeat=None, until=None, alarms=None,
                    format=None, json=None, env=None, url=None):
    info: EventCreationTypes
    try:
        info = parse_datetime.eventinfofstr(
            info, conf['locale'],
            default_event_duration=conf['default']['default_event_duration'],
            default_dayevent_duration=conf['default']['default_dayevent_duration'],
            adjust_reasonably=True,
        )
    except DateTimeParseError:
        info = {}

    while True:
        summary = info.get('summary')
        if not summary:
            summary = None
        info['summary'] = prompt('summary', default=summary)
        if info['summary']:
            break
        echo("a summary is required")

    while True:
        range_string = None
        if info.get('dtstart') and info.get('dtend'):
            start_string = info["dtstart"].strftime(conf['locale']['datetimeformat'])
            end_string = info["dtend"].strftime(conf['locale']['datetimeformat'])
            range_string = start_string + ' ' + end_string
        daterange = prompt("datetime range", default=range_string)
        start, end, allday = parse_datetime.guessrangefstr(
            daterange, conf['locale'], adjust_reasonably=True)
        info['dtstart'] = start
        info['dtend'] = end
        info['allday'] = allday
        if info['dtstart'] and info['dtend']:
            break
        echo("invalid datetime range")

    while True:
        tz = info.get('timezone') or conf['locale']['default_timezone']
        timezone = prompt("timezone", default=str(tz))
        try:
            tz = pytz.timezone(timezone)
            info['timezone'] = tz
            break
        except pytz.UnknownTimeZoneError:
            echo("unknown timezone")

    info['description'] = prompt("description (or 'None')", default=info.get('description'))
    if info['description'] == 'None':
        info['description'] = ''

    info.update({
        'location': location,
        'categories': categories,
        'repeat': repeat,
        'until': until,
        'alarms': alarms,
        'url': url,
    })

    event = new_from_dict(
        info,
        collection,
        conf,
        format=format,
        env=env,
        calendar_name=calendar_name,
        json=json,
    )
    echo("event saved")

    term_width, _ = get_terminal_size()
    edit_event(event, collection, conf['locale'], width=term_width)


def new_from_string(collection, calendar_name, conf, info, location=None,
                    categories=None, repeat=None, until=None, alarms=None,
                    url=None, format=None, json=None, env=None):
    """construct a new event from a string and add it"""
    info = parse_datetime.eventinfofstr(
        info, conf['locale'],
        conf['default']['default_event_duration'],
        conf['default']['default_dayevent_duration'],
        adjust_reasonably=True,
    )
    if alarms is None:
        if info['allday']:
            alarms = timedelta2str(conf['default']['default_dayevent_alarm'])
        else:
            alarms = timedelta2str(conf['default']['default_event_alarm'])
    info.update({
        'location': location,
        'categories': categories,
        'repeat': repeat,
        'until': until,
        'alarms': alarms,
        'url': url,
    })
    new_from_dict(
        info,
        collection,
        conf=conf,
        format=format,
        env=env,
        calendar_name=calendar_name,
        json=json,
    )


def new_from_dict(
    event_args: EventCreationTypes,
    collection: CalendarCollection,
    conf,
    calendar_name: Optional[str]=None,
    format=None,
    env=None,
    json=None,
) -> Event:
    """Create a new event from arguments and save in vdirs

    This is a wrapper around CalendarCollection.create_event_from_dict()
    """
    if isinstance(event_args['categories'], str):
        event_args['categories'] = [event_args['categories'].strip()
                                    for category in event_args['categories'].split(',')]
    try:
        event = collection.create_event_from_dict(event_args, calendar_name=calendar_name)
    except ValueError as error:
        raise FatalError(error)

    try:
        collection.insert(event)
    except ReadOnlyCalendarError:
        raise FatalError(
            f'ERROR: Cannot modify calendar `{calendar_name}` as it is read-only'
        )

    if conf['default']['print_new'] == 'event':
        if json is None or len(json) == 0:
            if format is None:
                format = conf['view']['event_format']
            formatter = human_formatter(format)
        else:
            formatter = json_formatter(json)
        echo(formatter(event.attributes(dt.datetime.now(), env=env)))
    elif conf['default']['print_new'] == 'path':
        assert event.href
        path = os.path.join(collection._calendars[event.calendar]['path'], event.href)
        echo(path)
    return event


def present_options(options, prefix="", sep="  ", width=70):
    option_list = [prefix] if prefix else []
    chars = {}
    for option in options:
        char = options[option]["short"]
        chars[char] = option
        option_list.append(option.replace(char, '[' + char + ']', 1))
    option_string = sep.join(option_list)
    option_string = textwrap.fill(option_string, width)
    char = prompt(option_string)
    if char in chars:
        return chars[char]
    else:
        return None


def edit_event(event, collection, locale, allow_quit=False, width=80):
    options = OrderedDict()
    if allow_quit:
        options["no"] = {"short": "n"}
        options["quit"] = {"short": "q"}
    else:
        options["done"] = {"short": "n"}
    options["summary"] = {"short": "s", "attr": "summary"}
    options["description"] = {"short": "d", "attr": "description", "none": True}
    options["datetime range"] = {"short": "t"}
    options["repeat"] = {"short": "p"}
    options["location"] = {"short": "l", "attr": "location", "none": True}
    options["categories"] = {"short": "c", "attr": "categories", "none": True}
    options["alarm"] = {"short": "a"}
    options["Delete"] = {"short": "D"}
    options["url"] = {"short": "u", "attr": "url", "none": True}
    # some output contains ansi escape sequences (probably only resets)
    # if hitting enter, the output (including the escape sequence) gets parsed
    # and fails the parsing. Therefore we remove ansi escape sequences before
    # parsing.
    ansi = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    now = dt.datetime.now()

    while True:
        choice = present_options(options, prefix="Edit?", width=width)
        if choice is None:
            echo("unknown choice")
            continue
        if choice == 'no':
            return True
        if choice in ['quit', 'done']:
            return False

        edited = False

        if choice == "Delete":
            if confirm("Delete all occurences of event?"):
                collection.delete(event.href, event.etag, event.calendar)
                return True
        elif choice == "datetime range":
            current = human_formatter("{start} {end}")(event.attributes(relative_to=now))
            value = prompt("datetime range", default=current)
            try:
                start, end, allday = parse_datetime.guessrangefstr(ansi.sub('', value), locale)
                event.update_start_end(start, end)
                edited = True
            except:  # noqa
                echo("error parsing range")
        elif choice == "repeat":
            recur = event.recurobject
            freq = recur["freq"] if "freq" in recur else ""
            until = recur["until"] if "until" in recur else ""
            if not freq:
                freq = 'None'
            freq = prompt('frequency (or "None")', freq)
            if freq == 'None':
                event.update_rrule(None)
            else:
                until = prompt('until (or "None")', until)
                if until == 'None':
                    until = None
                rrule = parse_datetime.rrulefstr(freq, until, locale, event.start.tzinfo)
                event.update_rrule(rrule)
            edited = True
        elif choice == "alarm":
            default_alarms = []
            for a in event.alarms:
                s = parse_datetime.timedelta2str(-1 * a[0])
                default_alarms.append(s)

            default = ', '.join(default_alarms)
            if not default:
                default = 'None'
            alarm = prompt('alarm (or "None")', default)
            if alarm == "None":
                alarm = ""
            alarm_list = []
            for a in alarm.split(","):
                alarm_trig = -1 * parse_datetime.guesstimedeltafstr(a.strip())
                new_alarm = (alarm_trig, event.description)
                alarm_list += [new_alarm]
            event.update_alarms(alarm_list)
            edited = True
        else:
            attr = options[choice]["attr"]
            default = getattr(event, attr)
            question = choice

            allow_none = False
            if "none" in options[choice] and options[choice]["none"]:
                question += ' (or "None")'
                allow_none = True
                if not default:
                    default = 'None'

            value = prompt(question, default)
            if allow_none and value == "None":
                value = ""
            if attr == 'categories':
                getattr(event, "update_" + attr)([cat.strip() for cat in value.split(',')])
            else:
                getattr(event, "update_" + attr)(value)
            edited = True

        if edited:
            event.increment_sequence()
            collection.update(event)


def edit(collection, search_string, locale, format=None, allow_past=False, conf=None):
    if conf is not None:
        if format is None:
            format = conf['view']['event_format']

    term_width, _ = get_terminal_size()
    now = conf['locale']['local_timezone'].localize(dt.datetime.now())

    events = sorted(collection.search(search_string))
    for event in events:
        if not allow_past:
            if event.allday and event.end < now.date():
                continue
            elif not event.allday and event.end_local < now:
                continue
        event_text = textwrap.wrap(human_formatter(format)(
            event.attributes(relative_to=now)), term_width)
        echo(''.join(event_text))
        if not edit_event(event, collection, locale, allow_quit=True, width=term_width):
            return


def interactive(collection, conf):
    """start the interactive user interface"""
    from . import ui
    pane = ui.ClassicView(
        collection, conf, title="select an event", description="do something")
    ui.start_pane(
        pane, pane.cleanup,
        program_info=f'{__productname__} v{__version__}',
        quit_keys=conf['keybindings']['quit'],
    )


def import_ics(collection, conf, ics, batch=False, random_uid=False, format=None,
               env=None):
    """
    :param batch: setting this to True will insert without asking for approval,
                  even when an event with the same uid already exists
    :type batch: bool
    :param random_uid: whether to assign a random UID to imported events or not
    :type random_uid: bool
    :param format: the format string to print events with
    :type format: str
    """
    if format is None:
        format = conf['view']['event_format']
    try:
        vevents = split_ics(ics, random_uid, conf['locale']['default_timezone'])
    except Exception as error:
        raise FatalError(error)
    for vevent in vevents:
        import_event(vevent, collection, conf['locale'], batch, format, env)


def import_event(vevent, collection, locale, batch, format=None, env=None):
    """import one event into collection, let user choose the collection

    :type vevent: list of vevents, which can be more than one VEVENT, i.e., the
        same UID, i.e., one "master" event and (optionally) 1+ RECURRENCE-ID events
    :type vevent: list(str)
    """
    # print all sub-events
    if not batch:
        for item in cal_from_ics(vevent).walk():
            if item.name == 'VEVENT':
                event = Event.fromVEvents(
                    [item], calendar=collection.default_calendar_name, locale=locale)
                echo(human_formatter(format)(event.attributes(dt.datetime.now(), env=env)))

    # get the calendar to insert into
    if not collection.writable_names:
        raise ConfigurationError('No writable calendars found, aborting import.')
    if len(collection.writable_names) == 1:
        calendar_name = collection.writable_names[0]
    elif batch:
        calendar_name = collection.default_calendar_name
    else:
        calendar_names = sorted(collection.writable_names)
        choices = ', '.join(
            [f'{name}({num})' for num, name in enumerate(calendar_names)])
        while True:
            value = prompt(
                "Which calendar do you want to import to? (unique prefixes are fine)\n"
                f"{choices}",
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
            echo('invalid choice')
    assert calendar_name in collection.writable_names

    if batch or confirm(f"Do you want to import this event into `{calendar_name}`?"):
        try:
            collection.insert(Item(vevent), collection=calendar_name)
        except DuplicateUid:
            if batch or confirm(
                    "An event with the same UID already exists. Do you want to update it?"):
                collection.force_update(Item(vevent), collection=calendar_name)
            else:
                logger.warning(f"Not importing event with UID `{event.uid}`")


def print_ics(conf, name, ics, format):
    if format is None:
        format = conf['view']['event_format']
    cal = cal_from_ics(ics)
    events = [item for item in cal.walk() if item.name == 'VEVENT']
    events_grouped = defaultdict(list)
    for event in events:
        events_grouped[event['UID']].append(event)

    vevents = []
    for uid in events_grouped:
        vevents.append(sorted(events_grouped[uid], key=sort_vevent_key))

    echo(f'{len(vevents)} events found in {name}')
    for sub_event in vevents:
        event = Event.fromVEvents(sub_event, locale=conf['locale'])
        echo(human_formatter(format)(event.attributes(dt.datetime.now())))
