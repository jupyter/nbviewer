#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import zlib
from time import monotonic

from concurrent.futures import ThreadPoolExecutor
from asyncio import Future

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
    
    async def get(self, key):
        f = Future()
        f.set_result(None)
        return await f

    async def set(self, key, value, *args, **kwargs):
        f = Future()
        f.set_result(None)
        return await f

    async def add(self, key, value, *args, **kwargs):
        f = Future()
        f.set_result(True)
        return await f

    async def incr(self, key):
        f = Future()
        f.set_result(None)
        return await f

class DummyAsyncCache(object):
    """Dummy Async Cache. Just stores things in a dict of fixed size."""
    def __init__(self, limit=10):
        self._cache = {}
        self._cache_order = []
        self.limit = limit

    async def get(self, key):
        f = Future()
        f.set_result(self._get(key))
        return await f

    def _get(self, key):
        value, deadline = self._cache.get(key, (None, None))
        if deadline and deadline < monotonic():
            self._cache.pop(key)
            self._cache_order.remove(key)
        else:
            return value

    async def set(self, key, value, expires=0):
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
        return await f
    
    async def add(self, key, value, expires=0):
        f = Future()
        if self._get(key) is not None:
            f.set_result(False)
        else:
            await self.set(key, value, expires)
            f.set_result(True)
        return await f

    async def incr(self, key):
        f = Future()
        if self._get(key) is not None:
            value, deadline = self._cache[key]
            value = value + 1
            self._cache[key] = (value, deadline)
        else:
            value = None
        f.set_result(value)
        return await f

class AsyncMemcache(object):
    """Wrap pylibmc.Client to run in a background thread
    
    via concurrent.futures.ThreadPoolExecutor
    """
    def __init__(self, *args, **kwargs):
        self.pool = kwargs.pop('pool', None) or ThreadPoolExecutor(1)
        
        self.mc = pylibmc.Client(*args, **kwargs)
        self.mc_pool = pylibmc.ThreadMappedPool(self.mc)
        
        self.loop = asyncio.get_event_loop()

    async def _call_in_thread(self, method_name, *args, **kwargs):
        # https://stackoverflow.com/questions/34376814/await-future-from-executor-future-cant-be-used-in-await-expression

        key = args[0]
        if 'multi' in method_name:
            key = sorted(key)[0].decode('ascii') + '[%i]' % len(key)
        app_log.debug("memcache submit %s %s", method_name, key)
        def f():
            app_log.debug("memcache %s %s", method_name, key)
            with self.mc_pool.reserve() as mc:
                meth = getattr(mc, method_name)
                return meth(*args, **kwargs)
        return await self.loop.run_in_executor(self.pool, f)
    
    async def get(self, *args, **kwargs):
        return await self._call_in_thread('get', *args, **kwargs)
    
    async def set(self, *args, **kwargs):
        return await self._call_in_thread('set', *args, **kwargs)
    
    async def add(self, *args, **kwargs):
        return await self._call_in_thread('add', *args, **kwargs)
    
    async def incr(self, *args, **kwargs):
        return await self._call_in_thread('incr', *args, **kwargs)

class AsyncMultipartMemcache(AsyncMemcache):
    """subclass of AsyncMemcache that splits large files into multiple chunks
    
    because memcached limits record size to 1MB
    """
    def __init__(self, *args, **kwargs):
        self.chunk_size = kwargs.pop('chunk_size', 950000)
        self.max_chunks = kwargs.pop('max_chunks', 16)
        super().__init__(*args, **kwargs)
    
    async def get(self, key, *args, **kwargs):
        keys = [('%s.%i' % (key, idx)).encode()
                for idx in range(self.max_chunks)]
        values = await self._call_in_thread('get_multi', keys, *args, **kwargs)
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
                return result
    
    async def set(self, key, value, *args, **kwargs):
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
        return await self._call_in_thread('set_multi', values, *args, **kwargs)

