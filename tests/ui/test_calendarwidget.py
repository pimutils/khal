import calendar
import datetime as dt

import pytest
from freezegun import freeze_time

from khal.ui.calendarwidget import CalendarWidget
from khal.utils import get_month_abbr_len

on_press: dict = {}

keybindings = {
    "today": ["T"],
    "left": ["left", "h", "backspace"],
    "up": ["up", "k"],
    "right": ["right", "l", " "],
    "down": ["down", "j"],
}


@pytest.mark.parametrize(
    "day_abbr",
    [("h", "k", "sze", "cs", "p", "szo", "v"), ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")],
    ids=["hungarian", "english"],
)
@pytest.mark.parametrize("firstweekday", [0, 6])
@pytest.mark.parametrize("weeknumbers", [False, "left", "right"])
def test_weekday_header_alignment(monkeypatch, day_abbr, firstweekday, weeknumbers):
    # Exercise the real padded formatweekheader output without requiring installed locales.
    monkeypatch.setattr(calendar, "day_abbr", day_abbr)
    frame = CalendarWidget(
        on_date_change=lambda _: None,
        keybindings=keybindings,
        firstweekday=firstweekday,
        weeknumbers=weeknumbers,
    )
    weekdays = day_abbr[firstweekday:] + day_abbr[:firstweekday]
    names = [name[:2].ljust(2) for name in weekdays]
    if weeknumbers == "right":
        names.append("#w")
    expected = " " * (get_month_abbr_len() + 1) + " ".join(names)
    header = next(iter(frame.render((len(expected), 8)).decoded_text))
    assert header == expected


def test_initial_focus_today():
    today = dt.date.today()
    frame = CalendarWidget(
        on_date_change=lambda _: None,
        keybindings=keybindings,
        on_press=on_press,
        weeknumbers="right",
    )
    assert frame.focus_date == today


def test_set_focus_date():
    today = dt.date.today()
    for diff in range(-10, 10, 1):
        frame = CalendarWidget(
            on_date_change=lambda _: None,
            keybindings=keybindings,
            on_press=on_press,
            weeknumbers="right",
        )
        day = today + dt.timedelta(days=diff)
        frame.set_focus_date(day)
        assert frame.focus_date == day


def test_set_focus_date_weekstart_6():
    with freeze_time("2016-04-10"):
        today = dt.date.today()
        for diff in range(-21, 21, 1):
            frame = CalendarWidget(
                on_date_change=lambda _: None,
                keybindings=keybindings,
                on_press=on_press,
                firstweekday=6,
                weeknumbers="right",
            )
            day = today + dt.timedelta(days=diff)
            frame.set_focus_date(day)
            assert frame.focus_date == day

    with freeze_time("2016-04-23"):
        today = dt.date.today()
        for diff in range(10):
            frame = CalendarWidget(
                on_date_change=lambda _: None,
                keybindings=keybindings,
                on_press=on_press,
                firstweekday=6,
                weeknumbers="right",
            )
            day = today + dt.timedelta(days=diff)
            frame.set_focus_date(day)
            assert frame.focus_date == day


def test_set_focus_far_future():
    future_date = dt.date.today() + dt.timedelta(days=1000)
    frame = CalendarWidget(
        on_date_change=lambda _: None,
        keybindings=keybindings,
        on_press=on_press,
        weeknumbers="right",
    )
    frame.set_focus_date(future_date)
    assert frame.focus_date == future_date


def test_set_focus_far_past():
    future_date = dt.date.today() - dt.timedelta(days=1000)
    frame = CalendarWidget(
        on_date_change=lambda _: None,
        keybindings=keybindings,
        on_press=on_press,
        weeknumbers="right",
    )
    frame.set_focus_date(future_date)
    assert frame.focus_date == future_date
