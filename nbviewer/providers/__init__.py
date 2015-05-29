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
    """
    for feature in FEATURES:
        for ep in iter_entry_points(_entry_point(feature)):
            if ep.name in ENABLED:
                continue

            enabled = None
            opt_with, opt_without = _with_opts(ep.name)

            if opt_with in options:
                enabled = options[opt_with]
            else:
                enabled = not options[opt_without]

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


def _with_opts(ep_name):
    """Format the command line options consistently
    """
    return [base.format(ep_name) for base in ["with_{}", "without_{}"]]


def provider_config_options(define):
    """Find all of the providers with all features, and generate the inputs
       to `tornado.options.define`
    """

    ep_names = []

    for feature in FEATURES:
        for ep in iter_entry_points(_entry_point(feature)):
            if ep.name in ep_names:
                continue

            opt_with, opt_without = _with_opts(ep.name)
            if ep.name in BUNDLED:
                define(
                    name=opt_without,
                    default=False,
                    help="Disable the {} provider".format(ep.name),
                    group="provider"
                )
            else:
                define(
                    name=opt_with,
                    default=False,
                    help="Enable the {} provider".format(ep.name),
                    group="provider"
                )
            ep_names.append(ep.name)


def _feature_entry_points(feature):
    """Load those feature entry points previously enabled
    """
    for ep in iter_entry_points(_entry_point(feature)):
        if ep.name in ENABLED:
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
