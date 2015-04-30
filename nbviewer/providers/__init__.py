#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

default_providers = ['nbviewer.providers.{}'.format(prov)
                     for prov in ['url', 'github', 'gist']]

default_rewrites = ['nbviewer.providers.{}'.format(prov)
                    for prov in ['gist', 'github', 'dropbox', 'url']]


def provider_handlers(providers=None):
    """Load tornado URL handlers from an ordered list of dotted-notation modules
       which contain a `default_handlers` function

       `default_handlers` should accept a list of handlers and returns an
       augmented list of handlers: this allows the addition of, for
       example, custom URLs which should be intercepted before being
       handed to the basic `url` handler
    """
    return _load_provider_feature('default_handlers',
                                  providers,
                                  default_providers)


def provider_uri_rewrites(providers=None):
    """Load (regex, template) tuples from an ordered list of dotted-notation
       modules which contain a `uri_rewrites` function

       `uri_rewrites` should accept a list of rewrites and returns an
       augmented list of rewrites: this allows the addition of, for
       example, the greedy behavior of the `gist` and `github` providers
    """
    return _load_provider_feature('uri_rewrites', providers, default_rewrites)


def _load_provider_feature(feature, providers, default_providers):
    """Load the named feature from an ordered list of dotted-notation modules
       which each implements the feature.

       The feature will be passed a list of feature implementations and must
       return that list, suitably modified.
    """
    features = []

    providers = providers or default_providers

    for provider in providers:
        mod = __import__(provider, fromlist=[feature])
        features = getattr(mod, feature)(features)

    return features
