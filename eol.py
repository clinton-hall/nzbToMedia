#!/usr/bin/env python

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import datetime
import sys
import warnings

__version__ = '1.0.0'


def date(string, fmt='%Y-%m-%d'):
    """
    Convert date string to date.

    :param string: A date string
    :param fmt: Format to use when parsing the date string
    :return: A datetime.date
    """
    return datetime.datetime.strptime(string, fmt).date()


# https://devguide.python.org/
# https://devguide.python.org/devcycle/#devcycle
PYTHON_EOL = {
    (3, 11): date('2027-10-1'),
    (3, 10): date('2026-10-01'),
    (3, 9): date('2025-10-05'),
    (3, 8): date('2024-10-14'),
    (3, 7): date('2023-06-27'),
    (3, 6): date('2021-12-23'),
    (3, 5): date('2020-09-13'),
    (3, 4): date('2019-03-16'),
    (3, 3): date('2017-09-29'),
    (3, 2): date('2016-02-20'),
    (3, 1): date('2012-04-09'),
    (3, 0): date('2009-01-13'),
    (2, 7): date('2020-01-01'),
    (2, 6): date('2013-10-29'),
}


class Error(Exception):
    """An error has occurred."""


class LifetimeError(Error):
    """Lifetime has been exceeded and upgrade is required."""


class LifetimeWarning(Warning):
    """Lifetime has been exceeded and is no longer supported."""


def lifetime(version=None):
    """
    Calculate days left till End-of-Life for a version.

    :param version: An optional tuple with version information
        If a version is not provided, the current system version will be used.
    :return: Days left until End-of-Life
    """
    if version is None:
        version = sys.version_info
    major = version[0]
    minor = version[1]
    now = datetime.datetime.now().date()
    time_left = PYTHON_EOL[(major, minor)] - now
    return time_left.days


def expiration(version=None, grace_period=0):
    """
    Calculate expiration date for a version given a grace period.

    :param version: An optional tuple with version information
        If a version is not provided, the current system version will be used.
    :param grace_period: An optional number of days grace period
    :return: Total days till expiration
    """
    days_left = lifetime(version)
    return days_left + grace_period


def check(version=None, grace_period=0):
    """
    Raise an exception if end of life has been reached and recommend upgrade.

    :param version: An optional tuple with version information
        If a version is not provided, the current system version will be used.
    :param grace_period: An optional number of days grace period
        If a grace period is not provided, a default 60 days grace period will
        be used.
    :return: None
    """
    try:
        warn_for_status(version, grace_period)
    except LifetimeError as error:
        print('Please use a newer version of Python.')
        print_statuses()
        sys.exit(error)


def raise_for_status(version=None, grace_period=0):
    """
    Raise an exception if end of life has been reached.

    :param version: An optional tuple with version information
        If a version is not provided, the current system version will be used.
    :param grace_period: An optional number of days grace period
        If a grace period is not provided, a default 60 days grace period will
        be used.
    :return: None
    """
    if version is None:
        version = sys.version_info
    days_left = lifetime(version)
    expires = days_left + grace_period
    if expires <= 0:
        msg = 'Python {major}.{minor} is no longer supported.'.format(
            major=version[0],
            minor=version[1],
        )
        raise LifetimeError(msg)


def warn_for_status(version=None, grace_period=0):
    """
    Warn if end of life has been reached.

    :param version: An optional tuple with version information
        If a version is not provided, the current system version will be used.
    :param grace_period: An optional number of days grace period
    :return: None
    """
    if version is None:
        version = sys.version_info
    days_left = lifetime(version)
    expires = days_left + grace_period
    if expires <= 0:
        msg = 'Python {major}.{minor} is no longer supported.'.format(
            major=version[0],
            minor=version[1],
        )
        warnings.warn(msg, LifetimeWarning)


def print_statuses(show_expired=False):
    """
    Print end-of-life statuses of known python versions.

    :param show_expired: If true also print expired python version statuses
    """
    lifetimes = sorted(
        (lifetime(python_version), python_version)
        for python_version in PYTHON_EOL
    )
    print('Python End-of-Life for current versions:')
    for days_left, python_version in lifetimes:
        if days_left >= 0:
            print(
                'v{major}.{minor} in {remaining:>4} days'.format(
                    major=python_version[0],
                    minor=python_version[1],
                    remaining=days_left,
                ),
            )
    if not show_expired:
        return

    print()
    print('Python End-of-Life for expired versions:')
    for days_left, python_version in lifetimes:
        if days_left < 0:
            print(
                'v{major}.{minor} {remaining:>4} days ago'.format(
                    major=python_version[0],
                    minor=python_version[1],
                    remaining=-days_left,
                ),
            )


if __name__ == '__main__':
    print_statuses(show_expired=True)
