# vim: set ts=4 sw=4 expandtab sts=4 fileencoding=utf-8:
# Copyright (c) 2013-2015 Christian Geier et al.
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

from datetime import date, datetime, time
import signal
import sys

import urwid

from .. import aux
from . import colors
from .base import Pane, Window, Choice
from .widgets import ExtendedEdit as Edit
from .startendeditor import StartEndEditor
from .calendarwidget import CalendarWidget


NOREPEAT = 'No'
ALL = 0
INSTANCES = 1


class DateConversionError(Exception):
    pass


class U_Event(urwid.Text):

    def __init__(self, event, this_date=None, eventcolumn=None):
        """
        representation of an event in EventList

        :param event: the encapsulated event
        :type event: khal.event.Event
        """
        if isinstance(this_date, datetime) or not isinstance(this_date, date):
            raise ValueError('`this_date` is of type `{}`, sould be '
                             '`datetime.date`'.format(type(this_date)))
        self.event = event
        self.this_date = this_date
        self.eventcolumn = eventcolumn
        self.conf = eventcolumn.pane.conf
        super(U_Event, self).__init__(self.event.relative_to(self.this_date))
        self.set_title()

    @property
    def is_viewed(self):
        return self.event is self.eventcolumn.current_event

    @classmethod
    def selectable(cls):
        return True

    @property
    def uid(self):
        return self.event.calendar + u'\n' + \
            str(self.event.href) + u'\n' + str(self.event.etag)

    @property
    def recuid(self):
        return (self.uid, self.event.recurrence_id)

    def set_title(self, mark=' '):
        if self.uid in self.eventcolumn.pane.deleted[ALL]:
            mark = 'D'
        elif self.recuid in self.eventcolumn.pane.deleted[INSTANCES]:
            mark = 'd'
        self.set_text(mark + u' ' + self.event.relative_to(self.this_date))

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
        event = self.eventcolumn.pane.collection.new(event)
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

        if key in binds['view']:
            if self.is_viewed:
                if self.uid in self.eventcolumn.pane.deleted[ALL] or \
                        self.recuid in self.eventcolumn.pane.deleted[INSTANCES]:
                    self.eventcolumn.pane.window.alert(
                        ('light red', 'This event is marked as deleted'))
                    return
                self.eventcolumn.edit(self.event)
            else:
                self.eventcolumn.current_event = self.event
        elif key in binds['delete']:
            self.toggle_delete()
        elif key in binds['duplicate']:
            self.duplicate()
        elif key in ['left', 'up', 'down']:
            if not self.conf['view']['event_view_always_visible']:
                self.eventcolumn.current_event = None
            else:
                events = self.eventcolumn.events.events
                focused = self.eventcolumn.events.list_walker.focus
                if key == 'down' and focused < len(events) - 1:
                    self.eventcolumn.current_event = events[focused + 1]
                if key == 'up' and focused > 0:
                    self.eventcolumn.current_event = events[focused - 1]

        if key in ['esc'] and self.eventcolumn.current_event:
            self.eventcolumn.current_event = None
        else:
            return key


class EventList(urwid.WidgetWrap):

    """list of events"""

    def __init__(self, eventcolumn):
        self.eventcolumn = eventcolumn
        self.events = None
        self.list_walker = None
        pile = urwid.Filler(urwid.Pile([]))
        urwid.WidgetWrap.__init__(self, pile)
        self.update()

    def update(self, this_date=date.today()):
        if this_date is None:   # this_date might be None
            return
        local_tz = self.eventcolumn.pane.conf['locale']['local_timezone']
        start = local_tz.localize(datetime.combine(this_date, time.min))
        end = local_tz.localize(datetime.combine(this_date, time.max))

        date_text = urwid.Text(
            this_date.strftime(self.eventcolumn.pane.conf['locale']['longdateformat']))
        event_column = list()
        all_day_events = self.eventcolumn.pane.collection.get_allday_by_time_range(this_date)
        events = self.eventcolumn.pane.collection.get_datetime_by_time_range(start, end)

        for event in all_day_events:
            event_column.append(
                urwid.AttrMap(U_Event(event, this_date=this_date,
                                      eventcolumn=self.eventcolumn),
                              event.color, 'reveal focus'))
        events.sort(key=lambda e: e.start)
        for event in events:
            event_column.append(
                urwid.AttrMap(U_Event(event, this_date=this_date,
                                      eventcolumn=self.eventcolumn),
                              event.color, 'reveal focus'))
        event_list = [urwid.AttrMap(event, None, 'reveal focus')
                      for event in event_column]
        event_count = len(event_list)
        if not event_list:
            event_list = [urwid.Text('no scheduled events')]
        self.list_walker = urwid.SimpleFocusListWalker(event_list)
        pile = urwid.ListBox(self.list_walker)
        pile = urwid.Frame(pile, header=date_text)
        self._w = pile
        self.events = all_day_events + events
        return event_count


class EventColumn(urwid.WidgetWrap):

    """contains the eventlist as well as the event viewer"""

    def __init__(self, pane):
        self.pane = pane
        self.divider = urwid.Divider(u'─')
        self.editor = False
        self.eventcount = 0
        self._current_date = None
        self.event_width = int(self.pane.conf['view']['event_view_weighting'])

        self.events = EventList(eventcolumn=self)
        self.container = urwid.Pile([self.events])
        urwid.WidgetWrap.__init__(self, self.container)

    @property
    def current_event(self):
        """returns the event currently in focus"""
        l = len(self.container.contents)
        assert l > 0
        if l > 2:
            return self.container.contents[-1][0].event

    @current_event.setter
    def current_event(self, event):
        while len(self.container.contents) > 1:
            self.container.contents.pop()
        if not event:
            return
        self.container.contents.append((self.divider, ('pack', None)))
        self.container.contents.append(
            (EventDisplay(self.pane.conf, event, collection=self.pane.collection),
             ('weight', self.event_width)))

    @property
    def current_date(self):
        return self._current_date

    @current_date.setter
    def current_date(self, date):
        self._current_date = date
        self.eventcount = self.events.update(date)
        self.current_event = self.current_event

        # Show first event if show event view is true
        if self.pane.conf['view']['event_view_always_visible']:
            if len(self.events.events) > 0:
                self.current_event = self.events.events[0]
            else:
                self.current_event = None

    def set_current_date(self, date):
        self.current_date = date

    def edit(self, event):
        """create an EventEditor and display it

        :param event: event to edit
        :type event: khal.event.Event
        """
        if event.readonly:
            self.pane.window.alert(
                ('light red',
                 'Calendar {} is read-only.'.format(event.calendar)))
            return

        if self.editor:
            self.pane.window.backtrack()

        assert not self.editor
        self.editor = True
        editor = EventEditor(self.pane, event)
        current_day = self.container.contents[0][0]

        if self.pane.conf['view']['frame']:
            ContainerWidget = urwid.LineBox
        else:
            ContainerWidget = urwid.WidgetPlaceholder
        new_pane = urwid.Columns([
            ('weight', 1.5, ContainerWidget(editor)),
            ('weight', 1, ContainerWidget(current_day))
        ], dividechars=0, focus_column=0)
        new_pane.title = editor.title
        new_pane.get_keys = editor.get_keys

        def teardown(data):
            self.editor = False
            self.current_date = self.current_date
        self.pane.window.open(new_pane, callback=teardown)

    def new(self, date, end):
        """create a new event on date

        :param date: default date for new event
        :type date: datetime.date
        """
        if end is None:
            event = aux.new_event(
                dtstart=date, timezone=self.pane.conf['locale']['default_timezone'])
        else:
            event = aux.new_event(dtstart=date, dtend=end, allday=True)

        # TODO proper default cal
        event = self.pane.collection.new_event(
            event.to_ical(), self.pane.collection.default_calendar_name)

        self.edit(event)
        self.eventcount += 1

    def selectable(self):
        return bool(self.eventcount)


class RecursionEditor(urwid.WidgetWrap):

    def __init__(self, rrule):
        # TODO: actually implement the Recursion Editor

        self.rrule = rrule
        recursive = self.rrule['freq'][0].lower() if self.rrule else NOREPEAT
        self.recursion_choice = Choice(
            [NOREPEAT, u"weekly", u"monthly", u"yearly"], recursive)
        self.columns = urwid.Columns([(10, urwid.Text(u'Repeat: ')), (11, self.recursion_choice)])
        urwid.WidgetWrap.__init__(self, self.columns)

    @property
    def changed(self):
        if self.recursion_choice.changed:
            return True
        return False

    @property
    def active(self):
        recursive = self.recursion_choice.active
        if recursive != NOREPEAT:
            self.rrule["freq"] = [recursive]
            return self.rrule
        return None

    @active.setter
    def active(self, val):
        self.recursion_choice.active = val


class EventDisplay(urwid.WidgetWrap):

    """showing events

    widget for displaying one event's details
    """

    def __init__(self, conf, event, collection=None):
        self.conf = conf
        self.collection = collection
        self.event = event
        divider = urwid.Divider(u' ')

        lines = []
        lines.append(urwid.Text(u'Title: ' + event.summary))

        # show organizer
        if event.organizer != u'':
            lines.append(urwid.Text(u'Organizer: ' + event.organizer))

        if event.location != u'':
            lines.append(urwid.Text(u'Location: ' + event.location))

        # start and end time/date
        if event.allday:
            startstr = event.start_local.strftime(self.conf['locale']['dateformat'])
            endstr = event.end_local.strftime(self.conf['locale']['dateformat'])
        else:
            startstr = event.start_local.strftime(
                u'{} {}'.format(self.conf['locale']['dateformat'],
                                self.conf['locale']['timeformat'])
            )
            if event.start_local.date == event.end_local.date:
                endstr = event.end_local.strftime(self.conf['locale']['timeformat'])
            else:
                endstr = event.end_local.strftime(
                    u'{} {}'.format(self.conf['locale']['dateformat'],
                                    self.conf['locale']['timeformat'])
                )

        if startstr == endstr:
            lines.append(urwid.Text(u'Date: ' + startstr))
        else:
            lines.append(urwid.Text(u'Date: ' + startstr + u' - ' + endstr))

        lines.append(urwid.Text(u'Calendar: ' + event.calendar))
        lines.append(divider)

        if event.description != u'':
            lines.append(urwid.Text(event.description))

        pile = urwid.Pile(lines)
        urwid.WidgetWrap.__init__(self, urwid.Filler(pile, valign='top'))


class EventEditor(urwid.WidgetWrap):

    """
    Widget for event Editing
    """

    def __init__(self, pane, event):
        """
        :type event: khal.event.Event
        """

        self.pane = pane
        self.event = event

        self.collection = pane.collection
        self.conf = pane.conf

        self._abort_confirmed = False

        self.description = event.description
        self.location = event.location

        self.startendeditor = StartEndEditor(
            event.start_local, event.end_local, self.conf,
            self.pane.eventscolumn.original_widget.set_current_date)
        self.recursioneditor = RecursionEditor(self.event.recurobject)
        self.summary = Edit(caption=u'Title: ', edit_text=event.summary)

        divider = urwid.Divider(' ')

        # TODO warning message if len(self.collection.writable_names) == 0
        def decorate_choice(c):
            return (c.color or u'', c.name)

        self.calendar_chooser = Choice(
            [c for c in self.collection.calendars if not c.readonly],
            self.collection._calnames[self.event.calendar],
            decorate_choice
        )
        self.description = Edit(caption=u'Description: ',
                                edit_text=self.description, multiline=True)
        self.location = Edit(caption=u'Location: ',
                             edit_text=self.location)
        self.pile = urwid.ListBox(urwid.SimpleFocusListWalker([
            urwid.Columns([self.summary, self.calendar_chooser], dividechars=2),
            divider,
            self.location,
            self.description,
            divider,
            self.startendeditor,
            self.recursioneditor,
            divider,
            urwid.Button(u'Save', on_press=self.save)
        ]))

        urwid.WidgetWrap.__init__(self, self.pile)

    @property
    def title(self):  # Window title
        return u'Edit: {}'.format(self.summary.get_edit_text())

    def get_keys(self):
        return [(['arrowsu'], u'navigate through properties'),
                (['enter'], u'edit property'),
                (['esc'], u'abort')]

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
        if self.startendeditor.changed or self.calendar_chooser.changed:
            return True
        if self.recursioneditor.changed:
            return True
        return False

    def update_vevent(self):
        self.event.update_summary(self.summary.get_edit_text())
        self.event.update_description(self.description.get_edit_text())
        self.event.update_location(self.location.get_edit_text())

        if self.startendeditor.changed:
            self.event.update_start_end(self.startendeditor.newstart,
                                        self.startendeditor.newend)
        if self.recursioneditor.changed:
            rrule = self.recursioneditor.active
            self.event.update_rrule(rrule)

            # self.event.vevent.pop("RRULE")
            # if rrule and rrule["freq"][0] != NOREPEAT:
            #    self.event.vevent.add("RRULE", rrule)
        # TODO self.newaccount = self.calendar_chooser.active ?

    def save(self, button):
        """
        saves the event to the db (only when it has been changed)
        :param button: not needed, passed via the button press
        """
        # need to call this to set date backgrounds to False
        changed = self.changed
        if 'alert' in [self.startendeditor.bgs.startdate,
                       self.startendeditor.bgs.starttime,
                       self.startendeditor.bgs.enddate,
                       self.startendeditor.bgs.endtime]:
            # toggle also updates the background, therefore we toggle the state
            # to the current state, thus only updating the background colors
            # finally we set the focus to the element containing the
            # StartEndEditor
            self.startendeditor.toggle(None, state=self.startendeditor.allday)
            for num, element in enumerate(self.pile.body):
                if isinstance(element, StartEndEditor):
                    self.pile.set_focus(num)
                    self.startendeditor.toggle(None, state=self.startendeditor.allday)
                    break
            return
        else:
            self.update_vevent()

        if changed is True:
            self.event.allday = self.startendeditor.allday
            self.event.increment_sequence()
            if self.event.etag is None:  # has not been saved before
                self.event.calendar = self.calendar_chooser.active.name
                self.collection.new(self.event)
            elif self.calendar_chooser.changed:
                self.collection.change_collection(
                    self.event,
                    self.calendar_chooser.active.name
                )
            else:
                self.collection.update(self.event)

        self._abort_confirmed = False
        self.pane.window.backtrack()

    def keypress(self, size, key):
        if key in ['esc'] and self.changed and not self._abort_confirmed:
            # TODO Use user-defined keybindings
            self.pane.window.alert(
                ('light red',
                 'Unsaved changes! Hit ESC again to discard.'))
            self._abort_confirmed = True
            return
        if key in self.pane.conf['keybindings']['save']:
            self.save(None)
        return super(EventEditor, self).keypress(size, key)


class DeleteDialog(urwid.WidgetWrap):
    def __init__(self, this_func, all_func, abort_func):
        lines = []
        lines.append(urwid.Text(u'This is a recurring event.'))
        lines.append(urwid.Text(u'Which instances do you want to delete?'))
        lines.append(urwid.Text(u''))
        buttons = urwid.Columns(
            [urwid.Button(u'Only this', on_press=this_func),
             urwid.Button(u'All (past and future)', on_press=all_func),
             urwid.Button(u'Abort', on_press=abort_func),
             ])
        lines.append(buttons)
        content = urwid.Pile(lines)
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

        ContainerWidget = urwid.LineBox if self.conf['view']['frame'] else urwid.WidgetPlaceholder
        self.eventscolumn = ContainerWidget(EventColumn(pane=self))
        calendar = CalendarWidget(
            on_date_change=self.show_date,
            keybindings=self.conf['keybindings'],
            on_press={'n': self.new_event},
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
                (['q', 'esc'], 'previous pane/quit'),
                ]

    def show_date(self, date):
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


def start_pane(pane, callback, program_info=''):
    """Open the user interface with the given initial pane."""
    frame = Window(footer=program_info + ' | q: quit, ?: help')
    frame.open(pane, callback)
    loop = urwid.MainLoop(frame, getattr(colors, pane.conf['view']['theme']),
                          unhandled_input=frame.on_key_press,
                          pop_ups=True)

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
