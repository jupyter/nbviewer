#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import os

from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import url_concat
from tornado.log import app_log

from .utils import url_path_join, quote

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
        self.auth = {
            'client_id': os.environ.get('GITHUB_OAUTH_KEY', ''),
            'client_secret': os.environ.get('GITHUB_OAUTH_SECRET', ''),
            'token' : os.environ.get('GITHUB_API_TOKEN', ''),
        }
        self.auth = {k:v for k,v in self.auth.items() if v}
    
    def github_api_request(self, path, callback=None, params=None, **kwargs):
        """Make a GitHub API request to URL
        
        URL is constructed from url and params, if specified.
        callback and **kwargs are passed to client.fetch unmodified.
        """
        url = url_path_join(self.github_api_url, path)
        
        params = {} if params is None else params
        headers = kwargs.setdefault('headers', {})
        headers.setdefault('User-Agent', 'Tornado-Async-GitHub-Client')
        # don't log auth
        app_log.info("Fetching %s", url_concat(url, params))
        if self.auth:
            params.update(self.auth)
        url = url_concat(url, params)
        future = self.client.fetch(url, callback, **kwargs)
        return future
        
    def get_gist(self, gist_id, callback=None, **kwargs):
        """Get a gist"""
        path = 'gists/{}'.format(gist_id)
        return self.github_api_request(path, callback, **kwargs)
    
    def get_contents(self, user, repo, path, callback=None, ref=None, **kwargs):
        """Make contents API request - either file contents or directory listing"""
        path = quote('repos/{user}/{repo}/contents/{path}'.format(
            **locals()
        ))
        if ref is not None:
            params = kwargs.setdefault('params', {})
            params['ref'] = ref
        return self.github_api_request(path, callback, **kwargs)
    
    def get_repos(self, user, callback=None, **kwargs):
        """List a user's repos"""
        path = "users/{user}/repos".format(user=user)
        return self.github_api_request(path, callback ,**kwargs)
    
    def get_gists(self, user, callback=None, **kwargs):
        """List a user's gists"""
        path = "users/{user}/gists".format(user=user)
        return self.github_api_request(path, callback ,**kwargs)
    
