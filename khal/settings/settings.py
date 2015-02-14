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

import os

from configobj import ConfigObj, flatten_errors, get_extra_values, \
    ConfigObjError
from validate import Validator
import xdg.BaseDirectory

from .exceptions import InvalidSettingsError, CannotParseConfigFileError
from khal import __productname__
from ..log import logger
from .utils import is_timezone, weeknumber_option, config_checks, \
    expand_path, expand_db_path

SPECPATH = os.path.join(os.path.dirname(__file__), 'khal.spec')


def _find_configuration_file():
    """Return the configuration filename.

    This function builds the list of paths known by khal and
    then return the first one which exists. The first paths
    searched are the ones described in the XDG Base Directory
    Standard. Each one of this path ends with
    DEFAULT_PATH/DEFAULT_FILE.

    On failure, the path DEFAULT_PATH/DEFAULT_FILE, prefixed with
    a dot, is searched in the home user directory. Ultimately,
    DEFAULT_FILE is searched in the current directory.
    """
    DEFAULT_FILE = __productname__ + '.conf'
    DEFAULT_PATH = __productname__
    resource = os.path.join(DEFAULT_PATH, DEFAULT_FILE)

    paths = []
    paths.extend([os.path.join(path, resource)
                  for path in xdg.BaseDirectory.xdg_config_dirs])
    paths.append(os.path.expanduser(os.path.join('~', '.' + resource)))
    paths.append(os.path.expanduser(DEFAULT_FILE))

    for path in paths:
        if os.path.exists(path):
            return path

    return None


def get_config(config_path=None):
    """reads the config file, validates it and return a config dict

    :param config_path: path to a custom config file, if none is given the
                        default locations will be searched
    :type config_path: str
    :returns: configuration
    :rtype: dict
    """
    if config_path is None:
        config_path = _find_configuration_file()

    logger.debug('using the config file at {}'.format(config_path))

    try:
        user_config = ConfigObj(config_path,
                                configspec=SPECPATH,
                                interpolation=False,
                                file_error=True,
                                )
    except ConfigObjError as error:
        logger.fatal('parsing the config file file with the following error: '
                     '{}'.format(error))
        logger.fatal('if you recently updated khal, the config file format '
                     'might have changed, in that case please consult the '
                     'CHANGELOG or other documentation')
        raise CannotParseConfigFileError()

    fdict = {'timezone': is_timezone,
             'expand_path': expand_path,
             'expand_db_path': expand_db_path,
             'weeknumbers': weeknumber_option,
             }
    validator = Validator(fdict)
    results = user_config.validate(validator, preserve_errors=True)

    abort = False
    for section, subsection, error in flatten_errors(user_config, results):
        abort = True
        if isinstance(error, Exception):
            logger.fatal(
                'config error:\n'
                'in [{}] {}: {}'.format(section[0], subsection, error))
        else:
            for key in error:
                if isinstance(error[key], Exception):
                    logger.fatal('config error:\nin {} {}: {}'.format(
                        sectionize(section + [subsection]),
                        key,
                        str(error[key]))
                    )

    if abort or not results:
        raise InvalidSettingsError()

    config_checks(user_config)

    extras = get_extra_values(user_config)
    for section, value in extras:
        if section == ():
            logger.warn('unknown section "{}" in config file'.format(value))
        else:
            section = sectionize(section)
            logger.warn('unknown key or subsection "{}" in '
                        'section "{}"'.format(value, section))
    return user_config


def sectionize(sections, depth=1):
    """converts list of string into [list][[of]][[[strings]]]"""
    this_part = depth * '[' + sections[0] + depth * ']'
    if len(sections) > 1:
        return this_part + sectionize(sections[1:], depth=depth + 1)
    else:
        return this_part
