import unittest

import toml
import os.path

import latexpp

# thanks https://github.com/python-poetry/poetry/issues/144#issuecomment-877835259

class TestHardcodedPackageVersion(unittest.TestCase):

    def test_versions_are_in_sync(self):
        """Checks if the pyproject.toml and package.__init__.py __version__ are in sync."""

        path = os.path.join( os.path.dirname(__file__), '..', "pyproject.toml" )
        with open(path) as fpp:
            pyproject = toml.loads(fpp.read())
        pyproject_version = pyproject["tool"]["poetry"]["version"]

        package_init_version = latexpp.__version__

        self.assertEqual(package_init_version, pyproject_version)


if __name__ == '__main__':
    unittest.main()
