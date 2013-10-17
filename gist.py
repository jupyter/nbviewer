import os
import re
import requests
import json

from IPython.nbformat import current as nbformat

from IPython.nbconvert.exporters import HTMLExporter

from flask import Flask , request, render_template
from flask import redirect, abort, Response
from requests.exceptions import RequestException, Timeout

from werkzeug.routing import BaseConverter
from werkzeug.exceptions import NotFound

from flask.ext.cache import Cache
from flaskext.markdown import Markdown

from lib.MemcachedMultipart import multipartmemecached


class RegexConverter(BaseConverter):
    """regex route filter

    from: http://stackoverflow.com/questions/5870188
    """
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]

app = Flask(__name__)
Markdown(app)
app.url_map.converters['regex'] = RegexConverter
app.url_map.strict_slashes = False

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite://')
app.config['GITHUB'] = {
    'client_id': os.environ.get('GITHUB_OAUTH_KEY', ''),
    'client_secret': os.environ.get('GITHUB_OAUTH_SECRET', ''),
}



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
config.HTMLExporter.template_file = 'basic'
config.NbconvertApp.fileext = 'html'
config.CSSHTMLHeaderTransformer.enabled = False
# don't strip the files prefix - we use it for redirects
config.Exporter.filters = {'strip_files_prefix': lambda s: s}

C = HTMLExporter(config=config)

minutes = 60
hours = 60*minutes

import newrelic.agent

def nrhead():
    return newrelic.agent.get_browser_timing_header()

def nrfoot():
    return newrelic.agent.get_browser_timing_footer()

app.jinja_env.globals.update(nrhead=nrhead, nrfoot=nrfoot)

def static(strng):
    return open('static/'+strng).read()

@app.route('/favicon.ico')
@cache.cached(5*hours)
def favicon():
    return static('ico/ipynb_icon_16x16.ico')

@app.route('/')
def hello():
    nvisit = int(request.cookies.get('rendered_urls', 0))
    betauser = (True if nvisit > 30 else False)
    theme = request.cookies.get('theme', None)

    response = _hello(betauser)

    if(theme):
        response.set_cookie('theme', value=theme)
    return response

@cache.cached(5*hours)
def _hello(betauser):
    return app.make_response(render_template('index.html', betauser=betauser))

@app.route('/faq')
#@cache.cached(5*hours)
def faq():
    return render_template('faq.md')

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


#@app.route('/popular')
@cache.cached(1*minutes)
def popular():
    entries = [{'url':y.url, 'count':x} for x, y in stats.most_accessed(count=20)]
    return render_template('popular.html', entries=entries)

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
    response.set_cookie('rendered_urls', value=str(nvisit+1))
    return response

#https !
@cache.memoize()
def cachedget(url):
    try:
        r = requests.get(url, timeout=8)
    except RequestException as e:
        app.logger.error("Error (%s) in request: %s" % (e, url), exc_info=False)
        abort(400)
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

def uc_render_url_urls(url, https=False):
    forced_theme = request.cookies.get('theme', None)
    return render_url_urls(url, https, forced_theme=forced_theme)

@cache.memoize(10*minutes)
def render_url_urls(url, https, forced_theme=None):

    url = ('https://' + url) if https else ('http://' + url)

    try:
        content = cachedget(url)
    except NotFound:
        if '/files/' in url:
            new_url = url.replace('/files/', '/', 1)
            app.logger.info("redirecting nb local-files url: %s to %s" % (url, new_url))
            return redirect(new_url)
        else:
            raise

    try:
        return render_content(content, url, forced_theme)
    except NbFormatError:
        app.logger.error("Couldn't render notebook from %s" % url, exc_info=False)
        abort(400)
    except Exception:
        app.logger.error("Couldn't render notebook from %s" % url, exc_info=True)
        abort(400)



@app.route('/url/<path:url>')
def render_url(url):
    return uc_render_url_urls(url, https=False)

@app.route('/urls/<path:url>')
def render_urls(url):
    return uc_render_url_urls(url, https=True)

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
        json.dumps(r.json(), indent=1),
        ])
    return '\n'.join(lines)

def body_render(config, body):
    return render_template('notebook.html', body=body, **config)

class NbFormatError(Exception):
    pass

def render_content(content, url=None, forced_theme=None):
    try :
        nb = nbformat.reads_json(content)
    except ValueError:
        raise NbFormatError('Error reading json notebook')


    css_theme = nb.get('metadata', {}).get('_nbviewer', {}).get('css', None)

    if css_theme and not re.match('\w', css_theme):
        css_theme = None

    if forced_theme and forced_theme != 'None' :
        css_theme = forced_theme

    # get the notebook title
    try:
        name = nb.metadata.name
    except AttributeError:
        name = None
    
    if not name:
        name = url.rsplit('/')[-1]

    if not name.endswith(".ipynb"):
        name = name + ".ipynb"

    config = {
            'download_url': url,
            'download_name': name,
            'css_theme': css_theme,
            'mathjax_conf': None,
            }
    return body_render(config, body=C.from_notebook_node(nb)[0])


def github_api_request(url):
    r = requests.get('https://api.github.com/%s' % url, params=app.config['GITHUB'])
    if not r.ok:
        summary = request_summary(r, header=(r.status_code != 404), content=app.debug)
        app.logger.error("API request failed: %s", summary)
        abort(r.status_code if r.status_code == 404 else 400)
    return r

@app.route('/<regex("[a-f0-9]+"):id>')
def fetch_and_render(id=None):
    """Fetch and render a post from the Github API"""
    if id is None:
        return redirect('/')

    r = github_api_request('gists/{}'.format(id))

    try:
        decoded = r.json().copy()
        files = decoded['files'].values()
        if len(files) == 1 :
            jsonipynb = files[0]['content']
            return render_content(jsonipynb, files[0]['raw_url'])
        else:
            entries = []
            for file in files :
                entry = {}
                entry['path'] = file['filename']
                entry['url'] = '/%s/%s' % (id, file['filename'])
                entries.append(entry)
            return render_template('gistlist.html', entries=entries)
    except NbFormatError:
        app.logger.error("Failed to render gist: %s" % request_summary(r), exc_info=True)
        abort(400)
    except:
        app.logger.error("Unhandled error rendering gist: %s" % request_summary(r), exc_info=True)
        abort(500)

    return result


@app.route('/<regex("[a-f0-9]+"):id>/<subfile>')
def gistsubfile(id, subfile):
    """Fetch and render a post from the Github API"""

    r = github_api_request('gists/{}'.format(id))

    try:
        decoded = r.json().copy()
        files = decoded['files'].values()
        thefile = [f for f in files if f['filename'] == subfile]
        jsonipynb = thefile[0]['content']
        if subfile.endswith('.ipynb'):
            return render_content(jsonipynb, thefile[0]['raw_url'])
        else:
            return Response(jsonipynb, mimetype='text/plain')
    except NbFormatError:
        app.logger.error("Failed to render gist: %s" % request_summary(r), exc_info=True)
        abort(400)
    except:
        app.logger.error("Unhandled error rendering gist: %s" % request_summary(r), exc_info=True)
        abort(500)

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    debug = os.path.exists('.debug')
    if debug :
        print 'DEBUG MODE IS ACTIVATED !!!'
    else :
        print 'debug is not activated'
    app.run(host='0.0.0.0', port=port, debug=debug)
