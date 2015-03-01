#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import invoke
from IPython.html import DEFAULT_STATIC_FILES_PATH


APP_ROOT = os.path.dirname(__file__)
NPM_BIN = os.path.join(APP_ROOT, "node_modules", ".bin")


@invoke.task
def test():
    invoke.run("nosetests -v")


@invoke.task
def bower():
    invoke.run(
        "cd {}/nbviewer/static &&".format(APP_ROOT) +
        " {}/bower install".format(NPM_BIN) +
        " --config.interactive=false --allow-root"
    )


@invoke.task
def less(debug=False):
    if debug:
        extra = "--source-map"
    else:
        extra = " --clean-css='--s1 --advanced --compatibility=ie8'"


    tmpl = (
    "cd {}/nbviewer/static/less ".format(APP_ROOT) +
    " && {}/lessc".format(NPM_BIN) +
    " {1} "
    " --include-path={2}"
    " --autoprefix='> 1%'"
    " {0}.less ../build/{0}.css"
    )

    args = (extra, DEFAULT_STATIC_FILES_PATH)

    [
        invoke.run(tmpl.format(less_file, *args))
        for less_file in ["styles", "notebook"]
    ]
