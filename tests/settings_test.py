import os.path

import pytz
import pytest

from tzlocal import get_localzone

from khal.settings import get_config, InvalidSettingsError

PATH = __file__.rsplit('/', 1)[0] + '/configs/'


class TestSettings(object):
    def test_simple_config(self):
        config = get_config(PATH + 'simple.conf')
        assert config == {
            'calendars': {
                'home': {'path': os.path.expanduser('~/.calendars/home/'), 'readonly': False, 'color': ''},
                'work': {'path': os.path.expanduser('~/.calendars/work/'), 'readonly': False, 'color': ''},
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
                'debug': False,
                'default_calendar': 'home',
            }
        }

    def test_nocalendars(self):
        with pytest.raises(InvalidSettingsError):
            get_config(PATH + 'nocalendars.conf')

    def test_small(self):
        config = get_config(PATH + 'small.conf')
        assert config == {
            'calendars': {
                'home': {'path': os.path.expanduser('~/.calendars/home/'), 'color': 'dark green', 'readonly': False},
                'work': {'path': os.path.expanduser('~/.calendars/work/'), 'readonly': True, 'color': ''}},
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
                'default_command': 'calendar',
                'debug': False,
                'default_calendar': 'home',
            }
        }
