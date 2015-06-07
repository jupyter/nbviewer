from ..base import Provider

from . import handlers as url_handlers


class UrlProvider(Provider):
    context = {
        'provider_label': 'URL',
    }

    def handlers(self, handlers, options):
        """Tornado handlers"""

        return handlers + [
            (r'/url([s]?)/(.*)', url_handlers.URLHandler),
        ]

    handlers.weight = 100

    def uri_rewrites(self, rewrites, options):
        """URL will mop up everything else: anything weighted greater than it
           will NEVER be rewritten
        """
        return rewrites + [
            ('^http(s?)://(.*)$', u'/url{0}/{1}'),
            ('^(.*)$', u'/url/{0}'),
        ]

    uri_rewrites.weight = 1000
