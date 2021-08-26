from __future__ import unicode_literals, absolute_import

import re
import sys
import itertools

from .api import Distribution
from zipfile import ZipFile

if sys.version_info >= (3,):  # pragma: nocover
    from contextlib import suppress
    from pathlib import Path
else:  # pragma: nocover
    from contextlib2 import suppress  # noqa
    from itertools import imap as map  # type: ignore
    from pathlib2 import Path

    FileNotFoundError = IOError, OSError
    __metaclass__ = type


def install(cls):
    """Class decorator for installation on sys.meta_path."""
    sys.meta_path.append(cls)
    return cls


class NullFinder:
    @staticmethod
    def find_spec(*args, **kwargs):
        return None

    # In Python 2, the import system requires finders
    # to have a find_module() method, but this usage
    # is deprecated in Python 3 in favor of find_spec().
    # For the purposes of this finder (i.e. being present
    # on sys.meta_path but having no other import
    # system functionality), the two methods are identical.
    find_module = find_spec


@install
class MetadataPathFinder(NullFinder):
    """A degenerate finder for distribution packages on the file system.

    This finder supplies only a find_distribution() method for versions
    of Python that do not have a PathFinder find_distribution().
    """
    search_template = r'{name}(-.*)?\.(dist|egg)-info'

    @classmethod
    def find_distribution(cls, name):
        paths = cls._search_paths(name)
        dists = map(PathDistribution, paths)
        return next(dists, None)

    @classmethod
    def _search_paths(cls, name):
        """
        Find metadata directories in sys.path heuristically.
        """
        return itertools.chain.from_iterable(
            cls._search_path(path, name)
            for path in map(Path, sys.path)
            )

    @classmethod
    def _search_path(cls, root, name):
        if not root.is_dir():
            return ()
        normalized = name.replace('-', '_')
        return (
            item
            for item in root.iterdir()
            if item.is_dir()
            and re.match(
                cls.search_template.format(name=normalized),
                str(item.name),
                flags=re.IGNORECASE,
                )
            )


class PathDistribution(Distribution):
    def __init__(self, path):
        """Construct a distribution from a path to the metadata directory."""
        self._path = path

    def read_text(self, filename):
        with suppress(FileNotFoundError):
            with self._path.joinpath(filename).open(encoding='utf-8') as fp:
                return fp.read()
        return None
    read_text.__doc__ = Distribution.read_text.__doc__


@install
class WheelMetadataFinder(NullFinder):
    """A degenerate finder for distribution packages in wheels.

    This finder supplies only a find_distribution() method for versions
    of Python that do not have a PathFinder find_distribution().
    """
    search_template = r'{name}(-.*)?\.whl'

    @classmethod
    def find_distribution(cls, name):
        paths = cls._search_paths(name)
        dists = map(WheelDistribution, paths)
        return next(dists, None)

    @classmethod
    def _search_paths(cls, name):
        return (
            item
            for item in map(Path, sys.path)
            if re.match(
                cls.search_template.format(name=name),
                str(item.name),
                flags=re.IGNORECASE,
                )
            )


class WheelDistribution(Distribution):
    def __init__(self, archive):
        self._archive = archive
        name, version = archive.name.split('-')[0:2]
        self._dist_info = '{}-{}.dist-info'.format(name, version)

    def read_text(self, filename):
        with ZipFile(_path_to_filename(self._archive)) as zf:
            with suppress(KeyError):
                as_bytes = zf.read('{}/{}'.format(self._dist_info, filename))
                return as_bytes.decode('utf-8')
        return None
    read_text.__doc__ = Distribution.read_text.__doc__


def _path_to_filename(path):  # pragma: nocover
    """
    On non-compliant systems, ensure a path-like object is
    a string.
    """
    try:
        return path.__fspath__()
    except AttributeError:
        return str(path)
