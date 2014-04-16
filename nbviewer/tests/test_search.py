#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import requests
from mock import patch

from .base import NBViewerTestCase
from ..google_search import GoogleSearchClient
from tornado.httputil import url_concat

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

    def test_search_link(self):
        value, client, url = self._get_client_info('genome')

        with patch.object(GoogleSearchClient, '_fetch_results', 
                return_value=url) as mock_method:
            results = client.search(value)
        
        mock_method.assert_called_once_with(url)
        self.assertEquals(results, url)
        self.assertIn(value, results)

    def test_search_results_parsed(self):
        value, client, url = self._get_client_info('genome')
        
        with patch.object(GoogleSearchClient, '_fetch_results', 
                return_value=result_set_1) as mock_method:
            results = client.search(value)

        mock_method.assert_called_once_with(url)

        parsed = client.parse_results(results)
        self.assertEquals(len(parsed), 1)
        self.assertEquals(parsed[0]['title'], 'test')
        self.assertEquals(parsed[0]['summary'], 'test summary')
        self.assertEquals(parsed[0]['link'], 'somewhere')

    def _get_client_info(self, value):
        c = GoogleSearchClient()
        u = url_concat(c.google_api_url, {'key':'','cx':'','q':value})
        return value, c, u


result_set_1 = {
    'items': [
        {'title':'test','snippet':'test summary','link':'somewhere'}
    ]
}
