import datetime
import locale

import pytest

from khal.calendar_display import vertical_month, getweeknumber, str_week


today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)
tomorrow = today + datetime.timedelta(days=1)


def test_getweeknumber():
    assert getweeknumber(datetime.date(2011, 12, 12)) == 50
    assert getweeknumber(datetime.date(2011, 12, 31)) == 52
    assert getweeknumber(datetime.date(2012, 1, 1)) == 52
    assert getweeknumber(datetime.date(2012, 1, 2)) == 1


def test_str_week():
    aday = datetime.date(2012, 6, 1)
    bday = datetime.date(2012, 6, 8)
    week = [datetime.date(2012, 6, 6),
            datetime.date(2012, 6, 7),
            datetime.date(2012, 6, 8),
            datetime.date(2012, 6, 9),
            datetime.date(2012, 6, 10),
            datetime.date(2012, 6, 11),
            datetime.date(2012, 6, 12),
            datetime.date(2012, 6, 13)]
    assert str_week(week, aday) == ' 6  7  8  9 10 11 12 13 '
    assert str_week(week, bday) == ' 6  7 \x1b[7m 8\x1b[0m  9 10 11 12 13 '


example1 = [
    '\x1b[1m    Mo Tu We Th Fr Sa Su \x1b[0m',
    '\x1b[1mDec \x1b[0m28 29 30  1  2  3  4 ',
    '     5  6  7  8  9 10 11 ',
    '    \x1b[7m12\x1b[0m 13 14 15 16 17 18 ',
    '    19 20 21 22 23 24 25 ',
    '\x1b[1mJan \x1b[0m26 27 28 29 30 31  1 ',
    '     2  3  4  5  6  7  8 ',
    '     9 10 11 12 13 14 15 ',
    '    16 17 18 19 20 21 22 ',
    '    23 24 25 26 27 28 29 ',
    '\x1b[1mFeb \x1b[0m30 31  1  2  3  4  5 ',
    '     6  7  8  9 10 11 12 ',
    '    13 14 15 16 17 18 19 ',
    '    20 21 22 23 24 25 26 ',
    '\x1b[1mMar \x1b[0m27 28 29  1  2  3  4 ']


example_weno = [
    '\x1b[1m    Mo Tu We Th Fr Sa Su     \x1b[0m',
    '\x1b[1mDec \x1b[0m28 29 30  1  2  3  4 \x1b[1m 48\x1b[0m',
    '     5  6  7  8  9 10 11 \x1b[1m 49\x1b[0m',
    '    \x1b[7m12\x1b[0m 13 14 15 16 17 18 \x1b[1m 50\x1b[0m',
    '    19 20 21 22 23 24 25 \x1b[1m 51\x1b[0m',
    '\x1b[1mJan \x1b[0m26 27 28 29 30 31  1 \x1b[1m 52\x1b[0m',
    '     2  3  4  5  6  7  8 \x1b[1m 1\x1b[0m',
    '     9 10 11 12 13 14 15 \x1b[1m 2\x1b[0m',
    '    16 17 18 19 20 21 22 \x1b[1m 3\x1b[0m',
    '    23 24 25 26 27 28 29 \x1b[1m 4\x1b[0m',
    '\x1b[1mFeb \x1b[0m30 31  1  2  3  4  5 \x1b[1m 5\x1b[0m',
    '     6  7  8  9 10 11 12 \x1b[1m 6\x1b[0m',
    '    13 14 15 16 17 18 19 \x1b[1m 7\x1b[0m',
    '    20 21 22 23 24 25 26 \x1b[1m 8\x1b[0m',
    '\x1b[1mMar \x1b[0m27 28 29  1  2  3  4 \x1b[1m 9\x1b[0m']

example_we_start_su = [
    '\x1b[1m    Su Mo Tu We Th Fr Sa \x1b[0m',
    '\x1b[1mDec \x1b[0m27 28 29 30  1  2  3 ',
    '     4  5  6  7  8  9 10 ',
    '    11 \x1b[7m12\x1b[0m 13 14 15 16 17 ',
    '    18 19 20 21 22 23 24 ',
    '    25 26 27 28 29 30 31 ',
    '\x1b[1mJan \x1b[0m 1  2  3  4  5  6  7 ',
    '     8  9 10 11 12 13 14 ',
    '    15 16 17 18 19 20 21 ',
    '    22 23 24 25 26 27 28 ',
    '\x1b[1mFeb \x1b[0m29 30 31  1  2  3  4 ',
    '     5  6  7  8  9 10 11 ',
    '    12 13 14 15 16 17 18 ',
    '    19 20 21 22 23 24 25 ',
    '\x1b[1mMar \x1b[0m26 27 28 29  1  2  3 ']

example_cz = [
    u'\x1b[1m    Po \xdat St \u010ct P\xe1 So Ne \x1b[0m',
    u'\x1b[1mpro \x1b[0m28 29 30  1  2  3  4 ',
    u'     5  6  7  8  9 10 11 ',
    u'    \x1b[7m12\x1b[0m 13 14 15 16 17 18 ',
    u'    19 20 21 22 23 24 25 ',
    u'\x1b[1mled \x1b[0m26 27 28 29 30 31  1 ',
    u'     2  3  4  5  6  7  8 ',
    u'     9 10 11 12 13 14 15 ',
    u'    16 17 18 19 20 21 22 ',
    u'    23 24 25 26 27 28 29 ',
    u'\x1b[1m\xfano \x1b[0m30 31  1  2  3  4  5 ',
    u'     6  7  8  9 10 11 12 ',
    u'    13 14 15 16 17 18 19 ',
    u'    20 21 22 23 24 25 26 ',
    u'\x1b[1mb\u0159e \x1b[0m27 28 29  1  2  3  4 ']

example_de = [
    u'\x1b[1m    Mo Di Mi Do Fr Sa So \x1b[0m',
    u'\x1b[1mDez \x1b[0m28 29 30  1  2  3  4 ',
    u'     5  6  7  8  9 10 11 ',
    u'    \x1b[7m12\x1b[0m 13 14 15 16 17 18 ',
    u'    19 20 21 22 23 24 25 ',
    u'\x1b[1mJan \x1b[0m26 27 28 29 30 31  1 ',
    u'     2  3  4  5  6  7  8 ',
    u'     9 10 11 12 13 14 15 ',
    u'    16 17 18 19 20 21 22 ',
    u'    23 24 25 26 27 28 29 ',
    u'\x1b[1mFeb \x1b[0m30 31  1  2  3  4  5 ',
    u'     6  7  8  9 10 11 12 ',
    u'    13 14 15 16 17 18 19 ',
    u'    20 21 22 23 24 25 26 ',
    u'\x1b[1mM\xe4r \x1b[0m27 28 29  1  2  3  4 ']


def test_vertical_month():
    locale.setlocale(locale.LC_ALL, 'en_US.utf-8')
    vert_str = vertical_month(month=12, year=2011,
                              today=datetime.date(2011, 12, 12))
    assert vert_str == example1

    weno_str = vertical_month(month=12, year=2011,
                              today=datetime.date(2011, 12, 12),
                              weeknumber='right')
    assert weno_str == example_weno

    we_start_su_str = vertical_month(
        month=12, year=2011,
        today=datetime.date(2011, 12, 12),
        firstweekday=6)
    assert we_start_su_str == example_we_start_su


def test_vertical_month_unicode():
    try:
        locale.setlocale(locale.LC_ALL, 'de_DE.utf-8')
    except locale.Error as error:
        if str(error) == 'unsupported locale setting':
            pytest.xfail(
                'To get this test to run, you need to add `de_DE.utf-8` to '
                'your locales. On Debian GNU/Linux 8 you do this by '
                'uncommenting `de_DE.utf-8 in /etc/locale.gen and then run '
                '`locale-gen` (as root).'
            )
        else:
            raise

    vert_str = vertical_month(month=12, year=2011,
                              today=datetime.date(2011, 12, 12))
    assert vert_str == example_de
    u'\n'.join(vert_str)  # issue 142


def test_vertical_month_unicode_weekdeays():
    try:
        locale.setlocale(locale.LC_ALL, 'cs_CZ.UTF-8')
    except locale.Error as error:
        if str(error) == 'unsupported locale setting':
            pytest.xfail(
                'To get this test to run, you need to add `cs_CZ.UTF-8` to '
                'your locales. On Debian GNU/Linux 8 you do this by '
                'uncommenting `cs_CZ.UTF-8` in /etc/locale.gen and then run '
                '`locale-gen` (as root).'
            )
        else:
            raise

    vert_str = vertical_month(month=12, year=2011,
                              today=datetime.date(2011, 12, 12))
    assert vert_str == example_cz
    u'\n'.join(vert_str)  # issue 142/293
