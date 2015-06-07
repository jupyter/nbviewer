#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import io
import os

from tornado import (
    gen,
    web,
)
from tornado.log import app_log

from ..base import (
    cached,
    RenderingHandler,
)


class LocalFileHandler(RenderingHandler):
    """Renderer for /localfile

    Serving notebooks from the local filesystem
    """
    @cached
    @gen.coroutine
    def get(self, path):
        root = self.settings['localfile_path']

        abspath = os.path.abspath(os.path.join(root, path))

        app_log.info("looking for file `{}` in `{}`".format(abspath, root))

        if not abspath.startswith(root):
            app_log.warn("unsafe path requested: `{}`"
                         .format(path))
            raise web.HTTPError(400)
        elif not os.path.exists(abspath):
            raise web.HTTPError(404)

        with io.open(abspath, encoding='utf-8') as f:
            nbdata = f.read()

        yield self.finish_notebook(nbdata, download_url=path,
                                   msg="file from localfile: %s" % path,
                                   public=False,
                                   format=self.format,
                                   request=self.request)
