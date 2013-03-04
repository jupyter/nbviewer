import os
import sys
import logging

from gist import app as gist
#from githubapp import app as github

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    debugfile = os.path.exists('.debug')
    debugenv = os.environ.get('DEBUG', '')
    debug = debugfile or debugenv
    print 'url scheme' , os.environ.get('URL_SCHEME', 'gist')
    if debug:
        print 'DEBUG MODE IS ACTIVATED !!!'

    urlscheme = os.environ.get('URLSCHEME', 'GIST')
    
    if not debug:
        log_level = getattr(logging, os.environ.get('LOG_LEVEL', 'WARN'))
        gist.logger.setLevel(log_level)
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(log_level)
        handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s '
        ))
        gist.logger.addHandler(handler)
        # gist.logger.addHandler(logging.StreamHandler())
    
    http_server = HTTPServer(WSGIContainer(gist))
    http_server.listen(port)
    IOLoop.instance().start()
    #gist.run(host='0.0.0.0', port=port, debug=debug)
