import os
import re
import requests
import json
from nbformat import current as nbformat

from nbconvert2.converters.template import ConverterTemplate

from flask import Flask , request, render_template
from flask import redirect, abort, Response

from sqlalchemy import create_engine

from werkzeug.routing import BaseConverter
from werkzeug.exceptions import NotFound

from flask.ext.cache import Cache


import jinja2
import markdown

def safe_markdown(text):
    return jinja2.Markup(markdown.markdown(text))


from lib.MemcachedMultipart import multipartmemecached

import tornado.web
from jinja2 import Environment, FileSystemLoader


class RegexConverter(BaseConverter):
    """regex route filter

    from: http://stackoverflow.com/questions/5870188
    """
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]

app = Flask(__name__)
app.url_map.converters['regex'] = RegexConverter

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite://')
app.config['GITHUB'] = {
    'client_id': os.environ.get('GITHUB_OAUTH_KEY', ''),
    'client_secret': os.environ.get('GITHUB_OAUTH_SECRET', ''),
}


env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")))
env.filters['markdown'] = safe_markdown

servers = os.environ.get('MEMCACHIER_SERVERS', '127.0.0.1'),
username = str(os.environ.get('MEMCACHIER_USERNAME', '')),
password = str(os.environ.get('MEMCACHIER_PASSWORD', '')),
config = None


if username[0] == '' or password[0]== '':
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

cache = Cache(app, config=config)


from IPython.config import Config
config = Config()
config.ConverterTemplate.template_file = 'basichtml'
config.NbconvertApp.fileext = 'html'
config.CSSHtmlHeaderTransformer.enabled = False

C = ConverterTemplate(config=config)

minutes = 60
hours = 60*minutes


def static(strng):
    return open('static/'+strng).read()

@app.route('/favicon.ico')
@cache.cached(5*hours)
def favicon():
    return static('ico/ipynb_icon_16x16.ico')

@app.errorhandler(400)
@cache.cached(5*hours)
def page_not_found(error):
    return render_template('400.html'), 400

@app.errorhandler(404)
@cache.cached(5*hours)
def page_not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
@cache.cached(5*hours)
def internal_error(error):
    return render_template('500.html'), 500


@app.route('/404')
def four_o_four():
    abort(404)

@app.route('/400')
def four_hundred():
    abort(400)

@app.route('/500')
def five_hundred():
    abort(500)

@app.route('/create/', methods=['POST'])
def create(v=None):
    value = request.form['gistnorurl']

    response = None
    increasegen = False
    if v and not value:
        value = v
    gist = re.search(r'^https?://gist.github.com/(\w+/)?([a-f0-9]+)$', value)
    if re.match('^[a-f0-9]+$', value):
        response = redirect('/'+value)
    elif gist:
        response = redirect('/'+gist.group(2))
    elif value.startswith('https://'):
        response = redirect('/urls/'+value[8:])
    elif value.startswith('http://'):
        response = redirect('/url/'+value[7:])
    else:
        # default is to assume http url
        response = redirect('/url/'+value)

    response = app.make_response(response)
    nvisit = int(request.cookies.get('rendered_urls', 0))
    response.set_cookie('rendered_urls', value=nvisit+1)
    return response

#https !
#@cache.memoize()
def cachedget(url):
    try:
        r = requests.get(url)
    except Exception:
        app.logger.error("Unhandled exception in request: %s" % url, exc_info=True)
        abort(500)
    else:
        if r.status_code == 404:
            abort(404)
        elif not r.ok:
            app.logger.error("Failed request: %s" % (
                request_summary(r, header=True, content=app.debug)
            ))
            abort(400)
    return r.content


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
    return env.get_template('notebook.html').render(body=body)

def render_content(content, url=None, forced_theme=None):
    nb = nbformat.reads_json(content)

    css_theme = nb.get('metadata', {}).get('_nbviewer', {}).get('css', None)

    if css_theme and not re.match('\w', css_theme):
        css_theme = None

    if forced_theme and forced_theme != 'None' :
        css_theme = forced_theme

    #body=C.convert(nb)[0],
    config = {
            'download_url':url,
            'css_theme':css_theme,
            'mathjax_conf':None
            }
    return body_render(config, body=C.convert(nb)[0])


def github_api_request(url):
    r = requests.get('https://api.github.com/%s' % url, params=app.config['GITHUB'])
    if not r.ok:
        summary = request_summary(r, header=(r.status_code != 404), content=app.debug)
        app.logger.error("API request failed: %s", summary)
        abort(r.status_code if r.status_code == 404 else 400)
    return r



from tornado.web import asynchronous
from tornado.httpclient import AsyncHTTPClient
from tornado import gen

stupidcache = {}

class BaseHandler(tornado.web.RequestHandler):

    def write_error(self, status_code, **kwargs):
        self.write(env.get_template('errors.html').render(locals()))
        self.finish()

class FAQHandler(BaseHandler):
    def get(self):
        self.write(env.get_template('faq.md').render())

class MainHandler(BaseHandler):
    def get(self):
        self.write(env.get_template('index.html').render())

class URLHandler(BaseHandler):

    def __init__(self, *args, **kwargs):
        self.https=kwargs.pop('https',False)
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
                    raise
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
            return redirect('/')

        r = github_api_request('gists/{}'.format(id))
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
            abort(400)
        #except Exception as e:

            #app.logger.error("Unhandled error rendering gist: %s" % request_summary(r), exc_info=True)
        #    abort(500)
        self.write(tw)
        self.finish()
