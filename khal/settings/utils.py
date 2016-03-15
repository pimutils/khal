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

from os.path import expandvars, expanduser, join
import os

import pytz
import xdg
from tzlocal import get_localzone
from validate import VdtValueError

from ..log import logger
from .exceptions import InvalidSettingsError

from ..terminal import COLORS
from vdirsyncer.storage.filesystem import FilesystemStorage
from vdirsyncer.exceptions import CollectionNotFound


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


def weeknumber_option(option):
    """checks if *option* is a valid value

    :param option: the option the user set in the config file
    :type option: str
    :returns: off, left, right
    :rtype: str/bool
    """
    option = option.lower()
    if option == 'left':
        return 'left'
    elif option == 'right':
        return 'right'
    elif option in ['off', 'false', '0', 'no', 'none']:
        return False
    else:
        raise VdtValueError(
            "Invalid value '{}' for option 'weeknumber', must be one of "
            "'off', 'left' or 'right'".format(option))


def expand_path(path):
    """expands `~` as well as variable names"""
    return expanduser(expandvars(path))


def expand_db_path(path):
    """expands `~` as well as variable names, defaults to $XDG_DATA_HOME"""
    if path is None:
        path = join(xdg.BaseDirectory.xdg_data_home, 'khal', 'khal.db')
    return expanduser(expandvars(path))


def is_color(color):
    """checks if color represents a valid color

    raises a VdtValueError if color is not valid
    """
    # check if color is
    # 1) the default empty value
    # 2) auto
    # 3) a color name from the 16 color palette
    # 4) a color index from the 256 color palette
    # 5) a HTML-style color code
    if (color in ['', 'auto'] or
            color in COLORS.keys() or
            (color.isdigit() and int(color) >= 0 and int(color) <= 255) or
            (color.startswith('#') and (len(color) in [4, 7, 9]) and
             all(c in '01234567890abcdefABCDEF' for c in color[1:]))):
        return color
    raise VdtValueError(color)


def test_default_calendar(config):
    """test if config['default']['default_calendar'] is set to a sensible
    value
    """
    if config['default']['default_calendar'] is None:
        pass
    elif config['default']['default_calendar'] not in config['calendars']:
        logger.fatal(
            "in section [default] {} is not valid for 'default_calendar', "
            "must be one of {}".format(config['default']['default_calendar'],
                                       config['calendars'].keys())
        )
        raise InvalidSettingsError()


def get_color_from_vdir(path):
    try:
        color = FilesystemStorage(path, '.ics').get_meta('color')
    except CollectionNotFound:
        color = None
    if color is None or color is '':
        logger.debug('Found no or empty file `color` in {}'.format(path))
        color = None
    return color


def get_unique_name(path, names):
    # TODO take care of edge cases, make unique name finding less brain-dead
    name = FilesystemStorage(path, '.ics').get_meta('displayname')
    if name is None or name == '':
        logger.debug('Found no or empty file `displayname` in {}'.format(path))
        name = os.path.split(path)[-1]
    if name in names:
        while name in names:
            name = name + '1'
    return name


def get_all_vdirs(path):
    """returns (recursively) all directories under `path` that contain
    only files (not directories).
    """
    # TODO take care of links
    vdirs = list()
    contains_only_file = True
    items = os.listdir(path)
    for item in items:
        itempath = os.path.join(path, item)
        if os.path.isdir(itempath):
            contains_only_file = False
            vdirs += get_all_vdirs(itempath)
    if contains_only_file:
        vdirs.append(path)
    return vdirs


def get_vdir_type(_):
    # TODO implement
    return 'calendar'


def config_checks(config):
    """do some tests on the config we cannot do with configobj's validator"""
    if len(config['calendars'].keys()) < 1:
        logger.fatal('Found no calendar section in the config file')
        raise InvalidSettingsError()
    config['sqlite']['path'] = expand_db_path(config['sqlite']['path'])
    if not config['locale']['default_timezone']:
        config['locale']['default_timezone'] = is_timezone(
            config['locale']['default_timezone'])
    if not config['locale']['local_timezone']:
        config['locale']['local_timezone'] = is_timezone(
            config['locale']['local_timezone'])

    # expand calendars with type = discover
    vdirs = list()
    for calendar in list(config['calendars'].keys()):
        if config['calendars'][calendar]['type'] == 'discover':
            vdirs += get_all_vdirs(config['calendars'][calendar]['path'])
            config['calendars'].pop(calendar)
    for vdir in sorted(vdirs):
        calendar = {'path': vdir,
                    'color': get_color_from_vdir(vdir),
                    'type': get_vdir_type(vdir),
                    'readonly': False
                    }
        name = get_unique_name(vdir, config['calendars'].keys())
        config['calendars'][name] = calendar

    test_default_calendar(config)
    for calendar in config['calendars']:
        if config['calendars'][calendar]['type'] == 'birthdays':
            config['calendars'][calendar]['readonly'] = True
        if config['calendars'][calendar]['color'] == 'auto':
            config['calendars'][calendar]['color'] = \
                get_color_from_vdir(config['calendars'][calendar]['path'])
