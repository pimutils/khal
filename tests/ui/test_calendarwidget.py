import datetime as dt

from freezegun import freeze_time

from khal.ui.calendarwidget import CalendarWidget

on_press: dict = {}

keybindings = {
    "today": ["T"],
    "left": ["left", "h", "backspace"],
    "up": ["up", "k"],
    "right": ["right", "l", " "],
    "down": ["down", "j"],
}


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


@freeze_time("2016-04-10")
def test_handing_over_a_marked_range_ends_marking():
    """v, move, n (new event for the range): the marking ends right away, so
    the calendar is back to normal after the editor closes, saved or not"""
    calls = []
    keys = dict(keybindings, mark=["v"], other=["o"])
    frame = CalendarWidget(
        on_date_change=lambda _: None,
        keybindings=keys,
        on_press={"n": lambda start, end: calls.append((start, end))},
        weeknumbers="right",
    )
    size = (28, 10)
    frame.render(size, focus=True)
    frame.keypress(size, "v")
    frame.keypress(size, "right")
    frame.keypress(size, "right")
    frame.keypress(size, "n")
    assert calls == [(dt.date(2016, 4, 10), dt.date(2016, 4, 12))]
    frame.keypress(size, "right")
    frame.keypress(size, "n")
    assert calls[-1] == (dt.date(2016, 4, 13), None)  # no range any more
