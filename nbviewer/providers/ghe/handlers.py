import os

from ..github import handlers as ghh

PROVIDER_URL_FRAG = os.environ.get("GHE_PROVIDER_URL_FRAG", "ghe")
HTML_URL = os.environ.get("GITHUB_HTML_URL", None)


class GithubEnterpriseMixin(object):
    PROVIDER_URL_FRAG = PROVIDER_URL_FRAG


class AddSlashHandler(ghh.AddSlashHandler, GithubEnterpriseMixin):
    pass


class GitHubUserHandler(ghh.GitHubUserHandler, GithubEnterpriseMixin):
    pass


class GitHubRepoHandler(ghh.GitHubRepoHandler, GithubEnterpriseMixin):
    pass


class RemoveSlashHandler(ghh.RemoveSlashHandler, GithubEnterpriseMixin):
    pass


class GitHubBlobHandler(ghh.GitHubBlobHandler, GithubEnterpriseMixin):
    pass


class GitHubTreeHandler(ghh.GitHubTreeHandler, GithubEnterpriseMixin):
    pass


def default_handlers(handlers=[]):
    """Tornado handlers"""

    return handlers + [
        (r'/{}/([^\/]+)'.format(PROVIDER_URL_FRAG),
            AddSlashHandler),
        (r'/{}/([^\/]+)/'.format(PROVIDER_URL_FRAG),
            GitHubUserHandler),
        (r'/{}/([^\/]+)/([^\/]+)'.format(PROVIDER_URL_FRAG),
            AddSlashHandler),
        (r'/{}/([^\/]+)/([^\/]+)/'.format(PROVIDER_URL_FRAG),
            GitHubRepoHandler),
        (r'/{}/([^\/]+)/([^\/]+)/blob/([^\/]+)/(.*)/'.format(PROVIDER_URL_FRAG),
            RemoveSlashHandler),
        (r'/{}/([^\/]+)/([^\/]+)/blob/([^\/]+)/(.*)'.format(PROVIDER_URL_FRAG),
            GitHubBlobHandler),
        (r'/{}/([^\/]+)/([^\/]+)/tree/([^\/]+)'.format(PROVIDER_URL_FRAG),
            AddSlashHandler),
        (r'/{}/([^\/]+)/([^\/]+)/tree/([^\/]+)/(.*)'.format(PROVIDER_URL_FRAG),
            GitHubTreeHandler)
    ]

def uri_rewrites(rewrites=[]):
    return rewrites + [
        (HTML_URL + r'^([\w\-]+)/([^\/]+)/(blob|tree)/(.*)$',
            u'/' + PROVIDER_URL_FRAG + u'/{0}/{1}/{2}/{3}'),
        (r'^([\w\-]+)/([^\/]+)$',
            u'/' + PROVIDER_URL_FRAG + u'/{0}/{1}/tree/master/'),
        (r'^([\w\-]+)$',
            u'/' + PROVIDER_URL_FRAG + u'/{0}/'),
    ]
