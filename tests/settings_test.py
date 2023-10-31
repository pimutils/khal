import datetime as dt
import os.path

import pytest
from tzlocal import get_localzone as _get_localzone

from khal.settings import get_config
from khal.settings.exceptions import CannotParseConfigFileError, InvalidSettingsError
from khal.settings.utils import (
    config_checks,
    get_all_vdirs,
    get_color_from_vdir,
    get_unique_name,
    is_color,
)

try:
    # Available from configobj 5.1.0
    from configobj.validate import VdtValueError
except ModuleNotFoundError:
    from validate import VdtValueError

from .utils import LOCALE_BERLIN

PATH = __file__.rsplit('/', 1)[0] + '/configs/'


def get_localzone():
    # this reproduces the code in settings.util for the time being
    import pytz
    return pytz.timezone(str(_get_localzone()))


class TestSettings:
    def test_simple_config(self):
        config = get_config(
            PATH + 'simple.conf',
            _get_color_from_vdir=lambda x: None,
            _get_vdir_type=lambda x: 'calendar',
        )
        comp_config = {
            'calendars': {
                'home': {
                    'path': os.path.expanduser('~/.calendars/home/'), 'readonly': False,
                    'color': None, 'priority': 10, 'type': 'calendar', 'addresses': [''],
                },
                'work': {
                    'path': os.path.expanduser('~/.calendars/work/'), 'readonly': False,
                    'color': None, 'priority': 10, 'type': 'calendar', 'addresses': [''],
                },
            },
            'sqlite': {'path': os.path.expanduser('~/.local/share/khal/khal.db')},
            'locale': LOCALE_BERLIN,
            'default': {
                'default_calendar': None,
                'print_new': 'False',
                'highlight_event_days': False,
                'timedelta': dt.timedelta(days=2),
                'default_event_duration': dt.timedelta(hours=1),
                'default_dayevent_duration': dt.timedelta(days=1),
                'default_event_alarm': dt.timedelta(0),
                'default_dayevent_alarm': dt.timedelta(0),
                'show_all_days': False,
                'enable_mouse': True,
            }
        }
        for key in comp_config:
            assert config[key] == comp_config[key]

    def test_nocalendars(self):
        with pytest.raises(InvalidSettingsError):
            get_config(PATH + 'nocalendars.conf')

    def test_one_level_calendar(self):
        with pytest.raises(InvalidSettingsError):
            get_config(PATH + 'one_level_calendars.conf')

    def test_small(self):
        config = get_config(
            PATH + 'small.conf',
            _get_color_from_vdir=lambda x: None,
            _get_vdir_type=lambda x: 'calendar',
        )
        comp_config = {
            'calendars': {
                'home': {'path': os.path.expanduser('~/.calendars/home/'),
                         'color': 'dark green', 'readonly': False, 'priority': 20,
                         'type': 'calendar', 'addresses': ['']},
                'work': {'path': os.path.expanduser('~/.calendars/work/'),
                         'readonly': True, 'color': None, 'priority': 10,
                         'type': 'calendar', 'addresses': ['user@example.com']}},
            'sqlite': {'path': os.path.expanduser('~/.local/share/khal/khal.db')},
            'locale': {
                'local_timezone': get_localzone(),
                'default_timezone': get_localzone(),
                'timeformat': '%X',
                'dateformat': '%x',
                'longdateformat': '%x',
                'datetimeformat': '%c',
                'longdatetimeformat': '%c',
                'firstweekday': 0,
                'unicode_symbols': True,
                'weeknumbers': False,
            },
            'default': {
                'default_calendar': None,
                'print_new': 'False',
                'highlight_event_days': False,
                'timedelta': dt.timedelta(days=2),
                'default_event_duration': dt.timedelta(hours=1),
                'default_dayevent_duration': dt.timedelta(days=1),
                'show_all_days': False,
                'enable_mouse': True,
                'default_event_alarm': dt.timedelta(0),
                'default_dayevent_alarm': dt.timedelta(0),
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


def test_broken_color(metavdirs):
    path = metavdirs
    newvdir = path + '/cal5/'
    os.makedirs(newvdir)
    with open(newvdir + 'color', 'w') as metafile:
        metafile.write('xxx')
    assert get_color_from_vdir(newvdir) is None


def test_discover(metavdirs):
    test_vdirs = {
        '/cal1/public', '/cal1/private', '/cal2/public',
        '/cal3/home', '/cal3/public', '/cal3/work',
        '/cal4/cfgcolor', '/cal4/dircolor', '/cal4/cfgcolor_again',
        '/cal4/cfgcolor_once_more',
        '/singlecollection',
    }
    path = metavdirs
    assert test_vdirs == {vdir[len(path):] for vdir in get_all_vdirs(path + '/**/*/')}
    assert test_vdirs == {vdir[len(path):] for vdir in get_all_vdirs(path + '/**/')}
    assert test_vdirs == {vdir[len(path):] for vdir in get_all_vdirs(path + '/**/*')}


def test_get_unique_name(metavdirs):
    path = metavdirs
    vdirs = list(get_all_vdirs(path + '/**/'))
    names = []
    for vdir in sorted(vdirs):
        names.append(get_unique_name(vdir, names))
    assert sorted(names) == sorted([
        'my private calendar', 'my calendar', 'public', 'home', 'public1',
        'work', 'cfgcolor', 'cfgcolor_again', 'cfgcolor_once_more', 'dircolor',
        'singlecollection',
    ])


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

    test_config = {
        'calendars': {
            'home': {
                'color': None,
                'path': '/cal3/home',
                'readonly': False,
                'type': 'calendar',
                'priority': 10,
            },
            'my calendar': {
                'color': 'dark blue',
                'path': '/cal1/public',
                'readonly': False,
                'type': 'calendar',
                'priority': 10,
            },
            'my private calendar': {
                'color': '#FF00FF',
                'path': '/cal1/private',
                'readonly': False,
                'type': 'calendar',
                'priority': 10,
            },
            'public1': {
                'color': None,
                'path': '/cal3/public',
                'readonly': False,
                'type': 'calendar',
                'priority': 10,
            },
            'public': {
                'color': None,
                'path': '/cal2/public',
                'readonly': False,
                'type': 'calendar',
                'priority': 10,
            },
            'work': {
                'color': None,
                'path': '/cal3/work',
                'readonly': False,
                'type': 'calendar',
                'priority': 10,
            },
            'cfgcolor': {
                'color': 'dark blue',
                'path': '/cal4/cfgcolor',
                'readonly': False,
                'type': 'calendar',
                'priority': 10,
            },
            'dircolor': {
                'color': 'dark blue',
                'path': '/cal4/dircolor',
                'readonly': False,
                'type': 'calendar',
                'priority': 10,
            },
            'cfgcolor_again': {
                'color': 'dark blue',
                'path': '/cal4/cfgcolor_again',
                'readonly': False,
                'type': 'calendar',
                'priority': 10,
            },
            'cfgcolor_once_more': {
                'color': 'dark blue',
                'path': '/cal4/cfgcolor_once_more',
                'readonly': False,
                'type': 'calendar',
                'priority': 10,
            },

        },
        'default': {'default_calendar': None},
        'locale': {'default_timezone': 'Europe/Berlin', 'local_timezone': 'Europe/Berlin'},
        'sqlite': {'path': '/tmp'},
    }

    assert config['calendars'] == test_config['calendars']
    assert config == test_config


def test_is_color():
    assert is_color('dark blue') == 'dark blue'
    assert is_color('#123456') == '#123456'
    assert is_color('123') == '123'
    with pytest.raises(VdtValueError):
        assert is_color('red') == 'red'
