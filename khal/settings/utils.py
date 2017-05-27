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
#

from os.path import expandvars, expanduser, join
import os
import glob

import pytz
import xdg
from tzlocal import get_localzone
from validate import VdtValueError

from ..log import logger
from .exceptions import InvalidSettingsError

from ..terminal import COLORS
from ..khalendar.vdir import Vdir, CollectionNotFoundError
from ..utils import guesstimedeltafstr


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


def is_timedelta(string):
    try:
        return guesstimedeltafstr(string)
    except ValueError:
        raise VdtValueError("Invalid timedelta: {}".format(string))


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
    # 5) an HTML-style color code
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
    elif config['calendars'][config['default']['default_calendar']]['readonly']:
        logger.fatal('default_calendar may not be read_only!')
        raise InvalidSettingsError()


def get_color_from_vdir(path):
    try:
        color = Vdir(path, '.ics').get_meta('color')
    except CollectionNotFoundError:
        color = None
    if color is None or color is '':
        logger.debug('Found no or empty file `color` in {}'.format(path))
        return None
    color = color.strip()
    try:
        is_color(color)
    except VdtValueError:
        logger.warning("Found invalid color `{}` in {}color".format(color, path))
        color = None
    return color


def get_unique_name(path, names):
    # TODO take care of edge cases, make unique name finding less brain-dead
    name = Vdir(path, '.ics').get_meta('displayname')
    if name is None or name == '':
        logger.debug('Found no or empty file `displayname` in {}'.format(path))
        name = os.path.split(path)[-1]
    if name in names:
        while name in names:
            name = name + '1'
    return name


def get_all_vdirs(path):
    """returns a list of paths, expanded using glob
    """
    items = glob.glob(path)
    return items


def get_vdir_type(_):
    # TODO implement
    return 'calendar'


def config_checks(
        config,
        _get_color_from_vdir=get_color_from_vdir,
        _get_vdir_type=get_vdir_type):
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
    vdirs_complete = list()
    vdir_colors_from_config = {}
    for calendar in list(config['calendars'].keys()):
        if config['calendars'][calendar]['type'] == 'discover':
            logger.debug(
                'discovering calendars in {}'.format(config['calendars'][calendar]['path'])
            )
            vdirs = get_all_vdirs(config['calendars'][calendar]['path'])
            vdirs_complete += vdirs
            if 'color' in config['calendars'][calendar]:
                for vdir in vdirs:
                    vdir_colors_from_config[vdir] = config['calendars'][calendar]['color']
            config['calendars'].pop(calendar)
    for vdir in sorted(vdirs_complete):
        calendar = {'path': vdir,
                    'color': _get_color_from_vdir(vdir),
                    'type': _get_vdir_type(vdir),
                    'readonly': False
                    }

        # get color from config if not defined in vdir

        if calendar['color'] is None and vdir in vdir_colors_from_config:
            logger.debug("using collection's color for {}".format(vdir))
            calendar['color'] = vdir_colors_from_config[vdir]

        name = get_unique_name(vdir, config['calendars'].keys())
        config['calendars'][name] = calendar

    test_default_calendar(config)
    for calendar in config['calendars']:
        if config['calendars'][calendar]['type'] == 'birthdays':
            config['calendars'][calendar]['readonly'] = True
        if config['calendars'][calendar]['color'] == 'auto':
            config['calendars'][calendar]['color'] = \
                _get_color_from_vdir(config['calendars'][calendar]['path'])
