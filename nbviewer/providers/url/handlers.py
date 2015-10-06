#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

try:
    # py3
    from urllib.parse import urlparse
    from urllib import robotparser
except ImportError:
    from urlparse import urlparse
    import robotparser

from tornado import (
    gen,
    httpclient,
    web,
)
from tornado.log import app_log
from tornado.escape import url_unescape

from ...utils import (
    quote,
    response_text,
)

from ..base import (
    cached,
    RenderingHandler,
)


class URLHandler(RenderingHandler):
    """Renderer for /url or /urls"""
    @cached
    @gen.coroutine
    def get(self, secure, netloc, url):
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
            robots_response = yield self.fetch(robots_url)
            robotstxt = response_text(robots_response)
            rfp = robotparser.RobotFileParser()
            rfp.set_url(robots_url)
            rfp.parse(robotstxt.splitlines())
            public = rfp.can_fetch('*', remote_url)
        except httpclient.HTTPError as e:
            app_log.debug("Robots.txt not available for {}".format(remote_url),
                    exc_info=True)
            public = True
        except Exception as e:
            app_log.error(e)


        response = yield self.fetch(remote_url)

        try:
            nbjson = response_text(response, encoding='utf-8')
        except UnicodeDecodeError:
            app_log.error("Notebook is not utf8: %s", remote_url, exc_info=True)
            raise web.HTTPError(400)

        yield self.finish_notebook(nbjson, download_url=remote_url,
                                   msg="file from url: %s" % remote_url,
                                   public=public,
                                   request=self.request,
                                   format=self.format)


def default_handlers(handlers=[]):
    """Tornado handlers"""

    return handlers + [
        (r'/url([s]?)/([^/]+)/(.*)', URLHandler),
    ]


def uri_rewrites(rewrites=[]):
    return rewrites + [
        ('^http(s?)://(.*)$', u'/url{0}/{1}'),
        ('^(.*)$', u'/url/{0}'),
    ]
