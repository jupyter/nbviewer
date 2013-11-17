#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import os

from tornado.concurrent import Future

from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import url_concat
from tornado.log import app_log

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

class DummyAsyncCache(object):
    """Dummy Async Cache. Just stores things in a dict of fixed size."""
    def __init__(self, limit=10):
        self._cache = {}
        self._cache_order = []
        self.limit = limit
    
    def get(self, key, callback=None):
        result = self._cache.get(key, None)
        if callback:
            callback(result)

    def set(self, key, value, time=0, callback=None):
        if key in self._cache and self._cache_order[-1] != key:
            idx = self._cache_order.rfind(key)
            del self._cache_order[idx]
            self._cache_order.append(key)
        else:
            if len(self._cache) >= self.limit:
                oldest = self._cache_order.pop(0)
                self._cache.pop(oldest)
            self._cache_order.append(key)
        self._cache[key] = value
        if callback:
            callback(None)

