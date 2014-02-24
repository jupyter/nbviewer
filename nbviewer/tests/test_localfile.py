#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import requests
import sys
from nbviewer.utils import url_path_join

from .base import NBViewerTestCase

class LocalFileDefaultTestCase(NBViewerTestCase):
    @classmethod
    def get_server_cmd(cls): 
        return [
            sys.executable, '-m', 'nbviewer',
            '--port=%d' % cls.port,
            '--localfile=True',
            ]

    def test_url(self):
        ## assumes being run from base of this repo
        url = self.url('localfile/nbviewer/tests/notebook.ipynb')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)

class LocalFileURITestCase(NBViewerTestCase):
    @classmethod
    def get_server_cmd(cls): 
        return [
            sys.executable, '-m', 'nbviewer',
            '--port=%d' % cls.port,
            '--localfile=True',
            '--localfile_uri=/TEST/',
            ]

    def test_url(self):
        ## assumes being run from base of this repo
        url = self.url('TEST/nbviewer/tests/notebook.ipynb')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)

class LocalFileRelativePathTestCase(NBViewerTestCase):
    @classmethod
    def get_server_cmd(cls): 
        return [
            sys.executable, '-m', 'nbviewer',
            '--port=%d' % cls.port,
            '--localfile=True',
            '--localfile_path=nbviewer/',
            ]

    def test_url(self):
        ## assumes being run from base of this repo
        url = self.url('localfile/tests/notebook.ipynb')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)

