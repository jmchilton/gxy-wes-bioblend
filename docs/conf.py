import os
import sys

cwd = os.getcwd()
project_root = os.path.dirname(cwd)
sys.path.insert(0, project_root)

import gxy_wes_bioblend as project_module  # noqa: E402

# -- General configuration ---------------------------------------------

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinxarg.ext",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
    "bioblend": ("https://bioblend.readthedocs.io/en/latest/", None),
}

source_suffix = [".rst", ".md"]
master_doc = "index"

project = "gxy-wes-bioblend"
copyright = "2026, Galaxy Project and Community"

version = project_module.__version__
release = project_module.__version__

exclude_patterns = ["_build"]
pygments_style = "default"

# -- Options for HTML output -------------------------------------------

html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "logo": {"text": "gxy-wes-bioblend"},
    "navbar_align": "left",
    "show_prev_next": True,
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/jmchilton/gxy-wes-bioblend",
            "icon": "fa-brands fa-github",
        },
        {
            "name": "Galaxy Project",
            "url": "https://galaxyproject.org",
            "icon": "fa-solid fa-globe",
        },
    ],
    "navigation_with_keys": True,
}
html_title = "gxy-wes-bioblend"
html_short_title = "gxy-wes-bioblend"
htmlhelp_basename = "gxywesbioblenddoc"
