import pytz
import pytest

from khal.settings import get_config

PATH = __file__.rsplit('/', 1)[0] + '/configs/'


class TestSettings(object):
    def test_simple_config(self):
        config = get_config(PATH + 'simple.conf')
        assert config == {
            'calendars': {
                'home': {'path': '~/.calendars/home/', 'readonly': False},
                'work': {'path': '~/.calendars/work/', 'readonly': False},
            },
            'sqlite': {'path': '$XDG_CACHE_HOME/khal/khal.db'},
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
            },
            'default': {
                'default_command': 'calendar',
                'debug': False,
                'default_calendar': 'home',
            }
        }

    def test_nocalendars(self):
        with pytest.raises(ValueError):
            get_config(PATH + 'nocalendars.conf')
