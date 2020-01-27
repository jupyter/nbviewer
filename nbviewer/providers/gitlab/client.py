import json
import os
from tornado.httpclient import AsyncHTTPClient, HTTPError
from tornado.log import app_log
from ...utils import response_text


class GitlabClient(object):
    """Asynchronous client for a private GitLab instance using V4 REST API."""

    def __init__(self, host, token=None, client=None):
        """Init a GitlabClient.

        host: str
        token: optional str
          This needs a private access token - if not provided, uses
          environment variable GITLAB_TOKEN
        client: AsyncHTTPClient
        """
        self.client = client or AsyncHTTPClient()
        self.host = host
        self.token = token or os.environ.get("GITLAB_TOKEN")

    @property
    def api_url(self):
        """The base URL of the REST API."""
        return "https://{host}/api/v4".format(host=self.host)

    async def _fetch_json(self, url):
        """Fetch JSON content at URL."""
        app_log.info("Fetching " + url)
        response = await self.client.fetch(url)
        text = response_text(response)
        content = json.loads(text)
        return content

    async def projects(self):
        """List all projects accessible on this GitLab instance."""
        projects_url = ("{base}/projects?private_token={token}"
                        .format(base=self.api_url, token=self.token))
        return await self._fetch_json(projects_url)

    async def tree(self, project_id, branch):
        """List all files in the given branch and project.

        project_id: int
        branch: str
        """
        tree_url = ("{base}/projects/{project_id}/repository/tree"
                    "?recursive=true"
                    "&ref={branch}"
                    "&per_page=1000"
                    "&private_token={token}"
                    .format(base=self.api_url,
                            project_id=project_id,
                            branch=branch,
                            token=self.token))
        return await self._fetch_json(tree_url)

    def raw_file_url(self, project_id, blob_sha):
        """URL of the raw file matching given blob SHA in project.

        project_id: int
        blob_sha: str
        """
        raw_url = ("{base}/projects/{project_id}"
                   "/repository/blobs/{blob_sha}/raw?private_token={token}")
        return raw_url.format(base=self.api_url,
                              project_id=project_id,
                              blob_sha=blob_sha,
                              token=self.token)
