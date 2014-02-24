#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import base64
import hashlib
import json
import os
import io
import socket
import time

from contextlib import contextmanager

try:
    # py3
    from http.client import responses
except ImportError:
    from httplib import responses

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


from .render import render_notebook, NbFormatError
from .utils import transform_ipynb_uri, quote, response_text

#-----------------------------------------------------------------------------
# Handler classes
#-----------------------------------------------------------------------------

class BaseHandler(web.RequestHandler):
    """Base Handler class with common utilities"""
    
    @property
    def exporter(self):
        return self.settings['exporter']
    
    @property
    def github_client(self):
        return self.settings['github_client']
    
    @property
    def client(self):
        return self.settings['client']
    
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
    
    #---------------------------------------------------------------
    # error handling
    #---------------------------------------------------------------
    
    def reraise_client_error(self, exc):
        """Remote fetch raised an error"""
        try:
            url = exc.response.request.url
        except AttributeError:
            url = 'url'
        app_log.warn("Fetching %s failed with %s", url, exc)
        if exc.code == 599:
            str_exc = str(exc)
            # strip the unhelpful 599 prefix
            if str_exc.startswith('HTTP 599: '):
                str_exc = str_exc[10:]
            if isinstance(exc, CurlError):
                en = getattr(exc, 'errno', -1)
                # can't connect to server should be 404
                # possibly more here
                if en in (pycurl.E_COULDNT_CONNECT, pycurl.E_COULDNT_RESOLVE_HOST):
                    raise web.HTTPError(404, str_exc)
            # otherwise, raise 400 with informative message:
            raise web.HTTPError(400, str_exc)
        if exc.code >= 500:
            # 5XX, server error, but not this server
            raise web.HTTPError(502, str(exc))
        else:
            if exc.code == 404:
                raise web.HTTPError(404, "Remote %s" % exc)
            else:
                # client-side error, blame our client
                raise web.HTTPError(400, str(exc))
    
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
    
    @contextmanager
    def time_block(self, message):
        """context manager for timing a block
        
        logs millisecond timings of the block
        """
        tic = time.time()
        yield
        toc = time.time()
        app_log.info("%s in %.2f ms", message, 1e3*(toc-tic))
        
    def get_error_html(self, status_code, **kwargs):
        """render custom error pages"""
        exception = kwargs.get('exception')
        message = ''
        status_message = responses.get(status_code, 'Unknown')
        if exception:
            # get the custom message, if defined
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
        return html

    #---------------------------------------------------------------
    # response caching
    #---------------------------------------------------------------
    
    _cache_key = None
    @property
    def cache_key(self):
        """Use checksum of uri, not uri itself, in the cache
        
        cache has size limit on keys
        """
        if self._cache_key is None:
            self._cache_key = hashlib.sha1(utf8(self.request.uri)).hexdigest()
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
        self.write(content)
        short_url = self.truncate(self.request.uri)
        bcontent = utf8(content)
        request_time = self.request.request_time()
        # set cache expiry to 120x request time
        # bounded by cache_expiry_min,max
        # a 30 second render will be cached for an hour
        expiry = max(
            min(120 * request_time, self.cache_expiry_max),
            self.cache_expiry_min,
        )
        refer_url = self.request.headers.get('Referer', '').split('://')[-1]
        if refer_url == self.request.host + '/' and not self.get_argument('create', ''):
            # if it's a link from the front page, cache for a long time
            expiry = self.cache_expiry_max
        
        app_log.info("caching (expiry=%is) %s", expiry, short_url)
        try:
            with self.time_block("cache set %s" % short_url):
                yield self.cache.set(
                    self.cache_key, bcontent, int(time.time() + expiry),
                )
        except Exception:
            app_log.error("cache set for %s failed", short_url, exc_info=True)
        else:
            app_log.debug("cache set finished %s", short_url)


class Custom404(BaseHandler):
    """Render our 404 template"""
    def prepare(self):
        raise web.HTTPError(404)

this_dir, this_filename = os.path.split(__file__)
DATA_PATH = os.path.join(this_dir , "frontpage.json")
with io.open(DATA_PATH, 'r') as datafile:
    sections = json.load(datafile)

class IndexHandler(BaseHandler):
    """Render the index"""
    def get(self):
        self.finish(self.render_template('index.html',sections=sections))


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
        short_url = self.truncate(self.request.uri)
        try:
            with self.time_block("cache get %s" % short_url):
                cached_response = yield self.cache.get(self.cache_key)
        except Exception as e:
            app_log.error("Exception getting %s from cache", short_url, exc_info=True)
            cached_response = None
        
        if cached_response is not None:
            app_log.debug("cache hit %s", short_url)
            self.write(cached_response)
        else:
            app_log.debug("cache miss %s", short_url)
            # call the wrapped method
            yield method(self, *args, **kwargs)
    
    return cached_method


class RenderingHandler(BaseHandler):
    """Base for handlers that render notebooks"""
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
        self.finish(html)
        
        # short circuit some methods because the rest of the rendering will still happen
        self.write = self.finish = self.redirect = lambda chunk=None: None
    
    
    @gen.coroutine
    def finish_notebook(self, nbjson, download_url, home_url=None, msg=None):
        """render a notebook from its JSON body.
        
        download_url is required, home_url is not.
        
        msg is extra information for the log message when rendering fails.
        """
        if msg is None:
            msg = download_url
        try:
            app_log.debug("Requesting render of %s", download_url)
            with self.time_block("Rendered %s" % download_url):
                nbhtml, config = yield self.pool.submit(
                    render_notebook, self.exporter, nbjson, download_url,
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
            **config)
        yield self.cache_and_finish(html)


class CreateHandler(BaseHandler):
    """handle creation via frontpage form
    
    only redirects to the appropriate URL
    """
    def post(self):
        value = self.get_argument('gistnorurl', '')
        redirect_url = transform_ipynb_uri(value)
        app_log.info("create %s => %s", value, redirect_url)
        self.redirect(url_concat(redirect_url, {'create': 1}))


class URLHandler(RenderingHandler):
    """Renderer for /url or /urls"""
    @cached
    @gen.coroutine
    def get(self, secure, url):
        proto = 'http' + secure
        
        remote_url = u"{}://{}".format(proto, quote(url))
        if not url.endswith('.ipynb'):
            # this is how we handle relative links (files/ URLs) in notebooks
            # if it's not a .ipynb URL and it is a link from a notebook,
            # redirect to the original URL rather than trying to render it as a notebook
            refer_url = self.request.headers.get('Referer', '').split('://')[-1]
            if refer_url.startswith(self.request.host + '/url'):
                self.redirect(remote_url)
                return
        
        with self.catch_client_error():
            response = yield self.client.fetch(remote_url)
        
        try:
            nbjson = response_text(response)
        except UnicodeDecodeError:
            app_log.error("Notebook is not utf8: %s", remote_url, exc_info=True)
            raise web.HTTPError(400)
        
        yield self.finish_notebook(nbjson, download_url=remote_url, msg="file from url: %s" % remote_url)


class UserGistsHandler(BaseHandler):
    """list a user's gists containing notebooks
    
    .ipynb file extension is required for listing (not for rendering).
    """
    @cached
    @gen.coroutine
    def get(self, user):
        with self.catch_client_error():
            response = yield self.github_client.get_gists(user)
        
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
            user_dict = gist['user']
            if user_dict:
                user = user_dict['login']
            else:
                user = 'anonymous'
            new_url = u"/gist/{user}/{gist_id}".format(user=user, gist_id=gist_id)
            if filename:
                new_url = new_url + "/" + filename
            self.redirect(new_url)
            return
        
        github_url = gist['html_url']
        files = gist['files']
        many_files_gist = (len(files) > 1)
        
        if not many_files_gist and not filename:
            filename = list(files.keys())[0]
        
        if filename and filename in files:

            if not many_files_gist or filename.endswith('.ipynb'):
                file = files[filename]
                nbjson = file['content']
                yield self.finish_notebook(nbjson, file['raw_url'],
                    home_url=gist['html_url'],
                    msg="gist: %s" % gist_id,
                )
            else:
                file = files[filename]
                # cannot redirect because of X-Frame-Content
                self.finish(file['content'])
                return

        elif filename:
            raise web.HTTPError(404, "No such file in gist: %s (%s)", filename, list(files.keys()))
        else:
            entries = []
            for filename, file in files.items():
                entries.append(dict(
                    path=filename,
                    url=quote('/%s/%s' % (gist_id, filename)),
                ))
            html = self.render_template('gistlist.html',
                entries=entries, github_url=gist['html_url'],
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
        with self.catch_client_error():
            response = yield self.github_client.get_repos(user)
        
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

        path_list = [{
            'url' : base_url,
            'name' : repo,
        }]
        if path:
            for name in path.split('/'):
                href = base_url = "%s/%s" % (base_url, name)
                path_list.append({
                    'url' : base_url,
                    'name' : name,
                })
        
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
                e['class'] = 'icon-folder-open'
                dirs.append(e)
            elif file['name'].endswith('.ipynb'):
                e['url'] = u'/github/{user}/{repo}/blob/{ref}/{path}'.format(
                user=user, repo=repo, ref=ref, path=file['path']
                )
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
            e['url'] = quote(e['url'])
        
        entries.extend(dirs)
        entries.extend(ipynbs)
        entries.extend(others)

        html = self.render_template("treelist.html",
            entries=entries, path_list=path_list, github_url=github_url,
        )
        yield self.cache_and_finish(html)
    

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
        raw_url = u"https://raw.github.com/{user}/{repo}/{ref}/{path}".format(
            user=user, repo=repo, ref=ref, path=quote(path)
        )
        blob_url = u"https://github.com/{user}/{repo}/blob/{ref}/{path}".format(
            user=user, repo=repo, ref=ref, path=quote(path),
        )
        with self.catch_client_error():
            response = yield self.client.fetch(raw_url)
        
        if response.effective_url.startswith("https://github.com/{user}/{repo}/tree".format(
            user=user, repo=repo
        )):
            tree_url = "/github/{user}/{repo}/tree/{ref}/{path}/".format(
                user=user, repo=repo, ref=ref, path=quote(path),
            )
            app_log.info("%s is a directory, redirecting to %s", raw_url, tree_url)
            self.redirect(tree_url)
            return
        
        filedata = response.body
        
        if path.endswith('.ipynb'):
            try:
                nbjson = response_text(response)
            except Exception as e:
                app_log.error("Failed to decode notebook: %s", raw_url, exc_info=True)
                raise web.HTTPError(400)
            yield self.finish_notebook(nbjson, raw_url,
                home_url=blob_url,
                msg="file from GitHub: %s" % raw_url,
            )
        else:
            self.set_header("Content-Type", response.headers.get('Content-Type', 'text/plain'))
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
        self.redirect(self.request.uri + '/')


class RemoveSlashHandler(BaseHandler):
    """redirector for URLs that should never have trailing slash"""
    def get(self, *args, **kwargs):
        self.redirect(self.request.uri.rstrip('/'))

class LocalFileHandler(RenderingHandler):
    """Renderer for /localfile """
    @cached
    @gen.coroutine
    def get(self, path):
        
        #remote_url = u"{}://{}".format(proto, quote(url))
        #if not url.endswith('.ipynb'):
            # this is how we handle relative links (files/ URLs) in notebooks
            # if it's not a .ipynb URL and it is a link from a notebook,
            # redirect to the original URL rather than trying to render it as a notebook
        #    refer_url = self.request.headers.get('Referer', '').split('://')[-1]
        #    if refer_url.startswith(self.request.host + '/url'):
        #        self.redirect(remote_url)
        #        return
        
        #with self.catch_client_error():
        #abspath = os.path.join(os.path.abspath(os.curdir),path)
        abspath = os.path.join(
            os.path.abspath(os.curdir),
            self.settings.get('localfile_path', ''),
            path,
        )
        app_log.info("looking for file: '%s'" % abspath)
        with io.open(abspath) as f:
            response = f.read()
        
        yield self.finish_notebook(response, download_url=path, msg="file from localfile: %s" % path)
#-----------------------------------------------------------------------------
# Default handler URL mapping
#-----------------------------------------------------------------------------

handlers = [
    ('/', IndexHandler),
    ('/index.html', IndexHandler),
    (r'/faq/?', FAQHandler),
    (r'/create/?', CreateHandler),
    
    # don't let super old browsers request data-uris
    (r'.*/data:.*;base64,.*', Custom404),
    
    (r'/url[s]?/github\.com/([^\/]+)/([^\/]+)/(tree|blob|raw)/([^\/]+)/(.*)', GitHubRedirectHandler),
    (r'/url[s]?/raw\.?github\.com/([^\/]+)/([^\/]+)/(.*)', RawGitHubURLHandler),
    (r'/url([s]?)/(.*)', URLHandler),
    
    (r'/github/([\w\-]+)', AddSlashHandler),
    (r'/github/([\w\-]+)/', GitHubUserHandler),
    (r'/github/([\w\-]+)/([\w\-]+)', AddSlashHandler),
    (r'/github/([\w\-]+)/([\w\-]+)/', GitHubRepoHandler),
    (r'/github/([\w\-]+)/([^\/]+)/blob/([^\/]+)/(.*)/', RemoveSlashHandler),
    (r'/github/([\w\-]+)/([^\/]+)/blob/([^\/]+)/(.*)', GitHubBlobHandler),
    (r'/github/([\w\-]+)/([^\/]+)/tree/([^\/]+)', AddSlashHandler),
    (r'/github/([\w\-]+)/([^\/]+)/tree/([^\/]+)/(.*)', GitHubTreeHandler),
    
    (r'/gist/([\w\-]+/)?([0-9]+|[0-9a-f]{20})', GistHandler),
    (r'/gist/([\w\-]+/)?([0-9]+|[0-9a-f]{20})/(?:files/)?(.*)', GistHandler),
    (r'/([0-9]+|[0-9a-f]{20})', GistRedirectHandler),
    (r'/([0-9]+|[0-9a-f]{20})/(.*)', GistRedirectHandler),
    (r'/gist/([\w\-]+)/?', UserGistsHandler),

    (r'.*', Custom404),
]
