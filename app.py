import os
from flask import Flask , request
import nbconvert.nbconvert as nbconvert
import requests
from nbformat import current as nbformat
from flask import Flask, redirect, abort
import re

app = Flask(__name__)

@app.route('/')
def hello():
    return open('static/index.html').read()


@app.route('/assets/<path:path>', methods=['GET'])
def sitemap(path):
    return open('static/assets/'+path).read()


@app.errorhandler(404)
def page_not_found(error):
    return "OHNO ! it cannot be found !" 
    #return render_template('page_not_found.html'), 404

@app.route('/create/',methods=['POST'])
def login():
    value = request.form['gistnorurl']
    if re.match('^[0-9]+$',value):
        return redirect('/'+value)
    
    gist = re.search(r'^https?://gist.github.com/([0-9]+)$',value)
    if gist:
        return redirect('/'+gist.group(1))

    if value.startswith('https://'):
        return redirect('/urls/'+value[8:])

    if value.startswith('http://'):
        return redirect('/urls/'+value[7:])

    return "don't now how to access this ipynb file..."

#https !
@app.route('/urls/<path:url>')
def render_urls(url):
    try:
        r = requests.get('https://'+url)

        if r.status_code != 200:
            return None
        print 'will init converter'
        converter = nbconvert.ConverterHTML()
        print 'will set json'
        converter.nb = nbformat.reads_json(r.content)
        print 'will convert'
        result = converter.convert()
        print 'will return'
        return result
    except ValueError :
        abort(501)
        
#http ! 
@app.route('/url/<path:url>')
def render_url(url):
    try:
        r = requests.get('http://'+url)

        if r.status_code != 200:
            return None

        converter = nbconvert.ConverterHTML()
        converter.nb = nbformat.reads_json(r.content)
        result = converter.convert()
        return result
    except ValueError :
        abort(501)

@app.route('/<int:id>')
def fetch_and_render(id):
    """Fetch and render a post from the Github API"""
    r = requests.get('https://api.github.com/gists/{}'.format(id))

    if r.status_code != 200:
        return None
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
    app.run(host='0.0.0.0', port=port)
