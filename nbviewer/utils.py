#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import base64
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


def clean_filename(fn):
    """ Github url sanitizes gist filenames to produce their permalink. This is
    not provided over API, so we recreate it here. """
    return re.sub('[^0-9a-zA-Z]+', '-', fn)


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


def transform_ipynb_uri(uri, uri_rewrite_dict):
    """Transform a given uri (an ipynb 'URI') into an app URL

    State-free part of transforming URIs to nbviewer URLs.

    :param uri: uri to transform
    :param uri_rewrite_dict: dict mapping URI regexes to URL templates
    """
    for reg, rewrite in uri_rewrite_dict.items():
        matches = re.match(reg, uri)
        if matches:
            return rewrite.format(*matches.groups())

    # encode query parameters as last url part
    if '?' in uri:
        uri, query = uri.split('?', 1)
        uri = '%s/%s' % (uri, quote('?' + query))

    return uri

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

def response_text(response, encoding=None):
    """mimic requests.text property, but for plain HTTPResponse"""
    encoding = (
        encoding or
        get_encoding_from_headers(response.headers) or
        'utf-8'
    )
    return response.body.decode(encoding, 'replace')

# parse_header_links from requests.util
# modified to actually return a dict, like the docstring says.

def parse_header_links(value):
    """Return a dict of parsed link headers proxies.

    i.e. Link: <http:/.../front.jpeg>; rel=front; type="image/jpeg",<http://.../back.jpeg>; rel=back;type="image/jpeg"

    """

    links = {}

    replace_chars = " '\""

    for val in value.split(","):
        try:
            url, params = val.split(";", 1)
        except ValueError:
            url, params = val, ''

        link = {}

        link["url"] = url.strip("<> '\"")

        for param in params.split(";"):
            try:
                key, value = param.split("=")
            except ValueError:
                break

            link[key.strip(replace_chars)] = value.strip(replace_chars)
        
        if 'rel' in link:
            links[link['rel']] = link

    return links

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

def base64_decode(s):
    """unicode-safe base64
    
    base64 API only talks bytes
    """
    s = py3compat.cast_bytes(s)
    decoded = base64.decodestring(s)
    return decoded

def base64_encode(s):
    """unicode-safe base64
    
    base64 API only talks bytes
    """
    s = py3compat.cast_bytes(s)
    encoded = base64.encodestring(s)
    return encoded.decode('ascii')
