import os.path
import datetime as dt
from validate import VdtValueError

import pytest
from tzlocal import get_localzone

from .utils import LOCALE_BERLIN

from khal.settings import get_config
from khal.settings.exceptions import InvalidSettingsError, \
    CannotParseConfigFileError
from khal.settings.utils import get_all_vdirs, get_unique_name, config_checks, \
    get_color_from_vdir, is_color

PATH = __file__.rsplit('/', 1)[0] + '/configs/'


class TestSettings(object):
    def test_simple_config(self):
        config = get_config(
            PATH + 'simple.conf',
            _get_color_from_vdir=lambda x: None,
            _get_vdir_type=lambda x: 'calendar',
        )
        comp_config = {
            'calendars': {
                'home': {'path': os.path.expanduser('~/.calendars/home/'),
                         'readonly': False, 'color': None, 'type': 'calendar'},
                'work': {'path': os.path.expanduser('~/.calendars/work/'),
                         'readonly': False, 'color': None, 'type': 'calendar'},
            },
            'sqlite': {'path': os.path.expanduser('~/.local/share/khal/khal.db')},
            'locale': LOCALE_BERLIN,
            'default': {
                'default_command': 'calendar',
                'default_calendar': None,
                'print_new': 'False',
                'highlight_event_days': False,
                'timedelta': dt.timedelta(days=2),
                'show_all_days': False
            }
        }
        for key in comp_config:
            assert config[key] == comp_config[key]

    def test_nocalendars(self):
        with pytest.raises(InvalidSettingsError):
            get_config(PATH + 'nocalendars.conf')

    def test_small(self):
        config = get_config(
            PATH + 'small.conf',
            _get_color_from_vdir=lambda x: None,
            _get_vdir_type=lambda x: 'calendar',
        )
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
                'unicode_symbols': True,
                'weeknumbers': False,
            },
            'default': {
                'default_calendar': None,
                'default_command': 'calendar',
                'print_new': 'False',
                'highlight_event_days': False,
                'timedelta': dt.timedelta(days=2),
                'show_all_days': False
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

    def test_default_calendar_readonly(self, tmpdir):
        config = """
[calendars]
[[home]]
path = ~/.khal/calendars/home/
color = dark blue
readonly = True
[default]
default_calendar = home
"""
        conf_path = str(tmpdir.join('old.conf'))
        with open(conf_path, 'w+') as conf:
            conf.write(config)
        with pytest.raises(InvalidSettingsError):
            config_checks(get_config(conf_path))


@pytest.fixture
def metavdirs(tmpdir):
    tmpdir = str(tmpdir)
    dirstructure = [
        '/cal1/public/',
        '/cal1/private/',
        '/cal2/public/',
        '/cal3/public/',
        '/cal3/work/',
        '/cal3/home/',
        '/cal4/cfgcolor/',
        '/cal4/dircolor/',
        '/cal4/cfgcolor_again/',
        '/cal4/cfgcolor_once_more/',
    ]
    for one in dirstructure:
        os.makedirs(tmpdir + one)
    filestructure = [
        ('/cal1/public/displayname', 'my calendar'),
        ('/cal1/public/color', 'dark blue'),
        ('/cal1/private/displayname', 'my private calendar'),
        ('/cal1/private/color', '#FF00FF'),
        ('/cal4/dircolor/color', 'dark blue'),
    ]
    for filename, content in filestructure:
        with open(tmpdir + filename, 'w') as metafile:
            metafile.write(content)
    return tmpdir


def test_broken_color(metavdirs):
    path = metavdirs
    newvdir = path + '/cal5/'
    os.makedirs(newvdir)
    with open(newvdir + 'color', 'w') as metafile:
        metafile.write('xxx')
    assert get_color_from_vdir(newvdir) is None


def test_discover(metavdirs):
    path = metavdirs
    vdirs = {vdir[len(path):] for vdir in get_all_vdirs(path + '/*/*')}
    assert vdirs == {
        '/cal1/public', '/cal1/private', '/cal2/public',
        '/cal3/home', '/cal3/public', '/cal3/work',
        '/cal4/cfgcolor', '/cal4/dircolor', '/cal4/cfgcolor_again', '/cal4/cfgcolor_once_more'
    }


def test_get_unique_name(metavdirs):
    path = metavdirs
    vdirs = [vdir for vdir in get_all_vdirs(path + '/*/*')]
    names = list()
    for vdir in sorted(vdirs):
        names.append(get_unique_name(vdir, names))
    assert names == [
        'my private calendar', 'my calendar', 'public', 'home', 'public1',
        'work', 'cfgcolor', 'cfgcolor_again', 'cfgcolor_once_more', 'dircolor',
    ]


def test_config_checks(metavdirs):
    path = metavdirs
    config = {
        'calendars': {
            'default': {'path': path + '/cal[1-3]/*', 'type': 'discover'},
            'calendars_color': {'path': path + '/cal4/*', 'type': 'discover', 'color': 'dark blue'},
        },
        'sqlite': {'path': '/tmp'},
        'locale': {'default_timezone': 'Europe/Berlin', 'local_timezone': 'Europe/Berlin'},
        'default': {'default_calendar': None},
    }
    config_checks(config)
    # cut off the part of the path that changes on each run
    for cal in config['calendars']:
        config['calendars'][cal]['path'] = config['calendars'][cal]['path'][len(metavdirs):]

    assert config == {
        'calendars': {
            'home': {
                'color': None,
                'path': '/cal3/home',
                'readonly': False,
                'type': 'calendar',
            },
            'my calendar': {
                'color': 'dark blue',
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
                'path': '/cal3/public',
                'readonly': False,
                'type': 'calendar',
            },
            'work': {
                'color': None,
                'path': '/cal3/work',
                'readonly': False,
                'type': 'calendar',
            },
            'cfgcolor': {
                'color': 'dark blue',
                'path': '/cal4/cfgcolor',
                'readonly': False,
                'type': 'calendar',
            },
            'dircolor': {
                'color': 'dark blue',
                'path': '/cal4/dircolor',
                'readonly': False,
                'type': 'calendar',
            },
            'cfgcolor_again': {
                'color': 'dark blue',
                'path': '/cal4/cfgcolor_again',
                'readonly': False,
                'type': 'calendar',
            },
            'cfgcolor_once_more': {
                'color': 'dark blue',
                'path': '/cal4/cfgcolor_once_more',
                'readonly': False,
                'type': 'calendar',
            },

        },
        'default': {'default_calendar': None},
        'locale': {'default_timezone': 'Europe/Berlin', 'local_timezone': 'Europe/Berlin'},
        'sqlite': {'path': '/tmp'},
    }


def test_is_color():
    assert is_color('dark blue') == 'dark blue'
    assert is_color('#123456') == '#123456'
    assert is_color('123') == '123'
    with pytest.raises(VdtValueError):
        assert is_color('red') == 'red'
