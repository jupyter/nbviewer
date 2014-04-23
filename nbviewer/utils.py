#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import cgi
import re
from subprocess import check_output

try:
    from urllib.parse import quote as stdlib_quote
except ImportError:
    from urllib2 import quote as stdlib_quote

from IPython.utils import py3compat

def quote(s):
    """unicode-safe quote
    
    - Python 2 requires str, not unicode
    - always return unicode
    """
    s = py3compat.cast_bytes_py2(s)
    quoted = stdlib_quote(s)
    return py3compat.str_to_unicode(quoted)


def url_path_join(*pieces):
    """Join components of url into a relative url

    Use to prevent double slash when joining subpath. This will leave the
    initial and final / in place
    """
    initial = pieces[0].startswith('/')
    final = pieces[-1].endswith('/')
    stripped = [s.strip('/') for s in pieces]
    result = '/'.join(s for s in stripped if s)
    if initial:
        result = '/' + result
    if final:
        result += '/'
    if result == '//':
        result = '/'
    return result

GIST_RGX = re.compile(r'^([a-f0-9]+)/?$')
GIST_URL_RGX = re.compile(r'^https?://gist.github.com/(\w+/)?([a-f0-9]+)/?$')
GITHUB_URL_RGX = re.compile(r'^https?://github.com/(\w+)/(\w+)/blob/(.*)$')
GITHUB_RAW_URL_RGX = re.compile(r'^https?://raw.?github.com/(\w+)/(\w+)/(.*)$')
GITHUB_USER_RGX = re.compile(r'^(\w+)$')
GITHUB_USERREPO_RGX = re.compile(r'^(\w+)/(\w+)$')
DROPBOX_URL_RGX = re.compile(r'^http(s?)://www.dropbox.com/(sh?)/(.+)$')


#def url_rewrite(value):
#
#    for reg,template in regs_dict:
#        matches = reg.match(value)
#        if matches: 
#            return template.format(matches.groups)

from collections import OrderedDict

url_rewrite_dict = OrderedDict({
        GIST_RGX           : u'/{0}',
        GIST_URL_RGX       : u'/{1}',
        GITHUB_URL_RGX     : u'/github/{0}/{1}/blob/{2}',
        GITHUB_RAW_URL_RGX : u'/github/{0}/{1}/blob/{2}',
        GITHUB_USERREPO_RGX : u'/github/{0}/{1}/tree/master/',
        GITHUB_USER_RGX    : u'/github/{0}/',
        DROPBOX_URL_RGX    : u'/url{0}/dl.dropbox.com/{1}/{2}',
    })


def transform_ipynb_uri(value):
    """Transform a given value (an ipynb 'URI') into an app URL"""

    for reg,rewrite in url_rewrite_dict.iteritems() :
        matches = reg.match(value)
        if matches :
            return rewrite.format(*matches.groups())

    if value.startswith('https://'):
        return u'/urls/%s' % value[8:]

    if value.startswith('http://'):
        return u'/url/%s' % value[7:]

    return u'/url/%s' % value

# get_encoding_from_headers from requests.utils (1.2.3)
# (c) 2013 Kenneth Reitz
# used under Apache 2.0

def get_encoding_from_headers(headers):
    """Returns encodings from given HTTP Header Dict.

    :param headers: dictionary to extract encoding from.
    """

    content_type = headers.get('content-type')

    if not content_type:
        return None

    content_type, params = cgi.parse_header(content_type)

    if 'charset' in params:
        return params['charset'].strip("'\"")

    if 'text' in content_type:
        return 'ISO-8859-1'

def response_text(response):
    """mimic requests.text property, but for plain HTTPResponse"""
    encoding = get_encoding_from_headers(response.headers) or 'utf-8'
    return response.body.decode(encoding, 'replace')

def git_info(path):
    """Return some git info"""
    command = ['git', 'log', '-1', '--format=%H\n%s\n%cD']
    sha, msg, date = check_output(command, cwd=path).decode('utf8').splitlines()
    return dict(
        sha=sha,
        date=date,
        msg=msg,
    )

def ipython_info():
    """Get IPython info dict"""
    from IPython.utils import sysinfo
    try:
        return sysinfo.get_sys_info()
    except AttributeError:
        # IPython < 2.0
        return eval(sysinfo.sys_info())
