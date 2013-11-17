#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import os

from tornado import web, httpserver, ioloop, log
from tornado.httpclient import AsyncHTTPClient

import tornado.options
from tornado.options import define, options

from jinja2 import Environment, FileSystemLoader

from IPython.config import Config
from IPython.nbconvert.exporters import HTMLExporter

from .handlers import handlers, CustomErrorHandler
from .github import AsyncGitHubClient

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

here = os.path.dirname(__file__)
pjoin = os.path.join

def nrhead():
    try:
        import newrelic.agent
    except ImportError:
        return ''
    return newrelic.agent.get_browser_timing_header()

def nrfoot():
    try:
        import newrelic.agent
    except ImportError:
        return ''
    return newrelic.agent.get_browser_timing_footer()

def main():
    """docstring for main"""
    define("port", default=5000, help="run on the given port", type=int)
    tornado.options.parse_command_line()
    
    config = Config()
    config.HTMLExporter.template_file = 'basic'
    config.NbconvertApp.fileext = 'html'
    config.CSSHTMLHeaderTransformer.enabled = False
    # don't strip the files prefix - we use it for redirects
    config.Exporter.filters = {'strip_files_prefix': lambda s: s}

    exporter = HTMLExporter(config=config)
    
    web.ErrorHandler = CustomErrorHandler
    template_path = pjoin(here, 'templates')
    static_path = pjoin(here, 'static')
    env = Environment(loader=FileSystemLoader(template_path))
    env.globals.update(nrhead=nrhead, nrfoot=nrfoot)
    client = AsyncHTTPClient()
    github_client = AsyncGitHubClient(client)
    github_client.authenticate()
    
    settings = dict(
        jinja2_env=env,
        static_path=static_path,
        client=client,
        github_client=github_client,
        exporter=exporter,
    )
    app = web.Application(handlers, **settings)
    http_server = httpserver.HTTPServer(app)
    log.app_log.info("Listing on port %i", options.port)
    http_server.listen(options.port)
    ioloop.IOLoop.instance().start()
    

if __name__ == '__main__':
    main()