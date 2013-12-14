#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import os

import json
import logging
from cgi import escape
from concurrent.futures import ThreadPoolExecutor

from tornado import web, httpserver, ioloop, log
from tornado.httpclient import AsyncHTTPClient

import tornado.options
from tornado.options import define, options

from jinja2 import Environment, FileSystemLoader

from IPython.config import Config
from IPython.nbconvert.exporters import HTMLExporter
from IPython.nbconvert.filters import markdown2html

from .handlers import handlers
from .cache import DummyAsyncCache, AsyncMultipartMemcache, pylibmc
try:
    from .client import LoggingCurlAsyncHTTPClient as HTTPClientClass
except ImportError:
    from .client import LoggingSimpleAsyncHTTPClient as HTTPClientClass
from .github import AsyncGitHubClient
from .utils import git_info

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------
access_log = log.access_log
app_log = log.app_log

here = os.path.dirname(__file__)
pjoin = os.path.join

def nrhead():
    try:
        import newrelic.agent
    except ImportError:
        return ''
    return newrelic.agent.get_browser_timing_header()

def nrfoot():
    try:
        import newrelic.agent
    except ImportError:
        return ''
    return newrelic.agent.get_browser_timing_footer()

def log_request(handler):
    """log a bit more information about each request than tornado's default
    
    - move static file get success to debug-level (reduces noise)
    - get proxied IP instead of proxy IP
    - log referer for redirect and failed requests
    - log user-agent for failed requests
    """
    status = handler.get_status()
    request = handler.request
    if status < 300 or status == 304 and isinstance(handler, web.StaticFileHandler):
        # static-file get successes (or 304 FOUND) are debug-level
        log_method = access_log.debug
    elif status < 400:
        log_method = access_log.info
    elif status < 500:
        log_method = access_log.warning
    else:
        log_method = access_log.error
    
    # If behind a proxy, get the true requester's address
    if 'X-Forwarded-For' in request.headers:
        remote_ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
    else:
        remote_ip = request.remote_ip
    request_time = 1000.0 * handler.request.request_time()
    ns = dict(
        status=status,
        method=request.method,
        ip=remote_ip,
        uri=request.uri,
        request_time=request_time,
    )
    msg = "{status} {method} {uri} ({ip}) {request_time:.2f}ms"
    if status >= 300:
        # log referers on redirects
        ns['referer'] = request.headers.get('Referer', '')
        msg = msg + ' referer={referer}'
    if status >= 400:
        # log user agent for failed requests
        ns['agent'] = request.headers.get('User-Agent', 'unknown')
        msg = msg + ' user-agent={agent}'
        # log all headers for failed requests (temporary)
        log_method(json.dumps(request.headers, indent=2))
    log_method(msg.format(**ns))

def main():
    # command-line options
    define("debug", default=False, help="run in debug mode", type=bool)
    define("port", default=5000, help="run on the given port", type=int)
    define("cache_expiry_min", default=10*60, help="minimum cache expiry (seconds)", type=int)
    define("cache_expiry_max", default=2*60*60, help="maximum cache expiry (seconds)", type=int)
    define("mc_threads", default=1, help="number of threads to use for Async Memcache", type=int)
    define("threads", default=1, help="number of threads to use for background IO", type=int)
    tornado.options.parse_command_line()
    
    # NBConvert config
    config = Config()
    config.HTMLExporter.template_file = 'basic'
    config.NbconvertApp.fileext = 'html'
    config.CSSHTMLHeaderTransformer.enabled = False
    # don't strip the files prefix - we use it for redirects
    # config.Exporter.filters = {'strip_files_prefix': lambda s: s}
    
    exporter = HTMLExporter(config=config, log=log.app_log)
    
    # DEBUG env implies both autoreload and log-level
    if os.environ.get("DEBUG"):
        options.debug = True
        logging.getLogger().setLevel(logging.DEBUG)
    
    # setup memcache
    mc_pool = ThreadPoolExecutor(options.mc_threads)
    pool = ThreadPoolExecutor(options.threads)
    memcache_urls = os.environ.get('MEMCACHIER_SERVERS',
        os.environ.get('MEMCACHE_SERVERS')
    )
    if pylibmc and memcache_urls:
        kwargs = dict(pool=mc_pool)
        username = os.environ.get('MEMCACHIER_USERNAME', '')
        password = os.environ.get('MEMCACHIER_PASSWORD', '')
        if username and password:
            kwargs['binary'] = True
            kwargs['username'] = username
            kwargs['password'] = password
            log.app_log.info("Using SASL memcache")
        else:
            log.app_log.info("Using plain memecache")
        
        cache = AsyncMultipartMemcache(memcache_urls.split(','), **kwargs)
    else:
        log.app_log.info("Using in-memory cache")
        cache = DummyAsyncCache()
    
    # setup tornado handlers and settings
    
    template_path = pjoin(here, 'templates')
    static_path = pjoin(here, 'static')
    env = Environment(loader=FileSystemLoader(template_path))
    env.filters['markdown'] = markdown2html
    try:
        git_data = git_info(here)
    except Exception as e:
        app_log.error("Failed to get git info: %s", e)
        git_data = {}
    else:
        git_data['msg'] = escape(git_data['msg'])
    env.globals.update(nrhead=nrhead, nrfoot=nrfoot, git_data=git_data)
    AsyncHTTPClient.configure(HTTPClientClass)
    client = AsyncHTTPClient()
    github_client = AsyncGitHubClient(client)
    github_client.authenticate()
    
    settings = dict(
        log_function=log_request,
        jinja2_env=env,
        static_path=static_path,
        client=client,
        github_client=github_client,
        exporter=exporter,
        cache=cache,
        cache_expiry_min=options.cache_expiry_min,
        cache_expiry_max=options.cache_expiry_max,
        pool=pool,
        render_timeout=20,
    )
    
    # create and start the app
    app = web.Application(handlers, debug=options.debug, **settings)
    http_server = httpserver.HTTPServer(app)
    log.app_log.info("Listening on port %i", options.port)
    http_server.listen(options.port)
    ioloop.IOLoop.instance().start()
    

if __name__ == '__main__':
    main()
