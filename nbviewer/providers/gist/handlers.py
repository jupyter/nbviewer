# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import os
import json

from tornado import web, gen
from tornado.log import app_log


from ..base import (
    BaseHandler,
    cached,
    RenderingHandler,
)

from ...utils import (
    clean_filename,
    quote,
    response_text,
)

from ..github.handlers import GithubClientMixin

from .. import _load_handler_from_location


class GistClientMixin(GithubClientMixin):
    PROVIDER_CTX = {
        'provider_label': 'Gist',
        'provider_icon': 'github-square',
        'executor_label': 'Binder',
        'executor_icon': 'icon-binder',
    }
    
    BINDER_TMPL = '{binder_base_url}/gist/{user}/{gist_id}/master'
    BINDER_PATH_TMPL = BINDER_TMPL+'?filepath={path}'
    
    def client_error_message(self, exc, url, body, msg=None):
        if exc.code == 403 and 'too big' in body.lower():
            return 400, "GitHub will not serve raw gists larger than 10MB"

        return super(GistClientMixin, self).client_error_message(
            exc, url, body, msg
        )


class UserGistsHandler(GistClientMixin, BaseHandler):
    """list a user's gists containing notebooks

    .ipynb file extension is required for listing (not for rendering).
    """
    def render_usergists_template(self, entries, user, provider_url, prev_url,
                                 next_url, **namespace):
        return self.render_template("usergists.html", entries=entries, user=user,
                                   provider_url=provider_url, prev_url=prev_url,
                                   next_url=next_url, **self.PROVIDER_CTX,
                                   **namespace)
    
    @cached
    @gen.coroutine
    def get(self, user, **namespace):
        page = self.get_argument("page", None)
        params = {}
        if page:
            params['page'] = page

        with self.catch_client_error():
            response = yield self.github_client.get_gists(user, params=params)

        prev_url, next_url = self.get_page_links(response)

        gists = json.loads(response_text(response))
        entries = []
        for gist in gists:
            notebooks = [f for f in gist['files'] if f.endswith('.ipynb')]
            if notebooks:
                entries.append(dict(
                    id=gist['id'],
                    notebooks=notebooks,
                    description=gist['description'] or '',
                ))
        gist_url = os.environ.get('GIST_URL', 'https://gist.github.com/')
        provider_url = gist_url + u"{user}".format(user=user)
        html = self.render_usergists_template(entries=entries, user=user, provider_url=provider_url, 
                                              prev_url=prev_url, next_url=next_url, **namespace

        )
        yield self.cache_and_finish(html)


class GistHandler(GistClientMixin, RenderingHandler):
    """render a gist notebook, or list files if a multifile gist"""
    @cached
    @gen.coroutine
    def get(self, user, gist_id, filename=''):
        with self.catch_client_error():
            response = yield self.github_client.get_gist(gist_id)

        gist = json.loads(response_text(response))
        gist_id=gist['id']
        if user is None:
            # redirect to /gist/user/gist_id if no user given
            owner_dict = gist.get('owner', {})
            if owner_dict:
                user = owner_dict['login']
            else:
                user = 'anonymous'
            new_url = u"{format}/gist/{user}/{gist_id}".format(
                format=self.format_prefix, user=user, gist_id=gist_id)
            if filename:
                new_url = new_url + "/" + filename
            self.redirect(self.from_base(new_url))
            return

        files = gist['files']
        many_files_gist = (len(files) > 1)

        if not many_files_gist and not filename:
            filename = list(files.keys())[0]

        if filename and filename in files:
            file = files[filename]
            if (file['type'] or '').startswith('image/'):
                app_log.debug("Fetching raw image (%s) %s/%s: %s", file['type'], gist_id, filename, file['raw_url'])
                response = yield self.fetch(file['raw_url'])
                # use raw bytes for images:
                content = response.body
            elif file['truncated']:
                app_log.debug("Gist %s/%s truncated, fetching %s", gist_id, filename, file['raw_url'])
                response = yield self.fetch(file['raw_url'])
                content = response_text(response, encoding='utf-8')
            else:
                content = file['content']

            # Enable a binder navbar icon if a binder base URL is configured
            executor_url = self.BINDER_PATH_TMPL.format(
                binder_base_url=self.binder_base_url,
                user=user.rstrip('/'),
                gist_id=gist_id,
                path=quote(filename)
            ) if self.binder_base_url else None

            if not many_files_gist or filename.endswith('.ipynb'):
                yield self.finish_notebook(
                    content,
                    file['raw_url'],
                    provider_url=gist['html_url'],
                    executor_url=executor_url,
                    msg="gist: %s" % gist_id,
                    public=gist['public'],
                    **self.PROVIDER_CTX
                )
            else:
                self.set_header('Content-Type', file.get('type') or 'text/plain')
                # cannot redirect because of X-Frame-Content
                self.finish(content)
                return

        elif filename:
            raise web.HTTPError(404, "No such file in gist: %s (%s)", filename, list(files.keys()))
        else:
            entries = []
            ipynbs = []
            others = []

            for file in files.values():
                e = {}
                e['name'] = file['filename']
                if file['filename'].endswith('.ipynb'):
                    e['url'] = quote('/%s/%s' % (gist_id, file['filename']))
                    e['class'] = 'fa-book'
                    ipynbs.append(e)
                else:
                    gist_url = os.environ.get('GIST_URL', 'https://gist.github.com/')
                    provider_url = gist_url + u"{user}/{gist_id}#file-{clean_name}".format(
                        user=user,
                        gist_id=gist_id,
                        clean_name=clean_filename(file['filename']),
                    )
                    e['url'] = provider_url
                    e['class'] = 'fa-share'
                    others.append(e)

            entries.extend(ipynbs)
            entries.extend(others)

            # Enable a binder navbar icon if a binder base URL is configured
            executor_url = self.BINDER_TMPL.format(
                binder_base_url=self.binder_base_url,
                user=user.rstrip('/'),
                gist_id=gist_id
            ) if self.binder_base_url else None

            html = self.render_template(
                'treelist.html',
                entries=entries,
                tree_type='gist',
                tree_label='gists',
                user=user.rstrip('/'),
                provider_url=gist['html_url'],
                executor_url=executor_url,
                **self.PROVIDER_CTX
            )
            yield self.cache_and_finish(html)


class GistRedirectHandler(BaseHandler):
    """redirect old /<gist-id> to new /gist/<gist-id>"""
    def get(self, gist_id, file=''):
        new_url = '%s/gist/%s' % (self.format_prefix, gist_id)
        if file:
            new_url = "%s/%s" % (new_url, file)

        app_log.info("Redirecting %s to %s", self.request.uri, new_url)
        self.redirect(self.from_base(new_url))


def default_handlers(handlers=[], **handler_names):
    """Tornado handlers"""

    gist_handler = _load_handler_from_location(handler_names['gist_handler'])
    user_gists_handler = _load_handler_from_location(handler_names['user_gists_handler'])

    return handlers + [
        (r'/gist/([^\/]+/)?([0-9]+|[0-9a-f]{20,})', gist_handler, {}),
        (r'/gist/([^\/]+/)?([0-9]+|[0-9a-f]{20,})/(?:files/)?(.*)', gist_handler, {}),
        (r'/([0-9]+|[0-9a-f]{20,})', GistRedirectHandler, {}),
        (r'/([0-9]+|[0-9a-f]{20,})/(.*)', GistRedirectHandler, {}),
        (r'/gist/([^\/]+)/?', user_gists_handler, {}),
    ]


def uri_rewrites(rewrites=[]):
    gist_rewrites = [
        (r'^([a-f0-9]+)/?$',
            u'/{0}'),
        (r'^https?://gist.github.com/([^\/]+/)?([a-f0-9]+)/?$',
            u'/{1}'),
    ] 
    # github enterprise
    if os.environ.get('GIST_URL', '') != '':
        gist_url = os.environ.get('GIST_URL')
        gist_rewrites.extend([
            # embedded in URL
            (r'^' + gist_url + r'([^\/]+/)?([a-f0-9]+)/?$',
                u'/{1}'),
        ])

    return gist_rewrites + rewrites
