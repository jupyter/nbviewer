__author__ = 'mt'

import os
import requests
from tornado.log import app_log

class GoogleSearchClient:

    google_api_url = 'https://www.googleapis.com/customsearch/v1'

    def __init__(self):
        self.search_auth_key = os.environ.get('GOOGLE_SEARCH_KEY', '')
        self.search_auth_cx =  os.environ.get('GOOGLE_SEARCH_CX', '')

    def search(self, search_phrase):
        """ Queries google for all the notebooks

        """
        query = u'filetype:ipynb ' + search_phrase
        search_params = {'key' : self.search_auth_key,
                        'cx'  : self.search_auth_cx,
                        'q'   : query}
        app_log.info("Searching google with query: %s", query)
        results = requests.get(self.google_api_url, verify = False, params = search_params).json()

        app_log.info(results)

        parsed_links = []
        if results.has_key(u'items'):
            for item in results[u'items']:
                obj = {'title' : item[u'title'],
                       'summary' : item[u'snippet'],
                       'link' : item[u'link']}
                parsed_links.append(obj)

        return parsed_links
