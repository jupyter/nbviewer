#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import zlib
from time import monotonic

from concurrent.futures import ThreadPoolExecutor
from tornado.concurrent import Future

from tornado import gen
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

    def add(self, key, value, *args, **kwargs):
        f = Future()
        f.set_result(True)
        return f

    def incr(self, key):
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
        f.set_result(self._get(key))
        return f

    def _get(self, key):
        value, deadline = self._cache.get(key, (None, None))
        if deadline and deadline < monotonic():
            self._cache.pop(key)
            self._cache_order.remove(key)
        else:
            return value

    def set(self, key, value, expires=0):
        if key in self._cache and self._cache_order[-1] != key:
            idx = self._cache_order.index(key)
            del self._cache_order[idx]
            self._cache_order.append(key)
        else:
            if len(self._cache) >= self.limit:
                oldest = self._cache_order.pop(0)
                self._cache.pop(oldest)
            self._cache_order.append(key)

        if not expires:
            deadline = None
        else:
            deadline = monotonic() + expires

        self._cache[key] = (value, deadline)
        f = Future()
        f.set_result(True)
        return f
    
    def add(self, key, value, expires=0):
        f = Future()
        if self._get(key) is not None:
            f.set_result(False)
        else:
            self.set(key, value, expires)
            f.set_result(True)
        return f

    def incr(self, key):
        f = Future()
        if self._get(key) is not None:
            value, deadline = self._cache[key]
            value = value + 1
            self._cache[key] = (value, deadline)
        else:
            value = None
        f.set_result(value)
        return f

class AsyncMemcache(object):
    """Wrap pylibmc.Client to run in a background thread
    
    via concurrent.futures.ThreadPoolExecutor
    """
    def __init__(self, *args, **kwargs):
        self.pool = kwargs.pop('pool', None) or ThreadPoolExecutor(1)
        
        self.mc = pylibmc.Client(*args, **kwargs)
        self.mc_pool = pylibmc.ThreadMappedPool(self.mc)
    
    def _call_in_thread(self, method_name, *args, **kwargs):
        key = args[0]
        if 'multi' in method_name:
            key = sorted(key)[0].decode('ascii') + '[%i]' % len(key)
        app_log.debug("memcache submit %s %s", method_name, key)
        def f():
            app_log.debug("memcache %s %s", method_name, key)
            with self.mc_pool.reserve() as mc:
                meth = getattr(mc, method_name)
                return meth(*args, **kwargs)
        return self.pool.submit(f)
    
    def get(self, *args, **kwargs):
        return self._call_in_thread('get', *args, **kwargs)
    
    def set(self, *args, **kwargs):
        return self._call_in_thread('set', *args, **kwargs)
    
    def add(self, *args, **kwargs):
        return self._call_in_thread('add', *args, **kwargs)
    
    def incr(self, *args, **kwargs):
        return self._call_in_thread('incr', *args, **kwargs)

class AsyncMultipartMemcache(AsyncMemcache):
    """subclass of AsyncMemcache that splits large files into multiple chunks
    
    because memcached limits record size to 1MB
    """
    def __init__(self, *args, **kwargs):
        self.chunk_size = kwargs.pop('chunk_size', 950000)
        self.max_chunks = kwargs.pop('max_chunks', 16)
        super(AsyncMultipartMemcache, self).__init__(*args, **kwargs)
    
    @gen.coroutine
    def get(self, key, *args, **kwargs):
        keys = [('%s.%i' % (key, idx)).encode()
                for idx in range(self.max_chunks)]
        values = yield self._call_in_thread('get_multi', keys, *args, **kwargs)
        parts = []
        for key in keys:
            if key not in values:
                break
            parts.append(values[key])
        if parts:
            compressed = b''.join(parts)
            try:
                result = zlib.decompress(compressed)
            except zlib.error as e:
                app_log.error("zlib decompression of %s failed: %s", key, e)
            else:
                raise gen.Return(result)
    
    @gen.coroutine
    def set(self, key, value, *args, **kwargs):
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
        return self._call_in_thread('set_multi', values, *args, **kwargs)

