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

try:
    from setproctitle import setproctitle
except ImportError:
    setproctitle = lambda x: None

import click

from khal import controllers
from khal import khalendar
from khal import __version__
from khal.log import logger
from khal.settings import get_config, InvalidSettingsError
from khal.exceptions import FatalError

try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO


days_option = click.option('--days', default=None, type=int,
                           help='How many days to include.')
events_option = click.option('--events', default=None, type=int,
                             help='How many events to include.')
dates_arg = click.argument('dates', nargs=-1)
time_args = lambda f: dates_arg(events_option(days_option(f)))


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
                    locale=conf['locale']
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

    out = StringIO()
    conf.write(out)
    logger.debug('Using config:')
    logger.debug(out.getvalue().decode('utf-8'))

    if conf is None:
        raise click.UsageError('Invalid config file, exiting.')


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
        controllers.Calendar(
            build_collection(ctx),
            date=dates,
            firstweekday=ctx.obj['conf']['locale']['firstweekday'],
            encoding=ctx.obj['conf']['locale']['encoding'],
            locale=ctx.obj['conf']['locale'],
            weeknumber=ctx.obj['conf']['locale']['weeknumbers'],
            show_all_days=ctx.obj['conf']['default']['show_all_days'],
            days=days,
            events=events
        )

    @cli.command()
    @time_args
    @calendar_selector
    @click.pass_context
    def agenda(ctx, days, events, dates):
        '''Print agenda.'''
        controllers.Agenda(
            build_collection(ctx),
            date=dates,
            firstweekday=ctx.obj['conf']['locale']['firstweekday'],
            encoding=ctx.obj['conf']['locale']['encoding'],
            show_all_days=ctx.obj['conf']['default']['show_all_days'],
            locale=ctx.obj['conf']['locale'],
            days=days,
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
    @click.argument('description', nargs=-1, required=True)
    @click.pass_context
    def new(ctx, description, location, repeat):
        '''Create a new event.'''
        controllers.NewFromString(
            build_collection(ctx),
            ctx.obj['conf'],
            list(description),
            location=location,
            repeat=repeat,
        )

    @cli.command()
    @calendar_selector
    @click.pass_context
    def interactive(ctx):
        '''Interactive UI. Also launchable via `ikhal`.'''
        controllers.Interactive(build_collection(ctx), ctx.obj['conf'])

    @click.command()
    @calendar_selector
    @global_options
    @click.pass_context
    def interactive_cli(ctx, config, verbose):
        '''Interactive UI. Also launchable via `khal interactive`.'''
        prepare_context(ctx, config, verbose)
        controllers.Interactive(build_collection(ctx), ctx.obj['conf'])

    @cli.command()
    @calendar_selector
    @click.pass_context
    def printcalendars(ctx):
        '''List all calendars.'''
        click.echo('\n'.join(build_collection(ctx).names))

    return cli, interactive_cli


main_khal, main_ikhal = _get_cli()
