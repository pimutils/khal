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

from click import confirm, prompt, UsageError
import xdg

from functools import partial
from itertools import zip_longest
from os.path import expanduser, expandvars, join, normpath, exists, isdir
from os import makedirs

from datetime import date, datetime

from khal.log import logger
from .exceptions import FatalError
from .settings import settings


def validate_int(input, min_value, max_value):
    try:
        number = int(input)
    except ValueError:
        raise UsageError('Input must be an integer')
    if min_value <= number <= max_value:
        return number
    else:
        raise UsageError('Input must be between {} and {}'.format(min_value, max_value))


DATE_FORMAT_INFO = [
    ('Year', ['%Y', '%y']),
    ('Month', ['%m', '%B', '%b']),
    ('Day', ['%d', '%a', '%A'])
]


def present_date_format_info(example_date):
    columns = []
    widths = []
    for title, formats in DATE_FORMAT_INFO:
        newcol = [title]
        for f in formats:
            newcol.append('{}={}'.format(f, example_date.strftime(f)))
        widths.append(max(len(s) for s in newcol) + 2)
        columns.append(newcol)

    print('Common fields for date formatting:')
    for row in zip_longest(*columns, fillvalue=''):
        print(''.join(s.ljust(w) for (s, w) in zip(row, widths)))

    print('More info: '
          'https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior')


def choose_datetime_format():
    """query user for their date format of choice"""
    choices = [
        ('year-month-day', '%Y-%m-%d'),
        ('day/month/year', '%d/%m/%Y'),
        ('month/day/year', '%m/%d/%Y'),
    ]
    validate = partial(validate_int, min_value=0, max_value=3)
    today = date.today()
    print("What ordering of year, month, date do you want to use?")
    for num, (desc, fmt) in enumerate(choices):
        print('[{}] {} (today: {})'.format(num, desc, today.strftime(fmt)))
    print('[3] Custom')
    choice_no = prompt("Please choose one of the above options", value_proc=validate)
    if choice_no == 3:
        present_date_format_info(today)
        dateformat = prompt('Make your date format')
    else:
        dateformat = choices[choice_no][1]
    print("Date format: {} "
          "(today as an example: {})".format(dateformat, today.strftime(dateformat)))
    return dateformat


def choose_time_format():
    """query user for their time format of choice"""
    choices = ['%H:%M', '%I:%M %p']
    print("What timeformat do you want to use?")
    print("[0] 24 hour clock (recommended)\n[1] 12 hour clock")
    validate = partial(validate_int, min_value=0, max_value=1)
    prompt_text = "Please choose one of the above options"
    timeformat = choices[prompt(prompt_text, default=0, value_proc=validate)]
    now = datetime.now()
    print("Time format: {} "
          "(current time as an example: {})".format(timeformat, now.strftime(timeformat)))
    return timeformat


def get_vdirs_from_vdirsyncer_config():
    """trying to load vdirsyncer's config and read all vdirs from it"""
    print("If you use vdirsyncer to sync with CalDAV servers, we can try to "
          "load its config file and add your calendars to khal's config.")
    if not confirm("Should we try to load vdirsyncer's config?", default='y'):
        return None
    try:
        from vdirsyncer.cli import config
        from vdirsyncer.exceptions import UserError
    except ImportError:
        print("Sorry, cannot import vdirsyncer. Please make sure you have it "
              "installed.")
        return None
    try:
        vdir_config = config.load_config()
    except UserError as error:
        print("Sorry, trying to load vdirsyncer failed with the following "
              "error message:")
        print(error)
        return None
    vdirs = list()
    for storage in vdir_config.storages.values():
        if storage['type'] == 'filesystem':
            # TODO detect type of storage properly
            path = storage['path']
            if path[-1] != '/':
                path += '/'
            path += '*'
            vdirs.append((storage['instance_name'], path, 'discover'))
    if vdirs == list():
        print("No usable collections were found")
        return None
    else:
        print("The following collections were found:")
        for name, path, _ in vdirs:
            print('  {}: {}'.format(name, path))
        return vdirs


def create_vdir(names=[]):
    if not confirm("Do you want to create a local calendar? (You can always "
                   "set it up to synchronize with a server in vdirsyncer "
                   "later)."):
        return None
    name = 'private'
    while True:
        path = join(xdg.BaseDirectory.xdg_data_home, 'khal', 'calendars', name)
        path = normpath(expanduser(expandvars(path)))
        if name not in names and not exists(path):
            break
        else:
            name += '1'
    try:
        makedirs(path)
    except OSError as error:
        print("Could not create directory {} because of {}. Exiting".format(path, error))
        raise
    print("Created new vdir at {}".format(path))
    return [(name, path, 'calendar')]


def create_config(vdirs, dateformat, timeformat):
    config = ['[calendars]']
    for name, path, type_ in sorted(vdirs or ()):
        config.append('\n[[{name}]]'.format(name=name))
        config.append('path = {path}'.format(path=path))
        config.append('type = {type}'.format(type=type_))

    config.append('\n[locale]')
    config.append('timeformat = {timeformat}\n'
                  'dateformat = {dateformat}\n'
                  'longdateformat = {longdateformat}\n'
                  'datetimeformat = {dateformat} {timeformat}\n'
                  'longdatetimeformat = {longdateformat} {timeformat}\n'
                  .format(timeformat=timeformat,
                          dateformat=dateformat,
                          longdateformat=dateformat))

    config = '\n'.join(config)
    return config


def configwizard():
    config_file = settings.find_configuration_file()
    if config_file is not None:
        logger.fatal("Found an existing config file at {}.".format(config_file))
        logger.fatal(
            "If you want to create a new configuration file, "
            "please remove the old one first. Exiting.")
        raise FatalError()
    dateformat = choose_datetime_format()
    print()
    timeformat = choose_time_format()
    print()
    vdirs = get_vdirs_from_vdirsyncer_config()
    print()
    if not vdirs:
        try:
            vdirs = create_vdir()
        except OSError as error:
            raise FatalError(error)

    if not vdirs:
        print("\nWARNING: no vdir configured, khal will not be usable like this!\n")

    config = create_config(vdirs, dateformat=dateformat, timeformat=timeformat)
    config_path = join(xdg.BaseDirectory.xdg_config_home, 'khal', 'config')
    if not confirm(
            "Do you want to write the config to {}? "
            "(Choosing `No` will abort)".format(config_path), default=True):
        raise FatalError('User aborted...')
    config_dir = join(xdg.BaseDirectory.xdg_config_home, 'khal')
    if not exists(config_dir) and not isdir(config_dir):
        try:
            makedirs(config_dir)
        except OSError as error:
            print(
                "Could not write config file at {} because of {}. "
                "Aborting".format(config_dir, error)
            )
            raise FatalError(error)
        else:
            print('created directory {}'.format(config_dir))
    with open(config_path, 'w') as config_file:
        config_file.write(config)
    print("Successfully wrote configuration to {}".format(config_path))
