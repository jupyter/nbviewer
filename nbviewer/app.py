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


# https://docs.python.org/3/library/cgi.html#cgi.escape
# Deprecated since version 3.2: This function is unsafe because quote is
# false by default, and therefore deprecated. Use html.escape() instead.
try:
    from html import escape
except ImportError:
    from cgi import escape

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from tornado import web, httpserver, ioloop, log
from tornado.httpclient import AsyncHTTPClient

import tornado.options
from tornado.options import define, options

from jinja2 import Environment, FileSystemLoader

from traitlets.config import Config

from .handlers import init_handlers, format_handlers
from .cache import DummyAsyncCache, AsyncMultipartMemcache, MockCache, pylibmc
from .index import NoSearch, ElasticSearch
from .formats import configure_formats

from .providers import default_providers, default_rewrites
from .providers.local import LocalFileHandler

try:
    from .providers.url.client import NBViewerCurlAsyncHTTPClient as HTTPClientClass
except ImportError:
    from .providers.url.client import NBViewerSimpleAsyncHTTPClient as HTTPClientClass


from .log import log_request
from .utils import git_info, jupyter_info, url_path_join

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


def make_app():
    # NBConvert config
    config = Config()
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

    # setup formats
    formats = configure_formats(options, config, log.app_log)

    if options.processes:
        pool = ProcessPoolExecutor(options.processes)
    else:
        pool = ThreadPoolExecutor(options.threads)

    memcache_urls = os.environ.get('MEMCACHIER_SERVERS',
        os.environ.get('MEMCACHE_SERVERS')
    )

    # Handle linked Docker containers
    if(os.environ.get('NBCACHE_PORT')):
        tcp_memcache = os.environ.get('NBCACHE_PORT')
        memcache_urls = tcp_memcache.split('tcp://')[1]

    if(os.environ.get('NBINDEX_PORT')):
        log.app_log.info("Indexing notebooks")
        tcp_index = os.environ.get('NBINDEX_PORT')
        index_url = tcp_index.split('tcp://')[1]
        index_host, index_port = index_url.split(":")
        indexer = ElasticSearch(index_host, index_port)
    else:
        log.app_log.info("Not indexing notebooks")
        indexer = NoSearch()

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

    template_paths = pjoin(here, 'templates')

    if options.template_path is not None:
        log.app_log.info("Using custom template path {}".format(
            options.template_path)
        )
        template_paths = [options.template_path, template_paths]

    static_path = pjoin(here, 'static')
    env = Environment(
        loader=FileSystemLoader(template_paths),
        autoescape=True
    )
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
        jupyter_info=jupyter_info(), len=len,
    )
    AsyncHTTPClient.configure(HTTPClientClass)
    client = AsyncHTTPClient()
    client.cache = cache

    # load frontpage sections
    with io.open(options.frontpage, 'r') as f:
        frontpage_sections = json.load(f)

    # cache frontpage links for the maximum allowed time
    max_cache_uris = {''}
    for section in frontpage_sections:
        for link in section['links']:
            max_cache_uris.add('/' + link['target'])

    fetch_kwargs = dict(connect_timeout=10,)
    if options.proxy_host:
        fetch_kwargs.update(dict(proxy_host=options.proxy_host,
                                 proxy_port=options.proxy_port))

        log.app_log.info("Using web proxy {proxy_host}:{proxy_port}."
                         "".format(**fetch_kwargs))

    if options.no_check_certificate:
        fetch_kwargs.update(dict(validate_cert=False))

        log.app_log.info("Not validating SSL certificates")

    settings = dict(
        log_function=log_request,
        jinja2_env=env,
        static_path=static_path,
        static_url_prefix=url_path_join(options.base_url, '/static/'),
        client=client,
        formats=formats,
        default_format=options.default_format,
        providers=options.providers,
        provider_rewrites=options.provider_rewrites,
        config=config,
        index=indexer,
        cache=cache,
        cache_expiry_min=options.cache_expiry_min,
        cache_expiry_max=options.cache_expiry_max,
        max_cache_uris=max_cache_uris,
        frontpage_sections=frontpage_sections,
        pool=pool,
        gzip=True,
        render_timeout=options.render_timeout,
        localfile_path=os.path.abspath(options.localfiles),
        fetch_kwargs=fetch_kwargs,
        mathjax_url=options.mathjax_url,
        statsd_host=options.statsd_host,
        statsd_port=options.statsd_port,
        statsd_prefix=options.statsd_prefix,
        base_url=options.base_url,
        hub_api_token=os.getenv('JUPYTERHUB_API_TOKEN'),
        hub_api_url=os.getenv('JUPYTERHUB_API_URL'),
    )

    # handle handlers
    handlers = init_handlers(formats, options.providers, options.base_url)

    if options.localfiles:
        log.app_log.warning("Serving local notebooks in %s, this can be a security risk", options.localfiles)
        # use absolute or relative paths:
        local_handlers = [( url_path_join(options.base_url, r'/localfile/?(.*)'), LocalFileHandler)]
        handlers = (
            local_handlers +
            format_handlers(formats, local_handlers) +
            handlers
        )

    # create the app
    return web.Application(handlers, debug=options.debug, **settings)


def init_options():
    # command-line options
    if 'port' in options:
        # already run
        return

    define("debug", default=False, help="run in debug mode", type=bool)
    define("no_cache", default=False, help="Do not cache results", type=bool)
    define("localfiles", default="", help="Allow to serve local files under /localfile/* this can be a security risk", type=str)
    define("port", default=5000, help="run on the given port", type=int)
    define("cache_expiry_min", default=10*60, help="minimum cache expiry (seconds)", type=int)
    define("cache_expiry_max", default=2*60*60, help="maximum cache expiry (seconds)", type=int)
    define("render_timeout", default=15, help="Time to wait for a render to complete before showing the 'Working...' page.", type=int)
    define("mc_threads", default=1, help="number of threads to use for Async Memcache", type=int)
    define("threads", default=1, help="number of threads to use for rendering", type=int)
    define("processes", default=0, help="use processes instead of threads for rendering", type=int)
    define("frontpage", default=FRONTPAGE_JSON, help="path to json file containing frontpage content", type=str)
    define("sslcert", help="path to ssl .crt file", type=str)
    define("sslkey", help="path to ssl .key file", type=str)
    define("no_check_certificate", default=False, help="Do not validate SSL certificates", type=bool)
    define("default_format", default="html", help="format to use for legacy / URLs", type=str)
    define("proxy_host", default="", help="The proxy URL.", type=str)
    define("proxy_port", default="", help="The proxy port.", type=int)
    define("providers", default=default_providers, help="Full dotted package(s) that provide `default_handlers`", type=str, multiple=True, group="provider")
    define("provider_rewrites", default=default_rewrites, help="Full dotted package(s) that provide `uri_rewrites`", type=str, multiple=True, group="provider")
    define("mathjax_url", default="https://cdn.mathjax.org/mathjax/latest/", help="URL base for mathjax package", type=str)
    define("template_path", default=os.environ.get("NBVIEWER_TEMPLATE_PATH", None), help="Custom template path for the nbviewer app (not rendered notebooks)", type=str)
    define("statsd_host", default="", help="Host running statsd to send metrics to", type=str)
    define("statsd_port", default=8125, help="Port on which statsd is listening for metrics on statsd_host", type=int)
    define("statsd_prefix", default='nbviewer', help="Prefix to use for naming metrics sent to statsd", type=str)
    define("base_url", default=os.getenv('JUPYTERHUB_SERVICE_PREFIX', '/'), help='URL base for the server')


def main(argv=None):
    init_options()
    tornado.options.parse_command_line(argv)

    # create and start the app
    app = make_app()

    # load ssl options
    ssl_options = None
    if options.sslcert:
        ssl_options = {
            'certfile' : options.sslcert,
            'keyfile' : options.sslkey,
        }

    http_server = httpserver.HTTPServer(app, xheaders=True, ssl_options=ssl_options)
    log.app_log.info("Listening on port %i, path %s", options.port, options.base_url)
    http_server.listen(options.port)
    ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
