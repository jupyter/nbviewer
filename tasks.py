#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import shutil
import tempfile

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


@invoke.task
def screenshots(root="http://localhost:5000/", dest="./screenshots"):
    dest = os.path.abspath(dest)

    script = """
        root = "{root}"

        urls = ({{name, url}} for name, url of {{
            home: ""
            dir: "github/ipython/ipython/tree/3.x/examples/"
            user: "github/ipython/"
            gists: "gist/fperez/"
            notebook: "github/ipython/ipython/blob/3.x/examples/Notebook/Notebook%20Basics.ipynb"}})

        screens = ({{name, w, h}} for name, [w, h] of {{
            smartphone_portrait: [320, 480]
            smartphone_landscape: [480, 320]
            tablet_portrait: [768, 1024]
            tablet_landscape: [1024, 768]
            desktop_standard: [1280, 1024]
            desktop_1080p: [1920, 1080]
        }})
        
        casper.start root

        casper.each screens, (_, screen) ->
            @then ->
                @viewport screen.w, screen.h, ->
            _.each urls, (_, page) ->
                @thenOpen root + page.url, ->
                    @wait 1000
                @then ->
                    @echo "#{{page.name}} #{{screen.name}}"
                    @capture "{dest}/#{{page.name}}-#{{screen.name}}.png"

        casper.run()
    """.format(root=root, dest=dest)
    
    tmpdir = tempfile.mkdtemp()
    tmpfile = os.path.join(tmpdir, "screenshots.coffee")
    with open(tmpfile, "w+") as f:
        f.write(script)
    invoke.run("casperjs test {script}".format(script=tmpfile))
    
    shutil.rmtree(tmpdir)