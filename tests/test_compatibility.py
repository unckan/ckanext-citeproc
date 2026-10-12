"""Compatibility checks using real CKAN and citeproc, without external services."""
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from ckanext.citeproc.plugin import CiteProcPlugin
from ckanext.citeproc.logic import action, auth


@pytest.fixture
def plugin():
    return CiteProcPlugin()


def test_config_declaration(plugin):
    declaration = Mock()
    plugin.declare_config_options(declaration, None)
    config_file = Path(__file__).parents[1] / 'ckanext/citeproc/config_declaration.yaml'
    options = yaml.safe_load(config_file.read_text())['groups'][0]['options']
    assert {option['key'] for option in options} >= {
        'ckanext.citeproc.citation_styles_path',
        'ckanext.citeproc.dataset_show_citations',
        'ckanext.citeproc.dataset_resource_show_citations',
    }


def test_style_loading_is_repeatable(plugin, tmp_path):
    source = Path(__file__).parents[1] / 'ckanext/citeproc/csl_styles/vancouver.csl'
    (tmp_path / 'vancouver.csl').write_bytes(source.read_bytes())
    with patch('ckanext.citeproc.plugin.plugins.toolkit.config', {
        'ckanext.citeproc.citation_styles_path': str(tmp_path),
    }):
        plugin.load_citation_styles()
        plugin.load_citation_styles()
    assert len(plugin.citation_styles) == 1
    with patch.object(action, '_get_plugin', return_value=plugin), \
            patch.object(action, '_', side_effect=lambda value: value):
        citations = action._generate_citations('example', 'plain', [{
            'id': 'example', 'type': 'webpage', 'title': 'Example dataset',
            'URL': 'https://example.org/dataset/example',
            'issued': {'date-parts': [[2026, 10, 12]]},
        }])
    assert len(citations) == 1
    assert 'Example dataset' in citations[0]['citation']


@pytest.mark.parametrize('name,delegate', [
    ('dataset_citation_show', 'package_show'),
    ('resource_citation_show', 'resource_show'),
])
@pytest.mark.parametrize('allowed', [True, False])
def test_anonymous_auth_delegates_access(name, delegate, allowed):
    context, data = {'user': None}, {'id': 'example'}
    function = getattr(auth, name)
    assert function.auth_allow_anonymous_access
    with patch.object(auth, 'is_authorized', return_value={'success': allowed}) as check:
        assert function(context, data) == {'success': allowed}
    check.assert_called_once_with(delegate, context, data)


@pytest.mark.parametrize('name,resource', [
    ('dataset_citation_show', False), ('resource_citation_show', True),
])
def test_citation_dates(plugin, name, resource):
    package = {'id': 'dataset', 'type': 'dataset', 'title': 'Dataset',
               'metadata_created': '2026-09-23T12:00:00'}
    res = {'id': 'resource', 'package_id': 'dataset', 'name': 'Resource',
           'created': '2026-09-24T12:00:00'}
    data = {'id': res['id'] if resource else package['id'], 'format': 'plain'}

    def get_action(name):
        return lambda *_: res if name == 'resource_show' else package
    with patch.object(action, 'check_access'), \
            patch.object(action, 'navl_validate', return_value=(data, {})), \
            patch.object(action, 'get_action', side_effect=get_action), \
            patch.object(action, 'PluginImplementations', return_value=[plugin]), \
            patch.object(action, '_generate_citations', return_value=[]) as generate, \
            patch('ckanext.citeproc.plugin.plugins.toolkit.h') as helpers:
        helpers.lang.return_value = 'en'
        helpers.url_for.return_value = 'https://example.org'
        getattr(action, name)({'user': None}, data)
    citation = generate.call_args.args[2][0]
    assert citation['issued']['date-parts'] == [[2026, 9, 24 if resource else 23]]
    now = datetime.now()
    assert citation['accessed']['date-parts'] == [[now.year, now.month, now.day]]
