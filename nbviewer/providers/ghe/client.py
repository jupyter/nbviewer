from ..github.client import AsyncGitHubClient


class AsyncGHEClient(AsyncGitHubClient):
    ENV_PREFIX = 'GHE_'
