#-----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
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

from tornado import web, httpserver, ioloop
from tornado.log import access_log, app_log, LogFormatter
from tornado.curl_httpclient import curl_log

import tornado.options
from tornado.options import define, options

from jinja2 import Environment, FileSystemLoader

from traitlets import Any, Bool, Dict, Int, List, Set, Unicode, default
from traitlets.config import Application

from .handlers import init_handlers
from .cache import DummyAsyncCache, AsyncMultipartMemcache, MockCache, pylibmc
from .index import NoSearch
from .formats import default_formats
from nbconvert.exporters.export import exporter_map

from .providers import default_providers, default_rewrites
from .client import NBViewerAsyncHTTPClient as HTTPClientClass
from .ratelimit import RateLimiter

from .log import log_request
from .utils import git_info, jupyter_info, url_path_join

try: # Python 3.8
    from functools import cached_property
except ImportError:
    from .utils import cached_property

from jupyter_server.base.handlers import FileFindHandler as StaticFileHandler

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

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

    aliases = Dict({
        'base-url' : 'NBViewer.base_url',
        'binder-base-url' : 'NBViewer.binder_base_url',
        'cache-expiry-max' : 'NBViewer.cache_expiry_max',
        'cache-expiry-min' : 'NBViewer.cache_expiry_min',
        'config-file' : 'NBViewer.config_file',
        'content-security-policy' : 'NBViewer.content_security_policy',
        'default-format' : 'NBViewer.default_format',
        'frontpage' : 'NBViewer.frontpage',
        'host' : 'NBViewer.host',
        'ipywidgets-base-url' : 'NBViewer.ipywidgets_base_url',
        'jupyter-js-widgets-version' : 'NBViewer.jupyter_js_widgets_version',
        'jupyter-widgets-html-manager-version' : 'NBViewer.jupyter_widgets_html_manager_version',
        'localfiles' : 'NBViewer.localfiles',
        'log-level' : 'Application.log_level',
        'mathjax-url' : 'NBViewer.mathjax_url',
        'mc-threads' : 'NBViewer.mc_threads',
        'port' : 'NBViewer.port',
        'processes' : 'NBViewer.processes',
        'provider-rewrites' : 'NBViewer.provider_rewrites',
        'providers' : 'NBViewer.providers',
        'proxy-host' : 'NBViewer.proxy_host',
        'proxy-port' : 'NBViewer.proxy_port',
        'rate-limit' : 'NBViewer.rate_limit',
        'rate-limit-interval' : 'NBViewer.rate_limit_interval',
        'render-timeout' : 'NBViewer.render_timeout',
        'sslcert' : 'NBViewer.sslcert',
        'sslkey' : 'NBViewer.sslkey',
        'static-path' : 'NBViewer.static_path',
        'static-url-prefix' : 'NBViewer.static_url_prefix',
        'statsd-host' : 'NBViewer.statsd_host',
        'statsd-port' : 'NBViewer.statsd_port',
        'statsd-prefix' : 'NBViewer.statsd_prefix',
        'template-path' : 'NBViewer.template_path',
        'threads' : 'NBViewer.threads',
    })

    flags = Dict({
        'debug' : (
            {'Application' : {'log_level' : logging.DEBUG}},
            "Set log-level to debug, for the most verbose logging."
    ),
    })

    # Use this to insert custom configuration of handlers for NBViewer extensions
    handler_settings = Dict().tag(config=True)

    create_handler      = Unicode(default_value="nbviewer.handlers.CreateHandler",                      help="The Tornado handler to use for creation via frontpage form.").tag(config=True)
    custom404_handler   = Unicode(default_value="nbviewer.handlers.Custom404",                          help="The Tornado handler to use for rendering 404 templates.").tag(config=True)
    faq_handler         = Unicode(default_value="nbviewer.handlers.FAQHandler",                         help="The Tornado handler to use for rendering and viewing the FAQ section.").tag(config=True)
    gist_handler        = Unicode(default_value="nbviewer.providers.gist.handlers.GistHandler",         help="The Tornado handler to use for viewing notebooks stored as GitHub Gists").tag(config=True)
    github_blob_handler = Unicode(default_value="nbviewer.providers.github.handlers.GitHubBlobHandler", help="The Tornado handler to use for viewing notebooks stored as blobs on GitHub").tag(config=True)
    github_tree_handler = Unicode(default_value="nbviewer.providers.github.handlers.GitHubTreeHandler", help="The Tornado handler to use for viewing directory trees on GitHub").tag(config=True)
    github_user_handler = Unicode(default_value="nbviewer.providers.github.handlers.GitHubUserHandler", help="The Tornado handler to use for viewing all of a user's repositories on GitHub.").tag(config=True)
    index_handler       = Unicode(default_value="nbviewer.handlers.IndexHandler",                       help="The Tornado handler to use for rendering the frontpage section.").tag(config=True)
    local_handler       = Unicode(default_value="nbviewer.providers.local.handlers.LocalFileHandler",   help="The Tornado handler to use for viewing notebooks found on a local filesystem").tag(config=True)
    url_handler         = Unicode(default_value="nbviewer.providers.url.handlers.URLHandler",           help="The Tornado handler to use for viewing notebooks accessed via URL").tag(config=True)
    user_gists_handler  = Unicode(default_value="nbviewer.providers.gist.handlers.UserGistsHandler",    help="The Tornado handler to use for viewing directory containing all of a user's Gists").tag(config=True)

    client = Any().tag(config=True)
    @default('client')
    def _default_client(self):
        client = HTTPClientClass(log=self.log)
        client.cache = self.cache
        return client

    index = Any().tag(config=True)
    @default('index')
    def _load_index(self):
        if os.environ.get('NBINDEX_PORT'):
            self.log.info("Indexing notebooks")
            tcp_index = os.environ.get('NBINDEX_PORT')
            index_url = tcp_index.split('tcp://')[1]
            index_host, index_port = index_url.split(":")
        else:
            self.log.info("Not indexing notebooks")
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

    processes = Int(default_value=0, help="use processes instead of threads for rendering").tag(config=True)

    static_path = Unicode(default_value=os.environ.get("NBVIEWER_STATIC_PATH", ""), help="Custom path for loading additional static files.").tag(config=True)

    static_url_prefix = Unicode(default_value='/static/').tag(config=True)
    # Not exposed to end user for configuration, since needs to access base_url
    _static_url_prefix = Unicode()
    @default('_static_url_prefix')
    def _load_static_url_prefix(self):
        # Last '/' ensures that NBViewer still works regardless of whether user chooses e.g. '/static2/' or '/static2' as their custom prefix
        return url_path_join(self._base_url, self.static_url_prefix, '/')

    # prefer the JupyterHub defined service prefix over the CLI
    @cached_property
    def _base_url(self):
        return os.getenv("JUPYTERHUB_SERVICE_PREFIX", options.base_url)

    @cached_property
    def cache(self):
        memcache_urls = os.environ.get('MEMCACHIER_SERVERS', os.environ.get('MEMCACHE_SERVERS'))
        # Handle linked Docker containers
        if os.environ.get('NBCACHE_PORT'):
            tcp_memcache = os.environ.get('NBCACHE_PORT')
            memcache_urls = tcp_memcache.split('tcp://')[1]
        if options.no_cache:
            self.log.info("Not using cache")
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
                self.log.info("Using SASL memcache")
            else:
                self.log.info("Using plain memcache")

            cache = AsyncMultipartMemcache(memcache_urls.split(','), **kwargs)
        else:
            self.log.info("Using in-memory cache")
            cache = DummyAsyncCache()

        return cache

    @cached_property
    def env(self):
        env = Environment(loader=FileSystemLoader(self.template_paths), autoescape=True)
        env.filters['markdown'] = markdown.markdown
        try:
            git_data = git_info(here)
        except Exception as e:
            self.log.error("Failed to get git info: %s", e)
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
            self.log.info("Using web proxy {proxy_host}:{proxy_port}."
                             "".format(**fetch_kwargs))
        
        if options.no_check_certificate:
            fetch_kwargs.update(validate_cert=False)
            self.log.info("Not validating SSL certificates")

        return fetch_kwargs

    @cached_property
    def formats(self):
        return self.configure_formats()

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

    # Attribute inherited from traitlets.config.Application, automatically used to style logs
    # https://github.com/ipython/traitlets/blob/master/traitlets/config/application.py#L191
    _log_formatter_cls = LogFormatter
    # Need Tornado LogFormatter for color logs, keys 'color' and 'end_color' in log_format

    # Observed traitlet inherited again from traitlets.config.Application
    # https://github.com/ipython/traitlets/blob/master/traitlets/config/application.py#L177
    @default('log_level')
    def _log_level_default(self):
        return logging.INFO

    # Ditto the above: https://github.com/ipython/traitlets/blob/master/traitlets/config/application.py#L197
    @default('log_format')
    def _log_format_default(self):
        """override default log format to include time and color, plus to always display the log level, not just when it's high"""
        return "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s %(module)s:%(lineno)d]%(end_color)s %(message)s"

    # For consistency with JupyterHub logs
    @default('log_datefmt')
    def _log_datefmt_default(self):
        """Exclude date from default date format"""
        return "%Y-%m-%d %H:%M:%S"

    @cached_property
    def pool(self):
        if self.processes:
            pool = ProcessPoolExecutor(self.processes)
        else:
            pool = ThreadPoolExecutor(options.threads)
        return pool

    @cached_property
    def rate_limiter(self):
        rate_limiter = RateLimiter(limit=options.rate_limit, interval=options.rate_limit_interval, cache=self.cache)
        return rate_limiter

    @cached_property
    def static_paths(self):
        default_static_path = pjoin(here, 'static')
        if self.static_path:
            self.log.info("Using custom static path {}".format(self.static_path))
            static_paths = [self.static_path, default_static_path]
        else:
            static_paths = [default_static_path]

        return static_paths

    @cached_property
    def template_paths(self):
        default_template_path = pjoin(here, 'templates')
        if options.template_path is not None:
            self.log.info("Using custom template path {}".format(options.template_path))
            template_paths = [options.template_path, default_template_path]
        else:
            template_paths = [default_template_path]

        return template_paths

    def configure_formats(self, formats=None):
        """
        Format-specific configuration.
        """
        if formats is None:
            formats = default_formats()

        # This would be better defined in a class
        self.config.HTMLExporter.template_file = 'basic'
        self.config.SlidesExporter.template_file = 'slides_reveal'

        self.config.TemplateExporter.template_path = [
            os.path.join(os.path.dirname(__file__), "templates", "nbconvert")
        ]

        for key, format in formats.items():
            exporter_cls = format.get("exporter", exporter_map[key])
            if self.processes:
                # can't pickle exporter instances,
                formats[key]["exporter"] = exporter_cls
            else:
                formats[key]["exporter"] = exporter_cls(config=self.config, log=self.log)
    
        return formats

    def init_tornado_application(self):
        # handle handlers
        handler_names = dict(
                  create_handler=self.create_handler,
                  custom404_handler=self.custom404_handler,
                  faq_handler=self.faq_handler,
                  gist_handler=self.gist_handler,
                  github_blob_handler=self.github_blob_handler,
                  github_tree_handler=self.github_tree_handler,
                  github_user_handler=self.github_user_handler,
                  index_handler=self.index_handler,
                  local_handler=self.local_handler,
                  url_handler=self.url_handler,
                  user_gists_handler=self.user_gists_handler,
        )
        handler_kwargs = {'handler_names' : handler_names, 'handler_settings' : self.handler_settings}
        handlers = init_handlers(self.formats, options.providers, self._base_url, options.localfiles, **handler_kwargs)
        
        # NBConvert config
        self.config.NbconvertApp.fileext = 'html'
        self.config.CSSHTMLHeaderTransformer.enabled = False

        # DEBUG env implies both autoreload and log-level
        if os.environ.get("DEBUG"):
            self.log.setLevel(logging.DEBUG)
   
        # input traitlets to settings
        settings = dict(
                  # Allow FileFindHandler to load static directories from e.g. a Docker container
                  allow_remote_access=True,
                  base_url=self._base_url,
                  binder_base_url=options.binder_base_url,
                  cache=self.cache,
                  cache_expiry_max=options.cache_expiry_max,
                  cache_expiry_min=options.cache_expiry_min,
                  client=self.client,
                  config=self.config,
                  content_security_policy=options.content_security_policy,
                  default_format=options.default_format,
                  fetch_kwargs=self.fetch_kwargs,
                  formats=self.formats,
                  frontpage_setup=self.frontpage_setup,
                  google_analytics_id=os.getenv('GOOGLE_ANALYTICS_ID'),
                  gzip=True,
                  hub_api_token=os.getenv('JUPYTERHUB_API_TOKEN'),
                  hub_api_url=os.getenv('JUPYTERHUB_API_URL'),
                  hub_base_url=os.getenv('JUPYTERHUB_BASE_URL'),
                  index=self.index,
                  ipywidgets_base_url=options.ipywidgets_base_url,
                  jinja2_env=self.env,
                  jupyter_js_widgets_version=options.jupyter_js_widgets_version,
                  jupyter_widgets_html_manager_version=options.jupyter_widgets_html_manager_version,
                  localfile_any_user=options.localfile_any_user,
                  localfile_follow_symlinks=options.localfile_follow_symlinks,
                  localfile_path=os.path.abspath(options.localfiles),
                  log=self.log,
                  log_function=log_request,
                  mathjax_url=options.mathjax_url,
                  max_cache_uris=self.max_cache_uris,
                  pool=self.pool,
                  provider_rewrites=options.provider_rewrites,
                  providers=options.providers,
                  rate_limiter=self.rate_limiter,
                  render_timeout=options.render_timeout,
                  static_handler_class = StaticFileHandler,
                  # FileFindHandler expects list of static paths, so self.static_path*s* is correct
                  static_path=self.static_paths,
                  static_url_prefix=self._static_url_prefix,
                  statsd_host=options.statsd_host,
                  statsd_port=options.statsd_port,
                  statsd_prefix=options.statsd_prefix,
        )

        if options.localfiles:
            self.log.warning("Serving local notebooks in %s, this can be a security risk", options.localfiles)
        
        # create the app
        self.tornado_application = web.Application(handlers, **settings)

    def init_logging(self):

        # Note that we inherit a self.log attribute from traitlets.config.Application
        # https://github.com/ipython/traitlets/blob/master/traitlets/config/application.py#L209
        # as well as a log_level attribute
        # https://github.com/ipython/traitlets/blob/master/traitlets/config/application.py#L177

        # This prevents double log messages because tornado use a root logger that
        # self.log is a child of. The logging module dispatches log messages to a log
        # and all of its ancestors until propagate is set to False
        self.log.propagate = False

        tornado_log = logging.getLogger('tornado')
        # hook up tornado's loggers to our app handlers
        for log in (app_log, access_log, tornado_log, curl_log):
            # ensure all log statements identify the application they come from
            log.name = self.log.name
            log.parent = self.log
            log.propagate = True
            log.setLevel(self.log_level)

        # disable curl debug, which logs all headers, info for upstream requests, which is TOO MUCH
        curl_log.setLevel(
            max(self.log_level, logging.INFO))

    # Mostly copied from JupyterHub because if it isn't broken then don't fix it
    def write_config_file(self):
        """Write our default config to a .py config file"""
        config_file_dir = os.path.dirname(os.path.abspath(options.config_file))
        if not os.path.isdir(config_file_dir):
            self.exit("{} does not exist. The destination directory must exist before generating config file.".format(config_file_dir))
        if os.path.exists(options.config_file) and not options.answer_yes:
            answer = ''

            def ask():
                prompt = "Overwrite %s with default config? [y/N]" % options.config_file
                try:
                    return input(prompt).lower() or 'n'
                except KeyboardInterrupt:
                    print('')  # empty line
                    return 'n'

            answer = ask()
            while not answer.startswith(('y', 'n')):
                print("Please answer 'yes' or 'no'")
                answer = ask()
            if answer.startswith('n'):
                self.exit("Not overwriting config file with default.")

        # Inherited method from traitlets.Application
        config_text = self.generate_config_file()
        if isinstance(config_text, bytes):
            config_text = config_text.decode('utf8')
        print("Writing default config to: %s" % options.config_file)
        with open(options.config_file, mode='w') as f:
            f.write(config_text)
        self.exit("Wrote default config file.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if options.generate_config:
            self.write_config_file()

        # Inherited method from traitlets.Application
        self.load_config_file(options.config_file)
        self.init_logging()
        self.init_tornado_application()

def init_options():
    # command-line options
    if 'port' in options:
        # already run
        return

    # Make this a cached property of NBViewer during traitlets refactor
    def default_endpoint():
        # check if JupyterHub service options are available to use as defaults
        if 'JUPYTERHUB_SERVICE_URL' in os.environ:
            url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])
            default_host, default_port = url.hostname, url.port
        else:
            default_host, default_port = '0.0.0.0', 5000
        return {'host': default_host, 'port': default_port}

    define("answer_yes", default=False, help="Answer yes to any questions (e.g. confirm overwrite).", type=bool)
    define("base_url", default='/', help='URL base for the server')
    define("binder_base_url", default="https://mybinder.org/v2", help="URL base for binder notebook execution service", type=str)
    define("cache_expiry_max", default=2*60*60, help="maximum cache expiry (seconds)", type=int)
    define("cache_expiry_min", default=10*60, help="minimum cache expiry (seconds)", type=int)
    define("config_file", default='nbviewer_config.py', help="The config file to load", type=str)
    define("content_security_policy", default="connect-src 'none';", help="Content-Security-Policy header setting", type=str)
#    define("debug", default=False, help="run in debug mode", type=bool)
    define("default_format", default="html", help="format to use for legacy / URLs", type=str)
    define("frontpage", default=FRONTPAGE_JSON, help="path to json file containing frontpage content", type=str)
    define("generate_config", default=False, help="Generate default config file and then stop.", type=bool)
    define("host", default=default_endpoint()['host'], help="run on the given interface", type=str)
    define("ipywidgets_base_url", default="https://unpkg.com/", help="URL base for ipywidgets JS package", type=str)
    define("jupyter_js_widgets_version", default="*", help="Version specifier for jupyter-js-widgets JS package", type=str)
    define("jupyter_widgets_html_manager_version", default="*", help="Version specifier for @jupyter-widgets/html-manager JS package", type=str)
    define("localfile_any_user", default=False, help="Also serve files that are not readable by 'Other' on the local file system", type=bool)
    define("localfile_follow_symlinks", default=False, help="Resolve/follow symbolic links to their target file using realpath", type=bool)
    define("localfiles", default="", help="Allow to serve local files under /localfile/* this can be a security risk", type=str)
    define("mathjax_url", default="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.1/", help="URL base for mathjax package", type=str)
    define("mc_threads", default=1, help="number of threads to use for Async Memcache", type=int)
    define("no_cache", default=False, help="Do not cache results", type=bool)
    define("no_check_certificate", default=False, help="Do not validate SSL certificates", type=bool)
    define("port", default=default_endpoint()['port'], help="run on the given port", type=int)
    define("provider_rewrites", default=default_rewrites, help="Full dotted package(s) that provide `uri_rewrites`", type=str, multiple=True, group="provider")
    define("providers", default=default_providers, help="Full dotted package(s) that provide `default_handlers`", type=str, multiple=True, group="provider")
    define("proxy_host", default="", help="The proxy URL.", type=str)
    define("proxy_port", default="", help="The proxy port.", type=int)
    define("rate_limit", default=60, help="Number of requests to allow in rate_limt_interval before limiting. Only requests that trigger a new render are counted.", type=int)
    define("rate_limit_interval", default=600, help="Interval (in seconds) for rate limiting.", type=int)
    define("render_timeout", default=15, help="Time to wait for a render to complete before showing the 'Working...' page.", type=int)
    define("sslcert", help="path to ssl .crt file", type=str)
    define("sslkey", help="path to ssl .key file", type=str)
    define("statsd_host", default="", help="Host running statsd to send metrics to", type=str)
    define("statsd_port", default=8125, help="Port on which statsd is listening for metrics on statsd_host", type=int)
    define("statsd_prefix", default='nbviewer', help="Prefix to use for naming metrics sent to statsd", type=str)
    define("template_path", default=os.environ.get("NBVIEWER_TEMPLATE_PATH", None), help="Custom template path for the nbviewer app (not rendered notebooks)", type=str)
    define("threads", default=1, help="number of threads to use for rendering", type=int)


def main(argv=None):
    init_options()
    tornado.options.parse_command_line(argv)
    
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
    nbviewer.log.info("Listening on %s:%i, path %s", options.host, options.port,
                     app.settings['base_url'])
    http_server.listen(options.port, options.host)
    ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
