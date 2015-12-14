import os

import pytest

from khal.khalendar import CalendarCollection
from vdirsyncer.storage.filesystem import FilesystemStorage

from .aux import locale, example_cals, cal1


@pytest.fixture
def coll_vdirs(tmpdir):
    calendars, vdirs = dict(), dict()
    for name in example_cals:
        path = str(tmpdir) + '/' + name
        os.makedirs(path, mode=0o770)
        calendars[name] = {'name': name, 'path': path, 'color': 'dark blue',
                           'readonly': False, 'unicode_symbols': True}
        vdirs[name] = FilesystemStorage(path, '.ics')
    coll = CalendarCollection(calendars=calendars, dbpath=':memory:', locale=locale)
    coll.default_calendar_name = cal1
    return coll, vdirs
