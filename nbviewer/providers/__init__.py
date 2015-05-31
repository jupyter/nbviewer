#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import os

from pkg_resources import iter_entry_points

from tornado.log import app_log


_cached_ep_specs = {}


def entry_point_specs():
    """Return the instances of the providers
    """
    if not _cached_ep_specs:
        _cached_ep_specs.update({
            spec.name: spec.load()(spec.name)
            for spec in iter_entry_points("nbviewer.provider")
        })

    return _cached_ep_specs


def provider_config_options(define):
    """Find all of the providers with all features, and generate the inputs
       to `tornado.options.define`.

       All options will be made configurable via environment variables,
       prefixed with `NBVIEWER_`
    """

    for name, provider in entry_point_specs().items():
        for option in provider.options():
            if "group" not in option:
                option["group"] = "provider {}".format(name)

            env_var = "NBVIEWER_{}".format(option["name"].upper())

            option["default"] = os.environ.get(
                env_var,
                option.get("default", None)
            )

            option["help"] = "{} [{}]".format(
                option.get("help", ""),
                env_var
            ).strip()

            define(**option)


def provider_init_enabled(options):
    """Updates the icky global of entry point specs based on the
       command line options/environment variables.
    """

    spec_dict = entry_point_specs()

    for name, provider in spec_dict.items():
        enabled = provider.enabled(options)
        if enabled:
            app_log.info("Provider {} enabled".format(name))
        else:
            app_log.info("Provider {} disabled".format(name))
            del spec_dict[name]


def provider_handlers(options):
    """Load tornado URL handlers from an ordered list of dotted-notation modules
       which contain a `handlers` function
    """
    return _provider_feature("handlers", options)


def provider_uri_rewrites(options):
    """Load (regex, template) tuples from an ordered list of setup_tools
       entry_points which contain a `uri_rewrites` function
    """
    return _provider_feature("uri_rewrite", options)


def _provider_feature(feature, options):
    """Load the named feature from an ordered list of providers
       which each implements the feature.

       The feature will be passed a list of feature implementations and must
       return that list, suitably modified.
    """
    items = []

    def _weight_comp(a, b):
        a_feat = getattr(a, feature)
        b_feat = getattr(b, feature)
        return cmp(getattr(a_feat, "weight", 0), getattr(b_feat, "weight", 0))

    for provider in sorted(entry_point_specs().values(), cmp=_weight_comp):
        items = getattr(provider, feature)(items, options)

    return items
