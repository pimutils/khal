# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:

from pkg_resources import parse_version
import pytest
import click
from click.testing import CliRunner

from khal.cli import main_khal


@pytest.fixture
def runner():
    return CliRunner()

config_template = '''
[calendars]
[[one]]
path = {calpath}
color = dark blue

[locale]
local_timezone = Europe/Berlin
default_timezone = America/New_York

timeformat = %H:%M
dateformat = %d.%m.
longdateformat = %d.%m.%Y
datetimeformat =  %d.%m. %H:%M
longdatetimeformat = %d.%m.%Y %H:%M

firstweekday = 0

[default]
default_command = {command}
default_calendar = one
debug = 1'''


def test_simple(tmpdir, runner):
    config = tmpdir.join('config.ini')
    calendar = tmpdir.mkdir('calendar')

    config.write(config_template.format(calpath=str(calendar),
                                        command='NOPE'))
    conf_arg = ['-c', str(config)]
    result = runner.invoke(main_khal, conf_arg + ['agenda'])
    assert not result.exception
    assert result.output == 'No events\n'

    from .event_test import cal_dt
    calendar.join('test.ics').write('\n'.join(cal_dt))
    result = runner.invoke(main_khal, conf_arg + ['agenda', '09.04.2014'])
    assert not result.exception
    assert result.output == u'09.04.2014\n09:30-10:30: An Event\n'


def test_default_command_empty(tmpdir, runner):
    config = tmpdir.join('config.ini')
    calendar = tmpdir.mkdir('calendar')
    config.write(config_template.format(calpath=str(calendar), command=''))

    conf_arg = ['-c', str(config)]
    result = runner.invoke(main_khal, conf_arg)
    assert result.exception
    assert result.exit_code == 1
    assert result.output.startswith('Usage: ')


def test_default_command_nonempty(tmpdir, runner):
    config = tmpdir.join('config.ini')
    calendar = tmpdir.mkdir('calendar')
    config.write(config_template.format(calpath=str(calendar),
                                        command='agenda'))

    conf_arg = ['-c', str(config)]
    result = runner.invoke(main_khal, conf_arg)
    assert not result.exception
    assert result.output == 'No events\n'
