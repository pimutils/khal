# Copyright (c) 2013-2017 Christian Geier et al.
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


import urwid
import threading
import time

from .widgets import NColumns


class Pane(urwid.WidgetWrap):

    """An abstract Pane to be used in a Window object."""

    def __init__(self, widget, title=None, description=None):
        self.widget = widget
        urwid.WidgetWrap.__init__(self, widget)
        self._title = title or ''
        self._description = description or ''
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

    def dialog(self, text, buttons):
        """Open a dialog box.

        :param text: Text to appear as the body of the Dialog box
        :type text: str
        :param buttons: list of tuples button labels and functions to call
            when the button is pressed
        :type buttons: list(str, callable)
        """
        lines = [urwid.Text(line) for line in text.splitlines()]

        buttons = NColumns(
            [urwid.Button(label, on_press=func) for label, func in buttons],
            outermost=True,
        )
        lines.append(buttons)
        content = urwid.LineBox(urwid.Pile(lines))
        overlay = urwid.Overlay(content, self, 'center', ('relative', 70), ('relative', 70), None)
        self.window.open(overlay)

    def keypress(self, size, key):
        """Handle application-wide key strokes."""
        if key in ['f1', '?']:
            self.show_keybindings()
        else:
            return super().keypress(size, key)

    def show_keybindings(self):
        lines = list()
        lines.append('  Command              Keys')
        lines.append('  =======              ====')
        for command, keys in self._conf['keybindings'].items():
            lines.append('  {:20} {}'.format(command, keys))
        lines.append('')
        lines.append("Press `Escape` to close this window")

        self.dialog('\n'.join(lines), [])


class Window(urwid.Frame):
    """The main user interface frame.

    A window is a frame which displays a header, a footer and a body.
    The header and the footer are handled by this object, and the body
    is the space where Panes can be displayed.

    Each Pane is an interface to interact with the database in one
    way: list the VCards, edit one VCard, and so on. The Window
    provides a mechanism allowing the panes to chain themselves, and
    to carry data between them.
    """

    def __init__(self, footer='', quit_keys=['q']):
        self._track = []

        header = urwid.AttrWrap(urwid.Text(''), 'header')
        footer = urwid.AttrWrap(urwid.Text(footer), 'footer')
        urwid.Frame.__init__(
            self, urwid.Text(''), header=header, footer=footer,
        )
        self.update_header()
        self._original_w = None
        self.quit_keys = quit_keys

        self._alert_daemon = AlertDaemon(self.update_header)
        self._alert_daemon.start()
        self.alert = self._alert_daemon.alert
        self.loop = None

    def open(self, pane, callback=None):
        """Open a new pane.

        The given pane is added to the track and opened. If the given
        callback is not None, it will be called when this new pane
        will be closed.
        """
        pane.window = self
        self._track.append((pane, callback))
        self._update(pane)

    def backtrack(self, data=None):
        """Unstack the displayed pane.

        The current pane is discarded, and the previous one is
        displayed. If the current pane was opened with a callback,
        this callback is called with the given data (if any) before
        the previous pane gets redrawn.
        """
        old_pane, cb = self._track.pop()
        if cb:
            cb(data)

        if self._track:
            self._update(self._get_current_pane())
        else:
            raise urwid.ExitMainLoop()

    def is_top_level(self):
        """Is the current pane the top-level one?
        """
        return len(self._track) == 1

    def on_key_press(self, key):
        """Handle application-wide key strokes."""
        if key in self.quit_keys:
            self.backtrack()
        elif key == 'esc' and not self.is_top_level():
            self.backtrack()
        return key

    def _update(self, pane):
        self.set_body(pane)
        self.update_header()

    def _get_current_pane(self):
        return self._track[-1][0] if self._track else None

    def update_header(self, alert=None):
        """Update the Windows header line.

        :param alert: additional text to show in header, additionally to
            the current title. If `alert` is a tuple, the first entry must
            be a valid palette entry
        :type alert: str or (palette_entry, str)
        """
        pane_title = getattr(self._get_current_pane(), 'title', None)
        text = []

        for part in (pane_title, alert):
            if part:
                text.append(part)
                text.append(('black', ' | '))

        self.header.w.set_text(text[:-1] or '')


class AlertDaemon(threading.Thread):
    def __init__(self, set_msg_func):
        threading.Thread.__init__(self)
        self._set_msg_func = set_msg_func
        self.daemon = True
        self._start_countdown = threading.Event()

    def alert(self, msg):
        self._set_msg_func(msg)
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
