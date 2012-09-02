import os
from flask import Flask , request, render_template
import nbconvert.nbconvert as nbconvert
import requests
from nbformat import current as nbformat
from flask import Flask, redirect, abort
import re

app = Flask(__name__)

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
    return render_template('index.html')


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
def four_o_foru():
    abort(500)

@app.route('/create/', methods=['POST'])
def create(v=None):
    value = request.form['gistnorurl']
    if v and not value:
        value = v
    if re.match('^[0-9]+$', value):
        return redirect('/'+value)
    gist = re.search(r'^https?://gist.github.com/([0-9]+)$', value)
    if gist:
        return redirect('/'+gist.group(1))
    if value.startswith('https://') and value.endswith('.ipynb'):
        return redirect('/urls/'+value[8:])

    if value.startswith('http://') and value.endswith('.ipynb'):
        return redirect('/url/'+value[7:])

    return render_template('unknown_filetype.html')

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
    content = cachedget('https://'+url)
    return render_content(content)

#http !
@cachedfirstparam
@app.route('/url/<path:url>')
def render_url(url):
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
@app.route('/<int:id>')
def fetch_and_render(id=None):
    """Fetch and render a post from the Github API"""
    if id is None :
        return redirect('/')

    r = requests.get('https://api.github.com/gists/{}'.format(id))

    if r.status_code != 200:
        abort(404)
    try :
        decoded = r.json.copy()
        jsonipynb = decoded['files'].values()[0]['content']

        converter = nbconvert.ConverterHTML()
        converter.nb = nbformat.reads_json(jsonipynb)
        result = converter.convert()
    except ValueError as e :
        abort(404)

    return result

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    debug = os.path.exists('.debug')
    if debug :
        print 'DEBUG MODE IS ACTIVATED !!!'
    else :
        print 'debug is not activated'
    app.run(host='0.0.0.0', port=port, debug=debug)
