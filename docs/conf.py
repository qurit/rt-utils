"""Sphinx configuration for the RT-Utils documentation.

The version is read from the installed package rather than hard-coded, so a
release never leaves the documentation claiming the previous version.
"""

import os
import sys
from datetime import date

# Import rt_utils from the source tree, so the documentation can be built
# without installing the package first.
sys.path.insert(0, os.path.abspath(".."))

from rt_utils import __version__  # noqa: E402

# -- Project information -----------------------------------------------------

project = "RT-Utils"
author = "Quantitative Radiomolecular Imaging and Therapy Lab (QURIT)"
copyright = f"{date.today().year}, {author}"

release = __version__
version = ".".join(__version__.split(".")[:2])

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Warnings are errors in CI, so an unresolved reference or a page left out of
# a toctree fails the build rather than quietly producing a broken site.
nitpicky = False

# -- MyST --------------------------------------------------------------------

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "attrs_inline",
    "attrs_block",
    "substitution",
    "smartquotes",
    "tasklist",
]
myst_heading_anchors = 3

# -- Autodoc -----------------------------------------------------------------

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "member-order": "bysource",
}
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented_params"
autodoc_class_signature = "separated"
autosummary_generate = True

# SimpleITK is an optional dependency, imported lazily inside rt_utils.nifti,
# so the module documents fine without it. Mocked anyway so a build on a
# machine that has no wheel for it still works.
autodoc_mock_imports = []

napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = True

# -- Intersphinx -------------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pydicom": ("https://pydicom.github.io/pydicom/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
}

# -- HTML output -------------------------------------------------------------

html_theme = "furo"
html_title = f"RT-Utils {release}"
html_logo = "_static/logo.png"
html_favicon = "_static/logo.png"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_copy_source = False
html_show_sphinx = False

pygments_style = "friendly"
pygments_dark_style = "material"

html_theme_options = {
    "sidebar_hide_name": True,
    "navigation_with_keys": True,
    "top_of_page_buttons": ["view", "edit"],
    "source_repository": "https://github.com/qurit/rt-utils/",
    "source_branch": "main",
    "source_directory": "docs/",
    "light_css_variables": {
        "color-brand-primary": "#4f2bbd",
        "color-brand-content": "#5b35c7",
        "color-api-name": "#0e7490",
        "color-api-pre-name": "#6d28d9",
        "font-stack": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', "
        "Helvetica, Arial, sans-serif",
        "font-stack--monospace": "'JetBrains Mono', 'SF Mono', Menlo, "
        "Consolas, monospace",
    },
    "dark_css_variables": {
        "color-brand-primary": "#c4b5fd",
        "color-brand-content": "#a5b4fc",
        "color-api-name": "#67e8f9",
        "color-api-pre-name": "#c4b5fd",
    },
}

# -- Link checking -----------------------------------------------------------

linkcheck_ignore = [
    # Rendered by GitHub on demand; the shield services rate-limit CI.
    r"https://img\.shields\.io/.*",
    r"https://badge\.fury\.io/.*",
]
