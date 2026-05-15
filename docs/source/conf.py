# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import importlib.metadata

# -- Project information -----------------------------------------------------

project = 'argclz'
copyright = '2025, Yu-Ting Wei'
author = 'Yu-Ting Wei'
release = importlib.metadata.version('argclz')
version = '.'.join(release.split('.')[:2])

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx_prompt',
    'sphinx_copybutton',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

templates_path = ['_templates']
exclude_patterns = []

# -- Options for autodoc ------------------------------------------------
autodoc_member_order = 'bysource'
autodoc_class_signature = 'separated'
autodoc_typehints = 'description'
autodoc_typehints_format = 'short'
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'inherited-members': True,
    'show-inheritance': True,
}

# -- Options for autosummary ------------------------------------------------
autosummary_generate = True

# -- Options for HTML output -------------------------------------------------

html_theme = 'pydata_sphinx_theme'
html_static_path = ['_static']
html_theme_options = {
    'navigation_depth': 2,
    'show_toc_level': 4,
    'github_url': 'https://github.com/ytsimon2004/argclz',
    'show_prev_next': True,
    'back_to_top_button': True,
    'collapse_navigation': False,
    'sidebar_includehidden': True,
    'secondary_sidebar_items': [
        'page-toc',
        'edit-this-page',
        'sourcelink',
    ],
    'use_edit_page_button': True,
}

html_context = {
    'github_user': 'ytsimon2004',
    'github_repo': 'argclz',
    'github_version': 'main',
    'doc_path': 'docs/source',
}

# -- Copy Button --------------------------------
copybutton_prompt_text = r'^\$ '
copybutton_prompt_is_regexp = True
copybutton_remove_prompts = True
