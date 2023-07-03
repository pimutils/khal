import datetime as dt

import icalendar

from khal.ui.editor import RecurrenceEditor, StartEndEditor

from ..utils import BERLIN, LOCALE_BERLIN
from .canvas_render import CanvasTranslator

CONF = {'locale': LOCALE_BERLIN, 'keybindings': {}, 'view': {'monthdisplay': 'firstday'}}

START = BERLIN.localize(dt.datetime(2015, 4, 26, 22, 23))
END = BERLIN.localize(dt.datetime(2015, 4, 27, 23, 23))

palette = {
    'date header focused': 'blue',
    'date header': 'green',
    'default': 'black',
    'edit focused': 'red',
    'edit': 'blue',
}


def test_popup(monkeypatch):
    """making sure the popup calendar gets callend with the right inital value

    #405
    """
    class FakeCalendar:
        def store(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    fake = FakeCalendar()
    monkeypatch.setattr(
        'khal.ui.calendarwidget.CalendarWidget.__init__', fake.store)
    see = StartEndEditor(START, END, CONF)
    see.widgets.startdate.keypress((22, ), 'enter')
    assert fake.kwargs['initial'] == dt.date(2015, 4, 26)
    see.widgets.enddate.keypress((22, ), 'enter')
    assert fake.kwargs['initial'] == dt.date(2015, 4, 27)


def test_check_understood_rrule():
    assert RecurrenceEditor.check_understood_rrule(
        icalendar.vRecur.from_ical('FREQ=MONTHLY;BYDAY=1SU')
    )
    assert RecurrenceEditor.check_understood_rrule(
        icalendar.vRecur.from_ical('FREQ=MONTHLY;BYMONTHDAY=1')
    )
    assert RecurrenceEditor.check_understood_rrule(
        icalendar.vRecur.from_ical('FREQ=MONTHLY;BYDAY=TH;BYSETPOS=1')
    )
    assert RecurrenceEditor.check_understood_rrule(
        icalendar.vRecur.from_ical('FREQ=MONTHLY;BYDAY=TU,TH;BYSETPOS=1')
    )
    assert RecurrenceEditor.check_understood_rrule(
        icalendar.vRecur.from_ical('FREQ=MONTHLY;INTERVAL=2;BYDAY=MO,TU,WE,TH,FR,SA,SU;BYSETPOS=1')
    )
    assert RecurrenceEditor.check_understood_rrule(
        icalendar.vRecur.from_ical('FREQ=MONTHLY;INTERVAL=2;BYDAY=WE,SU,MO,TH,FR,TU,SA;BYSETPOS=1')
    )
    assert RecurrenceEditor.check_understood_rrule(
        icalendar.vRecur.from_ical('FREQ=MONTHLY;INTERVAL=2;BYDAY=WE,MO,TH,FR,TU,SA;BYSETPOS=1')
    )
    assert not RecurrenceEditor.check_understood_rrule(
        icalendar.vRecur.from_ical('FREQ=MONTHLY;BYDAY=-1SU')
    )
    assert not RecurrenceEditor.check_understood_rrule(
        icalendar.vRecur.from_ical('FREQ=MONTHLY;BYDAY=TH;BYMONTHDAY=1,2,3,4,5,6,7')
    )
    assert not RecurrenceEditor.check_understood_rrule(
        icalendar.vRecur.from_ical('FREQ=MONTHLY;BYDAY=TH;BYMONTHDAY=-1')
    )
    assert not RecurrenceEditor.check_understood_rrule(
        icalendar.vRecur.from_ical('FREQ=MONTHLY;BYDAY=TH;BYSETPOS=3')
    )


def test_editor():
    """test for the issue in #666"""
    editor = StartEndEditor(
        BERLIN.localize(dt.datetime(2017, 10, 2, 13)),
        BERLIN.localize(dt.datetime(2017, 10, 4, 18)),
        conf=CONF
    )
    assert editor.startdt == BERLIN.localize(dt.datetime(2017, 10, 2, 13))
    assert editor.enddt == BERLIN.localize(dt.datetime(2017, 10, 4, 18))
    assert editor.changed is False
    for _ in range(3):
        editor.keypress((10, ), 'tab')
    for _ in range(3):
        editor.keypress((10, ), 'shift tab')
    assert editor.startdt == BERLIN.localize(dt.datetime(2017, 10, 2, 13))
    assert editor.enddt == BERLIN.localize(dt.datetime(2017, 10, 4, 18))
    assert editor.changed is False


def test_convert_to_date():
    """test for the issue in #666"""
    editor = StartEndEditor(
        BERLIN.localize(dt.datetime(2017, 10, 2, 13)),
        BERLIN.localize(dt.datetime(2017, 10, 4, 18)),
        conf=CONF
    )
    canvas = editor.render((50, ), True)
    assert CanvasTranslator(canvas, palette).transform() == (
        '[ ] Allday\nFrom: \x1b[31m2.10.2017 \x1b[0m \x1b[34m13:00 \x1b[0m\n'
        'To:   \x1b[34m04.10.2017\x1b[0m \x1b[34m18:00 \x1b[0m\n'
    )

    assert editor.startdt == BERLIN.localize(dt.datetime(2017, 10, 2, 13))
    assert editor.enddt == BERLIN.localize(dt.datetime(2017, 10, 4, 18))
    assert editor.changed is False
    assert editor.allday is False

    # set to all day event
    editor.keypress((10, ), 'shift tab')
    editor.keypress((10, ), ' ')
    for _ in range(3):
        editor.keypress((10, ), 'tab')
    for _ in range(3):
        editor.keypress((10, ), 'shift tab')

    canvas = editor.render((50, ), True)
    assert CanvasTranslator(canvas, palette).transform() == (
        '[X] Allday\nFrom: \x1b[34m02.10.2017\x1b[0m  \n'
        'To:   \x1b[34m04.10.2017\x1b[0m  \n'
    )

    assert editor.changed is True
    assert editor.allday is True
    assert editor.startdt == dt.date(2017, 10, 2)
    assert editor.enddt == dt.date(2017, 10, 4)
