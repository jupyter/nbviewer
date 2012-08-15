import os
from flask import Flask , request, render_template
import nbconvert.nbconvert as nbconvert
import requests
from nbformat import current as nbformat
from flask import Flask, redirect, abort
import re

app = Flask(__name__)


def static(strng) :
    return open('static/'+strng).read()

@app.route('/')
def hello():
    return static('index.html')


@app.route('/assets/<path:path>', methods=['GET'])
def sitemap(path):
    return open('static/assets/'+path).read()


@app.errorhandler(500)
def page_not_found(error):
    return static('500.html'),500

@app.errorhandler(404)
def page_not_found(error):
    return static('404.html'),404

@app.route('/404')
def four_o_foru():
    abort(404)

@app.route('/500')
def four_o_foru():
    abort(500)

@app.route('/create/',methods=['POST'])
def create(v=None):
    value = request.form['gistnorurl']
    if v and not value:
        value = v
    if re.match('^[0-9]+$',value):
        return redirect('/'+value)
    gist = re.search(r'^https?://gist.github.com/([0-9]+)$',value)
    if gist:
        return redirect('/'+gist.group(1))
    if value.startswith('https://') and value.endswith('.ipynb'):
        return redirect('/urls/'+value[8:])

    if value.startswith('http://') and value.endswith('.ipynb'):
        return redirect('/url/'+value[7:])

    return static('unknown_filetype.html')

#https !
@app.route('/urls/<path:url>')
def render_urls(url):
    try :
        r = requests.get('https://'+url)
    except Exception as e :
        abort(404)
    return(render_request(r))

#http !
@app.route('/url/<path:url>')
def render_url(url):
    try :
        r = requests.get('http://'+url)
    except Exception as e :
        abort(404)

    return(render_request(r))


def render_request(r):
    try:
        if r.status_code != 200:
            abort(404)
        converter = nbconvert.ConverterHTML()
        converter.nb = nbformat.reads_json(r.content)
        result = converter.convert()
        return result
    except  :
        abort(404)


@app.route('/<int:id>')
def fetch_and_render(id):
    """Fetch and render a post from the Github API"""
    r = requests.get('https://api.github.com/gists/{}'.format(id))

    if r.status_code != 200:
        return None

    decoded = r.json.copy()
    files = decoded['files'].values()
    if len(files) > 1:
        return file_listing(id, files)    

    file = files[0]
    return render_file(file, decoded)


@app.route('/<int:id>/<string:filename>')
def fetch_file(id, filename):
    """Fetch and render a post from the Github API"""
    r = requests.get('https://api.github.com/gists/{}'.format(id))

    if r.status_code != 200:
        return None
    try :
        decoded = r.json.copy()
        files = decoded['files'].values()
        for f in files:
            if f['filename'] == filename:
                return render_file(f, decoded)
        abort(404)
    except ValueError as e :
        abort(404)

    return result

def file_listing(gist_id, files):
    links = []
    for file in files:
        fn = file['filename']
        link = '<a href="/{0}/{1}">{2}</a>'.format(gist_id, fn, fn)
        links.append(link)

    return '<h2>Files in Gist</h2>'+'<br />'.join(links)

RECENT_FILES = []

@app.route('/recent_files')
def recent_files():
    return str(RECENT_FILES)


def render_file(file, decoded):
    """Fetch and render a post from the Github API"""
    try :
        jsonipynb = file['content']
        RECENT_FILES.append((file['filename'], decoded['description'], decoded['html_url']))
        print RECENT_FILES

        converter = nbconvert.ConverterHTML()
        converter.nb = nbformat.reads_json(jsonipynb)
        result = converter.convert()
    except ValueError as e :
        abort(404)

    return result

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5005))
    debug = os.path.exists('.debug')
    if debug :
        print 'DEBUG MODE IS ACTIVATED !!!'
    else :
        print 'debug is not activated'
    app.run(host='0.0.0.0', port=port, debug=debug)
