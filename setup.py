# -----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------
import os
import pipes
from distutils import log
from subprocess import check_call

from setuptools import setup
from setuptools.command.develop import develop

import versioneer


def sh(cmd):
    """Run a command, echoing what command is to be run"""
    log.info("Running command %s" % " ".join(map(pipes.quote, cmd)))
    check_call(cmd)


def preflight():
    log.info("Building LESS")
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
        ["frontpage.json", "git_info.json"]
        + walk_subpkg("static")
        + walk_subpkg("templates")
        + walk_subpkg("providers")
    )
}

cmdclass = versioneer.get_cmdclass()
# run invoke prior to develop/sdist
cmdclass["develop"] = invoke_first(develop)
cmdclass["build_py"] = invoke_first(cmdclass["build_py"])
cmdclass["sdist"] = invoke_first(cmdclass["sdist"])


setup_args = dict(
    name="nbviewer",
    version=versioneer.get_version(),
    packages=["nbviewer"],
    package_data=pkg_data,
    setup_requires=["invoke"],
    author="The Jupyter Development Team",
    author_email="jupyter@googlegroups.com",
    url="https://nbviewer.jupyter.org",
    description="Jupyter Notebook Viewer",
    long_description="Jupyter nbconvert as a web service",
    license="BSD",
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
    ],
    test_suite="nose.collector",
    cmdclass=cmdclass,
)

install_requires = setup_args["install_requires"] = []
with open("requirements.in") as f:
    for line in f:
        req = line.strip()
        if not req.startswith("#"):
            install_requires.append(req)

setup(**setup_args)
