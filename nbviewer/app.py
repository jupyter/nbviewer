#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import os

import logging
import markdown 

from cgi import escape
from concurrent.futures import ThreadPoolExecutor

from tornado import web, httpserver, ioloop, log
from tornado.httpclient import AsyncHTTPClient

import tornado.options
from tornado.options import define, options

from jinja2 import Environment, FileSystemLoader

from IPython.config import Config
from IPython.nbconvert.exporters import HTMLExporter

from .handlers import handlers, LocalFileHandler
from .cache import DummyAsyncCache, AsyncMultipartMemcache, MockCache, pylibmc
try:
    from .client import LoggingCurlAsyncHTTPClient as HTTPClientClass
except ImportError:
    from .client import LoggingSimpleAsyncHTTPClient as HTTPClientClass
from .github import AsyncGitHubClient
from .log import log_request
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

def main():
    # command-line options
    define("debug", default=False, help="run in debug mode", type=bool)
    define("no_cache", default=False, help="Do not cache results", type=bool)
    define("localfile", default=False, help="Allow to serve localfile under /localfile/* this can be a security risk", type=bool)
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
    if options.no_cache :
        log.app_log.info("Not using cache")
        cache = MockCache()
    elif pylibmc and memcache_urls:
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
    env.filters['markdown'] = markdown.markdown
    try:
        git_data = git_info(here)
    except Exception as e:
        app_log.error("Failed to get git info: %s", e)
        git_data = {}
    else:
        git_data['msg'] = escape(git_data['msg'])

    if options.no_cache :
        # force jinja to recompile template every time
        env.globals.update(cache_size=0)
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
        gzip=True,
        render_timeout=20,
    )
    
    # create and start the app
    if options.localfile:
        log.app_log.warning("Serving local files, this can be a security risk")
        handlers.insert(0, (r'/localfile/(.*)', LocalFileHandler))

    app = web.Application(handlers, debug=options.debug, **settings)
    http_server = httpserver.HTTPServer(app, xheaders=True)
    log.app_log.info("Listening on port %i", options.port)
    http_server.listen(options.port)
    ioloop.IOLoop.instance().start()
    

if __name__ == '__main__':
    main()
