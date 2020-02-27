#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import json
import os

from urllib.parse import urlparse

from tornado.httpclient import AsyncHTTPClient, HTTPError
from tornado.httputil import url_concat

from ...utils import url_path_join, quote, response_text

#-----------------------------------------------------------------------------
# Async GitHub Client
#-----------------------------------------------------------------------------

class AsyncGitHubClient(object):
    """AsyncHTTPClient wrapper with methods for common requests"""
    auth = None
    
    def __init__(self, log, client=None):
        self.log = log
        self.client = client or AsyncHTTPClient()
        self.github_api_url = os.environ.get('GITHUB_API_URL', 'https://api.github.com/')
        self.authenticate()

    def authenticate(self):
        self.auth = {
            'client_id': os.environ.get('GITHUB_OAUTH_KEY', ''),
            'client_secret': os.environ.get('GITHUB_OAUTH_SECRET', ''),
            'access_token': os.environ.get('GITHUB_API_TOKEN', ''),
        }

    def fetch(self, url, params=None, **kwargs):
        """Add GitHub auth to self.client.fetch"""
        if not url.startswith(self.github_api_url):
            raise ValueError(
                "Only fetch GitHub urls with GitHub auth (%s)" % url
            )
        params = {} if params is None else params
        kwargs.setdefault('user_agent', 'Tornado-Async-GitHub-Client')

        if self.auth['client_id'] and self.auth['client_secret']:
            kwargs['auth_username'] = self.auth['client_id']
            kwargs['auth_password'] = self.auth['client_secret']

        if self.auth['access_token']:
            headers = kwargs.setdefault('headers', {})
            headers['Authorization'] = 'token ' + self.auth['access_token']

        url = url_concat(url, params)
        future = self.client.fetch(url, **kwargs)
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
            if r is None:
                # some errors don't have a response (e.g. failure to build request)
                return
        limit_s = r.headers.get('X-RateLimit-Limit', '')
        remaining_s = r.headers.get('X-RateLimit-Remaining', '')
        if not remaining_s or not limit_s:
            if r.code < 300:
                self.log.warn("No rate limit headers. Did GitHub change? %s",
                    json.dumps(dict(r.headers), indent=1)
                )
            return
        
        remaining = int(remaining_s)
        limit = int(limit_s)
        if remaining == 0 and r.code >= 400:
            text = response_text(r)
            try:
                message = json.loads(text)['message']
            except Exception:
                # Can't extract message, log full reply
                message = text
            self.log.error("GitHub rate limit (%s) exceeded: %s", limit, message)
            return
        
        if 10 * remaining > limit:
            log = self.log.info
        else:
            log = self.log.warn
        log("%i/%i GitHub API requests remaining", remaining, limit)

    def github_api_request(self, path, **kwargs):
        """Make a GitHub API request to URL
        
        URL is constructed from url and params, if specified.
        **kwargs are passed to client.fetch unmodified.
        """
        url = url_path_join(self.github_api_url, quote(path))
        return self.fetch(url, **kwargs)

    def get_gist(self, gist_id, **kwargs):
        """Get a gist"""
        path = u'gists/{}'.format(gist_id)
        return self.github_api_request(path, **kwargs)
    
    def get_contents(self, user, repo, path, ref=None, **kwargs):
        """Make contents API request - either file contents or directory listing"""
        path = u'repos/{user}/{repo}/contents/{path}'.format(**locals())
        if ref is not None:
            params = kwargs.setdefault('params', {})
            params['ref'] = ref
        return self.github_api_request(path, **kwargs)
    
    def get_repos(self, user, **kwargs):
        """List a user's repos"""
        path = u"users/{user}/repos".format(user=user)
        return self.github_api_request(path, **kwargs)
    
    def get_gists(self, user, **kwargs):
        """List a user's gists"""
        path = u"users/{user}/gists".format(user=user)
        return self.github_api_request(path, **kwargs)
    
    def get_tree(self, user, repo, path, ref='master', recursive=False, **kwargs):
        """Get a git tree"""
        # only need a recursive fetch if it's not in the top-level dir
        if '/' in path:
            recursive = True
        path = u"repos/{user}/{repo}/git/trees/{ref}".format(**locals())
        if recursive:
            params = kwargs.setdefault('params', {})
            params['recursive'] = True
        tree = self.github_api_request(path, **kwargs)
        return tree
    
    def get_branches(self, user, repo, **kwargs):
        """List a repo's branches"""
        path = u"repos/{user}/{repo}/branches".format(user=user, repo=repo)
        return self.github_api_request(path, **kwargs)
    
    def get_tags(self, user, repo, **kwargs):
        """List a repo's branches"""
        path = u"repos/{user}/{repo}/tags".format(user=user, repo=repo)
        return self.github_api_request(path, **kwargs)
    
    def extract_tree_entry(self, path, tree_response):
        """extract a single tree entry from
        a tree response using for a path
        
        raises 404 if not found

        Useful for finding the blob url for a given path.
        """
        tree_response.rethrow()
        self.log.debug(tree_response)
        jsondata = response_text(tree_response)
        data = json.loads(jsondata)
        for entry in data['tree']:
            if entry['path'] == path:
                return entry
        
        raise HTTPError(404, "%s not found among %i files" % (path, len(data['tree'])))
