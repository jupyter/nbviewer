"""Async HTTP client with bonus features!

- Support caching via upstream 304 with ETag, Last-Modified
- Log request timings for profiling
"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import hashlib
import pickle
import time

import asyncio

from tornado.httpclient import HTTPRequest, HTTPError
from tornado.curl_httpclient import CurlAsyncHTTPClient

from nbviewer.utils import time_block

#-----------------------------------------------------------------------------
# Async HTTP Client
#-----------------------------------------------------------------------------

# cache headers and their response:request mapping
# use this to map headers in cached response to the headers
# that should be set in the request.

cache_headers = {
    'ETag': 'If-None-Match',
    'Last-Modified': 'If-Modified-Since',
}

class NBViewerAsyncHTTPClient(object):
    """Subclass of AsyncHTTPClient with bonus logging and caching!
    
    If upstream servers support 304 cache replies with the following headers:
    
    - ETag : If-None-Match
    - Last-Modified : If-Modified-Since
    
    Upstream requests are still made every time,
    but resources and rate limits may be saved by 304 responses.
    
    If upstream responds with 304 or an error and a cached response is available,
    use the cached response.
    
    Responses are cached as long as possible.
    """

    cache = None

    def __init__(self, log, client=None):
        self.log = log
        self.client = client or CurlAsyncHTTPClient()

    def fetch(self, url, params=None, **kwargs):
        request = HTTPRequest(url, **kwargs)

        if request.user_agent is None:
            request.user_agent = 'Tornado-Async-Client'

        # The future which will become the response upon awaiting.
        response_future = asyncio.ensure_future(self.smart_fetch(request))

        return response_future

    async def smart_fetch(self, request):
        """
        Before fetching request, first look to see whether it's already in cache.
        If so load the response from cache. Only otherwise attempt to fetch the request.
        When response code isn't 304 or 400, cache response before loading, else just load.
        """
        tic = time.time()

        # when logging, use the URL without params
        name = request.url.split('?')[0]
        self.log.debug("Fetching %s", name)

        # look for a cached response
        cached_response = None
        cache_key = hashlib.sha256(request.url.encode('utf8')).hexdigest()
        cached_response = await self._get_cached_response(cache_key, name)
        toc = time.time()
        self.log.info("Upstream cache get %s %.2f ms", name, 1e3 * (toc-tic))

        if cached_response:
            self.log.info("Upstream cache hit %s", name)
            # add cache headers, if any
            for resp_key, req_key in cache_headers.items():
                value = cached_response.headers.get(resp_key)
                if value:
                    request.headers[req_key] = value
            return cached_response
        else:
            self.log.info("Upstream cache miss %s", name)

            response = await self.client.fetch(request)
            dt = time.time() - tic
            self.log.info("Fetched %s in %.2f ms", name, 1e3 * dt)
            await self._cache_response(cache_key, name, response)
            return response

    async def _get_cached_response(self, cache_key, name):
        """Get the cached response, if any"""
        if not self.cache:
            return
        try:
            cached_pickle = await self.cache.get(cache_key)
            if cached_pickle:
                self.log.info("Type of self.cache is: %s", type(self.cache))
                return pickle.loads(cached_pickle)
        except Exception:
            self.log.error("Upstream cache get failed %s", name, exc_info=True)
    
    async def _cache_response(self, cache_key, name, response):
        """Cache the response, if any cache headers we understand are present."""
        if not self.cache:
            return
        with time_block("Upstream cache set %s" % name, logger=self.log):
            # cache the response
            try:
                pickle_response = pickle.dumps(response, pickle.HIGHEST_PROTOCOL)
                await self.cache.set(
                    cache_key,
                    pickle_response,
                )
            except Exception:
                self.log.error("Upstream cache failed %s" % name, exc_info=True)

