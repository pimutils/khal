from datetime import date, timedelta

from freezegun import freeze_time

from khal.ui.calendarwidget import CalendarWidget

on_press = {}

keybindings = {
    'today': ['T'],
    'left': ['left', 'h', 'backspace'],
    'up': ['up', 'k'],
    'right': ['right', 'l', ' '],
    'down': ['down', 'j'],
}


def test_initial_focus_today():
    today = date.today()
    frame = CalendarWidget(on_date_change=lambda _: None,
                           keybindings=keybindings,
                           on_press=on_press,
                           weeknumbers='right')
    assert frame.focus_date == today


def test_set_focus_date():
    today = date.today()
    for diff in range(-10, 10, 1):
        frame = CalendarWidget(on_date_change=lambda _: None,
                               keybindings=keybindings,
                               on_press=on_press,
                               weeknumbers='right')
        day = today + timedelta(days=diff)
        frame.set_focus_date(day)
        assert frame.focus_date == day


def test_set_focus_date_weekstart_6():

    with freeze_time('2016-04-10'):
        today = date.today()
        for diff in range(-21, 21, 1):
            frame = CalendarWidget(on_date_change=lambda _: None,
                                   keybindings=keybindings,
                                   on_press=on_press,
                                   firstweekday=6,
                                   weeknumbers='right')
            day = today + timedelta(days=diff)
            frame.set_focus_date(day)
            assert frame.focus_date == day

    with freeze_time('2016-04-23'):
        today = date.today()
        for diff in range(10):
            frame = CalendarWidget(on_date_change=lambda _: None,
                                   keybindings=keybindings,
                                   on_press=on_press,
                                   firstweekday=6,
                                   weeknumbers='right')
            day = today + timedelta(days=diff)
            frame.set_focus_date(day)
            assert frame.focus_date == day
