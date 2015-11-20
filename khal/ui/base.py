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


import urwid
import threading
import time


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

    @property
    def description(self):
        return self._description

    def get_keys(self):
        """Return a description of the keystrokes recognized by this pane.

        This method returns a list of tuples describing the keys
        handled by a pane. This list is used to build a contextual
        pane help. Each tuple is a pair of a list of keys and a
        description.

        The abstract pane returns the default keys handled by the
        window. Panes which do not override these keys should extend
        this list.
        """
        return [(['up', 'down', 'pg.up', 'pg.down'],
                 'navigate through the fields.'),
                (['esc'], 'backtrack to the previous pane or exit.'),
                (['F1', '?'], 'open this pane help.')]


class HelpPane(Pane):

    """A contextual help screen."""

    def __init__(self, pane):
        content = []
        for key_list, description in pane.get_keys():
            key_text = []
            for key in key_list:
                if key_text:
                    key_text.append(', ')
                key_text.append(('bright', key))
            content.append(
                urwid.Columns(
                    [urwid.Padding(urwid.Text(key_text), left=10),
                     urwid.Padding(urwid.Text(description), right=10)]))

        Pane.__init__(self, urwid.ListBox(urwid.SimpleListWalker(content)),
                      'Help')


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

    def __init__(self, footer=''):
        self._track = []

        header = urwid.AttrWrap(urwid.Text(''), 'header')
        footer = urwid.AttrWrap(urwid.Text(footer), 'footer')
        urwid.Frame.__init__(self, urwid.Text(''),
                             header=header,
                             footer=footer)
        self.update_header()
        self._original_w = None

        self._alert_daemon = AlertDaemon(self.update_header)
        self._alert_daemon.start()
        self.alert = self._alert_daemon.alert

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

    def on_key_press(self, key):
        """Handle application-wide key strokes."""
        if key in ['esc', 'q']:
            self.backtrack()
        elif key in ['f1', '?']:
            self.open(HelpPane(self._get_current_pane()))

    def _update(self, pane):
        self.set_body(pane)
        self.update_header()

    def _get_current_pane(self):
        return self._track[-1][0] if self._track else None

    def update_header(self, alert=None):
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


class Choice(urwid.PopUpLauncher):
    def __init__(self, choices, active, decorate_func=None):
        self.choices = choices
        self._decorate = decorate_func or (lambda x: x)
        self.active = self._original = active

    def create_pop_up(self):
        pop_up = ChoiceList(self)
        urwid.connect_signal(pop_up, 'close',
                             lambda button: self.close_pop_up())
        return pop_up

    def get_pop_up_parameters(self):
        return {'left': 0,
                'top': 1,
                'overlay_width': 32,
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
        urwid.connect_signal(self.button, 'click',
                             lambda button: self.open_pop_up())


class ChoiceList(urwid.WidgetWrap):
    signals = ['close']

    def __init__(self, parent):
        self.parent = parent
        buttons = []
        for c in parent.choices:
            buttons.append(
                urwid.Button(parent._decorate(c),
                             on_press=self.set_choice, user_data=c)
            )

        pile = urwid.Pile(buttons)
        fill = urwid.Filler(pile)
        urwid.WidgetWrap.__init__(self, urwid.AttrMap(fill, 'popupbg'))

    def set_choice(self, button, account):
        self.parent.active = account
        self._emit("close")
