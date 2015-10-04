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
#
"""all functions related to terminal display are collected here"""

try:
    from itertools import izip_longest as zip_longest
except ImportError:
    from itertools import zip_longest

try:
    # python 3.3+
    import shutil.get_terminal_size as get_terminal_size
except ImportError:
    def get_terminal_size():
        import fcntl
        import struct
        import termios
        try:
            h, w, hp, wp = struct.unpack(
                'HHHH',
                fcntl.ioctl(0, termios.TIOCGWINSZ,
                            struct.pack('HHHH', 0, 0, 0, 0)))
        except IOError:
            w, h = 80, 24
        return w, h

RTEXT = '\x1b[7m'  # reverse
NTEXT = '\x1b[0m'  # normal
BTEXT = '\x1b[1m'  # bold
RESET = '\33[0m'
COLORS = {
    'black': '\33[30m',
    'dark red': '\33[31m',
    'dark green': '\33[32m',
    'brown': '\33[33m',
    'dark blue': '\33[34m',
    'dark magenta': '\33[35m',
    'dark cyan': '\33[36m',
    'white': '\33[37m',
    'light grey': '\33[1;37m',
    'dark grey': '\33[1;30m',
    'light red': '\33[1;31m',
    'light green': '\33[1;32m',
    'yellow': '\33[1;33m',
    'light blue': '\33[1;34m',
    'light magenta': '\33[1;35m',
    'light cyan': '\33[1;36m'
}


def colored(string, colorstring):
    try:
        color = COLORS[colorstring]
    except KeyError:
        color = ''
    return color + string + (RESET if color else '')


def merge_columns(lcolumn, rcolumn, width=25):
    """merge two lists elementwise together

    Wrap right columns to terminal width.
    If the right list(column) is longer, first lengthen the left one.
    We assume that the left column has width `width`, we cannot find
    out its (real) width automatically since it might contain ANSI
    escape sequences.
    """

    missing = len(rcolumn) - len(lcolumn)
    if missing > 0:
        lcolumn = lcolumn + missing * [width * ' ']

    rows = ['    '.join(one) for one in zip_longest(
        lcolumn, rcolumn, fillvalue='')]
    return rows


def urwid_to_click(color):
    """convert urwid color name to click color name
    """
    col = color.split()[-1]
    if col == 'brown':
        return 'yellow'
    return col


def urwid_to_click_bold(color):
    """convert urwid color name to click bold attribute
    """
    col = color.split()[0]
    if col == 'brown':
        return False
    return col == 'light' or col == 'yellow'
