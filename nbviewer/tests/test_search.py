#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import requests

from .base import NBViewerTestCase

class SearchTestCase(NBViewerTestCase):

    def test_search_page(self):
        urllink = self.url('search')
        r = requests.get(urllink)
        self.assertEqual(r.status_code, 200)

    def test_search_results_no_res(self):
        # no results search
        urllink = self.url('search')
        post_data = {'searchphrase' : ""}
        r = requests.post(urllink, params = post_data)
        self.assertEquals(r.status_code, 200)
        html = r.text
        self.assertIn("No results found", html)

    def test_search_results_paging_single(self):
        # single results page
        urllink = self.url('search')
        post_data = {'searchphrase' : 'physics'}
        r = requests.post(urllink, params = post_data)
        print(r, post_data)
        self.assertEquals(r.status_code, 200)
        html = r.text
        self.assertIn("physics", html.lower())



