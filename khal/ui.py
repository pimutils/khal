import urwid
import calendar
from datetime import date

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


def construct_week(week):
    """
    :param week: list of datetime.date objects
    returns urwid.Columns
    """
    if 1 in [day.day for day in week]:
        month_name = calendar.month_abbr[week[-1].month].ljust(4)
    else:
        month_name = '    '

    this_week = [(4, urwid.Text(month_name))]

    for day in week:
        if day == date.today():
            this_week.append((2, urwid.AttrMap(Date(day), 'today', 'today_focus')))
        else:
            this_week.append((2, urwid.AttrMap(Date(day), None, 'reveal focus')))
    #this_week = this_week + [(2, urwid.AttrMap(Date(day), None, 'reveal focus')) for day in week]
    week = urwid.Columns(this_week, dividechars=1)
    return week


def interactive(conf=None, dbtool=None):
    lines = list()
    daynames = 'Mo Tu We Th Fr Sa Su'.split(' ')
    daynames = urwid.Columns([(4, urwid.Text('    '))] + [(2, urwid.Text(name)) for name in daynames],
                             dividechars=1)
    lines = [daynames]
    for week in week_list():
        week = construct_week(week)
        lines.append(week)

    weeks = urwid.Pile(lines)

    fill = urwid.Filler(weeks)
    urwid.MainLoop(fill, palette=palette).run()
