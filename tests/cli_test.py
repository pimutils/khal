import os
import sys
import datetime
from datetime import timedelta

import pytest
from freezegun import freeze_time
from click.testing import CliRunner

from khal.cli import main_khal, main_ikhal

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
    calendar2 = tmpdir.mkdir('calendar2')
    calendar3 = tmpdir.mkdir('calendar3')

    def inner(command='list', default_calendar=True, days=2, **kwargs):
        if default_calendar:
            default_calendar = 'default_calendar = one'
        else:
            default_calendar = ''
        config.write(config_template.format(
            command=command,
            delta=str(days)+'d',
            calpath=str(calendar), calpath2=str(calendar2), calpath3=str(calendar3),
            default_calendar=default_calendar,
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

[[two]]
path = {calpath2}
color = dark green

[[three]]
path = {calpath3}

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
{default_calendar}
timedelta = {delta}

[sqlite]
path = {dbpath}
'''


def test_direct_modification(runner):
    runner = runner(command='list')

    result = runner.invoke(main_khal, ['list'])
    assert not result.exception
    assert result.output == 'No events\n'

    cal_dt = _get_text('event_dt_simple')
    event = runner.calendars['one'].join('test.ics')
    event.write(cal_dt)
    format = '{start-date-once}{start-date-once-newline}{start-end-time-style}: {title}'
    result = runner.invoke(main_khal, ['list', '--format', format, '09.04.2014'])
    assert not result.exception
    assert result.output == '09.04.2014\n09:30-10:30: An Event\n'

    os.remove(str(event))
    result = runner.invoke(main_khal, ['list'])
    assert not result.exception
    assert result.output == 'No events\n'


def test_simple(runner):
    runner = runner(command='list', days=2)

    result = runner.invoke(main_khal)
    assert not result.exception
    assert result.output == 'No events\n'

    now = datetime.datetime.now().strftime('%d.%m.%Y')
    result = runner.invoke(
        main_khal, 'new {} 18:00 myevent'.format(now).split())
    assert result.output == ''
    assert not result.exception

    result = runner.invoke(main_khal)
    assert 'myevent' in result.output
    assert '18:00' in result.output
    # test show_all_days default value
    assert 'Tomorrow:' not in result.output
    assert not result.exception


def test_simple_color(runner):
    runner = runner(command='list', days=2)

    now = datetime.datetime.now().strftime('%d.%m.%Y')
    result = runner.invoke(main_khal, 'new {} 18:00 myevent'.format(now).split())
    assert result.output == ''
    assert not result.exception

    result = runner.invoke(main_khal, color=True)
    assert not result.exception
    assert '\x1b[34m' in result.output


def test_days(runner):
    runner = runner(command='list', days=9)

    when = (datetime.datetime.now() + timedelta(days=7)).strftime('%d.%m.%Y')
    result = runner.invoke(main_khal, 'new {} 18:00 nextweek'.format(when).split())
    assert result.output == ''
    assert not result.exception

    when = (datetime.datetime.now() + timedelta(days=30)).strftime('%d.%m.%Y')
    result = runner.invoke(main_khal, 'new {} 18:00 nextmonth'.format(when).split())
    assert result.output == ''
    assert not result.exception

    result = runner.invoke(main_khal)
    assert 'nextweek' in result.output
    assert 'nextmonth' not in result.output
    assert '18:00' in result.output
    assert not result.exception


def test_calendar(runner):
    with freeze_time('2015-6-1'):
        runner = runner(command='calendar', days=0)
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
    runner = runner(command='', days=2)

    result = runner.invoke(main_khal)
    assert result.exception
    assert result.exit_code == 1
    assert result.output.startswith('Usage: ')


def test_default_command_nonempty(runner):
    runner = runner(command='list', days=2)

    result = runner.invoke(main_khal)
    assert not result.exception
    assert result.output == 'No events\n'


def test_invalid_calendar(runner):
    runner = runner(command='', days=2)
    result = runner.invoke(
        main_khal, ['new'] + '-a one 18:00 myevent'.split())
    assert not result.exception
    result = runner.invoke(
        main_khal, ['new'] + '-a inexistent 18:00 myevent'.split())
    assert result.exception
    assert result.exit_code == 2
    assert 'Unknown calendar ' in result.output


def test_attach_calendar(runner):
    runner = runner(command='calendar', days=2)
    result = runner.invoke(main_khal, ['printcalendars'])
    assert set(result.output.split('\n')[:3]) == set(['one', 'two', 'three'])
    assert not result.exception
    result = runner.invoke(main_khal, ['printcalendars', '-a', 'one'])
    assert result.output == 'one\n'
    assert not result.exception
    result = runner.invoke(main_khal, ['printcalendars', '-d', 'one'])
    assert set(result.output.split('\n')[:2]) == set(['two', 'three'])
    assert not result.exception


@pytest.mark.parametrize('contents', [
    '',
    'BEGIN:VCALENDAR\nBEGIN:VTODO\nEND:VTODO\nEND:VCALENDAR\n'
])
def test_no_vevent(runner, tmpdir, contents):
    runner = runner(command='list', days=2)
    broken_item = runner.calendars['one'].join('broken_item.ics')
    broken_item.write(contents.encode('utf-8'), mode='wb')

    result = runner.invoke(main_khal)
    assert not result.exception
    assert 'No events' in result.output


def test_printformats(runner):
    runner = runner(command='printformats', days=2)

    result = runner.invoke(main_khal)
    assert '\n'.join(['longdatetimeformat: 21.12.2013 10:09',
                      'datetimeformat: 21.12. 10:09',
                      'longdateformat: 21.12.2013',
                      'dateformat: 21.12.',
                      'timeformat: 10:09',
                      '']) == result.output
    assert not result.exception


def test_repeating(runner):
    runner = runner(command='list', days=2)
    now = datetime.datetime.now().strftime('%d.%m.%Y')
    end_date = datetime.datetime.now() + datetime.timedelta(days=10)
    result = runner.invoke(
        main_khal, 'new {} 18:00 myevent -r weekly -u {}'.format(
            now, end_date.strftime('%d.%m.%Y')).split())
    assert result.output == ''
    assert not result.exception


def test_at(runner):
    runner = runner(command='calendar', days=2)
    now = datetime.datetime.now().strftime('%d.%m.%Y')
    end_date = datetime.datetime.now() + datetime.timedelta(days=10)
    result = runner.invoke(
        main_khal,
        'new {} 18:00 myevent'.format(now, end_date.strftime('%d.%m.%Y')).split())
    result = runner.invoke(main_khal, ['--color', 'at', '--format', '{start-time}{title}', '18:30'])
    assert result.output.startswith('18:00')
    assert not result.exception


def test_list(runner):
    runner = runner(command='calendar', days=2)
    now = datetime.datetime.now().strftime('%d.%m.%Y')
    end_date = datetime.datetime.now() + datetime.timedelta(days=10)
    result = runner.invoke(
        main_khal,
        'new {} 18:00 myevent'.format(now, end_date.strftime('%d.%m.%Y')).split())
    format = '{red}{start-end-time-style}{reset} {title} :: {description}'
    result = runner.invoke(main_khal, ['--color', 'list', '--format', format, '18:30'])
    assert result.output.startswith('\x1b[31m18:00-19:00\x1b[0m myevent :: \x1b[0m\n')
    assert not result.exception


def test_search(runner):
    runner = runner(command='calendar', days=2)
    now = datetime.datetime.now().strftime('%d.%m.%Y')
    result = runner.invoke(main_khal, 'new {} 18:00 myevent'.format(now).split())
    format = '{red}{start-end-time-style}{reset} {title} :: {description}'
    result = runner.invoke(main_khal, ['--color', 'search', '--format', format, 'myevent'])
    assert result.output.startswith('\x1b[34m\x1b[31m18:00')
    assert not result.exception


def test_no_default_new(runner):
    runner = runner(default_calendar=False)
    result = runner.invoke(main_khal, 'new 18:00 beer'.split())
    assert ("Error: Invalid value: No default calendar is configured, "
            "please provide one explicitly.") in result.output
    assert result.exit_code == 2


def test_import(runner, monkeypatch):
    runner = runner()
    result = runner.invoke(main_khal, 'import -a one -a two import file.ics'.split())
    assert result.exception
    assert result.exit_code == 2
    assert 'Can\'t use "--include-calendar" / "-a" more than once' in result.output

    class FakeImport():
        args, kwargs = None, None

        def clean(self):
            self.args, self.kwargs = None, None

        def import_ics(self, *args, **kwargs):
            print('saving args')
            print(args)
            self.args = args
            self.kwargs = kwargs

    fake = FakeImport()
    monkeypatch.setattr('khal.controllers.import_ics', fake.import_ics)
    # as we are not actually parsing the file we want to import, we can use
    # any readable file at all, therefore re-using the configuration file
    result = runner.invoke(main_khal, 'import -a one {}'.format(runner.config).split())
    assert not result.exception
    assert {cal['name'] for cal in fake.args[0].calendars} == {'one'}

    fake.clean()
    result = runner.invoke(main_khal, 'import {}'.format(runner.config).split())
    assert not result.exception
    assert {cal['name'] for cal in fake.args[0].calendars} == {'one', 'two', 'three'}


def test_interactive_command(runner, monkeypatch):
    runner = runner(command='list', days=2)
    token = "hooray"

    def fake_ui(*a, **kw):
        print(token)
        sys.exit(0)

    monkeypatch.setattr('khal.ui.start_pane', fake_ui)

    result = runner.invoke(main_ikhal, ['-a', 'one'])
    assert not result.exception
    assert result.output.strip() == token

    result = runner.invoke(main_khal, ['interactive', '-a', 'one'])
    assert not result.exception
    assert result.output.strip() == token


def test_color_option(runner):
    runner = runner(command='list', days=2)

    result = runner.invoke(main_khal, ['--no-color'])
    assert result.output == 'No events\n'

    result = runner.invoke(main_khal, ['--color'])
    assert 'No events' in result.output
    assert result.output != 'No events\n'


def test_configure_command(runner, monkeypatch):
    e = Exception('Hocus pocus!')

    def hocus_pocus(*a, **kw):
        raise e

    monkeypatch.setattr('khal.configwizard.configwizard', hocus_pocus)

    runner = runner(command='list', days=2)
    runner.config.remove()

    result = runner.invoke(main_khal, ['configure'])
    assert result.exception is e
