__author__ = 'mt'

import os
from tornado.log import app_log
from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import url_concat

class GoogleSearchClient:

    google_api_url = 'https://www.googleapis.com/customsearch/v1'

    def __init__(self):
        self.search_auth_key = os.environ.get('GOOGLE_SEARCH_KEY', '')
        self.search_auth_cx =  os.environ.get('GOOGLE_SEARCH_CX', '')

    def search(self, search_phrase, start_index=1):
        """ Queries google for all the notebooks

        """
        search_params = {'key': self.search_auth_key,
                        'cx': self.search_auth_cx,
                        'q': search_phrase,
                        'start': start_index}
        app_log.info("Searching google with query: %s", search_phrase)
        url = url_concat(self.google_api_url, search_params)
        app_log.info("Search url: %s", url)
        future = self._fetch_results(url)
        return future

    def _fetch_results(self, url):
        client = AsyncHTTPClient()
        return client.fetch(url)

    def parse_results(self, results):
        parsed_links = {
            'count': 0,
            'index': 1,
            'total': 0,
            'items': []
        }
        if results.has_key(u'items'):
            for item in results[u'items']:
                obj = {'title' : item[u'title'],
                       'summary' : item[u'snippet'],
                       'link' : item[u'link']}
                parsed_links['items'].append(obj)
        if results.has_key(u'queries') and \
                results[u'queries'].has_key(u'request'):
            req = results[u'queries'][u'request'][0]
            parsed_links[u'count'] = req[u'count']
            parsed_links[u'index'] = int(req[u'startIndex'])
            parsed_links[u'total'] = int(req[u'totalResults'])

        return parsed_links
