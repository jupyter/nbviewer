#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import hashlib
import pickle
import socket
import time

from cgi import escape
from contextlib import contextmanager
from datetime import datetime

try:
    # py3
    from http.client import responses
    from urllib.parse import urlparse
except ImportError:
    from httplib import responses
    from urlparse import urlparse

from tornado import (
    gen,
    httpclient,
    web,
)
from tornado.escape import utf8
from tornado.ioloop import IOLoop
from tornado.log import app_log

from IPython.nbformat import (
    current_nbformat,
    reads,
)

from ..render import (
    NbFormatError,
    render_notebook,
)
from ..utils import parse_header_links

try:
    import pycurl
    from tornado.curl_httpclient import CurlError
except ImportError:
    pycurl = None

    class CurlError(Exception):
        pass

date_fmt = "%a, %d %b %Y %H:%M:%S UTC"
format_prefix = "/format/"
bundled_providers = [
    "dropbox",
    "gist",
    "github",
    "url",
]


class Provider(object):
    """The base class for all providers. This should be the target of your
       `entry_point` specification.
    """

    # context will be **merged into some templates
    context = {
        # convenience method `label` will try to access this
        'provider_label': 'Provider',
        # http://fortawesome.github.io/Font-Awesome/icons/, no `fa-` prefix
        'provider_icon': 'database',
        # for navigation links
        'collections_label': 'Collections',
    }

    @property
    def label(self):
        """Human-readable name for both logs and templates
        """
        return self.context['provider_label']

    def __init__(self, spec_name):
        """A new instance of a provider shouldn't really do much, as at this
           point it won't be certain to be enabled.

           spec_name will be read off the entry_point
        """
        self.spec_name = spec_name

    def enabled(self, options):
        """Return whether the provider is enabled.

           It would be ideal to always honor `with_<provider>`, but very simple
           providers may benefit from "short circuit" enabling with e.g. API
           key or file path
        """
        return options["with_{}".format(self.spec_name)]

    def initialize(self, options):
        """Run AFTER the provider is initialized, but BEFORE anything is done
           with it. Here, you could sanitize options, etc.
        """
        pass

    def options(self):
        """Generate the configuration options to be called with `define`,
           with default values to be used if not found in environment variables

           Make sure to call `super` to get the `with-<provider name>` option!

           The `options` object will be available to your handler classes.
        """
        return [
            dict(
                name="with_{}".format(self.spec_name),
                default=self.spec_name in bundled_providers,
                help="Enable/disable the {} provider".format(self.spec_name)
            )
        ]

    def handlers(self, handlers, options):
        """Given a list of tornado (url, class) handlers, return the list of
           handlers, suitably modified.
        """
        return handlers

    def uri_rewrites(self, rewrites, options):
        return rewrites

    # lower weight handlers/uri_rewrites will be called first
    handlers.weight = 0
    uri_rewrites.weight = 0


class BaseHandler(web.RequestHandler):
    """Base Handler class with common utilities"""

    def initialize(self, format=None, format_prefix=""):
        self.format = format or self.default_format
        self.format_prefix = format_prefix

    @property
    def pending(self):
        return self.settings.setdefault('pending', set())

    @property
    def formats(self):
        return self.settings['formats']

    @property
    def default_format(self):
        return self.settings['options'].default_format

    @property
    def config(self):
        return self.settings['config']

    @property
    def client(self):
        return self.settings['client']

    @property
    def index(self):
        return self.settings['index']

    @property
    def cache(self):
        return self.settings['cache']

    @property
    def cache_expiry_min(self):
        return self.settings['options'].cache_expiry_min

    @property
    def cache_expiry_max(self):
        return self.settings['options'].cache_expiry_max

    @property
    def pool(self):
        return self.settings['pool']

    @property
    def max_cache_uris(self):
        return self.settings.setdefault('max_cache_uris', set())

    @property
    def frontpage_sections(self):
        return self.settings.setdefault('frontpage_sections', {})

    @property
    def options(self):
        return self.settings['options']

    @property
    def providers(self):
        return self.settings['providers']

    #---------------------------------------------------------------
    # template rendering
    #---------------------------------------------------------------

    def get_template(self, name):
        """Return the jinja template object for a given name"""
        return self.settings['jinja2_env'].get_template(name)

    def render_template(self, name, **ns):
        ns.update(self.template_namespace)
        template = self.get_template(name)
        return template.render(**ns)

    @property
    def template_namespace(self):
        return {}

    def breadcrumbs(self, path, base_url):
        """Generate a list of breadcrumbs"""
        breadcrumbs = []
        if not path:
            return breadcrumbs
        for name in path.split('/'):
            href = base_url = "%s/%s" % (base_url, name)
            breadcrumbs.append({
                'url' : base_url,
                'name' : name,
            })
        return breadcrumbs

    def get_page_links(self, response):
        """return prev_url, next_url for pagination

        Response must be an HTTPResponse from a paginated GitHub API request.

        Each will be None if there no such link.
        """
        links = parse_header_links(response.headers.get('Link', ''))
        next_url = prev_url = None
        if 'next' in links:
            next_url = '?' + urlparse(links['next']['url']).query
        if 'prev' in links:
            prev_url = '?' + urlparse(links['prev']['url']).query
        return prev_url, next_url

    #---------------------------------------------------------------
    # error handling
    #---------------------------------------------------------------

    def client_error_message(self, exc, url, body, msg=None):
        """Turn the tornado HTTP error into something useful"""
        str_exc = str(exc)

        # strip the unhelpful 599 prefix
        if str_exc.startswith('HTTP 599: '):
            str_exc = str_exc[10:]

        if (msg is None) and body and len(body) < 100:
            # if it's a short plain-text error message, include it
            msg = "%s (%s)" % (str_exc, escape(body))

        return msg or str_exc

    def reraise_client_error(self, exc):
        """Remote fetch raised an error"""
        try:
            url = exc.response.request.url.split('?')[0]
            body = exc.response.body.decode('utf8', 'replace').strip()
        except AttributeError:
            url = 'url'
            body = ''

        msg = self.client_error_message(exc, url, body)

        slim_body = escape(body[:300])

        app_log.warn("Fetching %s failed with %s. Body=%s", url, msg, slim_body)
        if exc.code == 599:
            if isinstance(exc, CurlError):
                en = getattr(exc, 'errno', -1)
                # can't connect to server should be 404
                # possibly more here
                if en in (pycurl.E_COULDNT_CONNECT, pycurl.E_COULDNT_RESOLVE_HOST):
                    raise web.HTTPError(404, msg)
            # otherwise, raise 400 with informative message:
            raise web.HTTPError(400, msg)
        if exc.code >= 500:
            # 5XX, server error, but not this server
            raise web.HTTPError(502, msg)
        else:
            # client-side error, blame our client
            if exc.code == 404:
                raise web.HTTPError(404, "Remote %s" % msg)
            else:
                raise web.HTTPError(400, msg)

    @contextmanager
    def catch_client_error(self):
        """context manager for catching httpclient errors

        they are transformed into appropriate web.HTTPErrors
        """
        try:
            yield
        except httpclient.HTTPError as e:
            self.reraise_client_error(e)
        except socket.error as e:
            raise web.HTTPError(404, str(e))

    @property
    def fetch_kwargs(self):
        return self.settings.setdefault('fetch_kwargs', {})

    @gen.coroutine
    def fetch(self, url, **overrides):
        """fetch a url with our async client

        handle default arguments and wrapping exceptions
        """
        kw = {}
        kw.update(self.fetch_kwargs)
        kw.update(overrides)
        with self.catch_client_error():
            response = yield self.client.fetch(url, **kw)
        raise gen.Return(response)

    @contextmanager
    def time_block(self, message):
        """context manager for timing a block

        logs millisecond timings of the block
        """
        tic = time.time()
        yield
        dt = time.time() - tic
        log = app_log.info if dt > 1 else app_log.debug
        log("%s in %.2f ms", message, 1e3 * dt)

    def write_error(self, status_code, **kwargs):
        """render custom error pages"""
        exc_info = kwargs.get('exc_info')
        message = ''
        status_message = responses.get(status_code, 'Unknown')
        if exc_info:
            # get the custom message, if defined
            exception = exc_info[1]
            try:
                message = exception.log_message % exception.args
            except Exception:
                pass

            # construct the custom reason, if defined
            reason = getattr(exception, 'reason', '')
            if reason:
                status_message = reason

        # build template namespace
        ns = dict(
            status_code=status_code,
            status_message=status_message,
            message=message,
            exception=exception,
        )

        # render the template
        try:
            html = self.render_template('%d.html' % status_code, **ns)
        except Exception as e:
            app_log.warn("No template for %d", status_code)
            html = self.render_template('error.html', **ns)
        self.set_header('Content-Type', 'text/html')
        self.write(html)

    #---------------------------------------------------------------
    # response caching
    #---------------------------------------------------------------

    @property
    def cache_headers(self):
        # are there other headers to cache?
        h = {}
        for key in ('Content-Type',):
            if key in self._headers:
                h[key] = self._headers[key]
        return h

    _cache_key = None
    _cache_key_attr = 'uri'
    @property
    def cache_key(self):
        """Use checksum for cache key because cache has size limit on keys
        """

        if self._cache_key is None:
            to_hash = utf8(getattr(self.request, self._cache_key_attr))
            self._cache_key = hashlib.sha1(to_hash).hexdigest()
        return self._cache_key

    def truncate(self, s, limit=256):
        """Truncate long strings"""
        if len(s) > limit:
            s = "%s...%s" % (s[:limit/2], s[limit/2:])
        return s

    @gen.coroutine
    def cache_and_finish(self, content=''):
        """finish a request and cache the result

        does not actually call finish - if used in @web.asynchronous,
        finish must be called separately. But we never use @web.asynchronous,
        because we are using gen.coroutine for async.

        currently only works if:

        - result is not written in multiple chunks
        - custom headers are not used
        """
        request_time = self.request.request_time()
        # set cache expiry to 120x request time
        # bounded by cache_expiry_min,max
        # a 30 second render will be cached for an hour
        expiry = max(
            min(120 * request_time, self.cache_expiry_max),
            self.cache_expiry_min,
        )

        if self.request.uri in self.max_cache_uris:
            # if it's a link from the front page, cache for a long time
            expiry = self.cache_expiry_max

        if expiry > 0:
            self.set_header("Cache-Control", "max-age=%i" % expiry)

        self.write(content)
        self.finish()

        short_url = self.truncate(self.request.path)
        cache_data = pickle.dumps({
            'headers' : self.cache_headers,
            'body' : content,
        }, pickle.HIGHEST_PROTOCOL)
        log = app_log.info if expiry > self.cache_expiry_min else app_log.debug
        log("caching (expiry=%is) %s", expiry, short_url)
        try:
            with self.time_block("cache set %s" % short_url):
                yield self.cache.set(
                    self.cache_key, cache_data, int(time.time() + expiry),
                )
        except Exception:
            app_log.error("cache set for %s failed", short_url, exc_info=True)
        else:
            app_log.debug("cache set finished %s", short_url)


def cached(method):
    """decorator for a cached page.

    This only handles getting from the cache, not writing to it.
    Writing to the cache must be handled in the decorated method.
    """
    @gen.coroutine
    def cached_method(self, *args, **kwargs):
        uri = self.request.path
        short_url = self.truncate(uri)

        if self.get_argument("flush_cache", False):
            app_log.info("flushing cache %s", short_url)
            # call the wrapped method
            yield method(self, *args, **kwargs)
            return

        if uri in self.pending:
            loop = IOLoop.current()
            app_log.info("Waiting for concurrent request at %s", short_url)
            tic = loop.time()
            while uri in self.pending:
                # another request is already rendering this request,
                # wait for it
                yield gen.Task(loop.add_timeout, loop.time() + 1)
            toc = loop.time()
            app_log.info("Waited %.3fs for concurrent request at %s",
                 toc-tic, short_url
            )

        try:
            with self.time_block("cache get %s" % short_url):
                cached_pickle = yield self.cache.get(self.cache_key)
            if cached_pickle is not None:
                cached = pickle.loads(cached_pickle)
            else:
                cached = None
        except Exception as e:
            app_log.error("Exception getting %s from cache", short_url, exc_info=True)
            cached = None

        if cached is not None:
            app_log.debug("cache hit %s", short_url)
            for key, value in cached['headers'].items():
                self.set_header(key, value)
            self.write(cached['body'])
        else:
            app_log.debug("cache miss %s", short_url)
            self.pending.add(uri)
            try:
                # call the wrapped method
                yield method(self, *args, **kwargs)
            finally:
                if uri in self.pending:
                    # protect against double-remove
                    self.pending.remove(uri)

    return cached_method


class RenderingHandler(BaseHandler):
    """Base for handlers that render notebooks"""

    # notebook caches based on path (no url params)
    _cache_key_attr = 'path'

    @property
    def render_timeout(self):
        """0 render_timeout means never finish early"""
        return self.settings.setdefault('render_timeout', 0)

    def initialize(self, **kwargs):
        super(RenderingHandler, self).initialize(**kwargs)
        loop = IOLoop.current()
        if self.render_timeout:
            self.slow_timeout = loop.add_timeout(
                loop.time() + self.render_timeout,
                self.finish_early
            )

    def finish_early(self):
        """When the render is slow, draw a 'waiting' page instead

        rely on the cache to deliver the page to a future request.
        """
        if self._finished:
            return
        app_log.info("finishing early %s", self.request.uri)
        html = self.render_template('slow_notebook.html')
        self.set_status(202) # Accepted
        self.finish(html)

        # short circuit some methods because the rest of the rendering will still happen
        self.write = self.finish = self.redirect = lambda chunk=None: None

    def filter_formats(self, nb, raw):
        """Generate a list of formats that can render the given nb json

        formats that do not provide a `test` method are assumed to work for
        any notebook
        """
        for name, format in self.formats.items():
            test = format.get("test", None)
            try:
                if test is None or test(nb, raw):
                    yield (name, format)
            except Exception as err:
                app_log.info("failed to test %s: %s", self.request.uri, name)

    @gen.coroutine
    def finish_notebook(self, json_notebook, download_url, provider_url=None,
                        msg=None, breadcrumbs=None, public=False, format=None,
                        request=None, **extra_context):
        """render a notebook from its JSON body.

        download_url is required, provider_url is not.

        msg is extra information for the log message when rendering fails.
        """

        if msg is None:
            msg = download_url

        try:
            nb = reads(json_notebook, current_nbformat)
        except ValueError:
            app_log.error("Failed to render %s", msg, exc_info=True)
            raise web.HTTPError(400, "Error reading JSON notebook")

        try:
            app_log.debug("Requesting render of %s", download_url)
            with self.time_block("Rendered %s" % download_url):
                app_log.info("rendering %d B notebook from %s", len(json_notebook), download_url)
                nbhtml, config = yield self.pool.submit(render_notebook,
                    self.formats[format], nb, download_url,
                    config=self.config,
                )
        except NbFormatError as e:
            app_log.error("Invalid notebook %s: %s", msg, e)
            raise web.HTTPError(400, str(e))
        except Exception as e:
            app_log.error("Failed to render %s", msg, exc_info=True)
            raise web.HTTPError(400, str(e))
        else:
            app_log.debug("Finished render of %s", download_url)

        context = {}
        context.update(extra_context)
        context.update(config)

        html = self.render_template(
            "formats/%s.html" % format,
            body=nbhtml,
            nb=nb,
            download_url=download_url,
            provider_url=provider_url,
            format=self.format,
            default_format=self.default_format,
            format_prefix=format_prefix,
            formats=dict(self.filter_formats(nb, json_notebook)),
            format_base=self.request.uri.replace(self.format_prefix, ""),
            date=datetime.utcnow().strftime(date_fmt),
            breadcrumbs=breadcrumbs,
            **context)

        yield self.cache_and_finish(html)

        # Index notebook
        self.index.index_notebook(download_url, nb, public)


class FilesRedirectHandler(BaseHandler):
    """redirect files URLs without files prefix

    matches behavior of old app, currently unused.
    """
    def get(self, before_files, after_files):
        app_log.info("Redirecting %s to %s", before_files, after_files)
        self.redirect("%s/%s" % (before_files, after_files))


class AddSlashHandler(BaseHandler):
    """redirector for URLs that should always have trailing slash"""
    def get(self, *args, **kwargs):
        uri = self.request.path + '/'
        if self.request.query:
            uri = '%s?%s' % (uri, self.request.query)
        self.redirect(uri)


class RemoveSlashHandler(BaseHandler):
    """redirector for URLs that should never have trailing slash"""
    def get(self, *args, **kwargs):
        uri = self.request.path.rstrip('/')
        if self.request.query:
            uri = '%s?%s' % (uri, self.request.query)
        self.redirect(uri)
