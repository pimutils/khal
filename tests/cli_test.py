# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:

import os
import datetime
from pkg_resources import parse_version
import pytest
import click
from click.testing import CliRunner

from khal.cli import main_khal


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
debug = 1

[sqlite]
path = {dbpath}
'''

def test_direct_modification(runner):
    runner = runner(command='NOPE')

    result = runner.invoke(main_khal, ['agenda'])
    assert not result.exception
    assert result.output == 'No events\n'

    from .event_test import cal_dt
    event = runner.calendars['one'].join('test.ics')
    event.write('\n'.join(cal_dt))
    result = runner.invoke(main_khal, ['agenda', '09.04.2014'])
    assert not result.exception
    assert result.output == u'09.04.2014\n09:30-10:30: An Event\n'

    os.remove(str(event))
    result = runner.invoke(main_khal, ['agenda'])
    assert not result.exception
    assert result.output == 'No events\n'


def test_simple(runner):
    runner = runner(command='agenda')

    result = runner.invoke(main_khal)
    assert not result.exception
    assert result.output == 'No events\n'

    now = datetime.datetime.now().strftime('%d.%m.%Y')
    result = runner.invoke(main_khal, ['new', '{} 18:00 myevent'.format(now)])
    assert result.output == ''
    assert not result.exception

    result = runner.invoke(main_khal)
    assert 'myevent' in result.output
    assert '18:00' in result.output
    assert not result.exception


def test_default_command_empty(runner):
    runner = runner(command='')

    result = runner.invoke(main_khal)
    assert result.exception
    assert result.exit_code == 1
    assert result.output.startswith('Usage: ')


def test_default_command_nonempty(runner):
    runner = runner(command='agenda')

    result = runner.invoke(main_khal)
    assert not result.exception
    assert result.output == 'No events\n'
