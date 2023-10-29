from collections.abc import Callable, Mapping
from typing import Dict, List, Tuple

from khal._compat import importlib_metadata

# This is a shameless ripoff of mdformat's plugin extension API.
# see:
#   https://github.com/executablebooks/mdformat/blob/master/src/mdformat/plugins.py
#   https://setuptools.pypa.io/en/latest/userguide/entry_point.html


def _load_formatters() -> dict[str, Callable[[str], str]]:
    formatter_entrypoints = importlib_metadata.entry_points(group="khal.formatter")
    return {ep.name: ep.load() for ep in formatter_entrypoints}


FORMATTERS: Mapping[str, Callable[[str], str]] = _load_formatters()

def _load_color_themes() -> Dict[str, List[Tuple[str, ...]]]:
    color_theme_entrypoints = importlib_metadata.entry_points(group="khal.color_theme")
    return {ep.name: ep.load() for ep in color_theme_entrypoints}

THEMES: Dict[str, List[Tuple[str, ...]],] = _load_color_themes()
