#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import hashlib
import json
import mimetypes
import os
import pickle
import io
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

from tornado import web, gen, httpclient
from tornado.escape import utf8
from tornado.httputil import url_concat
from tornado.ioloop import IOLoop
from tornado.log import app_log, access_log
try:
    import pycurl
    from tornado.curl_httpclient import CurlError
except ImportError:
    pycurl = None
    class CurlError(Exception): pass

from IPython.html import DEFAULT_STATIC_FILES_PATH as ipython_static_path
from IPython.nbformat.current import reads_json

from .render import render_notebook, NbFormatError
from .utils import (transform_ipynb_uri, quote, response_text, base64_decode,
                    parse_header_links, clean_filename)

date_fmt = "%a, %d %b %Y %H:%M:%S UTC"

#-----------------------------------------------------------------------------
# Handler classes
#-----------------------------------------------------------------------------

class BaseHandler(web.RequestHandler):
    """Base Handler class with common utilities"""

    @property
    def pending(self):
        return self.settings.setdefault('pending', set())

    @property
    def exporter(self):
        return self.settings['exporter']

    @property
    def github_client(self):
        return self.settings['github_client']

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
        return self.settings.setdefault('cache_expiry_min', 60)

    @property
    def cache_expiry_max(self):
        return self.settings.setdefault('cache_expiry_max', 120)

    @property
    def pool(self):
        return self.settings['pool']

    @property
    def max_cache_uris(self):
        return self.settings.setdefault('max_cache_uris', set())

    @property
    def frontpage_sections(self):
        return self.settings.setdefault('frontpage_sections', {})

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

    def reraise_client_error(self, exc):
        """Remote fetch raised an error"""
        try:
            url = exc.response.request.url.split('?')[0]
            body = exc.response.body.decode('utf8', 'replace').strip()
        except AttributeError:
            url = 'url'
            body = ''

        str_exc = str(exc)
        # strip the unhelpful 599 prefix
        if str_exc.startswith('HTTP 599: '):
            str_exc = str_exc[10:]

        if exc.code == 403 and 'too big' in body and 'gist' in url:
            msg = "GitHub will not serve raw gists larger than 10MB"
        elif body and len(body) < 100:
            # if it's a short plain-text error message, include it
            msg = "%s (%s)" % (str_exc, escape(body))
        else:
            msg = str_exc

        app_log.warn("Fetching %s failed with %s", url, msg)
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


class Custom404(BaseHandler):
    """Render our 404 template"""
    def prepare(self):
        raise web.HTTPError(404)


class IndexHandler(BaseHandler):
    """Render the index"""
    def get(self):
        self.finish(self.render_template('index.html', sections=self.frontpage_sections))


class FAQHandler(BaseHandler):
    """Render the markdown FAQ page"""
    def get(self):
        self.finish(self.render_template('faq.md'))


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

    def initialize(self):
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


    @gen.coroutine
    def finish_notebook(self, json_notebook, download_url, home_url=None, msg=None,
                        breadcrumbs=None, public=False):
        """render a notebook from its JSON body.

        download_url is required, home_url is not.

        msg is extra information for the log message when rendering fails.
        """

        if msg is None:
            msg = download_url

        try:
            nb = reads_json(json_notebook)
        except ValueError:
            app_log.error("Failed to render %s", msg, exc_info=True)
            raise web.HTTPError(400, "Error reading JSON notebook")

        try:
            app_log.debug("Requesting render of %s", download_url)
            with self.time_block("Rendered %s" % download_url):
                app_log.info("rendering %d B notebook from %s", len(json_notebook), download_url)
                nbhtml, config = yield self.pool.submit(
                    render_notebook, self.exporter, nb, download_url,
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

        html = self.render_template('notebook.html',
            body=nbhtml,
            download_url=download_url,
            home_url=home_url,
            date=datetime.utcnow().strftime(date_fmt),
            breadcrumbs=breadcrumbs,
            **config)

        yield self.cache_and_finish(html)

        # Index notebook
        self.index.index_notebook(download_url, nb, public)


class CreateHandler(BaseHandler):
    """handle creation via frontpage form

    only redirects to the appropriate URL
    """
    def post(self):
        value = self.get_argument('gistnorurl', '')
        redirect_url = transform_ipynb_uri(value)
        app_log.info("create %s => %s", value, redirect_url)
        self.redirect(redirect_url)


class URLHandler(RenderingHandler):
    """Renderer for /url or /urls"""
    @cached
    @gen.coroutine
    def get(self, secure, url):
        proto = 'http' + secure

        if '/?' in url:
            url, query = url.rsplit('/?', 1)
        else:
            query = None

        remote_url = u"{}://{}".format(proto, quote(url))
        if query:
            remote_url = remote_url + '?' + query
        if not url.endswith('.ipynb'):
            # this is how we handle relative links (files/ URLs) in notebooks
            # if it's not a .ipynb URL and it is a link from a notebook,
            # redirect to the original URL rather than trying to render it as a notebook
            refer_url = self.request.headers.get('Referer', '').split('://')[-1]
            if refer_url.startswith(self.request.host + '/url'):
                self.redirect(remote_url)
                return

        response = yield self.fetch(remote_url)

        try:
            nbjson = response_text(response)
        except UnicodeDecodeError:
            app_log.error("Notebook is not utf8: %s", remote_url, exc_info=True)
            raise web.HTTPError(400)

        yield self.finish_notebook(nbjson, download_url=remote_url,
                                   msg="file from url: %s" % remote_url,
                                   public=True)


class UserGistsHandler(BaseHandler):
    """list a user's gists containing notebooks

    .ipynb file extension is required for listing (not for rendering).
    """
    @cached
    @gen.coroutine
    def get(self, user):
        page = self.get_argument("page", None)
        params = {}
        if page:
            params['page'] = page

        with self.catch_client_error():
            response = yield self.github_client.get_gists(user, params=params)

        prev_url, next_url = self.get_page_links(response)

        gists = json.loads(response_text(response))
        entries = []
        for gist in gists:
            notebooks = [f for f in gist['files'] if f.endswith('.ipynb')]
            if notebooks:
                entries.append(dict(
                    id=gist['id'],
                    notebooks=notebooks,
                    description=gist['description'] or '',
                ))
        github_url = u"https://gist.github.com/{user}".format(user=user)
        html = self.render_template("usergists.html",
            entries=entries, user=user, github_url=github_url,
            prev_url=prev_url, next_url=next_url,
        )
        yield self.cache_and_finish(html)


class GistHandler(RenderingHandler):
    """render a gist notebook, or list files if a multifile gist"""
    @cached
    @gen.coroutine
    def get(self, user, gist_id, filename=''):
        with self.catch_client_error():
            response = yield self.github_client.get_gist(gist_id)

        gist = json.loads(response_text(response))
        gist_id=gist['id']
        if user is None:
            # redirect to /gist/user/gist_id if no user given
            owner_dict = gist.get('owner', {})
            if owner_dict:
                user = owner_dict['login']
            else:
                user = 'anonymous'
            new_url = u"/gist/{user}/{gist_id}".format(user=user, gist_id=gist_id)
            if filename:
                new_url = new_url + "/" + filename
            self.redirect(new_url)
            return

        files = gist['files']
        many_files_gist = (len(files) > 1)

        if not many_files_gist and not filename:
            filename = list(files.keys())[0]

        if filename and filename in files:
            file = files[filename]
            if file['truncated']:
                app_log.debug("Gist %s/%s truncated, fetching %s", gist_id, filename, file['raw_url'])
                response = yield self.fetch(file['raw_url'])
                content = response_text(response)
            else:
                content = file['content']

            if not many_files_gist or filename.endswith('.ipynb'):
                yield self.finish_notebook(
                    content,
                    file['raw_url'],
                    home_url=gist['html_url'],
                    msg="gist: %s" % gist_id,
                    public=gist['public']
                )
            else:
                # cannot redirect because of X-Frame-Content
                self.finish(content)
                return

        elif filename:
            raise web.HTTPError(404, "No such file in gist: %s (%s)", filename, list(files.keys()))
        else:
            entries = []
            ipynbs = []
            others = []

            for file in files.itervalues():
                e = {}
                e['name'] = file['filename']
                if file['filename'].endswith('.ipynb'):
                    e['url'] = quote('/%s/%s' % (gist_id, file['filename']))
                    e['class'] = 'icon-book'
                    ipynbs.append(e)
                else:
                    github_url = u"https://gist.github.com/{user}/{gist_id}#file-{clean_name}".format(
                        user=user,
                        gist_id=gist_id,
                        clean_name=clean_filename(file['filename']),
                    )
                    e['url'] = github_url
                    e['class'] = 'icon-share'
                    others.append(e)

            entries.extend(ipynbs)
            entries.extend(others)

            html = self.render_template(
                'treelist.html',
                entries=entries,
                tree_type='gist',
                user=user.rstrip('/'),
                github_url=gist['html_url'],
            )
            yield self.cache_and_finish(html)


class GistRedirectHandler(BaseHandler):
    """redirect old /<gist-id> to new /gist/<gist-id>"""
    def get(self, gist_id, file=''):
        new_url = '/gist/%s' % gist_id
        if file:
            new_url = "%s/%s" % (new_url, file)

        app_log.info("Redirecting %s to %s", self.request.uri, new_url)
        self.redirect(new_url)


class RawGitHubURLHandler(BaseHandler):
    """redirect old /urls/raw.github urls to /github/ API urls"""
    def get(self, user, repo, path):
        new_url = u'/github/{user}/{repo}/blob/{path}'.format(
            user=user, repo=repo, path=path,
        )
        app_log.info("Redirecting %s to %s", self.request.uri, new_url)
        self.redirect(new_url)


class GitHubRedirectHandler(BaseHandler):
    """redirect github blob|tree|raw urls to /github/ API urls"""
    def get(self, user, repo, app, ref, path):
        if app == 'raw':
            app = 'blob'
        new_url = u'/github/{user}/{repo}/{app}/{ref}/{path}'.format(**locals())
        app_log.info("Redirecting %s to %s", self.request.uri, new_url)
        self.redirect(new_url)


class GitHubUserHandler(BaseHandler):
    """list a user's github repos"""
    @cached
    @gen.coroutine
    def get(self, user):
        page = self.get_argument("page", None)
        params = {'sort' : 'updated'}
        if page:
            params['page'] = page
        with self.catch_client_error():
            response = yield self.github_client.get_repos(user, params=params)

        prev_url, next_url = self.get_page_links(response)
        repos = json.loads(response_text(response))

        entries = []
        for repo in repos:
            entries.append(dict(
                url=repo['name'],
                name=repo['name'],
            ))
        github_url = u"https://github.com/{user}".format(user=user)
        html = self.render_template("userview.html",
            entries=entries, github_url=github_url,
            next_url=next_url, prev_url=prev_url,
        )
        yield self.cache_and_finish(html)


class GitHubRepoHandler(BaseHandler):
    """redirect /github/user/repo to .../tree/master"""
    def get(self, user, repo):
        self.redirect("/github/%s/%s/tree/master/" % (user, repo))


class GitHubTreeHandler(BaseHandler):
    """list files in a github repo (like github tree)"""
    @cached
    @gen.coroutine
    def get(self, user, repo, ref, path):
        if not self.request.uri.endswith('/'):
            self.redirect(self.request.uri + '/')
            return
        path = path.rstrip('/')
        with self.catch_client_error():
            response = yield self.github_client.get_contents(user, repo, path, ref=ref)

        contents = json.loads(response_text(response))

        branches, tags = yield self.refs(user, repo)

        if not isinstance(contents, list):
            app_log.info("{user}/{repo}/{ref}/{path} not tree, redirecting to blob",
                extra=dict(user=user, repo=repo, ref=ref, path=path)
            )
            self.redirect(
                u"/github/{user}/{repo}/blob/{ref}/{path}".format(
                    user=user, repo=repo, ref=ref, path=path,
                )
            )
            return

        base_url = u"/github/{user}/{repo}/tree/{ref}".format(
            user=user, repo=repo, ref=ref,
        )
        github_url = u"https://github.com/{user}/{repo}/tree/{ref}/{path}".format(
            user=user, repo=repo, ref=ref, path=path,
        )

        breadcrumbs = [{
            'url' : base_url,
            'name' : repo,
        }]
        breadcrumbs.extend(self.breadcrumbs(path, base_url))

        entries = []
        dirs = []
        ipynbs = []
        others = []
        for file in contents:
            e = {}
            e['name'] = file['name']
            if file['type'] == 'dir':
                e['url'] = u'/github/{user}/{repo}/tree/{ref}/{path}'.format(
                user=user, repo=repo, ref=ref, path=file['path']
                )
                e['url'] = quote(e['url'])
                e['class'] = 'icon-folder-open'
                dirs.append(e)
            elif file['name'].endswith('.ipynb'):
                e['url'] = u'/github/{user}/{repo}/blob/{ref}/{path}'.format(
                user=user, repo=repo, ref=ref, path=file['path']
                )
                e['url'] = quote(e['url'])
                e['class'] = 'icon-book'
                ipynbs.append(e)
            elif file['html_url']:
                e['url'] = file['html_url']
                e['class'] = 'icon-share'
                others.append(e)
            else:
                # submodules don't have html_url
                e['url'] = ''
                e['class'] = 'icon-folder-close'
                others.append(e)


        entries.extend(dirs)
        entries.extend(ipynbs)
        entries.extend(others)

        html = self.render_template("treelist.html",
            entries=entries, breadcrumbs=breadcrumbs, github_url=github_url,
            user=user, repo=repo, ref=ref, path=path,
            branches=branches, tags=tags
        )
        yield self.cache_and_finish(html)

    @gen.coroutine
    def refs(self, user, repo):
        """get (cached) branches and tags for this user/repo"""
        short_url = self.truncate("github/%s/%s/refs" % (user, repo))
        ref_types = ("branches", "tags")
        ref_data = [None, None]
        cached_pickle = None

        try:
            with self.time_block("cache get %s" % short_url):
                cached_pickle = yield self.cache.get(short_url)
            if cached_pickle is not None:
                ref_data = pickle.loads(cached_pickle)
        except Exception as e:
            app_log.error("Exception getting %s from cache", short_url, exc_info=True)

        if cached_pickle is None:
            for i, ref_type in enumerate(ref_types):
                with self.catch_client_error():
                    response = yield getattr(self.github_client, "get_%s" % ref_type)(user, repo)
                ref_data[i] = json.loads(response_text(response))

            cache_data = pickle.dumps(ref_data, pickle.HIGHEST_PROTOCOL)

            request_time = self.request.request_time()
            # set cache expiry to 120x request time
            # bounded by cache_expiry_min,max
            # a 30 second render will be cached for an hour
            expiry = max(
                min(120 * request_time, self.cache_expiry_max),
                self.cache_expiry_min,
            )

            log = app_log.info if expiry > self.cache_expiry_min else app_log.debug
            log("caching (expiry=%is) %s", expiry, short_url)
            try:
                with self.time_block("cache set %s" % short_url):
                    yield self.cache.set(
                        short_url, cache_data, int(time.time() + expiry),
                    )
            except Exception:
                app_log.error("cache set for %s failed", short_url, exc_info=True)
            else:
                app_log.debug("cache set finished %s", short_url)

        raise gen.Return(ref_data)


class GitHubBlobHandler(RenderingHandler):
    """handler for files on github

    If it's a...

    - notebook, render it
    - non-notebook file, serve file unmodified
    - directory, redirect to tree
    """
    @cached
    @gen.coroutine
    def get(self, user, repo, ref, path):
        raw_url = u"https://raw.githubusercontent.com/{user}/{repo}/{ref}/{path}".format(
            user=user, repo=repo, ref=ref, path=quote(path)
        )
        blob_url = u"https://github.com/{user}/{repo}/blob/{ref}/{path}".format(
            user=user, repo=repo, ref=ref, path=quote(path),
        )
        with self.catch_client_error():
            tree_entry = yield self.github_client.get_tree_entry(
                user, repo, path=path, ref=ref
            )

        if tree_entry['type'] == 'tree':
            tree_url = "/github/{user}/{repo}/tree/{ref}/{path}/".format(
                user=user, repo=repo, ref=ref, path=quote(path),
            )
            app_log.info("%s is a directory, redirecting to %s", self.request.path, tree_url)
            self.redirect(tree_url)
            return

        # fetch file data from the blobs API
        with self.catch_client_error():
            response = yield self.github_client.fetch(tree_entry['url'])

        data = json.loads(response_text(response))
        contents = data['content']
        if data['encoding'] == 'base64':
            # filedata will be bytes
            filedata = base64_decode(contents)
        else:
            # filedata will be unicode
            filedata = contents

        if path.endswith('.ipynb'):
            dir_path = path.rsplit('/', 1)[0]
            base_url = "/github/{user}/{repo}/tree/{ref}".format(
                user=user, repo=repo, ref=ref,
            )
            breadcrumbs = [{
                'url' : base_url,
                'name' : repo,
            }]
            breadcrumbs.extend(self.breadcrumbs(dir_path, base_url))

            try:
                # filedata may be bytes, but we need text
                if isinstance(filedata, bytes):
                    nbjson = filedata.decode('utf-8')
                else:
                    nbjson = filedata
            except Exception as e:
                app_log.error("Failed to decode notebook: %s", raw_url, exc_info=True)
                raise web.HTTPError(400)
            yield self.finish_notebook(nbjson, raw_url,
                home_url=blob_url,
                breadcrumbs=breadcrumbs,
                msg="file from GitHub: %s" % raw_url,
                public=True
            )
        else:
            mime, enc = mimetypes.guess_type(path)
            self.set_header("Content-Type", mime or 'text/plain')
            self.cache_and_finish(filedata)


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


class LocalFileHandler(RenderingHandler):
    """Renderer for /localfile

    Serving notebooks from the local filesystem
    """
    @cached
    @gen.coroutine
    def get(self, path):
        abspath = os.path.join(
            self.settings.get('localfile_path', ''),
            path,
        )

        app_log.info("looking for file: '%s'" % abspath)
        if not os.path.exists(abspath):
            raise web.HTTPError(404)

        with io.open(abspath, encoding='utf-8') as f:
            nbdata = f.read()

        yield self.finish_notebook(nbdata, download_url=path,
                                   msg="file from localfile: %s" % path,
                                   public=False)


#-----------------------------------------------------------------------------
# Default handler URL mapping
#-----------------------------------------------------------------------------

handlers = [
    ('/', IndexHandler),
    ('/index.html', IndexHandler),
    (r'/faq/?', FAQHandler),
    (r'/create/?', CreateHandler),
    (r'/ipython-static/(.*)', web.StaticFileHandler, dict(path=ipython_static_path)),

    # don't let super old browsers request data-uris
    (r'.*/data:.*;base64,.*', Custom404),

    (r'/url[s]?/github\.com/([^\/]+)/([^\/]+)/(tree|blob|raw)/([^\/]+)/(.*)', GitHubRedirectHandler),
    (r'/url[s]?/raw\.?github(?:usercontent)?\.com/([^\/]+)/([^\/]+)/(.*)', RawGitHubURLHandler),
    (r'/url([s]?)/(.*)', URLHandler),

    (r'/github/([^\/]+)', AddSlashHandler),
    (r'/github/([^\/]+)/', GitHubUserHandler),
    (r'/github/([^\/]+)/([^\/]+)', AddSlashHandler),
    (r'/github/([^\/]+)/([^\/]+)/', GitHubRepoHandler),
    (r'/github/([^\/]+)/([^\/]+)/blob/([^\/]+)/(.*)/', RemoveSlashHandler),
    (r'/github/([^\/]+)/([^\/]+)/blob/([^\/]+)/(.*)', GitHubBlobHandler),
    (r'/github/([^\/]+)/([^\/]+)/tree/([^\/]+)', AddSlashHandler),
    (r'/github/([^\/]+)/([^\/]+)/tree/([^\/]+)/(.*)', GitHubTreeHandler),

    (r'/gist/([^\/]+/)?([0-9]+|[0-9a-f]{20})', GistHandler),
    (r'/gist/([^\/]+/)?([0-9]+|[0-9a-f]{20})/(?:files/)?(.*)', GistHandler),
    (r'/([0-9]+|[0-9a-f]{20})', GistRedirectHandler),
    (r'/([0-9]+|[0-9a-f]{20})/(.*)', GistRedirectHandler),
    (r'/gist/([^\/]+)/?', UserGistsHandler),
    (r'/(robots\.txt|favicon\.ico)', web.StaticFileHandler),

    (r'.*', Custom404),
]
