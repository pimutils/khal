from collections.abc import Callable, Mapping
from functools import cache
from importlib import metadata as importlib_metadata

# This is a shameless ripoff of mdformat's plugin extension API.
# see:
#   https://github.com/executablebooks/mdformat/blob/master/src/mdformat/plugins.py
#   https://setuptools.pypa.io/en/latest/userguide/entry_point.html


def _load_formatters() -> dict[str, Callable[[str], str]]:
    formatter_entrypoints = importlib_metadata.entry_points(group="khal.formatter")
    return {ep.name: ep.load() for ep in formatter_entrypoints}


FORMATTERS: Mapping[str, Callable[[str], str]] = _load_formatters()


def _load_color_themes() -> dict[str, list[tuple[str | None, ...]] | dict]:
    color_theme_entrypoints = importlib_metadata.entry_points(group="khal.color_theme")
    return {ep.name: ep.load() for ep in color_theme_entrypoints}


# a full urwid palette or (see khal.ui.colors.SEMANTIC_THEMES) a dict of a
# few semantic colours
THEMES: dict[
    str,
    list[tuple[str | None, ...]] | dict,
] = _load_color_themes()


def _load_commands() -> dict[str, Callable]:
    command_entrypoints = importlib_metadata.entry_points(group="khal.commands")
    return {ep.name: ep.load() for ep in command_entrypoints}


COMMANDS: dict[str, Callable] = _load_commands()


@cache
def get_views() -> dict[str, Callable]:
    """load alternative views for ikhal's event column

    Each entry point must resolve to a callable with the signature
    ``factory(pane: khal.ui.ClassicView) -> urwid.Widget``. The returned box
    widget replaces the default event list in the right column of ikhal and
    must implement the interface described in :class:`khal.ui.EventView`.

    In contrast to the other plugin types, views are loaded lazily, as they
    will usually need to import from :mod:`khal.ui` themselves.
    """
    view_entrypoints = importlib_metadata.entry_points(group="khal.views")
    return {ep.name: ep.load() for ep in view_entrypoints}
