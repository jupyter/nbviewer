#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import base64
import httplib
import json

from tornado import web
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
    
class CustomErrorHandler(web.ErrorHandler, BaseHandler):
    """Render errors with custom template"""
    def get_error_html(self, status_code, **kwargs):
        try:
            html = self.render_template('%d.html' % status_code)
        except Exception as e:
            self.log.error("no template", exc_info=True)
            html = self.render_template('error.html',
                status_code=status_code,
                status_message=httplib.responses[status_code]
            )
        return html

class IndexHandler(BaseHandler):
    
    def get(self):
        self.finish(self.render_template('index.html'))

class URLHandler(BaseHandler):
    
    @web.asynchronous
    def get(self, secure, remote_url):
        app_log.info("requesting URL: %s | %s", secure, remote_url)
        proto = 'http' + secure
        self.client.fetch("{}://{}".format(proto, remote_url),
            callback=self.handle_response
        )
    
    def handle_response(self, response):
        if response.error:
            response.rethrow()
        
        nbjson = response.body.decode('utf8')
        url = response.request.url
        try:
            nbhtml, config = render_notebook(self.exporter, nbjson, url=url)
        except NbFormatError:
            app_log.error("Failed to render file from url %s", url, exc_info=True)
            raise web.HTTPError(400)
        html = self.render_template('notebook.html', body=nbhtml, **config)
        self.finish(html)

class GistHandler(BaseHandler):
    @web.asynchronous
    def get(self, gist_id):
        self.github_client.get_gist(gist_id, self.handle_gist_reply)
    
    def handle_gist_reply(self, response):
        if response.error:
            response.rethrow()
        
        data = json.loads(response.body)
        app_log.info(json.dumps(data.keys(), indent=1))
        gist_id=data['id']
        files = data['files'].values()
        if len(files) == 1:
            file = files[0]
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
        self.finish(html)

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
    @web.asynchronous
    def get(self, user, repo, ref, path):
        app_log.info("GitHub: %s / %s / %s @ %s", user, repo, path, ref)
        self.github_client.get_contents(user, repo, path, ref=ref,
            callback=self.handle_reply
        )
    
    def handle_reply(self, response):
        if response.error:
            response.rethrow()
        
        data = json.loads(response.body)
        raw_url = data['html_url'].replace(
            '//github.com', '//rawgithub.com', 1
            ).replace('/blob/', '/', 1)
        try:
            nbjson = base64.decodestring(data['content'])
            nbhtml, config = render_notebook(self.exporter, nbjson, url=raw_url)
        except NbFormatError:
            app_log.error("Failed to render file from GitHub: %s", data['url'], exc_info=True)
            raise web.HTTPError(400)
        html = self.render_template('notebook.html', body=nbhtml, **config)
        self.finish(html)

class FilesRedirectHandler(BaseHandler):
    def get(self, before_files, after_files):
        app_log.info("redirect: %s / %s", before_files, after_files)
        self.redirect("%s/%s" % (before_files, after_files))

#-----------------------------------------------------------------------------
# Default handler URL mapping
#-----------------------------------------------------------------------------

handlers = [
    ('/', IndexHandler),
    ('/index.html', IndexHandler),
    (r'/url[s]?/github\.com/([^\/]+)/([^\/]+)/(?:tree|blob)/([^\/]+)/(.*)', GitHubRedirectHandler),
    (r'/url[s]?/raw\.?github\.com/(.*)', RawGitHubURLHandler),
    (r'/url([s]?)/(.*)', URLHandler),
    (r'/github/([\w\-]+)/([^\/]+)/([^\/]+)/(.*)', GitHubHandler),
    (r'/gist/([a-fA-F0-9]+)', GistHandler),
    (r'/([a-fA-F0-9]+)', GistHandler),
    (r'/(.*)/files/(.*)', FilesRedirectHandler),
]