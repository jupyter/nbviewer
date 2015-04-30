#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import json
import mimetypes

from tornado import (
    web,
    gen,
)
from tornado.log import app_log
from tornado.escape import url_unescape

from ..base import (
    AddSlashHandler,
    BaseHandler,
    cached,
    RemoveSlashHandler,
    RenderingHandler,
)

from ...utils import (
    base64_decode,
    quote,
    response_text,
)

from .client import AsyncGitHubClient


PROVIDER_CTX = {
    'provider_label': 'GitHub',
    'provider_icon': 'github',
}


class GithubClientMixin(object):
    @property
    def github_client(self):
        """Create an upgraded github API client from the HTTP client"""
        if getattr(self, "_github_client", None) is None:
            self._github_client = AsyncGitHubClient(self.client)
        return self._github_client


class RawGitHubURLHandler(BaseHandler):
    """redirect old /urls/raw.github urls to /github/ API urls"""
    def get(self, user, repo, path):
        new_url = u'{format}/github/{user}/{repo}/blob/{path}'.format(
            format=self.format_prefix, user=user, repo=repo, path=path,
        )
        app_log.info("Redirecting %s to %s", self.request.uri, new_url)
        self.redirect(new_url)


class GitHubRedirectHandler(GithubClientMixin, BaseHandler):
    """redirect github blob|tree|raw urls to /github/ API urls"""
    def get(self, user, repo, app, ref, path):
        if app == 'raw':
            app = 'blob'
        new_url = u'{format}/github/{user}/{repo}/{app}/{ref}/{path}'.format(
            format=self.format_prefix, user=user, repo=repo, app=app,
            ref=ref, path=path,
        )
        app_log.info("Redirecting %s to %s", self.request.uri, new_url)
        self.redirect(new_url)


class GitHubUserHandler(GithubClientMixin, BaseHandler):
    """list a user's github repos"""
    @cached
    @gen.coroutine
    def get(self, user):
        page = self.get_argument("page", None)
        params = {'sort' : 'updated'}
        if page:
            params['page'] = page
        with self.catch_client_error():
            response = yield self.github_client.get_repos(user, params=params)

        prev_url, next_url = self.get_page_links(response)
        repos = json.loads(response_text(response))

        entries = []
        for repo in repos:
            entries.append(dict(
                url=repo['name'],
                name=repo['name'],
            ))
        provider_url = u"https://github.com/{user}".format(user=user)
        html = self.render_template("userview.html",
            entries=entries, provider_url=provider_url, 
            next_url=next_url, prev_url=prev_url,
            **PROVIDER_CTX
        )
        yield self.cache_and_finish(html)


class GitHubRepoHandler(BaseHandler):
    """redirect /github/user/repo to .../tree/master"""
    def get(self, user, repo):
        self.redirect("%s/github/%s/%s/tree/master/" % (self.format_prefix, user, repo))


class GitHubTreeHandler(GithubClientMixin, BaseHandler):
    """list files in a github repo (like github tree)"""
    @cached
    @gen.coroutine
    def get(self, user, repo, ref, path):
        if not self.request.uri.endswith('/'):
            self.redirect(self.request.uri + '/')
            return
        path = path.rstrip('/')
        with self.catch_client_error():
            response = yield self.github_client.get_contents(user, repo, path, ref=ref)

        contents = json.loads(response_text(response))

        branches, tags = yield self.refs(user, repo)

        for nav_ref in branches + tags:
            nav_ref["url"] = (u"/github/{user}/{repo}/tree/{ref}/{path}"
                .format(
                    ref=nav_ref["name"], user=user, repo=repo, path=path
                ))

        if not isinstance(contents, list):
            app_log.info(
                "{format}/{user}/{repo}/{ref}/{path} not tree, redirecting to blob",
                extra=dict(format=self.format_prefix, user=user, repo=repo, ref=ref, path=path)
            )
            self.redirect(
                u"{format}/github/{user}/{repo}/blob/{ref}/{path}".format(
                    format=self.format_prefix, user=user, repo=repo, ref=ref, path=path,
                )
            )
            return

        base_url = u"/github/{user}/{repo}/tree/{ref}".format(
            user=user, repo=repo, ref=ref,
        )
        provider_url = u"https://github.com/{user}/{repo}/tree/{ref}/{path}".format(
            user=user, repo=repo, ref=ref, path=path,
        )

        breadcrumbs = [{
            'url' : base_url,
            'name' : repo,
        }]
        breadcrumbs.extend(self.breadcrumbs(path, base_url))

        entries = []
        dirs = []
        ipynbs = []
        others = []
        for file in contents:
            e = {}
            e['name'] = file['name']
            if file['type'] == 'dir':
                e['url'] = u'/github/{user}/{repo}/tree/{ref}/{path}'.format(
                user=user, repo=repo, ref=ref, path=file['path']
                )
                e['url'] = quote(e['url'])
                e['class'] = 'fa-folder-open'
                dirs.append(e)
            elif file['name'].endswith('.ipynb'):
                e['url'] = u'/github/{user}/{repo}/blob/{ref}/{path}'.format(
                user=user, repo=repo, ref=ref, path=file['path']
                )
                e['url'] = quote(e['url'])
                e['class'] = 'fa-book'
                ipynbs.append(e)
            elif file['html_url']:
                e['url'] = file['html_url']
                e['class'] = 'fa-share'
                others.append(e)
            else:
                # submodules don't have html_url
                e['url'] = ''
                e['class'] = 'fa-folder-close'
                others.append(e)


        entries.extend(dirs)
        entries.extend(ipynbs)
        entries.extend(others)

        html = self.render_template("treelist.html",
            entries=entries, breadcrumbs=breadcrumbs, provider_url=provider_url,
            user=user, repo=repo, ref=ref, path=path,
            branches=branches, tags=tags, tree_type="github",
            **PROVIDER_CTX
        )
        yield self.cache_and_finish(html)

    @gen.coroutine
    def refs(self, user, repo):
        """get branches and tags for this user/repo"""
        ref_types = ("branches", "tags")
        ref_data = [None, None]

        for i, ref_type in enumerate(ref_types):
            with self.catch_client_error():
                response = yield getattr(self.github_client, "get_%s" % ref_type)(user, repo)
            ref_data[i] = json.loads(response_text(response))

        raise gen.Return(ref_data)


class GitHubBlobHandler(GithubClientMixin, RenderingHandler):
    """handler for files on github

    If it's a...

    - notebook, render it
    - non-notebook file, serve file unmodified
    - directory, redirect to tree
    """
    @cached
    @gen.coroutine
    def get(self, user, repo, ref, path):
        raw_url = u"https://raw.githubusercontent.com/{user}/{repo}/{ref}/{path}".format(
            user=user, repo=repo, ref=ref, path=quote(path)
        )
        blob_url = u"https://github.com/{user}/{repo}/blob/{ref}/{path}".format(
            user=user, repo=repo, ref=ref, path=quote(path),
        )
        with self.catch_client_error():
            tree_entry = yield self.github_client.get_tree_entry(
                user, repo, path=url_unescape(path), ref=ref
            )

        if tree_entry['type'] == 'tree':
            tree_url = "/github/{user}/{repo}/tree/{ref}/{path}/".format(
                user=user, repo=repo, ref=ref, path=quote(path),
            )
            app_log.info("%s is a directory, redirecting to %s", self.request.path, tree_url)
            self.redirect(tree_url)
            return

        # fetch file data from the blobs API
        with self.catch_client_error():
            response = yield self.github_client.fetch(tree_entry['url'])

        data = json.loads(response_text(response))
        contents = data['content']
        if data['encoding'] == 'base64':
            # filedata will be bytes
            filedata = base64_decode(contents)
        else:
            # filedata will be unicode
            filedata = contents

        if path.endswith('.ipynb'):
            dir_path = path.rsplit('/', 1)[0]
            base_url = "/github/{user}/{repo}/tree/{ref}".format(
                user=user, repo=repo, ref=ref,
            )
            breadcrumbs = [{
                'url' : base_url,
                'name' : repo,
            }]
            breadcrumbs.extend(self.breadcrumbs(dir_path, base_url))

            try:
                # filedata may be bytes, but we need text
                if isinstance(filedata, bytes):
                    nbjson = filedata.decode('utf-8')
                else:
                    nbjson = filedata
            except Exception as e:
                app_log.error("Failed to decode notebook: %s", raw_url, exc_info=True)
                raise web.HTTPError(400)
            yield self.finish_notebook(nbjson, raw_url,
                provider_url=blob_url,
                breadcrumbs=breadcrumbs,
                msg="file from GitHub: %s" % raw_url,
                public=True,
                format=self.format,
                request=self.request,
                **PROVIDER_CTX
            )
        else:
            mime, enc = mimetypes.guess_type(path)
            self.set_header("Content-Type", mime or 'text/plain')
            self.cache_and_finish(filedata)


def default_handlers(handlers=[]):
    """Tornado handlers"""

    return [
        (r'/url[s]?/github\.com/([^\/]+)/([^\/]+)/(tree|blob|raw)/([^\/]+)/(.*)', GitHubRedirectHandler),
        (r'/url[s]?/raw\.?github(?:usercontent)?\.com/([^\/]+)/([^\/]+)/(.*)', RawGitHubURLHandler),
    ] + handlers + [
        (r'/github/([^\/]+)', AddSlashHandler),
        (r'/github/([^\/]+)/', GitHubUserHandler),
        (r'/github/([^\/]+)/([^\/]+)', AddSlashHandler),
        (r'/github/([^\/]+)/([^\/]+)/', GitHubRepoHandler),
        (r'/github/([^\/]+)/([^\/]+)/blob/([^\/]+)/(.*)/', RemoveSlashHandler),
        (r'/github/([^\/]+)/([^\/]+)/blob/([^\/]+)/(.*)', GitHubBlobHandler),
        (r'/github/([^\/]+)/([^\/]+)/tree/([^\/]+)', AddSlashHandler),
        (r'/github/([^\/]+)/([^\/]+)/tree/([^\/]+)/(.*)', GitHubTreeHandler)
    ]


def uri_rewrites(rewrites=[]):
    return rewrites + [
        (r'^https?://github.com/([\w\-]+)/([^\/]+)/(blob|tree)/(.*)$',
            u'/github/{0}/{1}/{2}/{3}'),
        (r'^https?://raw.?github.com/([\w\-]+)/([^\/]+)/(.*)$',
            u'/github/{0}/{1}/blob/{2}'),
        (r'^([\w\-]+)/([^\/]+)$',
            u'/github/{0}/{1}/tree/master/'),
        (r'^([\w\-]+)$',
            u'/github/{0}/'),
    ]
