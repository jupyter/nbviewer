#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

from pkg_resources import iter_entry_points

from tornado.log import app_log


FEATURES = ["handlers", "uri_rewrite"]
BUNDLED = ["dropbox", "gist", "github", "url"]
ENABLED = []


def provider_init_enabled(options):
    """Updates the icky global of enabled entry point names based on the
       command line options.

       If no options are provided, enable all bundled.
    """
    for feature in FEATURES:
        for ep in iter_entry_points(_entry_point(feature)):
            if ep.name in ENABLED:
                continue

            enabled = None
            opt_with = _with_opt(ep.name)

            if opt_with in options:
                enabled = options[opt_with]

            if enabled:
                ENABLED.append(ep.name)


def provider_handlers():
    """Load tornado URL handlers from an ordered list of dotted-notation modules
       which contain a `default_handlers` function

       `default_handlers` should accept a list of handlers and returns an
       augmented list of handlers: this allows the addition of, for
       example, custom URLs which should be intercepted before being
       handed to the basic `url` handler
    """
    return _provider_feature(_feature_entry_points("handlers"))


def provider_uri_rewrites():
    """Load (regex, template) tuples from an ordered list of setup_tools
       entry_points which contain a `uri_rewrites` function

       `uri_rewrites` should accept a list of rewrites and returns an
       augmented list of rewrites: this allows the addition of, for
       example, the greedy behavior of the `gist` and `github` providers
    """
    return _provider_feature(_feature_entry_points("uri_rewrite"))


def _entry_point(feature):
    """Format the entry_point category consistently
    """
    return "nbviewer.provider.{}".format(feature)


def _with_opt(ep_name):
    """Format the command line options consistently
    """
    return "with_{}".format(ep_name)


def provider_config_options(define):
    """Find all of the providers with all features, and generate the inputs
       to `tornado.options.define`
    """

    ep_names = []

    for feature in FEATURES:
        for ep in iter_entry_points(_entry_point(feature)):
            if ep.name in ep_names:
                continue

            define(
                name=_with_opt(ep.name),
                default=ep.name in BUNDLED,
                help="Enable the {} provider".format(ep.name),
                group="provider"
            )
            ep_names.append(ep.name)


def _feature_entry_points(feature):
    """Load those feature entry points previously enabled
    """
    if ENABLED:
        enabled = ENABLED
    else:
        enabled = BUNDLED

    for ep in iter_entry_points(_entry_point(feature)):
        if ep.name in enabled:
            app_log.info("Loaded {}: {}".format(feature, ep.name))
            yield ep.load()


def _provider_feature(providers):
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
