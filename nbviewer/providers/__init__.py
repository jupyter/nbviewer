# -----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------

default_providers = [
    "nbviewer.providers.{}".format(prov) for prov in ["url", "github", "gist"]
]

default_rewrites = [
    "nbviewer.providers.{}".format(prov)
    for prov in ["gist", "github", "dropbox", "url"]
]


def provider_handlers(providers, **handler_kwargs):
    """Load tornado URL handlers from an ordered list of dotted-notation modules
     which contain a `default_handlers` function

     `default_handlers` should accept a list of handlers and returns an
     augmented list of handlers: this allows the addition of, for
     example, custom URLs which should be intercepted before being
     handed to the basic `url` handler

    `handler_kwargs` is a dict of dicts: first dict is `handler_names`, which
    specifies the handler_classes to load for the providers, the second
    is `handler_settings` (see comments in `format_handlers` in nbviewer/handlers.py)
    """
    handler_names = handler_kwargs["handler_names"]
    handler_settings = handler_kwargs["handler_settings"]

    urlspecs = _load_provider_feature("default_handlers", providers, **handler_names)
    for handler_setting in handler_settings:
        if handler_settings[handler_setting]:
            # here we modify the URLSpec dict to have the key-value pairs from
            # handler_settings in NBViewer.init_tornado_application
            # kwargs passed to initialize are None by default but can be added
            # https://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.initialize
            for urlspec in urlspecs:
                urlspec[2][handler_setting] = handler_settings[handler_setting]
    return urlspecs


def provider_uri_rewrites(providers):
    """Load (regex, template) tuples from an ordered list of dotted-notation
    modules which contain a `uri_rewrites` function

    `uri_rewrites` should accept a list of rewrites and returns an
    augmented list of rewrites: this allows the addition of, for
    example, the greedy behavior of the `gist` and `github` providers
    """
    return _load_provider_feature("uri_rewrites", providers)


def _load_provider_feature(feature, providers, **handler_names):
    """Load the named feature from an ordered list of dotted-notation modules
     which each implements the feature.

     The feature will be passed a list of feature implementations and must
     return that list, suitably modified.

    `handler_names` is the same as the `handler_names` attribute of the NBViewer class
    """

    # Ex: provider = 'nbviewer.providers.url'
    # provider.rsplit(',', 1) = ['nbviewer.providers', 'url']
    # provider_type = 'url'
    provider_types = [provider.rsplit(".", 1)[-1] for provider in providers]

    if "github" in provider_types:
        provider_types.append("github_blob")
        provider_types.append("github_tree")
        provider_types.remove("github")

    provider_handlers = {}

    # Ex: provider_type = 'url'
    for provider_type in provider_types:
        # Ex: provider_handler_key = 'url_handler'
        provider_handler_key = provider_type + "_handler"
        try:
            # Ex: handler_names['url_handler']
            handler_names[provider_handler_key]
        except KeyError as e:
            continue
        else:
            # Ex: provider_handlers['url_handler'] = handler_names['url_handler']
            provider_handlers[provider_handler_key] = handler_names[
                provider_handler_key
            ]

    features = []

    # Ex: provider = 'nbviewer.providers.url'
    for provider in providers:
        # Ex: module = __import__('nbviewer.providers.url', fromlist=['default_handlers'])
        module = __import__(provider, fromlist=[feature])
        # Ex: getattr(module, 'default_handlers') = the `default_handlers` function from
        # nbviewer.providers.url (in handlers.py of nbviewer/providers/url)
        # so in example, features = nbviewer.providers.url.default_handlers(list_of_already_loaded_handlers, **handler_names)
        # => features = list_of_already_loaded_handlers + [URLSpec of chosen URL handler]
        features = getattr(module, feature)(features, **handler_names)
    return features


def _load_handler_from_location(handler_location):
    # Ex: handler_location = 'nbviewer.providers.url.URLHandler'
    # module_name = 'nbviewer.providers.url', handler_name = 'URLHandler'
    module_name, handler_name = tuple(handler_location.rsplit(".", 1))

    module = __import__(module_name, fromlist=[handler_name])
    handler = getattr(module, handler_name)
    return handler
