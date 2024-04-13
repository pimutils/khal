__all__ = ["importlib_metadata"]

import sys

if sys.version_info >= (3, 10):  # pragma: no cover
    from importlib import metadata as importlib_metadata
else:  # pragma: no cover
    import importlib_metadata
