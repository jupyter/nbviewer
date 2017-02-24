"""Notebook related utilities"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import print_function

import ctypes
import errno
import os
import stat
import sys
from distutils.version import LooseVersion

try:
    from urllib.parse import quote, unquote, urlparse
except ImportError:
    from urllib import quote, unquote
    from urlparse import urlparse

from ipython_genutils import py3compat

# UF_HIDDEN is a stat flag not defined in the stat module.
# It is used by BSD to indicate hidden files.
UF_HIDDEN = getattr(stat, 'UF_HIDDEN', 32768)


def url_path_join(*pieces):
    """Join components of url into a relative url

    Use to prevent double slash when joining subpath. This will leave the
    initial and final / in place
    """
    initial = pieces[0].startswith('/')
    final = pieces[-1].endswith('/')
    stripped = [s.strip('/') for s in pieces]
    result = '/'.join(s for s in stripped if s)
    if initial: result = '/' + result
    if final: result = result + '/'
    if result == '//': result = '/'
    return result

def url_is_absolute(url):
    """Determine whether a given URL is absolute"""
    return urlparse(url).path.startswith("/")

def path2url(path):
    """Convert a local file path to a URL"""
    pieces = [ quote(p) for p in path.split(os.sep) ]
    # preserve trailing /
    if pieces[-1] == '':
        pieces[-1] = '/'
    url = url_path_join(*pieces)
    return url

def url2path(url):
    """Convert a URL to a local file path"""
    pieces = [ unquote(p) for p in url.split('/') ]
    path = os.path.join(*pieces)
    return path
    
def url_escape(path):
    """Escape special characters in a URL path
    
    Turns '/foo bar/' into '/foo%20bar/'
    """
    parts = py3compat.unicode_to_str(path, encoding='utf8').split('/')
    return u'/'.join([quote(p) for p in parts])

def url_unescape(path):
    """Unescape special characters in a URL path
    
    Turns '/foo%20bar/' into '/foo bar/'
    """
    return u'/'.join([
        py3compat.str_to_unicode(unquote(p), encoding='utf8')
        for p in py3compat.unicode_to_str(path, encoding='utf8').split('/')
    ])

_win32_FILE_ATTRIBUTE_HIDDEN = 0x02

def is_hidden(abs_path, abs_root=''):
    """Is a file hidden or contained in a hidden directory?
    
    This will start with the rightmost path element and work backwards to the
    given root to see if a path is hidden or in a hidden directory. Hidden is
    determined by either name starting with '.' or the UF_HIDDEN flag as 
    reported by stat.
    
    Parameters
    ----------
    abs_path : unicode
        The absolute path to check for hidden directories.
    abs_root : unicode
        The absolute path of the root directory in which hidden directories
        should be checked for.
    """
    if not abs_root:
        abs_root = abs_path.split(os.sep, 1)[0] + os.sep
    inside_root = abs_path[len(abs_root):]
    if any(part.startswith('.') for part in inside_root.split(os.sep)):
        return True
    
    # check that dirs can be listed
    # may fail on Windows junctions or non-user-readable dirs
    if os.path.isdir(abs_path):
        try:
            os.listdir(abs_path)
        except OSError:
            return True
    
    # check UF_HIDDEN on any location up to root
    path = abs_path
    while path and path.startswith(abs_root) and path != abs_root:
        if not os.path.exists(path):
            path = os.path.dirname(path)
            continue
        try:
            # may fail on Windows junctions
            st = os.stat(path)
        except OSError:
            return True
        if getattr(st, 'st_flags', 0) & UF_HIDDEN:
            return True
        path = os.path.dirname(path)
    
    if sys.platform == 'win32':
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(py3compat.cast_unicode(path))
        except AttributeError:
            pass
        else:
            if attrs > 0 and attrs & _win32_FILE_ATTRIBUTE_HIDDEN:
                return True

    return False

def to_os_path(path, root=''):
    """Convert an API path to a filesystem path
    
    If given, root will be prepended to the path.
    root must be a filesystem path already.
    """
    parts = path.strip('/').split('/')
    parts = [p for p in parts if p != ''] # remove duplicate splits
    path = os.path.join(root, *parts)
    return path

def to_api_path(os_path, root=''):
    """Convert a filesystem path to an API path
    
    If given, root will be removed from the path.
    root must be a filesystem path already.
    """
    if os_path.startswith(root):
        os_path = os_path[len(root):]
    parts = os_path.strip(os.path.sep).split(os.path.sep)
    parts = [p for p in parts if p != ''] # remove duplicate splits
    path = '/'.join(parts)
    return path


def check_version(v, check):
    """check version string v >= check

    If dev/prerelease tags result in TypeError for string-number comparison,
    it is assumed that the dependency is satisfied.
    Users on dev branches are responsible for keeping their own packages up to date.
    """
    try:
        return LooseVersion(v) >= LooseVersion(check)
    except TypeError:
        return True


# Copy of IPython.utils.process.check_pid:

def _check_pid_win32(pid):
    import ctypes
    # OpenProcess returns 0 if no such process (of ours) exists
    # positive int otherwise
    return bool(ctypes.windll.kernel32.OpenProcess(1,0,pid))

def _check_pid_posix(pid):
    """Copy of IPython.utils.process.check_pid"""
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            return False
        elif err.errno == errno.EPERM:
            # Don't have permission to signal the process - probably means it exists
            return True
        raise
    else:
        return True

if sys.platform == 'win32':
    check_pid = _check_pid_win32
else:
    check_pid = _check_pid_posix
