import io
import abc
import sys
import email

from importlib import import_module

if sys.version_info > (3,):  # pragma: nocover
    from configparser import ConfigParser
else:  # pragma: nocover
    from ConfigParser import SafeConfigParser as ConfigParser

try:
    BaseClass = ModuleNotFoundError
except NameError:                                 # pragma: nocover
    BaseClass = ImportError                       # type: ignore


__metaclass__ = type


class PackageNotFoundError(BaseClass):
    """The package was not found."""


class Distribution:
    """A Python distribution package."""

    @abc.abstractmethod
    def read_text(self, filename):
        """Attempt to load metadata file given by the name.

        :param filename: The name of the file in the distribution info.
        :return: The text if found, otherwise None.
        """

    @classmethod
    def from_name(cls, name):
        """Return the Distribution for the given package name.

        :param name: The name of the distribution package to search for.
        :return: The Distribution instance (or subclass thereof) for the named
            package, if found.
        :raises PackageNotFoundError: When the named package's distribution
            metadata cannot be found.
        """
        for resolver in cls._discover_resolvers():
            resolved = resolver(name)
            if resolved is not None:
                return resolved
        else:
            raise PackageNotFoundError(name)

    @staticmethod
    def _discover_resolvers():
        """Search the meta_path for resolvers."""
        declared = (
            getattr(finder, 'find_distribution', None)
            for finder in sys.meta_path
            )
        return filter(None, declared)

    @property
    def metadata(self):
        """Return the parsed metadata for this Distribution.

        The returned object will have keys that name the various bits of
        metadata.  See PEP 566 for details.
        """
        return email.message_from_string(
            self.read_text('METADATA') or self.read_text('PKG-INFO')
            )

    @property
    def version(self):
        """Return the 'Version' metadata for the distribution package."""
        return self.metadata['Version']


def distribution(package):
    """Get the ``Distribution`` instance for the given package.

    :param package: The name of the package as a string.
    :return: A ``Distribution`` instance (or subclass thereof).
    """
    return Distribution.from_name(package)


def metadata(package):
    """Get the metadata for the package.

    :param package: The name of the distribution package to query.
    :return: An email.Message containing the parsed metadata.
    """
    return Distribution.from_name(package).metadata


def version(package):
    """Get the version string for the named package.

    :param package: The name of the distribution package to query.
    :return: The version string for the package as defined in the package's
        "Version" metadata key.
    """
    return distribution(package).version


def entry_points(name):
    """Return the entry points for the named distribution package.

    :param name: The name of the distribution package to query.
    :return: A ConfigParser instance where the sections and keys are taken
        from the entry_points.txt ini-style contents.
    """
    as_string = read_text(name, 'entry_points.txt')
    # 2018-09-10(barry): Should we provide any options here, or let the caller
    # send options to the underlying ConfigParser?   For now, YAGNI.
    config = ConfigParser()
    try:
        config.read_string(as_string)
    except AttributeError:  # pragma: nocover
        # Python 2 has no read_string
        config.readfp(io.StringIO(as_string))
    return config


def resolve(entry_point):
    """Resolve an entry point string into the named callable.

    :param entry_point: An entry point string of the form
        `path.to.module:callable`.
    :return: The actual callable object `path.to.module.callable`
    :raises ValueError: When `entry_point` doesn't have the proper format.
    """
    path, colon, name = entry_point.rpartition(':')
    if colon != ':':
        raise ValueError('Not an entry point: {}'.format(entry_point))
    module = import_module(path)
    return getattr(module, name)


def read_text(package, filename):
    """
    Read the text of the file in the distribution info directory.
    """
    return distribution(package).read_text(filename)
