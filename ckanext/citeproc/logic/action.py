from datetime import datetime

from citeproc import CitationStylesBibliography
from citeproc import Citation, CitationItem
from citeproc import formatter, PRIMARY_DIALECTS
from citeproc.types import WEBPAGE
from citeproc.source.json import CiteProcJSON
from logging import getLogger
from flask import has_request_context

from typing import Dict, Any, List
from ckan.types import (
    Context,
    DataDict
)

from ckan.plugins import PluginImplementations
from ckan.plugins.toolkit import (
    side_effect_free,
    check_access,
    navl_validate,
    ValidationError,
    get_action,
    h,
    _
)
from ckanext.citeproc.interfaces import ICiteProcStyles, ICiteProcMappings
from ckanext.citeproc.logic.schema import (
    dataset_citation_show_schema,
    resource_citation_show_schema
)


log = getLogger(__name__)


def _get_plugin():
    """
    Find the CiteProc instance
    """
    for plugin in PluginImplementations(ICiteProcStyles):
        return plugin
    raise Exception('CiteProc plugin not found. Have you enabled the plugin?')


def _generate_citations(id: str,
                        format: str,
                        cite_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    citations = []
    citation_styles = _get_plugin().citation_styles
    bib_source = CiteProcJSON(cite_data)

    def _log_cite_failure(_cite: CitationItem):
        log.debug('Reference with key {} not found in '
                  'the bibliography.'.format(_cite.key))

    for citation_style in citation_styles:
        try:
            citation_style_class = citation_style.get('class')
            locale = 'en-US'
            if has_request_context() and h.lang() in PRIMARY_DIALECTS:
                locale = PRIMARY_DIALECTS[h.lang()]
            citation_style_class.root.set_locale_list(locale, validate=False)
            bibliography = CitationStylesBibliography(citation_style_class,
                                                      bib_source,
                                                      getattr(formatter, format))
            citation = Citation([CitationItem(id)])
            bibliography.register(citation)
            bibliography.cite(citation, _log_cite_failure)
            try:
                # not all CSL styles have bibliography.
                citation = bibliography.bibliography()[0]
            except Exception:
                log.debug('CSL style "%s" does not support bibliography.' %
                          citation_style['type'])
                continue
            citations.append({
                'type': _(citation_style['type']),
                'type_acronym': _(citation_style['type_acronym']),
                'type_summary': _(citation_style['type_summary']),
                'citation': str(citation)
            })
        except Exception as e:
            # FIXME: https://github.com/citeproc-py/citeproc-py/issues/101
            # FIXED_WITH: https://github.com/citeproc-py/citeproc-py/pull/156
            log.warning('Could not generate citation for %s in the style "%s"' %
                        (id, citation_style['type']))
            log.warning(e)
            pass
    return citations


@side_effect_free
def dataset_citation_show(context: Context,
                          data_dict: DataDict) -> List[Dict[str, Any]]:
    check_access('dataset_citation_show', context, data_dict)

    schema = dataset_citation_show_schema()

    data, errors = navl_validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    pkg_dict = get_action('package_show')(context, {'id': data['id']})

    date_now = datetime.now()
    cite_data = {
        'type': WEBPAGE,
        'accessed': {
            'date-parts': [[date_now.year, date_now.month, date_now.day]]
        }
    }
    for plugin in PluginImplementations(ICiteProcMappings):
        do_next_plugins = plugin.update_dataset_citation_map(
            cite_data, pkg_dict)
        if not do_next_plugins:
            break
    # non-editable ID
    cite_data['id'] = data['id']

    return _generate_citations(data['id'], data['format'], [cite_data])


@side_effect_free
def resource_citation_show(context: Context,
                           data_dict: DataDict) -> List[Dict[str, Any]]:
    check_access('resource_citation_show', context, data_dict)

    schema = resource_citation_show_schema()

    data, errors = navl_validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    res_dict = get_action('resource_show')(context, {'id': data['id']})
    pkg_dict = get_action('package_show')(context, {'id': res_dict['package_id']})

    date_now = datetime.now()
    cite_data = {
        'type': WEBPAGE,
        'accessed': {
            'date-parts': [[date_now.year, date_now.month, date_now.day]]
        }
    }
    for plugin in PluginImplementations(ICiteProcMappings):
        do_next_plugins = plugin.update_resource_citation_map(
            cite_data, pkg_dict, res_dict)
        if not do_next_plugins:
            break
    # non-editable ID
    cite_data['id'] = data['id']

    return _generate_citations(data['id'], data['format'], [cite_data])
