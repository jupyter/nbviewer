#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import requests

from .base import NBViewerTestCase, skip_unless_github_auth
from ..providers.local.tests.test_localfile import LocalFileDefaultTestCase


class SlidesGistTestCase(NBViewerTestCase):
    @skip_unless_github_auth
    def test_gist(self):
        url = self.url('/format/slides/0c5b3639b10ed3d7cc85/single-cell.ipynb')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.content
        self.assertIn('reveal.js', html)

    @skip_unless_github_auth
    def test_html_exporter_link(self):
        url = self.url('/format/slides/0c5b3639b10ed3d7cc85/single-cell.ipynb')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.content
        self.assertIn('/gist/minrk/0c5b3639b10ed3d7cc85/single-cell.ipynb', html)
        self.assertNotIn('//gist/minrk/0c5b3639b10ed3d7cc85/single-cell.ipynb', html)

    @skip_unless_github_auth
    def test_no_slides_exporter_link(self):
        url = self.url('/0c5b3639b10ed3d7cc85/single-cell.ipynb')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.content
        self.assertNotIn(
            '/format/slides/gist/minrk/7518294/Untitled0.ipynb',
            html
        )


class SlideLocalFileDefaultTestCase(LocalFileDefaultTestCase):
    def test_slides_local(self):
        ## assumes being run from base of this repo
        url = self.url('format/slides/localfile/nbviewer/tests/notebook.ipynb')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.content
        self.assertIn('reveal.js', html)


class SlidesGitHubTestCase(NBViewerTestCase):
    def ipython_example(self, *parts, **kwargs):
        ref = kwargs.get('ref', 'rel-2.0.0')
        return self.url(
            '/format/slides/github/ipython/ipython/blob/%s/examples' % ref,
            *parts
        )

    @skip_unless_github_auth
    def test_github(self):
        url = self.ipython_example('Index.ipynb')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.content
        self.assertIn('reveal.js', html)
