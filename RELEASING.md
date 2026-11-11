# Releasing RT-Utils

The package version has a single source of truth in `rt_utils/_version.py`.
`pyproject.toml` reads that value statically, without importing the package.

Releases are published by the **Publish to PyPI** GitHub Actions workflow
(`.github/workflows/publish.yml`), which runs when a GitHub Release is
published. Do not upload from a laptop unless the workflow is unavailable.

## One-time setup

PyPI permissions matter here, and the two roles are not equivalent:

| Action | Maintainer | Owner |
| --- | --- | --- |
| Upload a new release | yes | yes |
| Create a project-scoped API token | yes | yes |
| Configure Trusted Publishing | **no** | yes |
| Add or change collaborators | **no** | yes |

### Using an API token (works for a Maintainer)

1. On PyPI, go to Account settings -> API tokens -> *Add API token*.
2. Set the scope to the **rt-utils** project only. Copy the `pypi-` token.
3. In GitHub, add it as the repository secret `PYPI_API_TOKEN`
   (Settings -> Secrets and variables -> Actions).
4. Optionally repeat on TestPyPI and store it as `TEST_PYPI_API_TOKEN` so the
   manual dry run works.

### Using Trusted Publishing (preferred, requires Owner)

An Owner configures this at
<https://pypi.org/manage/project/rt-utils/settings/publishing/> with:

- Owner `qurit`, repository `rt-utils`
- Workflow `publish.yml`, environment `pypi`

Then follow the instructions in the comment block at the bottom of
`.github/workflows/publish.yml` to drop the stored token.

## Release checklist

1. Bump `rt_utils/_version.py` and merge the change into `main`.
2. Confirm CI is green on `main`.
3. Optional dry run: Actions -> *Publish to PyPI* -> *Run workflow* ->
   target `testpypi`. This builds, validates and uploads to TestPyPI only.
4. Create a GitHub Release whose tag is `v<version>` (for example `v1.3.2`),
   targeting the commit you want published.
5. The workflow then builds the sdist and wheel, runs `twine check --strict`,
   verifies the tag matches `rt_utils/_version.py`, verifies the version is not
   already on PyPI, smoke-tests the wheel in a clean virtualenv, and uploads.
6. Confirm the new version appears at <https://pypi.org/project/rt-utils/>.

## Notes

PyPI distributions cannot be replaced or re-uploaded. If a bad release goes
out, yank it on PyPI and publish a new patch version. The workflow fails fast
when the tag and `_version.py` disagree, or when the version already exists,
precisely so that a mistake does not consume a version number.
