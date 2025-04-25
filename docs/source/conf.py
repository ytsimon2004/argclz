# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'argclz'
copyright = '2025, yu-ting wei'
author = 'yu-ting wei'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.autosummary',
              'sphinx_prompt',
              'sphinx_copybutton']

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
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'pydata_sphinx_theme'
html_static_path = ['_static']
html_theme_options = {
    "max_navbar_depth": 4,
    "show_toc_level": 4
}

# -- Copy Button --------------------------------
copybutton_prompt_text = r'^(>>> |\.\.\. |\$ )'
copybutton_prompt_is_regexp = True
copybutton_remove_prompts = True
