import os
from datetime import datetime
import xmltodict
import shutil
import subprocess
import tempfile

from lxml.etree import tostring
from citeproc import CitationStylesStyle
from logging import getLogger

import ckan.plugins as plugins
from ckan.common import CKANConfig

from typing import Dict, Union, Callable, Any
from ckan.types import (
    Action,
    ChainedAction,
    AuthFunction,
    ChainedAuthFunction,
    DataDict
)

from ckan.lib.plugins import DefaultTranslation

from ckanext.citeproc.interfaces import ICiteProcStyles, ICiteProcMappings
from ckanext.citeproc.logic import action, auth
from ckanext.citeproc import helpers


log = getLogger(__name__)


class CiteProcPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(ICiteProcStyles, inherit=True)
    plugins.implements(ICiteProcMappings)
    plugins.implements(plugins.ITranslation, inherit=True)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.ITemplateHelpers, inherit=True)

    citation_styles = []

    # ICiteProcStyles
    def load_citation_styles(self):
        citation_styles_dir = plugins.toolkit.config.get(
            'ckanext.citeproc.citation_styles_path',
            os.path.join(os.path.dirname(__file__), 'csl_styles')
        )
        # Check if directory exists and has CSL files
        if not os.path.isdir(citation_styles_dir) or not any(
            f.endswith('.csl')
            for f in os.listdir(citation_styles_dir)
            if os.path.isfile(os.path.join(citation_styles_dir, f))
        ):
            log.info('No CSL files found in %s. Downloading styles...',
                     citation_styles_dir)
            # Ensure the directory exists
            if not os.path.isdir(citation_styles_dir):
                os.makedirs(citation_styles_dir)

            # Clone repository to temp dir and copy CSL files
            with tempfile.TemporaryDirectory() as tmpdirname:
                try:
                    subprocess.check_call(
                        ['git', 'clone',
                         'https://github.com/citation-style-language/styles.git',
                         tmpdirname]
                    )
                    # Copy only .csl files (not the entire git history)
                    for root, _, files in os.walk(tmpdirname):
                        for f in files:
                            if f.endswith('.csl'):
                                shutil.copy(
                                    os.path.join(root, f),
                                    os.path.join(citation_styles_dir, f)
                                )
                    log.info('Successfully downloaded CSL files to %s',
                             citation_styles_dir)
                except (subprocess.SubprocessError, OSError) as e:
                    log.error('Failed to download CSL files: %s', str(e))
                    raise RuntimeError(
                        'Failed to download CSL files. Please check the '
                        'configuration or manually place CSL files in %s' %
                        citation_styles_dir
                    )
        # Load CSL files from the directory
        for f in os.listdir(citation_styles_dir):
            if f.endswith('.csl'):
                bib_style = CitationStylesStyle(os.path.join(citation_styles_dir, f),
                                                validate=False)
                style_info = xmltodict.parse(tostring(bib_style.xml))
                style_info = style_info.get(
                    'style', {}).get('info', {}) if style_info else {}
                self.citation_styles.append({
                    'type': style_info.get('title'),
                    'type_acronym': style_info.get('title-short'),
                    'type_summary': style_info.get('summary'),
                    'class': bib_style})
        # Sort citation styles alphabetically by title
        self.citation_styles.sort(key=lambda x: x['type'].lower() if x['type'] else '')
        # Log the number of loaded citation styles
        log.debug('Loaded %s citation styles from %s' %
                  (len(self.citation_styles), citation_styles_dir))

    # ICiteProcMappings
    def update_dataset_citation_map(self, cite_data: DataDict,
                                    pkg_dict: DataDict) -> bool:
        lang = 'en'
        try:
            lang = plugins.toolkit.h.lang()
        except RuntimeError:
            pass
        cite_data['title'] = pkg_dict.get('title_translated', {}).get(
            lang, pkg_dict['title'])
        cite_data['container_title'] = plugins.toolkit.config.get('ckan.site_title')
        if pkg_dict.get('owner_org'):
            org_dict = plugins.toolkit.get_action('organization_show')(
                {'ignore_auth': True}, {'id': pkg_dict.get('owner_org')})
            cite_data['publisher'] = org_dict.get('title_translated', {}).get(
                lang, org_dict['title'])
        created_date = datetime.fromisoformat(pkg_dict['metadata_created'])
        cite_data['issued'] = {
            'date-parts': [[created_date.year, created_date.month, created_date.month]]
        }
        cite_data['URL'] = plugins.toolkit.h.url_for('%s.read' % pkg_dict['type'],
                                                     _external=True,
                                                     id=pkg_dict['id'])
        return True

    def update_resource_citation_map(self, cite_data: DataDict,
                                     pkg_dict: DataDict,
                                     res_dict: DataDict) -> bool:
        lang = 'en'
        try:
            lang = plugins.toolkit.h.lang()
        except RuntimeError:
            pass
        cite_data['title'] = pkg_dict.get('title_translated', {}).get(
            lang, pkg_dict['title']) + ' - ' + res_dict.get('name_translated', {}).get(
                lang, res_dict['name'])
        cite_data['container_title'] = plugins.toolkit.config.get('ckan.site_title')
        if pkg_dict.get('owner_org'):
            org_dict = plugins.toolkit.get_action('organization_show')(
                {'ignore_auth': True}, {'id': pkg_dict.get('owner_org')})
            cite_data['publisher'] = org_dict.get('title_translated', {}).get(
                lang, org_dict['title'])
        created_date = datetime.fromisoformat(res_dict['created'])
        cite_data['issued'] = {
            'date-parts': [[created_date.year, created_date.month, created_date.month]]
        }
        cite_data['URL'] = plugins.toolkit.h.url_for('%s_resource.read' %
                                                     pkg_dict['type'],
                                                     _external=True,
                                                     package_type=pkg_dict['type'],
                                                     id=pkg_dict['id'],
                                                     resource_id=res_dict['id'])
        return True

    # DefaultTranslation, ITranslation
    def i18n_domain(self) -> str:
        return 'ckanext-citeproc'

    # IConfigurer
    def update_config(self, config: 'CKANConfig'):
        plugins.toolkit.add_template_directory(config, 'templates')
        plugins.toolkit.add_resource('assets', 'ckanext-citeproc')
        self.load_citation_styles()

    # IActions
    def get_actions(self) -> Dict[str, Union[Action, ChainedAction]]:
        return {
            'dataset_citation_show': action.dataset_citation_show,
            'resource_citation_show': action.resource_citation_show,
        }

    # IAuthFunctions
    def get_auth_functions(self) -> Dict[str, Union[AuthFunction,
                                                    ChainedAuthFunction]]:
        return {
            'dataset_citation_show': auth.dataset_citation_show,
            'resource_citation_show': auth.resource_citation_show,
        }

    # ITemplateHelpers
    def get_helpers(self) -> Dict[str, Callable[..., Any]]:
        return {'show_citations_for': helpers.show_citations_for}
