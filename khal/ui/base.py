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


"""this module should contain classes that are specific to ikhal, more
general widgets should go in widgets.py"""

from __future__ import annotations

import datetime as dt
import logging
import threading
import time
from collections.abc import Callable

import urwid

from .floating import Answer, ChoiceDialog, HelpView, LogEntry, LogView, float_box, help_groups
from .widgets import NColumns

logger = logging.getLogger("khal")


class Pane(urwid.WidgetWrap):
    """An abstract Pane to be used in a Window object."""

    def __init__(self, widget, title=None, description=None) -> None:
        self.widget = widget
        urwid.WidgetWrap.__init__(self, widget)
        self._title = title or ""
        self._description = description or ""
        self.window = None

    @property
    def title(self):
        return self._title

    def selectable(self):
        """mark this widget as selectable"""
        return True

    @property
    def description(self):
        return self._description

    def choose(
        self,
        title: str,
        question: str,
        answers: list[Answer],
        description: str = "",
        on_cancel: Callable[[], None] | None = None,
    ) -> ChoiceDialog:
        """Ask a question in a floating box, every answer has its own key.

        The dialog is closed before an answer's callback is called; esc closes
        it and calls `on_cancel` (if given).
        """
        assert self.window is not None
        window = self.window

        def close_then(callback):
            def run():
                window.backtrack()
                if callback is not None:
                    callback()

            return run

        answers = [
            Answer(answer.key, answer.label, close_then(answer.callback), answer.detail)
            for answer in answers
        ]
        dialog = ChoiceDialog(title, question, answers, close_then(on_cancel), description)
        window.open_floating(dialog, width=dialog.width, height="pack")
        return dialog

    def dialog(self, text: str, buttons: list[tuple[str, Callable]]) -> None:
        """Open a dialog box (kept for plugins, prefer `choose()`).

        :param text: Text to appear as the body of the Dialog box
        :param buttons: list of tuples button labels and functions to call
            when the button is pressed (they get passed `None`), each gets
            the first not yet used letter of its label as key
        """
        used: set[str] = set()
        answers = []
        for label, func in buttons:
            key = next((c.lower() for c in label if c.isalnum() and c.lower() not in used), "")
            used.add(key)

            def callback(func=func):
                func(None)

            answers.append(Answer(key, label, callback))
        lines = text.splitlines() or [""]
        # the callbacks of the old API close the dialog themselves
        assert self.window is not None
        dialog = ChoiceDialog("", lines[0], answers, self.window.backtrack, "\n".join(lines[1:]))
        self.window.open_floating(dialog, width=dialog.width, height="pack")

    def scrollable_dialog(
        self,
        text: str | list[urwid.Widget],
        buttons: list[tuple[str, Callable]] | None = None,
        title: str = "",
        hint: str = "esc close",
    ) -> None:
        """Open a scrollable floating box (closed with esc)."""
        if isinstance(text, str):
            body = urwid.ListBox([urwid.Text(line) for line in text.splitlines()])
        else:
            body = urwid.ListBox(text)
        if buttons:
            buttons = NColumns(
                [urwid.Button(label, on_press=func) for label, func in buttons],
                outermost=True,
            )
            content = urwid.Pile([body, ("pack", buttons)])
        else:
            content = body
        assert self.window is not None
        self.window.open_floating(
            float_box(title, content, hint), width=("relative", 80), height=("relative", 80)
        )

    def keypress(self, size, key):
        """Handle application-wide key strokes."""
        if key in ["f1", "?"]:
            self.show_keybindings()
        elif key in ["L"]:
            self.show_log()
        else:
            return super().keypress(size, key)

    def extra_keybindings(self) -> list[tuple[str, list[tuple[str, list[str], str]]]]:
        """additional sections for the keybindings help

        :returns: list of (section title, list of (command, keys, description))
        """
        return []

    def show_keybindings(self):
        """the keys, as a floating box"""
        conf = getattr(self, "_conf", None) or {}
        help_view = HelpView(help_groups(conf.get("keybindings", {}), self.extra_keybindings()))
        assert self.window is not None
        self.window.open_floating(
            float_box("Keys", help_view, "esc close"),
            width=("relative", 90),
            height=("relative", 90),
            min_width=40,
        )

    def show_log(self):
        """the log, as a floating box (the newest entry at the bottom)"""
        assert self.window is not None
        self.window.open_floating(
            float_box("Log", LogView(self.window._log), "esc close"),
            width=("relative", 90),
            height=("relative", 80),
            min_width=40,
        )


class FooterLine(urwid.WidgetWrap):
    """the key hints and, if there's room for both, the version at the right"""

    def __init__(self, hints: urwid.Text, version: str) -> None:
        self._hints = hints
        self._version = version
        version_text = urwid.Text(("footer version", version + " "), align="right")
        self._both = urwid.Columns([hints, ("pack", version_text)], dividechars=1)
        self._alone = urwid.Columns([hints])
        super().__init__(self._both)

    def render(self, size, focus=False):
        text = self._hints.get_text()[0]
        needed = urwid.calc_width(text, 0, len(text)) + len(self._version) + 2
        wanted = self._both if not self._version or needed <= size[0] else self._alone
        if self._w is not wanted:
            self._w = wanted
        return super().render(size, focus)


class PromptLine(urwid.WidgetWrap):
    """an input line in place of the footer (like vim's command line)

    enter calls `on_enter(text)`, which returns an error to show (the line
    stays open) or None (the line closes); esc closes it.
    """

    def __init__(self, caption: str, on_enter, on_close) -> None:
        self._on_enter = on_enter
        self._on_close = on_close
        self.edit = urwid.Edit()
        self._error = urwid.Text("", align="right")
        super().__init__(
            urwid.Columns(
                [
                    ("pack", urwid.Text(("footer key", f" {caption} "))),
                    self.edit,
                    (24, self._error),
                ]
            )
        )

    def keypress(self, size, key):
        if key == "esc":
            self._on_close()
            return None
        if key == "enter":
            error = self._on_enter(self.edit.get_edit_text())
            if error:
                self._error.set_text(("message error", f"✗ {error} "))
            else:
                self._on_close()
            return None
        self._error.set_text("")
        self.edit.keypress((max(1, size[0] - 20),), key)
        return None


class HeaderLine(urwid.WidgetWrap):
    """the window's header line: a message (for a few seconds) or the
    header of the pane (`header_markup(maxcol)`, which can adapt to the
    width) or its title"""

    no_cache = ["render", "rows"]  # the header changes with the time and the width

    def __init__(self, window: Window, text: urwid.Text) -> None:
        self._window = window
        self._text = text  # the title or a message, see Window.update_header
        self._shown = urwid.Text("", wrap="ellipsis")
        super().__init__(self._shown)

    def _markup(self, maxcol: int):
        window = self._window
        if not window._header_is_warning:
            for pane, _ in reversed(window._track):
                header = getattr(pane, "header_markup", None)
                if header is None:
                    continue
                markup = header(maxcol)
                if markup is not None:
                    return markup
                break
        text, attrs = self._text.get_text()
        return self._text_markup(text, attrs) if attrs else text

    @property
    def text(self) -> str:
        """the title or message (without the pane's own header)"""
        return self._text.text

    @staticmethod
    def _text_markup(text: str, attrs) -> list:
        markup, position = [], 0
        for attr, length in attrs:
            markup.append((attr, text[position : position + length]))
            position += length
        if position < len(text):
            markup.append(text[position:])
        return markup

    def rows(self, size, focus=False):
        return 1

    def render(self, size, focus=False):
        markup = self._markup(size[0])
        if markup != getattr(self, "_last", None):
            self._last = markup
            self._shown.set_text(markup or "")
        return super().render(size, focus)


class Window(urwid.Frame):
    """The main user interface frame.

    A window is a frame which displays a header, a footer and a body.
    The header and the footer are handled by this object, and the body
    is the space where Panes can be displayed.

    Each Pane is an interface to interact with the database in one
    way: list the VCards, edit one VCard, and so on. The Window
    provides a mechanism allowing the panes to chain themselves, and
    to carry data between them.

    The header shows the current pane's title, or for a few seconds a message
    (see `message()`); the footer shows key hints and, at its right, the
    version.
    """

    MESSAGE_SECONDS = 4
    # attributes used by `alert((attr, text))` callers -> message kind
    ALERT_KINDS = {"alert": "error", "light red": "error", "light green": "ok"}

    def __init__(self, footer="", quit_keys=None, version: str = "", log_key: str = "L") -> None:
        quit_keys = quit_keys or ["q"]
        self._track: list[tuple[urwid.Widget, Callable | None]] = []

        self._header_text = urwid.Text("", wrap="ellipsis")
        self._header_line = HeaderLine(self, self._header_text)
        header = urwid.AttrMap(self._header_line, "header")
        self._footer_text = urwid.Text(footer, wrap="ellipsis")
        footer_widget = urwid.AttrMap(FooterLine(self._footer_text, version), "footer")
        urwid.Frame.__init__(
            self,
            urwid.Text(""),
            header=header,
            footer=footer_widget,
        )
        self._original_w = None
        self.quit_keys = quit_keys
        self.log_key = log_key
        self.loop = None
        self._log: list[LogEntry] = []
        self._header_is_warning = False
        self._message_serial = 0
        # attribute map for the screen behind floating boxes (None: no backdrop)
        self.backdrop: dict[str | None, str] | None = None
        # the theme's semantic colours (bg, acc, ...), set by start_pane
        self.theme_colors: dict[str, str] = {}
        # the theme paints its own background (set by start_pane)
        self.paints_background = False

        def clear(message):
            if message is None:
                self._header_is_warning = False
                self.clear_header()

        self._alert_daemon = AlertDaemon(clear)
        self._alert_daemon.start()
        self.update_header()

    # -- panes

    def open(self, pane, callback=None):
        """Open a new pane.

        The given pane is added to the track and opened. If the given
        callback is not None, it will be called when this new pane
        will be closed.
        """
        pane.window = self
        self._track.append((pane, callback))
        self._update(pane)

    def open_floating(
        self, box, width, height, min_width=None, callback=None, backdrop: bool = True
    ) -> urwid.Overlay:
        """open `box` floating over the current pane (with the backdrop,
        unless `backdrop` is False, e.g. for lists that belong to a field)"""
        behind = self._get_current_pane()
        if self.backdrop is not None and backdrop:
            behind = urwid.AttrMap(behind, self.backdrop)
        overlay = urwid.Overlay(box, behind, "center", width, "middle", height, min_width=min_width)
        overlay.title = getattr(self._get_current_pane(), "title", "")
        self.open(overlay, callback)
        return overlay

    def backtrack(self, data=None):
        """Unstack the displayed pane.

        The current pane is discarded, and the previous one is
        displayed. If the current pane was opened with a callback,
        this callback is called with the given data (if any) before
        the previous pane gets redrawn.
        """
        _old_pane, cb = self._track.pop()
        if cb:
            cb(data)

        if self._track:
            self._update(self._get_current_pane())
        else:
            raise urwid.ExitMainLoop()

    def keypress(self, size, key):
        # the header shows the view (tabs) and the time, keys may change both
        self._header_line._invalidate()
        return super().keypress(size, key)

    def mouse_event(self, size, event, button, col, row, focus):
        self._header_line._invalidate()
        return super().mouse_event(size, event, button, col, row, focus)

    def is_top_level(self):
        """Is the current pane the top-level one?"""
        return len(self._track) == 1

    def on_key_press(self, key):
        """Handle application-wide key strokes."""
        if key in self.quit_keys:
            self.backtrack()
        elif key == "esc" and not self.is_top_level():
            self.backtrack()
        return key

    def _update(self, pane):
        self.set_body(pane)
        hints = getattr(pane, "footer_hints", None)
        if hints is not None:  # key hints for the current context
            self._footer_text.set_text(hints)
        self.clear_header()

    def prompt(self, caption: str, on_enter) -> PromptLine:
        """ask for a line of text at the bottom, see PromptLine"""
        footer = self.footer

        def close():
            self.footer = footer
            self.focus_position = "body"

        line = PromptLine(caption, on_enter, close)
        self.footer = urwid.AttrMap(line, "footer")
        self.focus_position = "footer"
        return line

    def refresh_footer(self) -> None:
        """show the current pane's key hints again (e.g. after they changed)"""
        hints = getattr(self._get_current_pane(), "footer_hints", None)
        if hints is not None:
            self._footer_text.set_text(hints)

    def log(self, record: str | LogEntry, level: int = logging.INFO) -> None:
        """add `record` to the log (`L`), a text gets the current time"""
        if not isinstance(record, LogEntry):
            record = LogEntry(dt.datetime.now(), level, str(record))
        self._log.append(record)

    def _get_current_pane(self):
        return self._track[-1][0] if self._track else None

    # -- header

    def clear_header(self):
        """clears header if we are not currently showing a message"""
        if not self._header_is_warning:
            self.update_header()

    def update_header(self, alert=None, warn=False):
        """show the current pane's title (and `alert`) in the header line"""
        self._header_is_warning = warn
        pane_title = getattr(self._get_current_pane(), "title", None)
        text: list = []
        for part in (pane_title, alert):
            if part:
                text.append(part)
                text.append(("message info", " | "))
        self._header_text.set_text(text[:-1] or "")
        self._header_line._invalidate()

    def message(self, text: str, kind: str = "info") -> None:
        """show `text` in the header for a few seconds

        :param kind: `ok` (✓ ...), `error` (✗ ..., with a hint to the log) or `info`
        """
        markup: list = [" "]
        if kind == "ok":
            markup.append(("message ok", f"✓ {text}"))
        elif kind == "error":
            markup.append(("message error", f"✗ {text}"))
            markup.append(("message info", f"  {self.log_key} shows the log"))
        else:
            markup.append(("message info", text))
        self._header_is_warning = True
        self._header_text.set_text(markup)
        self._header_line._invalidate()
        self._message_serial += 1
        serial = self._message_serial
        if self.loop is not None:

            def clear(_loop, _data):
                if serial == self._message_serial:
                    self._header_is_warning = False
                    self.clear_header()

            self.loop.set_alarm_in(self.MESSAGE_SECONDS, clear)
        else:
            self._alert_daemon.alert(text)

    def alert(self, message) -> None:
        """compatibility: `message` is a text or (palette attribute, text)"""
        if isinstance(message, tuple):
            attr, text = message
            self.message(text, self.ALERT_KINDS.get(attr, "info"))
        else:
            self.message(message, "info")


class AlertDaemon(threading.Thread):
    def __init__(self, set_msg_func) -> None:
        threading.Thread.__init__(self)
        self._set_msg_func = set_msg_func
        self.daemon = True
        self._start_countdown = threading.Event()

    def alert(self, msg):
        self._start_countdown.set()

    def run(self):
        # This is a daemon thread. Since the global namespace is going to
        # vanish on interpreter shutdown, redefine everything from the global
        # namespace here.
        _sleep = time.sleep
        _exception = Exception
        _event = self._start_countdown
        _set_msg = self._set_msg_func

        while True:
            _event.wait()
            _sleep(3)
            try:
                _set_msg(None)
            except _exception:
                pass
            _event.clear()
