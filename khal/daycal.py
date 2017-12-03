#!/home/arie/programs/khal/venv-git/bin/python3
import logging
import sys
import textwrap
from shutil import get_terminal_size

try:
    from setproctitle import setproctitle
except ImportError:
    def setproctitle(x):
        pass

import click
import pytz

from khal import controllers, khalendar, __version__
from khal.parse_datetime import guessdatetimefstr
from khal.settings import get_config, InvalidSettingsError
from khal.settings.exceptions import NoConfigFile
from khal.exceptions import FatalError
from khal.terminal import colored


logger = logging.getLogger('khal')

days_option = click.option('--days', default=None, type=int,
                           help='How many days to include.')
week_option = click.option('--week', '-w',
                           help=('Include all events in one week.'), is_flag=True)
events_option = click.option('--events', default=None, type=int,
                             help='How many events to include.')
dates_arg = click.argument('dates', nargs=-1)


def time_args(f):
    return dates_arg(events_option(week_option(days_option(f))))


def _multi_calendar_select_callback(ctx, option, calendars):
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
                raise click.BadParameter(
                    'Unknown calendar {}, run `khal printcalendars` to get a '
                    'list of all configured calendars.'.format(cal_name)
                )

        selection.update(calendars)
    elif mode == 'exclude_calendar':
        selection.update(ctx.obj['conf']['calendars'].keys())
        for value in calendars:
            selection.remove(value)
    else:
        raise ValueError(mode)


def multi_calendar_option(f):
    a = click.option('--include-calendar', '-a', multiple=True, metavar='CAL',
                     expose_value=False,
                     callback=_multi_calendar_select_callback,
                     help=('Include the given calendar. Can be specified '
                           'multiple times.'))
    d = click.option('--exclude-calendar', '-d', multiple=True, metavar='CAL',
                     expose_value=False,
                     callback=_multi_calendar_select_callback,
                     help=('Exclude the given calendar. Can be specified '
                           'multiple times.'))

    return d(a(f))


def _calendar_select_callback(ctx, option, calendar):
    calendar = calendar or ctx.obj['conf']['default']['default_calendar']
    if not calendar:
        raise click.BadParameter(
            'No default calendar is configured, '
            'please provide one explicitly.'
        )
    if calendar not in ctx.obj['conf']['calendars']:
        raise click.BadParameter(
            'Unknown calendar {}, run `khal printcalendars` to get a '
            'list of all configured calendars.'.format(calendar)
        )

    return calendar


def calendar_option(f):
    return click.option('--calendar', '-a', metavar='CAL',
                        callback=_calendar_select_callback)(f)


def global_options(f):
    def config_callback(ctx, option, config):
        prepare_context(ctx, config)

    def verbosity_callback(ctx, option, verbose):
        if verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    def color_callback(ctx, option, value):
        ctx.color = value

    config = click.option(
        '--config', '-c',
        is_eager=True,  # make sure other options can access config
        help='The config file to use.',
        default=None, metavar='PATH', expose_value=False,
        callback=config_callback
    )
    verbose = click.option(
        '--verbose', '-v',
        is_eager=True,  # make sure to log config when debugging
        help='Output debugging information.',
        is_flag=True, expose_value=False, callback=verbosity_callback
    )
    color = click.option(
        '--color/--no-color',
        help=('Use colored/uncolored output. Default is to only enable colors '
              'when not part of a pipe.'),
        expose_value=False, default=None,
        callback=color_callback
    )

    version = click.version_option(version=__version__)

    return config(verbose(color(version(f))))


def build_collection(ctx):
    try:
        conf = ctx.obj['conf']
        selection = ctx.obj.get('calendar_selection', None)

        props = dict()
        for name, cal in conf['calendars'].items():
            if selection is None or name in ctx.obj['calendar_selection']:
                props[name] = {
                    'name': name,
                    'path': cal['path'],
                    'readonly': cal['readonly'],
                    'color': cal['color'],
                    'ctype': cal['type'],
                }
        collection = khalendar.CalendarCollection(
            calendars=props,
            color=ctx.obj['conf']['highlight_days']['color'],
            locale=ctx.obj['conf']['locale'],
            dbpath=conf['sqlite']['path'],
            hmethod=ctx.obj['conf']['highlight_days']['method'],
            default_color=ctx.obj['conf']['highlight_days']['default_color'],
            multiple=ctx.obj['conf']['highlight_days']['multiple'],
            highlight_event_days=ctx.obj['conf']['default']['highlight_event_days'],
        )
    except FatalError as error:
        logger.fatal(error)
        sys.exit(1)

    collection._default_calendar_name = conf['default']['default_calendar']
    return collection


class _NoConfig(object):
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
        sys.exit(1)
    else:
        logger.debug('Using config:')
        logger.debug(stringify_conf(conf))

    ctx.obj = {'conf_path': config, 'conf': conf}


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


def do_summary(collection, conf, dates=None, encoding='utf-8', show_all_days=False, full=False,
           days=None, week=False, bold_for_light_color=True, **kwargs):
    from click import echo
    term_width, _ = get_terminal_size()
    event_column = get_summary(collection, conf, dates=dates, width=term_width,
                              show_all_days=show_all_days, full=full, days=days,
                              week=week,
                              bold_for_light_color=bold_for_light_color, **kwargs)
    # XXX: Generate this as a unicode in the first place, rather than
    # casting it.
    echo('\n'.join(event_column))

def is_holiday(day):
    import dateutil.easter
    from datetime import date, timedelta
    if day.weekday() == 6:
        return True
    if (day.month, day.day) in (
            (1, 1), (1, 6), (4, 25),
            (5, 1), (6, 2), (8, 15),
            (11, 1), (12, 8), (12, 25),
            (23, 26)):
        return True

    easter = dateutil.easter.easter(day.year)
    if day == easter + timedelta(days=1):
        return True
    return False

def get_summary(collection, conf, locale, dates=None, firstweekday=0, days=None, events=None, width=45,
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
    from datetime import date, timedelta
    from click import style, echo

    event_column = list()

    if days is None:
        days = 2

    if dates is None or len(dates) == 0:
        dates = [date.today()]
    else:
        try:
            dates = [
                guessdatetimefstr([day], locale)[0].date()
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

    last_day = None
    for day in daylist:
        if last_day is None or day.month != last_day.month:
            event_column.append(style(day.strftime("%B"), bold=True))

        last_day = day
        events = sorted(collection.get_events_on(day))
        if is_holiday(day):
            prefix = style(day.strftime("%d*%a: "), bold=True)
        else:
            prefix = style(day.strftime("%d %a: "), bold=False)
        if not events:
            event_column.append(prefix)
            continue
        for event in events:
            lines = list()
            items = event.format(conf['view']['agenda_event_format'], day).splitlines()
            for item in items:
                lines += textwrap.wrap(item, width)
            lines = [colored(line, event.color, bold_for_light_color=bold_for_light_color) for line in lines]
            event_column.append(prefix + lines[0])
            prefix = " " * 8
            event_column += [prefix + line for line in lines[1:]]

    if event_column == []:
        event_column = [style('No events', bold=True)]
    return event_column



def _get_cli():
    @click.group(invoke_without_command=True)
    @global_options
    @click.pass_context
    def cli(ctx):
        # setting the process title so it looks nicer in ps
        # shows up as 'khal' under linux and as 'python: khal (python2.7)'
        # under FreeBSD, which is still nicer than the default
        setproctitle('daycal')

        if not ctx.invoked_subcommand:
            command = "summary"
            if command:
                ctx.invoke(cli.commands[command])
            else:
                click.echo(ctx.get_help())
                ctx.exit(1)

    @cli.command()
    @time_args
    @multi_calendar_option
    @click.pass_context
    @click.option('--full', '-f', help=('Print description and location with event'),
                  is_flag=True)
    def summary(ctx, days, events, dates, week, full=False):
        '''Print summary.'''
        if week and days:
            raise click.UsageError('Cannot use --days and -week at the same time.')
        do_summary(
            build_collection(ctx),
            ctx.obj['conf'],
            dates=dates,
            firstweekday=ctx.obj['conf']['locale']['firstweekday'],
            show_all_days=ctx.obj['conf']['default']['show_all_days'],
            locale=ctx.obj['conf']['locale'],
            events=events,
            days=days,
            week=week,
            full=full,
            bold_for_light_color=ctx.obj['conf']['view']['bold_for_light_color']
        )

    return cli


main_khal = _get_cli()

if __name__ == "__main__":
    main_khal()
