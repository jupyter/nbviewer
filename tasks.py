#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import hashlib
import shutil
import tempfile
import sys
from zipfile import ZipFile
import pip

import invoke

NOTEBOOK_VERSION = '4.1.0' # the notebook version whose LESS we will use
NOTEBOOK_CHECKSUM = '24cac518544caaeca34b39931cbc1a4ac580078f2044ba09adb9dee01a72dc84' # sha256 checksum of notebook tarball

APP_ROOT = os.path.dirname(__file__)
NPM_BIN = os.path.join(APP_ROOT, "node_modules", ".bin")
NOTEBOOK_STATIC_PATH = os.path.join(APP_ROOT, 'notebook-%s' % NOTEBOOK_VERSION, 'notebook', 'static')


@invoke.task
def test(ctx):
    ctx.run("nosetests -v")


@invoke.task
def bower(ctx):
    ctx.run(
        "cd {}/nbviewer/static &&".format(APP_ROOT) +
        " {}/bower install".format(NPM_BIN) +
        " --config.interactive=false --allow-root"
    )


@invoke.task
def notebook_static(ctx):
    if os.path.exists(NOTEBOOK_STATIC_PATH):
        return
    fname = 'notebook-%s.zip' % NOTEBOOK_VERSION
    nb_zip = os.path.join(APP_ROOT, fname)
    if not os.path.exists(nb_zip):
        print("Downloading from pypi -> %s" % nb_zip)
        pip.main(['download', 'notebook=={}'.format(NOTEBOOK_VERSION), '--no-deps', '-d', APP_ROOT, '--no-binary', ':all:'])
    with open(nb_zip, 'rb') as f:
        checksum = hashlib.sha256(f.read()).hexdigest()
    if checksum != NOTEBOOK_CHECKSUM:
        print("Notebook zipfile checksum mismatch", file=sys.stderr)
        print("Expected: %s" % NOTEBOOK_CHECKSUM, file=sys.stderr)
        print("Got: %s" % checksum, file=sys.stderr)
        sys.exit(1)
    with ZipFile(nb_zip, 'r') as nb_zip_file:
        print("Extract {0} in {1}".format(nb_zip, nb_zip_file.extractall()))


@invoke.task
def less(ctx, debug=False):
    notebook_static(ctx)
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

    args = (extra, NOTEBOOK_STATIC_PATH)

    [
        ctx.run(tmpl.format(less_file, *args))
        for less_file in ["styles", "notebook", "slides"]
    ]


@invoke.task
def screenshots(ctx, root="http://localhost:5000/", dest="./screenshots"):
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
    ctx.run("casperjs test {script}".format(script=tmpfile))

    shutil.rmtree(tmpdir)
