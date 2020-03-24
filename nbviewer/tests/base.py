"""Base class for nbviewer tests.

Derived from IPython.html notebook test case in 2.0
"""

#-----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import time
import requests
from contextlib import contextmanager
from unittest import TestCase, skipIf

from tornado.escape import to_unicode
from tornado.log import app_log

from nbviewer.utils import url_path_join
from nbviewer.providers.github.client import AsyncGitHubClient

from subprocess import Popen
from subprocess import DEVNULL as devnull
import os
import sys

class NBViewerTestCase(TestCase):
    """A base class for tests that need a running nbviewer server."""

    port = 12341

    environment_variables = {}

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
    def get_server_cmd(cls):
        return [ sys.executable, '-m', 'nbviewer', '--port=%d' % cls.port, ]
                
    @classmethod
    def setup_class(cls):
        server_cmd = cls.get_server_cmd()
        cls.server = Popen(server_cmd,
                stdout=devnull, stderr=devnull,
                # Set environment variables if any
                env=dict(os.environ, **cls.environment_variables))
        cls.wait_until_alive()
    
    @classmethod
    def teardown_class(cls):
        cls.server.terminate()
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
    cl = AsyncGitHubClient(log=app_log)
    can_auth = 'access_token' in cl.auth or ('client_id' in cl.auth and 'client_secret' in cl.auth)
    return skipIf(not can_auth, 'github creds not available')(f)
