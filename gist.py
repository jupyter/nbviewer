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

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']

db = SQLAlchemy(app)

#engine = create_engine('sqlite:///foo.db', echo=False)
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], echo=False)
stat = Stats(engine)

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

    print('user has rendered {n} urls'.format(n=nvisit))
    return render_template('index.html', betauser=betauser)


@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.route('/404')
def four_o_foru():
    abort(404)

@app.route('/500')
def fiveoo():
    abort(500)

@app.route('/create/', methods=['POST'])
def create(v=None):
    value = request.form['gistnorurl']

    response = None
    increasegen = False
    if v and not value:
        value = v
    gist = re.search(r'^https?://gist.github.com/([0-9]+)$', value)
    if re.match('^[0-9]+$', value):
        response = redirect('/'+value)
    elif gist:
        response = redirect('/'+gist.group(1))
        
    elif value.startswith('https://') and value.endswith('.ipynb'):
        response = redirect('/urls/'+value[8:])

    elif value.startswith('http://') and value.endswith('.ipynb'):
        response = redirect('/url/'+value[7:])
    else :
        response = render_template('unknown_filetype.html')

    response = app.make_response(response)
    nvisit = int(request.cookies.get('rendered_urls',0))
    response.set_cookie('rendered_urls',value=nvisit+1)
    return response

#https !
@cachedfirstparam
def cachedget(url):
    try :
        r = requests.get(url)
        if r.status_code is not 200 :
            abort(404)
        return r.content
    except Exception :
        abort(404)



@cachedfirstparam
@app.route('/urls/<path:url>')
def render_urls(url):
    stat.get(url).access()
    content = cachedget('https://'+url)
    return render_content(content)

#http !
@cachedfirstparam
@app.route('/url/<path:url>')
def render_url(url):
    stat.get(url).access()
    content = cachedget('http://'+url)
    return render_content(content)


@cachedfirstparam
def render_request(r=None):
    try:
        if r.status_code != 200:
            abort(404)
        return render_content(r.content)
    except  :
        abort(404)

def render_content(content):
    converter = nbconvert.ConverterHTML()
    converter.nb = nbformat.reads_json(content)
    return converter.convert()


@cachedfirstparam
@app.route('/<int:id>/')
def fetch_and_render(id=None):
    """Fetch and render a post from the Github API"""
    if id is None :
        return redirect('/')

    r = requests.get('https://api.github.com/gists/{}'.format(id))

    if r.status_code != 200:
        abort(404)
    try :
        decoded = r.json.copy()
        files = decoded['files'].values()
        if len(files) == 1 :
            jsonipynb = files[0]['content']
            converter = nbconvert.ConverterHTML()
            converter.nb = nbformat.reads_json(jsonipynb)
            result = converter.convert()
        else :
            entries = []
            for file in files :
                entry = {}
                entry['path'] = file['filename']
                entry['url'] = '/%s/%s' %( id,file['filename'])
                entries.append(entry)
            return render_template('gistlist.html', entries=entries)
    except ValueError as e :
        abort(404)

    return result


@app.route('/<int:id>/<subfile>')
def gistsubfile(id, subfile):
    """Fetch and render a post from the Github API"""

    r = requests.get('https://api.github.com/gists/{}'.format(id))

    if r.status_code != 200:
        abort(404)
    try :
        decoded = r.json.copy()
        files = decoded['files'].values()
        thefile = [f for f in files if f['filename'] == subfile]
        jsonipynb = thefile[0]['content']
        if subfile.endswith('.ipynb'):
            return render_content(jsonipynb)
        else :
            return Response(jsonipynb, mimetype='text/plain')
    except ValueError as e :
        abort(404)

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    debug = os.path.exists('.debug')
    if debug :
        print 'DEBUG MODE IS ACTIVATED !!!'
    else :
        print 'debug is not activated'
    app.run(host='0.0.0.0', port=port, debug=debug)
