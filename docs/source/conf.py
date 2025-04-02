# conf.py

import os
import sys
from recommonmark.parser import CommonMarkParser

# Add your project directory to the sys.path
# sys.path.insert(0, os.path.abspath('../../pandora'))

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Pandora Box'
html_title = 'Pandora Box Documentation'
html_short_title = 'Pandora'

copyright = '2025, Johnny H. Esteves'
author = 'Johnny H. Esteves'
release = '0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# General configuration
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinxcontrib.programoutput',
    'recommonmark',
    'sphinx_wagtail_theme',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.autosummary',
    'sphinx.ext.autodoc.typehints'
]
autodoc_mock_imports = ['labjack']

templates_path = ['_templates']
exclude_patterns = []
autosummary_generate = True  # Optional: auto-generate summary files


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_wagtail_theme'
html_show_sphinx = False

html_theme_options = dict(
    header_links = "Github Repo|https://github.com/stubbslab/PANDORA/tree/v1.0",
    footer_links = ",".join([
        "About Us|http://example.com/",
        "Contact|http://example.com/contact",
        "Legal|http://example.com/dev/null",
    ]),
    # site_name = 'Pandora Box',
    # html_title = 'Pandora Box Documentation',
    # html_short_title = 'Pandora',
    project_name = 'Pandora Box',
    # project_subtitle = 'Version 0.1',
 )
# html_theme = 'pydata_sphinx_theme'
# import sphinx_theme_pd
# html_theme = 'sphinx_theme_pd'
# html_theme_path = [sphinx_theme_pd.get_html_theme_path()]

# pygments_style = 'murphy'
# pygments_dark_style = 'colorful'
html_static_path = ['_static']


# Configure recommonmark
source_parsers = {
    '.md': CommonMarkParser,
}