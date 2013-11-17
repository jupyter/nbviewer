#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import requests

from .base import NBViewerTestCase

class GitHubTestCase(NBViewerTestCase):
    def ipython_example(self, *parts, **kwargs):
        ref = kwargs.get('ref', 'master')
        return self.url('github/ipython/ipython/%s/examples/notebooks' % ref, *parts)
    
    def test_github(self):
        url = self.ipython_example('Part 1 - Running Code.ipynb')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)

    def test_github_tag(self):
        url = self.ipython_example('Part 1 - Running Code.ipynb', ref='rel-1.0.0')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
    
    def test_github_commit(self):
        url = self.ipython_example('Part 1 - Running Code.ipynb',
            ref='02da31ca5a6576dfe9a95ecd9497c1df9a63533d'
        )
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
    
    def test_github_blob_redirect(self):
        url = self.url(
            'urls/github.com/ipython/ipython/blob/rel-1.0.0/examples/notebooks',
            'Part 1 - Running Code.ipynb',
        )
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        # verify redirect
        self.assertIn('/github/ipython/ipython/rel-1.0.0', r.request.url)
