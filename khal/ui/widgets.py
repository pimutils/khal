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
import typing
import weakref
from collections.abc import Callable
from dataclasses import dataclass

import urwid

# the size urwid passes to render(), keypress() and friends: () for fixed,
# (maxcol,) for flow and (maxcol, maxrow) for box widgets
Size = tuple[()] | tuple[int] | tuple[int, int]
# the size of a ListBox (flow or box)
ListBoxSize = tuple[int] | tuple[int, int]


class FlowWidget(typing.Protocol):
    """a widget that can be rendered with a (maxcol,) size"""

    def rows(self, size: tuple[int], focus: bool = False) -> int: ...


class DateConversionError(Exception):
    pass


def delete_last_word(text, number=1):
    """delete last `number` of words from text"""
    words = re.findall(r"[\w]+|[^\w\s]", text, re.UNICODE)
    for one in range(1, number + 1):
        text = text.rstrip()
        if text == "":
            return text
        text = text[: len(text) - len(words[-one])]
    return text


def delete_till_beginning_of_line(text):
    """delete till beginning of line"""
    if text.rfind("\n") == -1:
        return ""
    return text[0 : text.rfind("\n") + 1]


def delete_till_end_of_line(text):
    """delete till beginning of line"""
    if text.find("\n") == -1:
        return ""
    return text[text.find("\n") :]


def goto_beginning_of_line(text):
    if text.rfind("\n") == -1:
        return 0
    return text.rfind("\n") + 1


def goto_end_of_line(text):
    if text.find("\n") == -1:
        return len(text)
    return text.find("\n")


def markup_text(markup) -> str:
    """the text of urwid markup (urwid also allows bytes)"""
    text = urwid.decompose_tagmarkup(markup)[0]
    return text.decode() if isinstance(text, bytes) else text


class ExtendedEdit(urwid.Edit):
    """A text editing widget supporting some more editing commands"""

    def keypress(self, size: tuple[int], key: str) -> str | None:  # type: ignore[override]  # urwid.Edit narrows the size, too
        if key == "ctrl w":
            self._delete_word()
        elif key == "ctrl u":
            self._delete_till_beginning_of_line()
        elif key == "ctrl k":
            self._delete_till_end_of_line()
        elif key == "ctrl a":
            self._goto_beginning_of_line()
        elif key == "ctrl e":
            self._goto_end_of_line()
        else:
            return super().keypress(size, key)

        return None

    def _delete_word(self):
        """delete word before cursor"""
        text = self.get_edit_text()
        f_text = delete_last_word(text[: self.edit_pos])
        self.set_edit_text(f_text + text[self.edit_pos :])
        self.set_edit_pos(len(f_text))

    def _delete_till_beginning_of_line(self):
        """delete till start of line before cursor"""
        text = self.get_edit_text()
        f_text = delete_till_beginning_of_line(text[: self.edit_pos])
        self.set_edit_text(f_text + text[self.edit_pos :])
        self.set_edit_pos(len(f_text))

    def _delete_till_end_of_line(self):
        """delete till end of line before cursor"""
        text = self.get_edit_text()
        f_text = delete_till_end_of_line(text[self.edit_pos :])
        self.set_edit_text(text[: self.edit_pos] + f_text)

    def _goto_beginning_of_line(self):
        text = self.get_edit_text()
        self.set_edit_pos(goto_beginning_of_line(text[: self.edit_pos]))

    def _goto_end_of_line(self):
        text = self.get_edit_text()
        self.set_edit_pos(goto_end_of_line(text[self.edit_pos :]) + self.edit_pos)


class DateTimeWidget(ExtendedEdit):
    def __init__(self, dateformat: str, on_date_change=lambda x: None, **kwargs) -> None:
        self.dateformat = dateformat
        self.on_date_change = on_date_change
        super().__init__(wrap="any", **kwargs)

    def keypress(self, size, key):
        if key == "ctrl x":
            self.decrease()
            return None
        elif key == "ctrl a":
            self.increase()
            return None

        if (
            key in ["up", "down", "tab", "shift tab", "page up", "page down", "meta enter"]
            or (key in ["right"] and self.edit_pos >= len(self.edit_text))
            or (key in ["left"] and self.edit_pos == 0)
        ):
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
    """a field with a value out of a list, enter opens a `ChoiceList` below it

    :param hints: dim hints for some choices in the list (choice -> text),
        e.g. what picking it means
    """

    def __init__(
        self,
        choices: list,
        active,
        decorate_func=None,
        overlay_width: int = 0,
        callback=lambda: None,
        button_factory=urwid.Button,
        hints: dict | None = None,
    ) -> None:
        self.choices = choices
        self._callback = callback
        self._button_factory = button_factory
        self._decorate = decorate_func or (lambda x: x)
        self._overlay_width = overlay_width
        self.hints = hints or {}
        self.active = self._original = active

    def create_pop_up(self):
        pop_up = ChoiceList(self, callback=self._callback)
        urwid.connect_signal(pop_up, "close", lambda button: self.close_pop_up())
        return pop_up

    def get_pop_up_parameters(self):
        pop_up = getattr(self, "_pop_up_widget", None)
        if not isinstance(pop_up, ChoiceList):
            pop_up = ChoiceList(self)
        return {
            "left": 0,
            "top": 1,
            "overlay_width": max(self._overlay_width, pop_up.width),
            "overlay_height": pop_up.height,
        }

    @property
    def changed(self):
        return self._active != self._original

    def set_button_factory(self, button_factory) -> None:
        """change how the currently active choice is displayed"""
        self._button_factory = button_factory
        self.active = self._active

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, val):
        self._active = val
        self.button = self._button_factory(self._decorate(self._active))
        urwid.PopUpLauncher.__init__(self, self.button)
        urwid.connect_signal(self.button, "click", lambda button: self.open_pop_up())


def calendar_mark(attr: str) -> str:
    """`calendar <name> popup` -> `calendar <name> mark`: a calendar's dot in
    its colour as foreground, whatever `[highlight_days] method` says"""
    if attr.startswith("calendar ") and attr.endswith(" popup"):
        return attr.removesuffix(" popup") + " mark"
    return attr


def calendar_row(attr: str) -> str:
    """the focused-row version of a `calendar <name> mark` attribute"""
    return attr.removesuffix(" mark") + " row"


def _plain_markup(markup) -> list:
    """the label markup of a choice for the list: calendar dots in their
    colours on the list's background (not the old "... popup" fill)"""
    if not isinstance(markup, list):
        markup = [markup]
    out: list = []
    for part in markup:
        if isinstance(part, tuple) and isinstance(part[0], str):
            out.append((calendar_mark(part[0]), part[1]))
        else:
            out.append(part)
    return out


class ChoiceRow(urwid.WidgetWrap):
    """one entry of a ChoiceList: `▌ ● home ✓  hint` (the ▌ while focused)"""

    def __init__(self, value, label: list, current: bool, hint: str, on_pick) -> None:
        self.value = value
        self.label = label
        self.text = urwid.decompose_tagmarkup(label)[0]
        self._on_pick = on_pick
        tail: list = []
        if current:
            tail.append(("float choice tick", " ✓"))
        if hint:
            tail.append(("float choice hint", "  " + hint))
        self._markup = [*label, *tail, " "]
        self._text = urwid.Text("", wrap="clip")
        focus_map: dict = {
            None: "float choice focus",
            "float choice": "float choice focus",
            "float choice tick": "float choice tick focus",
            "float choice hint": "float choice hint focus",
        }
        for part in label:
            if isinstance(part, tuple) and part[0].startswith("calendar "):
                focus_map[part[0]] = calendar_row(part[0])
        self._focused: bool | None = None
        super().__init__(urwid.AttrMap(self._text, "float choice", focus_map))

    @property
    def width(self) -> int:
        text = urwid.decompose_tagmarkup(self._markup)[0]
        return 2 + urwid.calc_width(text, 0, len(text))

    def selectable(self) -> bool:
        return True

    def keypress(self, size, key):
        return key

    def mouse_event(self, size, event, button, col, row, focus):
        if event == "mouse press" and button == 1:
            self._on_pick(self.value)
            return True
        return False

    def render(self, size, focus=False):
        if focus != self._focused:
            self._focused = focus
            marker = ("editor marker", "▌") if focus else " "
            self._text.set_text([marker, " ", *self._markup])
        return super().render(size, focus)


class ChoiceList(urwid.WidgetWrap):
    """the pop-up list of a Choice: an accent framed box below the field

    One row per choice, the current one ticked (✓) and focused; calendars
    with their colour dot. With `FILTER_FROM` or more choices, the first row
    is a filter: typing filters the list. ↑↓ (and j/k without a filter) move,
    enter or space picks, esc closes.
    """

    signals = ["close"]
    FILTER_FROM = 6
    # the pop-up hangs one row below the top of its field (see PopUpTarget)
    anchor_rows = 1

    def __init__(self, parent, callback=lambda: None) -> None:
        from .editor_layout import Card

        self.parent = parent
        self._callback = callback
        self._filter = ""
        self.entries = [
            ChoiceRow(
                c,
                _plain_markup(parent._decorate(c)),
                c == parent.active,
                parent.hints.get(c, "") if isinstance(c, str) else "",
                self.set_choice,
            )
            for c in parent.choices
        ]
        self._walker = urwid.SimpleFocusListWalker(list(self.entries))
        self._listbox = urwid.ListBox(self._walker)
        self._has_filter = len(self.entries) >= self.FILTER_FROM
        self._filter_text = urwid.Text("", wrap="clip")
        self._update_filter_row()
        body: urwid.Widget = self._listbox
        if self._has_filter:
            body = urwid.Pile([("pack", self._filter_text), self._listbox], focus_item=1)
        current = [i for i, row in enumerate(self.entries) if row.value == parent.active]
        if current:
            self._walker.set_focus(current[0])
        filter_width = 2 + len("type to filter") + 1 if self._has_filter else 0
        inner = max([row.width for row in self.entries] + [filter_width])
        self.width = inner + 3
        self._box = Card(
            "",
            urwid.Padding(body, left=1),
            attr="float border",
            focus_attr="float border",
        )
        super().__init__(self._box)

    @property
    def height(self) -> int:
        return max(1, len(self._walker)) + self._has_filter + 2

    def _update_filter_row(self) -> None:
        if self._filter:
            self._filter_text.set_text(
                [("float choice hint", "filter "), ("float choice", self._filter)]
            )
        else:
            self._filter_text.set_text(("float choice placeholder", "type to filter"))

    def _apply_filter(self) -> None:
        self._update_filter_row()
        needle = self._filter.lower()
        self._walker[:] = [row for row in self.entries if needle in row.text.lower()]
        if self._walker:
            self._walker.set_focus(0)

    def set_choice(self, value, *_):
        self.parent.active = value
        self._callback()
        self._emit("close")

    def keypress(self, size, key):
        if key == "esc":
            self._emit("close")
            return None
        if key in ("enter", " "):
            if self._walker:
                self.set_choice(self._walker.get_focus()[0].value)
            return None
        if self._has_filter:
            if key == "backspace":
                self._filter = self._filter[:-1]
                self._apply_filter()
                return None
            if len(key) == 1 and key.isprintable():
                self._filter += key
                self._apply_filter()
                return None
        else:
            key = {"j": "down", "k": "up"}.get(key, key)
        if key in ("up", "down", "page up", "page down", "home", "end"):
            super().keypress(size, key)
        return None


class SupportsNext:
    """classes inheriting from SupportsNext must implement the following methods:
    _select_first_selectable
    _select_last_selectable
    """

    def __init__(self, *args, **kwargs) -> None:
        self.outermost = kwargs.get("outermost", False)
        if "outermost" in kwargs:
            kwargs.pop("outermost")
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
        for j in range(len(self._contents)):
            if self._contents[j][0].selectable():
                return j
        return False

    def _last_selectable(self):
        """return sequence number of self._contents last selectable item"""
        for j in range(len(self._contents) - 1, -1, -1):
            if self._contents[j][0].selectable():
                return j
        return False

    def keypress(self, size, key):
        key = super().keypress(size, key)

        if key == "tab":
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
        elif key == "shift tab":
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
        for j in range(len(self.body)):
            if self.body[j].selectable():
                return j
        return False

    def _last_selectable(self):
        """return sequence number of self.contents last selectable item"""
        for j in range(len(self.body) - 1, -1, -1):
            if self.body[j].selectable():
                return j
        return False

    def keypress(self, size, key):
        key = super().keypress(size, key)
        if key == "tab":
            if self.outermost and self.focus_position == self._last_selectable():
                self._select_first_selectable()
            else:
                self._keypress_down(size)
        elif key == "shift tab":
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
        self._original_widget = urwid.AttrMap(
            EditWidget(*args, **kwargs), "editor field", "editor field focus"
        )
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
            self._original_widget.set_attr_map({None: "editor field"})
            self._original_widget.set_focus_map({None: "editor field focus"})
            return True
        else:
            self._original_widget.set_attr_map({None: "editor error"})
            self._original_widget.set_focus_map({None: "editor error"})
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
            key in ["up", "down", "tab", "shift tab", "page up", "page down", "meta enter"]
            or (key in ["right"] and self.edit_pos >= len(self.edit_text))
            or (key in ["left"] and self.edit_pos == 0)
        ):
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


def parse_duration(text: str) -> dt.timedelta:
    """parse `5m`, `1h30m`, `2d`, `1d 2h` (like the config) into a positive timedelta

    :raises ValueError: for anything else
    """
    from khal.parse_datetime import guesstimedeltafstr

    text = text.strip()
    if text == "0":
        return dt.timedelta(0)
    if not text:
        raise ValueError("empty duration")
    delta = guesstimedeltafstr(text)
    if delta < dt.timedelta(0):
        raise ValueError("negative duration")
    return delta


def format_duration_long(delta: dt.timedelta) -> str:
    """`1 hour 30 minutes`, `2 days`, `0 minutes`"""
    seconds = int(abs(delta).total_seconds())
    days, seconds = divmod(seconds, 24 * 60 * 60)
    hours, seconds = divmod(seconds, 60 * 60)
    minutes, seconds = divmod(seconds, 60)
    parts = [
        f"{value} {unit}{'' if value == 1 else 's'}"
        for value, unit in (
            (days, "day"),
            (hours, "hour"),
            (minutes, "minute"),
            (seconds, "second"),
        )
        if value
    ]
    return " ".join(parts) or "0 minutes"


def format_duration_short(delta: dt.timedelta) -> str:
    """`1h30m`, the syntax `parse_duration` accepts"""
    from khal.parse_datetime import timedelta2str

    return timedelta2str(delta).replace(" ", "") or "0"


class DelegateNext(SupportsNext):
    """SupportsNext for widget wrappers: forwards to the wrapped widget"""

    def _delegate_next_target(self):
        return self._w

    def _select_first_selectable(self):
        target = self._delegate_next_target()
        if isinstance(target, SupportsNext):
            target._select_first_selectable()

    def _select_last_selectable(self):
        target = self._delegate_next_target()
        if isinstance(target, SupportsNext):
            target._select_last_selectable()


class ActionButton(urwid.WidgetWrap):
    """A flat, fixed width button that is just its label

    Unlike urwid.Button it has no `< >` decoration (put brackets into the
    label if you want them) and it can be packed into Columns.
    """

    signals = ["click"]

    def __init__(
        self,
        label,
        on_press=None,
        user_data=None,
        attr: str = "editor button",
        focus_attr: str = "editor button focus",
    ) -> None:
        self._label = label
        icon = urwid.SelectableIcon(label, 0)
        super().__init__(urwid.AttrMap(icon, attr, focus_attr))
        if on_press is not None:
            urwid.connect_signal(self, "click", on_press, user_data)

    @property
    def width(self) -> int:
        text = markup_text(self._label)
        return urwid.calc_width(text, 0, len(text))

    def get_label(self) -> str:
        return markup_text(self._label)

    def keypress(self, size, key):
        if key in ("enter", " "):
            self._emit("click")
            return None
        return key

    def mouse_event(self, size, event, button, col, row, focus):
        if event == "mouse press" and button == 1:
            self._emit("click")
            return True
        return False


class PlaceholderEdit(ExtendedEdit):
    """An ExtendedEdit that shows a (dimmed) placeholder while empty and unfocused"""

    def __init__(self, *args, placeholder="", **kwargs) -> None:
        # (not `_placeholder`: urwid >= 5 Edit has an attribute of that name)
        self._hint_text = urwid.Text(placeholder, wrap="ellipsis")
        super().__init__(*args, **kwargs)

    def set_placeholder(self, markup) -> None:
        self._hint_text.set_text(markup)
        self._invalidate()

    def _show_placeholder(self, focus: bool) -> bool:
        return not focus and self.edit_text == "" and self._hint_text.text != ""

    def rows(self, size, focus=False):
        if self._show_placeholder(focus):
            return 1
        return super().rows(size, focus)

    def render(self, size, focus=False):
        if self._show_placeholder(focus):
            return self._hint_text.render(size)
        return super().render(size, focus)


class LiveText(urwid.Text):
    """A Text whose content is recomputed by `func` every time it is rendered"""

    no_cache = ["render", "rows"]  # the content changes without invalidating us

    # all live texts, see refresh_all()
    _instances: weakref.WeakSet = weakref.WeakSet()

    def __init__(self, func, **kwargs) -> None:
        self._func = func
        self._markup = self._compute()
        super().__init__(self._markup, **kwargs)
        LiveText._instances.add(self)

    @classmethod
    def refresh_all(cls) -> None:
        """recompute all live texts; those that changed invalidate their
        parents' cached canvases (which would otherwise be drawn again
        without asking the live text)"""
        for text in list(cls._instances):
            text._refresh()

    def _compute(self):
        try:
            return self._func()
        except Exception:  # never let a status line crash the UI
            return ""

    def _refresh(self) -> None:
        markup = self._compute()
        if markup != self._markup:
            self._markup = markup
            self.set_text(markup)

    def rows(self, size, focus=False):
        self._refresh()
        return super().rows(size, focus)

    def render(self, size, focus=False):
        self._refresh()
        return super().render(size, focus)


class FocusExpand(SupportsNext, urwid.WidgetWrap):
    """shows `collapsed` (a flow widget) unless focused, then `expanded`"""

    def __init__(self, collapsed: urwid.Widget, expanded: urwid.Widget) -> None:
        self._collapsed = collapsed
        urwid.WidgetWrap.__init__(self, expanded)

    def _select_first_selectable(self):
        if isinstance(self._w, SupportsNext):
            self._w._select_first_selectable()

    def _select_last_selectable(self):
        if isinstance(self._w, SupportsNext):
            self._w._select_last_selectable()

    def selectable(self) -> bool:
        return True

    def rows(self, size, focus=False):
        return (self._w if focus else self._collapsed).rows(size, focus)

    def render(self, size, focus=False):
        if focus:
            return self._w.render(size, focus)
        return self._collapsed.render(size, False)


class LiveValidatedEdit(ValidatedEdit):
    """a ValidatedEdit that shows invalid input (as `editor error`) while typing"""

    def render(self, size, focus=False):
        self._validate()
        return super().render(size, focus)

    def keypress(self, size, key):
        key = super().keypress(size, key)
        self._validate()  # apply the input now, not only on the next render
        return key

    @property
    def valid(self) -> bool:
        return bool(self._validate_func(self.base_widget.get_edit_text()))


@dataclass
class AlarmStyle:
    """how AlarmsEditor lays out its rows

    The defaults reproduce the classic look (header line, Delete button at
    the far right, Add button below).
    """

    header: str | None = "Alarms:"
    icon: str = "  "
    direction_width: int = 14
    show_description: bool = True
    # unfocused rows read "5 minutes before" (or "5m before" if not long_units)
    long_units: bool = True
    error_hint: str = "✗ e.g. 1h30m"
    delete: Callable[[Callable, object], urwid.Widget] | None = None
    add: Callable[[Callable], urwid.Widget] | None = None
    # button factory for the before/after Choice (None: urwid.Button)
    choice_button: Callable | None = None
    # wraps each alarm row (the add row gets index -1)
    row: Callable[[urwid.Widget, int], urwid.Widget] = lambda widget, index: widget

    def delete_widget(self, on_press, user_data):
        if self.delete is not None:
            return self.delete(on_press, user_data)
        return (10, button("Delete", on_press=on_press, user_data=user_data))

    def add_widget(self, on_press):
        if self.add is not None:
            return self.add(on_press)
        return urwid.Columns([(12, button("Add", on_press=on_press))])


class AlarmsEditor(DelegateNext, urwid.WidgetWrap):
    class AlarmEditor(urwid.WidgetWrap):
        """one alarm: a duration (`1h30m`), before/after and a description

        While the row is not focused it reads `1 hour 30 minutes before`.
        """

        def __init__(
            self,
            alarm: tuple[dt.timedelta, str],
            delete_handler,
            style: AlarmStyle | None = None,
        ) -> None:
            duration, description = alarm
            if duration.total_seconds() > 0:
                direction = "after"
            else:
                direction = "before"
                duration = -1 * duration

            self._delete_handler = delete_handler
            self.duration = LiveValidatedEdit(
                edit_text=format_duration_short(duration), validate=self._valid_duration
            )
            self.description = ExtendedEdit(
                caption=("editor label", "text: "),
                edit_text=description if description is not None else "",
            )
            self.direction = Choice(["before", "after"], active=direction, overlay_width=10)
            self.restyle(style or AlarmStyle())

        @staticmethod
        def _valid_duration(text: str) -> bool:
            try:
                parse_duration(text)
            except ValueError:
                return False
            return True

        def summary(self) -> str:
            try:
                delta = parse_duration(self.duration.get_edit_text())
            except ValueError:
                return self.duration.get_edit_text()
            if self._style.long_units:
                return f"{format_duration_long(delta)} {self.direction.active}"
            return f"{format_duration_short(delta)} {self.direction.active}"

        def restyle(self, style: AlarmStyle) -> None:
            self._style = style
            self.direction.set_button_factory(style.choice_button or urwid.Button)
            fields = NColumns(
                [
                    (8, self.duration),
                    (style.direction_width, urwid.Padding(self.direction, right=1)),
                    self.description if style.show_description else urwid.Text(""),
                ],
                dividechars=1,
                focus_column=0,
            )
            collapsed = LiveText(lambda: ("editor field", self.summary()), wrap="ellipsis")
            hint = LiveText(
                lambda: "" if self.duration.valid else ("editor error hint", style.error_hint),
                align="right",
            )
            # the divider separates the icon from the text (`◔ 5 minutes`)
            icon = style.icon.rstrip() or style.icon
            columns = [
                (len(icon), urwid.Text(icon)),
                FocusExpand(collapsed, fields),
                (len(style.error_hint), hint),
                style.delete_widget(self._delete_handler, self),
            ]
            self.columns = NColumns(columns, dividechars=1, focus_column=1)
            urwid.WidgetWrap.__init__(self, self.columns)

        def get_alarm(self):
            direction = self.direction.active
            if direction == "before":
                prefix = -1
            else:
                prefix = 1
            delta = parse_duration(self.duration.get_edit_text())
            return (prefix * delta, self.description.get_edit_text())

    def __init__(self, event, style: AlarmStyle | None = None) -> None:
        self.event = event
        self._style = style or AlarmStyle()
        self._editors = [self.AlarmEditor(a, self.remove_alarm, self._style) for a in event.alarms]
        self.pile = NPile([])
        urwid.WidgetWrap.__init__(self, self.pile)
        self._refill()

    def restyle(self, style: AlarmStyle) -> None:
        self._style = style
        for editor in self._editors:
            editor.restyle(style)
        self._refill()

    def _refill(self, focus: int | None = None) -> None:
        rows: list[urwid.Widget] = []
        if self._style.header is not None:
            rows.append(urwid.Text(self._style.header))
        rows.extend(self._style.row(editor, index) for index, editor in enumerate(self._editors))
        rows.append(self._style.row(self._style.add_widget(self.add_alarm), -1))
        self.pile.contents[:] = [(row, self.pile.options("weight", 1)) for row in rows]
        offset = 0 if self._style.header is None else 1
        if focus is not None:
            self.pile.focus_position = offset + max(0, min(focus, len(self._editors)))
        else:
            self.pile.focus_position = len(rows) - 1

    @property
    def alarm_editors(self) -> list["AlarmsEditor.AlarmEditor"]:
        return list(self._editors)

    def clear(self) -> None:
        """clear the alarm list"""
        self._editors.clear()
        self._refill()

    def add_alarm(self, button, timedelta: dt.timedelta | None = None):
        if timedelta is None:
            timedelta = dt.timedelta(0)
        self._editors.append(
            self.AlarmEditor((timedelta, self.event.summary), self.remove_alarm, self._style)
        )
        self._refill(focus=len(self._editors) - 1)

    def remove_alarm(self, button, editor):
        index = self._editors.index(editor)
        self._editors.remove(editor)
        self._refill(focus=index)

    def get_alarms(self):
        return [editor.get_alarm() for editor in self._editors]

    @property
    def changed(self):
        try:
            return self.event.alarms != self.get_alarms()
        except ValueError:
            return False


class TopBorder(urwid.WidgetWrap):
    """the top line of a frame: `┌─ Title ──────── status ─┐`

    `status` is called on every render and returns markup (or nothing),
    `title` is a text or (also called on every render) a function returning one.
    """

    no_cache = ["render", "rows"]  # the status changes without invalidating us

    def __init__(
        self,
        corners: tuple[str, str],
        line: str,
        attr: str,
        title: str = "",
        status: Callable[[], list] | None = None,
        title_attr: str = "editor title",
    ) -> None:
        self._text = urwid.Text("", wrap="clip")
        self.title = title
        self._status = status
        self._title_attr = title_attr
        self.set_style(corners, line, attr)
        super().__init__(self._text)

    def set_style(self, corners: tuple[str, str], line: str, attr: str) -> None:
        self._corners, self._line, self._attr = corners, line, attr

    def render(self, size, focus=False):
        (maxcol,) = size
        left, right = self._corners
        line, attr = self._line, self._attr
        head: list = [(attr, left)]
        title = self.title() if callable(self.title) else self.title
        if title:
            head += [(attr, line), " ", (self._title_attr, title), " "]
        status = self._status() if self._status is not None else []
        tail: list = []
        if status:
            tail = [" ", *status, " ", (attr, line)]
        tail.append((attr, right))

        def width(markup):
            text = urwid.decompose_tagmarkup(markup)[0]
            return urwid.calc_width(text, 0, len(text))

        fill = maxcol - width(head) - width(tail)
        if fill < 1:  # too narrow: drop the status, then the title
            tail, fill = [(attr, right)], maxcol - width(head) - 1
            if fill < 1:
                head, fill = [(attr, left)], maxcol - 2
        self._text.set_text([*head, (attr, line * max(0, fill)), *tail])
        return super().render(size, focus)


class FocusLineBoxWidth(urwid.WidgetDecoration, urwid.WidgetWrap):
    def __init__(self, widget, title="", status=None, title_attr: str = "editor title") -> None:
        # we cheat here with the attrs, if we use thick dividers we apply the
        # focus attr group. We probably should fix this in render()
        hline = urwid.AttrMap(urwid.Divider("─"), "frame")
        hline_focus = urwid.AttrMap(urwid.Divider("━"), "frame focus")
        self._vline = urwid.AttrMap(urwid.SolidFill("│"), "frame")
        self._vline_focus = urwid.AttrMap(urwid.SolidFill("┃"), "frame focus")
        self._topline = TopBorder(("┌", "┐"), "─", "frame", title, status, title_attr)
        self._bottomline = urwid.Columns(
            [
                (1, urwid.AttrMap(urwid.Text("└"), "frame")),
                hline,
                (1, urwid.AttrMap(urwid.Text("┘"), "frame")),
            ]
        )
        self._bottomline_focus = urwid.Columns(
            [
                (1, urwid.AttrMap(urwid.Text("┗"), "frame focus")),
                hline_focus,
                (1, urwid.AttrMap(urwid.Text("┛"), "frame focus")),
            ]
        )
        self._middle = urwid.Columns(
            [(1, self._vline), widget, (1, self._vline)],
            focus_column=1,
        )
        self._all = urwid.Pile(
            [("pack", self._topline), self._middle, ("pack", self._bottomline)],
            focus_item=1,
        )

        urwid.WidgetWrap.__init__(self, self._all)
        self._original_widget = widget

    def render(self, size, focus):
        inner = self._all.contents[1][0]
        if focus:
            self._topline.set_style(("┏", "┓"), "━", "frame focus")
            inner.contents[0] = (self._vline_focus, ("given", 1, False))
            inner.contents[2] = (self._vline_focus, ("given", 1, False))
            self._all.contents[2] = (self._bottomline_focus, ("pack", None))
        else:
            self._topline.set_style(("┌", "┐"), "─", "frame")
            inner.contents[0] = (self._vline, ("given", 1, False))
            inner.contents[2] = (self._vline, ("given", 1, False))
            self._all.contents[2] = (self._bottomline, ("pack", None))
        return super().render(size, focus)


class FocusLineBoxColor(urwid.WidgetDecoration, urwid.WidgetWrap):
    def __init__(self, widget, title="", status=None, title_attr: str = "editor title") -> None:
        hline = urwid.Divider("─")
        self._vline = urwid.AttrMap(urwid.SolidFill("│"), "frame")
        self._topline = TopBorder(("╭", "╮"), "─", "frame", title, status, title_attr)
        self._bottomline = urwid.AttrMap(
            urwid.Columns(
                [
                    (1, urwid.Text("╰")),
                    hline,
                    (1, urwid.Text("╯")),
                ]
            ),
            "frame",
        )

        self._middle = urwid.Columns(
            [(1, self._vline), widget, (1, self._vline)],
            focus_column=1,
        )
        self._all = urwid.Pile(
            [("pack", self._topline), self._middle, ("pack", self._bottomline)],
            focus_item=1,
        )

        urwid.WidgetWrap.__init__(self, self._all)
        self._original_widget = widget

    def render(self, size, focus):
        attr = "frame focus color" if focus else "frame"
        self._middle.contents[0][0].set_attr_map({None: attr})
        self._topline.set_style(("╭", "╮"), "─", attr)
        self._all.contents[2][0].set_attr_map({None: attr})
        return super().render(size, focus)


class FocusLineBoxTop(urwid.WidgetDecoration, urwid.WidgetWrap):
    def __init__(self, widget, title="", status=None, title_attr: str = "editor title") -> None:
        self._topline = TopBorder(("━", "━"), "━", "frame", title, status, title_attr)
        self._all = urwid.Pile([("pack", self._topline), widget], focus_item=1)
        urwid.WidgetWrap.__init__(self, self._all)
        self._original_widget = widget

    def render(self, size, focus):
        self._topline.set_style(("━", "━"), "━", "frame focus top" if focus else "frame")
        return super().render(size, focus)


class NoFrame(urwid.WidgetPlaceholder):
    """`[view] frame = False`: no frame (and no room for a title)"""

    def __init__(self, widget, title="", status=None, title_attr: str = "editor title") -> None:
        super().__init__(widget)


def has_title(frame_style: str) -> bool:
    """whether frames of `[view] frame` style show a title and a status"""
    return frame_style != "False"


linebox = {
    "color": FocusLineBoxColor,
    "top": FocusLineBoxTop,
    "width": FocusLineBoxWidth,
    "False": NoFrame,
}


def button(
    *args,
    attr_map: str = "button",
    focus_map="button focus",
    padding_left=0,
    padding_right=0,
    **kwargs,
):
    """wrapping an urwid button in attrmap and padding"""
    mapped = urwid.AttrMap(urwid.Button(*args, **kwargs), attr_map=attr_map, focus_map=focus_map)
    return urwid.Padding(mapped, left=padding_left, right=padding_right)


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


class PopUpTarget(urwid.PopUpTarget):
    """keeps pop-ups on the screen

    A pop-up that would reach beyond the bottom opens upwards, above the row
    of its launcher (if there's room there, otherwise it's moved up as far as
    needed); one reaching beyond the right edge is moved to the left.
    Pop-ups hang `anchor_rows` rows (an attribute of the pop-up widget,
    default 1) below the top of their launcher.

    Unlike urwid's, the screen below a pop-up is drawn as focused, so the
    field (row, card, frame) the pop-up belongs to keeps its focus style.
    """

    def render(self, size, focus=False):
        self._update_overlay(size, focus)
        if not self._pop_up_levels:
            return self._current_widget.render(size, focus=focus)
        canvas = urwid.CompositeCanvas(self._original_widget.render(size, focus=focus))
        canvas.cursor = None  # the cursor belongs to the pop-up
        for widget, overlay in self._pop_up_levels:
            top = urwid.CompositeCanvas(
                widget.render((overlay.width_amount, overlay.height_amount), focus=focus)
            )
            canvas = urwid.CanvasOverlay(top, canvas, overlay.left, overlay.top)
        return canvas

    def _update_overlay(self, size, focus):
        super()._update_overlay(size, focus)
        maxcol, maxrow = size
        for widget, overlay in self._pop_up_levels:
            width, height = overlay.width_amount, overlay.height_amount
            if not isinstance(width, int) or not isinstance(height, int):
                continue
            left, top = overlay.left, overlay.top
            if top + height > maxrow:
                above = top - getattr(widget, "anchor_rows", 1) - height
                top = above if above >= 0 else max(0, maxrow - height)
            if left + width > maxcol:
                left = max(0, maxcol - width)
            if (left, top) != (overlay.left, overlay.top):
                overlay.set_overlay_parameters(
                    align="left", width=width, valign="top", height=height, left=left, top=top
                )


W = typing.TypeVar("W", bound=urwid.Widget)


def find_child(widget: object, cls: type[W]) -> W:
    """the first widget of type `cls` in `widget` or the widgets it wraps
    (decorations like AttrMap and Padding, WidgetWrap, PopUpLauncher), so the
    static type survives chains like `x.original_widget.base_widget`

    :raises TypeError: if there is none
    """
    current: object = widget
    seen = 0
    while current is not None and seen < 32:
        if isinstance(current, cls):
            return current
        if isinstance(current, urwid.WidgetDecoration):
            current = current.original_widget
        elif isinstance(current, urwid.WidgetWrap):
            current = current._w
        elif isinstance(current, urwid.WidgetPlaceholder):
            current = current.original_widget
        else:
            break
        seen += 1
    raise TypeError(f"no {cls.__name__} in {widget!r}")
