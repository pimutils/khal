import logging
import os
from time import sleep

import pytest

from khal.custom_types import CalendarConfiguration
from khal.khalendar import CalendarCollection
from khal.khalendar.vdir import Vdir

from .utils import LOCALE_BERLIN, CollVdirType, cal1, example_cals


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
        '/singlecollection/',
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


@pytest.fixture
def coll_vdirs(tmpdir) -> CollVdirType:
    calendars, vdirs = {}, {}
    for name in example_cals:
        path = str(tmpdir) + '/' + name
        os.makedirs(path, mode=0o770)
        readonly = True if name == 'a_calendar' else False
        calendars[name] = CalendarConfiguration(
            name=name,
            path=path,
            readonly=readonly,
            color='dark blue',
            priority=10,
            ctype='calendar',
            addresses='user@example.com',
        )
        vdirs[name] = Vdir(path, '.ics')
    coll = CalendarCollection(calendars=calendars, dbpath=':memory:', locale=LOCALE_BERLIN)
    coll.default_calendar_name = cal1
    return coll, vdirs


@pytest.fixture
def coll_vdirs_birthday(tmpdir):
    calendars, vdirs = {}, {}
    for name in example_cals:
        path = str(tmpdir) + '/' + name
        os.makedirs(path, mode=0o770)
        readonly = True if name == 'a_calendar' else False
        calendars[name] = {'name': name, 'path': path, 'color': 'dark blue',
                           'readonly': readonly, 'unicode_symbols': True, 'ctype': 'birthdays',
                           'addresses': 'user@example.com'}
        vdirs[name] = Vdir(path, '.vcf')
    coll = CalendarCollection(calendars=calendars, dbpath=':memory:', locale=LOCALE_BERLIN)
    coll.default_calendar_name = cal1
    return coll, vdirs


@pytest.fixture(autouse=True)
def never_echo_bytes(monkeypatch):
    '''Click's echo function will not strip colorcodes if we call `click.echo`
    with a bytestring message. The reason for this that bytestrings may contain
    arbitrary binary data (such as images).

    Khal is not concerned with such data at all, but may contain a few
    instances where it explicitly encodes its output into the configured
    locale. This in turn would break the functionality of the global
    `--color/--no-color` flag.
    '''
    from click import echo as old_echo

    def echo(msg=None, *a, **kw):
        assert not isinstance(msg, bytes)
        return old_echo(msg, *a, **kw)

    monkeypatch.setattr('click.echo', echo)

    class Result:
        @staticmethod
        def undo():
            monkeypatch.setattr('click.echo', old_echo)

    return Result


@pytest.fixture(scope='session')
def sleep_time(tmpdir_factory):
    """
    Returns the filesystem's mtime precision

    Returns how long we need to sleep for the filesystem's mtime precision to
    pick up differences.

    This keeps test fast on systems with high precisions, but makes them pass
    on those that don't.
    """
    tmpfile = tmpdir_factory.mktemp('sleep').join('touch_me')

    def touch_and_mtime():
        tmpfile.open('w').close()
        stat = os.stat(str(tmpfile))
        return getattr(stat, 'st_mtime_ns', stat.st_mtime)

    i = 0.00001
    while i < 100:
        # Measure three times to avoid things like 12::18:11.9994 [mis]passing
        first = touch_and_mtime()
        sleep(i)
        second = touch_and_mtime()
        sleep(i)
        third = touch_and_mtime()

        if first != second != third:
            return i * 1.1
        i = i * 10

    # This should never happen, but oh, well:
    raise Exception(
        'Filesystem does not seem to save modified times of files. \n'
        'Cannot run tests that depend on this.'
    )


@pytest.fixture
def fix_caplog(monkeypatch):
    """Temporarily undoes the logging setup by click-log such that the caplog fixture can be used"""
    logger = logging.getLogger('khal')
    monkeypatch.setattr(logger, 'handlers', [])
    monkeypatch.setattr(logger, 'propagate', True)
