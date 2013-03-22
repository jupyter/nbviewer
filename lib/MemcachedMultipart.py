"""
Simple Subclass of memcached client that split
the key/value into multipart if they are bigger than a certain treshold.
"""

from flask.ext.cache.backends import SASLMemcachedCache
import cPickle as pickle


class MemcachedMultipart(SASLMemcachedCache):
    """
    Simple Subclass of SASL Memcached client that split
    the key/value into multipart if they are bigger than a certain treshold.
    """

    def __init__(self, *args, **kwargs):
        super(MemcachedMultipart, self).__init__(*args, **kwargs)

    def set(self, key, value, timeout=None, chunksize=950000):
        """set a key to value, eventually splittig it in multiple part"""

        serialized = pickle.dumps(value, 2)
        values = {}
        len_ser = len(serialized)
        chks = xrange(0, len_ser, chunksize)
        print 'cut in', len(chks), 'chuncks'
        for i in chks:
            values['%s.%s' % (key, i//chunksize)] = serialized[i : i+chunksize]
        super(MemcachedMultipart, self).set_many(values, timeout)

    def get(self, key):
        """get a key, eventually splitted in multiple part"""
        to_get = ['%s.%s' % (key, i) for i in xrange(32)]
        result = super(MemcachedMultipart, self).get_many( *to_get)
        serialized = ''.join([v for v in result if v is not None])
        if not serialized:
            return None
        return pickle.loads(serialized)

def multipartmemecached(app, config, args, kwargs):
    """methods to register  with flask cache"""

    args.append(config['CACHE_MEMCACHED_SERVERS'])
    kwargs.update(dict(username=config.get('CACHE_MEMCACHED_USERNAME'),
                      password=config.get('CACHE_MEMCACHED_PASSWORD'),
                      key_prefix=config['CACHE_KEY_PREFIX']))
    return MemcachedMultipart(*args, **kwargs)
