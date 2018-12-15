.. _using:

==========================
 Using importlib_metadata
==========================

``importlib_metadata`` is a library that provides for access to installed
package metadata.  Built in part on Python's import system, this library
intends to replace similar functionality in ``pkg_resources`` `entry point
API`_ and `metadata API`_.  Along with ``importlib.resources`` in `Python 3.7
and newer`_ (backported as `importlib_resources`_ for older versions of
Python), this can eliminate the need to use the older and less efficient
``pkg_resources`` package.

By "installed package" we generally mean a third party package installed into
Python's ``site-packages`` directory via tools such as ``pip``.  Specifically,
it means a package with either a discoverable ``dist-info`` or ``egg-info``
directory, and metadata defined by `PEP 566`_ or its older specifications.
By default, package metadata can live on the file system or in wheels on
``sys.path``.  Through an extension mechanism, the metadata can live almost
anywhere.


Overview
========

Let's say you wanted to get the version string for a package you've installed
using ``pip``.  We start by creating a virtual environment and installing
something into it::

    $ python3 -m venv example
    $ source example/bin/activate
    (example) $ pip install importlib_metadata
    (example) $ pip install wheel

You can get the version string for ``wheel`` by running the following::

    (example) $ python
    >>> from importlib_metadata import version
    >>> version('wheel')
    '0.31.1'

You can also get the set of entry points for the ``wheel`` package.  Since the
``entry_points.txt`` file is an ``.ini``-style, the ``entry_points()``
function returns a `ConfigParser instance`_.  To get the list of command line
entry points, extract the ``console_scripts`` section::

    >>> cp = entry_points('wheel')
    >>> cp.options('console_scripts')
    ['wheel']

You can also get the callable that the entry point is mapped to::

    >>> cp.get('console_scripts', 'wheel')
    'wheel.tool:main'

Even more conveniently, you can resolve this entry point to the actual
callable::

    >>> from importlib_metadata import resolve
    >>> ep = cp.get('console_scripts', 'wheel')
    >>> resolve(ep)
    <function main at 0x111b91bf8>


Distributions
=============

While the above API is the most common and convenient usage, you can get all
of that information from the ``Distribution`` class.  A ``Distribution`` is an
abstract object that represents the metadata for a Python package.  You can
get the ``Distribution`` instance::

    >>> from importlib_metadata import distribution
    >>> dist = distribution('wheel')

Thus, an alternative way to get the version number is through the
``Distribution`` instance::

    >>> dist.version
    '0.31.1'

There are all kinds of additional metadata available on the ``Distribution``
instance::

    >>> d.metadata['Requires-Python']
    '>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*'
    >>> d.metadata['License']
    'MIT'

The full set of available metadata is not described here.  See PEP 566 for
additional details.


Extending the search algorithm
==============================

Because package metadata is not available through ``sys.path`` searches, or
package loaders directly, the metadata for a package is found through import
system `finders`_.  To find a distribution package's metadata,
``importlib_metadata`` queries the list of `meta path finders`_ on
`sys.meta_path`_.

By default ``importlib_metadata`` installs a finder for packages found on the
file system.  This finder doesn't actually find any *packages*, but it cany
find the package's metadata.

The abstract class :py:class:`importlib.abc.MetaPathFinder` defines the
interface expected of finders by Python's import system.
``importlib_metadata`` extends this protocol by looking for an optional
``find_distribution()`` ``@classmethod`` on the finders from
``sys.meta_path``.  If the finder has this method, it takes a single argument
which is the name of the distribution package to find.  The method returns
``None`` if it cannot find the distribution package, otherwise it returns an
instance of the ``Distribution`` abstract class.

What this means in practice is that to support finding distribution package
metadata in locations other than the file system, you should derive from
``Distribution`` and implement the ``load_metadata()`` method.  This takes a
single argument which is the name of the package whose metadata is being
found.  This instance of the ``Distribution`` base abstract class is what your
finder's ``find_distribution()`` method should return.


.. _`entry point API`: https://setuptools.readthedocs.io/en/latest/pkg_resources.html#entry-points
.. _`metadata API`: https://setuptools.readthedocs.io/en/latest/pkg_resources.html#metadata-api
.. _`Python 3.7 and newer`: https://docs.python.org/3/library/importlib.html#module-importlib.resources
.. _`importlib_resources`: https://importlib-resources.readthedocs.io/en/latest/index.html
.. _`PEP 566`: https://www.python.org/dev/peps/pep-0566/
.. _`ConfigParser instance`: https://docs.python.org/3/library/configparser.html#configparser.ConfigParser
.. _`finders`: https://docs.python.org/3/reference/import.html#finders-and-loaders
.. _`meta path finders`: https://docs.python.org/3/glossary.html#term-meta-path-finder
.. _`sys.meta_path`: https://docs.python.org/3/library/sys.html#sys.meta_path
