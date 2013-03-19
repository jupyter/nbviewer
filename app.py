import os
import sys
import logging

from gist import *
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
    
    
    
    application = tornado.web.Application([
        (r"/", MainHandler),
        # planed url
        (r'/faq/?',FAQHandler),
        (r'/create/?',CreateHandler),
        #(r'/<gistnumber>(/<subfile>)?',,),
        #(r'/login/?',,), ?
        #(r'/github/*',,),
        #(r'/preferences',,),
        #(r'',,),
        #(r'',,),
        (r'/url/(.*)', URLHandler ),
        (r'/urls/(.*)', URLHandler, {'https':True} ),
        (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static/'}),
        # match <username>/<gistnumber>/<subfile>
        # with <username> and <subfile> optionnal
        (r'/(?P<_>(?P<user>[a-zA-Z0-9]+)/)?(?P<id>[a-f0-9]+)(?P<__>/(?P<subfile>.*))?$',GistHandler),
        (r'/(.*)$',NotFoundHandler),
    ],
    debug=debug
    )

    #if not debug:
    #    log_level = getattr(logging, os.environ.get('LOG_LEVEL', 'WARN'))
    #    application.logger.setLevel(log_level)
    #    handler = logging.StreamHandler(sys.stderr)
    #    handler.setLevel(log_level)
    #    handler.setFormatter(logging.Formatter(
    #        '[%(asctime)s] %(levelname)s: %(message)s '
    #    ))
    #    application.logger.addHandler(handler)
    #    application.logger.addHandler(logging.StreamHandler())

    application.listen(port)
    IOLoop.instance().start()

