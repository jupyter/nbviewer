#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------


from pkg_resources import iter_entry_points

from tornado.log import app_log


def provider_handlers():
    """Load tornado URL handlers from an ordered list of dotted-notation modules
       which contain a `default_handlers` function

       `default_handlers` should accept a list of handlers and returns an
       augmented list of handlers: this allows the addition of, for
       example, custom URLs which should be intercepted before being
       handed to the basic `url` handler
    """
    return _load_provider_feature(_load_feature_entry_points("handlers"))


def provider_uri_rewrites():
    """Load (regex, template) tuples from an ordered list of setup_tools
       entry_points which contain a `uri_rewrites` function

       `uri_rewrites` should accept a list of rewrites and returns an
       augmented list of rewrites: this allows the addition of, for
       example, the greedy behavior of the `gist` and `github` providers
    """
    return _load_provider_feature(_load_feature_entry_points("uri_rewrite"))


def _load_feature_entry_points(feature):
    for provider in iter_entry_points("nbviewer.provider.{}".format(feature)):
        app_log.info("Loaded {}: {}".format(feature, provider.name))
        yield provider.load()


def _load_provider_feature(providers):
    """Load the named feature from an ordered list of setuptools entry_points
       which each implements the feature.

       The feature will be passed a list of feature implementations and must
       return that list, suitably modified.
    """
    features = []

    def _weight_comp(a, b):
        return cmp(getattr(a, "weight", 0), getattr(b, "weight", 0))

    for provider in sorted(providers, cmp=_weight_comp):
        features = provider(features)

    return features
