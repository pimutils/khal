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
import logging
import sys
import textwrap

try:
    from setproctitle import setproctitle
except ImportError:
    def setproctitle(x):
        pass

import click
import pytz

from khal import aux, controllers, khalendar, __version__
from khal.log import logger
from khal.settings import get_config, InvalidSettingsError
from khal.exceptions import FatalError
from .compat import to_unicode
from .terminal import colored, get_terminal_size


days_option = click.option('--days', default=None, type=int,
                           help='How many days to include.')
events_option = click.option('--events', default=None, type=int,
                             help='How many events to include.')
dates_arg = click.argument('dates', nargs=-1)


def time_args(f):
    return dates_arg(events_option(days_option(f)))


def _calendar_select_callback(ctx, option, calendars):
    if not calendars:
        return
    if 'calendar_selection' in ctx.obj:
        raise click.UsageError('Can\'t use both -a and -d.')
    if not isinstance(calendars, tuple):
        calendars = (calendars,)

    mode = option.name
    selection = ctx.obj['calendar_selection'] = set()

    if mode == 'include_calendar':
        for cal_name in calendars:
            if cal_name not in ctx.obj['conf']['calendars']:
                raise click.UsageError(
                    'Unknown calendar {}, run `khal printcalendars` to get a '
                    'list of all configured calendars.'.format(cal_name)
                )

        selection.update(calendars)
    elif mode == 'exclude_calendar':
        selection.update(ctx.obj['conf']['calendars'].keys())
        for value in calendars:
            calendars.remove(value)
    else:
        raise ValueError(mode)


def calendar_selector(f):
    a = click.option('--include-calendar', '-a', multiple=True, metavar='CAL',
                     expose_value=False, callback=_calendar_select_callback,
                     help=('Include the given calendar. Can be specified '
                           'multiple times.'))
    d = click.option('--exclude-calendar', '-d', multiple=True, metavar='CAL',
                     expose_value=False, callback=_calendar_select_callback,
                     help=('Exclude the given calendar. Can be specified '
                           'multiple times.'))

    return d(a(f))


def global_options(f):
    config = click.option('--config', '-c', default=None, metavar='PATH',
                          help='The config file to use.')
    verbose = click.option('--verbose', '-v', is_flag=True,
                           help='Output debugging information.')
    version = click.version_option(version=__version__)

    return config(verbose(version(f)))


def build_collection(ctx):
    try:
        conf = ctx.obj['conf']
        collection = khalendar.CalendarCollection()
        selection = ctx.obj.get('calendar_selection', None)

        for name, cal in conf['calendars'].items():
            if selection is None or name in ctx.obj['calendar_selection']:
                collection.append(khalendar.Calendar(
                    name=name,
                    dbpath=conf['sqlite']['path'],
                    path=cal['path'],
                    readonly=cal['readonly'],
                    color=cal['color'],
                    unicode_symbols=conf['locale']['unicode_symbols'],
                    locale=conf['locale'],
                    ctype=cal['type'],
                ))
    except FatalError as error:
        logger.fatal(error)
        sys.exit(1)

    collection._default_calendar_name = conf['default']['default_calendar']
    return collection


def prepare_context(ctx, config, verbose):
    if ctx.obj is not None:
        return

    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    ctx.obj = {}
    try:
        ctx.obj['conf'] = conf = get_config(config)
    except InvalidSettingsError:
        sys.exit(1)

    logger.debug('Using config:')
    logger.debug(to_unicode(stringify_conf(conf), 'utf-8'))

    if conf is None:
        raise click.UsageError('Invalid config file, exiting.')


def stringify_conf(conf):
    # since we have only two levels of recursion, a recursive function isn't
    # really worth it
    out = list()
    for key, value in conf.items():
        out.append('[{}]'.format(key))
        for subkey, subvalue in value.items():
            if isinstance(subvalue, dict):
                out.append('  [[{}]]'.format(subkey))
                for subsubkey, subsubvalue in subvalue.items():
                    out.append('    {}: {}'.format(subsubkey, subsubvalue))
            else:
                out.append('  {}: {}'.format(subkey, subvalue))
    return '\n'.join(out)


def _get_cli():
    @click.group(invoke_without_command=True)
    @global_options
    @click.pass_context
    def cli(ctx, config, verbose):
        # setting the process title so it looks nicer in ps
        # shows up as 'khal' under linux and as 'python: khal (python2.7)'
        # under FreeBSD, which is still nicer than the default
        setproctitle('khal')
        prepare_context(ctx, config, verbose)

        if not ctx.invoked_subcommand:
            command = ctx.obj['conf']['default']['default_command']
            if command:
                ctx.invoke(cli.commands[command])
            else:
                click.echo(ctx.get_help())
                ctx.exit(1)

    @cli.command()
    @time_args
    @calendar_selector
    @click.pass_context
    def calendar(ctx, days, events, dates):
        '''Print calendar with agenda.'''
        controllers.calendar(
            build_collection(ctx),
            date=dates,
            firstweekday=ctx.obj['conf']['locale']['firstweekday'],
            locale=ctx.obj['conf']['locale'],
            weeknumber=ctx.obj['conf']['locale']['weeknumbers'],
            show_all_days=ctx.obj['conf']['default']['show_all_days'],
            days=days or ctx.obj['conf']['default']['days'],
            events=events
        )

    @cli.command()
    @time_args
    @calendar_selector
    @click.pass_context
    def agenda(ctx, days, events, dates):
        '''Print agenda.'''
        controllers.agenda(
            build_collection(ctx),
            date=dates,
            firstweekday=ctx.obj['conf']['locale']['firstweekday'],
            show_all_days=ctx.obj['conf']['default']['show_all_days'],
            locale=ctx.obj['conf']['locale'],
            days=days or ctx.obj['conf']['default']['days'],
            events=events,
        )

    @cli.command()
    @click.option('--include-calendar', '-a', help=('The calendar to use.'),
                  expose_value=False, callback=_calendar_select_callback,
                  metavar='CAL')
    @click.option('--location', '-l',
                  help=('The location of the new event.'))
    @click.option('--repeat', '-r',
                  help=('Repeat event: daily, weekly, monthly or yearly.'))
    @click.option('--until', '-u',
                  help=('Stop an event repeating on this date.'))
    @click.argument('description', nargs=-1, required=True)
    @click.pass_context
    def new(ctx, description, location, repeat, until):
        '''Create a new event.'''
        controllers.new_from_string(
            build_collection(ctx),
            ctx.obj['conf'],
            list(description),
            location=location,
            repeat=repeat,
            until=until.split(' ') if until is not None else None,
        )

    @cli.command()
    @calendar_selector
    @click.pass_context
    def interactive(ctx):
        '''Interactive UI. Also launchable via `ikhal`.'''
        controllers.interactive(build_collection(ctx), ctx.obj['conf'])

    @click.command()
    @calendar_selector
    @global_options
    @click.pass_context
    def interactive_cli(ctx, config, verbose):
        '''Interactive UI. Also launchable via `khal interactive`.'''
        prepare_context(ctx, config, verbose)
        controllers.interactive(build_collection(ctx), ctx.obj['conf'])

    @cli.command()
    @calendar_selector
    @click.pass_context
    def printcalendars(ctx):
        '''List all calendars.'''
        click.echo('\n'.join(build_collection(ctx).names))

    @cli.command()
    @click.pass_context
    def printformats(ctx):
        '''Print a date in all formats.

        Print the date 2013-12-11 10:09 in all configured date(time)
        formats to check if these locale settings are configured to once
        liking.'''
        from datetime import datetime
        time = datetime(2013, 12, 11, 10, 9)

        for strftime_format in [
                'longdatetimeformat', 'datetimeformat', 'longdateformat',
                'dateformat', 'timeformat']:
            dt_str = time.strftime(ctx.obj['conf']['locale'][strftime_format])
            click.echo('{}: {}'.format(strftime_format, dt_str))

    @cli.command()
    @calendar_selector
    @click.argument('search_string')
    @click.pass_context
    def search(ctx, search_string):
        '''Search for events matching SEARCH_STRING.

        For repetitive events only one event is currently shown.
        '''
        # TODO support for time ranges, location, description etc
        collection = build_collection(ctx)
        events = collection.search(search_string)
        event_column = list()
        term_width, _ = get_terminal_size()
        for event in events:
            desc = textwrap.wrap(event.long(), term_width)
            event_column.extend([colored(d, event.color) for d in desc])
        click.echo(to_unicode(
            '\n'.join(event_column),
            ctx.obj['conf']['locale']['encoding'])
        )

    @cli.command()
    @calendar_selector
    @click.argument('datetime', required=False, nargs=-1)
    @click.pass_context
    def at(ctx, datetime=None):
        '''Show all events scheduled for DATETIME.

        if DATETIME is given (or the string `now`) all events scheduled
        for this moment are shown, if only a time is given, the date is assumed
        to be today
        '''
        collection = build_collection(ctx)
        locale = ctx.obj['conf']['locale']
        dtime_list = list(datetime)
        if dtime_list == [] or dtime_list == ['now']:
            import datetime
            dtime = datetime.datetime.now()
        else:
            try:
                dtime, _ = aux.guessdatetimefstr(dtime_list, locale)
            except ValueError:
                logger.fatal(
                    '{} is not a valid datetime (matches neither {} nor {} nor'
                    ' {})'.format(
                        ' '.join(dtime_list),
                        locale['timeformat'],
                        locale['datetimeformat'],
                        locale['longdatetimeformat']))
                sys.exit(1)
        dtime = locale['local_timezone'].localize(dtime)
        dtime = dtime.astimezone(pytz.UTC)
        events = collection.get_events_at(dtime)
        event_column = list()
        term_width, _ = get_terminal_size()
        for event in events:
            desc = textwrap.wrap(event.long(), term_width)
            event_column.extend([colored(d, event.color) for d in desc])
        click.echo(to_unicode(
            '\n'.join(event_column),
            ctx.obj['conf']['locale']['encoding'])
        )

    return cli, interactive_cli

main_khal, main_ikhal = _get_cli()
