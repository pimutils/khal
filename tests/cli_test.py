import datetime as dt
import os
import sys

import pytest
from click.testing import CliRunner
from freezegun import freeze_time
from khal.cli import main_ikhal, main_khal

from .utils import _get_ics_filepath, _get_text


class CustomCliRunner(CliRunner):
    def __init__(self, config_file, db=None, calendars=None,
                 xdg_data_home=None, xdg_config_home=None, tmpdir=None, **kwargs):
        self.config_file = config_file
        self.db = db
        self.calendars = calendars
        self.xdg_data_home = xdg_data_home
        self.xdg_config_home = xdg_config_home
        self.tmpdir = tmpdir

        super(CustomCliRunner, self).__init__(**kwargs)

    def invoke(self, cli, args=None, *a, **kw):
        args = ['-c', str(self.config_file)] + (args or [])
        return super(CustomCliRunner, self).invoke(cli, args, *a, **kw)


@pytest.fixture
def runner(tmpdir, monkeypatch):
    db = tmpdir.join('khal.db')
    calendar = tmpdir.mkdir('calendar')
    calendar2 = tmpdir.mkdir('calendar2')
    calendar3 = tmpdir.mkdir('calendar3')

    xdg_data_home = tmpdir.join('vdirs')
    xdg_config_home = tmpdir.join('.config')
    config_file = xdg_config_home.join('khal').join('config')

    # TODO create a vdir config on disk and let vdirsyncer actually read it
    monkeypatch.setattr('vdirsyncer.cli.config.load_config', lambda: Config())
    monkeypatch.setattr('xdg.BaseDirectory.xdg_data_home', str(xdg_data_home))
    monkeypatch.setattr('xdg.BaseDirectory.xdg_config_home', str(xdg_config_home))
    monkeypatch.setattr('xdg.BaseDirectory.xdg_config_dirs', [str(xdg_config_home)])

    def inner(print_new=False, default_calendar=True, days=2, **kwargs):
        if default_calendar:
            default_calendar = 'default_calendar = one'
        else:
            default_calendar = ''
        if not os.path.exists(str(xdg_config_home.join('khal'))):
            os.makedirs(str(xdg_config_home.join('khal')))
        config_file.write(config_template.format(
            delta=str(days) + 'd',
            calpath=str(calendar), calpath2=str(calendar2), calpath3=str(calendar3),
            default_calendar=default_calendar,
            print_new=print_new,
            dbpath=str(db), **kwargs))
        runner = CustomCliRunner(
            config_file=config_file, db=db, calendars=dict(one=calendar),
            xdg_data_home=xdg_data_home, xdg_config_home=xdg_config_home,
            tmpdir=tmpdir,
        )
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
{default_calendar}
timedelta = {delta}
print_new = {print_new}

[sqlite]
path = {dbpath}
'''


def test_direct_modification(runner):
    runner = runner()

    result = runner.invoke(main_khal, ['list'])
    assert result.output == 'No events\n'
    assert not result.exception

    cal_dt = _get_text('event_dt_simple')
    event = runner.calendars['one'].join('test.ics')
    event.write(cal_dt)
    format = '{start-end-time-style}: {title}'
    args = ['list', '--format', format, '--day-format', '', '09.04.2014']
    result = runner.invoke(main_khal, args)
    assert not result.exception
    assert result.output == '09:30-10:30: An Event\n'

    os.remove(str(event))
    result = runner.invoke(main_khal, ['list'])
    assert not result.exception
    assert result.output == 'No events\n'


def test_simple(runner):
    runner = runner(days=2)
    result = runner.invoke(main_khal, ['list'])
    assert not result.exception
    assert result.output == 'No events\n'

    now = dt.datetime.now().strftime('%d.%m.%Y')
    result = runner.invoke(
        main_khal, 'new {} 18:00 myevent'.format(now).split())
    assert result.output == ''
    assert not result.exception

    result = runner.invoke(main_khal, ['list'])
    print(result.output)
    assert 'myevent' in result.output
    assert '18:00' in result.output
    # test show_all_days default value
    assert 'Tomorrow:' not in result.output
    assert not result.exception


def test_simple_color(runner):
    runner = runner(days=2)
    now = dt.datetime.now().strftime('%d.%m.%Y')
    result = runner.invoke(main_khal, 'new {} 18:00 myevent'.format(now).split())
    assert result.output == ''
    assert not result.exception

    result = runner.invoke(main_khal, ['list'], color=True)
    assert not result.exception
    assert '\x1b[34m' in result.output


def test_days(runner):
    runner = runner(days=9)

    when = (dt.datetime.now() + dt.timedelta(days=7)).strftime('%d.%m.%Y')
    result = runner.invoke(main_khal, 'new {} 18:00 nextweek'.format(when).split())
    assert result.output == ''
    assert not result.exception

    when = (dt.datetime.now() + dt.timedelta(days=30)).strftime('%d.%m.%Y')
    result = runner.invoke(main_khal, 'new {} 18:00 nextmonth'.format(when).split())
    assert result.output == ''
    assert not result.exception

    result = runner.invoke(main_khal, ['list'])
    assert 'nextweek' in result.output
    assert 'nextmonth' not in result.output
    assert '18:00' in result.output
    assert not result.exception


def test_notstarted(runner):
    with freeze_time('2015-6-1 15:00'):
        runner = runner(days=2)
        for command in [
                'new 30.5.2015 5.6.2015 long event',
                'new 2.6.2015 4.6.2015 two day event',
                'new 1.6.2015 14:00 18:00 four hour event',
                'new 1.6.2015 16:00 17:00 one hour event',
                'new 2.6.2015 10:00 13:00 three hour event',
        ]:
            result = runner.invoke(main_khal, command.split())
            assert not result.exception

        result = runner.invoke(main_khal, 'list now'.split())
        assert result.output == \
            """Today, 01.06.2015
↔ long event
14:00-18:00 four hour event
16:00-17:00 one hour event
Tomorrow, 02.06.2015
↔ long event
↦ two day event
10:00-13:00 three hour event
Wednesday, 03.06.2015
↔ long event
↔ two day event
"""
        assert not result.exception
        result = runner.invoke(main_khal, 'list now --notstarted'.split())
        assert result.output == \
            """Today, 01.06.2015
16:00-17:00 one hour event
Tomorrow, 02.06.2015
↦ two day event
10:00-13:00 three hour event
Wednesday, 03.06.2015
↔ two day event
"""
        assert not result.exception

        result = runner.invoke(main_khal, 'list now --once'.split())
        assert result.output == \
            """Today, 01.06.2015
↔ long event
14:00-18:00 four hour event
16:00-17:00 one hour event
Tomorrow, 02.06.2015
↦ two day event
10:00-13:00 three hour event
"""
        assert not result.exception

        result = runner.invoke(main_khal, 'list now --once --notstarted'.split())
        assert result.output == \
            """Today, 01.06.2015
16:00-17:00 one hour event
Tomorrow, 02.06.2015
↦ two day event
10:00-13:00 three hour event
"""
        assert not result.exception


def test_calendar(runner):
    with freeze_time('2015-6-1'):
        runner = runner(days=0)
        result = runner.invoke(main_khal, ['calendar'])
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


def test_long_calendar(runner):
    with freeze_time('2015-6-1'):
        runner = runner(days=100)
        result = runner.invoke(main_khal, ['calendar'])
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
            "     7  8  9 10 11 12 13     ",
            "    14 15 16 17 18 19 20     ",
            "    21 22 23 24 25 26 27     ",
            "Oct 28 29 30  1  2  3  4     ",
            "",
        ])
        assert result.output == output


def test_default_command_empty(runner):
    runner = runner(days=2)

    result = runner.invoke(main_khal)
    assert result.exception
    assert result.exit_code == 2
    assert result.output.startswith('Usage: ')


def test_invalid_calendar(runner):
    runner = runner(days=2)
    result = runner.invoke(
        main_khal, ['new'] + '-a one 18:00 myevent'.split())
    assert not result.exception
    result = runner.invoke(
        main_khal, ['new'] + '-a inexistent 18:00 myevent'.split())
    assert result.exception
    assert result.exit_code == 2
    assert 'Unknown calendar ' in result.output


def test_attach_calendar(runner):
    runner = runner(days=2)
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
    runner = runner(days=2)
    broken_item = runner.calendars['one'].join('broken_item.ics')
    broken_item.write(contents.encode('utf-8'), mode='wb')

    result = runner.invoke(main_khal, ['list'])
    assert not result.exception
    assert 'No events' in result.output


def test_printformats(runner):
    runner = runner(days=2)

    result = runner.invoke(main_khal, ['printformats'])
    assert '\n'.join(['longdatetimeformat: 21.12.2013 21:45',
                      'datetimeformat: 21.12. 21:45',
                      'longdateformat: 21.12.2013',
                      'dateformat: 21.12.',
                      'timeformat: 21:45',
                      '']) == result.output
    assert not result.exception


# "see #810"
@pytest.mark.xfail
def test_repeating(runner):
    runner = runner(days=2)
    now = dt.datetime.now().strftime('%d.%m.%Y')
    end_date = dt.datetime.now() + dt.timedelta(days=10)
    result = runner.invoke(
        main_khal, 'new {} 18:00 myevent -r weekly -u {}'.format(
            now, end_date.strftime('%d.%m.%Y')).split())
    assert not result.exception
    assert result.output == ''


def test_at(runner):
    runner = runner(days=2)
    now = dt.datetime.now().strftime('%d.%m.%Y')
    end_date = dt.datetime.now() + dt.timedelta(days=10)
    result = runner.invoke(
        main_khal,
        'new {} {} 18:00 myevent'.format(now, end_date.strftime('%d.%m.%Y')).split())
    args = ['--color', 'at', '--format', '{start-time}{title}', '--day-format', '', '18:30']
    result = runner.invoke(main_khal, args)
    assert not result.exception
    assert result.output.startswith('myevent')


def test_at_day_format(runner):
    runner = runner(days=2)
    now = dt.datetime.now().strftime('%d.%m.%Y')
    end_date = dt.datetime.now() + dt.timedelta(days=10)
    result = runner.invoke(
        main_khal,
        'new {} {} 18:00 myevent'.format(now, end_date.strftime('%d.%m.%Y')).split())
    args = ['--color', 'at', '--format', '{start-time}{title}', '--day-format', '{name}', '18:30']
    result = runner.invoke(main_khal, args)
    assert not result.exception
    assert result.output.startswith('Today\x1b[0m\nmyevent')


def test_list(runner):
    runner = runner(days=2)
    now = dt.datetime.now().strftime('%d.%m.%Y')
    end_date = dt.datetime.now() + dt.timedelta(days=10)
    result = runner.invoke(
        main_khal,
        'new {} 18:00 myevent'.format(now, end_date.strftime('%d.%m.%Y')).split())
    format = '{red}{start-end-time-style}{reset} {title} :: {description}'
    args = ['--color', 'list', '--format', format, '--day-format', 'header', '18:30']
    result = runner.invoke(main_khal, args)
    expected = 'header\x1b[0m\n\x1b[31m18:00-19:00\x1b[0m myevent :: \x1b[0m\n'
    assert not result.exception
    assert result.output.startswith(expected)


def test_search(runner):
    runner = runner(days=2)
    now = dt.datetime.now().strftime('%d.%m.%Y')
    result = runner.invoke(main_khal, 'new {} 18:00 myevent'.format(now).split())
    format = '{red}{start-end-time-style}{reset} {title} :: {description}'
    result = runner.invoke(main_khal, ['--color', 'search', '--format', format, 'myevent'])
    assert not result.exception
    assert result.output.startswith('\x1b[34m\x1b[31m18:00')


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
    result = runner.invoke(main_khal, 'import -a one {}'.format(runner.config_file).split())
    assert not result.exception
    assert {cal['name'] for cal in fake.args[0].calendars} == {'one'}

    fake.clean()
    result = runner.invoke(main_khal, 'import {}'.format(runner.config_file).split())
    assert not result.exception
    assert {cal['name'] for cal in fake.args[0].calendars} == {'one', 'two', 'three'}


def test_import_proper(runner):
    runner = runner()
    result = runner.invoke(main_khal, ['import', _get_ics_filepath('cal_d')], input='0\ny\n')
    assert result.output.startswith('09.04.-09.04. An Event')
    assert not result.exception
    result = runner.invoke(main_khal, ['search', 'Event'])
    assert result.output == '09.04.-09.04. An Event\n'


def test_import_proper_invalid_timezone(runner):
    runner = runner()
    result = runner.invoke(
        main_khal, ['import', _get_ics_filepath('invalid_tzoffset')], input='0\ny\n')
    assert result.output.startswith(
        'warning: Invalid timezone offset encountered, timezone information may be wrong')
    assert not result.exception
    result = runner.invoke(main_khal, ['search', 'Event'])
    assert result.output.startswith(
        'warning: Invalid timezone offset encountered, timezone information may be wrong')
    assert '02.12. 08:00-02.12. 09:30 Some event' in result.output


def test_import_invalid_choice_and_prefix(runner):
    runner = runner()
    result = runner.invoke(main_khal, ['import', _get_ics_filepath('cal_d')], input='9\nth\ny\n')
    assert result.output.startswith('09.04.-09.04. An Event')
    assert result.output.find('invalid choice') == 125
    assert not result.exception
    result = runner.invoke(main_khal, ['search', 'Event'])
    assert result.output == '09.04.-09.04. An Event\n'


def test_import_from_stdin(runner, monkeypatch):
    ics_data = 'This is some really fake icalendar data'

    class FakeImport():
        args, kwargs = None, None
        call_count = 0

        def clean(self):
            self.args, self.kwargs = None, None

        def import_ics(self, *args, **kwargs):
            print('saving args')
            print(args)
            self.call_count += 1
            self.args = args
            self.kwargs = kwargs

    importer = FakeImport()
    monkeypatch.setattr('khal.controllers.import_ics', importer.import_ics)
    runner = runner()
    result = runner.invoke(main_khal, ['import'], input=ics_data)

    assert not result.exception
    assert importer.call_count == 1
    assert importer.kwargs['ics'] == ics_data


def test_interactive_command(runner, monkeypatch):
    runner = runner(days=2)
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
    runner = runner(days=2)

    result = runner.invoke(main_khal, ['--no-color', 'list'])
    assert result.output == 'No events\n'

    result = runner.invoke(main_khal, ['--color', 'list'])
    assert 'No events' in result.output
    assert result.output != 'No events\n'


def choices(dateformat=0, timeformat=0,
            parse_vdirsyncer_conf=True,
            create_vdir=False,
            write_config=True):
    """helper function to generate input for testing `configure`"""
    confirm = {True: 'y', False: 'n'}

    out = [
        str(dateformat), str(timeformat),
        confirm[parse_vdirsyncer_conf],
    ]
    if not parse_vdirsyncer_conf:
        out.append(confirm[create_vdir])
    out.append(confirm[write_config])
    return '\n'.join(out)


class Config():
    """helper class for mocking vdirsyncer's config objects"""
    # TODO crate a vdir config on disk and let vdirsyncer actually read it
    storages = {
        'home_calendar_local': {
            'type': 'filesystem',
            'instance_name': 'home_calendar_local',
            'path': '~/.local/share/calendars/home/',
            'fileext': '.ics',
        },
        'events_local': {
            'type': 'filesystem',
            'instance_name': 'events_local',
            'path': '~/.local/share/calendars/events/',
            'fileext': '.ics',
        },
        'home_calendar_remote': {
            'type': 'caldav',
            'url': 'https://some.url/caldav',
            'username': 'foo',
            'password.fetch': ['command', 'get_secret'],
            'instance_name': 'home_calendar_remote',
        },
        'home_contacts_remote': {
            'type': 'carddav',
            'url': 'https://another.url/caldav',
            'username': 'bar',
            'password.fetch': ['command', 'get_secret'],
            'instance_name': 'home_contacts_remote',
        },
        'home_contacts_local': {
            'type': 'filesystem',
            'instance_name': 'home_contacts_local',
            'path': '~/.local/share/contacts/',
            'fileext': '.vcf',
        },
        'events_remote': {
            'type': 'http',
            'instance_name': 'events_remote',
            'url': 'http://list.of/events/',
        },
    }


def test_configure_command(runner):
    runner_factory = runner
    runner = runner()
    runner.config_file.remove()

    result = runner.invoke(main_khal, ['configure'], input=choices())
    assert 'Successfully wrote configuration to {}'.format(runner.config_file) in result.output
    assert result.exit_code == 0
    with open(str(runner.config_file)) as f:
        actual_config = ''.join(f.readlines())

    assert actual_config == '''[calendars]

[[events_local]]
path = ~/.local/share/calendars/events/*
type = discover

[[home_calendar_local]]
path = ~/.local/share/calendars/home/*
type = discover

[[home_contacts_local]]
path = ~/.local/share/contacts/*
type = discover

[locale]
timeformat = %H:%M
dateformat = %Y-%m-%d
longdateformat = %Y-%m-%d
datetimeformat = %Y-%m-%d %H:%M
longdatetimeformat = %Y-%m-%d %H:%M
'''

    # if aborting, no config file should be written
    runner = runner_factory()
    assert os.path.exists(str(runner.config_file))
    runner.config_file.remove()
    assert not os.path.exists(str(runner.config_file))

    result = runner.invoke(main_khal, ['configure'], input=choices(write_config=False))
    assert 'aborted' in result.output
    assert result.exit_code == 1


def test_print_ics_command(runner):
    runner = runner()
    # Input is empty and loading from stdin
    result = runner.invoke(main_khal, ['printics', '-'])
    assert result.exception

    # Non existing file
    result = runner.invoke(main_khal, ['printics', 'nonexisting_file'])
    assert result.exception
    assert (
        'Error: Invalid value for "ics": Could not open file: ' in result.output or
        'Error: Invalid value for "[ICS]": Could not open file:'
        in result.output)

    # Run on test files
    result = runner.invoke(main_khal, ['printics', _get_ics_filepath('cal_d')])
    assert not result.exception
    result = runner.invoke(main_khal, ['printics', _get_ics_filepath('cal_dt_two_tz')])
    assert not result.exception

    # Test with some nice format strings
    form = '{title}\t{description}\t{start}\t{start-long}\t{start-date}' \
           '\t{start-date-long}\t{start-time}\t{end}\t{end-long}\t{end-date}' \
           '\t{end-date-long}\t{end-time}\t{repeat-symbol}\t{description}' \
           '\t{description-separator}\t{location}\t{calendar}' \
           '\t{calendar-color}\t{start-style}\t{to-style}\t{end-style}' \
           '\t{start-end-time-style}\t{end-necessary}\t{end-necessary-long}'
    result = runner.invoke(main_khal, [
        'printics', '-f', form, _get_ics_filepath('cal_dt_two_tz')])
    assert not result.exception
    assert 24 == len(result.output.split('\t'))
    result = runner.invoke(main_khal, [
        'printics', '-f', form, _get_ics_filepath('cal_dt_two_tz')])
    assert not result.exception
    assert 24 == len(result.output.split('\t'))


def test_printics_read_from_stdin(runner):
    runner = runner(command='printics')
    result = runner.invoke(main_khal, ['printics'], input=_get_text('cal_d'))
    assert not result.exception
    assert '1 events found in stdin input\n An Event\n' in result.output


def test_configure_command_config_exists(runner):
    runner = runner()
    result = runner.invoke(main_khal, ['configure'], input=choices())
    assert 'Found an existing' in result.output
    assert result.exit_code == 1


def test_configure_command_create_vdir(runner):
    runner = runner()
    runner.config_file.remove()
    runner.xdg_config_home.remove()

    result = runner.invoke(
        main_khal, ['configure'],
        input=choices(parse_vdirsyncer_conf=False, create_vdir=True),
    )
    assert 'Successfully wrote configuration to {}'.format(str(runner.config_file)) in result.output
    assert result.exit_code == 0
    with open(str(runner.config_file)) as f:
        actual_config = ''.join(f.readlines())

    assert actual_config == '''[calendars]

[[private]]
path = {}/khal/calendars/private
type = calendar

[locale]
timeformat = %H:%M
dateformat = %Y-%m-%d
longdateformat = %Y-%m-%d
datetimeformat = %Y-%m-%d %H:%M
longdatetimeformat = %Y-%m-%d %H:%M
'''.format(runner.xdg_data_home)

    # running configure again, should yield another vdir path, as the old
    # one still exists
    runner.config_file.remove()
    result = runner.invoke(
        main_khal, ['configure'],
        input=choices(parse_vdirsyncer_conf=False, create_vdir=True),
    )
    assert 'Successfully wrote configuration to {}'.format(str(runner.config_file)) in result.output
    assert result.exit_code == 0
    with open(str(runner.config_file)) as f:
        actual_config = ''.join(f.readlines())

    assert '{}/khal/calendars/private1' .format(runner.xdg_data_home) in actual_config


def test_configure_command_cannot_write_config_file(runner):
    runner = runner()
    runner.config_file.remove()
    os.chmod(str(runner.xdg_config_home), 555)
    result = runner.invoke(main_khal, ['configure'], input=choices())
    assert result.exit_code == 1


def test_configure_command_cannot_create_vdir(runner):
    runner = runner()
    runner.config_file.remove()
    os.mkdir(str(runner.xdg_data_home), mode=555)
    result = runner.invoke(
        main_khal, ['configure'],
        input=choices(parse_vdirsyncer_conf=False, create_vdir=True),
    )
    assert 'Exiting' in result.output
    assert result.exit_code == 1


def test_configure_no_vdir(runner):
    runner = runner()
    runner.config_file.remove()
    result = runner.invoke(
        main_khal, ['configure'],
        input=choices(parse_vdirsyncer_conf=False, create_vdir=False),
    )
    assert 'khal will not be usable like this' in result.output
    assert result.exit_code == 0
    assert not result.exception


def test_edit(runner):
    runner = runner()
    result = runner.invoke(main_khal, ['list'])
    assert not result.exception
    assert result.output == 'No events\n'

    for name in ['event_dt_simple', 'event_d_15']:
        cal_dt = _get_text(name)
        event = runner.calendars['one'].join('{}.ics'.format(name))
        event.write(cal_dt)

    format = '{start-end-time-style}: {title}'
    result = runner.invoke(
        main_khal, ['edit', '--show-past', 'Event'], input='s\nGreat Event\nn\nn\n')
    assert not result.exception

    args = ['list', '--format', format, '--day-format', '', '09.04.2014']
    result = runner.invoke(main_khal, args)
    assert '09:30-10:30: Great Event' in result.output
    assert not result.exception

    args = ['list', '--format', format, '--day-format', '', '09.04.2015']
    result = runner.invoke(main_khal, args)
    assert ': An Event' in result.output
    assert not result.exception


def test_new(runner):
    runner = runner(print_new='path')

    result = runner.invoke(main_khal, 'new 13.03.2016 3d Visit'.split())
    assert not result.exception
    assert result.output.endswith('.ics\n')
    assert result.output.startswith(str(runner.tmpdir))


@freeze_time('2015-6-1 8:00')
def test_new_interactive(runner):
    runner = runner(print_new='path')

    result = runner.invoke(
        main_khal, 'new -i'.split(),
        'Another event\n13:00 17:00\n\nNone\nn\n'
    )
    assert not result.exception
    assert result.exit_code == 0


def test_debug(runner):
    runner = runner()
    result = runner.invoke(main_khal, ['-v', 'debug', 'printformats'])
    assert result.output.startswith('debug: khal 0.')
    assert 'using the config file at' in result.output
    assert 'debug: Using config:\ndebug: [calendars]' in result.output
    assert not result.exception


@freeze_time('2015-6-1 8:00')
def test_new_interactive_extensive(runner):
    runner = runner(print_new='path', default_calendar=False)

    result = runner.invoke(
        main_khal, 'new -i 15:00 15:30'.split(),
        '?\ninvalid\ntwo\n'
        'Unicce Name\n'
        '\n'
        'Europe/London\n'
        'bar\n'
        'l\non a boat\n'
        'p\nweekly\n'
        '1.1.2018\n'
        'a\n30m\n'
        'c\nwork\n'
        'n\n'
    )
    assert not result.exception
    assert result.exit_code == 0
