# Copyright (c) 2013-2022 khal contributors
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

import datetime as dt
import glob
import logging
import os
import pathlib
from collections.abc import Iterable
from os.path import expanduser, expandvars, join
from typing import Callable, Literal, Optional, Union

import pytz
import xdg
from tzlocal import get_localzone

try:
    # Available from configobj 5.1.0
    from configobj.validate import VdtValueError
except ModuleNotFoundError:
    from validate import VdtValueError

from ..khalendar.vdir import CollectionNotFoundError, Vdir
from ..parse_datetime import guesstimedeltafstr
from ..terminal import COLORS
from .exceptions import InvalidSettingsError

logger = logging.getLogger('khal')


def is_timezone(tzstring: Optional[str]) -> dt.tzinfo:
    """tries to convert tzstring into a pytz timezone or return local timezone

    raises a VdtvalueError if tzstring is not valid
    """
    if not tzstring:
        # later version of tzlocal return zoneinfo (not pytz) timezones
        # as a lot of our other code can't deal with this yet, we need to force
        # pytz timezones for the time being
        return pytz.timezone(str(get_localzone()))
    try:
        return pytz.timezone(tzstring)
    except pytz.UnknownTimeZoneError:
        raise VdtValueError(f"Unknown timezone {tzstring}")


def is_timedelta(string: str) -> dt.timedelta:
    try:
        return guesstimedeltafstr(string)
    except ValueError:
        raise VdtValueError(f"Invalid timedelta: {string}")


def weeknumber_option(option: str) -> Union[Literal['left', 'right'], Literal[False]]:
    """checks if *option* is a valid value

    :param option: the option the user set in the config file
    :returns: 'off', 'left', 'right' or False
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
            f"Invalid value '{option}' for option 'weeknumber', must be one of "
            "'off', 'left' or 'right'")


def monthdisplay_option(option: str) -> Literal['firstday', 'firstfullweek']:
    """checks if *option* is a valid value

    :param option: the option the user set in the config file
    """
    option = option.lower()
    if option == 'firstday':
        return 'firstday'
    elif option == 'firstfullweek':
        return 'firstfullweek'
    else:
        raise VdtValueError(
            f"Invalid value '{option}' for option 'monthdisplay', must be one "
            "of 'firstday' or 'firstfullweek'"
        )


def expand_path(path: str) -> str:
    """expands `~` as well as variable names"""
    return expanduser(expandvars(path))


def expand_db_path(path: str) -> str:
    """expands `~` as well as variable names, defaults to $XDG_DATA_HOME"""
    if path is None:
        path = join(xdg.BaseDirectory.xdg_data_home, 'khal', 'khal.db')
    return expanduser(expandvars(path))


def is_color(color: str) -> str:
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


def test_default_calendar(config) -> None:
    """test if config['default']['default_calendar'] is set to a sensible
    value
    """
    if config['default']['default_calendar'] is None:
        pass
    elif config['default']['default_calendar'] not in config['calendars']:
        logger.fatal(
            f"in section [default] {config['default']['default_calendar']} is "
            "not valid for 'default_calendar', must be one of "
            f"{config['calendars'].keys()}"
        )
        raise InvalidSettingsError()
    elif config['calendars'][config['default']['default_calendar']]['readonly']:
        logger.fatal('default_calendar may not be read_only!')
        raise InvalidSettingsError()


def get_color_from_vdir(path: str) -> Optional[str]:
    try:
        color = Vdir(path, '.ics').get_meta('color')
    except CollectionNotFoundError:
        color = None
    if color is None or color == '':
        logger.debug(f'Found no or empty file `color` in {path}')
        return None
    color = color.strip()
    try:
        is_color(color)
    except VdtValueError:
        logger.warning(f"Found invalid color `{color}` in {path}color")
        color = None
    return color


def get_unique_name(path: str, names: Iterable[str]) -> str:
    # TODO take care of edge cases, make unique name finding less brain-dead
    try:
        name = Vdir(path, '.ics').get_meta('displayname')
    except CollectionNotFoundError:
        logger.fatal(f'The calendar at `{path}` is not a directory.')
        raise
    if name is None or name == '':
        logger.debug(f'Found no or empty file `displayname` in {path}')
        name = os.path.split(path)[-1]
    if name in names:
        while name in names:
            name = name + '1'
    return name


def get_all_vdirs(expand_path: str) -> Iterable[str]:
    """returns a list of paths, expanded using glob
    """
    # FIXME currently returns a list of all directories in path
    # we add an additional / at the end to make sure we are only getting
    # directories
    items = glob.glob(f'{expand_path}/', recursive=True)
    paths = [pathlib.Path(item) for item in sorted(items, key=len, reverse=True)]
    leaves = set()
    parents = set()
    for path in paths:
        if path in parents:
            # we have already seen the current directory as the parent of
            # another directory, so this directory can't be a vdir
            continue
        parents.add(path.parent)
        leaves.add(path)
    # sort to make sure that auto generated names are always identical
    return sorted(os.fspath(path) for path in leaves)


def get_vdir_type(_: str) -> str:
    # TODO implement
    return 'calendar'

def validate_palette_entry(attr, definition: str) -> bool:
    if len(definition) not in (2, 3, 5):
        logging.error('Invalid color definition for %s: %s, must be of length, 2, 3, or 5',
                      attr, definition)
        return False
    if (definition[0] not in COLORS and definition[0] != '') or \
            (definition[1] not in COLORS and definition[1] != ''):
        logging.error('Invalid color definition for %s: %s, must be one of %s',
                      attr, definition, COLORS.keys())
        return False
    return True

def config_checks(
    config,
    _get_color_from_vdir: Callable=get_color_from_vdir,
    _get_vdir_type: Callable=get_vdir_type,
) -> None:
    """do some tests on the config we cannot do with configobj's validator"""
    # TODO rename or split up, we are also expanding vdirs of type discover
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
    # we need a copy of config['calendars'], because we modify config in the body of the loop
    for cname, cconfig in sorted(config['calendars'].items()):
        if not isinstance(config['calendars'][cname], dict):
            logger.fatal('Invalid config file, probably missing calendar sections')
            raise InvalidSettingsError
        if config['calendars'][cname]['type'] == 'discover':
            logger.debug(f"discovering calendars in {cconfig['path']}")
            vdirs_discovered = get_all_vdirs(cconfig['path'])
            logger.debug(f"found the following vdirs: {vdirs_discovered}")
            for vdir in vdirs_discovered:
                vdir_config = {
                    'path': vdir,
                    'color': _get_color_from_vdir(vdir) or cconfig.get('color', None),
                    'type': _get_vdir_type(vdir),
                    'readonly': cconfig.get('readonly', False),
                    'priority': 10,
                }
                unique_vdir_name = get_unique_name(vdir, config['calendars'].keys())
                config['calendars'][unique_vdir_name] = vdir_config
            config['calendars'].pop(cname)

    test_default_calendar(config)
    for calendar in config['calendars']:
        if config['calendars'][calendar]['type'] == 'birthdays':
            config['calendars'][calendar]['readonly'] = True
        if config['calendars'][calendar]['color'] == 'auto':
            config['calendars'][calendar]['color'] = \
                _get_color_from_vdir(config['calendars'][calendar]['path'])

    # check palette settings
    valid_palette = True
    for attr in config.get('palette', []):
        valid_palette = valid_palette and validate_palette_entry(attr, config['palette'][attr])
    if not valid_palette:
        logger.fatal('Invalid palette entry')
        raise InvalidSettingsError()
