#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import io
import os.path

from setuptools import setup


def read(*names, **kwargs):
    with io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8'),
    ) as fh:
        return fh.read()


setup(
    name='nzbToMedia',
    version='12.1.12',
    license='GPLv3',
    description='Efficient on demand post processing',
    long_description="""
    nzbToMedia
    ==========

    Efficient on demand post processing
    -----------------------------------

    A PVR app needs to know when a download is ready for post-processing. There are two methods:

    1. On-demand post-processing script (e.g. sabToSickBeard.py or nzbToMedia.py): A script in the downloader runs once at the end of the download job and notifies the PVR app that the download is complete.

    2. Continuous folder scanning: The PVR app frequently polls download folder(s) for completed downloads.

    On-demand is superior, for several reasons:

    1. The PVR app is notified only once, exactly when the download is ready for post-processing
    2. The PVR app does not have to wait for the next poll interval before it starts processing
    3. Continuous polling is not as efficient and is more stressful on low performance hardware
    4. Continuously polling a folder for changes can prevent the drive from going to sleep
    5. Continuous polling may encounter file access/permissions issues
    6. Continuous polling may miss a folder change, causing the PVR app to wait forever
    7. An on-demand post-processing script is able to utilize additional functionality such as ffprobe media checking to test for bad video files.
    8. On-demand scripts can be tweaked to allow for delays with slow hardware

    nzbToMedia is an on-demand post-processing script and was created out of a demand for more efficient post-processing on low-performance hardware. Many features have been added so higher performance hardware can benefit too.

    Many issues that users have with folder scanning can be fixed by switching to on-demand. A whole class of support issues can be eliminated by using nzbToMedia.
    """,
    author='Clinton Hall',
    author_email='fock_wulf@hotmail.com',
    url='https://github.com/clinton-hall/nzbToMedia',
    packages=['core'],
    install_requires=[
        'pywin32;platform_system=="Windows"',
    ],
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: MacOS',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Games/Entertainment',
        'Topic :: Multimedia',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Video',
        'Topic :: Utilities',
    ],
)
