import os

from ..github import handlers as ghh
from .client import AsyncGHEClient

PROVIDER_URL_FRAG = os.environ.get("GHE_PROVIDER_URL_FRAG", "ghe")
HTML_URL = os.environ.get("GHE_HTML_URL", None)


class GithubEnterpriseMixin(object):
    PROVIDER_URL_FRAG = PROVIDER_URL_FRAG
    HTML_URL = HTML_URL
    GH_CLIENT_CLASS = AsyncGHEClient


class AddSlashHandler(GithubEnterpriseMixin, ghh.AddSlashHandler):
    pass


class GitHubUserHandler(GithubEnterpriseMixin, ghh.GitHubUserHandler):
    pass


class GitHubRepoHandler(GithubEnterpriseMixin, ghh.GitHubRepoHandler):
    pass


class RemoveSlashHandler(GithubEnterpriseMixin, ghh.RemoveSlashHandler):
    pass


class GitHubBlobHandler(GithubEnterpriseMixin, ghh.GitHubBlobHandler):
    pass


class GitHubTreeHandler(GithubEnterpriseMixin, ghh.GitHubTreeHandler):
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
        (r'^' + HTML_URL + r'/([\w\-]+)/([^\/]+)/(blob|tree)/(.*)$',
            u'/' + PROVIDER_URL_FRAG + u'/{0}/{1}/{2}/{3}'),
        (r'^([\w\-]+)/([^\/]+)$',
            u'/' + PROVIDER_URL_FRAG + u'/{0}/{1}/tree/master/'),
        (r'^([\w\-]+)$',
            u'/' + PROVIDER_URL_FRAG + u'/{0}/'),
    ]
