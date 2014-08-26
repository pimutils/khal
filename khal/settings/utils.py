# vim: set ts=4 sw=4 expandtab sts=4 fileencoding=utf-8:
# Copyright (c) 2013-2014 Christian Geier et al.
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

from os.path import expandvars, expanduser, join

import pytz
import xdg
from tzlocal import get_localzone
from validate import VdtValueError


def is_timezone(tzstring):
    """tries to convert tzstring into a pytz timezone

    raises a VdtvalueError if tzstring is not valid
    """
    if not tzstring:
        return get_localzone()
    try:
        return pytz.timezone(tzstring)
    except pytz.UnknownTimeZoneError:
        raise VdtValueError("Unknown timezone {}".format(tzstring))


def expand_path(path):
    """expands `~` as well as variable names"""
    return expanduser(expandvars(path))


def expand_db_path(path):
    """expands `~` as well as variable names, defaults to $XDG_DATA_HOME"""
    if path is None:
        path = join(xdg.BaseDirectory.xdg_data_home, 'khal', 'khal.db')
    return expanduser(expandvars(path))


def test_default_calendar(config):
    """test if config['default']['default_calendar'] is set to a sensible
    value
    """
    if config['default']['default_calendar'] is None:
        config['default']['default_calendar'] = config['calendars'].keys()[0]
    elif config['default']['default_calendar'] not in config['calendars']:
        print("in section [default] {} is not valid for 'default_calendar', "
              "must be one of {}".format(config['default']['default_calendar'],
                                         config['calendars'].keys())
              )
        raise ValueError  # TODO own error class


def config_checks(config):
    """do some tests on the config we cannot do with configobj's validator"""
    if len(config['calendars'].keys()) < 1:
        raise ValueError('Found no calendar in the config file')
    test_default_calendar(config)
    config['sqlite']['path'] = expand_db_path(config['sqlite']['path'])
    if not config['locale']['default_timezone']:
        config['locale']['default_timezone'] = is_timezone(
            config['locale']['default_timezone'])
    if not config['locale']['local_timezone']:
        config['locale']['local_timezone'] = is_timezone(
            config['locale']['local_timezone'])
