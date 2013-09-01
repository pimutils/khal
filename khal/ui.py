import urwid
import calendar
from datetime import date
from datetime import time
from datetime import datetime

palette = [('header', 'white', 'black'),
           ('reveal focus', 'black', 'dark cyan', 'standout'),
           ('today_focus', 'white', 'black', 'standout'),
           ('today', 'black', 'white', 'dark cyan')]


class Date(urwid.Text):

    def __init__(self, date):
        self.date = date
        if date.today == date:
            urwid.AttrMap(super(Date, self).__init__(str(date.day).rjust(2)),
                          None,
                          'reveal focus')
        else:
            super(Date, self).__init__(str(date.day).rjust(2))

    @classmethod
    def selectable(cls):
        return True

    def keypress(self, _, key):
        return key


def week_list(count=3):
    month = date.today().month
    year = date.today().year
    khal = list()
    for _ in range(count):
        for week in calendar.Calendar(0).monthdatescalendar(year, month):
            if week not in khal:
                khal.append(week)
        month = month + 1
        if month > 12:
            month = 1
            year = year + 1
    return khal


class DateColumns(urwid.Columns):
    def __init__(self, widget_list, call=None, **kwargs):
        self.call = call

        super(DateColumns, self).__init__(widget_list, **kwargs)

    def _set_focus_position(self, position):
        """
        Set the widget in focus.

        position -- index of child widget to be made focus
        """

        try:
            if position < 0 or position >= len(self.contents):
                raise IndexError
        except (TypeError, IndexError):
            raise IndexError, "No Columns child widget at position %s" % (position,)
        # since first Column is month name, focus should only be 0 during
        # construction
        if not self.contents.focus == 0:
            self.call(self.contents[position][0].original_widget.date)
        self.contents.focus = position

    focus_position = property(urwid.Columns._get_focus_position, _set_focus_position, doc="""
index of child widget in focus. Raises IndexError if read when
Columns is empty, or when set to an invalid index.
""")


def construct_week(week, call=None):
    """
    :param week: list of datetime.date objects
    returns urwid.Columns
    """
    if 1 in [day.day for day in week]:
        month_name = calendar.month_abbr[week[-1].month].ljust(4)
    else:
        month_name = '    '

    this_week = [(4, urwid.Text(month_name))]

    for number, day in enumerate(week):
        if day == date.today():
            this_week.append((2, urwid.AttrMap(Date(day),
                                               'today', 'today_focus')))
            today = number + 1
        else:
            this_week.append((2, urwid.AttrMap(Date(day),
                                               None, 'reveal focus')))
            today = None
    week = DateColumns(this_week, call=call, dividechars=1, focus_column=today)
    return week, bool(today)


def calendar_walker(call=None):
    """hopefully this will soon become a real "walker",
    loading new weeks as nedded"""
    lines = list()
    daynames = 'Mo Tu We Th Fr Sa Su'.split(' ')
    daynames = urwid.Columns([(4, urwid.Text('    '))] + [(2, urwid.Text(name)) for name in daynames],
                             dividechars=1)
    lines = [daynames]
    for number, week in enumerate(week_list()):
        week, contains_today = construct_week(week, call=call)
        if contains_today:
            focus_item = number + 1
        lines.append(week)

    weeks = urwid.Pile(lines, focus_item=focus_item)
    return weeks


class EventList(urwid.WidgetWrap):

    def __init__(self, conf=None, dbtool=None):
        self.conf = conf
        self.dbtool = dbtool
        self.number = 1
        pile = urwid.Pile([])
        urwid.WidgetWrap.__init__(self, pile)
        self.update()

    def update(self, this_date=date.today()):

        self.number += 1
        start = datetime.combine(this_date, time.min)
        end = datetime.combine(this_date, time.max)

        event_column = [this_date.strftime('%d.%m.%Y')]
        all_day_events = list()
        events = list()
        for account in self.conf.sync.accounts:
            all_day_events += self.dbtool.get_allday_range(this_date,
                                                            account_name=account)
            events += self.dbtool.get_time_range(start, end, account)
        for event in all_day_events:
            event_column.append(event.summary)
        events.sort(key=lambda e: e.start)
        for event in events:
            event_column.append(event.start.strftime('%H:%M') + '-' +  event.end.strftime('%H:%M') + ': ' + event.summary)
        pile = urwid.Pile([urwid.Text(event) for event in event_column])
        self._w = pile


def interactive(conf=None, dbtool=None):
    events = EventList(conf=conf, dbtool=dbtool)
    weeks = calendar_walker(call=events.update)
    columns = urwid.Columns([(25, weeks), events], dividechars=2)
    fill = urwid.Filler(columns)
    urwid.MainLoop(fill, palette=palette).run()
