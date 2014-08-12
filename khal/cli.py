# vim: set ts=4 sw=4 expandtab sts=4 fileencoding=utf-8:
# Copyright (c) 2013-2014 Christian Geier et al.
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
import signal
import StringIO
import sys

try:
    from setproctitle import setproctitle
except ImportError:
    setproctitle = lambda x: None

import click

from khal import controllers
from khal import khalendar
from khal import __version__, __productname__
from khal.log import logger
from khal.settings import get_config


def _get_cli():
    @click.group()
    @click.option('--config', '-c', default=None, metavar='PATH',
                  help='The config file to use.')
    @click.option('--verbose', '-v', is_flag=True,
                  help='Output debugging information.')
    @click.option('--include-calendar', '-a', multiple=True, metavar='CAL',
                  help=('Include the given calendar. Can be specified '
                        'multiple times.'))
    @click.option('--exclude-calendar', '-d', multiple=True, metavar='CAL',
                  help=('Exclude the given calendar. Can be specified '
                        'multiple times.'))
    @click.version_option(version=__version__)
    @click.pass_context
    def cli(ctx, config, verbose, include_calendar, exclude_calendar):
        # setting the process title so it looks nicer in ps
        # shows up as 'khal' under linux and as 'python: khal (python2.7)'
        # under FreeBSD, which is still nicer than the default
        setproctitle('khal')

        if verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        if ctx.obj is None:
            ctx.obj = {}

        ctx.obj['conf'] = conf = get_config(config)

        out = StringIO()
        conf.write(out)
        logger.debug('Using config:')
        logger.debug(out.getvalue())

        if conf is None:
            raise click.UsageError('Invalid config file, exiting.')

        if include_calendar and exclude_calendar:
            raise click.UsageError('Can\'t use both -a and -d.')

        ctx.obj['collection'] = collection = khalendar.CalendarCollection()
        for name, cal in conf['calendars'].items():
            if (not exclude_calendar and name in include_calendar) or \
               (not include_calendar and name not in exclude_calendar):
                collection.append(khalendar.Calendar(
                    name=name,
                    dbpath=conf['sqlite']['path'],
                    path=cal['path'],
                    readonly=cal['readonly'],
                    color=cal['color'],
                    unicode_symbols=conf['locale']['unicode_symbols'],
                    local_tz=conf['locale']['local_timezone'],
                    default_tz=conf['locale']['default_timezone']
                ))
        collection._default_calendar_name = conf['default']['default_calendar']

    days_option = click.option('--days', default=None, type=int)
    events_option = click.option('--events', default=None, type=int)
    dates_arg = click.argument('dates', nargs=-1)
    time_args = lambda f: dates_arg(events_option(days_option(f)))

    @cli.command()
    @time_args
    @click.pass_context
    def calendar(ctx, days, events, dates):
        controllers.Calendar(
            ctx.obj['collection'],
            date=dates,
            firstweekday=ctx.obj['conf']['locale']['firstweekday'],
            encoding=ctx.obj['conf']['locale']['encoding'],
            dateformat=ctx.obj['conf']['locale']['dateformat'],
            longdateformat=ctx.obj['conf']['locale']['longdateformat'],
            days=days,
            events=events
        )

    @cli.command()
    @time_args
    @click.pass_context
    def agenda(ctx, days, events, dates):
        controllers.Agenda(
            ctx.obj['collection'],
            date=dates,
            firstweekday=ctx.obj['conf']['locale']['firstweekday'],
            encoding=ctx.obj['conf']['locale']['encoding'],
            dateformat=ctx.obj['conf']['locale']['dateformat'],
            longdateformat=ctx.obj['conf']['locale']['longdateformat'],
            days=days,
            events=events,
        )

    @cli.command()
    @click.argument('description')
    @click.pass_context
    def new(ctx, description):
        controllers.NewFromString(
            ctx.obj['collection'],
            ctx.obj['conf'],
            description
        )

    @cli.command()
    @click.pass_context
    def interactive(ctx):
        controllers.Interactive(ctx.obj['collection'], ctx.obj['conf'])

    @cli.command()
    @click.pass_context
    def printcalendars(ctx):
        click.echo('\n'.join(ctx.obj['collection'].names))

    return cli


main_khal = _get_cli()


def main_ikhal(args=sys.argv[1:]):
    main_khal(['interactive'] + args)
