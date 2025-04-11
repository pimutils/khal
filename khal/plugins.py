from collections.abc import Mapping
from typing import Callable

from khal._compat import importlib_metadata

# This is a shameless ripoff of mdformat's plugin extension API.
# see:
#   https://github.com/executablebooks/mdformat/blob/master/src/mdformat/plugins.py
#   https://setuptools.pypa.io/en/latest/userguide/entry_point.html


def _load_formatters() -> dict[str, Callable[[str], str]]:
    formatter_entrypoints = importlib_metadata.entry_points(group="khal.formatter")
    return {ep.name: ep.load() for ep in formatter_entrypoints}


FORMATTERS: Mapping[str, Callable[[str], str]] = _load_formatters()

def _load_color_themes() -> dict[str, list[tuple[str, ...]]]:
    color_theme_entrypoints = importlib_metadata.entry_points(group="khal.color_theme")
    return {ep.name: ep.load() for ep in color_theme_entrypoints}

THEMES: dict[str, list[tuple[str, ...]],] = _load_color_themes()


def _load_commands() -> dict[str, Callable]:
    command_entrypoints = importlib_metadata.entry_points(group="khal.commands")
    return {ep.name: ep.load() for ep in command_entrypoints}

COMMANDS: dict[str, Callable] = _load_commands()
