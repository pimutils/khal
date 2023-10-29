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
import stat
import sys
import textwrap
from shutil import get_terminal_size

import click
import click_log

from . import controllers, plugins
from .cli_utils import (
    _select_one_calendar_callback,
    build_collection,
    calendar_option,
    global_options,
    logger,
    mouse_option,
    multi_calendar_option,
    multi_calendar_select,
    prepare_context,
)
from .exceptions import FatalError
from .plugins import COMMANDS
from .terminal import colored
from .utils import human_formatter, json_formatter

try:
    from setproctitle import setproctitle
except ImportError:
    def setproctitle(_):
        pass


click_log.basic_config('khal')

days_option = click.option('--days', default=None, type=int, help='How many days to include.')
week_option = click.option('--week', '-w', help='Include all events in one week.', is_flag=True)
events_option = click.option('--events', default=None, type=int, help='How many events to include.')
dates_arg = click.argument('dates', nargs=-1)


def time_args(f):
    return dates_arg(events_option(week_option(days_option(f))))


def stringify_conf(conf):
    # since we have only two levels of recursion, a recursive function isn't
    # really worth it
    out = []
    for key, value in conf.items():
        out.append(f'[{key}]')
        for subkey, subvalue in value.items():
            if isinstance(subvalue, dict):
                out.append(f'  [[{subkey}]]')
                for subsubkey, subsubvalue in subvalue.items():
                    out.append(f'    {subsubkey}: {subsubvalue}')
            else:
                out.append(f'  {subkey}: {subvalue}')
    return '\n'.join(out)


class _KhalGroup(click.Group):
    def list_commands(self, ctx):
        return super().list_commands(ctx) + list(COMMANDS.keys())

    def get_command(self, ctx, name):
        if name in COMMANDS:
            logger.debug(f'found command {name} as a plugin')
            return COMMANDS[name]
        return super().get_command(ctx, name)


@click.group(cls=_KhalGroup)
@click_log.simple_verbosity_option('khal')
@global_options
@click.pass_context
def cli(ctx, config):
    # setting the process title so it looks nicer in ps
    # shows up as 'khal' under linux and as 'python: khal (python2.7)'
    # under FreeBSD, which is still nicer than the default
    setproctitle('khal')
    if ctx.logfilepath:
        logger = logging.getLogger('khal')
        logger.handlers = [logging.FileHandler(ctx.logfilepath)]
    prepare_context(ctx, config)

@cli.command()
@multi_calendar_option
@click.option('--format', '-f',
              help=('The format of the events.'))
@click.option('--day-format', '-df',
              help=('The format of the day line.'))
@click.option(
    '--once', '-o',
    help=('Print each event only once (even if it is repeated or spans multiple days).'),
    is_flag=True)
@click.option('--notstarted', help=('Print only events that have not started.'),
              is_flag=True)
@click.argument('DATERANGE', nargs=-1, required=False)
@click.pass_context
def calendar(ctx, include_calendar, exclude_calendar, daterange, once,
             notstarted, format, day_format):
    '''Print calendar with agenda.'''
    try:
        rows = controllers.calendar(
            build_collection(
                ctx.obj['conf'],
                multi_calendar_select(ctx, include_calendar, exclude_calendar)
            ),
            agenda_format=format,
            day_format=day_format,
            once=once,
            notstarted=notstarted,
            daterange=daterange,
            conf=ctx.obj['conf'],
            firstweekday=ctx.obj['conf']['locale']['firstweekday'],
            locale=ctx.obj['conf']['locale'],
            weeknumber=ctx.obj['conf']['locale']['weeknumbers'],
            monthdisplay=ctx.obj['conf']['view']['monthdisplay'],
            hmethod=ctx.obj['conf']['highlight_days']['method'],
            default_color=ctx.obj['conf']['highlight_days']['default_color'],
            multiple=ctx.obj['conf']['highlight_days']['multiple'],
            multiple_on_overflow=ctx.obj['conf']['highlight_days']['multiple_on_overflow'],
            color=ctx.obj['conf']['highlight_days']['color'],
            highlight_event_days=ctx.obj['conf']['default']['highlight_event_days'],
            bold_for_light_color=ctx.obj['conf']['view']['bold_for_light_color'],
            env={"calendars": ctx.obj['conf']['calendars']}
        )
        click.echo('\n'.join(rows))
    except FatalError as error:
        logger.debug(error, exc_info=True)
        logger.fatal(error)
        sys.exit(1)

@cli.command("list")
@multi_calendar_option
@click.option('--format', '-f',
              help=('The format of the events.'))
@click.option('--day-format', '-df',
              help=('The format of the day line.'))
@click.option('--once', '-o', is_flag=True,
              help=('Print each event only once '
                    '(even if it is repeated or spans multiple days).')
              )
@click.option('--notstarted', help=('Print only events that have not started.'),
              is_flag=True)
@click.option('--json', help=("Fields to output in json"), multiple=True)
@click.argument('DATERANGE', nargs=-1, required=False,
                metavar='[DATETIME [DATETIME | RANGE]]')
@click.pass_context
def klist(ctx, include_calendar, exclude_calendar,
          daterange, once, notstarted, json, format, day_format):
    """List all events between a start (default: today) and (optional)
    end datetime."""
    enabled_eventformatters = plugins.FORMATTERS
   # TODO: register user given format string as a plugin
    logger.debug(f'{enabled_eventformatters}')
    try:
        event_column = controllers.khal_list(
            build_collection(
                ctx.obj['conf'],
                multi_calendar_select(ctx, include_calendar, exclude_calendar)
            ),
            agenda_format=format,
            day_format=day_format,
            daterange=daterange,
            once=once,
            notstarted=notstarted,
            conf=ctx.obj['conf'],
            env={"calendars": ctx.obj['conf']['calendars']},
            json=json
        )
        if event_column:
            click.echo('\n'.join(event_column))
        else:
            logger.debug('No events found')

    except FatalError as error:
        logger.debug(error, exc_info=True)
        logger.fatal(error)
        sys.exit(1)

@cli.command()
@calendar_option
@click.option('--interactive', '-i', help=('Add event interactively'),
              is_flag=True)
@click.option('--location', '-l',
              help=('The location of the new event.'))
@click.option('--categories', '-g',
              help=('The categories of the new event, comma separated.'))
@click.option('--repeat', '-r',
              help=('Repeat event: daily, weekly, monthly or yearly.'))
@click.option('--until', '-u',
              help=('Stop an event repeating on this date.'))
@click.option('--format', '-f',
              help=('The format to print the event.'))
@click.option('--json', help=("Fields to output in json"), multiple=True)
@click.option('--alarms', '-m',
              help=('Alarm times for the new event as DELTAs comma separated'))
@click.option('--url', help=("URI for the event."))
@click.argument('info', metavar='[START [END | DELTA] [TIMEZONE] [SUMMARY] [:: DESCRIPTION]]',
                nargs=-1)
@click.pass_context
def new(ctx, calendar, info, location, categories, repeat, until, alarms, url, format,
        json, interactive):
    '''Create a new event from arguments.

    START and END can be either dates, times or datetimes, please have a
    look at the man page for details.
    Everything that cannot be interpreted as a (date)time or a timezone is
    assumed to be the event's summary, if two colons (::) are present,
    everything behind them is taken as the event's description.
    '''
    if not info and not interactive:
        raise click.BadParameter(
            'no details provided, did you mean to use --interactive/-i?'
        )

    calendar = calendar or ctx.obj['conf']['default']['default_calendar']
    if calendar is None:
        if interactive:
            while calendar is None:
                calendar = click.prompt('calendar')
                if calendar == '?':
                    for calendar in ctx.obj['conf']['calendars']:
                        click.echo(calendar)
                    calendar = None
                elif calendar not in ctx.obj['conf']['calendars']:
                    click.echo('unknown calendar enter ? for list')
                    calendar = None
        else:
            raise click.BadParameter(
                'No default calendar is configured, '
                'please provide one explicitly.'
            )
    try:
        new_func = controllers.new_from_string
        if interactive:
            new_func = controllers.new_interactive
        new_func(
            build_collection(ctx.obj['conf'], ctx.obj.get('calendar_selection', None)),
            calendar,
            ctx.obj['conf'],
            info=' '.join(info),
            location=location,
            categories=categories,
            repeat=repeat,
            env={"calendars": ctx.obj['conf']['calendars']},
            until=until,
            alarms=alarms,
            url=url,
            format=format,
            json=json
        )
    except FatalError as error:
        logger.debug(error, exc_info=True)
        logger.fatal(error)
        sys.exit(1)

@cli.command('import')
@click.option('--include-calendar', '-a', help=('The calendar to use.'),
              callback=_select_one_calendar_callback, multiple=True)
@click.option('--batch', help=('do not ask for any confirmation.'),
              is_flag=True)
@click.option('--random_uid', '-r', help=('Select a random uid.'),
              is_flag=True)
@click.argument('ics', type=click.File('rb'), nargs=-1)
@click.option('--format', '-f', help=('The format to print the event.'))
@click.pass_context
def import_ics(ctx, ics, include_calendar, batch, random_uid, format):
    '''Import events from an .ics file (or stdin).

    If an event with the same UID is already present in the (implicitly)
    selected calendar import will ask before updating (i.e. overwriting)
    that old event with the imported one, unless --batch is given, than it
    will always update. If this behaviour is not desired, use the
    `--random-uid` flag to generate a new, random UID.
    If no calendar is specified (and not `--batch`), you will be asked
    to choose a calendar. You can either enter the number printed behind
    each calendar's name or any unique prefix of a calendar's name.

    '''
    if include_calendar:
        ctx.obj['calendar_selection'] = {include_calendar, }
    collection = build_collection(ctx.obj['conf'], ctx.obj.get('calendar_selection', None))
    if batch and len(collection.names) > 1 and \
            ctx.obj['conf']['default']['default_calendar'] is None:
        raise click.UsageError(
            'When using batch import, please specify a calendar to import '
            'into or set the `default_calendar` in the config file.')
    rvalue = 0
    # Default to stdin:
    if not ics:
        ics_strs = ((sys.stdin.read(), 'stdin'),)
        if not batch:

            def isatty(_file):
                try:
                    return _file.isatty()
                except Exception:
                    return False

            if isatty(sys.stdin) and os.stat('/dev/tty').st_mode & stat.S_IFCHR > 0:
                sys.stdin = open('/dev/tty')
            else:
                logger.warning('/dev/tty does not exist, importing might not work')
    else:
        ics_strs = ((ics_file.read(), ics_file.name) for ics_file in ics)

    for ics_str, filename in ics_strs:
        try:
            controllers.import_ics(
                collection,
                ctx.obj['conf'],
                ics=ics_str,
                batch=batch,
                random_uid=random_uid,
                env={"calendars": ctx.obj['conf']['calendars']},
            )
        except FatalError as error:
            logger.debug(error, exc_info=True)
            logger.fatal(f"An error occurred when trying to import the file from {filename}")
            logger.fatal("Events from it will not be available in khal")
            if not batch:
                sys.exit(1)
            rvalue = 1
    sys.exit(rvalue)

@cli.command()
@multi_calendar_option
@mouse_option
@click.pass_context
def interactive(ctx, include_calendar, exclude_calendar, mouse):
    '''Interactive UI. Also launchable via `ikhal`.'''
    if mouse is not None:
        ctx.obj['conf']['default']['enable_mouse'] = mouse
    controllers.interactive(
        build_collection(
            ctx.obj['conf'],
            multi_calendar_select(ctx, include_calendar, exclude_calendar)
        ),
        ctx.obj['conf']
    )

@click.command()
@global_options
@multi_calendar_option
@mouse_option
@click.pass_context
def interactive_cli(ctx, config, include_calendar, exclude_calendar, mouse):
    '''Interactive UI. Also launchable via `khal interactive`.'''
    prepare_context(ctx, config)
    if mouse is not None:
        ctx.obj['conf']['default']['enable_mouse'] = mouse
    controllers.interactive(
        build_collection(
            ctx.obj['conf'],
            multi_calendar_select(ctx, include_calendar, exclude_calendar)
        ),
        ctx.obj['conf']
    )

@cli.command()
@multi_calendar_option
@click.pass_context
def printcalendars(ctx, include_calendar, exclude_calendar):
    '''List all calendars.'''
    try:
        click.echo('\n'.join(build_collection(
            ctx.obj['conf'],
            multi_calendar_select(ctx, include_calendar, exclude_calendar)
        ).names))
    except FatalError as error:
        logger.debug(error, exc_info=True)
        logger.fatal(error)
        sys.exit(1)

@cli.command()
@click.pass_context
def printformats(ctx):
    '''Print a date in all formats.

    Print the date 2013-12-21 21:45 in all configured date(time)
    formats to check if these locale settings are configured to ones
    liking.'''
    time = dt.datetime(2013, 12, 21, 21, 45)
    try:
        for strftime_format in [
                'longdatetimeformat', 'datetimeformat', 'longdateformat',
                'dateformat', 'timeformat']:
            dt_str = time.strftime(ctx.obj['conf']['locale'][strftime_format])
            click.echo(f'{strftime_format}: {dt_str}')
    except FatalError as error:
        logger.debug(error, exc_info=True)
        logger.fatal(error)
        sys.exit(1)

@cli.command()
@click.argument('ics', type=click.File('rb'), required=False)
@click.option('--format', '-f',
              help=('The format to print the event.'))
@click.pass_context
def printics(ctx, ics, format):
    '''Print an ics file (or read from stdin) without importing it.

    Just print the ics file, do nothing else.'''
    try:
        if ics:
            ics_str = ics.read()
            name = ics.name
        else:
            ics_str = sys.stdin.read()
            name = 'stdin input'
        controllers.print_ics(ctx.obj['conf'], name, ics_str, format)
    except FatalError as error:
        logger.debug(error, exc_info=True)
        logger.fatal(error)
        sys.exit(1)

@cli.command()
@multi_calendar_option
@click.option('--format', '-f',
              help=('The format of the events.'))
@click.option('--json', help=("Fields to output in json"), multiple=True)
@click.argument('search_string')
@click.pass_context
def search(ctx, format, json, search_string, include_calendar, exclude_calendar):
    '''Search for events matching SEARCH_STRING.

    For recurring events, only the master event and different overwritten
    events are shown.
    '''
    # TODO support for time ranges, location, description etc
    if format is None:
        format = ctx.obj['conf']['view']['event_format']
    try:
        collection = build_collection(
            ctx.obj['conf'],
            multi_calendar_select(ctx, include_calendar, exclude_calendar)
        )
        events = sorted(collection.search(search_string))
        event_column = []
        term_width, _ = get_terminal_size()
        now = dt.datetime.now()
        env = {"calendars": ctx.obj['conf']['calendars']}
        if len(json) == 0:
            formatter = human_formatter(format)
        else:
            formatter = json_formatter(json)
        for event in events:
            desc = textwrap.wrap(formatter(
                event.attributes(relative_to=now, env=env)), term_width)
            event_column.extend(
                [colored(d, event.color,
                         bold_for_light_color=ctx.obj['conf']['view']['bold_for_light_color'])
                 for d in desc]
            )
        if event_column:
            click.echo('\n'.join(event_column))
        else:
            logger.debug('No events found')
    except FatalError as error:
        logger.debug(error, exc_info=True)
        logger.fatal(error)
        sys.exit(1)

@cli.command()
@multi_calendar_option
@click.option('--format', '-f',
              help=('The format of the events.'))
@click.option('--show-past', help=('Show events that have already occurred as options'),
              is_flag=True)
@click.argument('search_string', nargs=-1)
@click.pass_context
def edit(ctx, format, search_string, show_past, include_calendar, exclude_calendar):
    '''Interactively edit (or delete) events matching the search string.'''
    try:
        controllers.edit(
            build_collection(
                ctx.obj['conf'],
                multi_calendar_select(ctx, include_calendar, exclude_calendar)
            ),
            ' '.join(search_string),
            format=format,
            allow_past=show_past,
            locale=ctx.obj['conf']['locale'],
            conf=ctx.obj['conf']
        )
    except FatalError as error:
        logger.debug(error, exc_info=True)
        logger.fatal(error)
        sys.exit(1)

@cli.command()
@multi_calendar_option
@click.option('--format', '-f',
              help=('The format of the events.'))
@click.option('--day-format', '-df',
              help=('The format of the day line.'))
@click.option('--notstarted', help=('Print only events that have not started'),
              is_flag=True)
@click.option('--json', help=("Fields to output in json"), multiple=True)
@click.argument('DATETIME', nargs=-1, required=False, metavar='[[START DATE] TIME | now]')
@click.pass_context
def at(ctx, datetime, notstarted, format, day_format, json, include_calendar, exclude_calendar):
    '''Print all events at a specific datetime (defaults to now).'''
    if not datetime:
        datetime = ("now",)
    if format is None:
        format = ctx.obj['conf']['view']['event_format']
    try:
        rows = controllers.khal_list(
            build_collection(
                ctx.obj['conf'],
                multi_calendar_select(ctx, include_calendar, exclude_calendar)
            ),
            agenda_format=format,
            day_format=day_format,
            datepoint=list(datetime),
            once=True,
            notstarted=notstarted,
            conf=ctx.obj['conf'],
            env={"calendars": ctx.obj['conf']['calendars']},
            json=json
        )
        if rows:
            click.echo('\n'.join(rows))
    except FatalError as error:
        logger.debug(error, exc_info=True)
        logger.fatal(error)
        sys.exit(1)

@cli.command()
@click.pass_context
def configure(ctx):
    """Helper for initial configuration of khal."""
    from . import configwizard
    try:
        configwizard.configwizard()
    except FatalError as error:
        logger.debug(error, exc_info=True)
        logger.fatal(error)
        sys.exit(1)


main_khal, main_ikhal = cli, interactive_cli
