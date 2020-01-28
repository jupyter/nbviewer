"""Base class for nbviewer tests.

Derived from IPython.html notebook test case in 2.0
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import time
import requests
from contextlib import contextmanager
from threading import Thread, Event
from unittest import TestCase, skipIf

from tornado.escape import to_unicode
from tornado.ioloop import IOLoop
import tornado.options

from nbviewer.utils import url_path_join
from nbviewer.app import main
from nbviewer.providers.github.client import AsyncGitHubClient


class NBViewerTestCase(TestCase):
    """A base class for tests that need a running nbviewer server."""

    port = 12341

    def assertIn(self, observed, expected, *args, **kwargs):
        return super().assertIn(
            to_unicode(observed),
            to_unicode(expected),
            *args,
            **kwargs
        )

    def assertNotIn(self, observed, expected, *args, **kwargs):
        return super().assertNotIn(
            to_unicode(observed),
            to_unicode(expected),
            *args,
            **kwargs
        )

    @classmethod
    def wait_until_alive(cls):
        """Wait for the server to be alive"""
        while True:
            try:
                requests.get(cls.url())
            except Exception:
                time.sleep(.1)
            else:
                break

    @classmethod
    def wait_until_dead(cls):
        """Wait for the server to stop getting requests after shutdown"""
        while True:
            try:
                requests.get(cls.url())
            except Exception:
                break
            else:
                time.sleep(.1)

    @classmethod
    def setup_class(cls):
        cls._start_evt = Event()
        cls.server = Thread(target=cls._server_main)
        cls.server.start()
        cls._start_evt.wait()
        cls.wait_until_alive()
    
    @classmethod
    def get_server_args(cls):
        return []
    
    @classmethod
    def _server_main(cls):
        cls._server_loop = loop = IOLoop()
        loop.make_current()
        cls._server_loop.add_callback(cls._start_evt.set)
        main(['', '--port=%d' % cls.port] + cls.get_server_args())
        loop.close(all_fds=True)

    @classmethod
    def teardown_class(cls):
        cls._server_loop.add_callback(cls._server_loop.stop)
        cls.server.join()
        cls.wait_until_dead()

    @classmethod
    def url(cls, *parts):
        return url_path_join('http://localhost:%i' % cls.port, *parts)


class FormatMixin(object):
    @classmethod
    def url(cls, *parts):
        return url_path_join(
            'http://localhost:%i' % cls.port, 'format', cls.key, *parts
        )


class FormatHTMLMixin(object):
    key = "html"


class FormatSlidesMixin(object):
    key = "slides"


@contextmanager
def assert_http_error(status, msg=None):
    try:
        yield
    except requests.HTTPError as e:
        real_status = e.response.status_code
        assert real_status == status, \
                    "Expected status %d, got %d" % (real_status, status)
        if msg:
            assert msg in str(e), e
    else:
        assert False, "Expected HTTP error status"


def skip_unless_github_auth(f):
    """Decorates a function to skip a test unless credentials are available for
    AsyhncGitHubClient to authenticate.

    Avoids noisy test failures on PRs due to GitHub API rate limiting with a
    valid token that might obscure test failures that are actually meaningful.

    Paraameters
    -----------
    f: callable
        test function to decorate

    Returns
    -------
    callable
        unittest.skipIf decorated function
    """
    cl = AsyncGitHubClient()
    can_auth = 'access_token' in cl.auth or ('client_id' in cl.auth and 'client_secret' in cl.auth)
    return skipIf(not can_auth, 'github creds not available')(f)
