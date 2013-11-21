#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import os

from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import Future

from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import url_concat
from tornado.log import app_log

try:
    import pylibmc
except ImportError:
    pylibmc = None

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

class DummyAsyncCache(object):
    """Dummy Async Cache. Just stores things in a dict of fixed size."""
    def __init__(self, limit=10):
        self._cache = {}
        self._cache_order = []
        self.limit = limit
    
    def get(self, key):
        f = Future()
        f.set_result(self._cache.get(key))
        return f

    def set(self, key, value, time=0):
        if key in self._cache and self._cache_order[-1] != key:
            idx = self._cache_order.index(key)
            del self._cache_order[idx]
            self._cache_order.append(key)
        else:
            if len(self._cache) >= self.limit:
                oldest = self._cache_order.pop(0)
                self._cache.pop(oldest)
            self._cache_order.append(key)
        self._cache[key] = value
        f = Future()
        f.set_result(None)
        return f

class AsyncMemcache(object):
    """subclass pylibmc.Client that runs requests in a background thread
    
    via concurrent.futures.ThreadPoolExecutor
    """
    def __init__(self, *args, **kwargs):
        self.pool = kwargs.pop('pool', None) or ThreadPoolExecutor(1)
        self.mc = pylibmc.Client(*args, **kwargs)
        self.mc_pool = pylibmc.ThreadMappedPool(self.mc)
    
    def get(self, *args, **kwargs):
        return self.pool.submit(self._threadsafe_get, *args, **kwargs)
    
    def _threadsafe_get(self, *args, **kwargs):
        with self.mc_pool.reserve() as mc:
            return mc.get(*args, **kwargs)
    
    def set(self, *args, **kwargs):
        return self.pool.submit(self._threadsafe_set, *args, **kwargs)

    def _threadsafe_set(self, *args, **kwargs):
        with self.mc_pool.reserve() as mc:
            return mc.set(*args, **kwargs)

