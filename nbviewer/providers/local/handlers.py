#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

from datetime import datetime
import errno
import io
import os
import stat

from tornado import (
    gen,
    web,
    iostream,
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
    # cache key is full uri to avoid mixing download vs view paths
    _cache_key_attr = 'uri'
    # provider root path
    _localfile_path = '/localfile'

    @property
    def localfile_path(self):
        if self.settings.get('localfile_follow_symlinks'):
            return os.path.realpath(self.settings.get('localfile_path', ''))
        else:
            return os.path.abspath(self.settings.get('localfile_path', ''))

    def breadcrumbs(self, path):
        """Build a list of breadcrumbs leading up to and including the
        given local path.

        Parameters
        ----------
        path: str
            Relative path up to and including the leaf directory or file to include
            in the breadcrumbs list

        Returns
        -------
        list
            Breadcrumbs suitable for the link_breadcrumbs() jinja macro
        """
        breadcrumbs = [{
            'url': url_path_join(self.base_url, self._localfile_path),
            'name': 'home'
        }]
        breadcrumbs.extend(super(LocalFileHandler, self).breadcrumbs(path, self._localfile_path))
        return breadcrumbs

    @gen.coroutine
    def download(self, fullpath):
        """Download the file at the given absolute path.

        Parameters
        ==========
        fullpath: str
            Absolute path to the file
        """
        filename = os.path.basename(fullpath)
        st = os.stat(fullpath)

        self.set_header('Content-Length', st.st_size)
        # Escape commas to workaround Chrome issue with commas in download filenames
        self.set_header('Content-Disposition',
                        'attachment; filename={};'.format(filename.replace(',', '_')))

        content = web.StaticFileHandler.get_content(fullpath)
        if isinstance(content, bytes):
            content = [content]
        for chunk in content:
            try:
                self.write(chunk)
                yield self.flush()
            except iostream.StreamClosedError:
                return

    def can_show(self, path):
        """
        Generally determine whether the given path is displayable.
        This function is useful for failing fast - further checks may
        be applied at notebook render to confirm a file may be shown.

        """
        if self.settings.get('localfile_follow_symlinks'):
            fullpath = os.path.realpath(os.path.join(
                self.localfile_path,
                path
            ))
        else:
            fullpath = os.path.abspath(os.path.normpath(os.path.join(
                self.localfile_path,
                path
            )))

        if not fullpath.startswith(self.localfile_path):
            app_log.warn("directory traversal attempt: '%s'" %
                         fullpath)
            return False

        if not os.path.exists(fullpath):
            return False

        if any(part.startswith('.') or part.startswith('_')
               for part in fullpath.split(os.sep)):
            return False

        if not self.settings.get('localfile_any_user'):
            fstat = os.stat(fullpath)

            # Ensure the file/directory has other read access for all.
            if not fstat.st_mode & stat.S_IROTH:
                return False

            if os.path.isdir(fullpath) and not fstat.st_mode & stat.S_IXOTH:
                # skip directories we can't execute (i.e. list)
                return False

        return True

    @cached
    @gen.coroutine
    def get(self, path):
        """Get a directory listing, rendered notebook, or raw file
        at the given path based on the type and URL query parameters.

        If the path points to an accessible directory, render its contents.
        If the path points to an accessible notebook file, render it.
        If the path points to an accessible file and the URL contains a
        'download' query parameter, respond with the file as a download.

        Parameters
        ==========
        path: str
            Local filesystem path
        """
        fullpath = os.path.join(self.localfile_path, path)

        if not self.can_show(fullpath):
            raise web.HTTPError(404)

        if os.path.isdir(fullpath):
            html = self.show_dir(fullpath, path)
            raise gen.Return(self.cache_and_finish(html))

        is_download = self.get_query_arguments('download')
        if is_download:
            self.download(fullpath)
            return

        try:
            with io.open(fullpath, encoding='utf-8') as f:
                nbdata = f.read()
        except IOError as ex:
            if ex.errno == errno.EACCES:
                # py2/3: can't read the file, so don't give away it exists
                raise web.HTTPError(404)
            raise ex

        yield self.finish_notebook(nbdata,
                                   download_url='?download',
                                   msg="file from localfile: %s" % path,
                                   public=False,
                                   format=self.format,
                                   request=self.request,
                                   breadcrumbs=self.breadcrumbs(path),
                                   title=os.path.basename(path))

    def show_dir(self, fullpath, path):
        """Render the directory view template for a given filesystem path.

        Parameters
        ==========
        fullpath: string
            Absolute path on disk to show
        path: string
            URL path equating to the path on disk

        Returns
        =======
        str
            Rendered HTML
        """
        entries = []
        dirs = []
        ipynbs = []

        try:
            contents = os.listdir(fullpath)
        except IOError as ex:
            if ex.errno == errno.EACCES:
                # py2/3: can't access the dir, so don't give away its presence
                raise web.HTTPError(404)

        for f in contents:
            absf = os.path.join(fullpath, f)

            if not self.can_show(absf):
                continue

            entry = {}
            entry['name'] = f

            # We need to make UTC timestamps conform to true ISO-8601 by
            # appending Z(ulu). Without a timezone, the spec says it should be
            # treated as local time which is not what we want and causes
            # moment.js on the frontend to show times in the past or future
            # depending on the user's timezone.
            # https://en.wikipedia.org/wiki/ISO_8601#Time_zone_designators
            if os.path.isdir(absf):
                st = os.stat(absf)
                dt = datetime.utcfromtimestamp(st.st_mtime)
                entry['modtime'] = dt.isoformat() + 'Z'
                entry['url'] = url_path_join(self._localfile_path, path, f)
                entry['class'] = 'fa fa-folder-open'
                dirs.append(entry)
            elif f.endswith('.ipynb'):
                st = os.stat(absf)
                dt = datetime.utcfromtimestamp(st.st_mtime)
                entry['modtime'] = dt.isoformat() + 'Z'
                entry['url'] = url_path_join(self._localfile_path, path, f)
                entry['class'] = 'fa fa-book'
                ipynbs.append(entry)

        dirs.sort(key=lambda e: e['name'])
        ipynbs.sort(key=lambda e: e['name'])

        entries.extend(dirs)
        entries.extend(ipynbs)

        html = self.render_template('dirview.html',
                                    entries=entries,
                                    breadcrumbs=self.breadcrumbs(path),
                                    title=url_path_join(path, '/'))
        return html


def default_handlers(handlers=[]):
    """Tornado handlers"""

    return handlers + [
        (r'/localfile/?(.*)', LocalFileHandler),
    ]

