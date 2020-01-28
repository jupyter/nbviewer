#-----------------------------------------------------------------------------
#  Copyright (C) 2020 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import json
import os
from urllib.parse import quote_plus
from tornado.httpclient import AsyncHTTPClient, HTTPClientError
from tornado.log import app_log
from ...utils import response_text


class GitlabClient(object):
    """Asynchronous client for a private GitLab instance using V4 REST API.

    Please see https://docs.gitlab.com/ee/api/ for details."""

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
        try:
            response = await self.client.fetch(url)
            text = response_text(response)
            content = json.loads(text)
            return content
        except HTTPClientError as ex:
            # log and raise because this can get lost in async
            app_log.error(ex)
            raise ex

    async def projects(self):
        """List all projects accessible on this GitLab instance."""
        projects_url = ("{base}/projects"
                        "?private_token={token}"
                        "&simple=true"
                        .format(base=self.api_url, token=self.token))
        return await self._fetch_json(projects_url)

    async def tree(self, project_id, branch="master", path=None, recursive=False):
        """List all files in the given branch and project.

        project_id: int or str
        branch: optional str
        path: optional str (defaults to root)
        recursive: optional bool
        """
        if type(project_id) is str:
            project_id = quote_plus(project_id)

        tree_url = ("{base}/projects/{project_id}/repository/tree"
                    "?private_token={token}"
                    "&recursive={recursive}"
                    "&ref={branch}"
                    "&per_page=1000"
                    .format(base=self.api_url,
                            project_id=project_id,
                            recursive=str(recursive),
                            branch=quote_plus(branch),
                            token=self.token))

        if path is not None:
            tree_url = "{url}&path={path}".format(url=tree_url,
                                                  path=quote_plus(path))

        return await self._fetch_json(tree_url)

    async def fileinfo(self, project_id, filepath, branch="master"):
        """Information for file in given branch and project.

        project_id: int or str
        branch: str
        filepath: str
        """
        if type(project_id) is str:
            project_id = quote_plus(project_id)

        file_url = ("{base}/projects/{project_id}/repository/files/{filepath}"
                    "?private_token={token}"
                    "&ref={branch}"
                    .format(base=self.api_url,
                            project_id=project_id,
                            branch=quote_plus(branch),
                            filepath=quote_plus(filepath),
                            token=self.token))
        return await self._fetch_json(file_url)

    def raw_file_url(self, project_id, blob_sha):
        """URL of the raw file matching given blob SHA in project.

        project_id: int or str
        blob_sha: str
        """
        if type(project_id) is str:
            project_id = quote_plus(project_id)

        raw_url = ("{base}/projects/{project_id}"
                   "/repository/blobs/{blob_sha}/raw?private_token={token}")
        return raw_url.format(base=self.api_url,
                              project_id=project_id,
                              blob_sha=blob_sha,
                              token=self.token)
