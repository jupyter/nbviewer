from gist import app as gist
from githubapp import app as github
import os

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    debug = os.path.exists('.debug')
    debug = True
    print 'url scheme' , os.environ.get('URL_SCHEME', None)
    if debug :
        print 'DEBUG MODE IS ACTIVATED !!!'
    else :
        print 'debug is not activated'
    github.run(host='0.0.0.0', port=port, debug=debug)
