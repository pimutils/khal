import os

import pytest

from khal.khalendar import Calendar, CalendarCollection
from vdirsyncer.storage.filesystem import FilesystemStorage

from .aux import locale, example_cals, cal1


@pytest.fixture
def cal_vdir(tmpdir):
    cal = Calendar(cal1, ':memory:', str(tmpdir), color='dark blue', locale=locale)
    vdir = FilesystemStorage(str(tmpdir), '.ics')
    return cal, vdir


@pytest.fixture
def coll_vdirs(tmpdir):
    coll = CalendarCollection(locale=locale)
    vdirs = dict()
    props = {'color': 'dark blue', 'readonly': False}
    for name in example_cals:
        path = str(tmpdir) + '/' + name
        os.makedirs(path, mode=0o770)
        coll.append(
            Calendar(name, ':memory:', path, color='dark blue', locale=locale), props=props)
        vdirs[name] = FilesystemStorage(path, '.ics')
    coll.default_calendar_name = cal1
    return coll, vdirs


@pytest.fixture
def coll_vdirs_disk(tmpdir):
    """same as above, but writes the database to disk as well, needed for some tests"""
    coll = CalendarCollection(locale=locale)
    vdirs = dict()
    props = {'color': 'dark blue', 'readonly': False}
    for name in example_cals:
        path = str(tmpdir) + '/' + name
        os.makedirs(path, mode=0o770)
        coll.append(
            Calendar(name, str(tmpdir) + '/db.db', path, color='dark blue', locale=locale),
            props=props)
        vdirs[name] = FilesystemStorage(path, '.ics')
    coll.default_calendar_name = cal1
    return coll, vdirs
