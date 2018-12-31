import sys
import unittest
import importlib_metadata

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

from importlib_resources import path


class BespokeLoader:
    archive = 'bespoke'


class TestZip(unittest.TestCase):
    def setUp(self):
        # Find the path to the example.*.whl so we can add it to the front of
        # sys.path, where we'll then try to find the metadata thereof.
        self.resources = ExitStack()
        self.addCleanup(self.resources.close)
        wheel = self.resources.enter_context(
            path('importlib_metadata.tests.data',
                 'example-21.12-py3-none-any.whl'))
        sys.path.insert(0, str(wheel))
        self.resources.callback(sys.path.pop, 0)

    def test_zip_version(self):
        self.assertEqual(importlib_metadata.version('example'), '21.12')

    def test_zip_entry_points(self):
        parser = importlib_metadata.entry_points('example')
        entry_point = parser.get('console_scripts', 'example')
        self.assertEqual(entry_point, 'example:main')

    def test_missing_metadata(self):
        distribution = importlib_metadata.distribution('example')
        self.assertIsNone(distribution.read_text('does not exist'))

    def test_case_insensitive(self):
        self.assertEqual(importlib_metadata.version('Example'), '21.12')
