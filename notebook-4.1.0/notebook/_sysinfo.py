# encoding: utf-8
"""
Utilities for getting information about Jupyter and the system it's running in.
"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import absolute_import

import os
import platform
import pprint
import sys
import subprocess

from ipython_genutils import py3compat, encoding

import notebook

def pkg_commit_hash(pkg_path):
    """Get short form of commit hash given directory `pkg_path`

    We get the commit hash from git if it's a repo.

    If this fail, we return a not-found placeholder tuple

    Parameters
    ----------
    pkg_path : str
       directory containing package
       only used for getting commit from active repo

    Returns
    -------
    hash_from : str
       Where we got the hash from - description
    hash_str : str
       short form of hash
    """

    # maybe we are in a repository, check for a .git folder
    p = os.path
    cur_path = None
    par_path = pkg_path
    while cur_path != par_path:
        cur_path = par_path
        if p.exists(p.join(cur_path, '.git')):
            proc = subprocess.Popen('git rev-parse --short HEAD',
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                cwd=pkg_path, shell=True)
            repo_commit, _ = proc.communicate()
            if repo_commit:
                return 'repository', repo_commit.strip().decode('ascii')
            else:
                return u'', u''
        par_path = p.dirname(par_path)
                
    return u'', u''


def pkg_info(pkg_path):
    """Return dict describing the context of this package

    Parameters
    ----------
    pkg_path : str
       path containing __init__.py for package

    Returns
    -------
    context : dict
       with named parameters of interest
    """
    src, hsh = pkg_commit_hash(pkg_path)
    return dict(
        notebook_version=notebook.__version__,
        notebook_path=pkg_path,
        commit_source=src,
        commit_hash=hsh,
        sys_version=sys.version,
        sys_executable=sys.executable,
        sys_platform=sys.platform,
        platform=platform.platform(),
        os_name=os.name,
        default_encoding=encoding.DEFAULT_ENCODING,
        )

def get_sys_info():
    """Return useful information about the system as a dict."""
    p = os.path
    path = p.realpath(p.dirname(p.abspath(p.join(notebook.__file__))))
    return pkg_info(path)

