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
def less():
    tmpl = ("cd nbviewer/static/less && lessc --include-path={0} "
            "{1}.less ../build/{1}.css")

    [
        invoke.run(tmpl.format(DEFAULT_STATIC_FILES_PATH, less_file))
        for less_file in ["styles", "notebook"]
    ]
