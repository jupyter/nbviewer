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

    async def lookup_notebook(self, client, group, repo, branch, filepath):
        """Attempt to find the notebook by searching project trees.
        Used when an instance is misconfigured and paths are getting sanitised."""
        projects = await client.projects(search=repo)

        project = None
        path_with_namespace = "{0}/{1}".format(group, repo)
        for p in projects:
            print(p["path_with_namespace"])
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

    async def get_notebook_data(self, client, group, repo, branch, filepath):
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
                    return await self.lookup_notebook(client, group, repo, branch, filepath)
                except Exception as e:
                    app_log.error(e)
            else:
                app_log.error(http_error)
        except Exception as e:
            app_log.error(e)

    async def deliver_notebook(self, host, group, repo, branch, path, remote_url):
        response = await self.fetch(remote_url)

        base_url = ("/gitlab/{host}/{group}/{repo}/tree/{branch}/"
                    .format(host=host,
                            group=group,
                            repo=repo,
                            branch=branch))

        breadcrumbs = [{"url": base_url, "name": repo}]
        dirpath = path.rsplit('/', 1)[0]
        breadcrumbs.extend(self.breadcrumbs(dirpath, base_url))

        try:
            nbjson = response_text(response, encoding='utf-8')
        except UnicodeDecodeError:
            app_log.error("Notebook is not utf8: %s", remote_url, exc_info=True)
            raise web.HTTPError(400)

        await self.finish_notebook(nbjson,
                                   download_url=remote_url,
                                   msg="file from url: " + remote_url,
                                   public=False,
                                   breadcrumbs=breadcrumbs,
                                   request=self.request)

    def render_dirview_template(self, entries, title, breadcrumbs):
        return self.render_template('dirview.html',
                                    entries=entries,
                                    breadcrumbs=breadcrumbs,
                                    title=title)

    async def show_dir(self, client, group, repo, branch, dirpath):
        path_with_namespace = "{group}/{repo}".format(group=group, repo=repo)
        tree = await client.tree(path_with_namespace, branch, dirpath)

        full_url = "/gitlab/{host}/{group}/{repo}/{path_type}/{branch}/{path}"
        external_url = "https://{host}/{group}/{repo}/{path_type}/{branch}/{path}"

        base_url = ("/gitlab/{host}/{group}/{repo}/tree/{branch}/"
                    .format(host=client.host,
                            group=group,
                            repo=repo,
                            branch=branch))

        breadcrumbs = [{"url": base_url, "name": repo}]
        breadcrumbs.extend(self.breadcrumbs(dirpath, base_url))

        entries = []
        for item in tree:
            if item["type"] == "tree":
                entry_class = "fa fa-folder-open"
                url = item["path"]
            elif item["type"] == "blob" and item["path"].endswith("ipynb"):
                entry_class = "fa fa-book"
                url = full_url.format(host=client.host,
                                      group=group,
                                      repo=repo,
                                      path_type="blob",
                                      branch=branch,
                                      path=item["path"])
            else:
                entry_class = "fa fa-share"
                url = external_url.format(host=client.host,
                                          group=group,
                                          repo=repo,
                                          path_type="blob",
                                          branch=branch,
                                          path=item["path"])

            entries.append({"name": item["name"],
                            "url": url,
                            "class": entry_class})

        html = self.render_dirview_template(entries=entries,
                                            title=dirpath,
                                            breadcrumbs=breadcrumbs)
        await self.cache_and_finish(html)

    @cached
    async def get(self, host, group, repo, path_type, branch, path):
        client = GitlabClient(host)
        if path_type == "blob":
            raw_url = await self.get_notebook_data(client, group, repo, branch, path)
            await self.deliver_notebook(host, group, repo, branch, path, raw_url)
        else:
            await self.show_dir(client, group, repo, branch, path)

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
