from datetime import datetime, date

from khal.ui.startendeditor import StartEndEditor

from ..utils import LOCALE_BERLIN, BERLIN

CONF = {'locale': LOCALE_BERLIN, 'keybindings': {}}

START = BERLIN.localize(datetime(2015, 4, 26, 22, 23))
END = BERLIN.localize(datetime(2015, 4, 27, 23, 23))


def test_popup(monkeypatch):
    """making sure the popup calendar gets callend with the right inital value

    #405
    """
    class FakeCalendar():
        def store(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    fake = FakeCalendar()
    monkeypatch.setattr(
        'khal.ui.calendarwidget.CalendarWidget.__init__', fake.store)
    see = StartEndEditor(START, END, CONF)
    see.widgets.startdate.keypress((22, ), 'enter')
    assert fake.kwargs['initial'] == date(2015, 4, 26)
    see.widgets.enddate.keypress((22, ), 'enter')
    assert fake.kwargs['initial'] == date(2015, 4, 27)
