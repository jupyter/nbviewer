#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import json
import os
import hashlib
import pipes
import shutil
import tempfile
import sys
from tarfile import TarFile

import invoke

NOTEBOOK_VERSION = '5.7.8' # the notebook version whose LESS we will use
NOTEBOOK_CHECKSUM = '573e0ae650c5d76b18b6e564ba6d21bf321d00847de1d215b418acb64f056eb8' # sha256 checksum of notebook tarball

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

    fname = "notebook-%s.tar.gz" % NOTEBOOK_VERSION
    nb_archive = os.path.join(APP_ROOT, fname)
    if not os.path.exists(nb_archive):
        print("Downloading from pypi -> %s" % nb_archive)
        ctx.run(
            " ".join(
                map(
                    pipes.quote,
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "download",
                        "notebook=={}".format(NOTEBOOK_VERSION),
                        "--no-deps",
                        "-d",
                        APP_ROOT,
                        "--no-binary",
                        ":all:",
                    ],
                )
            )
        )
    with open(nb_archive, "rb") as f:
        checksum = hashlib.sha256(f.read()).hexdigest()
    if checksum != NOTEBOOK_CHECKSUM:
        print("Notebook sdist checksum mismatch", file=sys.stderr)
        print("Expected: %s" % NOTEBOOK_CHECKSUM, file=sys.stderr)
        print("Got: %s" % checksum, file=sys.stderr)
        sys.exit(1)
    with TarFile.open(nb_archive, 'r:gz') as nb_archive_file:
        print("Extract {0} in {1}".format(nb_archive, nb_archive_file.extractall()))


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

    for less_file in ["styles", "notebook", "slides", "custom"]:
        ctx.run(tmpl.format(less_file, *args))


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


@invoke.task
def sdist(ctx):
    bower(ctx)
    less(ctx)
    ctx.run('python setup.py sdist')


@invoke.task
def git_info(ctx):
    sys.path.insert(0, os.path.join(APP_ROOT, "nbviewer"))
    from utils import git_info, GIT_INFO_JSON
    try:
        info = git_info(APP_ROOT)
    except Exception as e:
        print("Failed to get git info", e)
        return
    print("Writing git info to %s" % GIT_INFO_JSON)
    with open(GIT_INFO_JSON, "w") as f:
        json.dump(info, f)
    sys.path.pop(0)


@invoke.task
def release(ctx):
    bower(ctx)
    less(ctx)
    ctx.run('python setup.py sdist bdist_wheel upload')
