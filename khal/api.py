from typing import Callable, Dict

from .ui.colors import register_color_theme

_plugin_commands: Dict[str, Callable] = {}

def register_command(name: str, command: Callable):
    _plugin_commands[name] = command

__all__ = ["register_color_theme", "register_command"]
