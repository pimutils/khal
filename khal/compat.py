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

import sys


def to_unicode(string, *args, **kwargs):
    if not isinstance(string, unicode_type):
        return string.decode(*args, **kwargs)
    return string


def to_bytes(string, *args, **kwargs):
    if not isinstance(string, bytes_type):
        return string.encode(*args, **kwargs)
    return string


if sys.version_info[0] == 2:  # pragma: nocover
    VERSION = 2
    unicode_type = unicode  # NOQA
    bytes_type = str
    to_native = to_bytes

    def iteritems(d, *args, **kwargs):
        return iter(d.iteritems(*args, **kwargs))
else:  # pragma: nocover
    VERSION = 3
    unicode_type = str
    bytes_type = bytes
    to_native = to_unicode

    def iteritems(d, *args, **kwargs):
        return iter(d.items(*args, **kwargs))
