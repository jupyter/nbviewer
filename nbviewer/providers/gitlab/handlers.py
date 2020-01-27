import json
import os
from tornado import web
from tornado.log import app_log
from ..base import RenderingHandler, cached
from ...utils import response_text
from .. import _load_handler_from_location
from .client import GitlabClient


class GitlabHandler(RenderingHandler):

    async def get_notebook_data(self, host, group, repo, blob, branch, path):

        client = GitlabClient(host)

        try:
            projects = await client.projects()

            path_with_namespace = "{group}/{repo}".format(group=group, repo=repo)

            project = None
            for p in projects:
                if p["path_with_namespace"] == path_with_namespace:
                    project = p
                    break
            else:
                raise Exception("Project path not found: " + path_with_namespace)

            tree = await client.tree(project["id"], branch)

            blob = None
            for item in tree:
                if item["path"] == path:
                    blob = item
                    break
            else:
                raise Exception("Blob not found: " + path)

            return client.raw_file_url(project["id"], blob["id"])

        except Exception as e:
            app_log.error(e)


    async def deliver_notebook(self, remote_url):
        app_log.info("Fetching notebook: " + remote_url)

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
    async def get(self, host, group, repo, blob, branch, path):
        raw_url = await self.get_notebook_data(host, group, repo, blob, branch, path)
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
        (r'/gitlab/(?P<host>[\w_\-.]+)/(?P<group>[\w_\-.]+)/(?P<repo>[\w_\-]+)/(?P<blob>blob)/(?P<branch>[\w_\-()]+)/(?P<path>.*)', gitlab_handler, {}),
    ]
