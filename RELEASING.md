# Releasing RT-Utils

The package version has a single source of truth in
`rt_utils/_version.py`. `setup.py` reads that value without importing the
package.

## Release checklist

1. Update `rt_utils/_version.py` and merge the change into `main`.
2. Run the complete test suite.
3. Build and validate both distributions:

   ```bash
   python -m build
   python -m twine check dist/*
   ```

4. Install the wheel in a clean environment and confirm `rt_utils.__version__`.
5. Upload only the artifacts for the intended version to PyPI.
6. Tag the exact published commit as `v<version>`.
7. Create the matching GitHub release from that tag.

PyPI distributions cannot be replaced. Never tag or upload from an uncommitted
or untested working tree.
