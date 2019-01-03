# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import requests

from ....tests.base import NBViewerTestCase, FormatHTMLMixin, skip_unless_github_auth

class GistTestCase(NBViewerTestCase):
    @skip_unless_github_auth
    def test_gist(self):
        url = self.url('2352771')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)

    @skip_unless_github_auth
    def test_gist_not_nb(self):
        url = self.url('6689377')
        r = requests.get(url)
        self.assertEqual(r.status_code, 400)

    @skip_unless_github_auth
    def test_gist_no_such_file(self):
        url = self.url('6689377/no/file.ipynb')
        r = requests.get(url)
        self.assertEqual(r.status_code, 404)

    @skip_unless_github_auth
    def test_gist_list(self):
        url = self.url('7518294')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.text
        self.assertIn('<th>Name</th>', html)

    @skip_unless_github_auth
    def test_multifile_gist(self):
        url = self.url('7518294', 'Untitled0.ipynb')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.text
        self.assertIn('Download Notebook', html)

    @skip_unless_github_auth
    def test_anonymous_gist(self):
        url = self.url('gist/4465051')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.text
        self.assertIn('Download Notebook', html)

    @skip_unless_github_auth
    def test_gist_unicode(self):
        url = self.url('gist/amueller/3974344')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.text
        self.assertIn('<th>Name</th>', html)

    @skip_unless_github_auth
    def test_gist_unicode_content(self):
        url = self.url('gist/ocefpaf/cf023a8db7097bd9fe92')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.text
        self.assertNotIn('param&#195;&#169;trica', html)
        self.assertIn('param&#233;trica', html)



class FormatHTMLGistTestCase(GistTestCase, FormatHTMLMixin):
    pass
