[![Tests](https://github.com/open-data/ckanext-citeproc/workflows/Tests/badge.svg?branch=main)](https://github.com/open-data/ckanext-citeproc/actions)

# CKANEXT CiteProc

CKAN plugin to add citations to datasets and resources. This plugin uses https://github.com/citeproc-py/citeproc-py to generate citations in different formats.

## Requirements

Compatibility with core CKAN versions:

| CKAN version    | Compatible?   |
| --------------- | ------------- |
| 2.6 and earlier | no    |
| 2.7             | no    |
| 2.8             | no    |
| 2.9             | no    |
| 2.10             | yes    |
| 2.11             | yes    |
| 2.12             | yes    |

Compatibility with Python versions:

| Python version    | Compatible?   |
| --------------- | ------------- |
| 2.7 and earlier | no    |
| 3.10 and later           | yes    |

## Prerequisites

This extension bundles CSL styles in `ckanext/citeproc/csl_styles`.
You can optionally configure a custom directory. citeproc-py itself only contains `harvard1.csl` for the styles. To allow for more styles, you will need to put any desired CSL files from https://github.com/citation-style-language/styles onto your server and define the citeproc style path with `ckanext.citeproc.citation_styles_path` in your CKAN INI file. The available citation formats will be built from any CSL files in this directory.

## Installation

To install ckanext-citeproc:

1. Activate your CKAN virtual environment, for example:

     . /usr/lib/ckan/default/bin/activate

2. Clone the source and install it on the virtualenv:
  ```
  git clone --recurse-submodules https://github.com/open-data/ckanext-citeproc.git
  cd ckanext-citeproc
  pip install -e .
  ```
3. Add `citeproc` to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/ckan.ini`).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

     sudo service apache2 reload

## Config settings

**ckanext.citeproc.citation_styles_path** specifies the absolute path on the server to the directory containing the CSL files:

	# (optional, default: bundled csl_styles directory).
	ckanext.citeproc.citation_styles_path = /path/to/csl/styles/directory/

**ckanext.citeproc.<PACKAGE TYPE>_show_citations** controls citations showing for datasets of a given package type:

	# (optional, default: true).
	ckanext.citeproc.dataset_show_citations = false

**ckanext.citeproc.<PACKAGE TYPE>_resource_show_citations** controls citations showing for resources of a given package type:

	# (optional, default: true).
	ckanext.citeproc.dataset_resource_show_citations = false

## CKAN 2.12

Use Python 3.10 or later. Install this extension with `pip install -e .`;
citation dependencies are installed automatically. Keep `citeproc` in
`ckan.plugins` and restart CKAN after updating the extension.

The citation endpoints use GET requests and do not require a CSRF exemption.
Anonymous users can cite public datasets and resources; CKAN's normal access
checks still apply to private data.

Run the compatibility tests in a CKAN 2.12 virtual environment with:

```sh
pip install pytest
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest
```

These tests do not require PostgreSQL, Solr or Redis. They check plugin loading,
configuration declarations, citation generation and access delegation.
