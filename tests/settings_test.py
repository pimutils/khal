import os.path

import pytz
import pytest

from tzlocal import get_localzone

from khal.settings import get_config
from khal.settings.exceptions import InvalidSettingsError, \
    CannotParseConfigFileError
from khal.settings.utils import get_all_vdirs, get_unique_name, config_checks

PATH = __file__.rsplit('/', 1)[0] + '/configs/'


class TestSettings(object):
    def test_simple_config(self):
        config = get_config(PATH + 'simple.conf')
        comp_config = {
            'calendars': {
                'home': {'path': os.path.expanduser('~/.calendars/home/'),
                         'readonly': False, 'color': None, 'type': 'calendar'},
                'work': {'path': os.path.expanduser('~/.calendars/work/'),
                         'readonly': False, 'color': None, 'type': 'calendar'},
            },
            'sqlite': {'path': os.path.expanduser('~/.local/share/khal/khal.db')},
            'locale': {
                'local_timezone': pytz.timezone('Europe/Berlin'),
                'default_timezone': pytz.timezone('Europe/Berlin'),
                'timeformat': '%H:%M',
                'dateformat': '%d.%m.',
                'longdateformat': '%d.%m.%Y',
                'datetimeformat': '%d.%m. %H:%M',
                'longdatetimeformat': '%d.%m.%Y %H:%M',
                'firstweekday': 0,
                'encoding': 'utf-8',
                'unicode_symbols': True,
                'weeknumbers': False,
            },
            'default': {
                'default_command': 'calendar',
                'default_calendar': None,
                'show_all_days': False,
                'print_new': 'False',
                'days': 2,
                'highlight_event_days': False
            }
        }
        for key in comp_config:
            assert config[key] == comp_config[key]

    def test_nocalendars(self):
        with pytest.raises(InvalidSettingsError):
            get_config(PATH + 'nocalendars.conf')

    def test_small(self):
        config = get_config(PATH + 'small.conf')
        comp_config = {
            'calendars': {
                'home': {'path': os.path.expanduser('~/.calendars/home/'),
                         'color': 'dark green', 'readonly': False,
                         'type': 'calendar'},
                'work': {'path': os.path.expanduser('~/.calendars/work/'),
                         'readonly': True, 'color': None,
                         'type': 'calendar'}},
            'sqlite': {'path': os.path.expanduser('~/.local/share/khal/khal.db')},
            'locale': {
                'local_timezone': get_localzone(),
                'default_timezone': get_localzone(),
                'timeformat': '%H:%M',
                'dateformat': '%d.%m.',
                'longdateformat': '%d.%m.%Y',
                'datetimeformat': '%d.%m. %H:%M',
                'longdatetimeformat': '%d.%m.%Y %H:%M',
                'firstweekday': 0,
                'encoding': 'utf-8',
                'unicode_symbols': True,
                'weeknumbers': False,
            },
            'default': {
                'default_calendar': None,
                'default_command': 'calendar',
                'print_new': 'False',
                'show_all_days': False,
                'days': 2,
                'highlight_event_days': False
            }
        }
        for key in comp_config:
            assert config[key] == comp_config[key]

    def test_old_config(self, tmpdir):
        old_config = """
[Calendar home]
path: ~/.khal/calendars/home/
color: dark blue
[sqlite]
path: ~/.khal/khal.db
[locale]
timeformat: %H:%M
dateformat: %d.%m.
longdateformat: %d.%m.%Y
[default]
default_command: calendar
"""
        conf_path = str(tmpdir.join('old.conf'))
        with open(conf_path, 'w+') as conf:
            conf.write(old_config)
        with pytest.raises(CannotParseConfigFileError):
            get_config(conf_path)

    def test_extra_sections(self, tmpdir):
        config = """
[calendars]
[[home]]
path = ~/.khal/calendars/home/
color = dark blue
unknown = 42
[unknownsection]
foo = bar
"""
        conf_path = str(tmpdir.join('old.conf'))
        with open(conf_path, 'w+') as conf:
            conf.write(config)
        get_config(conf_path)
        # FIXME test for log entries


@pytest.fixture
def metavdirs(tmpdir):
    tmpdir = str(tmpdir)
    dirstructure = [
        '/cal1/public/',
        '/cal1/private/',
        '/cal2/public/',
        '/dir/cal3/public/',
        '/dir/cal3/work/',
        '/dir/cal3/home/',
    ]
    for one in dirstructure:
        os.makedirs(tmpdir + one)
    filestructure = [
        ('/cal1/public/displayname', 'my calendar'),
        ('/cal1/public/color', 'red'),
        ('/cal1/private/displayname', 'my private calendar'),
        ('/cal1/private/color', '#FF00FF'),
    ]
    for filename, content in filestructure:
        with open(tmpdir + filename, 'w') as metafile:
            metafile.write(content)
    return tmpdir


def test_discover(metavdirs):
    path = metavdirs
    vdirs = {vdir[len(path):] for vdir in get_all_vdirs(path)}
    assert vdirs == {
        '/cal1/public', '/cal1/private', '/cal2/public', '/dir/cal3/home',
        '/dir/cal3/public', '/dir/cal3/work'
    }


def test_get_unique_name(metavdirs):
    path = metavdirs
    vdirs = [vdir for vdir in get_all_vdirs(path)]
    names = list()
    for vdir in sorted(vdirs):
        names.append(get_unique_name(vdir, names))
    assert names == ['my private calendar', 'my calendar', 'public', 'home', 'public1', 'work']


def test_config_checks(metavdirs):
    path = metavdirs
    config = {'calendars': {'default': {'path': path, 'type': 'discover'}},
              'sqlite': {'path': '/tmp'},
              'locale': {'default_timezone': 'Europe/Berlin', 'local_timezone': 'Europe/Berlin'},
              'default': {'default_calendar': None},
              }
    config_checks(config)
    for cal in ['home', 'my calendar', 'my private calendar', 'work', 'public1', 'public']:
        config['calendars'][cal]['path'] = config['calendars'][cal]['path'][len(metavdirs):]
    assert config == {
        'calendars': {
            'home': {
                'color': None,
                'path': '/dir/cal3/home',
                'readonly': False,
                'type': 'calendar',
            },
            'my calendar': {
                'color': 'red',
                'path': '/cal1/public',
                'readonly': False,
                'type': 'calendar',
            },
            'my private calendar': {
                'color': '#FF00FF',
                'path': '/cal1/private',
                'readonly': False,
                'type': 'calendar',
            },
            'public': {
                'color': None,
                'path': '/cal2/public',
                'readonly': False,
                'type': 'calendar',
            },
            'public1': {
                'color': None,
                'path': '/dir/cal3/public',
                'readonly': False,
                'type': 'calendar',
            },
            'work': {
                'color': None,
                'path': '/dir/cal3/work',
                'readonly': False,
                'type': 'calendar',
            },
        },
        'default': {'default_calendar': None},
        'locale': {'default_timezone': 'Europe/Berlin', 'local_timezone': 'Europe/Berlin'},
        'sqlite': {'path': '/tmp'},
    }
