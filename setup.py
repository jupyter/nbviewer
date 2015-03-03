#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import os
import sys
pjoin = os.path.join

from setuptools import setup

def walk_subpkg(name):
    data_files = []
    package_dir = 'nbviewer'
    for parent, dirs, files in os.walk(os.path.join(package_dir, name)):
        sub_dir = os.sep.join(parent.split(os.sep)[1:]) # remove package_dir from the path
        for f in files:
            data_files.append(os.path.join(sub_dir, f))
    return data_files

pkg_data = {
    "nbviewer": ['frontpage.json'] + walk_subpkg('static') + walk_subpkg('templates')
}

setup_args = dict(
    name = "nbviewer",
    version = '0.2.0',
    packages = ["nbviewer"],
    package_data = pkg_data,
    author = "The Jupyter Development Team",
    author_email = "ipython-dev@scipy.org",
    url = 'http://nbviewer.ipython.org',
    description = "Jupyter Notebook Viewer",
    long_description = "Jupyter nbconvert as a web service",
    license = "BSD",
    classifiers = [
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
    ],
)

setup(**setup_args)

