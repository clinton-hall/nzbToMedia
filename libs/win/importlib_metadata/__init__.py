from .api import distribution, Distribution, PackageNotFoundError  # noqa: F401
from .api import metadata, entry_points, resolve, version, read_text

# Import for installation side-effects.
from . import _hooks  # noqa: F401


__all__ = [
    'metadata',
    'entry_points',
    'resolve',
    'version',
    'read_text',
    ]


__version__ = version(__name__)
