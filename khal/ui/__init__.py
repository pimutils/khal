# Copyright (c) 2013-2016 Christian Geier et al.
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

import calendar
from datetime import date, datetime, timedelta
from locale import getlocale
import signal
import sys

import urwid

from .. import aux
from . import colors
from .widgets import ExtendedEdit as Edit, NPile, NColumns, NListBox, Choice, AlarmsEditor, \
    linebox
from .base import Pane, Window
from .startendeditor import StartEndEditor
from .calendarwidget import CalendarWidget
from ..khalendar.exceptions import ReadOnlyCalendarError


NOREPEAT = 'No'
ALL = 0
INSTANCES = 1


class DateConversionError(Exception):
    pass


class SelectableText(urwid.Text):
    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class U_Event(urwid.Text):
    def __init__(self, event, this_date=None, eventcolumn=None, relative=True):
        """
        representation of an event in EventList

        :param event: the encapsulated event
        :type event: khal.event.Event
        """
        if relative:
            if isinstance(this_date, datetime) or not isinstance(this_date, date):
                raise ValueError('`this_date` is of type `{}`, sould be '
                                 '`datetime.date`'.format(type(this_date)))
        self.event = event
        self.this_date = this_date
        self.eventcolumn = eventcolumn
        self.conf = eventcolumn.pane.conf
        self.relative = relative
        if self.relative:
            text = self.event.format(
                self.conf['view']['agenda_event_format'],
                self.this_date,
                colors=False,
            )
        else:
            text = self.event.event_description
        super(U_Event, self).__init__(text)
        self.set_title()

    @property
    def is_viewed(self):
        return self.event is self.eventcolumn.current_event

    @classmethod
    def selectable(cls):
        return True

    @property
    def uid(self):
        return self.event.calendar + '\n' + \
            str(self.event.href) + '\n' + str(self.event.etag)

    @property
    def recuid(self):
        return (self.uid, self.event.recurrence_id)

    def set_title(self, mark=' '):
        if self.uid in self.eventcolumn.pane.deleted[ALL]:
            mark = 'D'
        elif self.recuid in self.eventcolumn.pane.deleted[INSTANCES]:
            mark = 'd'
        if self.relative:
            text = self.event.relative_to(self.this_date)
        else:
            text = self.event.event_description
        self.set_text(mark + ' ' + text)

    def export_event(self):
        """
        export the event as ICS
        """
        def export_this(_, user_data):
            try:
                self.event.export_ics(user_data.get_edit_text())
            except Exception as e:
                self.eventcolumn.pane.window.backtrack()
                self.eventcolumn.pane.window.alert(
                    ('light red',
                     'Failed to save event: %s' % e))
                return

            self.eventcolumn.pane.window.backtrack()
            self.eventcolumn.pane.window.alert(
                ('light green',
                 'Event successfuly exported'))

        overlay = urwid.Overlay(
            ExportDialog(
                export_this,
                self.eventcolumn.pane.window.backtrack,
                self.event,
            ),
            self.eventcolumn.pane,
            'center', ('relative', 50), ('relative', 50), None)
        self.eventcolumn.pane.window.open(overlay)

    def toggle_delete(self):
        """toggle the delete status of this event"""
        def delete_this(_):
            if self.recuid in self.eventcolumn.pane.deleted[INSTANCES]:
                self.eventcolumn.pane.deleted[INSTANCES].remove(self.recuid)
            else:
                self.eventcolumn.pane.deleted[INSTANCES].append(self.recuid)
            self.eventcolumn.pane.window.backtrack()
            self.set_title()

        def delete_all(_):
            if self.uid in self.eventcolumn.pane.deleted[ALL]:
                self.eventcolumn.pane.deleted[ALL].remove(self.uid)
            else:
                self.eventcolumn.pane.deleted[ALL].append(self.uid)
            self.eventcolumn.pane.window.backtrack()
            self.set_title()

        if self.event.readonly:
            self.eventcolumn.pane.window.alert(
                ('light red',
                 'Calendar {} is read-only.'.format(self.event.calendar)))
            return

        if self.uid in self.eventcolumn.pane.deleted[ALL]:
            self.eventcolumn.pane.deleted[ALL].remove(self.uid)
        elif self.recuid in self.eventcolumn.pane.deleted[INSTANCES]:
            self.eventcolumn.pane.deleted[INSTANCES].remove(self.recuid)
        elif self.event.recurring:
            overlay = urwid.Overlay(
                DeleteDialog(
                    delete_this,
                    delete_all,
                    self.eventcolumn.pane.window.backtrack,
                ),
                self.eventcolumn.pane,
                'center', ('relative', 70), ('relative', 70), None)
            self.eventcolumn.pane.window.open(overlay)
        else:
            self.eventcolumn.pane.deleted[ALL].append(self.uid)
        self.set_title()

    def duplicate(self):
        """duplicate this event"""
        focused = self.eventcolumn.events.list_walker.focus
        event = self.event.duplicate()
        try:
            event = self.eventcolumn.pane.collection.new(event)
        except ReadOnlyCalendarError:
            self.eventcolumn.pane.window.alert(
                ('light red', 'Read-only calendar'))
        else:
            self.eventcolumn.set_current_date(self.eventcolumn.current_date)
            self.eventcolumn.events.list_walker.set_focus(focused)

    def keypress(self, _, key):
        binds = self.conf['keybindings']
        if key in binds['left']:
            key = 'left'
        elif key in binds['up']:
            key = 'up'
        elif key in binds['right']:
            key = 'right'
        elif key in binds['down']:
            key = 'down'
        elif key in binds['delete']:
            self.toggle_delete()
            key = 'down'
        elif key in binds['duplicate']:
            self.duplicate()
            key = None
        elif key in binds['export']:
            self.export_event()
            key = None
        return key


class DListBox(urwid.ListBox):
    def __init__(self, *args, parent, **kwargs):
        self._init = True
        self.parent = parent
        self._old_focus = None
        super().__init__(*args, **kwargs)

    def render(self, size, focus=False):
        if self._init:
            while 'bottom' in self.ends_visible(size):
                self.body._autoextend()
            self._init = False
        return super().render(size, focus)

    def clean(self):
        if self._old_focus is not None:
            self.body[self._old_focus].contents[0][0].set_attr_map({None: 'date'})

    def update_by_date(self, day):
        """update the entry for `day` and bring it into focus"""
        try:
            self._old_focus = self.focus_position
        except IndexError:
            pass
        rval = self.body.update_by_date(day)
        self.body[self.focus_position].contents[0][0].set_attr_map({None: 'green'})
        self.set_focus_valign('top')  # FIXME does not work
        self.clean()
        return rval

    def keypress(self, size, key):
        movements = self.parent.pane.conf['keybindings']['up'] + \
            self.parent.pane.conf['keybindings']['down'] + ['tab', 'shift tab']
        if key in movements:
            try:
                self._old_focus = self.focus_position
            except IndexError:
                pass
            day = self.body[self.body.focus].date

            # we need to save DatePile.selected_date and reset it later, because
            # calling CalendarWalker.set_focus_date() calls back into
            # DayWalker().update_by_date() which actually set selected_date
            # that's why it's called callback hell...
            currently_selected_date = DatePile.selected_date
            self.parent.pane.calendar.base_widget.set_focus_date(day)  # TODO convert to callback
            DatePile.selected_date = currently_selected_date
#            self.body[self.focus_position + 1].contents[0][0].set_attr_map({None: 'date focus'})
        # TODO this really does not belong here, move it one step

        rval = super().keypress(size, key)
        self.clean()
        return rval


class DayWalker(urwid.SimpleFocusListWalker):
    """A list Walker that contains a list of DatePile objects, each representing
    one day and associated events"""

    def __init__(self, this_date, eventcolumn):
        self.eventcolumn = eventcolumn
        self._init = True
        self._last_day = this_date
        self._first_day = this_date

        firstweekday = eventcolumn.pane.conf['locale']['firstweekday']
        calendar.setfirstweekday(firstweekday)
        try:
            mylocale = '.'.join(getlocale())
        except TypeError:  # language code and encoding may be None
            mylocale = 'C'
        _calendar = calendar.LocaleTextCalendar(firstweekday, mylocale)
        self.weekdays = [weekday for weekday in _calendar.formatweekheader(11).split(' ') if weekday]

        super().__init__(list())
        self.update_by_date(this_date)


    def update_by_date(self, day):
        """make sure a DatePile for `day` exists and bring it into focus"""
        item_no = None
        if len(self) == 0:
            pile = self._get_events(day)
            self.append(pile)
            self._last_day = day
            self._first_day = day
            item_no = 0
        while day < self[0].date:
            self._autoprepend()
            item_no = 0
        while day > self[-1].date:
            self._autoextend()
            item_no = len(self) - 1
        if item_no is None:
            item_no = (day - self[0].date).days

        assert self[item_no].date == day
        DatePile.selected_date = day
        self.set_focus(item_no)

    def set_focus(self, position):
        """set focus by item number"""
        while position >= len(self) - 1:
            self._autoextend()
        while position <= 0:
            self._autoprepend()
            position += 1
        return super().set_focus(position)

    def _autoextend(self):
        self._last_day += timedelta(days=1)
        pile = self._get_events(self._last_day)
        self.append(pile)

    def _autoprepend(self):
        self._first_day -= timedelta(days=1)
        pile = self._get_events(self._first_day)
        self.insert(0, pile)

    def _get_events(self, day):
        """get all events on day, return a Pile of `U_Event()`s

        :type day: datetime.date
        """
        event_list = list()
        date_text = SelectableText(
            relative_day(
                day,
                self.weekdays[day.weekday()],
                self.eventcolumn.pane.conf['locale']['longdateformat']),
        )
        event_list.append(urwid.AttrMap(date_text, 'date'))
        self.events = sorted(self.eventcolumn.pane.collection.get_events_on(day))
        if not self.events:
            event_list.append(urwid.AttrMap(urwid.Text('  no scheduled events'), 'text'))
        event_list.extend([
            urwid.AttrMap(U_Event(event, this_date=day, eventcolumn=self.eventcolumn),
                          'calendar ' + event.calendar, 'reveal focus') for event in self.events])
        return DatePile(event_list, date=day)

    def selectable(self):
        """mark this widget as selectable"""
        return True

    @property
    def current_event(self):
        return self[self.focus].current_event


class DatePile(urwid.Pile):
    selected_date = None

    def __init__(self, *args, date, **kwargs):
        self.date = date
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return '<DatePile Widget {}>'.format(self.date)

    __str__ = __repr__

    def selectable(self):
        return True

    def keypress(self, size, key):
        return super().keypress(size, key)

    def render(self, a, focus):
        if focus:
            self.contents[0][0].set_attr_map({None: 'date focused'})
        elif DatePile.selected_date == self.date:
            self.contents[0][0].set_attr_map({None: 'date selected'})
        else:
            self.contents[0][0].set_attr_map({None: 'date'})
        return super().render(a, focus)

    @property
    def current_event(self):
        """return the U_Event in focus, if none is, return None"""
        if self.focus_position == 0:
            return None
        else:
            return self.focus.original_widget


class EventColumn(urwid.WidgetWrap):
    """contains the eventlist as well as the event viewer"""

    def __init__(self, pane):
        self.pane = pane
        self._conf = pane.conf
        self.divider = urwid.Divider('─')
        self.editor = False
        self._current_date = None
        self._eventshown = False
        self.event_width = int(self.pane.conf['view']['event_view_weighting'])
        self.events = DayWalker(date.today(), eventcolumn=self)
        self.dlistbox = DListBox(self.events, parent=self)
        self.container = urwid.Pile([self.dlistbox])
        urwid.WidgetWrap.__init__(self, self.container)

    @property
    def focus_event(self):
        """returns the event currently in focus"""
        return self.events.current_event

    @focus_event.setter
    def focus_event(self, event):
        raise
        while len(self.container.contents) > 1:
            self.container.contents.pop()
        if not event:
            return
        self.container.contents.append((self.divider, ('pack', None)))
        self.container.contents.append(
            (EventDisplay(self.pane.conf, event, collection=self.pane.collection),
             ('weight', self.event_width)))

    def view(self, event):
        """show event in the lower part of this column"""
        self._eventshown = True
        self.container.contents.append((self.divider, ('pack', None)))
        self.container.contents.append(
            (EventDisplay(self.pane.conf, event, collection=self.pane.collection),
             ('weight', self.event_width)))

    def clear_event_view(self):
        self._eventshown = False
        while len(self.container.contents) > 1:
            self.container.contents.pop()

    def set_focus_date(self, date):
        self.focus_date = date

    @property
    def focus_date(self):
        return self._current_date

    @focus_date.setter
    def focus_date(self, date):
        self._current_date = date
        self.dlistbox.update_by_date(date)
 #       self.current_event = self.current_event

        # Show firast event if show event view is true
        if self.pane.conf['view']['event_view_always_visible']:
            if len(self.events.events) > 0:
                self.current_event = self.events.events[0]
            else:
                self.current_event = None

    def edit(self, event):
        """create an EventEditor and display it

        :param event: event to edit
        :type event: khal.event.Event
        """
        if event.readonly:
            self.pane.window.alert(
                ('light red', 'Calendar {} is read-only.'.format(event.calendar)))
            return

        if isinstance(event.start_local, datetime):
            original_start = event.start_local.date()
        else:
            original_start = event.start_local
        if isinstance(event.end_local, datetime):
            original_end = event.end_local.date()
            original_end = event.end_local

        def update_colors(new_start, new_end):
            if isinstance(new_start, datetime):
                new_start = new_start.date()
            if isinstance(new_end, datetime):
                new_end = new_end.date()
            min_date = min(original_start, new_start)
            max_date = max(original_end, new_end)
            self.pane.calendar.base_widget.reset_styles_range(min_date, max_date)

        if self.editor:
            self.pane.window.backtrack()

        assert not self.editor
        self.editor = True
        editor = EventEditor(self.pane, event, update_colors)
        #current_day = self.container.contents[0][0]  FIXME

        ContainerWidget = linebox[self.pane.conf['view']['frame']]
        new_pane = urwid.Columns([
            ('weight', 2, ContainerWidget(editor)),
            ('weight', 1, ContainerWidget(self.dlistbox))
        ], dividechars=0, focus_column=0)
        new_pane.title = editor.title
        new_pane.get_keys = editor.get_keys

        def teardown(data):
            self.editor = False
        self.pane.window.open(new_pane, callback=teardown)

    def new(self, date, end):
        """create a new event on `date`

        :param date: default date for new event
        :type date: datetime.date
        """
        if not self.pane.collection.writable_names:
            self.pane.window.alert(('light red', 'No writable calendar.'))
            return
        if end is None:
            start = datetime.combine(date, datetime.now().time())
            end = start + timedelta(minutes=60)
            event = aux.new_event(dtstart=start, dtend=end, summary="new event",
                                  timezone=self.pane.conf['locale']['default_timezone'],
                                  locale=self.pane.conf['locale'])
        else:
            event = aux.new_event(dtstart=date, dtend=end, summary="new event",
                                  allday=True, locale=self.pane.conf['locale'])
        event = self.pane.collection.new_event(
            event.to_ical(), self.pane.collection.default_calendar_name)
        self.edit(event)

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key in self._conf['keybindings']['view'] and self.focus_event:
            if not self._eventshown:
                self.view(self.focus_event.event)
            elif self.focus_event.uid in self.pane.deleted[ALL] or \
                        self.focus_event.recuid in self.pane.deleted[INSTANCES]:
                    self.pane.window.alert(
                        ('light red', 'This event is marked as deleted'))
            else:
                self.clear_event_view()
                self.edit(self.focus_event.event)
        elif key in ['esc'] and self._eventshown:
            self.clear_event_view()
        elif key in self._conf['keybindings']['new']:
            self.new(self.focus_date, self.focus_date)
        else:
            return super().keypress(size, key)

    def render(self, a, focus):
        if focus:
            DatePile.selected_date = None
        return super().render(a, focus)


class RecurrenceEditor(urwid.WidgetWrap):

    def __init__(self, rrule):
        # TODO: support more recurrence schemes

        self.rrule = rrule
        recurrence = self.rrule['freq'][0].lower() if self.rrule else NOREPEAT
        self.recurrence_choice = Choice(
            [NOREPEAT, u"weekly", u"monthly", u"yearly"], recurrence)
        self.columns = urwid.Columns([(10, urwid.Text('Repeat: ')), (11, self.recurrence_choice)])
        urwid.WidgetWrap.__init__(self, self.columns)

    @property
    def changed(self):
        if self.recurrence_choice.changed:
            return True
        return False

    @property
    def active(self):
        recurrence = self.recurrence_choice.active
        if recurrence != NOREPEAT:
            self.rrule["freq"] = [recurrence]
            return self.rrule
        return None

    @active.setter
    def active(self, val):
        self.recurrence_choice.active = val


class EventDisplay(urwid.WidgetWrap):
    """A widget showing one Event()'s details """

    def __init__(self, conf, event, collection=None):
        self.conf = conf
        self.collection = collection
        self.event = event
        divider = urwid.Divider(' ')

        lines = []
        lines.append(urwid.Text('Title: ' + event.summary))

        # show organizer
        if event.organizer != '':
            lines.append(urwid.Text('Organizer: ' + event.organizer))

        if event.location != '':
            lines.append(urwid.Text('Location: ' + event.location))

        if event.categories != '':
            lines.append(urwid.Text('Categories: ' + event.categories))

        # start and end time/date
        if event.allday:
            startstr = event.start_local.strftime(self.conf['locale']['dateformat'])
            endstr = event.end_local.strftime(self.conf['locale']['dateformat'])
        else:
            startstr = event.start_local.strftime(
                '{} {}'.format(self.conf['locale']['dateformat'],
                               self.conf['locale']['timeformat'])
            )
            if event.start_local.date == event.end_local.date:
                endstr = event.end_local.strftime(self.conf['locale']['timeformat'])
            else:
                endstr = event.end_local.strftime(
                    '{} {}'.format(self.conf['locale']['dateformat'],
                                   self.conf['locale']['timeformat'])
                )

        if startstr == endstr:
            lines.append(urwid.Text('Date: ' + startstr))
        else:
            lines.append(urwid.Text('Date: ' + startstr + ' - ' + endstr))

        lines.append(urwid.Text('Calendar: ' + event.calendar))
        lines.append(divider)

        if event.description != '':
            lines.append(urwid.Text(event.description))


        pile = urwid.Pile(lines)
        urwid.WidgetWrap.__init__(self, urwid.Filler(pile, valign='top'))



class EventEditor(urwid.WidgetWrap):
    """Widget that allows Editing one `Event()`"""

    def __init__(self, pane, event, save_callback=None):
        """
        :type event: khal.event.Event
        :param save_callback: call when saving event with new start and end
             dates as parameters
        :type save_callback: callable
        """

        self.pane = pane
        self.event = event
        self._save_callback = save_callback

        self.collection = pane.collection
        self.conf = pane.conf

        self._abort_confirmed = False

        self.description = event.description
        self.location = event.location
        self.categories = event.categories
        self.startendeditor = StartEndEditor(
            event.start_local, event.end_local, self.conf,
            self.pane.eventscolumn.original_widget.set_focus_date)
        self.recurrenceeditor = RecurrenceEditor(self.event.recurobject)
        self.summary = Edit(caption='Title: ', edit_text=event.summary)

        divider = urwid.Divider(' ')

        def decorate_choice(c):
            return ('calendar ' + c['name'], c['name'])

        self.calendar_chooser = Choice(
            [self.collection._calendars[c] for c in self.collection.writable_names],
            self.collection._calendars[self.event.calendar],
            decorate_choice
        )
        self.description = Edit(caption='Description: ',
                                edit_text=self.description, multiline=True)
        self.location = Edit(caption='Location: ',
                             edit_text=self.location)
        self.categories = Edit(caption='Categories: ',
                               edit_text=self.categories)
        self.alarms = AlarmsEditor(self.event)
        self.pile = NListBox(urwid.SimpleFocusListWalker([
            NColumns([self.summary, self.calendar_chooser], dividechars=2),
            divider,
            self.location,
            self.categories,
            self.description,
            divider,
            self.startendeditor,
            self.recurrenceeditor,
            divider,
            self.alarms,
            divider,
            urwid.Button('Save', on_press=self.save),
            urwid.Button('Export', on_press=self.export)
        ]), outermost=True)

        urwid.WidgetWrap.__init__(self, self.pile)

    @property
    def title(self):  # Window title
        return 'Edit: {}'.format(self.summary.get_edit_text())

    def get_keys(self):
        return [(['arrowsu'], 'navigate through properties'),
                (['enter'], 'edit property'),
                (['esc'], 'abort')]

    @classmethod
    def selectable(cls):
        return True

    @property
    def changed(self):
        if self.summary.get_edit_text() != self.event.summary:
            return True
        if self.description.get_edit_text() != self.event.description:
            return True
        if self.location.get_edit_text() != self.event.location:
            return True
        if self.categories.get_edit_text() != self.event.categories:
            return True
        if self.startendeditor.changed or self.calendar_chooser.changed:
            return True
        if self.recurrenceeditor.changed:
            return True
        if self.alarms.changed:
            return True
        return False

    def update_vevent(self):
        self.event.update_summary(self.summary.get_edit_text())
        self.event.update_description(self.description.get_edit_text())
        self.event.update_location(self.location.get_edit_text())
        self.event.update_categories(self.categories.get_edit_text())

        if self.startendeditor.changed:
            self.event.update_start_end(
                self.startendeditor.startdt, self.startendeditor.enddt)
        if self.recurrenceeditor.changed:
            rrule = self.recurrenceeditor.active
            self.event.update_rrule(rrule)

        if self.alarms.changed:
            self.event.update_alarms(self.alarms.get_alarms())

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
        """
        saves the event to the db (only when it has been changed)
        :param button: not needed, passed via the button press
        """
        if not self.startendeditor.validate():
            self.pane.window.alert(
                ('light red', "Can't save: end date is before start date!"))
            return
        if self.changed is True:
            self.update_vevent()
            self.event.allday = self.startendeditor.allday
            self.event.increment_sequence()
            if self.event.etag is None:  # has not been saved before
                self.event.calendar = self.calendar_chooser.active['name']
                self.collection.new(self.event)
            elif self.calendar_chooser.changed:
                self.collection.change_collection(
                    self.event,
                    self.calendar_chooser.active['name']
                )
            else:
                self.collection.update(self.event)

            self._save_callback(self.event.start_local, self.event.end_local)
        self._abort_confirmed = False
        self.pane.window.backtrack()

    def keypress(self, size, key):
        if key in ['esc'] and self.changed and not self._abort_confirmed:
            self.pane.window.alert(
                ('light red', 'Unsaved changes! Hit ESC again to discard.'))
            self._abort_confirmed = True
            return
        else:
            self._abort_confirmed = False
        if key in self.pane.conf['keybindings']['save']:
            self.save(None)
        return super().keypress(size, key)


class DeleteDialog(urwid.WidgetWrap):
    def __init__(self, this_func, all_func, abort_func):
        lines = []
        lines.append(urwid.Text('This is a recurring event.'))
        lines.append(urwid.Text('Which instances do you want to delete?'))
        lines.append(urwid.Text(''))
        buttons = NColumns(
            [urwid.Button('Only this', on_press=this_func),
             urwid.Button('All (past and future)', on_press=all_func),
             urwid.Button('Abort', on_press=abort_func),
             ], outermost=True)
        lines.append(buttons)
        content = urwid.Pile(lines)
        urwid.WidgetWrap.__init__(self, urwid.LineBox(content))


class ExportDialog(urwid.WidgetWrap):
    def __init__(self, this_func, abort_func, event):
        lines = []
        lines.append(urwid.Text('Export event as ICS file'))
        lines.append(urwid.Text(''))
        export_location = Edit(caption='Location: ',
                               edit_text="~/%s.ics" % event.summary.strip())
        lines.append(export_location)
        lines.append(urwid.Divider(' '))
        lines.append(
            urwid.Button('Save', on_press=this_func, user_data=export_location)
        )
        content = NPile(lines)
        urwid.WidgetWrap.__init__(self, urwid.LineBox(content))


class SearchDialog(urwid.WidgetWrap):
    def __init__(self, search_func, abort_func):

        class Search(Edit):

            def keypress(self, size, key):
                if key == 'enter':
                    search_func(self.text)
                else:
                    return super().keypress(size, key)

        search_field = Search('')

        def this_func(_):
            search_func(search_field.text)

        lines = []
        lines.append(urwid.Text('Please enter a search term (Escape cancels):'))
        lines.append(search_field)
        buttons = NColumns([urwid.Button('Search', on_press=this_func),
                            urwid.Button('Abort', on_press=abort_func)])
        lines.append(buttons)
        content = NPile(lines, outermost=True)
        urwid.WidgetWrap.__init__(self, urwid.LineBox(content))


class ClassicView(Pane):

    """default Pane for khal

    showing a CalendarWalker on the left and the eventList + eventviewer/editor
    on the right
    """

    def __init__(self, collection, conf=None, title='',
                 description=''):
        self.init = True
        # Will be set when opening the view inside a Window
        self.window = None
        self.conf = conf
        self.collection = collection
        self.deleted = {ALL: [], INSTANCES: []}

        ContainerWidget = linebox[self.conf['view']['frame']]
        self.eventscolumn = ContainerWidget(EventColumn(pane=self))
        calendar = CalendarWidget(
            on_date_change=self.eventscolumn.original_widget.set_focus_date,
            keybindings=self.conf['keybindings'],
            on_press={key: self.new_event for key in self.conf['keybindings']['new']},
            firstweekday=conf['locale']['firstweekday'],
            weeknumbers=conf['locale']['weeknumbers'],
            get_styles=collection.get_styles
        )
        self.calendar = ContainerWidget(calendar)
        lwidth = 31 if conf['locale']['weeknumbers'] == 'right' else 28
        columns = urwid.Columns([(lwidth, self.calendar), self.eventscolumn],
                                dividechars=0,
                                box_columns=[0, 1])
        Pane.__init__(self, columns, title=title, description=description)

    def keypress(self, size, key):
        binds = self.conf['keybindings']
        if key in binds['search']:
            self.search()
        return super().keypress(size, key)

    def search(self):
        overlay = urwid.Overlay(
            SearchDialog(self._search, self.window.backtrack), self,
            align='center',
            width=('relative', 70),
            valign=('relative', 50),
            height=None)
        self.window.open(overlay)

    def _search(self, search_term):
        self.window.backtrack()
        events = list(self.collection.search(search_term))
        self.eventscolumn.original_widget.events.update_events(events)
        self.widget.set_focus_column(1)

    def render(self, size, focus=False):
        rval = super(ClassicView, self).render(size, focus)
        if self.init:
            # starting with today's events
            self.eventscolumn.current_date = date.today()
            self.init = False
        return rval

    def get_keys(self):
        return [(['arrows'], 'navigate through the calendar'),
                (['t'], 're-focus on today'),
                (['enter', 'tab'], 'select a date/event, show/edit event'),
                (['n'], 'create event on selected day'),
                (['d'], 'delete selected event'),
                (['e'], 'export selected event'),
                (['q', 'esc'], 'previous pane/quit'),
                ]

    def show_date(self, date):
        raise
        self.eventscolumn.original_widget.current_date = date

    def new_event(self, date, end):
        self.eventscolumn.original_widget.new(date, end)

    def cleanup(self, data):
        for part in self.deleted[ALL]:
            account, href, etag = part.split('\n', 2)
            self.collection.delete(href, etag, account)
        for part, rec_id in self.deleted[INSTANCES]:
            account, href, etag = part.split('\n', 2)
            event = self.collection.get_event(href, account)
            event.delete_instance(rec_id)
            self.collection.update(event)


def _urwid_palette_entry(name, color, hmethod):
    """Create an urwid compatible palette entry.

    :param name: name of the new attribute in the palette
    :type name: string
    :param color: color for the new attribute
    :type color: string
    :returns: an urwid palette entry
    :rtype: tuple
    """
    from ..terminal import COLORS
    if color == '' or color in COLORS or color is None:
        # Named colors already use urwid names, no need to change anything.
        pass
    elif color.isdigit():
        # Colors from the 256 color palette need to be prefixed with h in
        # urwid.
        color = 'h' + color
    else:
        # 24-bit colors are not supported by urwid.
        # Convert it to some color on the 256 color palette that might resemble
        # the 24-bit color.
        # First, generate the palette (indices 16-255 only). This assumes, that
        # the terminal actually uses the same palette, which may or may not be
        # the case.
        colors = {}
        # Colorcube
        colorlevels = (0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff)
        for r in range(0, 6):
            for g in range(0, 6):
                for b in range(0, 6):
                    colors[r * 36 + g * 6 + b + 16] = \
                        (colorlevels[r], colorlevels[g], colorlevels[b])
        # Grayscale
        graylevels = [0x08 + 10 * i for i in range(0, 24)]
        for c in range(0, 24):
            colors[232 + c] = (graylevels[c], ) * 3
        # Parse the HTML-style color into the variables r, g, b.
        if len(color) == 4:
            # e.g. #ABC, equivalent to #AABBCC
            r = int(color[1] * 2, 16)
            g = int(color[2] * 2, 16)
            b = int(color[3] * 2, 16)
        else:
            # e.g. #AABBCC
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
        # Now, find the color with the least distance to the requested color.
        best = None
        bestdist = 0.0
        for index, rgb in colors.items():
            # This is the euclidean distance metric. It is quick, simple and
            # wrong (in the sense of human color perception). However, any
            # serious color distance metric would be way more complicated.
            dist = (r - rgb[0]) ** 2 + (g - rgb[1]) ** 2 + (b - rgb[2]) ** 2
            if best is None or dist < bestdist:
                best = index
                bestdist = dist
        color = 'h' + str(best)
    # We unconditionally add the color to the high color slot. It seems to work
    # in lower color terminals as well.
    if hmethod in ['fg', 'foreground']:
        return (name, '', '', '', color, '')
    else:
        return (name, '', '', '', '', color)


def _add_calendar_colors(palette, collection):
    """Add the colors for the defined calendars to the palette.

    :param palette: the base palette
    :type palette: list
    :param collection:
    :type collection: CalendarCollection
    :returns: the modified palette
    :rtype: list
    """
    for cal in collection.calendars:
        if cal['color'] == '':
            # No color set for this calendar, use default_color instead.
            color = collection.default_color
        else:
            color = cal['color']
        palette.append(_urwid_palette_entry('calendar ' + cal['name'], color,
                                            collection.hmethod))
    palette.append(_urwid_palette_entry('highlight_days_color',
                                        collection.color, collection.hmethod))
    palette.append(_urwid_palette_entry('highlight_days_multiple',
                                        collection.multiple, collection.hmethod))
    return palette


def start_pane(pane, callback, program_info='', quit_keys=['q']):
    """Open the user interface with the given initial pane."""
    frame = Window(
        footer=program_info + ' | {}: quit, ?: help'.format(quit_keys[0]),
        quit_keys=quit_keys,
    )
    frame.open(pane, callback)
    palette = _add_calendar_colors(getattr(colors, pane.conf['view']['theme']),
                                   pane.collection)
    loop = urwid.MainLoop(frame, palette,
                          unhandled_input=frame.on_key_press,
                          pop_ups=True)
    # Make urwid use 256 color mode.
    loop.screen.set_terminal_properties(
        colors=256, bright_is_bold=pane.conf['view']['bold_for_light_color'])

    def ctrl_c(signum, f):
        raise urwid.ExitMainLoop()

    signal.signal(signal.SIGINT, ctrl_c)
    try:
        loop.run()
    except Exception:
        import traceback
        tb = traceback.format_exc()
        try:  # Try to leave terminal in usable state
            loop.stop()
        except Exception:
            pass
        print(tb)
        sys.exit(1)


def relative_day(day, weekday, dtformat):
    """convert day into a string with its weekday and relative distance to today

    :param day: day to be converted
    :type: day: datetime.day
    :param weekday: `day`'s weekday
    :type weekday: str
    :param dtformat: the format day is to be printed in, passed to strftime
    :tpye dtformat: str
    :rtype: str
    """

    daystr = day.strftime(dtformat)
    if day == date.today():
        return 'Today ({}, {})'.format(weekday, daystr)
    elif day == date.today() + timedelta(days=1):
        return 'Tomorrow ({}, {})'.format(weekday, daystr)
    elif day == date.today() - timedelta(days=1):
        return 'Yesterday ({}, {})'.format(weekday, daystr)

    days = (day - date.today()).days
    if days < 0:
        direction = 'ago'
    else:
        direction = 'from now'
    if abs(days) < 7:
        unit = 'day'
        count = abs(days)
    elif abs(days) < 365:
        unit = 'week'
        count = int(abs(days) / 7)
    else:
        unit = 'year'
        count = int(abs(days) / 365)
    if count > 1:
        unit += 's'

    return '{weekday}, {day} ({count} {unit} {direction})'.format(
        weekday=weekday,
        day=daystr,
        count=count,
        unit=unit,
        direction=direction,
    )
