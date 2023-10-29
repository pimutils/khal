from collections.abc import Callable, Mapping
from typing import Dict, List, Tuple

from khal._compat import importlib_metadata

# from khal._compat import Protocol, importlib_metadata
# from khal.khalendar.typing import Postprocess, Render

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

# class ParserExtensionInterface(Protocol):
#     """An interface for parser extension plugins."""

#     # Does the plugin's formatting change Markdown AST or not?
#     # (optional, default: False)
#     CHANGES_AST: bool = False

#     # A mapping from `RenderTreeNode.type` to a `Render` function that can
#     # render the given `RenderTreeNode` type. These override the default
#     # `Render` funcs defined in `mdformat.renderer.DEFAULT_RENDERERS`.
#     RENDERERS: Mapping[str, Render]

#     # A mapping from `RenderTreeNode.type` to a `Postprocess` that does
#     # postprocessing for the output of the `Render` function. Unlike
#     # `Render` funcs, `Postprocess` funcs are collaborative: any number of
#     # plugins can define a postprocessor for a syntax type and all of them
#     # will run in series.
#     # (optional)
#     POSTPROCESSORS: Mapping[str, Postprocess]

#     @staticmethod
#     def add_cli_options(parser: argparse.ArgumentParser) -> None:
#         """Add options to the khal CLI, to be stored in mdit.options["mdformat"]
#         (optional)"""

# def _load_parser_extensions() -> dict[str, ParserExtensionInterface]:
#     parser_extension_entrypoints = importlib_metadata.entry_points(
#         group="khal.parser_extension"
#     )
#     return {ep.name: ep.load() for ep in parser_extension_entrypoints}


# PARSER_EXTENSIONS: Mapping[str, ParserExtensionInterface] = _load_parser_extensions()
