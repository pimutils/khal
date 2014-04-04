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

"""all functions related to terminal display are collected here"""

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


def rstring(string):
    """returns string as reverse color string (ANSI escape codes)

    >>> rstring('test')
    '\\x1b[7mtest\\x1b[0m'
    """
    return RTEXT + string + NTEXT


def bstring(string):
    """returns string as bold string (ANSI escape codes)
    >>> bstring('test')
    '\\x1b[1mtest\\x1b[0m'
    """
    return BTEXT + string + NTEXT


def colored(string, colorstring):
    try:
        color = COLORS[colorstring]
    except KeyError:
        color = ''
    return color + string + RESET
