# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2011-2014 Christian Geier & contributors
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


def vimify(key):
    if key == 'h':
        return 'left'
    elif key == 'j':
        return 'down'
    elif key == 'k':
        return 'up'
    elif key == 'l':
        return 'right'
    # not really sure if these last to make any sense (not yet at least)
    # at least for the time being, they are more trouble, than they are worth
    # elif key == '0':
        # return 'home'
    # elif key == '$':
        # return 'end'
    else:
        return key


class CColumns(urwid.Columns):

    def keypress(self, size, key):
        # key = vimify(key)
        return urwid.Columns.keypress(self, size, key)


class CPile(urwid.Pile):

    def keypress(self, size, key):
        # key = vimify(key)
        return urwid.Pile.keypress(self, size, key)


class CSimpleFocusListWalker(urwid.SimpleFocusListWalker):

    def keypress(self, size, key):
        # key = vimify(key)
        return urwid.SimpleFocusListWalker.keypress(self, size, key)


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
    PALETTE = [('header', 'white', 'black'),
               ('footer', 'white', 'black'),
               ('line header', 'black', 'white', 'bold'),
               ('bright', 'dark blue', 'white', ('bold', 'standout')),
               ('list', 'black', 'white'),
               ('list focused', 'white', 'light blue', 'bold'),
               ('edit', 'black', 'white'),
               ('edit focused', 'white', 'light blue', 'bold'),
               ('button', 'black', 'dark cyan'),
               ('button focused', 'white', 'light blue', 'bold'),
               ('reveal focus', 'black', 'dark cyan', 'standout'),
               ('today_focus', 'white', 'black', 'standout'),
               ('today', 'black', 'white', 'dark cyan'),
               ('edit', 'white', 'dark blue'),
               ('alert', 'white', 'dark red'),

               ('editfc', 'white', 'dark blue', 'bold'),
               ('editbx', 'light gray', 'dark blue'),
               ('editcp', 'black', 'light gray', 'standout'),
               ('popupbg', 'white', 'black', 'bold'),

               ('black', 'black', ''),
               ('dark red', 'dark red', ''),
               ('dark green', 'dark green', ''),
               ('brown', 'brown', ''),
               ('dark blue', 'dark blue', ''),
               ('dark magenta', 'dark magenta', ''),
               ('dark cyan', 'dark cyan', ''),
               ('light gray', 'light gray', ''),
               ('dark gray', 'dark gray', ''),
               ('light red', 'light red', ''),
               ('light green', 'light green', ''),
               ('yellow', 'yellow', ''),
               ('light blue', 'light blue', ''),
               ('light magenta', 'light magenta', ''),
               ('light cyan', 'light cyan', ''),
               ('white', 'white', ''),
               ]

    def __init__(self, header='', footer=''):
        self._track = []
        self._title = header
        self._footer = footer

        header = urwid.AttrWrap(urwid.Text(self._title), 'header')
        footer = urwid.AttrWrap(urwid.Text(self._footer), 'footer')
        urwid.Frame.__init__(self, urwid.Text(''),
                             header=header,
                             footer=footer)
        self._original_w = None

    def open(self, pane, callback=None):
        """Open a new pane.

        The given pane is added to the track and opened. If the given
        callback is not None, it will be called when this new pane
        will be closed.
        """
        pane.window = self
        self._track.append((pane, callback))
        self._update(pane)

    def overlay(self, overlay_w, title):
        """put overlay_w as an overlay over the currently active pane
        """
        overlay = Pane(urwid.Overlay(urwid.Filler(overlay_w),
                                     self._get_current_pane(),
                                     'center', 60,
                                     'middle', 5), title)
        self.open(overlay)

    def backtrack(self, data=None):
        """Unstack the displayed pane.

        The current pane is discarded, and the previous one is
        displayed. If the current pane was opened with a callback,
        this callback is called with the given data (if any) before
        the previous pane gets redrawn.
        """
        _, cb = self._track.pop()
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
        self.header.w.set_text(u'%s | %s' % (self._title, pane.title))
        self.set_body(pane)

    def _get_current_pane(self):
        return self._track[-1][0] if self._track else None
