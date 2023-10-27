"""testing functions from the khal.utils"""
import datetime as dt

from click import style
from freezegun import freeze_time

from khal import utils


def test_relative_timedelta_str():
    with freeze_time('2016-9-19'):
        assert utils.relative_timedelta_str(dt.date(2016, 9, 24)) == '5 days from now'
        assert utils.relative_timedelta_str(dt.date(2016, 9, 29)) == '~1 week from now'
        assert utils.relative_timedelta_str(dt.date(2017, 9, 29)) == '~1 year from now'
        assert utils.relative_timedelta_str(dt.date(2016, 7, 29)) == '~7 weeks ago'


weekheader = """[1m    Mo Tu We Th Fr Sa Su   [0m"""
today_line = """[1mToday[0m[0m"""
calendarline = (
    "[1mNov [0m[1;33m31[0m [32m 1[0m [1;33m 2[0m "
    "[1;33m 3[0m [1;33m 4[0m [32m 5[0m [32m 6[0m"
)


def test_last_reset():
    assert utils.find_last_reset(weekheader) == (31, 35, '\x1b[0m')
    assert utils.find_last_reset(today_line) == (13, 17, '\x1b[0m')
    assert utils.find_last_reset(calendarline) == (99, 103, '\x1b[0m')
    assert utils.find_last_reset('Hello World') == (-2, -1, '')


def test_last_sgr():
    assert utils.find_last_sgr(weekheader) == (0, 4, '\x1b[1m')
    assert utils.find_last_sgr(today_line) == (0, 4, '\x1b[1m')
    assert utils.find_last_sgr(calendarline) == (92, 97, '\x1b[32m')
    assert utils.find_last_sgr('Hello World') == (-2, -1, '')


def test_find_unmatched_sgr():
    assert utils.find_unmatched_sgr(weekheader) is None
    assert utils.find_unmatched_sgr(today_line) is None
    assert utils.find_unmatched_sgr(calendarline) is None
    assert utils.find_unmatched_sgr('\x1b[31mHello World') == '\x1b[31m'
    assert utils.find_unmatched_sgr('\x1b[31mHello\x1b[0m \x1b[32mWorld') == '\x1b[32m'
    assert utils.find_unmatched_sgr('foo\x1b[1;31mbar') == '\x1b[1;31m'
    assert utils.find_unmatched_sgr('\x1b[0mfoo\x1b[1;31m') == '\x1b[1;31m'


def test_color_wrap():
    text = (
        "Lorem ipsum \x1b[31mdolor sit amet, consetetur sadipscing "
        "elitr, sed diam nonumy\x1b[0m eirmod tempor"
    )
    expected = [
        "Lorem ipsum \x1b[31mdolor sit amet,\x1b[0m",
        "\x1b[31mconsetetur sadipscing elitr, sed\x1b[0m",
        "\x1b[31mdiam nonumy\x1b[0m eirmod tempor",
    ]

    assert utils.color_wrap(text, 35) == expected


def test_color_wrap_256():
    text = (
        "\x1b[38;2;17;255;0mLorem ipsum dolor sit amet, consetetur sadipscing "
        "elitr, sed diam nonumy\x1b[0m"
    )
    expected = [
        "\x1b[38;2;17;255;0mLorem ipsum\x1b[0m",
        "\x1b[38;2;17;255;0mdolor sit amet, consetetur\x1b[0m",
        "\x1b[38;2;17;255;0msadipscing elitr, sed diam\x1b[0m",
        "\x1b[38;2;17;255;0mnonumy\x1b[0m"
    ]

    assert utils.color_wrap(text, 30) == expected


def test_color_wrap_multiple_colors_and_tabs():
    text = (
        "\x1b[31m14:00-14:50    AST-1002-102 INTRO AST II/STAR GALAX (R) Classes",
        "15:30-16:45    PHL-2000-104 PHILOSOPHY, SOCIETY & ETHICS (R) Classes",
        "\x1b[38;2;255;0m17:00-18:00    Pay Ticket Deadline Calendar",
        "09:30-10:45    PHL-1501-101 MIND, KNOWLEDGE & REALITY (R) Classes",
        "\x1b[38;2;255;0m11:00-14:00    Rivers Street (noodles and pizza) (R) Calendar",
    )
    expected = [
      '\x1b[31m14:00-14:50    AST-1002-102 INTRO AST II/STAR GALAX (R)\x1b[0m',
      '\x1b[31mClasses\x1b[0m',
      '15:30-16:45    PHL-2000-104 PHILOSOPHY, SOCIETY & ETHICS (R)',
      'Classes',
      '\x1b[38;2;255;0m17:00-18:00    Pay Ticket Deadline Calendar\x1b[0m',
      '09:30-10:45    PHL-1501-101 MIND, KNOWLEDGE & REALITY (R)',
      'Classes',
      '\x1b[38;2;255;0m11:00-14:00    Rivers Street (noodles and\x1b[0m',
      '\x1b[38;2;255;0mpizza) (R) Calendar\x1b[0m'
    ]
    actual = []
    for line in text:
        actual += utils.color_wrap(line, 60)
    assert actual == expected


def test_get_weekday_occurrence():
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 1)) == (2, 1)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 2)) == (3, 1)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 3)) == (4, 1)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 4)) == (5, 1)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 5)) == (6, 1)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 6)) == (0, 1)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 7)) == (1, 1)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 8)) == (2, 2)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 9)) == (3, 2)
    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 10)) == (4, 2)

    assert utils.get_weekday_occurrence(dt.datetime(2017, 3, 31)) == (4, 5)

    assert utils.get_weekday_occurrence(dt.date(2017, 5, 1)) == (0, 1)
    assert utils.get_weekday_occurrence(dt.date(2017, 5, 7)) == (6, 1)
    assert utils.get_weekday_occurrence(dt.date(2017, 5, 8)) == (0, 2)
    assert utils.get_weekday_occurrence(dt.date(2017, 5, 28)) == (6, 4)
    assert utils.get_weekday_occurrence(dt.date(2017, 5, 29)) == (0, 5)


def test_human_formatter_width():
    formatter = utils.human_formatter('{red}{title}', width=10)
    output = formatter({'title': 'morethan10characters', 'red': style('', reset=False, fg='red')})
    assert output.startswith('\x1b[31mmoret\x1b[0m')
