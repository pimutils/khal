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
import logging
import sys

import click
import click_log

from . import __version__, khalendar
from .exceptions import FatalError
from .settings import InvalidSettingsError, NoConfigFile, get_config

logger = logging.getLogger('khal')
click_log.basic_config('khal')

days_option = click.option('--days', default=None, type=int, help='How many days to include.')
week_option = click.option('--week', '-w', help='Include all events in one week.', is_flag=True)
events_option = click.option('--events', default=None, type=int, help='How many events to include.')
dates_arg = click.argument('dates', nargs=-1)


def time_args(f):
    return dates_arg(events_option(week_option(days_option(f))))


def multi_calendar_select(ctx, include_calendars, exclude_calendars):
    if include_calendars and exclude_calendars:
        raise click.UsageError('Can\'t use both -a and -d.')

    selection = set()

    if include_calendars:
        for cal_name in include_calendars:
            if cal_name not in ctx.obj['conf']['calendars']:
                raise click.BadParameter(
                    f'Unknown calendar {cal_name}, run `khal printcalendars` '
                    'to get a list of all configured calendars.'
                )

        selection.update(include_calendars)
    elif exclude_calendars:
        selection.update(ctx.obj['conf']['calendars'].keys())
        for value in exclude_calendars:
            selection.remove(value)

    return selection or None


def multi_calendar_option(f):
    a = click.option('--include-calendar', '-a', multiple=True, metavar='CAL',
                     help=('Include the given calendar. Can be specified '
                           'multiple times.'))
    d = click.option('--exclude-calendar', '-d', multiple=True, metavar='CAL',
                     help=('Exclude the given calendar. Can be specified '
                           'multiple times.'))

    return d(a(f))


def mouse_option(f):
    o = click.option(
        '--mouse/--no-mouse',
        is_flag=True,
        default=None,
        help='Disable mouse in interactive UI'
    )
    return o(f)


def _select_one_calendar_callback(ctx, option, calendar):
    if isinstance(calendar, tuple):
        if len(calendar) > 1:
            raise click.UsageError(
                'Can\'t use "--include-calendar" / "-a" more than once for this command.')
        elif len(calendar) == 1:
            calendar = calendar[0]
    return _calendar_select_callback(ctx, option, calendar)


def _calendar_select_callback(ctx, option, calendar):
    if calendar and calendar not in ctx.obj['conf']['calendars']:
        raise click.BadParameter(
            f'Unknown calendar {calendar}, run `khal printcalendars` to get a '
            'list of all configured calendars.'
        )
    return calendar


def calendar_option(f):
    return click.option('--calendar', '-a', metavar='CAL', callback=_calendar_select_callback)(f)


def global_options(f):
    def color_callback(ctx, option, value):
        ctx.color = value

    def logfile_callback(ctx, option, path):
        ctx.logfilepath = path

    config = click.option(
        '--config', '-c',
        help='The config file to use.',
        default=None, metavar='PATH'
    )
    color = click.option(
        '--color/--no-color',
        help=('Use colored/uncolored output. Default is to only enable colors '
              'when not part of a pipe.'),
        expose_value=False, default=None,
        callback=color_callback
    )

    logfile = click.option(
        '--logfile', '-l',
        help='The logfile to use [defaults to stdout]',
        type=click.Path(),
        callback=logfile_callback,
        default=None,
        expose_value=False,
        metavar='LOGFILE',
    )

    version = click.version_option(version=__version__)

    return logfile(config(color(version(f))))


def build_collection(conf, selection):
    """build and return a khalendar.CalendarCollection from the configuration"""
    try:
        props = {}
        for name, cal in conf['calendars'].items():
            if selection is None or name in selection:
                props[name] = {
                    'name': name,
                    'path': cal['path'],
                    'readonly': cal['readonly'],
                    'color': cal['color'],
                    'priority': cal['priority'],
                    'ctype': cal['type'],
                    'addresses': cal['addresses'] if 'addresses' in cal else '',
                }
        collection = khalendar.CalendarCollection(
            calendars=props,
            color=conf['highlight_days']['color'],
            locale=conf['locale'],
            dbpath=conf['sqlite']['path'],
            hmethod=conf['highlight_days']['method'],
            default_color=conf['highlight_days']['default_color'],
            multiple=conf['highlight_days']['multiple'],
            multiple_on_overflow=conf['highlight_days']['multiple_on_overflow'],
            highlight_event_days=conf['default']['highlight_event_days'],
        )
    except FatalError as error:
        logger.debug(error, exc_info=True)
        logger.fatal(error)
        sys.exit(1)

    collection._default_calendar_name = conf['default']['default_calendar']
    return collection


class _NoConfig:
    def __getitem__(self, key):
        logger.fatal(
            'Cannot find a config file. If you have no configuration file '
            'yet, you might want to run `khal configure`.')
        sys.exit(1)


def prepare_context(ctx, config):
    assert ctx.obj is None

    logger.debug('khal %s' % __version__)
    try:
        conf = get_config(config)
    except NoConfigFile:
        conf = _NoConfig()
    except InvalidSettingsError:
        logger.info('If your configuration file used to work, please have a '
                    'look at the Changelog to see what changed.')
        sys.exit(1)
    else:
        logger.debug('Using config:')
        logger.debug(stringify_conf(conf))

    ctx.obj = {'conf_path': config, 'conf': conf}


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
