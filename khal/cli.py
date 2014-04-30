#!/usr/bin/env python2
# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:
# Copyright (c) 2013-2014 Christian Geier & contributors
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
import datetime
import logging
import os
import re
import sys
import textwrap

try:
    from ConfigParser import RawConfigParser
    from ConfigParser import SafeConfigParser
    from ConfigParser import Error as ConfigParserError

except ImportError:
    from configparser import RawConfigParser
    from configparser import SafeConfigParser
    from configparser import Error as ConfigParserError

try:
    from setproctitle import setproctitle
except ImportError:
    setproctitle = lambda x: None

import argvard
import pytz
import xdg

from khal import ConfigurationParser
from khal import controllers
from khal import capture_user_interruption
from khal import khalendar


from khal import aux, calendar_display
from khal import __version__, __productname__
from .terminal import bstring, colored, get_terminal_size, merge_columns


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
    paths.append(os.path.expanduser(ConfigurationParser.DEFAULT_FILE))

    for path in paths:
        if os.path.exists(path):
            return path

    return None


class Namespace(dict):

    """The khal configuration holder.

    Mostly taken from pycarddav.

    This holder is a dict subclass that exposes its items as attributes.
    Inspired by NameSpace from argparse, Configuration is a simple
    object providing equality by attribute names and values, and a
    representation.

    Warning: Namespace instances do not have direct access to the dict
    methods. But since it is a dict object, it is possible to call
    these methods the following way: dict.get(ns, 'key')

    See http://code.activestate.com/recipes/577887-a-simple-namespace-class/
    """

    def __init__(self, obj=None):
        dict.__init__(self, obj if obj else {})

    def __dir__(self):
        return list(self)

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, dict.__repr__(self))

    def __getattribute__(self, name):
        try:
            return self[name]
        except KeyError:
            msg = "'%s' object has no attribute '%s'"
            raise AttributeError(msg % (type(self).__name__, name))

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        del self[name]


class Section(object):

    READERS = {bool: SafeConfigParser.getboolean,
               float: SafeConfigParser.getfloat,
               int: SafeConfigParser.getint,
               str: SafeConfigParser.get}

    def __init__(self, parser, group):
        self._parser = parser
        self._group = group
        self._schema = None
        self._parsed = {}

    def matches(self, name):
        return self._group == name.lower()

    def is_collection(self):
        return False

    def parse(self, section):
        failed = False
        if self._schema is None:
            return None

        for option, default, filter_ in self._schema:
            if filter_ is None:
                filter_ = lambda x: x
            try:
                self._parsed[option] = filter_(
                    self._parser.get(section, option)
                )
                self._parser.remove_option(section, option)
            except ConfigParserError:
                if default is None:
                    logging.error(
                        "Missing required option '{option}' in section "
                        "'{section}'".format(option=option, section=section))
                    failed = True
                self._parsed[option] = default
                # Remove option once handled (see the check function).
                self._parser.remove_option(section, option)
            except ConfigParserError:
                self._parsed[option] = default

        if failed:
            return None
        else:
            return Namespace(self._parsed)

    @property
    def group(self):
        return self._group

    def _parse_bool_string(self, value):
        """if value is either 'True' or 'False' it returns that value as a
        bool, otherwise it returns the value"""
        value = value.strip().lower()
        if value in ['true', 'yes', '1']:
            return True
        else:
            return False

    def _parse_time_zone(self, value):
        """returns pytz timezone"""
        return pytz.timezone(value)


class CalendarSection(Section):

    def __init__(self, parser):
        Section.__init__(self, parser, 'calendars')
        self._schema = [
            ('path', None, os.path.expanduser),
            ('readonly', False, None),
            ('color', '', None)
        ]

    def is_collection(self):
        return True

    def matches(self, name):
        match = re.match('calendar (?P<name>.*)', name, re.I)
        if match:
            self._parsed['name'] = match.group('name')
        return match is not None


class SQLiteSection(Section):

    def __init__(self, parser):
        Section.__init__(self, parser, 'sqlite')
        self._schema = [
            ('path', ConfigurationParser.DEFAULT_DB_PATH, os.path.expanduser),
        ]


class LocaleSection(Section):
    def __init__(self, parser):
        Section.__init__(self, parser, 'locale')
        self._schema = [
            ('local_timezone', None, self._parse_time_zone),
            ('default_timezone', None, self._parse_time_zone),
            ('timeformat', None, None),
            ('dateformat', None, None),
            ('longdateformat', None, None),
            ('datetimeformat', None, None),
            ('longdatetimeformat', None, None),
            ('firstweekday', 0, lambda x: x)
        ]


class DefaultSection(Section):
    def __init__(self, parser):
        Section.__init__(self, parser, 'default')
        self._schema = [
            ('debug', False, None),
            ('encoding', 'utf-8', None),
            ('unicode_symbols', 'True', self._parse_bool_string),
        ]


class ConfigParser(object):
    _sections = [
        DefaultSection, LocaleSection, SQLiteSection, CalendarSection
    ]

    _required_sections = [DefaultSection, LocaleSection, CalendarSection]

    def __init__(self):
        pass

    def _get_section_parser(self, section):
        for cls in self._sections:
            parser = cls(self._conf_parser)
            if parser.matches(section):
                return parser
        return None

    def parse_config(self, cfile):
        self._conf_parser = RawConfigParser()
        try:
            if not self._conf_parser.read(cfile):
                logging.error("Cannot read config file' {}'".format(cfile))
                return None
        except ConfigParserError as error:
            logging.error("Could not parse config file "
                          "'{}': {}".format(cfile, error))
            return None
        items = dict()
        failed = False
        for section in self._conf_parser.sections():
            parser = self._get_section_parser(section)
            if parser is None:
                logging.warning(
                    "Found unknown section '{}' in config file".format(section)
                )
                continue

            values = parser.parse(section)
            if values is None:
                failed = True
                continue
            if parser.is_collection():
                if parser.group not in items:
                    items[parser.group] = []
                items[parser.group].append(values)
            else:
                items[parser.group] = values

        failed = self.check_required(items) or failed
        self.warn_leftovers()
        self.dump(items)
        if failed:
            return None
        else:
            return Namespace(items)

    def check_required(self, items):
        groupnames = [sec(None).group for sec in self._required_sections]
        failed = False
        for group in groupnames:
            if group not in items:
                logging.error("Missing required section '{}'".format(group))
                failed = True
        return failed

    def warn_leftovers(self):
        for section in self._conf_parser.sections():
            for option in self._conf_parser.options(section):
                logging.warn("Ignoring unknow option '{}' in section "
                             "'{}'".format(option, section))

    def dump(self, conf, intro='Using configuration:', tab=0):
        """Dump the loaded configuration using the logging framework.

        The values displayed here are the exact values which are seen by
        the program, and not the raw values as they are read in the
        configuration file.
        """
        # TODO while this is fully functional it could be prettier
        logging.debug('{0}{1}'.format('\t' * tab, intro))

        if isinstance(conf, (Namespace, dict)):
            for name, value in sorted(dict.copy(conf).items()):
                if isinstance(value, (Namespace, dict, list)):
                    self.dump(value, '[' + name + ']', tab=tab + 1)
                else:
                    logging.debug('{0}{1}: {2}'.format('\t' * (tab + 1), name, value))
        elif isinstance(conf, list):
            for o in conf:
                self.dump(o, '\t' * tab + intro + ':', tab + 1)


class Display(object):

    def __init__(self, collection, firstweekday=0, encoding='utf-8'):
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        daylist = [(today, 'Today:'), (tomorrow, 'Tomorrow:')]
        event_column = list()

        term_width, _ = get_terminal_size()
        lwidth = 25
        rwidth = term_width - lwidth - 4

        for day, dayname in daylist:
            # TODO unify allday and datetime events
            start = datetime.datetime.combine(day, datetime.time.min)
            end = datetime.datetime.combine(day, datetime.time.max)

            event_column.append(bstring(dayname))

            all_day_events = collection.get_allday_by_time_range(day)
            events = collection.get_datetime_by_time_range(start, end)
            for event in all_day_events:
                desc = textwrap.wrap(event.compact(day), rwidth)
                event_column.extend([colored(d, event.color) for d in desc])

            events.sort(key=lambda e: e.start)
            for event in events:
                desc = textwrap.wrap(event.compact(day), rwidth)
                event_column.extend([colored(d, event.color) for d in desc])

        calendar_column = calendar_display.vertical_month(
            firstweekday=firstweekday)

        rows = merge_columns(calendar_column, event_column)
        print('\n'.join(rows).encode(encoding))


class NewFromString(object):

    def __init__(self, collection, conf):
        date_list = conf.new
        event = aux.construct_event(date_list,
                                    conf.default.timeformat,
                                    conf.default.dateformat,
                                    conf.default.longdateformat,
                                    conf.default.datetimeformat,
                                    conf.default.longdatetimeformat,
                                    conf.default.local_timezone,
                                    encoding=conf.default.encoding)
        # TODO proper default calendar
        event = collection.new_event(event, conf.active_calendars.pop())

        collection.new(event)


class Interactive(object):

    def __init__(self, collection, conf):
        import ui
        pane = ui.ClassicView(collection,
                              conf,
                              title='select an event',
                              description='do something')
        ui.start_pane(pane, pane.cleanup,
                      header=u'{0} v{1}'.format(__productname__, __version__))


def main_khal():
    capture_user_interruption()

    # setting the process title so it looks nicer in ps
    # shows up as 'khal' under linux and as 'python: khal (python2.7)'
    # under FreeBSD, which is still nicer than the default
    setproctitle('khal')

    _khal(None)


def _khal(conf):
    khal = argvard.Argvard()
    # Read configuration.
    config_file = _find_configuration_file()
    if config_file is None:
        sys.exit('Cannot find any config file, exiting')

    conf = ConfigParser().parse_config(config_file)
    if conf is None:
        sys.exit('Invalid config file, exiting.')

    @khal.main()
    def main(context):
        context.argvard(context.command_path + ['--help'])

    calendar = argvard.Command()

    @calendar.main('[calendar...]')
    def calendar_main(context, calendar=None):
#    (self, collection, firstweekday=0, encoding='utf-8'):
#
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        daylist = [(today, 'Today:'), (tomorrow, 'Tomorrow:')]
        event_column = list()

        term_width, _ = get_terminal_size()
        lwidth = 25
        rwidth = term_width - lwidth - 4

        for day, dayname in daylist:
            # TODO unify allday and datetime events
            start = datetime.datetime.combine(day, datetime.time.min)
            end = datetime.datetime.combine(day, datetime.time.max)

            event_column.append(bstring(dayname))

            all_day_events = collection.get_allday_by_time_range(day)
            events = collection.get_datetime_by_time_range(start, end)
            for event in all_day_events:
                desc = textwrap.wrap(event.compact(day), rwidth)
                event_column.extend([colored(d, event.color) for d in desc])

            events.sort(key=lambda e: e.start)
            for event in events:
                desc = textwrap.wrap(event.compact(day), rwidth)
                event_column.extend([colored(d, event.color) for d in desc])

        calendar_column = calendar_display.vertical_month(
            firstweekday=firstweekday)

        rows = merge_columns(calendar_column, event_column)
        print('\n'.join(rows).encode(encoding))

    khal.register_command('calendar', calendar)

    khal()
