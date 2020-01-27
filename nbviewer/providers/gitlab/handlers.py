#-----------------------------------------------------------------------------
#  Copyright (C) 2020 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import json
import os
from tornado import web
from tornado.httpclient import HTTPClientError
from tornado.log import app_log
from ..base import RenderingHandler, cached
from ...utils import response_text
from .. import _load_handler_from_location
from .client import GitlabClient


class GitlabHandler(RenderingHandler):

    async def lookup_notebook(self, client, path_with_namespace, branch, filepath):
        """Attempt to find the notebook by searching project trees.
        Used when an instance is misconfigured and paths are getting sanitised."""
        projects = await client.projects()

        project = None
        for p in projects:
            if p["path_with_namespace"] == path_with_namespace:
                project = p
                break
        else:
            raise Exception("Project path not found: " + path_with_namespace)

        tree = await client.tree(project["id"], branch, recursive=True)

        blob = None
        for item in tree:
            if item["path"] == filepath:
                blob = item
                break
        else:
            raise Exception("Blob not found: " + filepath)

        return client.raw_file_url(project["id"], blob["id"])

    async def get_notebook_data(self, host, group, repo, path_type, branch, filepath):
        client = GitlabClient(host)

        path_with_namespace = "{group}/{repo}".format(group=group, repo=repo)

        try:
            fileinfo = await client.fileinfo(path_with_namespace, filepath, branch)
            return client.raw_file_url(path_with_namespace, fileinfo["blob_id"])
        except HTTPClientError as http_error:
            if http_error.code == 404:
                try:
                    # Sometimes the url-encoded paths get sanitized, so give this a try
                    app_log.warn("Unable to access {filepath} in {path_with_namespace} directly, attempting lookup"
                                 .format(filepath=filepath,
                                         path_with_namespace=path_with_namespace))
                    return await self.lookup_notebook(client, path_with_namespace, branch, filepath)
                except Exception as e:
                    app_log.error(e)
            else:
                app_log.error(http_error)
        except Exception as e:
            app_log.error(e)

    async def deliver_notebook(self, remote_url):
        response = await self.fetch(remote_url)

        try:
            nbjson = response_text(response, encoding='utf-8')
        except UnicodeDecodeError:
            app_log.error("Notebook is not utf8: %s", remote_url, exc_info=True)
            raise web.HTTPError(400)

        await self.finish_notebook(nbjson,
                                   download_url=remote_url,
                                   msg="file from url: " + remote_url,
                                   public=False,
                                   request=self.request)

    @cached
    async def get(self, host, group, repo, path_type, branch, path):
        raw_url = await self.get_notebook_data(host, group, repo, path_type, branch, path)
        await self.deliver_notebook(raw_url)

def uri_rewrites(rewrites=[]):
    gitlab_rewrites = [
        (r'^https?://(gitlab\..*)$', r'/gitlab/{0}'),
        (r'^/url[s]?/(gitlab\..*)$', r'/gitlab/{0}'),
        (r'^/url[s]?/https?://(gitlab\..*)$', r'/gitlab/{0}'),
    ]
    return rewrites + gitlab_rewrites

def default_handlers(handlers=[], **handler_names):
    gitlab_handler = _load_handler_from_location(handler_names['gitlab_handler'])
    return handlers + [
        (r'/gitlab/(?P<host>[\w_\-.]+)'
          '/(?P<group>[\w_\-.]+)'
          '/(?P<repo>[\w_\-]+)'
          '/(?P<path_type>blob|tree)'
          '/(?P<branch>[\w_\-()]+)'
          '/(?P<path>.*)', gitlab_handler, {}),
    ]
