#-----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------
import unittest

import requests

from ....tests.base import NBViewerTestCase, FormatHTMLMixin


class URLTestCase(NBViewerTestCase):
    def test_url(self):
        url = self.url('url/jdj.mit.edu/~stevenj/IJulia Preview.ipynb')
        r = requests.get(url)
        # Base class overrides assertIn to do unicode in unicode checking
        # We want to use the original unittest implementation
        unittest.TestCase.assertIn(self, r.status_code, (200, 202))
        self.assertIn('Download Notebook', r.text)

    def test_urls_with_querystring(self):
        # This notebook is only available if the querystring is passed through.
        # Notebook URL: https://bug1348008.bmoattachments.org/attachment.cgi?id=8860059
        url = self.url('urls/bug1348008.bmoattachments.org/attachment.cgi/%3Fid%3D8860059')
        r = requests.get(url)
        # Base class overrides assertIn to do unicode in unicode checking
        # We want to use the original unittest implementation
        unittest.TestCase.assertIn(self, r.status_code, (200, 202))
        self.assertIn('Download Notebook', r.text)


class FormatHTMLURLTestCase(URLTestCase, FormatHTMLMixin):
    pass
