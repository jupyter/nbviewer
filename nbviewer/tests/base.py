"""Base class for nbviewer tests.

Derived from IPython.html notebook test case in 2.0
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import os
import sys
import time
import requests
from contextlib import contextmanager
from subprocess import Popen, PIPE
from unittest import TestCase

from nbviewer.utils import url_path_join

class NBViewerTestCase(TestCase):
    """A base class for tests that need a running nbviewer server."""

    port = 12341

    @classmethod
    def wait_until_alive(cls):
        """Wait for the server to be alive"""
        while True:
            try:
                requests.get(cls.url())
            except requests.exceptions.ConnectionError:
                time.sleep(.1)
            else:
                break
    
    @classmethod
    def wait_until_dead(cls):
        """Wait for the server to stop getting requests after shutdown"""
        while True:
            try:
                requests.get(cls.url())
            except requests.exceptions.ConnectionError:
                break
            else:
                time.sleep(.1)

    @classmethod
    def get_server_cmd(cls):
        return [
            sys.executable, '-m', 'nbviewer',
            '--port=%d' % cls.port,
            # '--logging=debug',
        ]
    
    @classmethod
    def setup_class(cls):
        server_cmd = cls.get_server_cmd()
        devnull = open(os.devnull, 'w')
        cls.server = Popen(server_cmd,
            stdout=devnull,
            stderr=devnull,
        )
        cls.wait_until_alive()

    @classmethod
    def teardown_class(cls):
        cls.server.terminate()
        cls.wait_until_dead()

    @classmethod
    def url(cls, *parts):
        return url_path_join('http://localhost:%i' % cls.port, *parts)


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
