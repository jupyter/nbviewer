from ..github.client import AsyncGitHubClient


class AsyncGHEClient(AsyncGitHubClient):
    API_URL_ENV = ('GHE_API_URL', '')
    OAUTH_KEY_ENV = ('GHE_OAUTH_KEY', '')
    OAUTH_SECRET_ENV = ('GHE_OAUTH_SECRET', '')
    OAUTH_TOKEN_ENV = ('GHE_API_TOKEN', '')
