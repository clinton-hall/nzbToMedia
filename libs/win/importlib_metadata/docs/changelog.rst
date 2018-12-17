=========================
 importlib_metadata NEWS
=========================

0.7 (2018-11-27)
================
* Fixed issue where packages with dashes in their names would
  not be discovered. Closes #21.
* Distribution lookup is now case-insensitive. Closes #20.
* Wheel distributions can no longer be discovered by their module
  name. Like Path distributions, they must be indicated by their
  distribution package name.

0.6 (2018-10-07)
================
* Removed ``importlib_metadata.distribution`` function. Now
  the public interface is primarily the utility functions exposed
  in ``importlib_metadata.__all__``. Closes #14.
* Added two new utility functions ``read_text`` and
  ``metadata``.

0.5 (2018-09-18)
================
* Updated README and removed details about Distribution
  class, now considered private. Closes #15.
* Added test suite support for Python 3.4+.
* Fixed SyntaxErrors on Python 3.4 and 3.5. !12
* Fixed errors on Windows joining Path elements. !15

0.4 (2018-09-14)
================
* Housekeeping.

0.3 (2018-09-14)
================
* Added usage documentation.  Closes #8
* Add support for getting metadata from wheels on ``sys.path``.  Closes #9

0.2 (2018-09-11)
================
* Added ``importlib_metadata.entry_points()``.  Closes #1
* Added ``importlib_metadata.resolve()``.  Closes #12
* Add support for Python 2.7.  Closes #4

0.1 (2018-09-10)
================
* Initial release.


..
   Local Variables:
   mode: change-log-mode
   indent-tabs-mode: nil
   sentence-end-double-space: t
   fill-column: 78
   coding: utf-8
   End:
