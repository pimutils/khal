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

"""A collection of (reusable) urwid widgets

Widgets that are specific to calendaring/khal should go into __init__.py or,
if they are large, into their own files
"""
import datetime as dt
import re
from typing import Optional

import urwid

from .calendarwidget import CalendarWidget  # noqa


class DateConversionError(Exception):
    pass


def delete_last_word(text, number=1):
    """delete last `number` of words from text"""
    words = re.findall(r"[\w]+|[^\w\s]", text, re.UNICODE)
    for one in range(1, number + 1):
        text = text.rstrip()
        if text == '':
            return text
        text = text[:len(text) - len(words[-one])]
    return text


def delete_till_beginning_of_line(text):
    """delete till beginning of line"""
    if text.rfind("\n") == -1:
        return ''
    return text[0:text.rfind("\n") + 1]


def delete_till_end_of_line(text):
    """delete till beginning of line"""
    if text.find("\n") == -1:
        return ''
    return text[text.find("\n"):]


def goto_beginning_of_line(text):
    if text.rfind("\n") == -1:
        return 0
    return text.rfind("\n") + 1


def goto_end_of_line(text):
    if text.find("\n") == -1:
        return len(text)
    return text.find("\n")


class ExtendedEdit(urwid.Edit):
    """A text editing widget supporting some more editing commands"""

    def keypress(self, size: tuple[int], key: Optional[str]) -> Optional[str]:
        if key == 'ctrl w':
            self._delete_word()
        elif key == 'ctrl u':
            self._delete_till_beginning_of_line()
        elif key == 'ctrl k':
            self._delete_till_end_of_line()
        elif key == 'ctrl a':
            self._goto_beginning_of_line()
        elif key == 'ctrl e':
            self._goto_end_of_line()
        else:
            return super().keypress(size, key)

        return None

    def _delete_word(self):
        """delete word before cursor"""
        text = self.get_edit_text()
        f_text = delete_last_word(text[:self.edit_pos])
        self.set_edit_text(f_text + text[self.edit_pos:])
        self.set_edit_pos(len(f_text))

    def _delete_till_beginning_of_line(self):
        """delete till start of line before cursor"""
        text = self.get_edit_text()
        f_text = delete_till_beginning_of_line(text[:self.edit_pos])
        self.set_edit_text(f_text + text[self.edit_pos:])
        self.set_edit_pos(len(f_text))

    def _delete_till_end_of_line(self):
        """delete till end of line before cursor"""
        text = self.get_edit_text()
        f_text = delete_till_end_of_line(text[self.edit_pos:])
        self.set_edit_text(text[:self.edit_pos] + f_text)

    def _goto_beginning_of_line(self):
        text = self.get_edit_text()
        self.set_edit_pos(goto_beginning_of_line(text[:self.edit_pos]))

    def _goto_end_of_line(self):
        text = self.get_edit_text()
        self.set_edit_pos(goto_end_of_line(text[self.edit_pos:]) + self.edit_pos)


class DateTimeWidget(ExtendedEdit):

    def __init__(self, dateformat: str, on_date_change=lambda x: None, **kwargs) -> None:
        self.dateformat = dateformat
        self.on_date_change = on_date_change
        super().__init__(wrap='any', **kwargs)

    def keypress(self, size, key):
        if key == 'ctrl x':
            self.decrease()
            return None
        elif key == 'ctrl a':
            self.increase()
            return None

        if (
                key in ['up', 'down', 'tab', 'shift tab',
                    'page up', 'page down', 'meta enter'] or
                (key in ['right'] and self.edit_pos >= len(self.edit_text)) or
                (key in ['left'] and self.edit_pos == 0)):
            # when leaving the current Widget we check if currently
            # entered value is valid and if so pass the new value
            try:
                new_date = self._get_current_value()
            except DateConversionError:
                pass
            else:
                self.on_date_change(new_date)
        return super().keypress(size, key)

    def increase(self):
        """call to increase the datefield by self.timedelta"""
        self._crease(self.dtype.__add__)

    def decrease(self):
        """call to decrease the datefield by self.timedelta"""
        self._crease(self.dtype.__sub__)

    def _crease(self, fun):
        """common implementation for `self.increase` and `self.decrease`"""
        try:
            new_date = fun(self._get_current_value(), self.timedelta)
            self.on_date_change(new_date)
            self.set_edit_text(new_date.strftime(self.dateformat))
        except DateConversionError:
            pass

    def set_value(self, new_date: dt.date):
        """set a new value for this widget"""
        self.set_edit_text(new_date.strftime(self.dateformat))


class DateWidget(DateTimeWidget):
    dtype = dt.date
    timedelta = dt.timedelta(days=1)

    def _get_current_value(self):
        try:
            new_date = dt.datetime.strptime(self.get_edit_text(), self.dateformat).date()
        except ValueError:
            raise DateConversionError
        else:
            return new_date


class TimeWidget(DateTimeWidget):
    dtype = dt.datetime
    timedelta = dt.timedelta(minutes=15)

    def _get_current_value(self):
        try:
            new_datetime = dt.datetime.strptime(self.get_edit_text(), self.dateformat)
        except ValueError:
            raise DateConversionError
        else:
            return new_datetime


class Choice(urwid.PopUpLauncher):
    def __init__(
        self, choices: list[str], active: str,
        decorate_func=None, overlay_width: int=32, callback=lambda: None,
    ) -> None:
        self.choices = choices
        self._callback = callback
        self._decorate = decorate_func or (lambda x: x)
        self._overlay_width = overlay_width
        self.active = self._original = active

    def create_pop_up(self):
        pop_up = ChoiceList(self, callback=self._callback)
        urwid.connect_signal(pop_up, 'close', lambda button: self.close_pop_up())
        return pop_up

    def get_pop_up_parameters(self):
        return {'left': 0,
                'top': 1,
                'overlay_width': self._overlay_width,
                'overlay_height': len(self.choices)}

    @property
    def changed(self):
        return self._active != self._original

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, val):
        self._active = val
        self.button = urwid.Button(self._decorate(self._active))
        urwid.PopUpLauncher.__init__(self, self.button)
        urwid.connect_signal(self.button, 'click', lambda button: self.open_pop_up())


class ChoiceList(urwid.WidgetWrap):
    """A pile of Button() widgets, intended to be used with Choice()"""
    signals = ['close']

    def __init__(self, parent, callback=lambda: None) -> None:
        self.parent = parent
        self._callback = callback
        buttons = []
        for c in parent.choices:
            buttons.append(
                button(
                    parent._decorate(c),
                    attr_map='popupbg',
                    focus_map='popupbg focus',
                    on_press=self.set_choice,
                    user_data=c,
                )
            )

        pile = NPile(buttons, outermost=True)
        num = [num for num, elem in enumerate(parent.choices) if elem == parent.active][0]
        pile.focus_position = num
        fill = urwid.Filler(pile)
        urwid.WidgetWrap.__init__(self, urwid.AttrMap(fill, 'popupbg'))

    def set_choice(self, button, account):
        self.parent.active = account
        self._callback()
        self._emit("close")


class SupportsNext:
    """classes inheriting from SupportsNext must implement the following methods:
    _select_first_selectable
    _select_last_selectable
    """

    def __init__(self, *args, **kwargs) -> None:
        self.outermost = kwargs.get('outermost', False)
        if 'outermost' in kwargs:
            kwargs.pop('outermost')
        super().__init__(*args, **kwargs)


class NextMixin(SupportsNext):
    """Implements SupportsNext for urwid.Pile and urwid.Columns"""

    def _select_first_selectable(self):
        """select our first selectable item (recursivly if that item SupportsNext)"""
        i = self._first_selectable()
        self.focus_position = i
        if isinstance(self.contents[i][0], SupportsNext):
            self.contents[i][0]._select_first_selectable()

    def _select_last_selectable(self):
        """select our last selectable item (recursivly if that item SupportsNext)"""
        i = self._last_selectable()
        self.focus_position = i
        if isinstance(self._contents[i][0], SupportsNext):
            self.contents[i][0]._select_last_selectable()

    def _first_selectable(self):
        """return sequence number of self.contents last selectable item"""
        for j in range(0, len(self._contents)):
            if self._contents[j][0].selectable():
                return j
        return False

    def _last_selectable(self):
        """return sequence number of self._contents last selectable item"""
        for j in range(len(self._contents) - 1, - 1, - 1):
            if self._contents[j][0].selectable():
                return j
        return False

    def keypress(self, size, key):
        key = super().keypress(size, key)

        if key == 'tab':
            if self.outermost and self.focus_position == self._last_selectable():
                self._select_first_selectable()
            else:
                for i in range(self.focus_position + 1, len(self._contents)):
                    if self._contents[i][0].selectable():
                        self.focus_position = i
                        if isinstance(self._contents[i][0], SupportsNext):
                            self._contents[i][0]._select_first_selectable()
                        break
                else:  # no break
                    return key
        elif key == 'shift tab':
            if self.outermost and self.focus_position == self._first_selectable():
                self._select_last_selectable()
            else:
                for i in range(self.focus_position - 1, 0 - 1, -1):
                    if self._contents[i][0].selectable():
                        self.focus_position = i
                        if isinstance(self._contents[i][0], SupportsNext):
                            self._contents[i][0]._select_last_selectable()
                        break
                else:  # no break
                    return key
        else:
            return key


class NPile(NextMixin, urwid.Pile):
    pass


class NColumns(NextMixin, urwid.Columns):
    pass


class NListBox(SupportsNext, urwid.ListBox):
    def _select_first_selectable(self):
        """select our first selectable item (recursivly if that item SupportsNext)"""
        i = self._first_selectable()
        self.focus_position = i
        if isinstance(self.body[i], SupportsNext):
            self.body[i]._select_first_selectable()

    def _select_last_selectable(self):
        """select our last selectable item (recursivly if that item SupportsNext)"""
        i = self._last_selectable()
        self.focus_position = i
        if isinstance(self.body[i], SupportsNext):
            self.body[i]._select_last_selectable()

    def _first_selectable(self):
        """return sequence number of self._contents last selectable item"""
        for j in range(0, len(self.body)):
            if self.body[j].selectable():
                return j
        return False

    def _last_selectable(self):
        """return sequence number of self.contents last selectable item"""
        for j in range(len(self.body) - 1, - 1, - 1):
            if self.body[j].selectable():
                return j
        return False

    def keypress(self, size, key):
        key = super().keypress(size, key)
        if key == 'tab':
            if self.outermost and self.focus_position == self._last_selectable():
                self._select_first_selectable()
            else:
                self._keypress_down(size)
        elif key == 'shift tab':
            if self.outermost and self.focus_position == self._first_selectable():
                self._select_last_selectable()
            else:
                self._keypress_up(size)
        else:
            return key


class ValidatedEdit(urwid.WidgetWrap):
    def __init__(self, *args, EditWidget=ExtendedEdit, validate=False, **kwargs) -> None:
        assert validate
        self._validate_func = validate
        self._original_widget = urwid.AttrMap(EditWidget(*args, **kwargs), 'edit', 'edit focused')
        super().__init__(self._original_widget)

    @property
    def _get_base_widget(self):
        return self._original_widget

    @property
    def base_widget(self):
        return self._original_widget.original_widget

    def _validate(self):
        text = self.base_widget.get_edit_text()
        if self._validate_func(text):
            self._original_widget.set_attr_map({None: 'edit'})
            self._original_widget.set_focus_map({None: 'edit'})
            return True
        else:
            self._original_widget.set_attr_map({None: 'alert'})
            self._original_widget.set_focus_map({None: 'alert'})
            return False

    def get_edit_text(self):
        self._validate()
        return self.base_widget.get_edit_text()

    @property
    def edit_pos(self):
        return self.base_widget.edit_pos

    @property
    def edit_text(self):
        return self.base_widget.edit_text

    def keypress(self, size, key):
        if (
                key in ['up', 'down', 'tab', 'shift tab',
                    'page up', 'page down', 'meta enter'] or
                (key in ['right'] and self.edit_pos >= len(self.edit_text)) or
                (key in ['left'] and self.edit_pos == 0)):
            if not self._validate():
                return
        return super().keypress(size, key)


class PositiveIntEdit(ValidatedEdit):
    def __init__(self, *args, EditWidget=ExtendedEdit, validate=False, **kwargs) -> None:
        """Variant of Validated Edit that only accepts positive integers."""
        super().__init__(*args, validate=self._unsigned_int, **kwargs)

    @staticmethod
    def _unsigned_int(number):
        """test if `number` can be converted to a positive int"""
        try:
            return int(number) >= 0
        except ValueError:
            return False


class DurationWidget(urwid.WidgetWrap):

    @staticmethod
    def unsigned_int(number):
        """test if `number` can be converted to a positive int"""
        try:
            return int(number) >= 0
        except ValueError:
            return False

    @staticmethod
    def _convert_timedelta(dt):
        seconds = dt.total_seconds()
        days = int(seconds // (24 * 60 * 60))
        hours = int((seconds // 3600) % 24)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return days, hours, minutes, seconds

    def __init__(self, timedelta: dt.timedelta) -> None:
        days, hours, minutes, seconds = self._convert_timedelta(timedelta)

        self.days_edit = ValidatedEdit(
            edit_text=str(days), validate=self.unsigned_int, align='right')
        self.hours_edit = ValidatedEdit(
            edit_text=str(hours), validate=self.unsigned_int, align='right')
        self.minutes_edit = ValidatedEdit(
            edit_text=str(minutes), validate=self.unsigned_int, align='right')
        self.seconds_edit = ValidatedEdit(
            edit_text=str(seconds), validate=self.unsigned_int, align='right')

        self.columns = NColumns([
            (4, self.days_edit),
            (2, urwid.Text('D')),
            (3, self.hours_edit),
            (2, urwid.Text('H')),
            (3, self.minutes_edit),
            (2, urwid.Text('M')),
            (3, self.seconds_edit),
            (2, urwid.Text('S')),
        ])

        urwid.WidgetWrap.__init__(self, self.columns)

    def get_timedelta(self) -> dt.timedelta:
        return dt.timedelta(
            seconds=int(self.seconds_edit.get_edit_text()) +
            int(self.minutes_edit.get_edit_text()) * 60 +
            int(self.hours_edit.get_edit_text()) * 60 * 60 +
            int(self.days_edit.get_edit_text()) * 24 * 60 * 60)


class AlarmsEditor(urwid.WidgetWrap):

    class AlarmEditor(urwid.WidgetWrap):

        def __init__(self, alarm: tuple[dt.timedelta, str], delete_handler) -> None:
            duration, description = alarm
            if duration.total_seconds() > 0:
                direction = 'after'
            else:
                direction = 'before'
                duration = -1 * duration

            self.duration = DurationWidget(duration)
            self.description = ExtendedEdit(
                edit_text=description if description is not None else "")
            self.direction = Choice(
                ['before', 'after'], active=direction, overlay_width=10)
            self.columns = NColumns([
                (2, urwid.Text('  ')),
                (21, self.duration),
                (14, urwid.Padding(self.direction, right=1)),
                self.description,
                (10, button('Delete', on_press=delete_handler, user_data=self)),
            ])

            urwid.WidgetWrap.__init__(self, self.columns)

        def get_alarm(self):
            direction = self.direction.active
            if direction == 'before':
                prefix = -1
            else:
                prefix = 1
            return (prefix * self.duration.get_timedelta(), self.description.get_edit_text())

    def __init__(self, event) -> None:
        self.event = event

        self.pile = NPile(
            [urwid.Text('Alarms:')] +
            [self.AlarmEditor(a, self.remove_alarm) for a in event.alarms] +
            [urwid.Columns([(12, button('Add', on_press=self.add_alarm))])])

        urwid.WidgetWrap.__init__(self, self.pile)


    def clear(self) -> None:
        """clear the alarm list"""
        self.pile.contents.clear()

    def add_alarm(self, button, timedelta: Optional[dt.timedelta] = None):
        if timedelta is None:
            timedelta = dt.timedelta(0)
        self.pile.contents.insert(
            len(self.pile.contents) - 1,
            (self.AlarmEditor((timedelta, self.event.summary), self.remove_alarm),
             ('weight', 1)))

    def remove_alarm(self, button, editor):
        self.pile.contents.remove((editor, ('weight', 1)))

    def get_alarms(self):
        alarms = []
        for widget, _ in self.pile.contents:
            if isinstance(widget, self.AlarmEditor):
                alarms.append(widget.get_alarm())
        return alarms

    @property
    def changed(self):
        try:
            return self.event.alarms != self.get_alarms()
        except ValueError:
            return False


class FocusLineBoxWidth(urwid.WidgetDecoration, urwid.WidgetWrap):
    def __init__(self, widget) -> None:
        # we cheat here with the attrs, if we use thick dividers we apply the
        # focus attr group. We probably should fix this in render()
        hline = urwid.AttrMap(urwid.Divider('─'), 'frame')
        hline_focus = urwid.AttrMap(urwid.Divider('━'), 'frame focus')
        self._vline = urwid.AttrMap(urwid.SolidFill('│'), 'frame')
        self._vline_focus = urwid.AttrMap(urwid.SolidFill('┃'), 'frame focus')
        self._topline = urwid.Columns([
            ('fixed', 1, urwid.AttrMap(urwid.Text('┌'), 'frame')),
            hline,
            ('fixed', 1, urwid.AttrMap(urwid.Text('┐'), 'frame')),
        ])
        self._topline_focus = urwid.Columns([
            ('fixed', 1, urwid.AttrMap(urwid.Text('┏'), 'frame focus')),
            hline_focus,
            ('fixed', 1, urwid.AttrMap(urwid.Text('┓'), 'frame focus')),
        ])
        self._bottomline = urwid.Columns([
            ('fixed', 1, urwid.AttrMap(urwid.Text('└'), 'frame')),
            hline,
            ('fixed', 1, urwid.AttrMap(urwid.Text('┘'), 'frame')),
        ])
        self._bottomline_focus = urwid.Columns([
            ('fixed', 1, urwid.AttrMap(urwid.Text('┗'), 'frame focus')),
            hline_focus,
            ('fixed', 1, urwid.AttrMap(urwid.Text('┛'), 'frame focus')),
        ])
        self._middle = urwid.Columns(
            [('fixed', 1, self._vline), widget, ('fixed', 1, self._vline)],
            focus_column=1,
        )
        self._all = urwid.Pile(
            [('flow', self._topline), self._middle, ('flow', self._bottomline)],
            focus_item=1,
        )

        urwid.WidgetDecoration.__init__(self, widget)
        urwid.WidgetWrap.__init__(self, self._all)

    def render(self, size, focus):
        inner = self._all.contents[1][0]
        if focus:
            self._all.contents[0] = (self._topline_focus, ('pack', None))
            inner.contents[0] = (self._vline_focus, ('given', 1, False))
            inner.contents[2] = (self._vline_focus, ('given', 1, False))
            self._all.contents[2] = (self._bottomline_focus, ('pack', None))
        else:
            self._all.contents[0] = (self._topline, ('pack', None))
            inner.contents[0] = (self._vline, ('given', 1, False))
            inner.contents[2] = (self._vline, ('given', 1, False))
            self._all.contents[2] = (self._bottomline, ('pack', None))
        return super().render(size, focus)


class FocusLineBoxColor(urwid.WidgetDecoration, urwid.WidgetWrap):
    def __init__(self, widget) -> None:
        hline = urwid.Divider('─')
        self._vline = urwid.AttrMap(urwid.SolidFill('│'), 'frame')
        self._topline = urwid.AttrMap(
            urwid.Columns([
                ('fixed', 1, urwid.Text('┌')),
                hline,
                ('fixed', 1, urwid.Text('┐')),
            ]),
            'frame')
        self._bottomline = urwid.AttrMap(
            urwid.Columns([
                ('fixed', 1, urwid.Text('└')),
                hline,
                ('fixed', 1, urwid.Text('┘')),
            ]),
            'frame')

        self._middle = urwid.Columns(
            [('fixed', 1, self._vline), widget, ('fixed', 1, self._vline)],
            focus_column=1,
        )
        self._all = urwid.Pile(
            [('flow', self._topline), self._middle, ('flow', self._bottomline)],
            focus_item=1,
        )

        urwid.WidgetWrap.__init__(self, self._all)
        urwid.WidgetDecoration.__init__(self, widget)

    def render(self, size, focus):
        if focus:
            self._middle.contents[0][0].set_attr_map({None: 'frame focus color'})
            self._all.contents[0][0].set_attr_map({None: 'frame focus color'})
            self._all.contents[2][0].set_attr_map({None: 'frame focus color'})
        else:
            self._middle.contents[0][0].set_attr_map({None: 'frame'})
            self._all.contents[0][0].set_attr_map({None: 'frame'})
            self._all.contents[2][0].set_attr_map({None: 'frame'})
        return super().render(size, focus)


class FocusLineBoxTop(urwid.WidgetDecoration, urwid.WidgetWrap):
    def __init__(self, widget) -> None:
        topline = urwid.AttrMap(urwid.Divider('━'), 'frame')
        self._all = urwid.Pile([('flow', topline), widget], focus_item=1)
        urwid.WidgetWrap.__init__(self, self._all)
        urwid.WidgetDecoration.__init__(self, widget)

    def render(self, size, focus):
        if focus:
            self._all.contents[0][0].set_attr_map({None: 'frame focus top'})
        else:
            self._all.contents[0][0].set_attr_map({None: 'frame'})
        return super().render(size, focus)


linebox = {
    'color': FocusLineBoxColor,
    'top': FocusLineBoxTop,
    'width': FocusLineBoxWidth,
    'False': urwid.WidgetPlaceholder,
}

def button(*args,
           attr_map: str='button', focus_map='button focus',
           padding_left=0, padding_right=0,
           **kwargs):
    """wrapping an urwid button in attrmap and padding"""
    button_ = urwid.Button(*args, **kwargs)
    button_ = urwid.AttrMap(button_, attr_map=attr_map, focus_map=focus_map)
    button_ = urwid.Padding(button_, left=padding_left, right=padding_right)
    return button_


class CAttrMap(urwid.AttrMap):
    """A variant of AttrMap that exposes all properties of the original widget"""
    def __getattr__(self, name):
        return getattr(self.original_widget, name)


class CPadding(urwid.Padding):
    """A variant of Patting that exposes some properties of the original widget"""
    @property
    def active(self):
        return self.original_widget.active

    @property
    def changed(self):
        return self.original_widget.changed
