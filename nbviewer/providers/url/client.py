"""Async HTTP client with bonus features!

- Support caching via upstream 304 with ETag, Last-Modified
- Log request timings for profiling
"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import hashlib
import pickle
import time

from tornado.simple_httpclient import SimpleAsyncHTTPClient
from tornado.log import app_log

from tornado import gen

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
    
    Currently, responses are cached for a non-configurable two hours.
    """
    
    cache = None
    expiry = 7200
    
    def fetch_impl(self, request, callback):
        self.io_loop.add_callback(lambda : self._fetch_impl(request, callback))
    
    @gen.coroutine
    def _fetch_impl(self, request, callback):
        tic = time.time()
        if request.user_agent is None:
            request.user_agent = 'Tornado-Async-Client'
        
        # when logging, use the URL without params
        name = request.url.split('?')[0]
        cached_response = None
        app_log.debug("Fetching %s", name)
        cache_key = hashlib.sha256(request.url.encode('utf8')).hexdigest()
        with time_block("Upstream cache get %s" % name):
            cached_response = yield self._get_cached_response(cache_key, name)
        
        if cached_response:
            app_log.debug("Upstream cache hit %s", name)
            # add cache headers, if any
            for resp_key, req_key in cache_headers.items():
                value = cached_response.headers.get(resp_key)
                if value:
                    request.headers[req_key] = value
        else:
            app_log.debug("Upstream cache miss %s", name)
        
        response = yield gen.Task(super(NBViewerAsyncHTTPClient, self).fetch_impl, request)
        dt = time.time() - tic
        log = app_log.info if dt > 1 else app_log.debug
        if response.code == 304 and cached_response:
            log("Upstream 304 on %s in %.2f ms", name, 1e3 * dt)
            response = self._update_cached_response(response, cached_response)
            callback(response)
        else:
            if not response.error:
                log("Fetched  %s in %.2f ms", name, 1e3 * dt)
            callback(response)
            if not response.error:
                yield self._cache_response(cache_key, name, response)
    
    def _update_cached_response(self, three_o_four, cached_response):
        """Apply any changes to the cached response from the 304

        Return the HTTPResponse to be used.

        Currently this hardcodes more recent GitHub rate limit headers,
        and that's it.
        Is there a better way for this to be in the right place?

        """
        # Copy GitHub rate-limit headers from 304 to the cached response
        # So we don't log stale rate limits.
        for key, value in three_o_four.headers.items():
            if key.lower().startswith('x-ratelimit-'):
                cached_response.headers[key] = value

        return cached_response

    @gen.coroutine
    def _get_cached_response(self, cache_key, name):
        """Get the cached response, if any"""
        if not self.cache:
            return
        try:
            cached_pickle = yield self.cache.get(cache_key)
            if cached_pickle:
                raise gen.Return(pickle.loads(cached_pickle))
        except gen.Return:
            raise # FIXME: remove gen.Return when we drop py2 support
        except Exception:
            app_log.error("Upstream cache get failed %s", name, exc_info=True)
    
    @gen.coroutine
    def _cache_response(self, cache_key, name, response):
        """Cache the response, if any cache headers we understand are present."""
        if not self.cache:
            return
        if not any(response.headers.get(key) for key in cache_headers):
            # no cache headers, no point in caching the response
            return
        with time_block("Upstream cache set %s" % name):
            # cache the response if there are any cache headers (use cache expiry?)
            try:
                pickle_response = pickle.dumps(response, pickle.HIGHEST_PROTOCOL)
                yield self.cache.set(
                    cache_key,
                    pickle_response,
                    int(time.time() + self.expiry),
                )
            except Exception:
                app_log.error("Upstream cache failed %s" % name, exc_info=True)


class NBViewerSimpleAsyncHTTPClient(NBViewerAsyncHTTPClient, SimpleAsyncHTTPClient):
    pass

try:
    from tornado.curl_httpclient import CurlAsyncHTTPClient
except ImportError:
    pass
else:
    class NBViewerCurlAsyncHTTPClient(NBViewerAsyncHTTPClient, CurlAsyncHTTPClient):
        pass

