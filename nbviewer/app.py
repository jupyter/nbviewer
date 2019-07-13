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

from urllib.parse import urlparse
from html import escape

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from tornado import web, httpserver, ioloop, log
from tornado.httpclient import AsyncHTTPClient

import tornado.options
from tornado.options import define, options

from jinja2 import Environment, FileSystemLoader

from traitlets import Any, Dict, Set, Unicode, default
from traitlets.config import Application

from .handlers import init_handlers
from .cache import DummyAsyncCache, AsyncMultipartMemcache, MockCache, pylibmc
from .index import NoSearch, ElasticSearch
from .formats import configure_formats
from .providers import default_providers, default_rewrites

try:
    from .providers.url.client import NBViewerCurlAsyncHTTPClient as HTTPClientClass
except ImportError:
    from .providers.url.client import NBViewerSimpleAsyncHTTPClient as HTTPClientClass
from .ratelimit import RateLimiter

from .log import log_request
from .utils import git_info, jupyter_info, url_path_join

try: # Python 3.8
    from functools import cached_property
except ImportError:
    from .utils import cached_property

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

class NBViewer(Application):

    name = Unicode('nbviewer')

    config_file = Unicode('nbviewer_config.py', help="The config file to load").tag(config=True)

    # Use this to insert custom configuration of handlers for NBViewer extensions
    handler_settings = Dict().tag(config=True)

    url_handler         = Unicode(default_value="nbviewer.providers.url.handlers.URLHandler",           help="The Tornado handler to use for viewing notebooks accessed via URL").tag(config=True)
    local_handler       = Unicode(default_value="nbviewer.providers.local.handlers.LocalFileHandler",   help="The Tornado handler to use for viewing notebooks found on a local filesystem").tag(config=True)
    github_blob_handler = Unicode(default_value="nbviewer.providers.github.handlers.GitHubBlobHandler", help="The Tornado handler to use for viewing notebooks stored as blobs on GitHub").tag(config=True)
    github_tree_handler = Unicode(default_value="nbviewer.providers.github.handlers.GitHubTreeHandler", help="The Tornado handler to use for viewing directory trees on GitHub").tag(config=True)
    gist_handler        = Unicode(default_value="nbviewer.providers.gist.handlers.GistHandler",         help="The Tornado handler to use for viewing notebooks stored as GitHub Gists").tag(config=True)
    user_gists_handler  = Unicode(default_value="nbviewer.providers.gist.handlers.UserGistsHandler",    help="The Tornado handler to use for viewing directory containing all of a user's Gists").tag(config=True)

    index = Any().tag(config=True)
    @default('index')
    def _load_index(self):
        if os.environ.get('NBINDEX_PORT'):
            log.app_log.info("Indexing notebooks")
            tcp_index = os.environ.get('NBINDEX_PORT')
            index_url = tcp_index.split('tcp://')[1]
            index_host, index_port = index_url.split(":")
        else:
            log.app_log.info("Not indexing notebooks")
            indexer = NoSearch()
        return indexer

    # cache frontpage links for the maximum allowed time
    max_cache_uris = Set().tag(config=True)
    @default('max_cache_uris')
    def _load_max_cache_uris(self):
        max_cache_uris = {''}
        for section in self.frontpage_setup['sections']:
            for link in section['links']:
                max_cache_uris.add('/' + link['target'])
        return max_cache_uris

    static_path = Unicode(default_value=pjoin(here, 'static')).tag(config=True)

    static_url_prefix = Unicode().tag(config=True)
    @default('static_url_prefix')
    def _load_static_url_prefix(self):
        return url_path_join(self.base_url, '/static/')

    @cached_property
    def base_url(self):
        # prefer the JupyterHub defined service prefix over the CLI
        base_url = os.getenv("JUPYTERHUB_SERVICE_PREFIX", options.base_url)
        return base_url

    @cached_property
    def cache(self):
        memcache_urls = os.environ.get('MEMCACHIER_SERVERS', os.environ.get('MEMCACHE_SERVERS'))
        # Handle linked Docker containers
        if os.environ.get('NBCACHE_PORT'):
            tcp_memcache = os.environ.get('NBCACHE_PORT')
            memcache_urls = tcp_memcache.split('tcp://')[1]
        if options.no_cache:
            log.app_log.info("Not using cache")
            cache = MockCache()
        elif pylibmc and memcache_urls:
            # setup memcache
            mc_pool = ThreadPoolExecutor(options.mc_threads)
            kwargs = dict(pool=mc_pool)
            username = os.environ.get("MEMCACHIER_USERNAME", "")
            password = os.environ.get("MEMCACHIER_PASSWORD", "")
            if username and password:
                kwargs['binary'] = True
                kwargs['username'] = username
                kwargs['password'] = password
                log.app_log.info("Using SASL memcache")
            else:
                log.app_log.info("Using plain memcache")

            cache = AsyncMultipartMemcache(memcache_urls.split(','), **kwargs)
        else:
            log.app_log.info("Using in-memory cache")
            cache = DummyAsyncCache()

        return cache

    # for some reason this needs to be a computed property,
    # and not a traitlets Any(), otherwise nbviewer won't run
    @cached_property
    def client(self):
        AsyncHTTPClient.configure(HTTPClientClass)
        client = AsyncHTTPClient()
        client.cache = self.cache
        return client

    @cached_property
    def env(self):
        env = Environment(loader=FileSystemLoader(self.template_paths), autoescape=True)
        env.filters['markdown'] = markdown.markdown
        try:
            git_data = git_info(here)
        except Exception as e:
            app_log.error("Failed to get git info: %s", e)
            git_data = {}
        else:
            git_data['msg'] = escape(git_data['msg'])

        if options.no_cache:
            # force Jinja2 to recompile template every time
            env.globals.update(cache_size=0)
        env.globals.update(nrhead=nrhead, nrfoot=nrfoot, git_data=git_data, jupyter_info=jupyter_info(), len=len)

        return env

    @cached_property
    def fetch_kwargs(self):
        fetch_kwargs = dict(connect_timeout=10,)
        if options.proxy_host:
            fetch_kwargs.update(proxy_host=options.proxy_host, proxy_port=options.proxy_port)
            log.app_log.info("Using web proxy {proxy_host}:{proxy_port}."
                             "".format(**fetch_kwargs))
        
        if options.no_check_certificate:
            fetch_kwargs.update(validate_cert=False)
            log.app_log.info("Not validating SSL certificates")

        return fetch_kwargs

    @cached_property
    def formats(self):
        formats = configure_formats(options, self.config, log.app_log)
        return formats

    # load frontpage sections
    @cached_property
    def frontpage_setup(self):
        with io.open(options.frontpage, 'r') as f:
            frontpage_setup = json.load(f)
        # check if the JSON has a 'sections' field, otherwise assume it is just a list of sessions,
        # and provide the defaults of the other fields
        if 'sections' not in frontpage_setup:
            frontpage_setup = {
                              'title':'nbviewer', 'subtitle':'A simple way to share Jupyter notebooks',
                              'show_input':True, 'sections':frontpage_setup
                              }
        return frontpage_setup

    @cached_property
    def pool(self):
        if options.processes:
            pool = ProcessPoolExecutor(options.processes)
        else:
            pool = ThreadPoolExecutor(options.threads)
        return pool

    @cached_property
    def rate_limiter(self):
        rate_limiter = RateLimiter(limit=options.rate_limit, interval=options.rate_limit_interval, cache=self.cache)
        return rate_limiter

    @cached_property
    def template_paths(self):
        template_paths = pjoin(here, 'templates')
        if options.template_path is not None:
            log.app_log.info("Using custom template path {}".format(options.template_path))
            template_paths = [options.template_path, template_paths]

        return template_paths


    def init_tornado_application(self):
        # handle handlers
        handler_names = dict(
                  url_handler=self.url_handler,
                  github_blob_handler=self.github_blob_handler,
                  github_tree_handler=self.github_tree_handler,
                  local_handler=self.local_handler,
                  gist_handler=self.gist_handler,
                  user_gists_handler=self.user_gists_handler,
        )
        handler_kwargs = {'handler_names' : handler_names, 'handler_settings' : self.handler_settings}
        handlers = init_handlers(self.formats, options.providers, self.base_url, options.localfiles, **handler_kwargs)
        
        # NBConvert config
        self.config.NbconvertApp.fileext = 'html'
        self.config.CSSHTMLHeaderTransformer.enabled = False

        # DEBUG env implies both autoreload and log-level
        if os.environ.get("DEBUG"):
            options.debug = True
            logging.getLogger().setLevel(logging.DEBUG)
   
        # input traitlets to settings
        settings = dict(
                  config=self.config,
                  index=self.index,
                  max_cache_uris=self.max_cache_uris,
                  static_path=self.static_path,
                  static_url_prefix=self.static_url_prefix,
        )
        # input computed properties to settings
        settings.update(
                  base_url=self.base_url,
                  cache=self.cache,
                  client=self.client,
                  fetch_kwargs=self.fetch_kwargs,
                  formats=self.formats,
                  frontpage_setup=self.frontpage_setup,
                  jinja2_env=self.env,
                  pool=self.pool,
                  rate_limiter=self.rate_limiter,
        )
        # input settings from CLI options
        settings.update(
                  binder_base_url=options.binder_base_url,
                  cache_expiry_max=options.cache_expiry_max,
                  cache_expiry_min=options.cache_expiry_min,
                  content_security_policy=options.content_security_policy,
                  default_format=options.default_format,
                  ipywidgets_base_url=options.ipywidgets_base_url,
                  jupyter_js_widgets_version=options.jupyter_js_widgets_version,
                  jupyter_widgets_html_manager_version=options.jupyter_widgets_html_manager_version,
                  localfile_any_user=options.localfile_any_user,
                  localfile_follow_symlinks=options.localfile_follow_symlinks,
                  localfile_path=os.path.abspath(options.localfiles),
                  mathjax_url=options.mathjax_url,
                  provider_rewrites=options.provider_rewrites,
                  providers=options.providers,
                  render_timeout=options.render_timeout,
                  statsd_host=options.statsd_host,
                  statsd_port=options.statsd_port,
                  statsd_prefix=options.statsd_prefix,
        )
        # additional settings
        settings.update(
                  google_analytics_id=os.getenv('GOOGLE_ANALYTICS_ID'),
                  gzip=True,
                  hub_api_token=os.getenv('JUPYTERHUB_API_TOKEN'),
                  hub_api_url=os.getenv('JUPYTERHUB_API_URL'),
                  hub_base_url=os.getenv('JUPYTERHUB_BASE_URL'),
                  log_function=log_request,
        )

        if options.localfiles:
            log.app_log.warning("Serving local notebooks in %s, this can be a security risk", options.localfiles)
    
        # create the app
        self.tornado_application = web.Application(handlers, debug=options.debug, **settings)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_config_file(self.config_file)
        self.init_tornado_application()

def init_options():
    # command-line options
    if 'port' in options:
        # already run
        return

    # check if JupyterHub service options are available to use as defaults
    if 'JUPYTERHUB_SERVICE_URL' in os.environ:
        url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])
        default_host, default_port = url.hostname, url.port
    else:
        default_host, default_port = '0.0.0.0', 5000

    define("debug", default=False, help="run in debug mode", type=bool)
    define("no_cache", default=False, help="Do not cache results", type=bool)
    define("localfiles", default="", help="Allow to serve local files under /localfile/* this can be a security risk", type=str)
    define("localfile_follow_symlinks", default=False, help="Resolve/follow symbolic links to their target file using realpath", type=bool)
    define("localfile_any_user", default=False, help="Also serve files that are not readable by 'Other' on the local file system", type=bool)
    define("host", default=default_host, help="run on the given interface", type=str)
    define("port", default=default_port, help="run on the given port", type=int)
    define("cache_expiry_min", default=10*60, help="minimum cache expiry (seconds)", type=int)
    define("cache_expiry_max", default=2*60*60, help="maximum cache expiry (seconds)", type=int)
    define("render_timeout", default=15, help="Time to wait for a render to complete before showing the 'Working...' page.", type=int)
    define("rate_limit", default=60, help="Number of requests to allow in rate_limt_interval before limiting. Only requests that trigger a new render are counted.", type=int)
    define("rate_limit_interval", default=600, help="Interval (in seconds) for rate limiting.", type=int)
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
    define("mathjax_url", default="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.1/", help="URL base for mathjax package", type=str)
    define("template_path", default=os.environ.get("NBVIEWER_TEMPLATE_PATH", None), help="Custom template path for the nbviewer app (not rendered notebooks)", type=str)
    define("statsd_host", default="", help="Host running statsd to send metrics to", type=str)
    define("statsd_port", default=8125, help="Port on which statsd is listening for metrics on statsd_host", type=int)
    define("statsd_prefix", default='nbviewer', help="Prefix to use for naming metrics sent to statsd", type=str)
    define("base_url", default='/', help='URL base for the server')
    define("ipywidgets_base_url", default="https://unpkg.com/", help="URL base for ipywidgets JS package", type=str)
    define("jupyter_js_widgets_version", default="*", help="Version specifier for jupyter-js-widgets JS package", type=str)
    define("jupyter_widgets_html_manager_version", default="*", help="Version specifier for @jupyter-widgets/html-manager JS package", type=str)
    define("content_security_policy", default="connect-src 'none';", help="Content-Security-Policy header setting", type=str)
    define("binder_base_url", default="https://mybinder.org/v2", help="URL base for binder notebook execution service", type=str)


def main(argv=None):
    init_options()
    tornado.options.parse_command_line(argv)
    
    try:
        from tornado.curl_httpclient import curl_log
    except ImportError as e:
        log.app_log.warning("Failed to import curl: %s", e)
    else:
        # debug-level curl_log logs all headers, info for upstream requests,
        # which is just too much.
        curl_log.setLevel(max(log.app_log.getEffectiveLevel(), logging.INFO))
    

    # create and start the app
    nbviewer = NBViewer()
    app = nbviewer.tornado_application

    # load ssl options
    ssl_options = None
    if options.sslcert:
        ssl_options = {
            'certfile' : options.sslcert,
            'keyfile' : options.sslkey,
        }

    http_server = httpserver.HTTPServer(app, xheaders=True, ssl_options=ssl_options)
    log.app_log.info("Listening on %s:%i, path %s", options.host, options.port,
                     app.settings['base_url'])
    http_server.listen(options.port, options.host)
    ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
