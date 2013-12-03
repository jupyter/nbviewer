# coding: utf-8
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
        return self.url('github/ipython/ipython/blob/%s/examples/notebooks' % ref, *parts)
    
    def test_github(self):
        url = self.ipython_example('Part 1 - Running Code.ipynb')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)

    def test_github_unicode(self):
        url = self.url('github/tlapicka/IPythonNotebooks/blob',
            'ee6d2d13b96023e5f5e38e4516803eb22ede977e',
            u'Matplotlib -- osy a mřížka.ipynb',
        )
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)

    def test_github_blob_redirect_unicode(self):
        url = self.url('/urls/github.com/tlapicka/IPythonNotebooks/blob',
            'ee6d2d13b96023e5f5e38e4516803eb22ede977e',
            u'Matplotlib -- osy a mřížka.ipynb',
        )
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        # verify redirect
        self.assertIn('/github/tlapicka/IPythonNotebooks/blob/', r.request.url)

    def test_github_raw_redirect_unicode(self):
        url = self.url('/url/raw.github.com/tlapicka/IPythonNotebooks',
            'ee6d2d13b96023e5f5e38e4516803eb22ede977e',
            u'Matplotlib -- osy a mřížka.ipynb',
        )
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        # verify redirect
        self.assertIn('/github/tlapicka/IPythonNotebooks/blob/', r.request.url)

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
        self.assertIn('/github/ipython/ipython/blob/rel-1.0.0', r.request.url)
    
    def test_github_raw_redirect(self):
        url = self.url(
            'urls/raw.github.com/ipython/ipython/rel-1.0.0/examples/notebooks',
            'Part 1 - Running Code.ipynb',
        )
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        # verify redirect
        self.assertIn('/github/ipython/ipython/blob/rel-1.0.0', r.request.url)
    
    def test_github_raw_redirect_2(self):
        """test /url/github.com/u/r/raw/ redirects"""
        url = self.url(
            "url/github.com/ipython/ipython/raw/rel-1.0.0/examples/notebooks",
            "Part 1 - Running Code.ipynb"
        )
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        # verify redirect
        self.assertIn('/github/ipython/ipython/blob/rel-1.0.0', r.request.url)
    
    def test_github_repo_redirect(self):
        url = self.url("github/ipython/ipython")
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        # verify redirect
        self.assertIn('/github/ipython/ipython/tree/master', r.request.url)

    def test_github_tree(self):
        url = self.url("github/ipython/ipython/tree/master/IPython/")
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertIn("__init__.py", r.text)


    def test_github_tree_redirect(self):
        url = self.url("github/ipython/ipython/tree/master/MANIFEST.in")
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        # verify redirect
        self.assertIn('/github/ipython/ipython/blob/master', r.request.url)
        self.assertIn('global-exclude', r.text)
