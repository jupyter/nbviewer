import os
import re
import requests

from nbformat import current as nbformat
import nbconvert.nbconvert as nbconvert

from flask import Flask , request, render_template
from flask import redirect, abort, Response

from statistics import Stats
from sqlalchemy import create_engine

from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug.routing import BaseConverter

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

engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], echo=False)
stats = Stats(engine)

try :
    import pylibmc
    mc = pylibmc.Client(["127.0.0.1"], binary=True,
                    behaviors={"tcp_nodelay": True,
                                "ketama": True})

    def cachedfirstparam(function):

        def wrapper(*args, **kw):
            if len(args)+len(kw) != 1:
               return function(*args, **kw)
            else :
                key = kw.values()[0] if kw else args[0]
                skey = str(key)+str(function.__name__)
                mcv = mc.get(skey)
                #mcv = None
                if mcv :
                    return mcv
                else :
                    value = function(key)
                    mc.set(skey, value, time=600)
                    return value
        return wrapper

except :
    def cachedfirstparam(fun):
        return fun

@cachedfirstparam
def static(strng) :
    return open('static/'+strng).read()

@app.route('/')
def hello():
    nvisit = int(request.cookies.get('rendered_urls',0))
    betauser = (True if nvisit > 30 else False)
    return render_template('index.html', betauser=betauser)

@app.errorhandler(400)
def page_not_found(error):
    return render_template('400.html'), 400

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500


@app.route('/popular')
def popular():
    entries = [{'url':y.url,'count':x} for x,y in stats.most_accessed(count=20)]
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
    nvisit = int(request.cookies.get('rendered_urls',0))
    response.set_cookie('rendered_urls',value=nvisit+1)
    return response

#https !
@cachedfirstparam
def cachedget(url):
    try:
        r = requests.get(url)
    except Exception:
        app.logger.error("Unhandled exception in request: %s" % (
                request_summary(r)
        ), exc_info=True)
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



@cachedfirstparam
@app.route('/urls/<path:url>')
def render_urls(url):
    try:
        stats.get('urls/'+url).access()
    except Exception:
        app.logger.error("exception getting stats", exc_info=True)
    url = 'https://' + url
    content = cachedget(url)
    try:
        return render_content(content, url)
    except Exception:
        app.logger.error("Couldn't render notebook from %s" % url, exc_info=True)
        abort(400)

#http !
@cachedfirstparam
@app.route('/url/<path:url>')
def render_url(url):
    stats.get('url/'+url).access()
    url = 'http://'+url
    content = cachedget(url)
    try:
        return render_content(content, url)
    except Exception:
        app.logger.error("Couldn't render notebook from %s" % url, exc_info=True)
        abort(400)


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
    

other_views = """<div style="position:absolute; right:1em; top:1em; padding:0.4em; border:1px dashed black;">
  <a href="{url}">Download notebook</a>
</div>"""

def render_content(content, url=None):
    converter = nbconvert.ConverterHTML()
    if url:
        converter.extra_body_start_html = other_views.format(url=url)
    converter.nb = nbformat.reads_json(content)
    return converter.convert()

def github_api_request(url):
    r = requests.get('https://api.github.com/%s' % url, params=app.config['GITHUB'])
    if not r.ok:
        summary = request_summary(r, header=(r.status_code != 404), content=app.debug)
        app.logger.error("API request failed: %s", summary)
        abort(r.status_code if r.status_code == 404 else 400)
    return r

@cachedfirstparam
@app.route('/<regex("[a-f0-9]+"):id>')
def fetch_and_render(id=None):
    """Fetch and render a post from the Github API"""
    if id is None:
        return redirect('/')
    try :
        stats.get(id).access()
    except :
        print 'oops ', id, 'crashed'

    r = github_api_request('gists/{}'.format(id))

    try:
        decoded = r.json.copy()
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
    except ValueError:
        app.logger.error("Failed to render gist: %s" % request_summary(r), exc_info=True)
        abort(400)
    except:
        app.logger.error("Unhandled error rendering gist: %s" % request_summary(r), exc_info=True)
        abort(500)

    return result


@app.route('/<int:id>/<subfile>')
def gistsubfile(id, subfile):
    """Fetch and render a post from the Github API"""

    r = github_api_request('gists/{}'.format(id))

    try:
        decoded = r.json.copy()
        files = decoded['files'].values()
        thefile = [f for f in files if f['filename'] == subfile]
        jsonipynb = thefile[0]['content']
        if subfile.endswith('.ipynb'):
            return render_content(jsonipynb, thefile[0]['raw_url'])
        else:
            return Response(jsonipynb, mimetype='text/plain')
    except ValueError:
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
