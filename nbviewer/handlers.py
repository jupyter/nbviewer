#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------
from tornado import web
from tornado.log import app_log

from notebook import DEFAULT_STATIC_FILES_PATH as ipython_static_path

from .utils import transform_ipynb_uri

from .providers import (
    provider_handlers,
    provider_uri_rewrites,
)
from .providers.base import (
    BaseHandler,
    format_prefix,
)

#-----------------------------------------------------------------------------
# Handler classes
#-----------------------------------------------------------------------------

class Custom404(BaseHandler):
    """Render our 404 template"""
    def prepare(self):
        raise web.HTTPError(404)


class IndexHandler(BaseHandler):
    """Render the index"""
    def get(self):
        self.finish(self.render_template('index.html', sections=self.frontpage_sections))


class FAQHandler(BaseHandler):
    """Render the markdown FAQ page"""
    def get(self):
        self.finish(self.render_template('faq.md'))


class CreateHandler(BaseHandler):
    """handle creation via frontpage form

    only redirects to the appropriate URL
    """
    uri_rewrite_list = None

    def post(self):
        value = self.get_argument('gistnorurl', '')
        redirect_url = transform_ipynb_uri(value, self.get_provider_rewrites())
        app_log.info("create %s => %s", value, redirect_url)
        self.redirect(redirect_url)

    def get_provider_rewrites(self):
        # storing this on a class attribute is a little icky, but is better
        # than the global this was refactored from.
        if self.uri_rewrite_list is None:
            # providers is a list of module import paths
            providers = self.settings['provider_rewrites']

            type(self).uri_rewrite_list = provider_uri_rewrites(providers)
        return self.uri_rewrite_list


#-----------------------------------------------------------------------------
# Default handler URL mapping
#-----------------------------------------------------------------------------

def format_handlers(formats, handlers):
    return [
        (prefix + url, handler, {
            "format": format,
            "format_prefix": prefix
        })
        for format in formats
        for url, handler in handlers
        for prefix in [format_prefix + format]
    ]


def init_handlers(formats, providers):
    pre_providers = [
        ('/', IndexHandler),
        ('/index.html', IndexHandler),
        (r'/faq/?', FAQHandler),
        (r'/create/?', CreateHandler),
        (r'/ipython-static/(.*)', web.StaticFileHandler, dict(path=ipython_static_path)),

        # don't let super old browsers request data-uris
        (r'.*/data:.*;base64,.*', Custom404),
    ]

    post_providers = [
        (r'/(robots\.txt|favicon\.ico)', web.StaticFileHandler),
        (r'.*', Custom404),
    ]

    handlers = provider_handlers(providers)

    return (
        pre_providers +
        handlers +
        format_handlers(formats, handlers) +
        post_providers
    )
