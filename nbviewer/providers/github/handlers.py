# -----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------
import json
import mimetypes
import os
import re

from tornado import web
from tornado.escape import url_unescape

from .. import _load_handler_from_location
from ...utils import base64_decode
from ...utils import quote
from ...utils import response_text
from ...utils import url_path_join
from ..base import AddSlashHandler
from ..base import BaseHandler
from ..base import cached
from ..base import RemoveSlashHandler
from ..base import RenderingHandler
from .client import AsyncGitHubClient


class GithubClientMixin(object):

    # PROVIDER_CTX is a dictionary whose entries are passed as keyword arguments
    # to the render_template method of the GistHandler. The following describe
    # the information contained in each of these keyword arguments:
    # provider_label: str
    #     Text to to apply to the navbar icon linking to the provider
    # provider_icon: str
    #     CSS classname to apply to the navbar icon linking to the provider
    # executor_label: str, optional
    #     Text to apply to the navbar icon linking to the execution service
    # executor_icon: str, optional
    #     CSS classname to apply to the navbar icon linking to the execution service
    PROVIDER_CTX = {
        "provider_label": "GitHub",
        "provider_icon": "github",
        "executor_label": "Binder",
        "executor_icon": "icon-binder",
    }

    BINDER_TMPL = "{binder_base_url}/gh/{org}/{repo}/{ref}"
    BINDER_PATH_TMPL = BINDER_TMPL + "?filepath={path}"

    @property
    def github_url(self):
        if getattr(self, "_github_url", None) is None:
            if os.environ.get("GITHUB_URL", ""):
                self._github_url = os.environ.get("GITHUB_URL")
            elif self.github_client.github_api_url == "https://api.github.com/":
                self._github_url = "https://github.com/"
            else:
                # Github Enterprise
                # https://developer.github.com/enterprise/2.18/v3/enterprise-admin/#endpoint-urls
                self._github_url = re.sub(
                    r"api/v3/$", "", self.github_client.github_api_url
                )
        return self._github_url

    @property
    def github_client(self):
        """Create an upgraded github API client from the HTTP client"""
        if getattr(self, "_github_client", None) is None:
            self._github_client = AsyncGitHubClient(self.log, self.client)
        return self._github_client

    def client_error_message(self, exc, url, body, msg=None):
        if exc.code == 403 and "rate limit" in body.lower():
            return 503, "GitHub API rate limit exceeded. Try again soon."

        return super().client_error_message(exc, url, body, msg)


class RawGitHubURLHandler(BaseHandler):
    """redirect old /urls/raw.github urls to /github/ API urls"""

    def get(self, user, repo, path):
        new_url = u"{format}/github/{user}/{repo}/blob/{path}".format(
            format=self.format_prefix, user=user, repo=repo, path=path
        )
        self.log.info("Redirecting %s to %s", self.request.uri, new_url)
        self.redirect(self.from_base(new_url))


class GitHubRedirectHandler(GithubClientMixin, BaseHandler):
    """redirect github urls to /github/ API urls"""

    def get(self, url):
        new_url = u"{format}/github/{url}".format(format=self.format_prefix, url=url)
        self.log.info("Redirecting %s to %s", self.request.uri, new_url)
        self.redirect(self.from_base(new_url))


class GitHubUserHandler(GithubClientMixin, BaseHandler):
    """list a user's github repos"""

    def render_github_user_template(
        self, entries, provider_url, next_url, prev_url, **namespace
    ):
        return self.render_template(
            "userview.html",
            entries=entries,
            provider_url=provider_url,
            next_url=next_url,
            prev_url=prev_url,
            **self.PROVIDER_CTX,
            **namespace
        )

    @cached
    async def get(self, user):
        page = self.get_argument("page", None)
        params = {"sort": "updated"}
        if page:
            params["page"] = page
        with self.catch_client_error():
            response = await self.github_client.get_repos(user, params=params)

        prev_url, next_url = self.get_page_links(response)
        repos = json.loads(response_text(response))

        entries = []
        for repo in repos:
            entries.append(dict(url=repo["name"], name=repo["name"]))

        provider_url = u"{github_url}{user}".format(
            user=user, github_url=self.github_url
        )
        html = self.render_github_user_template(
            entries=entries,
            provider_url=provider_url,
            next_url=next_url,
            prev_url=prev_url,
        )
        await self.cache_and_finish(html)


class GitHubRepoHandler(GithubClientMixin, BaseHandler):
    """redirect /github/user/repo to .../tree/master"""

    async def get(self, user, repo):
        response = await self.github_client.get_repo(user, repo)
        default_branch = json.loads(response_text(response))['default_branch']

        new_url = self.from_base(
            "/", self.format_prefix, "github", user, repo, "tree", default_branch
        )
        self.log.info("Redirecting %s to %s", self.request.uri, new_url)
        self.redirect(new_url)


class GitHubTreeHandler(GithubClientMixin, BaseHandler):
    """list files in a github repo (like github tree)"""

    def render_treelist_template(
        self,
        entries,
        breadcrumbs,
        provider_url,
        user,
        repo,
        ref,
        path,
        branches,
        tags,
        executor_url,
        **namespace
    ):
        """
        breadcrumbs: list of dict
            Breadcrumb 'name' and 'url' to render as links at the top of the notebook page
        provider_url: str
            URL to the notebook document upstream at the provider (e.g., GitHub)
        executor_url: str, optional
            URL to execute the notebook document (e.g., Binder)
        """
        return self.render_template(
            "treelist.html",
            entries=entries,
            breadcrumbs=breadcrumbs,
            provider_url=provider_url,
            user=user,
            repo=repo,
            ref=ref,
            path=path,
            branches=branches,
            tags=tags,
            tree_type="github",
            tree_label="repositories",
            executor_url=executor_url,
            **self.PROVIDER_CTX,
            **namespace
        )

    @cached
    async def get(self, user, repo, ref, path):
        if not self.request.uri.endswith("/"):
            self.redirect(self.request.uri + "/")
            return
        path = path.rstrip("/")
        with self.catch_client_error():
            response = await self.github_client.get_contents(user, repo, path, ref=ref)

        contents = json.loads(response_text(response))

        branches, tags = await self.refs(user, repo)

        for nav_ref in branches + tags:
            nav_ref["url"] = u"/github/{user}/{repo}/tree/{ref}/{path}".format(
                ref=nav_ref["name"], user=user, repo=repo, path=path
            )

        if not isinstance(contents, list):
            self.log.info(
                "{format}/{user}/{repo}/{ref}/{path} not tree, redirecting to blob",
                extra=dict(
                    format=self.format_prefix, user=user, repo=repo, ref=ref, path=path
                ),
            )
            self.redirect(
                u"{format}/github/{user}/{repo}/blob/{ref}/{path}".format(
                    format=self.format_prefix, user=user, repo=repo, ref=ref, path=path
                )
            )
            return

        # Account for possibility that GitHub API redirects us to get more accurate breadcrumbs
        # See: https://github.com/jupyter/nbviewer/issues/324
        example_file_url = contents[0]["html_url"]
        user, repo = re.match(
            r"^" + self.github_url + "(?P<user>[^\/]+)/(?P<repo>[^\/]+)/.*",
            example_file_url,
        ).group("user", "repo")

        base_url = u"/github/{user}/{repo}/tree/{ref}".format(
            user=user, repo=repo, ref=ref
        )

        provider_url = u"{github_url}{user}/{repo}/tree/{ref}/{path}".format(
            user=user, repo=repo, ref=ref, path=path, github_url=self.github_url
        )

        breadcrumbs = [{"url": base_url, "name": repo}]
        breadcrumbs.extend(self.breadcrumbs(path, base_url))

        entries = []
        dirs = []
        ipynbs = []
        others = []
        for file in contents:
            e = {}
            e["name"] = file["name"]
            if file["type"] == "dir":
                e["url"] = u"/github/{user}/{repo}/tree/{ref}/{path}".format(
                    user=user, repo=repo, ref=ref, path=file["path"]
                )
                e["url"] = quote(e["url"])
                e["class"] = "fa-folder-open"
                dirs.append(e)
            elif file["name"].endswith(".ipynb"):
                e["url"] = u"/github/{user}/{repo}/blob/{ref}/{path}".format(
                    user=user, repo=repo, ref=ref, path=file["path"]
                )
                e["url"] = quote(e["url"])
                e["class"] = "fa-book"
                ipynbs.append(e)
            elif file["html_url"]:
                e["url"] = file["html_url"]
                e["class"] = "fa-share"
                others.append(e)
            else:
                # submodules don't have html_url
                e["url"] = ""
                e["class"] = "fa-folder-close"
                others.append(e)

        entries.extend(dirs)
        entries.extend(ipynbs)
        entries.extend(others)

        # Enable a binder navbar icon if a binder base URL is configured
        executor_url = (
            self.BINDER_TMPL.format(
                binder_base_url=self.binder_base_url, org=user, repo=repo, ref=ref
            )
            if self.binder_base_url
            else None
        )

        html = self.render_treelist_template(
            entries=entries,
            breadcrumbs=breadcrumbs,
            provider_url=provider_url,
            user=user,
            repo=repo,
            ref=ref,
            path=path,
            branches=branches,
            tags=tags,
            executor_url=executor_url,
        )
        await self.cache_and_finish(html)

    async def refs(self, user, repo):
        """get branches and tags for this user/repo"""
        ref_types = ("branches", "tags")
        ref_data = [None, None]

        for i, ref_type in enumerate(ref_types):
            with self.catch_client_error():
                response = await getattr(self.github_client, "get_%s" % ref_type)(
                    user, repo
                )
            ref_data[i] = json.loads(response_text(response))

        return ref_data


class GitHubBlobHandler(GithubClientMixin, RenderingHandler):
    """handler for files on github

    If it's a...

    - notebook, render it
    - non-notebook file, serve file unmodified
    - directory, redirect to tree
    """

    async def get_notebook_data(self, user, repo, ref, path):
        if os.environ.get("GITHUB_API_URL", "") == "":
            raw_url = u"https://raw.githubusercontent.com/{user}/{repo}/{ref}/{path}".format(
                user=user, repo=repo, ref=ref, path=quote(path)
            )
        else:  # Github Enterprise has a different URL pattern for accessing raw files
            raw_url = url_path_join(
                self.github_url, user, repo, "raw", ref, quote(path)
            )
        blob_url = u"{github_url}{user}/{repo}/blob/{ref}/{path}".format(
            user=user, repo=repo, ref=ref, path=quote(path), github_url=self.github_url
        )
        with self.catch_client_error():
            tree = await self.github_client.get_tree(
                user, repo, path=url_unescape(path), ref=ref
            )
            tree_entry = self.github_client.extract_tree_entry(
                path=url_unescape(path), tree_response=tree
            )

        if tree_entry["type"] == "tree":
            tree_url = "/github/{user}/{repo}/tree/{ref}/{path}/".format(
                user=user, repo=repo, ref=ref, path=quote(path)
            )
            self.log.info(
                "%s is a directory, redirecting to %s", self.request.path, tree_url
            )
            self.redirect(tree_url)
            return

        return raw_url, blob_url, tree_entry

    async def deliver_notebook(
        self, user, repo, ref, path, raw_url, blob_url, tree_entry
    ):
        # fetch file data from the blobs API
        with self.catch_client_error():
            response = await self.github_client.fetch(tree_entry["url"])

        data = json.loads(response_text(response))
        contents = data["content"]
        if data["encoding"] == "base64":
            # filedata will be bytes
            filedata = base64_decode(contents)
        else:
            # filedata will be unicode
            filedata = contents

        if path.endswith(".ipynb"):
            dir_path = path.rsplit("/", 1)[0]
            base_url = "/github/{user}/{repo}/tree/{ref}".format(
                user=user, repo=repo, ref=ref
            )
            breadcrumbs = [{"url": base_url, "name": repo}]
            breadcrumbs.extend(self.breadcrumbs(dir_path, base_url))

            # Enable a binder navbar icon if a binder base URL is configured
            executor_url = (
                self.BINDER_PATH_TMPL.format(
                    binder_base_url=self.binder_base_url,
                    org=user,
                    repo=repo,
                    ref=ref,
                    path=quote(path),
                )
                if self.binder_base_url
                else None
            )

            try:
                # filedata may be bytes, but we need text
                if isinstance(filedata, bytes):
                    nbjson = filedata.decode("utf-8")
                else:
                    nbjson = filedata
            except Exception as e:
                self.log.error("Failed to decode notebook: %s", raw_url, exc_info=True)
                raise web.HTTPError(400)

            # Explanation of some kwargs passed into `finish_notebook`:
            # provider_url:
            #     URL to the notebook document upstream at the provider (e.g., GitHub)
            # breadcrumbs: list of dict
            #     Breadcrumb 'name' and 'url' to render as links at the top of the notebook page
            # executor_url: str, optional
            #     URL to execute the notebook document (e.g., Binder)
            await self.finish_notebook(
                nbjson,
                raw_url,
                provider_url=blob_url,
                executor_url=executor_url,
                breadcrumbs=breadcrumbs,
                msg="file from GitHub: %s" % raw_url,
                public=True,
                **self.PROVIDER_CTX
            )
        else:
            mime, enc = mimetypes.guess_type(path)
            self.set_header("Content-Type", mime or "text/plain")
            await self.cache_and_finish(filedata)

    @cached
    async def get(self, user, repo, ref, path):
        notebook_data = await self.get_notebook_data(user, repo, ref, path)

        if notebook_data is not None:
            raw_url, blob_url, tree_entry = notebook_data
        else:
            return

        await self.deliver_notebook(
            user, repo, ref, path, raw_url, blob_url, tree_entry
        )


def default_handlers(handlers=[], **handler_names):
    """Tornado handlers"""

    blob_handler = _load_handler_from_location(handler_names["github_blob_handler"])
    tree_handler = _load_handler_from_location(handler_names["github_tree_handler"])
    user_handler = _load_handler_from_location(handler_names["github_user_handler"])

    return (
        [
            # ideally these URIs should have been caught by an appropriate
            # uri_rewrite rather than letting the url provider catch them and then
            # fixing it here.
            # There are probably links in the wild that depend on these, so keep
            # these handlers for backwards compatibility.
            (r"/url[s]?/github\.com/(?P<url>.*)", GitHubRedirectHandler, {}),
            (
                r"/url[s]?/raw\.?github\.com/(?P<user>[^\/]+)/(?P<repo>[^\/]+)/(?P<path>.*)",
                RawGitHubURLHandler,
                {},
            ),
            (
                r"/url[s]?/raw\.?githubusercontent\.com/(?P<user>[^\/]+)/(?P<repo>[^\/]+)/(?P<path>.*)",
                RawGitHubURLHandler,
                {},
            ),
        ]
        + handlers
        + [
            (r"/github/([^\/]+)", AddSlashHandler, {}),
            (r"/github/(?P<user>[^\/]+)/", user_handler, {}),
            (r"/github/([^\/]+)/([^\/]+)", AddSlashHandler, {}),
            (r"/github/(?P<user>[^\/]+)/(?P<repo>[^\/]+)/", GitHubRepoHandler, {}),
            (
                r"/github/([^\/]+)/([^\/]+)/(?:blob|raw)/([^\/]+)/(.*)/",
                RemoveSlashHandler,
                {},
            ),
            (r"/github/([^\/]+)/([^\/]+)/tree/([^\/]+)", AddSlashHandler, {}),
        ]
        + [
            (
                r"/github/(?P<user>[^\/]+)/(?P<repo>[^\/]+)/tree/(?P<ref>[^\/]+)/(?P<path>.*)",
                tree_handler,
                {},
            ),
            (
                r"/github/(?P<user>[^\/]+)/(?P<repo>[^\/]+)/(?:blob|raw)/(?P<ref>[^\/]+)/(?P<path>.*)",
                blob_handler,
                {},
            ),
        ]
    )


def uri_rewrites(rewrites=[]):
    github_rewrites = [
        # three different uris for a raw view
        (
            r"^https?://github\.com/([^\/]+)/([^\/]+)/raw/([^\/]+)/(.*)",
            u"/github/{0}/{1}/blob/{2}/{3}",
        ),
        (
            r"^https?://raw\.github\.com/([^\/]+)/([^\/]+)/(.*)",
            u"/github/{0}/{1}/blob/{2}",
        ),
        (
            r"^https?://raw\.githubusercontent\.com/([^\/]+)/([^\/]+)/(.*)",
            u"/github/{0}/{1}/blob/{2}",
        ),
        # trees & blobs
        (
            r"^https?://github.com/([\w\-]+)/([^\/]+)/(blob|tree)/(.*)$",
            u"/github/{0}/{1}/{2}/{3}",
        ),
        # user/repo
        (r"^([\w\-]+)/([^\/]+)$", u"/github/{0}/{1}/tree/master/"),
        # user
        (r"^([\w\-]+)$", u"/github/{0}/"),
    ]
    # github enterprise
    if os.environ.get("GITHUB_API_URL", "") != "":
        github_base_url = os.environ.get("GITHUB_API_URL").split("api/v3")[0]

        github_rewrites.extend(
            [
                # raw view
                (
                    r"^" + github_base_url + r"([^\/]+)/([^\/]+)/raw/([^\/]+)/(.*)",
                    u"/github/{0}/{1}/blob/{2}/{3}",
                ),
                # trees & blobs
                (
                    r"^" + github_base_url + r"([\w\-]+)/([^\/]+)/(blob|tree)/(.*)$",
                    u"/github/{0}/{1}/{2}/{3}",
                ),
                # user/repo
                (
                    r"^" + github_base_url + r"([\w\-]+)/([^\/]+)/?$",
                    u"/github/{0}/{1}/tree/master",
                ),
                # user
                (r"^" + github_base_url + r"([\w\-]+)/?$", u"/github/{0}/"),
            ]
        )
    return rewrites + github_rewrites
