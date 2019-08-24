# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import latexpp

# -- Project information -----------------------------------------------------

project = 'latexpp'
copyright = '2019, Philippe Faist'
author = 'Philippe Faist'
version = latexpp.__version__


# -- General configuration ---------------------------------------------------

# Master document name
master_doc = 'index'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pylatexenc': ('https://pylatexenc.readthedocs.io/en/latest/', None),
}



# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

html_theme_options = {
    # customization
    'github_button': True,
    'github_type': 'star',
    'github_count': False,
    'github_user': 'phfaist',
    'github_repo': 'latexpp',
    # appearance
    'font_family': "'IBM Plex Serif', serif",
    'font_size': "16px",
    'head_font_family': "'IBM Plex Serif', serif",
    'code_font_family': "'IBM Plex Mono', monospace",
    'code_font_size': "0.9em",
    # colors
    'body_text': 'rgb(49, 54, 60)',
    'link': 'rgb(16,90,121)',
    'link_hover': 'rgb(147,2,28)',
    'anchor': 'rgba(16,90,121,0.12)',
    'anchor_hover_bg': 'rgba(109, 137, 149, 0.12)',
    'anchor_hover_fg': 'rgb(109, 137, 149)',
#    'gray_1': 'rgb(40,40,40)',
#    'gray_2': 'rgba(0,0,0,0.06)', # color of code blocks --> pre_bg
#    'gray_3': 'blue',
    'pre_bg': 'rgba(0,0,0,0.06)',
    'sidebar_text': 'rgb(40,40,50)',
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = [ '_static' ]
