# -----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------
import os
import shlex
import sys
from subprocess import check_call

from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist


def sh(cmd):
    """Run a command, echoing what command is to be run"""
    print("Running command %s" % " ".join(map(shlex.quote, cmd)), file=sys.stderr)
    check_call(cmd)


def preflight():
    print("Building LESS", file=sys.stderr)
    sh(["invoke", "git-info"])
    sh(["npm", "install"])
    sh(["invoke", "bower"])
    sh(["invoke", "less"])


def invoke_first(cmd):
    class InvokeFirst(cmd):
        def run(self):
            preflight()
            return cmd.run(self)

    return InvokeFirst


def walk_subpkg(name):
    data_files = []
    package_dir = "nbviewer"
    for parent, dirs, files in os.walk(os.path.join(package_dir, name)):
        sub_dir = os.sep.join(
            parent.split(os.sep)[1:]
        )  # remove package_dir from the path
        for f in files:
            data_files.append(os.path.join(sub_dir, f))
    return data_files


pkg_data = {
    "nbviewer": (
        ["frontpage.json"]
        + walk_subpkg("static")
        + walk_subpkg("templates")
        + walk_subpkg("providers")
    )
}

cmdclass = {}
# run invoke prior to develop/sdist
cmdclass["develop"] = invoke_first(develop)
cmdclass["build_py"] = invoke_first(build_py)
cmdclass["sdist"] = invoke_first(sdist)


setup(
    package_data=pkg_data,
    cmdclass=cmdclass,
)
