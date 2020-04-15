# coding: utf-8
# -----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------
import os

import requests

from ..providers.local.tests.test_localfile import (
    LocalFileRelativePathTestCase as LFRPTC,
)
from .base import NBViewerTestCase
from .base import skip_unless_github_auth


class XSSTestCase(NBViewerTestCase):
    def _xss(self, path, pattern="<script>alert"):
        r = requests.get(self.url() + path)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(pattern, r.content)

    @skip_unless_github_auth
    def test_github_dirnames(self):
        self._xss("/github/bburky/xss/tree/%3Cscript%3Ealert(1)%3C%2fscript%3E/")

    @skip_unless_github_auth
    def test_gist_filenames(self):
        self._xss("/gist/bburky/c020825874798a6544a7")


class LocalDirectoryTraversalTestCase(LFRPTC):
    def test_url(self):
        ## assumes being run from base of this repo
        url = self.url("localfile/../README.md")
        r = requests.get(url)
        self.assertEqual(r.status_code, 404)


class URLLeakTestCase(NBViewerTestCase):
    @skip_unless_github_auth
    def test_gist(self):
        url = self.url("/github/jupyter")
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.content
        self.assertNotIn("client_id", html)
        self.assertNotIn("client_secret", html)
        self.assertNotIn("access_token", html)


class JupyterHubServiceTestCase(NBViewerTestCase):
    HUB_SETTINGS = {
        "JUPYTERHUB_SERVICE_NAME": "nbviewer-test",
        "JUPYTERHUB_API_TOKEN": "test-token",
        "JUPYTERHUB_API_URL": "http://127.0.0.1:8080/hub/api",
        "JUPYTERHUB_BASE_URL": "/",
        "JUPYTERHUB_SERVICE_URL": "http://127.0.0.1:%d" % NBViewerTestCase.port,
        "JUPYTERHUB_SERVICE_PREFIX": "/services/nbviewer-test",
    }

    environment_variables = HUB_SETTINGS

    @classmethod
    def get_server_cmd(cls):
        return super().get_server_cmd() + ["--localfiles=."]

    def test_login_redirect(self):
        url = self.url("/services/nbviewer-test/github/jupyter")
        r = requests.get(url, allow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(
            r.headers["location"],
            "/hub/login?next=%2Fservices%2Fnbviewer-test%2Fgithub%2Fjupyter",
        )

        url = self.url("services/nbviewer-test/localfile/nbviewer/tests/notebook.ipynb")
        r = requests.get(url, allow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(
            r.headers["location"],
            "/hub/login?next=%2Fservices%2Fnbviewer-test%2Flocalfile%2Fnbviewer%2Ftests%2Fnotebook.ipynb",
        )
