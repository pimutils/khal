import pytz

from khal.cli import ConfigParser
from khal.cli import Namespace

str_calendars_good = """
[Calendar home]
path = /home/user/somewhere
color = dark blue

[Calendar work]
path = /home/user/somewhereelse
color = dark green
readonly = 0

[Calendar workagain]
path = /home/user/here
readonly = True
"""

str_sqlite_good = """
[sqlite]
path = /home/user/.khal/khal.db
"""

str_locale_good = """
[locale]
local_timezone: Europe/Berlin
default_timezone: America/New_York

timeformat: %H:%M
dateformat: %d.%m.
longdateformat: %d.%m.%Y
datetimeformat: %d.%m. %H:%M
longdatetimeformat: %d.%m.%Y %H:%M

firstweekday: 0
"""

str_default_good = """
[default]
default_command: calendar
debug: 0
"""


goodlocale = Namespace(
    {'dateformat': '%d.%m.',
     'local_timezone': pytz.timezone('Europe/Berlin'),
     'unicode_symbols': True,
     'longdateformat': '%d.%m.%Y',
     'longdatetimeformat': '%d.%m.%Y %H:%M',
     'default_timezone': pytz.timezone('America/New_York'),
     'encoding': 'utf-8',
     'timeformat': '%H:%M',
     'datetimeformat': '%d.%m. %H:%M',
     'firstweekday': 0
     }
)

gooddefault = Namespace(
    {'default_command': 'calendar',
     'debug': 0
     }
)

goodsqlite = Namespace(
    {'path': '/home/user/.khal/khal.db'
     }
)

goodcalendars = [
    Namespace({
        'name': 'home',
        'path': '/home/user/somewhere',
        'color': 'dark blue',
        'readonly': False
    }),
    Namespace({
        'name': 'work',
        'path': '/home/user/somewhereelse',
        'color': 'dark green',
        'readonly': False
    }),

    Namespace({
        'name': 'workagain',
        'path': '/home/user/here',
        'color': '',
        'readonly': True
    })
]


class TestConfigParser(object):
    def test_easy(self, tmpdir):
        goodconf = Namespace(
            {'locale': goodlocale,
             'sqlite': goodsqlite,
             'default': gooddefault,
             'calendars': goodcalendars
             }
        )

        basic_config = (str_calendars_good +
                        str_locale_good +
                        str_sqlite_good +
                        str_default_good)
        tmpdir.join('config').write(basic_config)
        conf_parser = ConfigParser()
        config = conf_parser.parse_config(str(tmpdir) + '/config')
        assert config == goodconf

    def test_no_cal(self, tmpdir, caplog):
        no_cal_config = (str_locale_good +
                         str_sqlite_good +
                         str_default_good)
        tmpdir.join('config').write(no_cal_config)
        conf_parser = ConfigParser()
        config = conf_parser.parse_config(str(tmpdir) + '/config')
        assert "Missing required section 'calendars'" in caplog.text()
        assert config is None
