# Copyright (c) 2013-2016 Christian Geier et al.
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

from collections import namedtuple
from itertools import zip_longest


NamedColor = namedtuple('NamedColor', ['index', 'light'])

RTEXT = '\x1b[7m'  # reverse
NTEXT = '\x1b[0m'  # normal
BTEXT = '\x1b[1m'  # bold
RESET = '\33[0m'
COLORS = {
    'black': NamedColor(index=0, light=False),
    'dark red': NamedColor(index=1, light=False),
    'dark green': NamedColor(index=2, light=False),
    'brown': NamedColor(index=3, light=False),
    'dark blue': NamedColor(index=4, light=False),
    'dark magenta': NamedColor(index=5, light=False),
    'dark cyan': NamedColor(index=6, light=False),
    'white': NamedColor(index=7, light=False),
    'light gray': NamedColor(index=7, light=True),
    'dark gray': NamedColor(index=0, light=True),  # actually light black
    'light red': NamedColor(index=1, light=True),
    'light green': NamedColor(index=2, light=True),
    'yellow': NamedColor(index=3, light=True),
    'light blue': NamedColor(index=4, light=True),
    'light magenta': NamedColor(index=5, light=True),
    'light cyan': NamedColor(index=6, light=True)
}


def colored(string, fg=None, bg=None, bold_for_light_color=True):
    result = ''
    for colorstring, is_bg in ((fg, False), (bg, True)):
        if colorstring:
            color = '\33['
            if colorstring in COLORS:
                # 16 color palette
                if not is_bg:
                    # foreground color
                    c = 30 + COLORS[colorstring].index
                    if COLORS[colorstring].light:
                        if bold_for_light_color:
                            color += '1;'
                        else:
                            c += 60
                else:
                    # background color
                    c = 40 + COLORS[colorstring].index
                    if COLORS[colorstring].light:
                        if not bold_for_light_color:
                            c += 60
                color += str(c)
            elif colorstring.isdigit():
                # 256 color palette
                if not is_bg:
                    color += '38;5;' + colorstring
                else:
                    color += '48;5;' + colorstring
            else:
                # HTML-style 24-bit color
                if len(colorstring) == 4:
                    # e.g. #ABC, equivalent to #AABBCC
                    r = int(colorstring[1] * 2, 16)
                    g = int(colorstring[2] * 2, 16)
                    b = int(colorstring[3] * 2, 16)
                else:
                    # e.g. #AABBCC
                    r = int(colorstring[1:3], 16)
                    g = int(colorstring[3:5], 16)
                    b = int(colorstring[5:7], 16)
                if not is_bg:
                    color += '38;2;{!s};{!s};{!s}'.format(r, g, b)
                else:
                    color += '48;2;{!s};{!s};{!s}'.format(r, g, b)
            color += 'm'
            result += color
    result += string
    if fg or bg:
        result += RESET
    return result


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
