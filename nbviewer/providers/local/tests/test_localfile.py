#-----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import requests

from ....tests.base import NBViewerTestCase, FormatHTMLMixin

class LocalFileDefaultTestCase(NBViewerTestCase):
    @classmethod
    def get_server_cmd(cls):
        return super().get_server_cmd() + [ '--localfiles=.' ]

    def test_url(self):
        ## assumes being run from base of this repo
        url = self.url('localfile/nbviewer/tests/notebook.ipynb')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)


class FormatHTMLLocalFileDefaultTestCase(LocalFileDefaultTestCase,
                                         FormatHTMLMixin):
    pass


class LocalFileRelativePathTestCase(NBViewerTestCase):
    @classmethod
    def get_server_cmd(cls):
        return super().get_server_cmd() + [ '--localfiles=nbviewer' ]

    def test_url(self):
        ## assumes being run from base of this repo
        url = self.url('localfile/tests/notebook.ipynb')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)

    def test_404(self):
        ## assumes being run from base of this repo
        url = self.url('localfile/doesntexist')
        r = requests.get(url)
        self.assertEqual(r.status_code, 404)


class FormatHTMLLocalFileRelativePathTestCase(LocalFileRelativePathTestCase,
                                           FormatHTMLMixin):
    pass
