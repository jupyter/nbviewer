# coding: utf-8
#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import requests

from unittest import SkipTest

from .base import NBViewerTestCase, FormatHTMLMixin

class GitHubTestCase(NBViewerTestCase):
    def ipython_example(self, *parts, **kwargs):
        ref = kwargs.get('ref', 'rel-2.0.0')
        return self.url('github/ipython/ipython/blob/%s/examples' % ref, *parts)

    def test_github(self):
        url = self.ipython_example('Index.ipynb')
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
        url = self.ipython_example('Index.ipynb', ref='rel-2.0.0')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
    
    def test_github_commit(self):
        url = self.ipython_example('Index.ipynb',
            ref='7f5cbd622058396f1f33c4b26c8d205a8dd26d16'
        )
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
    
    def test_github_blob_redirect(self):
        url = self.url(
            'urls/github.com/ipython/ipython/blob/rel-2.0.0/examples',
            'Index.ipynb',
        )
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        # verify redirect
        self.assertIn('/github/ipython/ipython/blob/master', r.request.url)
    
    def test_github_raw_redirect(self):
        url = self.url(
            'urls/raw.github.com/ipython/ipython/rel-2.0.0/examples',
            'Index.ipynb',
        )
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        # verify redirect
        self.assertIn('/github/ipython/ipython/blob/rel-2.0.0/examples', r.request.url)
    

    def test_github_rawusercontent_redirect(self):
        """Test GitHub's new raw domain"""
        url = self.url(
            'urls/raw.githubusercontent.com/ipython/ipython/rel-2.0.0/examples',
            'Index.ipynb',
        )
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        # verify redirect
        self.assertIn('/github/ipython/ipython/blob/rel-2.0.0/examples', r.request.url)
    
    def test_github_raw_redirect_2(self):
        """test /url/github.com/u/r/raw/ redirects"""
        url = self.url(
            "url/github.com/ipython/ipython/blob/rel-2.0.0/examples",
            "Index.ipynb"
        )
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        # verify redirect
        self.assertIn('/github/ipython/ipython/blob/rel-2.0.0', r.request.url)
    
    def test_github_repo_redirect(self):
        url = self.url("github/ipython/ipython")
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        # verify redirect
        self.assertIn('/github/ipython/ipython/tree/master', r.request.url)

    def test_github_tree(self):
        url = self.url("github/ipython/ipython/tree/rel-2.0.0/IPython/")
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertIn("__init__.py", r.text)


    def test_github_tree_redirect(self):
        url = self.url("github/ipython/ipython/tree/rel-2.0.0/MANIFEST.in")
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        # verify redirect
        self.assertIn('/github/ipython/ipython/blob/rel-2.0.0', r.request.url)
        self.assertIn('global-exclude', r.text)

    def test_github_blob_redirect(self):
        url = self.url("github/ipython/ipython/blob/rel-2.0.0/IPython")
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        # verify redirect
        self.assertIn('/github/ipython/ipython/tree/rel-2.0.0/IPython', r.request.url)
        self.assertIn('__init__.py', r.text)

    def test_github_ref_list(self):
        url = self.url('github/ipython/ipython/tree/master')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.text
        # verify branch is linked
        self.assertIn('/github/ipython/ipython/tree/2.x/', html)
        # verify tag is linked
        self.assertIn('/github/ipython/ipython/tree/rel-2.3.0/', html)


class FormatHTMLGitHubTestCase(NBViewerTestCase, FormatHTMLMixin):
    pass