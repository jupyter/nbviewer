# -----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------
import cgi
import json
import os
import re
import time
from base64 import decodebytes
from base64 import encodebytes
from contextlib import contextmanager
from functools import lru_cache
from subprocess import check_output
from urllib.parse import parse_qs
from urllib.parse import quote as stdlib_quote
from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.parse import urlunparse

STRIP_PARAMS = ["client_id", "client_secret", "access_token"]

HERE = os.path.dirname(__file__)
GIT_INFO_JSON = os.path.join(HERE, "git_info.json")


class EmptyClass(object):
    """
    Simple empty class that returns itself for all functions called on it.
    This allows us to call any method of any name on this, and it'll return another
    instance of itself that'll allow any method to be called on it.

    Primarily used to mock out the statsd client when statsd is not being used
    """

    def empty_function(self, *args, **kwargs):
        return self

    def __getattr__(self, attr):
        return self.empty_function


def quote(s):
    """unicode-safe quote

    - accepts str+unicode (not bytes on py3)
    - Python 2 requires str, not unicode
    - always return unicode
    """
    if not isinstance(s, str):
        s = s.encode("utf8")
    quoted = stdlib_quote(s)
    if isinstance(quoted, bytes):
        quoted = quoted.decode("utf8")
    return quoted


def clean_filename(fn):
    """ Github url sanitizes gist filenames to produce their permalink. This is
    not provided over API, so we recreate it here. """
    return re.sub("[^0-9a-zA-Z]+", "-", fn)


def url_path_join(*pieces):
    """Join components of url into a relative url

    Use to prevent double slash when joining subpath. This will leave the
    initial and final / in place
    """
    initial = pieces[0].startswith("/")
    final = pieces[-1].endswith("/")
    stripped = [s.strip("/") for s in pieces]
    result = "/".join(s for s in stripped if s)
    if initial:
        result = "/" + result
    if final:
        result += "/"
    if result == "//":
        result = "/"
    return result


def transform_ipynb_uri(uri, uri_rewrite_list):
    """Transform a given uri (an ipynb 'URI') into an app URL

    State-free part of transforming URIs to nbviewer URLs.

    :param uri: uri to transform
    :param uri_rewrite_list: list of (URI regexes, URL templates) tuples
    """
    for reg, rewrite in uri_rewrite_list:
        matches = re.match(reg, uri)
        if matches:
            uri = rewrite.format(*matches.groups())
            break

    # encode query parameters as last url part
    if "?" in uri:
        uri, query = uri.split("?", 1)
        uri = "%s/%s" % (uri, quote("?" + query))

    return uri


# get_encoding_from_headers from requests.utils (1.2.3)
# (c) 2013 Kenneth Reitz
# used under Apache 2.0


def get_encoding_from_headers(headers):
    """Returns encodings from given HTTP Header Dict.

    :param headers: dictionary to extract encoding from.
    """

    content_type = headers.get("content-type")

    if not content_type:
        return None

    content_type, params = cgi.parse_header(content_type)

    if "charset" in params:
        return params["charset"].strip("'\"")

    # per #507, at least some hosts are providing UTF-8 without declaring it
    # while the former choice of ISO-8859-1 wasn't known to be causing problems
    # in the wild
    if "text" in content_type:
        return "utf-8"


def response_text(response, encoding=None):
    """mimic requests.text property, but for plain HTTPResponse"""
    encoding = encoding or get_encoding_from_headers(response.headers) or "utf-8"
    return response.body.decode(encoding, "replace")


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
            url, params = val, ""

        link = {}

        parts = list(urlparse(url.strip("<> '\"")))

        get_params = parse_qs(parts[4])

        get_params = {
            key: value[0]
            for key, value in get_params.items()
            if key not in STRIP_PARAMS
        }
        parts[4] = urlencode(get_params)

        link["url"] = urlunparse(parts)

        for param in params.split(";"):
            try:
                key, value = param.split("=")
            except ValueError:
                break

            link[key.strip(replace_chars)] = value.strip(replace_chars)

        if "rel" in link:
            links[link["rel"]] = link

    return links


def git_info(path, force_git=False):
    """Return some git info"""
    if os.path.exists(GIT_INFO_JSON) and not force_git:
        with open(GIT_INFO_JSON, "r") as f:
            return json.load(f)
    command = ["git", "log", "-1", "--format=%H\n%s\n%cD"]
    sha, msg, date = check_output(command, cwd=path).decode("utf8").splitlines()
    return dict(sha=sha, date=date, msg=msg)


def jupyter_info():
    """Get Jupyter info dict"""
    import nbconvert

    return dict(nbconvert_version=nbconvert.__version__)


def base64_decode(s):
    """unicode-safe base64

    base64 API only talks bytes
    """
    if not isinstance(s, bytes):
        s = s.encode("ascii", "replace")
    decoded = decodebytes(s)
    return decoded


def base64_encode(s):
    """unicode-safe base64

    base64 API only talks bytes
    """
    if not isinstance(s, bytes):
        s = s.encode("ascii", "replace")
    encoded = encodebytes(s)
    return encoded.decode("ascii")


@contextmanager
def time_block(message, logger, debug_limit=1):
    """context manager for timing a block

    logs millisecond timings of the block
    
    If the time is longer than debug_limit,
    then log level will be INFO,
    otherwise it will be DEBUG.
    """
    tic = time.time()
    yield
    dt = time.time() - tic
    log = logger.info if dt > debug_limit else logger.debug
    log("%s in %.2f ms", message, 1e3 * dt)


def cached_property(method):
    return property(lru_cache(1)(method))
