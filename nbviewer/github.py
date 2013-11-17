#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import os
try:
    from urllib.request import quote
except ImportError:
    from urllib2 import quote

from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import url_concat
from tornado.log import app_log

#-----------------------------------------------------------------------------
# Async GitHub Client
#-----------------------------------------------------------------------------

class AsyncGitHubClient(object):
    """AsyncHTTPClient wrapper with methods for common requests"""
    github_api_url = 'https://api.github.com/'
    auth = None
    def __init__(self, client=None):
        self.client = client or AsyncHTTPClient()
        self.authenticate()
    
    def authenticate(self):
        self.auth = os.environ.get('GITHUB_API_TOKEN', None)
    
    def github_api_request(self, url, callback=None, params=None, **kwargs):
        """Make a GitHub API request to URL
        
        URL is constructed from url and params, if specified.
        callback and **kwargs are passed to client.fetch unmodified.
        """
        params = {} if params is None else params
        if self.auth:
            params['token'] = self.auth
        url = url_concat(url, params)
        app_log.info("Fetching %s", url)
        future = self.client.fetch(url, callback, **kwargs)
        return future
        
    def get_gist(self, gist_id, callback=None, **kwargs):
        url = self.github_api_url + 'gists/{}'.format(gist_id)
        return self.github_api_request(url, callback, **kwargs)
    
    def get_contents(self, owner, repo, path, callback=None, ref=None, **kwargs):
        path = quote('repos/{owner}/{repo}/contents/{path}'.format(
            **locals()
        ))
        url =  self.github_api_url + path
        if ref is not None:
            params = kwargs.setdefault('params', {})
            params['ref'] = ref
        return self.github_api_request(url, callback, **kwargs)
    
    
