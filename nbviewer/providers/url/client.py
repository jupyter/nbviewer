#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import hashlib
import pickle
import time

from tornado.simple_httpclient import SimpleAsyncHTTPClient
from tornado.log import app_log

from tornado import gen

#-----------------------------------------------------------------------------
# Async GitHub Client
#-----------------------------------------------------------------------------

# cache headers and their response:request mapping
# use this to map headers in cached response to the headers
# that should be set in the request.

cache_headers = {
    'ETag': 'If-None-Match',
    'Last-Modified': 'If-Modified-Since',
}

class NBViewerAsyncHTTPClient(object):
    """Subclass of AsyncHTTPClient with bonus logging and caching!"""
    
    def __init__(self, cache=None):
        self.cache = cache
    
    def fetch_impl(self, request, callback):
        self.io_loop.add_callback(lambda : self._cached_fetch(request, callback))
    
    @gen.coroutine
    def _cached_fetch(self, request, callback):
        tic = time.time()
        if request.user_agent is None:
            request.user_agent = 'Tornado-Async-Client'

        without_params = request.url.split('?')[0]
        cached_response = None
        app_log.debug("Fetching %s", without_params)
        cache_key = hashlib.sha256(request.url.encode('utf8')).hexdigest()
        if self.cache:
            cache_tic = time.time()
            try:
                cached_pickle = yield self.cache.get(cache_key)
                if cached_pickle:
                    cached_response = pickle.loads(cached_pickle)
            except Exception:
                app_log.error("Failed to get cached response for %s",
                    without_params, exc_info=True)
        if cached_response:
            app_log.info("Have cached response for %s", without_params)
            dt = time.time() - cache_tic
            app_log.debug("Upstream response cache hit for %s in %.2f ms",
                without_params, 1e3 * dt)
            # add cache headers, if any
            for resp_key, req_key in cache_headers.items():
                value = cached_response.headers.get(resp_key)
                if value:
                    request.headers[req_key] = value
        
        @gen.coroutine
        def finish(response):
            dt = time.time() - tic
            log = app_log.info if dt > 1 else app_log.debug
            if response.code == 304 and cached_response:
                log("Upstream 304 on %s in %.2f ms", without_params, 1e3 * dt)
                callback(cached_response)
            else:
                if not response.error:
                    log("Fetched  %s in %.2f ms", without_params, 1e3 * dt)
                callback(response)
                if self.cache:
                    yield self.cache_response(response)
                yield self.
                if self.cache and not response.error and any(response.headers.get(key) for key in cache_headers):
                    # cache for two hours if there are any cache headers (use cache expiry?)
                    cache_tic = time.time()
                    expiry = 7200
                    try:
                        pickle_response = pickle.dumps(response, pickle.HIGHEST_PROTOCOL)
                        yield self.cache.set(
                            cache_key,
                            pickle_response,
                            int(time.time() + expiry),
                        )
                    except Exception:
                        app_log.error("Failed to cache response for %s" % without_params, exc_info=True)
                    else:
                        dt = time.time() - cache_tic
                        app_log.debug("Cached upstream response for %s in %.2f ms",
                            without_params, 1e3 * dt)
        
        super(NBViewerAsyncHTTPClient, self).fetch_impl(request, finish)


class NBViewerSimpleAsyncHTTPClient(NBViewerAsyncHTTPClient, SimpleAsyncHTTPClient):
    pass

try:
    from tornado.curl_httpclient import CurlAsyncHTTPClient
except ImportError:
    pass
else:
    class NBViewerCurlAsyncHTTPClient(NBViewerAsyncHTTPClient, CurlAsyncHTTPClient):
        pass

