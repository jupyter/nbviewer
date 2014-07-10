#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import json
import io
import os

import logging
import markdown

from cgi import escape
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

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
from .utils import git_info, ipython_info

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

this_dir, this_filename = os.path.split(__file__)
FRONTPAGE_JSON = os.path.join(this_dir, "frontpage.json")

def main():
    # command-line options
    define("debug", default=False, help="run in debug mode", type=bool)
    define("no_cache", default=False, help="Do not cache results", type=bool)
    define("localfiles", default="", help="Allow to serve local files under /localfile/* this can be a security risk", type=str)
    define("port", default=5000, help="run on the given port", type=int)
    define("cache_expiry_min", default=10*60, help="minimum cache expiry (seconds)", type=int)
    define("cache_expiry_max", default=2*60*60, help="maximum cache expiry (seconds)", type=int)
    define("mc_threads", default=1, help="number of threads to use for Async Memcache", type=int)
    define("threads", default=1, help="number of threads to use for rendering", type=int)
    define("processes", default=0, help="use processes instead of threads for rendering", type=int)
    define("frontpage", default=FRONTPAGE_JSON, help="path to json file containing frontpage content", type=str)
    define("sslcert", help="path to ssl .crt file", type=str)
    define("sslkey", help="path to ssl .key file", type=str)
    tornado.options.parse_command_line()
    
    # NBConvert config
    config = Config()
    config.HTMLExporter.template_file = 'basic'
    config.NbconvertApp.fileext = 'html'
    config.CSSHTMLHeaderTransformer.enabled = False
    # don't strip the files prefix - we use it for redirects
    # config.Exporter.filters = {'strip_files_prefix': lambda s: s}
    
    # DEBUG env implies both autoreload and log-level
    if os.environ.get("DEBUG"):
        options.debug = True
        logging.getLogger().setLevel(logging.DEBUG)
    
    # setup memcache
    mc_pool = ThreadPoolExecutor(options.mc_threads)
    if options.processes:
        # can't pickle exporter instances,
        exporter = HTMLExporter
        pool = ProcessPoolExecutor(options.processes)
    else:
        exporter = HTMLExporter(config=config, log=log.app_log)
        pool = ThreadPoolExecutor(options.threads)
        
    memcache_urls = os.environ.get('MEMCACHIER_SERVERS',
        os.environ.get('MEMCACHE_SERVERS')
    )
    if options.no_cache:
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


    if options.no_cache:
        # force jinja to recompile template every time
        env.globals.update(cache_size=0)
    env.globals.update(nrhead=nrhead, nrfoot=nrfoot, git_data=git_data,
        ipython_info=ipython_info(), len=len,
    )
    AsyncHTTPClient.configure(HTTPClientClass)
    client = AsyncHTTPClient()
    github_client = AsyncGitHubClient(client)
    
    # load frontpage sections
    with io.open(options.frontpage, 'r') as f:
        frontpage_sections = json.load(f)
    
    # cache frontpage links for the maximum allowed time
    max_cache_uris = {''}
    for section in frontpage_sections:
        for link in section['links']:
            max_cache_uris.add('/' + link['target'])

    settings = dict(
        log_function=log_request,
        jinja2_env=env,
        static_path=static_path,
        client=client,
        github_client=github_client,
        exporter=exporter,
        config=config,
        cache=cache,
        cache_expiry_min=options.cache_expiry_min,
        cache_expiry_max=options.cache_expiry_max,
        max_cache_uris=max_cache_uris,
        frontpage_sections=frontpage_sections,
        pool=pool,
        gzip=True,
        render_timeout=20,
        localfile_path=os.path.abspath(options.localfiles),
        fetch_kwargs=dict(
            connect_timeout=10,
        ),
    )
    
    # create and start the app
    if options.localfiles:
        log.app_log.warning("Serving local notebooks in %s, this can be a security risk", options.localfiles)
        # use absolute or relative paths:
        handlers.insert(0, (r'/localfile/(.*)', LocalFileHandler))

    # load ssl options
    ssl_options = None
    if options.sslcert:
        ssl_options = {
            'certfile' : options.sslcert,
            'keyfile' : options.sslkey,
        }

    app = web.Application(handlers, debug=options.debug, **settings)
    http_server = httpserver.HTTPServer(app, xheaders=True, ssl_options=ssl_options)
    log.app_log.info("Listening on port %i", options.port)
    http_server.listen(options.port)
    ioloop.IOLoop.instance().start()
    

if __name__ == '__main__':
    main()
