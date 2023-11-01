from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from khal.khalendar.event import Event

# There should be `khal.khalendar.Event` instead of `Any`
# here and in `Postprocess` below but that results in recursive typing
# which mypy doesn't support until
# https://github.com/python/mypy/issues/731 is implemented.
Render = Callable[
    ["Event", Any],
    str,
]

Postprocess = Callable[[str, "Event", Any], str]
