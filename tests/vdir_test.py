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

import os
import time

import pytest
from khal.khalendar import vdir


@pytest.mark.xfail
def test_etag(tmpdir):
    fpath = os.path.join(str(tmpdir), 'foo')

    file_ = open(fpath, 'w')
    file_.write('foo')
    file_.close()

    old_etag = vdir.get_etag_from_file(fpath)

    file_ = open(fpath, 'w')
    file_.write('foo')
    file_.close()

    new_etag = vdir.get_etag_from_file(fpath)

    try:
        assert old_etag != new_etag
    except AssertionError:
        pytest.xfail(
            "Do we need to sleep?"
        )


def test_etag_sync(tmpdir):
    fpath = os.path.join(str(tmpdir), 'foo')

    file_ = open(fpath, 'w')
    file_.write('foo')
    file_.close()
    os.sync()

    old_etag = vdir.get_etag_from_file(fpath)

    file_ = open(fpath, 'w')
    file_.write('foo')
    file_.close()

    new_etag = vdir.get_etag_from_file(fpath)

    assert old_etag != new_etag


def test_etag_sleep(tmpdir, sleep_time):
    fpath = os.path.join(str(tmpdir), 'foo')

    file_ = open(fpath, 'w')
    file_.write('foo')
    file_.close()

    old_etag = vdir.get_etag_from_file(fpath)
    time.sleep(sleep_time)

    file_ = open(fpath, 'w')
    file_.write('foo')
    file_.close()

    new_etag = vdir.get_etag_from_file(fpath)

    assert old_etag != new_etag
