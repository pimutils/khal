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

"""The finder (`/` in ikhal): search events as you type

A floating box with the query and the matching events on the left and a
preview of the selected event on the right. ↑↓ (ctrl n/p) move, enter jumps
to the event in the list, esc closes.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

import urwid

from .details import _glyphs, details_rows
from .floating import float_box
from .widgets import ExtendedEdit

# more results are not shown (the count still says how many there are)
MAX_RESULTS = 200


def _start(event) -> dt.datetime:
    start = event.start_local
    if isinstance(start, dt.datetime):
        return start.replace(tzinfo=None)
    return dt.datetime.combine(start, dt.time())


def highlight(text: str, query: str) -> list:
    """`text` with (case insensitive) matches of `query` in the accent colour"""
    if not query:
        return [text]
    markup: list = []
    lower, needle, position = text.lower(), query.lower(), 0
    while True:
        found = lower.find(needle, position)
        if found < 0:
            break
        if found > position:
            markup.append(text[position:found])
        markup.append(("finder match", text[found : found + len(query)]))
        position = found + len(query)
    if position < len(text):
        markup.append(text[position:])
    return markup


class ResultRow(urwid.WidgetWrap):
    """`▌▍28.11. Dinner at Anna's` (▌ while selected)"""

    def __init__(self, event, query: str, dateformat: str, glyphs, hidden: bool = False) -> None:
        """
        :param hidden: the event's calendar is hidden: the row is dimmed
        """
        self.event = event
        self.hidden = hidden
        self._text = urwid.Text("", wrap="clip")
        title = highlight(event.summary or "", query)
        if hidden:
            title = [
                ("float choice hint", part) if isinstance(part, str) else part for part in title
            ]
        self._parts = [
            ("calendar " + event.calendar + " mark", "▍" if glyphs.marker == "▌" else "|"),
            ("float choice hint", _start(event).strftime(dateformat) + " "),
            *title,
        ]
        self._marker = glyphs.marker
        self._focus_map = {
            None: "float choice focus",
            "float choice hint": "float choice hint focus",
            "finder match": "finder match focus",
            "calendar " + event.calendar + " mark": "calendar " + event.calendar + " row",
        }
        self._map = urwid.AttrMap(self._text, "float choice")
        super().__init__(self._map)
        self.set_selected(False)

    def set_selected(self, selected: bool) -> None:
        """the selected row looks focused (the focus stays in the query)"""
        marker = ("editor marker", self._marker) if selected else " "
        self._text.set_text([marker, *self._parts])
        self._map.set_attr_map(self._focus_map if selected else {None: "float choice"})

    def selectable(self) -> bool:
        return False


class Finder(urwid.WidgetWrap):
    """search as you type, with a preview of the selected event"""

    def __init__(
        self,
        conf,
        search: Callable[[str], list],
        on_jump: Callable[[object], None],
        on_close: Callable[[], None],
        hidden: Callable[[object], bool] = lambda event: False,
    ) -> None:
        """
        :param hidden: events of hidden calendars are found, but dimmed
        """
        self._hidden = hidden
        self._conf = conf
        self._search = search
        self._on_jump = on_jump
        self._on_close = on_close
        self._glyphs = _glyphs(conf)
        self.query = ""
        self._searched: str | None = None
        self.results: list = []
        self.total = 0
        self.edit = ExtendedEdit(caption=("float key", "› "))
        self._count = urwid.Text("", align="right")
        self._walker: urwid.SimpleFocusListWalker[ResultRow] = urwid.SimpleFocusListWalker([])
        self._list = urwid.ListBox(self._walker)
        rule = urwid.AttrMap(urwid.Divider(self._glyphs.rule), "editor rule")
        top = urwid.Columns([self.edit, (9, self._count)], dividechars=1)
        find = urwid.Pile([("pack", top), ("pack", rule), self._list], focus_item=0)
        self._preview: urwid.WidgetPlaceholder[urwid.Widget] = urwid.WidgetPlaceholder(
            urwid.SolidFill(" ")
        )
        columns = urwid.Columns(
            [
                float_box("Find", find, "esc", self._glyphs),
                float_box("Preview", self._preview, "", self._glyphs),
            ]
        )
        super().__init__(columns)

    # -- searching (once per screen update, so typing fast stays fast)

    def _update(self) -> None:
        query = self.edit.get_edit_text()
        if query == self._searched:
            return
        self._searched = self.query = query
        events = sorted(self._search(query), key=_start) if query.strip() else []
        self.total = len(events)
        self.results = events[:MAX_RESULTS]
        dateformat = self._conf["locale"]["dateformat"]
        self._walker[:] = [
            ResultRow(event, query, dateformat, self._glyphs, self._hidden(event))
            for event in self.results
        ]
        if self.results:
            # the first event from today on, or the last one
            today = dt.datetime.combine(dt.date.today(), dt.time())
            upcoming = [i for i, event in enumerate(self.results) if _start(event) >= today]
            self._select(upcoming[0] if upcoming else len(self.results) - 1)
        else:
            self._update_preview()

    @property
    def _position(self) -> int | None:
        """the position of the selected row (None: no results)"""
        return self._walker.focus if self._walker else None

    def _select(self, position: int) -> None:
        if self._position is None:
            return
        self._walker[self._position].set_selected(False)
        self._walker.set_focus(max(0, min(position, len(self._walker) - 1)))
        self._walker[self._walker.focus or 0].set_selected(True)
        self._update_preview()

    @property
    def selected(self):
        position = self._position
        return None if position is None else self._walker[position].event

    def _update_preview(self) -> None:
        event = self.selected
        if self.results and self._position is not None:
            position = self._position + 1
            more = "+" if self.total > len(self.results) else ""
            self._count.set_text(("float dim", f"{position}/{len(self.results)}{more}"))
        else:
            self._count.set_text(("float dim", "0/0" if self.query.strip() else ""))
        if event is None:
            self._preview.original_widget = urwid.Filler(urwid.Pile([]), valign="top")
            return
        rows = details_rows(event, self._conf, self._glyphs, rule=False)[1:]
        self._preview.original_widget = urwid.Filler(urwid.Pile(rows), valign="top")

    def _move(self, delta: int) -> None:
        if self._position is not None:
            self._select(self._position + delta)

    # -- urwid

    def render(self, size, focus=False):
        self._update()
        return super().render(size, focus)

    def keypress(self, size, key):
        self._update()
        if key == "esc":
            self._on_close()
            return None
        if key in ("down", "ctrl n"):
            self._move(1)
            return None
        if key in ("up", "ctrl p"):
            self._move(-1)
            return None
        if key in ("page down", "page up"):
            self._move(10 if key == "page down" else -10)
            return None
        if key == "enter":
            if self.selected is not None:
                self._on_jump(self.selected)
            return None
        self.edit.keypress((max(1, size[0] // 2 - 16),), key)
        return None
