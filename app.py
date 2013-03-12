import os
import sys
import logging

from gist import app as gist
from gist import MainHandler, URLHandler, FAQHandler, GistHandler
#from githubapp import app as github

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
import tornado.web


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
    
    application = tornado.web.Application([
        (r"/", MainHandler),
        # planed url
        (r'/faq/?',FAQHandler),
        #(r'/create/',,),
        #(r'/<gistnumber>(/<subfile>)?',,),
        #(r'/login/?',,), ?
        #(r'/github/*',,),
        #(r'/preferences',,),
        #(r'',,),
        #(r'',,),
        (r'/url/(.*)', URLHandler ),
        (r'/urls/(.*)', URLHandler, {'https':True} ),
        (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static/'}),
        (r'/(?P<_>(?P<user>[a-zA-Z0-9]+)/)?(?P<id>[a-f0-9]+)$',GistHandler),
    ],
    debug=True
    )

    application.listen(port)
    IOLoop.instance().start()
    #gist.run(host='0.0.0.0', port=port, debug=debug)

