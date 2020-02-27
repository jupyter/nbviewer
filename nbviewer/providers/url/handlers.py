#-----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

from urllib.parse import urlparse
from urllib import robotparser

from tornado import (
    httpclient,
    web,
)
from tornado.escape import url_unescape

from ...utils import (
    quote,
    response_text,
)

from ..base import (
    cached,
    RenderingHandler,
)

from .. import _load_handler_from_location

class URLHandler(RenderingHandler):
    """Renderer for /url or /urls"""
    async def get_notebook_data(self, secure, netloc, url):
        proto = 'http' + secure
        netloc = url_unescape(netloc)

        if '/?' in url:
            url, query = url.rsplit('/?', 1)
        else:
            query = None

        remote_url = u"{}://{}/{}".format(proto, netloc, quote(url))

        if query:
            remote_url = remote_url + '?' + query
        if not url.endswith('.ipynb'):
            # this is how we handle relative links (files/ URLs) in notebooks
            # if it's not a .ipynb URL and it is a link from a notebook,
            # redirect to the original URL rather than trying to render it as a notebook
            refer_url = self.request.headers.get('Referer', '').split('://')[-1]
            if refer_url.startswith(self.request.host + '/url'):
                self.redirect(remote_url)
                return

        parse_result = urlparse(remote_url)

        robots_url = parse_result.scheme + "://" + parse_result.netloc + "/robots.txt"

        public = False # Assume non-public

        try:
            robots_response = await self.fetch(robots_url)
            robotstxt = response_text(robots_response)
            rfp = robotparser.RobotFileParser()
            rfp.set_url(robots_url)
            rfp.parse(robotstxt.splitlines())
            public = rfp.can_fetch('*', remote_url)
        except httpclient.HTTPError as e:
            self.log.debug("Robots.txt not available for {}".format(remote_url),
                    exc_info=True)
            public = True
        except Exception as e:
            self.log.error(e)

        return remote_url, public

    async def deliver_notebook(self, remote_url, public):
        response = await self.fetch(remote_url)

        try:
            nbjson = response_text(response, encoding='utf-8')
        except UnicodeDecodeError:
            self.log.error("Notebook is not utf8: %s", remote_url, exc_info=True)
            raise web.HTTPError(400)

        await self.finish_notebook(nbjson, download_url=remote_url,
                                   msg="file from url: %s" % remote_url,
                                   public=public,
                                   request=self.request)

    @cached
    async def get(self, secure, netloc, url):
        remote_url, public = await self.get_notebook_data(secure, netloc, url)

        await self.deliver_notebook(remote_url, public)

def default_handlers(handlers=[], **handler_names):
    """Tornado handlers"""

    url_handler = _load_handler_from_location(handler_names['url_handler'])

    return handlers + [
        (r'/url(?P<secure>[s]?)/(?P<netloc>[^/]+)/(?P<url>.*)', url_handler, {}),
    ]


def uri_rewrites(rewrites=[]):
    return rewrites + [
        ('^http(s?)://(.*)$', u'/url{0}/{1}'),
        ('^(.*)$', u'/url/{0}'),
    ]
