import icalendar
import os

import pytz

cal0 = 'a_calendar'
cal1 = 'foobar'
cal2 = 'work'
cal3 = 'private'

example_cals = [cal0, cal1, cal2, cal3]

BERLIN = pytz.timezone('Europe/Berlin')
NEW_YORK = pytz.timezone('America/New_York')
LONDON = pytz.timezone('Europe/London')
SAMOA = pytz.timezone('Pacific/Samoa')
SYDNEY = pytz.timezone('Australia/Sydney')
GMTPLUS3 = pytz.timezone('Etc/GMT+3')
# the lucky people in Bogota don't know the pain that is DST
BOGOTA = pytz.timezone('America/Bogota')


LOCALE_BERLIN = {
    'default_timezone': BERLIN,
    'local_timezone': BERLIN,
    'dateformat': '%d.%m.',
    'longdateformat': '%d.%m.%Y',
    'timeformat': '%H:%M',
    'datetimeformat': '%d.%m. %H:%M',
    'longdatetimeformat': '%d.%m.%Y %H:%M',
    'unicode_symbols': True,
    'firstweekday': 0,
    'weeknumbers': False,
}

LOCALE_NEW_YORK = {
    'default_timezone': NEW_YORK,
    'local_timezone': NEW_YORK,
    'timeformat': '%H:%M',
    'dateformat': '%Y/%m/%d',
    'longdateformat': '%Y/%m/%d',
    'datetimeformat': '%Y/%m/%d-%H:%M',
    'longdatetimeformat': '%Y/%m/%d-%H:%M',
    'firstweekday': 6,
    'unicode_symbols': True,
    'weeknumbers': False,
}

LOCALE_SAMOA = {
    'local_timezone': SAMOA,
    'default_timezone': SAMOA,
    'unicode_symbols': True,
}
LOCALE_SYDNEY = {'local_timezone': SYDNEY, 'default_timezone': SYDNEY}

LOCALE_BOGOTA = LOCALE_BERLIN.copy()
LOCALE_BOGOTA['local_timezone'] = BOGOTA
LOCALE_BOGOTA['default_timezone'] = BOGOTA

LOCALE_MIXED = LOCALE_BERLIN.copy()
LOCALE_MIXED['local_timezone'] = BOGOTA


def normalize_component(x):
    x = icalendar.cal.Component.from_ical(x)

    def inner(c):
        contentlines = icalendar.cal.Contentlines()
        for name, value in c.property_items(sorted=True, recursive=False):
            contentlines.append(c.content_line(name, value, sorted=True))
        contentlines.append('')

        return (c.name, contentlines.to_ical(),
                frozenset(inner(sub) for sub in c.subcomponents))

    return inner(x)


def _get_text(event_name):
    directory = '/'.join(__file__.split('/')[:-1]) + '/ics/'
    if directory == '/ics/':
        directory = './ics/'

    with open(os.path.join(directory, event_name + '.ics'), 'rb') as f:
        rv = f.read().decode('utf-8')

    return rv


def _get_vevent_file(event_path):
    directory = '/'.join(__file__.split('/')[:-1]) + '/ics/'
    with open(os.path.join(directory, event_path + '.ics'), 'rb') as f:
        ical = icalendar.Calendar.from_ical(
            f.read()
        )
    for component in ical.walk():
        if component.name == 'VEVENT':
            return component


def _get_ics_filepath(event_name):
    directory = '/'.join(__file__.split('/')[:-1]) + '/ics/'
    if directory == '/ics/':
        directory = './ics/'
    return os.path.join(directory, event_name + '.ics')


def _get_all_vevents_file(event_path):
    directory = '/'.join(__file__.split('/')[:-1]) + '/ics/'
    ical = icalendar.Calendar.from_ical(
        open(os.path.join(directory, event_path + '.ics'), 'rb').read()
    )
    for component in ical.walk():
        if component.name == 'VEVENT':
            yield component
