from ..base import Provider

from . import handlers as gist_handlers


class GistProvider(Provider):
    """A provider for Github Gists
    """
    # enable this by default
    default_enabled = True

    context = {
        'provider_label': 'Gist',
        'provider_icon': 'github-square',
    }

    def handlers(self, handlers, options):
        """Tornado handlers"""

        return handlers + [
            (r'/gist/([^\/]+/)?([0-9]+|[0-9a-f]{20})',
                gist_handlers.GistHandler),
            (r'/gist/([^\/]+/)?([0-9]+|[0-9a-f]{20})/(?:files/)?(.*)',
                gist_handlers.GistHandler),
            (r'/([0-9]+|[0-9a-f]{20})', gist_handlers.GistRedirectHandler),
            (r'/([0-9]+|[0-9a-f]{20})/(.*)',
                gist_handlers.GistRedirectHandler),
            (r'/gist/([^\/]+)/?', gist_handlers.UserGistsHandler),
        ]

    handlers.weight = 300

    def uri_rewrites(self, rewrites, options):
        return [
            (r'^([a-f0-9]+)/?$', u'/{0}'),
            ('^https?://gist.github.com/([^\/]+/)?([a-f0-9]+)/?$', u'/{1}'),
        ] + rewrites

    uri_rewrites.weight = 100
