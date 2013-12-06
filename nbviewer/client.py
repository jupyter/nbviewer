#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import time

from tornado.simple_httpclient import SimpleAsyncHTTPClient
from tornado.log import app_log

#-----------------------------------------------------------------------------
# Async GitHub Client
#-----------------------------------------------------------------------------

class LoggingAsyncHTTPClient(object):
    """Subclass of AsyncHTTPClient with bonus logging!"""
    
    def fetch_impl(self, request, callback):
        without_params = request.url.split('?')[0]
        app_log.info("Fetching %s", without_params)
        tic = time.time()
        if request.user_agent is None:
            request.user_agent = 'Tornado-Async-Client'

        def log_callback(result):
            toc = time.time()
            app_log.info("Fetched  %s in %.2f ms", without_params, toc-tic)
            callback(result)
        return super(LoggingAsyncHTTPClient, self).fetch_impl(request, log_callback)
    
class LoggingSimpleAsyncHTTPClient(LoggingAsyncHTTPClient, SimpleAsyncHTTPClient):
    pass

try:
    from tornado.curl_httpclient import CurlAsyncHTTPClient
except ImportError:
    pass
else:
    class LoggingCurlAsyncHTTPClient(LoggingAsyncHTTPClient, CurlAsyncHTTPClient):
        pass

