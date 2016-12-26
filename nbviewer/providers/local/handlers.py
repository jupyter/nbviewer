#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import errno
import io
import os
from datetime import datetime

from tornado import (
    gen,
    web,
)
from tornado.log import app_log

from ...utils import url_path_join
from ..base import (
    cached,
    RenderingHandler,
)


class LocalFileHandler(RenderingHandler):
    """Renderer for /localfile

    Serving notebooks from the local filesystem
    """
    @property
    def localfile_path(self):
        return os.path.abspath(self.settings.get('localfile_path', ''))

    @cached
    @gen.coroutine
    def get(self, path):
        abspath = os.path.abspath(os.path.join(
            self.localfile_path,
            path
        ))

        if not abspath.startswith(self.localfile_path):
            app_log.warn("directory traversal attempt: '%s'" %
                         self.localfile_path)
            raise web.HTTPError(404)

        if not os.path.exists(abspath):
            raise web.HTTPError(404)

        if os.path.isdir(abspath):
            html = self.show_dir(abspath, path)
            raise gen.Return(self.cache_and_finish(html))

        try:
            with io.open(abspath, encoding='utf-8') as f:
                nbdata = f.read()
        except IOError as ex:
            if ex.errno == errno.EACCES:
                # py2/3: can't read the file, so don't give away it exists
                raise web.HTTPError(404)
            raise ex

        yield self.finish_notebook(nbdata, download_url=path,
                                   msg="file from localfile: %s" % path,
                                   public=False,
                                   format=self.format,
                                   request=self.request)

    def show_dir(self,  abspath,  path):
        """Render the directory view template for a given filesystem path.

        Parameters
        ==========
        abspath: string
            Absolute path on disk to show
        path: string
            URL path equating to the path on disk

        Returns
        =======
        str
            Rendered HTML
        """
        base_url = '/localfile'

        breadcrumbs = [{
            'url': url_path_join(self.base_url, base_url),
            'name': 'home'
        }]
        breadcrumbs.extend(self.breadcrumbs(path, base_url))

        entries = []
        dirs = []
        ipynbs = []

        try:
            contents = os.listdir(abspath)
        except IOError as ex:
            if ex.errno == errno.EACCES:
                # py2/3: can't access the dir, so don't give away its presence
                raise web.HTTPError(404)

        for f in contents:
            absf = os.path.join(abspath, f)
            entry = {}
            entry['name'] = f

            # skip hidden or "hidden" files
            if f.startswith('.') or f.startswith('_'):
                continue
            elif os.path.isdir(absf):
                if not os.access(absf, os.X_OK | os.R_OK):
                    # skip directories we cannot visit
                    continue
                st = os.stat(absf)
                dt = datetime.utcfromtimestamp(st.st_mtime)
                entry['modtime'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                entry['url'] = url_path_join(base_url, path, f)
                entry['class'] = 'fa fa-folder-open'
                dirs.append(entry)
            elif f.endswith('.ipynb'):
                if not os.access(absf, os.R_OK):
                    # skip files we cannot read
                    continue
                st = os.stat(absf)
                dt = datetime.utcfromtimestamp(st.st_mtime)
                entry['modtime'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                entry['url'] = url_path_join(base_url, path, f)
                entry['class'] = 'fa fa-book'
                ipynbs.append(entry)

        dirs.sort(key=lambda e: e['name'])
        ipynbs.sort(key=lambda e: e['name'])

        entries.extend(dirs)
        entries.extend(ipynbs)

        html = self.render_template('dirview.html',
                                    entries=entries,
                                    breadcrumbs=breadcrumbs)
        return html
