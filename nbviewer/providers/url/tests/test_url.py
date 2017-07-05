#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
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


class FormatHTMLURLTestCase(URLTestCase, FormatHTMLMixin):
    pass
