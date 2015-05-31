from ..base import Provider

from . import handlers as gh_handlers


class GithubProvider(Provider):
    """A full provider for notebooks, users and directories on Github
    """
    # enable this by default
    default_enabled = True

    context = {
        'provider_label': 'GitHub',
        'provider_icon': 'github',
    }

    def handlers(self, handlers, options):
        """Tornado handlers"""

        return [
            (r'/url[s]?/github\.com/([^\/]+)/([^\/]+)/'
                '(tree|blob|raw)/([^\/]+)/(.*)',
                gh_handlers.GitHubRedirectHandler),
            (r'/url[s]?/raw\.?github(?:usercontent)?\.com/'
                '([^\/]+)/([^\/]+)/(.*)',
                gh_handlers.RawGitHubURLHandler),
        ] + handlers + [
            (r'/github/([^\/]+)', gh_handlers.AddSlashHandler),
            (r'/github/([^\/]+)/', gh_handlers.GitHubUserHandler),
            (r'/github/([^\/]+)/([^\/]+)', gh_handlers.AddSlashHandler),
            (r'/github/([^\/]+)/([^\/]+)/', gh_handlers.GitHubRepoHandler),
            (r'/github/([^\/]+)/([^\/]+)/blob/([^\/]+)/(.*)/',
                gh_handlers.RemoveSlashHandler),
            (r'/github/([^\/]+)/([^\/]+)/blob/([^\/]+)/(.*)',
                gh_handlers.GitHubBlobHandler),
            (r'/github/([^\/]+)/([^\/]+)/tree/([^\/]+)',
                gh_handlers.AddSlashHandler),
            (r'/github/([^\/]+)/([^\/]+)/tree/([^\/]+)/(.*)',
                gh_handlers.GitHubTreeHandler)
        ]

    handlers.weight = 200

    def uri_rewrites(self, rewrites, options):
        return rewrites + [
            (r'^https?://github.com/([\w\-]+)/([^\/]+)/(blob|tree)/(.*)$',
                u'/github/{0}/{1}/{2}/{3}'),
            (r'^https?://raw.?github.com/([\w\-]+)/([^\/]+)/(.*)$',
                u'/github/{0}/{1}/blob/{2}'),
            (r'^([\w\-]+)/([^\/]+)$',
                u'/github/{0}/{1}/tree/master/'),
            (r'^([\w\-]+)$',
                u'/github/{0}/'),
        ]

    uri_rewrites.weight = 200
