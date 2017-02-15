import os
from time import sleep

import pytest

from khal.khalendar import CalendarCollection
from khal.khalendar.vdir import Vdir

from .utils import LOCALE_BERLIN, example_cals, cal1


@pytest.fixture
def coll_vdirs(tmpdir):
    calendars, vdirs = dict(), dict()
    for name in example_cals:
        path = str(tmpdir) + '/' + name
        os.makedirs(path, mode=0o770)
        readonly = True if name == 'a_calendar' else False
        calendars[name] = {'name': name, 'path': path, 'color': 'dark blue',
                           'readonly': readonly, 'unicode_symbols': True}
        vdirs[name] = Vdir(path, '.ics')
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

    first = touch_and_mtime()
    sleep(0.1)
    second = touch_and_mtime()

    if first < second:
        return 0.01
    return 1.1
