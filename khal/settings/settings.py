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

import logging
import os

import xdg.BaseDirectory
from configobj import ConfigObj, ConfigObjError, flatten_errors, get_extra_values

from khal import __productname__

try:
    # Available from configobj 5.1.0
    from configobj.validate import Validator
except ModuleNotFoundError:
    from validate import Validator

from collections.abc import Callable

from .exceptions import CannotParseConfigFileError, InvalidSettingsError, NoConfigFile
from .utils import (
    config_checks,
    expand_db_path,
    expand_path,
    get_color_from_vdir,
    get_vdir_type,
    is_color,
    is_timedelta,
    is_timezone,
    monthdisplay_option,
    weeknumber_option,
)

logger = logging.getLogger("khal")
SPECPATH = os.path.join(os.path.dirname(__file__), "khal.spec")


def find_configuration_file() -> str | None:
    """Return the configuration filename.

    Check all the paths for configuration files defined in the XDG Base Directory
    Standard, and return the first one that exists, if any.

    For the common case, this will return ~/.config/khal/config, assuming that it
    exists.
    """

    for dir in xdg.BaseDirectory.xdg_config_dirs:
        path = os.path.join(dir, __productname__, "config")
        if os.path.exists(path):
            return path

    return None


def get_config(
    config_path: str | None = None,
    _get_color_from_vdir: Callable = get_color_from_vdir,
    _get_vdir_type: Callable = get_vdir_type,
    check_ui: bool = False,
) -> ConfigObj:
    """reads the config file, validates it and return a config dict

    With `check_ui` (ikhal is about to start), [view] settings ikhal would
    otherwise only check at startup are validated as well, so all mistakes are
    reported at once.

    :param config_path: path to a custom config file, if none is given the
                        default locations will be searched
    :param _get_color_from_vdir: override get_color_from_vdir for testing purposes
    :param _get_vdir_type: override get_vdir_type for testing purposes
    :returns: configuration
    """
    if config_path is None:
        config_path = find_configuration_file()
    if config_path is None or not os.path.exists(config_path):
        raise NoConfigFile()

    logger.debug(f"using the config file at {config_path}")

    try:
        user_config = ConfigObj(
            config_path,
            configspec=SPECPATH,
            interpolation=False,
            file_error=True,
        )
    except ConfigObjError as error:
        logger.fatal(f"parsing the config file with the following error: {error}")
        logger.fatal(
            "if you recently updated khal, the config file format "
            "might have changed, in that case please consult the "
            "CHANGELOG or other documentation"
        )
        raise CannotParseConfigFileError()

    fdict = {
        "timezone": is_timezone,
        "timedelta": is_timedelta,
        "expand_path": expand_path,
        "expand_db_path": expand_db_path,
        "weeknumbers": weeknumber_option,
        "monthdisplay": monthdisplay_option,
        "color": is_color,
    }
    validator = Validator(fdict)
    results = user_config.validate(validator, preserve_errors=True)

    # collect every problem first, so a config with several mistakes is
    # reported completely instead of one error per start
    problems: list[str] = []
    for section, subsection, config_error in flatten_errors(user_config, results):
        if isinstance(config_error, Exception):
            hint = _valid_values_hint(validator, user_config, section, subsection, config_error)
            problems.append(f"in [{section[0]}] {subsection}: {config_error}{hint}")
        else:
            for key in config_error:
                if isinstance(config_error[key], Exception):
                    hint = _valid_values_hint(
                        validator, user_config, section + [subsection], key, config_error[key]
                    )
                    where = sectionize(section + [subsection])
                    problems.append(f"in {where} {key}: {config_error[key]!s}{hint}")
    if check_ui:  # needs khal.ui, which the other commands don't load
        problems += ui_settings_problems(user_config)
    if problems:
        logger.fatal("config error:" if len(problems) == 1 else f"{len(problems)} config errors:")
    for problem in problems:
        logger.fatal(f"  {problem}")

    if problems or not results:
        raise InvalidSettingsError()

    config_checks(user_config, _get_color_from_vdir, _get_vdir_type)

    extras = get_extra_values(user_config)
    for section, value in extras:
        if section == ():
            logger.warning(f'unknown section "{value}" in config file')
        elif section == ("palette",):
            # we don't validate the palette section, because there is no way to
            # automatically extract valid attributes from the ui module
            continue
        elif section[:1] == ("plugins",):
            # plugins validate their own settings
            continue
        else:
            section = sectionize(section)
            logger.warning(f'unknown key or subsection "{value}" in section "{section}"')
    return user_config


def sectionize(sections: list[str], depth: int = 1) -> str:
    """converts list of string into [list][[of]][[[strings]]]"""
    this_part = depth * "[" + sections[0] + depth * "]"
    if len(sections) > 1:
        return this_part + sectionize(sections[1:], depth=depth + 1)
    else:
        return this_part


# valid values of the custom checks in khal.spec (option() lists its own)
_CHECK_VALUES = {
    "weeknumbers": ["off", "left", "right"],
    "monthdisplay": ["firstday", "firstfullweek"],
}


def _valid_values_hint(validator, config, sections: list[str], key: str, error=None) -> str:
    """the valid values of an option with a fixed set of them, as
    ` (valid: a, b, c)`; empty if there is no such set or the error message
    already names it"""
    if "must be one of" in str(error):
        return ""
    spec = config.configspec
    try:
        for name in sections:
            spec = spec[name] if name in spec else spec["__many__"]
        check = spec[key]
        name, args, _kwargs, _default = validator._parse_with_caching(check)
    except (KeyError, TypeError, AttributeError, ValueError):
        return ""
    values = args if name == "option" else _CHECK_VALUES.get(name)
    return f" (valid: {', '.join(values)})" if values else ""


def ui_settings_problems(config) -> list[str]:
    """checks of [view] settings ikhal would otherwise only notice at startup"""
    from importlib import metadata

    problems: list[str] = []
    view = config.get("view", {})
    if not isinstance(view, dict):
        return problems

    from khal.ui import colors

    themes = list(colors.themes) + [
        ep.name for ep in metadata.entry_points(group="khal.color_theme")
    ]
    theme = view.get("theme")
    if isinstance(theme, str) and theme not in themes:
        problems.append(
            f'in [view] theme: the value "{theme}" is unacceptable. (valid: {", ".join(themes)})'
        )

    views = ["list"] + [ep.name for ep in metadata.entry_points(group="khal.views")]
    default_view = view.get("default_view")
    if isinstance(default_view, str) and default_view and default_view not in views:
        problems.append(
            f'in [view] default_view: the value "{default_view}" is unacceptable. '
            f"(valid: {', '.join(views)})"
        )

    from khal.ui.agenda import parse_free_time, parse_hours

    for key, parse, example in (
        ("show_free_time", parse_free_time, "30m, 3h, off"),
        ("free_time_hours", parse_hours, "09:00-18:00"),
    ):
        value = view.get(key)
        if not isinstance(value, str):
            continue
        try:
            parse(value)
        except (ValueError, TypeError):
            problems.append(
                f'in [view] {key}: the value "{value}" is unacceptable. (e.g. {example})'
            )
    return problems
