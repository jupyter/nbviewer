#!/usr/bin/env python
# -*- coding: utf-8 -*-

import invoke
from IPython.html import DEFAULT_STATIC_FILES_PATH

@invoke.task
def test():
    invoke.run("nosetests -v")


@invoke.task
def bower():
    invoke.run("cd nbviewer/static && "
               "bower install --config.interactive=false --allow-root")


@invoke.task
def less(debug=False):
    if debug:
        extra_args = "--source-map"
    else:
        extra_args = "--compress"

    tmpl = (
        "cd nbviewer/static/less && lessc {1} --include-path={2} "
        "{0}.less ../build/{0}.css"
    )

    args = (extra_args, DEFAULT_STATIC_FILES_PATH)

    [
        invoke.run(tmpl.format(less_file, *args))
        for less_file in ["styles", "notebook"]
    ]
