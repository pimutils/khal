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

"""Showing and hiding calendars while ikhal runs (`c`)

Hidden calendars are a filter of the collection (`hidden_calendars`, see
`CalendarCollection.get_events_on`), so the list, the month column and view
plugins follow without knowing about it; nothing is saved.
"""

from __future__ import annotations

from collections.abc import Callable

import urwid

from .editor_layout import UNICODE, Glyphs
from .floating import float_box

HINT = "space show/hide · a all · n none · esc"


class CalendarRow(urwid.WidgetWrap):
    """`▌ ✓ ● work      2` (the ▌ while focused, ✓ while shown)"""

    def __init__(self, name: str, number: int, width: int, shown, glyphs: Glyphs) -> None:
        self.name = name
        self._number = number
        self._width = width
        self._shown = shown
        self._glyphs = glyphs
        self._text = urwid.Text("", wrap="clip")
        self._focused: bool | None = None
        self._map = urwid.AttrMap(self._text, "float choice")
        super().__init__(self._map)

    def selectable(self) -> bool:
        return True

    def keypress(self, size, key):
        return key

    def refresh(self, focused: bool | None = None) -> None:
        focused = self._focused if focused is None else focused
        self._focused = focused
        shown = self._shown(self.name)
        suffix = " focus" if focused else ""
        tick = "✓" if self._glyphs is UNICODE else "x"
        number = str(self._number) if self._number <= 9 else " "
        self._text.set_text(
            [
                ("editor marker", self._glyphs.marker) if focused else " ",
                " ",
                ("float choice tick" + suffix, tick) if shown else " ",
                " ",
                (f"calendar {self.name}" + (" row" if focused else " mark"), self._glyphs.dot),
                " ",
                (
                    ("float choice" + suffix) if shown else ("float choice hint" + suffix),
                    self.name.ljust(self._width),
                ),
                " ",
                ("float choice hint" + suffix, number),
                " ",
            ]
        )
        self._map.set_attr_map({None: "float choice" + suffix})

    def render(self, size, focus=False):
        if focus != self._focused:
            self.refresh(focus)
        return super().render(size, focus)


class CalendarsBox(urwid.WidgetWrap):
    """the list of calendars: space toggles the focused one right away, 1–9
    the n-th, a shows all, esc and enter close"""

    def __init__(
        self,
        names: list[str],
        is_shown: Callable[[str], bool],
        set_shown: Callable[[str, bool], None],
        on_close: Callable[[], None],
        glyphs: Glyphs = UNICODE,
    ) -> None:
        self.names = names
        self._is_shown = is_shown
        self._set_shown = set_shown
        self._on_close = on_close
        width = max([len(name) for name in names] + [12])
        self.entries = [
            CalendarRow(name, number, width, is_shown, glyphs)
            for number, name in enumerate(names, 1)
        ]
        for row in self.entries:
            row.refresh(False)
        self._walker = urwid.SimpleFocusListWalker(list(self.entries))
        self.listbox = urwid.ListBox(self._walker)
        hint = urwid.Text(("float dim", "  " + HINT))
        body = urwid.Pile([("weight", 1, self.listbox), ("pack", urwid.Divider()), ("pack", hint)])
        self._body = body
        self._glyphs = glyphs
        self.width = max(width + 12, len(HINT) + 6)
        self.height = len(names) + 4
        super().__init__(urwid.SolidFill(" "))
        self._update_title()

    @property
    def hidden(self) -> int:
        return sum(1 for name in self.names if not self._is_shown(name))

    def _update_title(self) -> None:
        """the top border says how many are hidden"""
        hint = f"{self.hidden} hidden" if self.hidden else ""
        self._w = float_box("Calendars", self._body, hint, self._glyphs)

    def toggle(self, name: str) -> None:
        self._set_shown(name, not self._is_shown(name))
        self._refresh()

    def show_all(self) -> None:
        for name in self.names:
            if not self._is_shown(name):
                self._set_shown(name, True)
        self._refresh()

    def show_none(self) -> None:
        for name in self.names:
            if self._is_shown(name):
                self._set_shown(name, False)
        self._refresh()

    def _refresh(self) -> None:
        focus = self._walker.get_focus()[1]
        for index, row in enumerate(self.entries):
            row.refresh(index == focus)
        self._update_title()

    def keypress(self, size, key):
        key = {"j": "down", "k": "up"}.get(key, key)
        if key in ("esc", "enter"):
            self._on_close()
            return None
        if key == " ":
            self.toggle(self._walker.get_focus()[0].name)
            return None
        if key == "a":
            self.show_all()
            return None
        if key == "n":
            self.show_none()
            return None
        if key.isdigit() and 1 <= int(key) <= min(9, len(self.names)):
            self.toggle(self.names[int(key) - 1])
            return None
        if key in ("up", "down", "page up", "page down", "home", "end"):
            super().keypress(size, key)
        return None
