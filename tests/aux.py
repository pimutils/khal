import icalendar
import os

import pytz

cal1 = 'foobar'
cal2 = 'work'
cal3 = 'private'

example_cals = [cal1, cal2, cal3]

BERLIN = pytz.timezone('Europe/Berlin')

locale = {'default_timezone': BERLIN,
          'local_timezone': BERLIN,
          'dateformat': '%d.%m.%Y',
          'timeformat': '%H:%M',
          'longdateformat': '%d.%m.%Y %H:%M',
          'unicode_symbols': True,
          }

SAMOA = pytz.timezone('Pacific/Samoa')
LOCALE_SAMOA = {'default_timezone': SAMOA,
                'local_timezone': SAMOA,
                'unicode_symbols': True,
                }


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
        directory == './ics/'

    return open(os.path.join(directory, event_name + '.ics'), 'rb').read().decode('utf-8')


def _get_vevent_file(event_path):
    directory = '/'.join(__file__.split('/')[:-1]) + '/ics/'
    ical = icalendar.Calendar.from_ical(
        open(os.path.join(directory, event_path + '.ics'), 'rb').read()
    )
    for component in ical.walk():
        if component.name == 'VEVENT':
            return component


def _get_all_vevents_file(event_path):
    directory = '/'.join(__file__.split('/')[:-1]) + '/ics/'
    ical = icalendar.Calendar.from_ical(
        open(os.path.join(directory, event_path + '.ics'), 'rb').read()
    )
    for component in ical.walk():
        if component.name == 'VEVENT':
            yield component
