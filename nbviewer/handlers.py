#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import base64
import json
import time

try:
    # py3
    from http.client import responses
except ImportError:
    from httplib import responses

from tornado import web, gen, httpclient
from tornado.escape import utf8
from tornado.log import app_log, access_log

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
    def cache_expiry(self):
        return self.settings.get('cache_expiry', 60)
    
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
    
    def get_error_html(self, status_code, **kwargs):
        try:
            html = self.render_template('%d.html' % status_code)
        except Exception as e:
            app_log.error("No template for %d", status_code)
            html = self.render_template('error.html',
                status_code=status_code,
                status_message=responses[status_code]
            )
        return html

    #---------------------------------------------------------------
    # response caching
    #---------------------------------------------------------------
    
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
        
        burl = utf8(self.request.uri)
        bcontent = utf8(content)
        
        try:
            yield self.cache.set(
                burl, bcontent, int(time.time() + self.cache_expiry),
            )
        except Exception:
            app_log.error("cache set for %s failed", burl, exc_info=True)


class Custom404(BaseHandler):
    """Render our 404 template"""
    def prepare(self):
        raise web.HTTPError(404)


class IndexHandler(BaseHandler):
    """Render the index"""
    def get(self):
        self.finish(self.render_template('index.html'))


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
        try:
            cached_response = yield self.cache.get(self.request.uri)
        except Exception as e:
            app_log.error("exception getting %s from cache", self.request.uri)
            cached_response = None
        
        if cached_response is not None:
            app_log.debug("cache hit %s", self.request.uri)
            self.write(cached_response)
        else:
            app_log.debug("cache miss %s", self.request.uri)
            # call the wrapped method
            yield method(self, *args, **kwargs)
    
    return cached_method


class RenderingHandler(BaseHandler):
    """Base for handlers that render notebooks"""
    @gen.coroutine
    def finish_notebook(self, nbjson, download_url, home_url=None, msg=None):
        """render a notebook from its JSON body.
        
        download_url is required, home_url is not.
        
        msg is extra information for the log message when rendering fails.
        """
        if msg is None:
            msg = url
        try:
            nbhtml, config = yield self.pool.submit(
                render_notebook, self.exporter, nbjson, download_url,
            )
        except NbFormatError as e:
            app_log.error("Failed to render %s", msg, exc_info=True)
            raise web.HTTPError(400)
        
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
        self.redirect(redirect_url)
        return


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
        
        app_log.info("Fetching %s", remote_url)
        try:
            response = yield self.client.fetch(remote_url)
        except httpclient.HTTPError as e:
            raise web.HTTPError(e.code)
        
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
        try:
            response = yield self.github_client.get_gists(user)
        except httpclient.HTTPError as e:
            raise web.HTTPError(e.code)
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
        html = self.render_template("usergists.html", entries=entries, user=user)
        yield self.cache_and_finish(html)


class GistHandler(RenderingHandler):
    """render a gist notebook, or list files if a multifile gist"""
    @cached
    @gen.coroutine
    def get(self, user, gist_id, filename=''):
        try:
            response = yield self.github_client.get_gist(gist_id)
        except httpclient.HTTPError as e:
            raise web.HTTPError(e.code)
        
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
        
        files = gist['files']
        if len(files) == 1 and not filename:
            filename = list(files.keys())[0]
        
        if filename and filename in files:
            file = files[filename]
            nbjson = file['content']
            yield self.finish_notebook(nbjson, file['raw_url'],
                home_url=gist['html_url'],
                msg="gist: %s" % gist_id,
            )
        elif filename:
            raise web.HTTPError(404, "No such file in gist: %s (%s)", filename, list(files.keys()))
        else:
            entries = []
            for filename, file in files.items():
                entries.append(dict(
                    path=filename,
                    url='/%s/%s' % (gist_id, filename),
                ))
            html = self.render_template('gistlist.html', entries=entries)
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
        try:
            response = yield self.github_client.get_repos(user)
        except httpclient.HTTPError as e:
            raise web.HTTPError(e.code)
        
        repos = json.loads(response_text(response))
        entries = []
        for repo in repos:
            entries.append(dict(
                url=repo['name'],
                name=repo['name'],
            ))
        html = self.render_template("userview.html", entries=entries)
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
        try:
            response = yield self.github_client.get_contents(user, repo, path, ref=ref)
        except httpclient.HTTPError as e:
            raise web.HTTPError(e.code)
        
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
        for file in contents:
            e = {}
            e['name'] = file['name']
            if file['type'] == 'dir':
                e['url'] = u'/github/{user}/{repo}/tree/{ref}/{path}'.format(
                user=user, repo=repo, ref=ref, path=file['path']
                )
                e['class'] = 'icon-folder-open'
            elif file['name'].endswith('.ipynb'):
                e['url'] = u'/github/{user}/{repo}/blob/{ref}/{path}'.format(
                user=user, repo=repo, ref=ref, path=file['path']
                )
                e['class'] = 'icon-book'
            else:
                e['url'] = file['html_url']
                e['class'] = 'icon-share'
            entries.append(e)
        # print path, path_list
        html = self.render_template("treelist.html", entries=entries, path_list=path_list)
        yield self.cache_and_finish(html)
    

class GitHubBlobHandler(RenderingHandler):
    """handler for files on github
    
    If it's a...
    
    - notebook, render it
    - non-notebook file, serve file unmodified
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
        app_log.info("fetching %s", raw_url)
        try:
            response = yield self.client.fetch(raw_url)
        except httpclient.HTTPError as e:
            raise web.HTTPError(e.code)
        
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
            self.set_header("Content-Type", "text/plain")
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


#-----------------------------------------------------------------------------
# Default handler URL mapping
#-----------------------------------------------------------------------------

handlers = [
    ('/', IndexHandler),
    ('/index.html', IndexHandler),
    (r'/faq/?', FAQHandler),
    (r'/create/?', CreateHandler),
    
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
    (r'/gist/([\w\-]+/)?([0-9]+|[0-9a-f]{20})/(.*)', GistHandler),
    (r'/([0-9]+|[0-9a-f]{20})', GistRedirectHandler),
    (r'/([0-9]+|[0-9a-f]{20})/(.*)', GistRedirectHandler),
    (r'/gist/([\w\-]+)/?', UserGistsHandler),

    (r'.*', Custom404),
]