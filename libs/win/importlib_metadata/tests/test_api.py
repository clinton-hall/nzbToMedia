import re
import unittest

import importlib_metadata


class APITests(unittest.TestCase):
    version_pattern = r'\d+\.\d+(\.\d)?'

    def test_retrieves_version_of_self(self):
        version = importlib_metadata.version('importlib_metadata')
        assert isinstance(version, str)
        assert re.match(self.version_pattern, version)

    def test_retrieves_version_of_pip(self):
        # Assume pip is installed and retrieve the version of pip.
        version = importlib_metadata.version('pip')
        assert isinstance(version, str)
        assert re.match(self.version_pattern, version)

    def test_for_name_does_not_exist(self):
        with self.assertRaises(importlib_metadata.PackageNotFoundError):
            importlib_metadata.distribution('does-not-exist')

    def test_for_top_level(self):
        distribution = importlib_metadata.distribution('importlib_metadata')
        self.assertEqual(
            distribution.read_text('top_level.txt').strip(),
            'importlib_metadata')

    def test_entry_points(self):
        parser = importlib_metadata.entry_points('pip')
        # We should probably not be dependent on a third party package's
        # internal API staying stable.
        entry_point = parser.get('console_scripts', 'pip')
        self.assertEqual(entry_point, 'pip._internal:main')

    def test_metadata_for_this_package(self):
        md = importlib_metadata.metadata('importlib_metadata')
        assert md['author'] == 'Barry Warsaw'
        assert md['LICENSE'] == 'Apache Software License'
        assert md['Name'] == 'importlib-metadata'
        classifiers = md.get_all('Classifier')
        assert 'Topic :: Software Development :: Libraries' in classifiers
