# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:

import os
import datetime
from datetime import timedelta

import pytest
from click.testing import CliRunner

from khal.cli import main_khal

from .aux import _get_text


class CustomCliRunner(CliRunner):
    def __init__(self, config, db=None, calendars=None, **kwargs):
        self.config = config
        self.db = db
        self.calendars = calendars
        super(CustomCliRunner, self).__init__(**kwargs)

    def invoke(self, cli, args=None, *a, **kw):
        args = ['-c', str(self.config)] + (args or [])
        return super(CustomCliRunner, self).invoke(cli, args, *a, **kw)


@pytest.fixture
def runner(tmpdir):
    config = tmpdir.join('config.ini')
    db = tmpdir.join('khal.db')
    calendar = tmpdir.mkdir('calendar')

    def inner(**kwargs):
        config.write(config_template.format(calpath=str(calendar),
                                            dbpath=str(db), **kwargs))
        runner = CustomCliRunner(config=config, db=db,
                                 calendars=dict(one=calendar))
        return runner
    return inner

config_template = '''
[calendars]
[[one]]
path = {calpath}
color = dark blue

[locale]
local_timezone = Europe/Berlin
default_timezone = Europe/Berlin

timeformat = %H:%M
dateformat = %d.%m.
longdateformat = %d.%m.%Y
datetimeformat =  %d.%m. %H:%M
longdatetimeformat = %d.%m.%Y %H:%M
firstweekday = 0

[default]
default_command = {command}
default_calendar = one
show_all_days = {showalldays}
days = {days}

[sqlite]
path = {dbpath}
'''


def test_direct_modification(runner):
    runner = runner(command='agenda', showalldays=False, days=2)

    result = runner.invoke(main_khal, ['agenda'])
    assert not result.exception
    assert result.output == 'No events\n'

    cal_dt = _get_text('event_dt_simple')
    event = runner.calendars['one'].join('test.ics')
    event.write(cal_dt)
    result = runner.invoke(main_khal, ['agenda', '09.04.2014'])
    assert not result.exception
    assert result.output == '09.04.2014\n09:30-10:30: An Event\n'

    os.remove(str(event))
    result = runner.invoke(main_khal, ['agenda'])
    assert not result.exception
    assert result.output == 'No events\n'


def test_simple(runner):
    runner = runner(command='agenda', showalldays=False, days=2)

    result = runner.invoke(main_khal)
    assert not result.exception
    assert result.output == 'No events\n'

    now = datetime.datetime.now().strftime('%d.%m.%Y')
    result = runner.invoke(
        main_khal, ['new'] + '{} 18:00 myevent'.format(now).split())
    assert result.output == ''
    assert not result.exception

    result = runner.invoke(main_khal)
    assert 'myevent' in result.output
    assert '18:00' in result.output
    # test show_all_days default value
    assert 'Tomorrow:' not in result.output
    assert not result.exception


def test_simple_color(runner):
    runner = runner(command='agenda', showalldays=False, days=2)

    now = datetime.datetime.now().strftime('%d.%m.%Y')
    result = runner.invoke(main_khal, ['new'] +
                           '{} 18:00 myevent'.format(now).split())
    assert result.output == ''
    assert not result.exception

    result = runner.invoke(main_khal, color=True)
    assert not result.exception
    assert '\x1b[34m' in result.output


def test_days(runner):
    runner = runner(command='agenda', showalldays=False, days=9)

    when = (datetime.datetime.now() + timedelta(days=7)).strftime('%d.%m.%Y')
    result = runner.invoke(
        main_khal, ['new'] + '{} 18:00 nextweek'.format(when).split())
    assert result.output == ''
    assert not result.exception

    when = (datetime.datetime.now() + timedelta(days=30)).strftime('%d.%m.%Y')
    result = runner.invoke(
        main_khal, ['new'] + '{} 18:00 nextmonth'.format(when).split())
    assert result.output == ''
    assert not result.exception

    result = runner.invoke(main_khal)
    assert 'nextweek' in result.output
    assert 'nextmonth' not in result.output
    assert '18:00' in result.output
    assert not result.exception


def test_showalldays(runner):
    runner = runner(command='agenda', showalldays=True, days=2)

    result = runner.invoke(main_khal)
    assert 'Tomorrow:' in result.output
    assert not result.exception


@pytest.mark.xfail
def test_calendar(runner):
    runner = runner(command='calendar', showalldays=False, days=0)
    result = runner.invoke(main_khal)
    assert not result.exception
    assert result.exit_code == 0
    output = '\n'.join([
        "    Mo Tu We Th Fr Sa Su     No events",
        "Jun  1  2  3  4  5  6  7     ",
        "     8  9 10 11 12 13 14     ",
        "    15 16 17 18 19 20 21     ",
        "    22 23 24 25 26 27 28     ",
        "Jul 29 30  1  2  3  4  5     ",
        "     6  7  8  9 10 11 12     ",
        "    13 14 15 16 17 18 19     ",
        "    20 21 22 23 24 25 26     ",
        "Aug 27 28 29 30 31  1  2     ",
        "     3  4  5  6  7  8  9     ",
        "    10 11 12 13 14 15 16     ",
        "    17 18 19 20 21 22 23     ",
        "    24 25 26 27 28 29 30     ",
        "Sep 31  1  2  3  4  5  6     ",
        "",
    ])
    assert result.output == output


def test_default_command_empty(runner):
    runner = runner(command='', showalldays=False, days=2)

    result = runner.invoke(main_khal)
    assert result.exception
    assert result.exit_code == 1
    assert result.output.startswith('Usage: ')


def test_default_command_nonempty(runner):
    runner = runner(command='agenda', showalldays=False, days=2)

    result = runner.invoke(main_khal)
    assert not result.exception
    assert result.output == 'No events\n'


def test_invalid_calendar(runner):
    runner = runner(command='', showalldays=False, days=2)
    result = runner.invoke(
        main_khal, ['new'] + '-a one 18:00 myevent'.split())
    assert not result.exception
    result = runner.invoke(
        main_khal, ['new'] + '-a two 18:00 myevent'.split())
    assert result.exception
    assert result.exit_code == 2
    assert 'Unknown calendar ' in result.output


@pytest.mark.parametrize('contents', [
    '',
    u'BEGIN:VCALENDAR\nBEGIN:VTODO\nEND:VTODO\nEND:VCALENDAR\n'
])
def test_no_vevent(runner, tmpdir, contents):
    runner = runner(command='agenda', showalldays=False, days=2)
    broken_item = runner.calendars['one'].join('broken_item.ics')
    broken_item.write(contents, mode='w')

    result = runner.invoke(main_khal)
    assert not result.exception
    assert 'No events' in result.output


def test_printformats(runner):
    runner = runner(command='printformats', showalldays=False, days=2)

    result = runner.invoke(main_khal)
    assert '\n'.join(['longdatetimeformat: 21.12.2013 10:09',
                      'datetimeformat: 21.12. 10:09',
                      'longdateformat: 21.12.2013',
                      'dateformat: 21.12.',
                      'timeformat: 10:09',
                      '']) == result.output
    assert not result.exception


def test_repeating(runner):
    runner = runner(command='agenda', showalldays=False, days=2)
    now = datetime.datetime.now().strftime('%d.%m.%Y')
    end_date = datetime.datetime.now() + datetime.timedelta(days=10)
    result = runner.invoke(
        main_khal, ['new'] + '{} 18:00 myevent -r weekly -u {}'.format(
            now, end_date.strftime('%d.%m.%Y')).split())
    assert result.output == ''
    assert not result.exception
