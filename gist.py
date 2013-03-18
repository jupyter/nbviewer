import os
import re
import json
import httplib

import jinja2
import markdown

# probably to get rid of
import requests

#ipython import
from IPython.nbformat import current as nbformat
from IPython.config import Config
from nbconvert2.converters.template import ConverterTemplate

#external import
from werkzeug.contrib.cache import SimpleCache

# to get rid of
from flask import request
from lib.MemcachedMultipart import multipartmemecached

# tornado import
import tornado.web
from tornado.web import asynchronous
from tornado.httpclient import AsyncHTTPClient
from tornado import gen
from jinja2 import Environment, FileSystemLoader


# global config

g_config = {}

# token to access github and not be limited in # of request
g_config['GITHUB'] = {
    'client_id': os.environ.get('GITHUB_OAUTH_KEY', ''),
    'client_secret': os.environ.get('GITHUB_OAUTH_SECRET', ''),
}


#jinja environement
env = Environment(
        loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates"))
        )

def safe_markdown(text):
    return jinja2.Markup(markdown.markdown(text))

env.filters['markdown'] = safe_markdown


# deal with memcache server if we have some
# nothing use it anymore, but just in case...
servers = os.environ.get('MEMCACHIER_SERVERS', '127.0.0.1'),
username = str(os.environ.get('MEMCACHIER_USERNAME', '')),
password = str(os.environ.get('MEMCACHIER_PASSWORD', '')),

config = None

if username[0] == '' or password[0 ]== '':
    print 'using clasical memcached'
    config = {'CACHE_TYPE': 'lib.MemcachedMultipart.multipartmemecached',
            'CACHE_MEMCACHED_SERVERS':servers}
else :
    print 'using sasl memcached'
    config = {'CACHE_TYPE': 'lib.MemcachedMultipart.multipartmemecached',
            'CACHE_MEMCACHED_SERVERS':servers,
            'CACHE_MEMCACHED_PASSWORD':password[0],
            'CACHE_MEMCACHED_USERNAME':username[0]
    }


# Cache configuration

second = 1
seconds = second
minute = 60
minutes = minute
hour = 60*minutes
hours = hour

# heroku dyno have 512 Mb Memory, more than memcache, let's use it.
cache = SimpleCache(threshold=100, default_timeout= 10*minutes)


# nbconvert converter configuration,
config = Config()
config.ConverterTemplate.template_file = 'basichtml'
config.NbconvertApp.fileext = 'html'
config.CSSHtmlHeaderTransformer.enabled = False

C = ConverterTemplate(config=config)



def cachedget(url, timeout, *args, **kwargs):
    """Fetch an url, and put the result in cache
    
    Fetch it from cache if already in it
    """

    value = cache.get(url)
    if value :
        return value
    try:
        # use async http client from tornado here
        r = requests.get(url)
    except Exception:
        #app.logger.error("Unhandled exception in request: %s" % url, exc_info=True)
        raise tornado.web.HTTPError(500)
    else:
        if r.status_code == 404:
            raise tornado.web.HTTPError(404)
        elif not r.ok:
            #app.logger.error("Failed request: %s" % (
            #    request_summary(r, header=True, content=app.debug)
            #))
            raise tornado.web.HTTPError(400)
    content = r.content

    try :
        cache.set(url, content)
    except Exception:
        pass

    return content


def request_summary(r, header=False, content=False):
    """text summary of failed request"""
    lines = [
        "%s %s: %i %s" % (
            r.request.method,
            r.url.split('?')[0],
            r.status_code,
            r.reason),
    ]
    if header:
        lines.extend([
        '--- HEADER ---',
        json.dumps(r.headers, indent=1),
        ])
    if content:
        lines.extend([
        '--- CONTENT ---',
        json.dumps(r.json, indent=1),
        ])
    return '\n'.join(lines)

def body_render(config, body):
    return env.get_template('notebook.html').render(
            body=body,
            download_url=config['download_url']
            )

def render_content(content, url=None, forced_theme=None):
    nb = nbformat.reads_json(content)

    css_theme = nb.get('metadata', {}).get('_nbviewer', {}).get('css', None)

    if css_theme and not re.match('\w', css_theme):
        css_theme = None

    if forced_theme and forced_theme != 'None' :
        css_theme = forced_theme

    config = {
            'download_url':url,
            'css_theme':css_theme,
            'mathjax_conf':None
            }
    return body_render(config, body=C.convert(nb)[0])


def github_api_request(url, callback):
    # try to get rid of sync requests here
    r = requests.get('https://api.github.com/%s' % url, params=g_config['GITHUB'])
    if not r.ok:
        #summary = request_summary(r, header=(r.status_code != 404), content=app.debug)
        #app.logger.error("API request failed: %s", summary)
        raise tornado.web.HTTPError(r.status_code if r.status_code == 404 else 400)
    return callback(r)




stupidcache = {}


class BaseHandler(tornado.web.RequestHandler):
    """A base handler to have custom error page
    """

    def write_error(self, status_code, **kwargs):
        short_description = httplib.responses.get(status_code, 'Unknown Error')
        self.write(env.get_template('errors.html').render(locals()))
        self.finish()


class NotFoundHandler(BaseHandler):
    """ A custom not Found handler

    Use to raise a custom 404 page if no url matches.
    """
    def get(self, *args, **kwargs):
        raise tornado.web.HTTPError(404)


faq = env.get_template('faq.md')
class FAQHandler(BaseHandler):
    def get(self):
        self.write(faq.render())


index = env.get_template('index.html')
class MainHandler(BaseHandler):
    def get(self):
        self.write(index.render())

class URLHandler(BaseHandler):

    def __init__(self, *args, **kwargs):
        self.https=kwargs.pop('https', False)
        super(URLHandler, self).__init__(*args, **kwargs)

    @asynchronous
    @gen.engine
    def get(self, url):

        url = ('https://' if self.https else 'http://')+url

        cached = stupidcache.get(url, None)
        should_finish =  True
        if cached is None:
            http_client = AsyncHTTPClient()
            content = yield gen.Task(http_client.fetch, url)
            if content.code == 404 : # not found
                if '/files/' in url:
                    new_url = url.replace('/files/', '/', 1)
                    self.redirect(new_url)
                    should_finish = False
                    #app.logger.info("redirecting nb local-files url: %s to %s" % (url, new_url))
                else :
                    raise tornado.web.HTTPError(404)
            else :
                cached = content.body
                stupidcache[url] = cached
        if should_finish:
            try :
                self.write(render_content(cached, url))
            except Exception:
                raise tornado.web.HTTPError(400)
            self.finish()


class GistHandler(BaseHandler):

    @asynchronous
    @gen.engine
    def get(self, id=None, subfile=None , **kwargs):
        """Fetch and render a gist from the Github API

        - Gist with only one file :
            try to render it as IPython notebook

        - If multifile:
            - No subfile set : show a list of files.

            - Subfile set:
                - try to render it as ipynb, or,
                - if it fails, return as raw file (text/plain).
        """
        if id is None:
            self.redirect('/')

        r = yield gen.Task(github_api_request, 'gists/{}'.format(id))
        try:
            decoded = r.json.copy()
            files = decoded['files'].values()
            if subfile :
                thefile = [f for f in files if f['filename'] == subfile]
                jsonipynb = thefile[0]['content']
                if subfile.endswith('.ipynb'):
                    tw =  render_content(jsonipynb, thefile[0]['raw_url'])
                else:
                    try:
                        tw = render_content(jsonipynb, thefile[0]['raw_url'])
                    except Exception:
                        tw = jsonipynb
                        self.set_header("Content-Type", "text/plain")

            elif len(files) == 1 :
                jsonipynb = files[0]['content']
                tw =  render_content(jsonipynb, files[0]['raw_url'])
            else:
                entries = []
                for file in files :
                    entry = {}
                    entry['path'] = file['filename']
                    entry['url'] = '/%s/%s' % (id, file['filename'])
                    entries.append(entry)
                tw = env.get_template('gistlist.html').render(entries=entries)
        except ValueError:
            #app.logger.error("Failed to render gist: %s" % request_summary(r), exc_info=True)
            raise tornado.web.HTTPError(400)
        #except Exception as e:

            #app.logger.error("Unhandled error rendering gist: %s" % request_summary(r), exc_info=True)
        #    raise tornado.web.HTTPError(500)
        self.write(tw)
        self.finish()

class CreateHandler(BaseHandler):
    def post(self, v=None):
        value = self.get_argument('gistnorurl', '')

        if v and not value:
            value = v
        gist = re.search(r'^https?://gist.github.com/(\w+/)?([a-f0-9]+)$', value)
        if re.match('^[a-f0-9]+$', value):
            self.redirect('/'+value)
        elif gist:
            self.redirect('/'+gist.group(2))
        elif value.startswith('https://'):
            self.redirect('/urls/'+value[8:])
        elif value.startswith('http://'):
            self.redirect('/url/'+value[7:])
        else:
            # default is to assume http url
            self.redirect('/url/'+value)
