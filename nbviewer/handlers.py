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

from tornado import web, gen
from tornado.escape import utf8
from tornado.log import app_log, access_log

from .render import render_notebook, NbFormatError

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
    # response caching
    #---------------------------------------------------------------
    
    def cache_and_finish(self, content=''):
        self.finish(content)
        
        burl = utf8(self.request.uri)
        bcontent = utf8(content)
        
        return self.cache.set(
            burl, bcontent, int(time.time() + self.cache_expiry),
        )


class CustomErrorHandler(web.ErrorHandler, BaseHandler):
    """Render errors with custom template"""
    def get_error_html(self, status_code, **kwargs):
        try:
            html = self.render_template('%d.html' % status_code)
        except Exception as e:
            self.log.error("no template", exc_info=True)
            html = self.render_template('error.html',
                status_code=status_code,
                status_message=responses[status_code]
            )
        return html


class IndexHandler(BaseHandler):
    def get(self):
        self.finish(self.render_template('index.html'))


class FAQHandler(BaseHandler):
    def get(self):
        self.finish(self.render_template('faq.md'))


def cached(method):
    def cached_method(self, *args, **kwargs):
        cached_response = yield self.cache.get(self.request.uri)
        if cached_response is not None:
            app_log.debug("cache hit %s", self.request.uri)
            self.finish(cached_response)
        else:
            app_log.debug("cache miss %s", self.request.uri)
            # make the actual call.
            # it's a bit hairy putting this in the right form for gen.coroutine
            generator = method(self, *args, **kwargs)
            for future in generator:
                result = yield future
                generator.send(result)
    
    return cached_method


class URLHandler(BaseHandler):
    
    @gen.coroutine
    @cached
    def get(self, secure, url):
        proto = 'http' + secure
        
        response = yield self.client.fetch("{}://{}".format(proto, url))
        if response.error:
            response.rethrow()
        
        nbjson = response.body.decode('utf8')
        try:
            nbhtml, config = render_notebook(self.exporter, nbjson, url=url)
        except NbFormatError:
            app_log.error("Failed to render file from url %s", url, exc_info=True)
            raise web.HTTPError(400)
        html = self.render_template('notebook.html', body=nbhtml, **config)
        yield self.cache_and_finish(html)

class GistHandler(BaseHandler):
    @gen.coroutine
    @cached
    def get(self, gist_id):
        response = yield self.github_client.get_gist(gist_id)
        if response.error:
            response.rethrow()
        
        data = json.loads(response.body.decode('utf8'))
        gist_id=data['id']
        files = data['files'].values()
        if len(files) == 1:
            file = list(files)[0]
            nbjson = file['content']
            try:
                nbhtml, config = render_notebook(self.exporter, nbjson, url=file['raw_url'])
            except NbFormatError:
                app_log.error("Failed to render gist: %s", gist_id, exc_info=True)
                raise web.HTTPError(400)
            html = self.render_template('notebook.html', body=nbhtml, **config)
        else:
            entries = []
            for file in files:
                entries.append(dict(
                    path=file['filename'],
                    url='/%s/%s' % (gist_id, file['filename']),
                ))
            html = self.render_template('gistlist.html', entries=entries)
        yield self.cache_and_finish(html)

class RawGitHubURLHandler(BaseHandler):
    def get(self, path):
        new_url = '/github/%s' % path
        app_log.info("Redirecting %s to %s", self.request.uri, new_url)
        self.redirect(new_url)

class GitHubRedirectHandler(BaseHandler):
    def get(self, user, repo, ref, path):
        new_url = '/github/{user}/{repo}/{ref}/{path}'.format(**locals())
        app_log.info("Redirecting %s to %s", self.request.uri, new_url)
        self.redirect(new_url)

class GitHubHandler(BaseHandler):
    @gen.coroutine
    @cached
    def get(self, user, repo, ref, path):
        response = yield self.github_client.get_contents(user, repo, path, ref=ref)
        if response.error:
            response.rethrow()
        
        data = json.loads(response.body.decode('utf8'))
        raw_url = data['html_url'].replace(
            '//github.com', '//rawgithub.com', 1
            ).replace('/blob/', '/', 1)
        try:
            nbjson = base64.decodestring(data['content'].encode('ascii')).decode('utf8')
            nbhtml, config = render_notebook(self.exporter, nbjson, url=raw_url)
        except NbFormatError:
            app_log.error("Failed to render file from GitHub: %s", data['url'], exc_info=True)
            raise web.HTTPError(400)
        html = self.render_template('notebook.html', body=nbhtml, **config)
        yield self.cache_and_finish(html)

class FilesRedirectHandler(BaseHandler):
    def get(self, before_files, after_files):
        app_log.info("Redirecting %s to %s", before_files, after_files)
        self.redirect("%s/%s" % (before_files, after_files))

#-----------------------------------------------------------------------------
# Default handler URL mapping
#-----------------------------------------------------------------------------

handlers = [
    ('/', IndexHandler),
    ('/index.html', IndexHandler),
    ('/faq', FAQHandler),
    (r'/url[s]?/github\.com/([^\/]+)/([^\/]+)/(?:tree|blob)/([^\/]+)/(.*)', GitHubRedirectHandler),
    (r'/url[s]?/raw\.?github\.com/(.*)', RawGitHubURLHandler),
    (r'/url([s]?)/(.*)', URLHandler),
    (r'/github/([\w\-]+)/([^\/]+)/([^\/]+)/(.*)', GitHubHandler),
    (r'/gist/([a-fA-F0-9]+)', GistHandler),
    (r'/([a-fA-F0-9]+)', GistHandler),
    (r'/(.*)/files/(.*)', FilesRedirectHandler),
]