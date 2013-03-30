"""
Simple Subclass of memcached client that split
the key/value into multipart if they are bigger than a certain threshold.
"""

from flask.ext.cache.backends import SASLMemcachedCache
import cPickle as pickle


class MemcachedMultipart(SASLMemcachedCache):
    """
    Simple Subclass of SASL Memcached client that split
    the key/value into multipart if they are bigger than a certain threshold.
    """

    def __init__(self, *args, **kwargs):
        super(MemcachedMultipart, self).__init__(*args, **kwargs)

    def set(self, key, value, timeout=None, chunksize=950000):
        """set a key to value, eventually splittig it in multiple part"""

        serialized = pickle.dumps(value, 2)
        values = {}
        len_ser = len(serialized)
        chks = xrange(0, len_ser, chunksize)
        print 'storing cache in %i chunks' % len(chks)
        for i in chks:
            values['%s.%s' % (key, i//chunksize)] = serialized[i : i+chunksize]
        try:
            super(MemcachedMultipart, self).set_many(values, timeout)
        except Exception as e:
            print "memcache set failed!", e

    def get(self, key):
        """get a key, split into multiple parts"""
        to_get = ['%s.%s' % (key, i) for i in xrange(64)]
        try:
            result = super(MemcachedMultipart, self).get_many( *to_get)
        except Exception as e:
            print "memcache get failed", e
            return None
        serialized = ''.join([v for v in result if v is not None])
        if not serialized:
            return None
        try:
            return pickle.loads(serialized)
        except Exception as e:
            print "memcache get failed, presumably because it's only partial in the cache"
            print e
            return None

def multipartmemecached(app, config, args, kwargs):
    """methods to register  with flask cache"""

    args.append(config['CACHE_MEMCACHED_SERVERS'])
    kwargs.update(dict(username=config.get('CACHE_MEMCACHED_USERNAME'),
                      password=config.get('CACHE_MEMCACHED_PASSWORD'),
                      key_prefix=config['CACHE_KEY_PREFIX']))
    return MemcachedMultipart(*args, **kwargs)
