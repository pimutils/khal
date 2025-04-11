# Copyright (c) 2013-2022 khal contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import datetime as dt
from typing import TYPE_CHECKING, Callable, Literal, Optional

import urwid

from ..utils import get_weekday_occurrence, get_wrapped_text
from .widgets import (
    AlarmsEditor,
    CalendarWidget,
    CAttrMap,
    Choice,
    CPadding,
    DateConversionError,
    DateWidget,
    ExtendedEdit,
    NColumns,
    NListBox,
    NPile,
    PositiveIntEdit,
    TimeWidget,
    ValidatedEdit,
    button,
)

if TYPE_CHECKING:
    import khal.khalendar.event

class StartEnd:

    def __init__(self, startdate, starttime, enddate, endtime) -> None:
        """collecting some common properties"""
        self.startdate = startdate
        self.starttime = starttime
        self.enddate = enddate
        self.endtime = endtime


class CalendarPopUp(urwid.PopUpLauncher):
    def __init__(self, widget, on_date_change, weeknumbers: Literal['left', 'right', False]=False,
                 firstweekday=0, monthdisplay='firstday', keybindings=None) -> None:
        self._on_date_change = on_date_change
        self._weeknumbers = weeknumbers
        self._monthdisplay = monthdisplay
        self._firstweekday = firstweekday
        self._keybindings = {} if keybindings is None else keybindings
        super().__init__(widget)

    def keypress(self, size, key):
        if key == 'enter':
            self.open_pop_up()
        else:
            return super().keypress(size, key)

    def create_pop_up(self):
        def on_change(new_date):
            self._get_base_widget().set_value(new_date)
            self._on_date_change(new_date)

        on_press = {'enter': lambda _, __: self.close_pop_up(),
                    'esc': lambda _, __: self.close_pop_up()}
        try:
            initial_date = self.base_widget._get_current_value()
        except DateConversionError:
            return None
        else:
            pop_up = CalendarWidget(
                on_change, self._keybindings, on_press,
                firstweekday=self._firstweekday,
                weeknumbers=self._weeknumbers,
                monthdisplay=self._monthdisplay,
                initial=initial_date)
            pop_up = CAttrMap(pop_up, 'calendar', ' calendar focus')
            pop_up = CAttrMap(urwid.LineBox(pop_up), 'calendar', 'calendar focus')
            return pop_up

    def get_pop_up_parameters(self):
        width = 31 if self._weeknumbers == 'right' else 28
        return {'left': 0, 'top': 1, 'overlay_width': width, 'overlay_height': 8}


class DateEdit(urwid.WidgetWrap):
    """Widget that allows editing a Date.

    Will open a calendar when `enter` is pressed, pressing `enter` again will
    select that date.
    """

    def __init__(
        self,
        startdt: dt.date,
        dateformat: str='%Y-%m-%d',
        on_date_change: Callable=lambda _: None,
        weeknumbers: Literal['left', 'right', False]=False,
        firstweekday: int=0,
        monthdisplay: Literal['firstday', 'firstfullweek']='firstday',
        keybindings: Optional[dict[str, list[str]]] = None,
    ) -> None:
        datewidth = len(startdt.strftime(dateformat))
        self._dateformat = dateformat
        if startdt is None:
            startdt = dt.date.today()
        self._edit = ValidatedEdit(
            dateformat=dateformat,
            EditWidget=DateWidget,
            validate=self._validate,
            edit_text=startdt.strftime(dateformat),
            on_date_change=on_date_change)
        wrapped = CalendarPopUp(self._edit, on_date_change, weeknumbers,
                                firstweekday, monthdisplay, keybindings)
        padded = CAttrMap(
            urwid.Padding(wrapped, align='left', width=datewidth, left=0, right=1),
            'calendar', 'calendar focus',
        )
        super().__init__(padded)

    def _validate(self, text: str):
        try:
            _date = dt.datetime.strptime(text, self._dateformat).date()
        except ValueError:
            return False
        else:
            return _date

    @property
    def date(self):
        """Get currently entered date, or False, if input is invalid.

        :returns: the currently entered date
        :rtype: datetime.date
        """
        return self._validate(self._edit.get_edit_text())

    @date.setter
    def date(self, date):
        """Update text of this Widget.

        :type date: datetime.date
        """
        self._edit.set_edit_text(dt.date.strftime(self._dateformat))


class StartEndEditor(urwid.WidgetWrap):
    """Widget for editing start and end times (of an event)."""

    def __init__(self,
                 start: dt.datetime,
                 end: dt.datetime,
                 conf,
                 on_start_date_change=lambda x: None,
                 on_end_date_change=lambda x: None,
                 on_type_change: Callable[[bool], None]=lambda _: None,
                 ) -> None:
        """
        :param on_start_date_change: a callable that gets called everytime a new
            start date is entered, with that new date as an argument
        :param on_end_date_change: same as for on_start_date_change, just for the
            end date
        :param on_type_change: callback that gets called when the event type
            (allday or datetime) changes, gets passed True if toggled to allday
            and False if toggled to daytime
        """
        self.allday = not isinstance(start, dt.datetime)
        self.conf = conf
        self._startdt: dt.date = start
        self._original_start: dt.date = start
        self._enddt: dt.date = end
        self._original_end: dt.date = end
        self.on_start_date_change = on_start_date_change
        self.on_end_date_change = on_end_date_change
        self.on_type_change = on_type_change
        self._datewidth = len(start.strftime(self.conf['locale']['longdateformat']))
        self._timewidth = len(start.strftime(self.conf['locale']['timeformat']))
        # this will contain the widgets for [start|end] [date|time]
        self.widgets = StartEnd(None, None, None, None)
        self.checkallday = urwid.CheckBox(
            'Allday', state=self.allday, on_state_change=self.toggle)
        self.toggle(None, self.allday)

    def keypress(self, size, key):
        return super().keypress(size, key)

    @property
    def startdt(self):
        if self.allday and isinstance(self._startdt, dt.datetime):
            return self._startdt.date()
        else:
            return self._startdt

    @property
    def _start_time(self):
        try:
            return self._startdt.time()
        except AttributeError:
            return dt.time(0)

    @property
    def localize_start(self):
        if getattr(self.startdt, 'tzinfo', None) is None:
            return self.conf['locale']['default_timezone'].localize
        else:
            return self.startdt.tzinfo.localize

    @property
    def localize_end(self):
        if getattr(self.enddt, 'tzinfo', None) is None:
            return self.conf['locale']['default_timezone'].localize
        else:
            return self.enddt.tzinfo.localize

    @property
    def enddt(self):
        if self.allday and isinstance(self._enddt, dt.datetime):
            return self._enddt.date()
        else:
            return self._enddt

    @property
    def _end_time(self):
        try:
            return self._enddt.time()
        except AttributeError:
            return dt.time(0)

    def _validate_start_time(self, text):
        try:
            startval = dt.datetime.strptime(text, self.conf['locale']['timeformat'])
            self._startdt = self.localize_start(
                dt.datetime.combine(self._startdt.date(), startval.time()))
        except ValueError:
            return False
        else:
            return startval

    def _start_date_change(self, date):
        self._startdt = self.localize_start(dt.datetime.combine(date, self._start_time))
        self.on_start_date_change(date)

    def _validate_end_time(self, text):
        try:
            endval = dt.datetime.strptime(text, self.conf['locale']['timeformat'])
            self._enddt = self.localize_end(dt.datetime.combine(self._enddt.date(), endval.time()))
        except ValueError:
            return False
        else:
            return endval

    def _end_date_change(self, date):
        self._enddt = self.localize_end(dt.datetime.combine(date, self._end_time))
        self.on_end_date_change(date)

    def toggle(self, checkbox, state: bool):
        """change from allday to datetime event

        :param checkbox: the checkbox instance that is used for toggling, gets
                         automatically passed by urwid (is not used)
        :type checkbox: checkbox
        :param state: state the event will toggle to;
                      True if allday event, False if datetime
        """

        if self.allday is True and state is False:
            self._startdt = dt.datetime.combine(self._startdt, dt.datetime.min.time())
            self._enddt = dt.datetime.combine(self._enddt, dt.datetime.min.time())
        elif self.allday is False and state is True:
            assert isinstance(self._startdt, dt.datetime)
            assert isinstance(self._enddt, dt.datetime)
            self._startdt = self._startdt.date()
            self._enddt = self._enddt.date()
        self.allday = state
        self.widgets.startdate = DateEdit(
            self._startdt, self.conf['locale']['longdateformat'],
            self._start_date_change, self.conf['locale']['weeknumbers'],
            self.conf['locale']['firstweekday'],
            self.conf['view']['monthdisplay'],
            self.conf['keybindings'],
        )
        self.widgets.enddate = DateEdit(
            self._enddt, self.conf['locale']['longdateformat'],
            self._end_date_change, self.conf['locale']['weeknumbers'],
            self.conf['locale']['firstweekday'],
            self.conf['view']['monthdisplay'],
            self.conf['keybindings'],
        )

        if state is True:  # allday event
            self.on_type_change(True)
            timewidth = 1
            self.widgets.starttime = urwid.Text('')
            self.widgets.endtime = urwid.Text('')
        elif state is False:  # datetime event
            self.on_type_change(False)
            timewidth = self._timewidth + 1
            raw_start_time_widget = ValidatedEdit(
                dateformat=self.conf['locale']['timeformat'],
                EditWidget=TimeWidget,
                validate=self._validate_start_time,
                edit_text=self.startdt.strftime(self.conf['locale']['timeformat']),
            )
            self.widgets.starttime = urwid.Padding(
                raw_start_time_widget, align='left', width=self._timewidth + 1, left=1)

            raw_end_time_widget = ValidatedEdit(
                dateformat=self.conf['locale']['timeformat'],
                EditWidget=TimeWidget,
                validate=self._validate_end_time,
                edit_text=self.enddt.strftime(self.conf['locale']['timeformat']),
            )
            self.widgets.endtime = urwid.Padding(
                raw_end_time_widget, align='left', width=self._timewidth + 1, left=1)

        columns = NPile([
            self.checkallday,
            NColumns([(5, urwid.Text('From:')), (self._datewidth, self.widgets.startdate), (
                timewidth, self.widgets.starttime)], dividechars=1),
            NColumns(
                [(5, urwid.Text('To:')), (self._datewidth, self.widgets.enddate),
                 (timewidth, self.widgets.endtime)],
                dividechars=1)
        ], focus_item=1)
        urwid.WidgetWrap.__init__(self, columns)

    @property
    def changed(self):
        """returns True if content has been edited, False otherwise"""
        return (self.startdt != self._original_start) or (self.enddt != self._original_end)

    def validate(self):
        return self.startdt <= self.enddt


class EventEditor(urwid.WidgetWrap):
    """Widget that allows Editing one `Event()`"""

    def __init__(
        self,
        pane,
        event: 'khal.khalendar.event.Event',
        save_callback=None,
        always_save: bool=False,
    ) -> None:
        """
        :param save_callback: call when saving event with new start and end
             dates and recursiveness of original and edited event as parameters
        :type save_callback: callable
        :param always_save: save event even if it has not changed
        """
        self.pane = pane
        self.event = event
        self._save_callback = save_callback

        self.collection = pane.collection
        self._conf = pane._conf

        self._abort_confirmed = False

        self.description = event.description
        self.location = event.location
        self.attendees = event.attendees
        self.categories = event.categories
        self.url = event.url
        self.startendeditor = StartEndEditor(
            event.start_local, event.end_local, self._conf,
            self.start_datechange, self.end_datechange,
            self.type_change,
        )
        # TODO make sure recurrence rules cannot be edited if we only
        # edit one instance (or this and future) (once we support that)
        self.recurrenceeditor = RecurrenceEditor(
            self.event.recurobject, self._conf, event.start_local,
        )
        self.summary = urwid.AttrMap(ExtendedEdit(
            caption=('caption', 'Title:       '), edit_text=event.summary), 'edit', 'edit focus',
        )

        divider = urwid.Divider(' ')

        def decorate_choice(c) -> tuple[str, str]:
            return ('calendar ' + c['name'] + ' popup', c['name'])

        self.calendar_chooser= CAttrMap(Choice(
            [self.collection._calendars[c] for c in self.collection.writable_names],
            self.collection._calendars[self.event.calendar],
            decorate_choice
        ), 'caption')

        self.description = urwid.AttrMap(
            ExtendedEdit(
                caption=('caption', 'Description: '),
                edit_text=self.description,
                multiline=True
            ),
            'edit', 'edit focus',
        )
        self.location = urwid.AttrMap(ExtendedEdit(
            caption=('caption', 'Location:    '), edit_text=self.location), 'edit', 'edit focus',
        )
        self.categories = urwid.AttrMap(ExtendedEdit(
            caption=('caption', 'Categories:  '), edit_text=self.categories), 'edit', 'edit focus',
        )
        self.attendees = urwid.AttrMap(
            ExtendedEdit(
                caption=('caption', 'Attendees:   '),
                edit_text=self.attendees,
                multiline=True
            ),
            'edit', 'edit focus',
        )
        self.url = urwid.AttrMap(ExtendedEdit(
            caption=('caption', 'URL:         '), edit_text=self.url), 'edit', 'edit focus',
        )
        self.alarmseditor: AlarmsEditor = AlarmsEditor(self.event)
        self.pile = NListBox(urwid.SimpleFocusListWalker([
            self.summary,
            urwid.Columns([(13, urwid.AttrMap(urwid.Text('Calendar:'), 'caption')),
                           (12, self.calendar_chooser)],
                          ),
            divider,
            self.location,
            self.categories,
            self.description,
            self.url,
            divider,
            self.attendees,
            divider,
            self.startendeditor,
            self.recurrenceeditor,
            divider,
            self.alarmseditor,
            divider,
            urwid.Columns(
                [(12, button('Save', on_press=self.save, padding_left=0, padding_right=0))]
            ),
            urwid.Columns(
                [(12, button('Export', on_press=self.export, padding_left=0, padding_right=0))],
            )
        ]), outermost=True)
        self._always_save = always_save
        urwid.WidgetWrap.__init__(self, self.pile)

    def start_datechange(self, date):
        self.pane.eventscolumn.original_widget.set_focus_date(date)
        self.recurrenceeditor.update_startdt(date)

    def end_datechange(self, date):
        self.pane.eventscolumn.original_widget.set_focus_date(date)

    def type_change(self, allday: bool) -> None:
        """when the event type changes, we might want to change the default alarms

        :params allday: True if the event is now an allday event, False if it isn't
        """
        # test if self.alarmseditor exists
        if not hasattr(self, 'alarmseditor'):
            return

        # to make the alarms before the event, we need to set it them to
        # negative values
        default_event_alarm = -1 * self._conf['default']['default_event_alarm']
        default_dayevent_alarm =-1 *  self._conf['default']['default_dayevent_alarm']
        alarms = self.alarmseditor.get_alarms()
        if len(alarms) == 1:
            timedelta = alarms[0][0]
            if allday and timedelta == default_event_alarm:
                self.alarmseditor.clear()
                self.alarmseditor.add_alarm(None, default_dayevent_alarm)
            elif (not allday) and timedelta == default_dayevent_alarm:
                self.alarmseditor.clear()
                self.alarmseditor.add_alarm(None, default_event_alarm)
            else:
                # either there were more than one alarm or the alarm was not the default
                pass

    @property
    def title(self):  # Window title
        return f'Edit: {get_wrapped_text(self.summary)}'

    @classmethod
    def selectable(cls):
        return True

    @property
    def changed(self):
        if get_wrapped_text(self.summary) != self.event.summary:
            return True
        if get_wrapped_text(self.description) != self.event.description:
            return True
        if get_wrapped_text(self.location) != self.event.location:
            return True
        if get_wrapped_text(self.categories) != self.event.categories:
            return True
        if get_wrapped_text(self.url) != self.event.url:
            return True
        if get_wrapped_text(self.attendees) != self.event.attendees:
            return True
        if self.startendeditor.changed or self.calendar_chooser.changed:
            return True
        if self.recurrenceeditor.changed:
            return True
        if self.alarmseditor.changed:
            return True
        return False

    def update_vevent(self):
        self.event.update_summary(get_wrapped_text(self.summary))
        self.event.update_description(get_wrapped_text(self.description))
        self.event.update_location(get_wrapped_text(self.location))
        self.event.update_attendees(get_wrapped_text(self.attendees).split(','))
        self.event.update_categories(get_wrapped_text(self.categories).split(','))
        self.event.update_url(get_wrapped_text(self.url))

        if self.startendeditor.changed:
            self.event.update_start_end(
                self.startendeditor.startdt, self.startendeditor.enddt)
        if self.recurrenceeditor.changed:
            rrule = self.recurrenceeditor.active
            self.event.update_rrule(rrule)

        if self.alarmseditor.changed:
            self.event.update_alarms(self.alarmseditor.get_alarms())

    def export(self, button):
        """
        export the event as ICS
        :param button: not needed, passed via the button press
        """
        def export_this(_, user_data):
            try:
                self.event.export_ics(user_data.get_edit_text())
            except Exception as e:
                self.pane.window.backtrack()
                self.pane.window.alert(
                    ('light red',
                     'Failed to save event: %s' % e))
                return

            self.pane.window.backtrack()
            self.pane.window.alert(
                ('light green',
                 'Event successfuly exported'))

        overlay = urwid.Overlay(
            ExportDialog(
                export_this,
                self.pane.window.backtrack,
                self.event,
            ),
            self.pane,
            'center', ('relative', 50), ('relative', 50), None)
        self.pane.window.open(overlay)

    def save(self, button):
        """saves the event to the db

        (only when it has been changed or always_save is set)
        :param button: not needed, passed via the button press
        """
        if not self.startendeditor.validate():
            self.pane.window.alert(
                ('light red', "Can't save: end date is before start date!"))
            return

        if self._always_save or self.changed is True:
            self.update_vevent()
            self.event.allday = self.startendeditor.allday
            self.event.increment_sequence()
            if self.event.etag is None:  # has not been saved before
                self.event.calendar = self.calendar_chooser.original_widget.active['name']
                self.collection.insert(self.event)
            elif self.calendar_chooser.changed:
                self.collection.change_collection(
                    self.event,
                    self.calendar_chooser.active['name']
                )
            else:
                self.collection.update(self.event)

            self._save_callback(
                self.event.start_local, self.event.end_local,
                self.event.recurring or self.recurrenceeditor.changed,
            )
        self._abort_confirmed = False
        self.pane.window.backtrack()

    def keypress(self, size: tuple[int], key: str) -> Optional[str]:
        if key in ['esc'] and self.changed and not self._abort_confirmed:
            self.pane.window.alert(
                ('light red', 'Unsaved changes! Hit ESC again to discard.'))
            self._abort_confirmed = True
            return None
        else:
            self._abort_confirmed = False
        return_value = super().keypress(size, key)
        if key in self.pane._conf['keybindings']['save']:
            self.save(None)
            return None
        return return_value


WEEKDAYS = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']  # TODO use locale and respect weekdaystart


class WeekDaySelector(urwid.WidgetWrap):
    def __init__(self, startdt, selected_days) -> None:

        self._weekday_boxes = {day: urwid.CheckBox(day, state=False) for day in WEEKDAYS}
        weekday = startdt.weekday()
        self._weekday_boxes[WEEKDAYS[weekday]].state = True
        self.weekday_checks = NColumns([(7, self._weekday_boxes[wd]) for wd in WEEKDAYS])
        for day in selected_days:
            self._weekday_boxes[day].state = True
        urwid.WidgetWrap.__init__(self, self.weekday_checks)

    @property
    def days(self):
        days = [day.label for (day, _) in self.weekday_checks.contents if day.state]
        return days


class RecurrenceEditor(urwid.WidgetWrap):

    def __init__(self, rrule, conf, startdt) -> None:
        self._conf = conf
        self._startdt = startdt
        self._rrule = rrule
        self.repeat = bool(rrule)
        self._allow_edit = not self.repeat or self.check_understood_rrule(rrule)
        self.repeat_box = urwid.CheckBox(
            'Repeat: ', state=self.repeat, on_state_change=self.check_repeat,
        )

        if "UNTIL" in self._rrule:
            self._until = "Until"
        elif "COUNT" in self._rrule:
            self._until = "Repetitions"
        else:
            self._until = "Forever"

        recurrence = self._rrule['freq'][0].lower() if self._rrule else "weekly"
        self.recurrence_choice = CPadding(CAttrMap(Choice(
            ["daily", "weekly", "monthly", "yearly"],
            recurrence,
            callback=self.rebuild,
        ), 'popupper'), align='center', left=2, right=2)
        self.interval_edit = PositiveIntEdit(
            caption=('caption', 'every:'),
            edit_text=str(self._rrule.get('INTERVAL', [1])[0]),
        )
        self.until_choice = CPadding(CAttrMap(Choice(
            ["Forever", "Until", "Repetitions"], self._until, callback=self.rebuild,
        ), 'popupper'), align='center', left=2, right=2)

        count = str(self._rrule.get('COUNT', [1])[0])
        self.repetitions_edit = PositiveIntEdit(edit_text=count)

        until = self._rrule.get('UNTIL', [None])[0]
        if until is None and isinstance(self._startdt, dt.datetime):
            until = self._startdt.date()
        elif until is None:
            until = self._startdt

        if isinstance(until, dt.datetime):
            until = until.date()
        self.until_edit = DateEdit(
            until, self._conf['locale']['longdateformat'],
            lambda _: None, self._conf['locale']['weeknumbers'],
            self._conf['locale']['firstweekday'],
            self._conf['view']['monthdisplay'],
        )

        self._rebuild_weekday_checks()
        self._rebuild_monthly_choice()
        self._pile = pile = NPile([urwid.Text('')])
        urwid.WidgetWrap.__init__(self, pile)
        self.rebuild()

    def _rebuild_monthly_choice(self):
        weekday, xth = get_weekday_occurrence(self._startdt)
        ords = {1: 'st', 2: 'nd', 3: 'rd', 21: 'st', 22: 'nd', 23: 'rd', 31: 'st'}
        self._xth_weekday = f"on every {xth}{ords.get(xth, 'th')} {WEEKDAYS[weekday]}"
        self._xth_monthday = (f"on every {self._startdt.day}"
                              f"{ords.get(self._startdt.day, 'th')} of the month")
        self.monthly_choice = Choice(
            [self._xth_monthday, self._xth_weekday], self._xth_monthday, callback=self.rebuild,
        )

    def _rebuild_weekday_checks(self):
        if self.recurrence_choice.active == 'weekly':
            initial_days = self._rrule.get('BYDAY', [])
        else:
            initial_days = []
        self.weekday_checks = WeekDaySelector(self._startdt, initial_days)

    def update_startdt(self, startdt):
        self._startdt = startdt
        self._rebuild_weekday_checks()
        self._rebuild_monthly_choice()
        self.rebuild()

    @staticmethod
    def check_understood_rrule(rrule):
        """test if we can reproduce `rrule`."""
        keys = set(rrule.keys())
        freq = rrule.get('FREQ', [None])[0]
        unsupported_rrule_parts = {
            'BYSECOND', 'BYMINUTE', 'BYHOUR', 'BYYEARDAY', 'BYWEEKNO', 'BYMONTH',
        }
        if keys.intersection(unsupported_rrule_parts):
            return False
        if len(rrule.get('BYMONTHDAY', [1])) > 1:
            return False
        # we don't support negative BYMONTHDAY numbers
        # don't need to check whole list, we only support one monthday anyway
        if rrule.get('BYMONTHDAY', [1])[0] < 1:
            return False
        if rrule.get('BYDAY', ['1'])[0][0] == '-':
            return False
        if rrule.get('BYSETPOS', [1])[0] != 1:
            return False
        if freq not in ['DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY']:
            return False
        if 'BYDAY' in keys and freq == 'YEARLY':
            return False
        return True

    def check_repeat(self, checkbox, state):
        self.repeat = state
        self.rebuild()

    def _refill_contents(self, lines):
        while True:
            try:
                self._pile.contents.pop()
            except IndexError:
                break
        [self._pile.contents.append((line, ('pack', None))) for line in lines]

    def rebuild(self):
        old_focus_y = self._pile.focus_position
        if not self._allow_edit:
            self._rebuild_no_edit()
        elif self.repeat:
            self._rebuild_edit()
            self._pile.set_focus(old_focus_y)
        else:
            self._rebuild_edit_no_repeat()

    def _rebuild_no_edit(self):
        def _allow_edit(_):
            self._allow_edit = True
            self.rebuild()
        lines = [
            urwid.Text("We cannot reproduce this event's repetition rules."),
            urwid.Text("Editing the repetition rules will destroy the current rules."),
            urwid.Button("Edit anyway", on_press=_allow_edit),
        ]
        self._refill_contents(lines)
        self._pile.set_focus(2)

    def _rebuild_edit_no_repeat(self):
        lines = [NColumns([(13, self.repeat_box)])]
        self._refill_contents(lines)

    def _rebuild_edit(self):
        firstline = NColumns([
            (13, self.repeat_box),
            (18, self.recurrence_choice),
            (13, self.interval_edit),
        ])
        lines = [firstline]

        if self.recurrence_choice.active == "weekly":
            lines.append(self.weekday_checks)
        if self.recurrence_choice.active == "monthly":
            lines.append(self.monthly_choice)

        nextline = [(20, self.until_choice.original_widget)]
        if self.until_choice.active == "Until":
            nextline.append((24, self.until_edit))
        elif self.until_choice.active == "Repetitions":
            nextline.append((4, self.repetitions_edit))
        lines.append(NColumns(nextline))

        self._refill_contents(lines)

    @property
    def changed(self):
        # TODO this often gives false positives which leads to redraws of all
        # events shown
        return self._rrule != self.rrule()  # TODO do this properly

    def rrule(self):
        rrule = {}
        rrule['freq'] = [self.recurrence_choice.active]
        interval = int(self.interval_edit.get_edit_text())
        if interval != 1:
            rrule['interval'] = [interval]
        if rrule['freq'] == ['weekly'] and len(self.weekday_checks.days) > 1:
            rrule['byday'] = self.weekday_checks.days
        if rrule['freq'] == ['monthly'] and self.monthly_choice.active == self._xth_weekday:
            weekday, occurrence = get_weekday_occurrence(self._startdt)
            rrule['byday'] = [f'{occurrence}{WEEKDAYS[weekday]}']
        if self.until_choice.active == 'Until':
            if isinstance(self._startdt, dt.datetime):
                rrule['until'] = dt.datetime.combine(
                    self.until_edit.date,
                    self._startdt.time(),
                )
            else:
                rrule['until'] = self.until_edit.date
        elif self.until_choice.active == 'Repetitions':
            rrule['count'] = int(self.repetitions_edit.get_edit_text())
        return rrule

    @property
    def active(self):
        if not self.repeat:
            return None
        else:
            return self.rrule()

    @active.setter
    def active(self, val):
        raise ValueError
        self.recurrence_choice.active = val


class ExportDialog(urwid.WidgetWrap):
    def __init__(self, this_func, abort_func, event) -> None:
        lines = []
        lines.append(urwid.Text('Export event as ICS file'))
        lines.append(urwid.Text(''))
        export_location = ExtendedEdit(
            caption='Location: ', edit_text="~/%s.ics" % event.summary.strip())
        lines.append(export_location)
        lines.append(urwid.Divider(' '))
        lines.append(CAttrMap(
            urwid.Button('Save', on_press=this_func, user_data=export_location),
            'button', 'button focus'))
        content = NPile(lines)
        urwid.WidgetWrap.__init__(self, urwid.LineBox(content))
