#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import os
import zlib

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

class MockCache(object):
    """Mock Cache. Just stores nothing and always return None on get."""
    def __init__(self, *args, **kwargs):
        pass
    
    def get(self, key):
        f = Future()
        f.set_result(None)
        return f

    def set(self, key, value, *args, **kwargs):
        f = Future()
        f.set_result(None)
        return f

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
    """Wrap pylibmc.Client to run in a background thread
    
    via concurrent.futures.ThreadPoolExecutor
    """
    def __init__(self, *args, **kwargs):
        self.pool = kwargs.pop('pool', None) or ThreadPoolExecutor(1)
        
        self.mc = pylibmc.Client(*args, **kwargs)
        self.mc_pool = pylibmc.ThreadMappedPool(self.mc)
    
    def get(self, key, *args, **kwargs):
        app_log.debug("memcache get submit %s", key)
        return self.pool.submit(self._threadsafe_get, key, *args, **kwargs)
    
    def _threadsafe_get(self, key, *args, **kwargs):
        app_log.debug("memcache get %s", key)
        with self.mc_pool.reserve() as mc:
            return mc.get(key, *args, **kwargs)
    
    def set(self, key, *args, **kwargs):
        app_log.debug("memcache set submit %s", key)
        return self.pool.submit(self._threadsafe_set, key, *args, **kwargs)

    def _threadsafe_set(self, key, value, *args, **kwargs):
        app_log.debug("memcache set %s", key)
        with self.mc_pool.reserve() as mc:
            return mc.set(key, value, *args, **kwargs)

class AsyncMultipartMemcache(AsyncMemcache):
    """subclass of AsyncMemcache that splits large files into multiple chunks
    
    because memcached limits record size to 1MB
    """
    def __init__(self, *args, **kwargs):
        self.chunk_size = kwargs.pop('chunk_size', 950000)
        self.max_chunks = kwargs.pop('max_chunks', 16)
        super(AsyncMultipartMemcache, self).__init__(*args, **kwargs)
    
    def _threadsafe_get(self, key, *args, **kwargs):
        app_log.debug("memcache get %s", key)
        keys = [('%s.%i' % (key, idx)).encode()
                for idx in range(self.max_chunks)]
        with self.mc_pool.reserve() as mc:
            values = mc.get_multi(keys, *args, **kwargs)
        parts = []
        for key in keys:
            if key not in values:
                break
            parts.append(values[key])
        if parts:
            compressed = b''.join(parts)
            try:
                return zlib.decompress(compressed)
            except zlib.error as e:
                app_log.error("zlib decompression of %s failed: %s", key, e)
    
    def _threadsafe_set(self, key, value, *args, **kwargs):
        app_log.debug("memcache set %s", key)
        chunk_size = self.chunk_size
        compressed = zlib.compress(value)
        offsets = range(0, len(compressed), chunk_size)
        app_log.debug('storing %s in %i chunks', key, len(offsets))
        if len(offsets) > self.max_chunks:
            raise ValueError("file is too large: %sB" % len(compressed))
        values = {}
        for idx, offset in enumerate(offsets):
            values[('%s.%i' % (key, idx)).encode()] = compressed[
                offset:offset + chunk_size
            ]
        with self.mc_pool.reserve() as mc:
            return mc.set_multi(values, *args, **kwargs)

