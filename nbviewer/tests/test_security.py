# coding: utf-8
#-----------------------------------------------------------------------------
#  Copyright (C) 2015 The Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import requests

from .base import NBViewerTestCase

from ..providers.local.tests.test_localfile import (
    LocalFileRelativePathTestCase as LFRPTC
)

class XSSTestCase(NBViewerTestCase):
    def _xss(self, path, pattern='<script>alert'):
        r = requests.get(self.url() + path)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(pattern, r.content)

    def test_github_dirnames(self):
        self._xss(
            '/github/bburky/xss/tree/%3Cscript%3Ealert(1)%3C%2fscript%3E/'
        )

    def test_gist_filenames(self):
        self._xss('/gist/bburky/c020825874798a6544a7')


class LocalDirectoryTraversalTestCase(LFRPTC):
    def test_url(self):
        ## assumes being run from base of this repo
        url = self.url('localfile/../README.md')
        r = requests.get(url)
        self.assertEqual(r.status_code, 404)
