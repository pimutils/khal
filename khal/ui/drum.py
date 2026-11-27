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

"""The drum: a small pop-up to pick a time or a duration by scrolling.

Columns of values (e.g. hours | minutes), two values above and below the
current one are visible, the focused column is filled in the accent colour.
←→/tab switch the column, ↑↓ scroll, typed digits set the value directly,
enter takes it, esc restores the old value. An optional note column shows e.g.
the resulting duration for an end time.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import urwid

from .editor_layout import UNICODE, Card, Glyphs

VISIBLE = 2  # values shown above and below the current one


@dataclass
class DrumColumn:
    values: Sequence
    index: int
    fmt: Callable[[object], str] = str
    wrap: bool = True  # scrolling past the end continues at the start

    @property
    def value(self):
        return self.values[self.index]

    def at(self, offset: int):
        """the value `offset` rows away, None if there is none (no wrap)"""
        position = self.index + offset
        if self.wrap:
            return self.values[position % len(self.values)]
        if 0 <= position < len(self.values):
            return self.values[position]
        return None

    def move(self, delta: int) -> int:
        """scroll by `delta`, returns how often it wrapped (-1, 0, 1)"""
        position = self.index + delta
        if not self.wrap:
            self.index = max(0, min(len(self.values) - 1, position))
            return 0
        self.index = position % len(self.values)
        return (position - self.index) // len(self.values)


class Drum(urwid.Widget):
    """a box widget with `columns`; `note(values)` annotates each row"""

    _sizing = frozenset([urwid.BOX])
    _selectable = True

    def __init__(
        self,
        columns: list[DrumColumn],
        on_take: Callable[[list], None],
        on_cancel: Callable[[], None],
        note: Callable[[list, int], str] | None = None,
        separator: str = ":",
        digits: Callable[[str], list | None] | None = None,
        glyphs: Glyphs = UNICODE,
    ) -> None:
        """
        :param note: gets the values of a row and the number of times the
            first column wrapped (e.g. past midnight), returns its note
        :param digits: turns typed digits into values (None: not yet complete)
        """
        super().__init__()
        self.columns = columns
        self.focus_column = 0
        self.wrapped = 0  # times the first column scrolled past its end
        self._on_take = on_take
        self._on_cancel = on_cancel
        self._note = note
        self._separator = separator
        self._digits = digits
        self._typed = ""
        self._glyphs = glyphs
        self.width = self._width()

    @property
    def values(self) -> list:
        return [column.value for column in self.columns]

    def _row_values(self, offset: int) -> list:
        return [column.at(offset) for column in self.columns]

    def _cell_width(self, column: DrumColumn) -> int:
        return max(len(column.fmt(value)) for value in column.values)

    def _note_width(self) -> int:
        if self._note is None:
            return 0
        notes = [self._note(self._row_values(offset), self.wrapped) for offset in range(-3, 4)]
        return max(12, max(len(note) for note in notes))

    def _hint(self) -> str:
        return " " + ("↑↓ ←→ enter esc" if self._glyphs is UNICODE else "up/down enter esc")

    def _width(self) -> int:
        cells = sum(self._cell_width(column) + 3 for column in self.columns)
        return max(2 + cells + self._note_width() + 2, len(self._hint()) + 1)

    def rows(self, size, focus=False):
        return 2 * VISIBLE + 2

    def render(self, size, focus=False):
        maxcol = size[0]
        lines = []
        for offset in range(-VISIBLE, VISIBLE + 1):
            markup: list = ["  "]
            row = self._row_values(offset)
            for index, column in enumerate(self.columns):
                value = row[index]
                text = "" if value is None else column.fmt(value)
                text = text.rjust(self._cell_width(column))
                if offset == 0 and index == self.focus_column:
                    markup.append(("editor day on", f" {text} "))
                elif offset == 0:
                    markup.append(("editor field", f" {text} "))
                else:
                    markup.append(("editor dim", f" {text} "))
                if index < len(self.columns) - 1:
                    markup.append(self._separator if offset == 0 else " ")
            if self._note is not None:
                # the note is about the focused column's value on this row,
                # combined with the current values of the other columns
                values = self.values
                values[self.focus_column] = row[self.focus_column]
                wrapped = self.wrapped + self._wraps_at(offset)
                note = self._note(values, wrapped) if None not in values else ""
                markup.append(("editor field" if offset == 0 else "editor dim", "  " + note))
            lines.append(urwid.Text(markup, wrap="clip"))
        lines.append(urwid.Text(("float dim", self._hint()), wrap="clip"))
        return urwid.Pile(lines).render((maxcol,), focus)

    def _wraps_at(self, offset: int) -> int:
        first = self.columns[0]
        if not first.wrap:
            return 0
        return (first.index + offset) // len(first.values)

    def keypress(self, size, key):
        if key in ("up", "k", "down", "j"):
            delta = -1 if key in ("up", "k") else 1
            wrapped = self.columns[self.focus_column].move(delta)
            if self.focus_column == 0:
                self.wrapped += wrapped
            self._typed = ""
        elif key in ("left", "h", "shift tab"):
            self.focus_column = (self.focus_column - 1) % len(self.columns)
        elif key in ("right", "l", "tab"):
            self.focus_column = (self.focus_column + 1) % len(self.columns)
        elif key == "enter":
            self._on_take(self.values)
        elif key == "esc":
            self._on_cancel()
        elif len(key) == 1 and key.isdigit() and self._digits is not None:
            self._typed += key
            values = self._digits(self._typed)
            if values is not None:
                self._set(values)
                self._typed = ""
        else:
            return key
        self._invalidate()
        return None

    def _set(self, values: list) -> None:
        for column, value in zip(self.columns, values):
            if value in column.values:
                column.index = list(column.values).index(value)


def drum_box(drum: Drum, glyphs: Glyphs = UNICODE) -> Card:
    """the drum in an accent framed box (a field pop-up: no backdrop)"""
    return Card(
        "",
        urwid.BoxAdapter(drum, drum.rows((drum.width,))),
        glyphs,
        attr="float border",
        focus_attr="float border",
    )


class DrumPopUp(urwid.PopUpLauncher):
    """opens a drum below the wrapped field when enter is pressed

    `make_drum(close)` creates the Drum, `close()` closes the pop-up.
    """

    def __init__(self, widget, make_drum: Callable[[Callable[[], None]], Drum]) -> None:
        self._make_drum = make_drum
        self._drum: Drum | None = None
        super().__init__(widget)

    def keypress(self, size, key):
        if key == "enter":
            self.open_pop_up()
            return None
        return super().keypress(size, key)

    def create_pop_up(self):
        self._drum = self._make_drum(self.close_pop_up)
        return drum_box(self._drum)

    def get_pop_up_parameters(self):
        drum = self._drum or self._make_drum(lambda: None)
        return {
            "left": 0,
            "top": 1,
            "overlay_width": drum.width + 2,
            "overlay_height": drum.rows((drum.width,)) + 2,
        }
