from ckan.types import Context, DataDict, AuthResult

from ckan.authz import is_authorized
from ckan.plugins.toolkit import auth_allow_anonymous_access


@auth_allow_anonymous_access
def dataset_citation_show(context: Context,
                          data_dict: DataDict) -> AuthResult:
    return is_authorized('package_show', context, data_dict)


@auth_allow_anonymous_access
def resource_citation_show(context: Context,
                           data_dict: DataDict) -> AuthResult:
    return is_authorized('resource_show', context, data_dict)
