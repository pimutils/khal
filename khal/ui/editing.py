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

"""ikhal's editing screen: the event editor and, at its right, the current
view of the events (list, time grid, ... see `khal.views`)

The split between the two can be moved with the mouse (drag the border) or
with keys, the width is kept for the rest of the session. A key moves the
focus between the editor and the right column, where the view's own keys
work (e.g. `w` for the next view, 1/3/7 in the time grid).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import urwid

from .editor_layout import UNICODE, format_key
from .widgets import CAttrMap, has_title, linebox

if TYPE_CHECKING:
    from .editor import EventEditor

# the editor gets about two thirds of the screen, but not more than it can use
EDITOR_SHARE = 2 / 3
EDITOR_MAX = 94  # columns, with the frame
MIN_COLUMN = 16  # neither column gets narrower than this
RESIZE_STEP = 4


def parse_width(value, maxcol: int) -> int | None:
    """`[view] editor_width`: '' (automatic), '60%' or a number of columns"""
    value = str(value or "").strip()
    if not value:
        return None
    try:
        if value.endswith("%"):
            return round(maxcol * float(value[:-1]) / 100)
        return int(value)
    except ValueError:
        return None


def automatic_width(maxcol: int) -> int:
    """the editor's width: two thirds, at most EDITOR_MAX, the rest is for the
    right column"""
    return min(EDITOR_MAX, round(maxcol * EDITOR_SHARE))


def clamp_width(width: int, maxcol: int) -> int:
    return max(min(MIN_COLUMN, maxcol), min(width, maxcol - MIN_COLUMN))


class EditingScreen(urwid.WidgetWrap):
    """the editor (left) and the current view of the events (right)"""

    def __init__(self, pane, column, editor: EventEditor) -> None:
        self.pane = pane
        self.column = column
        self.editor = editor
        self._conf = pane._conf
        frame_style = self._conf["view"]["frame"]
        box = linebox[frame_style]
        self.framed_status = has_title(frame_style)
        editor.status_in_frame = self.framed_status
        new = editor.event.etag is None
        self._editor_box = CAttrMap(
            box(
                editor,
                title="New event" if new else "Edit event",
                status=lambda: editor.status_markup(),
            ),
            "editor",
            "editor focus",
        )
        self._slot = urwid.WidgetPlaceholder(column.dlistbox)
        self._right_box = CAttrMap(box(self._slot), "eventcolumn")
        self._columns = urwid.Columns(
            [(automatic_width(80), self._editor_box), self._right_box],
            dividechars=0,
            focus_column=0,
        )
        self._dragging = False
        self._maxcol = 0
        super().__init__(self._columns)

    # -- the window's header and footer

    @property
    def title(self) -> str:
        """with the title in the frame, the header shows the overview's
        header line (clock, next event)"""
        if self.framed_status:
            return self.pane.title
        return self.editor.title

    def header_markup(self, maxcol: int) -> list | None:
        """the overview's header line (clock, next event), if the title is in
        the frame; otherwise the title (`Edit: …`)"""
        if self.framed_status:
            return self.pane.header_markup(maxcol)
        return None

    @property
    def footer_hints(self) -> list:
        keys = self._conf["keybindings"]
        markup: list = [" "]
        for command, text in (
            ("tab", "next field"),
            ("other_column", "other column"),
            ("switch_view_editor", "view"),
        ):
            bound = keys.get(command) or [command]
            markup += [("footer key", format_key(bound[0], UNICODE)), f" {text}  "]
        narrower, wider = keys.get("editor_narrower"), keys.get("editor_wider")
        if narrower and wider:
            markup += [
                ("footer key", format_key(narrower[0], UNICODE)),
                " ",
                ("footer key", format_key(wider[0], UNICODE)),
                " width  ",
            ]
        markup += [("footer key", "?"), " help"]
        return markup

    # -- width of the editor

    def editor_width(self, maxcol: int) -> int:
        width = getattr(self.pane, "editor_width", None)  # moved in this session
        if width is None:
            width = parse_width(self._conf["view"].get("editor_width", ""), maxcol)
        if width is None:
            width = automatic_width(maxcol)
        return clamp_width(width, maxcol)

    def set_editor_width(self, width: int) -> None:
        """move the split (kept for the rest of the session)"""
        self.pane.editor_width = clamp_width(width, self._maxcol or width + MIN_COLUMN)
        self._invalidate()

    def _layout(self, maxcol: int) -> None:
        self._maxcol = maxcol
        width = self.editor_width(maxcol)
        options = self._columns.options("given", width)
        if self._columns.contents[0][1] != options:
            self._columns.contents[0] = (self._editor_box, options)
        if self._slot.original_widget is not self.column.dlistbox:  # view switched
            self._slot.original_widget = self.column.dlistbox

    @property
    def right_focused(self) -> bool:
        return self._columns.focus_position == 1

    def focus_other_column(self) -> None:
        self._columns.focus_position = 0 if self.right_focused else 1

    # -- urwid

    def render(self, size, focus=False):
        self._layout(size[0])
        return super().render(size, focus)

    def keypress(self, size, key):
        self._layout(size[0])
        keys = self._conf["keybindings"]
        if key in keys.get("other_column", []):
            self.focus_other_column()
            return None
        if key in keys.get("editor_narrower", []):
            self.set_editor_width(self.editor_width(size[0]) - RESIZE_STEP)
            return None
        if key in keys.get("editor_wider", []):
            self.set_editor_width(self.editor_width(size[0]) + RESIZE_STEP)
            return None
        if key in keys.get("switch_view_editor", []) or (
            self.right_focused and key in keys.get("switch_view", [])
        ):
            self.pane.switch_view()
            self._layout(size[0])
            return None
        if self.right_focused and key == "esc":
            # back to the editor (esc in the editor leaves it)
            self._columns.focus_position = 0
            return None
        key = super().keypress(size, key)
        if self.right_focused and key in self.pane.window.quit_keys:
            return None  # don't leave the editor from the right column
        return key

    def _on_border(self, col: int) -> bool:
        """the frames' borders between editor and right column"""
        width = self.editor_width(self._maxcol)
        return width - 1 <= col <= width

    def mouse_event(self, size, event, button, col, row, focus):
        self._layout(size[0])
        if event == "mouse press" and button == 1 and self._on_border(col):
            self._dragging = True
            return True
        if self._dragging:
            if event == "mouse drag":
                self.set_editor_width(col + 1)
            elif event == "mouse release":
                self._dragging = False
            return True
        return super().mouse_event(size, event, button, col, row, focus)
