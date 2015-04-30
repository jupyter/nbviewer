#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import json
import os

try: # py3
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from tornado.concurrent import Future
from tornado.httpclient import AsyncHTTPClient, HTTPError
from tornado.httputil import url_concat
from tornado.log import app_log

from ...utils import url_path_join, quote, response_text

#-----------------------------------------------------------------------------
# Async GitHub Client
#-----------------------------------------------------------------------------

class AsyncGitHubClient(object):
    """AsyncHTTPClient wrapper with methods for common requests"""
    auth = None
    
    def __init__(self, client=None):
        self.client = client or AsyncHTTPClient()
        self.github_api_url = os.environ.get('GITHUB_API_URL', 'https://api.github.com/')
        self.authenticate()
    
    def authenticate(self):
        self.auth = {
            'client_id': os.environ.get('GITHUB_OAUTH_KEY', ''),
            'client_secret': os.environ.get('GITHUB_OAUTH_SECRET', ''),
            'access_token' : os.environ.get('GITHUB_API_TOKEN', ''),
        }
        self.auth = {k:v for k,v in self.auth.items() if v}
    
    def fetch(self, url, callback=None, params=None, **kwargs):
        """Add GitHub auth to self.client.fetch"""
        host = urlparse(url).hostname

        if not url.startswith(self.github_api_url):
            raise ValueError(
                "Only fetch GitHub urls with GitHub auth (%s)" % url
            )
        params = {} if params is None else params
        kwargs.setdefault('user_agent', 'Tornado-Async-GitHub-Client')
        if self.auth:
            params.update(self.auth)
        url = url_concat(url, params)
        future = self.client.fetch(url, callback, **kwargs)
        future.add_done_callback(self._log_rate_limit)
        return future
    
    def _log_rate_limit(self, future):
        """log GitHub rate limit headers
        
        - error if 0 remaining
        - warn if 10% or less remain
        - debug otherwise
        """
        try:
            r = future.result()
        except HTTPError as e:
            r = e.response
        limit_s = r.headers.get('X-RateLimit-Limit', '')
        remaining_s = r.headers.get('X-RateLimit-Remaining', '')
        if not remaining_s or not limit_s:
            if r.code < 300:
                app_log.warn("No rate limit headers. Did GitHub change? %s",
                    json.dumps(r.headers, indent=1)
                )
            return
        
        remaining = int(remaining_s)
        limit = int(limit_s)
        if remaining == 0:
            jsondata = response_text(r)
            data = json.loads(jsondata)
            app_log.error("GitHub rate limit (%s) exceeded: %s", limit, data.get('message', 'no message'))
            return
        
        if 10 * remaining > limit:
            log = app_log.debug
        else:
            log = app_log.warn
        log("%i/%i GitHub API requests remaining", remaining, limit)

    def github_api_request(self, path, callback=None, **kwargs):
        """Make a GitHub API request to URL
        
        URL is constructed from url and params, if specified.
        callback and **kwargs are passed to client.fetch unmodified.
        """
        url = url_path_join(self.github_api_url, path)
        return self.fetch(url, callback, **kwargs)

    def get_gist(self, gist_id, callback=None, **kwargs):
        """Get a gist"""
        path = u'gists/{}'.format(gist_id)
        return self.github_api_request(path, callback, **kwargs)
    
    def get_contents(self, user, repo, path, callback=None, ref=None, **kwargs):
        """Make contents API request - either file contents or directory listing"""
        path = quote(u'repos/{user}/{repo}/contents/{path}'.format(
            **locals()
        ))
        if ref is not None:
            params = kwargs.setdefault('params', {})
            params['ref'] = ref
        return self.github_api_request(path, callback, **kwargs)
    
    def get_repos(self, user, callback=None, **kwargs):
        """List a user's repos"""
        path = u"users/{user}/repos".format(user=user)
        return self.github_api_request(path, callback, **kwargs)
    
    def get_gists(self, user, callback=None, **kwargs):
        """List a user's gists"""
        path = u"users/{user}/gists".format(user=user)
        return self.github_api_request(path, callback, **kwargs)
    
    def get_tree(self, user, repo, ref='master', recursive=False, callback=None, **kwargs):
        """Get a git tree"""
        path = u"repos/{user}/{repo}/git/trees/{ref}".format(**locals())
        if recursive:
            params = kwargs.setdefault('params', {})
            params['recursive'] = True
        return self.github_api_request(path, callback, **kwargs)
    
    def get_branches(self, user, repo, callback=None, **kwargs):
        """List a repo's branches"""
        path = u"repos/{user}/{repo}/branches".format(user=user, repo=repo)
        return self.github_api_request(path, callback, **kwargs)
    
    def get_tags(self, user, repo, callback=None, **kwargs):
        """List a repo's branches"""
        path = u"repos/{user}/{repo}/tags".format(user=user, repo=repo)
        return self.github_api_request(path, callback, **kwargs)
    
    def _extract_tree_entry(self, path, tree_response):
        """extract a single tree entry from a file list
        
        For use as a callback in get_tree_entry
        raises 404 if not found
        """
        tree_response.rethrow()
        jsondata = response_text(tree_response)
        data = json.loads(jsondata)
        for entry in data['tree']:
            if entry['path'] == path:
                return entry
        
        raise HTTPError(404, "%s not found among %i files" % (path, len(data['tree'])))
    
    def get_tree_entry(self, user, repo, path, ref='master', callback=None, **kwargs):
        """Get a single tree entry for a path
        
        Useful for finding the blob url for a given path.
        """
        # only need a recursive fetch if it's not in the top-level dir
        if '/' in path:
            kwargs['recursive'] = True
        
        f = Future()
        def cb(response):
            try:
                tree_entry = self._extract_tree_entry(path, response)
            except Exception as e:
                f.set_exception(e)
                return
            if callback:
                result = callback(tree_entry)
            else:
                result = tree_entry
            f.set_result(result)
        
        self.get_tree(user, repo, ref=ref, callback=cb, **kwargs)
        return f
    
