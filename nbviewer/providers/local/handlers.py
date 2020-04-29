# -----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------
import errno
import io
import os
import stat
from datetime import datetime

from tornado import iostream
from tornado import web

from .. import _load_handler_from_location
from ...utils import url_path_join
from ..base import cached
from ..base import RenderingHandler


class LocalFileHandler(RenderingHandler):
    """Renderer for /localfile

    Serving notebooks from the local filesystem
    """

    # cache key is full uri to avoid mixing download vs view paths
    _cache_key_attr = "uri"
    # provider root path
    _localfile_path = "/localfile"

    @property
    def localfile_path(self):
        if self.settings.get("localfile_follow_symlinks"):
            return os.path.realpath(self.settings.get("localfile_path", ""))
        else:
            return os.path.abspath(self.settings.get("localfile_path", ""))

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
        breadcrumbs = [
            {"url": url_path_join(self.base_url, self._localfile_path), "name": "home"}
        ]
        breadcrumbs.extend(super().breadcrumbs(path, self._localfile_path))
        return breadcrumbs

    async def download(self, fullpath):
        """Download the file at the given absolute path.

        Parameters
        ==========
        fullpath: str
            Absolute path to the file
        """
        filename = os.path.basename(fullpath)
        st = os.stat(fullpath)

        self.set_header("Content-Length", st.st_size)
        # Escape commas to workaround Chrome issue with commas in download filenames
        self.set_header(
            "Content-Disposition",
            "attachment; filename={};".format(filename.replace(",", "_")),
        )

        content = web.StaticFileHandler.get_content(fullpath)
        if isinstance(content, bytes):
            content = [content]
        for chunk in content:
            try:
                self.write(chunk)
                await self.flush()
            except iostream.StreamClosedError:
                return

    def can_show(self, path):
        """
        Generally determine whether the given path is displayable.
        This function is useful for failing fast - further checks may
        be applied at notebook render to confirm a file may be shown.

        """
        if self.settings.get("localfile_follow_symlinks"):
            fullpath = os.path.realpath(os.path.join(self.localfile_path, path))
        else:
            fullpath = os.path.abspath(
                os.path.normpath(os.path.join(self.localfile_path, path))
            )

        if not fullpath.startswith(self.localfile_path):
            self.log.warn("Directory traversal attempt: '%s'" % fullpath)
            return False

        if not os.path.exists(fullpath):
            self.log.warn("Path: '%s' does not exist", fullpath)
            return False

        if any(
            part.startswith(".") or part.startswith("_")
            for part in fullpath.split(os.sep)
        ):
            return False

        if not self.settings.get("localfile_any_user"):
            fstat = os.stat(fullpath)

            # Ensure the file/directory has other read access for all.
            if not fstat.st_mode & stat.S_IROTH:
                self.log.warn("Path: '%s' does not have read permissions", fullpath)
                return False

            if os.path.isdir(fullpath) and not fstat.st_mode & stat.S_IXOTH:
                # skip directories we can't execute (i.e. list)
                self.log.warn("Path: '%s' does not have execute permissions", fullpath)
                return False

        return True

    async def get_notebook_data(self, path):
        fullpath = os.path.join(self.localfile_path, path)

        if not self.can_show(fullpath):
            self.log.info("Path: '%s' is not visible from within nbviewer", fullpath)
            raise web.HTTPError(404)

        if os.path.isdir(fullpath):
            html = self.show_dir(fullpath, path)
            await self.cache_and_finish(html)
            return

        is_download = self.get_query_arguments("download")
        if is_download:
            await self.download(fullpath)
            return

        return fullpath

    async def deliver_notebook(self, fullpath, path):
        try:
            with io.open(fullpath, encoding="utf-8") as f:
                nbdata = f.read()
        except IOError as ex:
            if ex.errno == errno.EACCES:
                # py3: can't read the file, so don't give away it exists
                self.log.info(
                    "Path : '%s' is not readable from within nbviewer", fullpath
                )
                raise web.HTTPError(404)
            raise ex

        # Explanation of some kwargs passed into `finish_notebook`:
        # breadcrumbs: list of dict
        #     Breadcrumb 'name' and 'url' to render as links at the top of the notebook page
        # title: str
        #     Title to use as the HTML page title (i.e., text on the browser tab)
        await self.finish_notebook(
            nbdata,
            download_url="?download",
            msg="file from localfile: %s" % path,
            public=False,
            breadcrumbs=self.breadcrumbs(path),
            title=os.path.basename(path),
        )

    @cached
    async def get(self, path):
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
        fullpath = await self.get_notebook_data(path)

        # get_notebook_data returns None if a directory is to be shown or a notebook is to be downloaded,
        # i.e. if no notebook is supposed to be rendered, making deliver_notebook inappropriate
        if fullpath:
            await self.deliver_notebook(fullpath, path)

    # Make available to increase modularity for subclassing
    # E.g. so subclasses can implement templates with custom logic
    # without having to copy-paste the entire show_dir method
    def render_dirview_template(self, entries, breadcrumbs, title, **namespace):
        """
        breadcrumbs: list of dict
            Breadcrumb 'name' and 'url' to render as links at the top of the notebook page
        title: str
            Title to use as the HTML page title (i.e., text on the browser tab)
        """
        return self.render_template(
            "dirview.html",
            entries=entries,
            breadcrumbs=breadcrumbs,
            title=title,
            **namespace
        )

    def show_dir(self, fullpath, path, **namespace):
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
                # can't access the dir, so don't give away its presence
                self.log.info(
                    "Contents of path: '%s' cannot be listed from within nbviewer",
                    fullpath,
                )
                raise web.HTTPError(404)

        for f in contents:
            absf = os.path.join(fullpath, f)

            if not self.can_show(absf):
                continue

            entry = {}
            entry["name"] = f

            # We need to make UTC timestamps conform to true ISO-8601 by
            # appending Z(ulu). Without a timezone, the spec says it should be
            # treated as local time which is not what we want and causes
            # moment.js on the frontend to show times in the past or future
            # depending on the user's timezone.
            # https://en.wikipedia.org/wiki/ISO_8601#Time_zone_designators
            if os.path.isdir(absf):
                st = os.stat(absf)
                dt = datetime.utcfromtimestamp(st.st_mtime)
                entry["modtime"] = dt.isoformat() + "Z"
                entry["url"] = url_path_join(self._localfile_path, path, f)
                entry["class"] = "fa fa-folder-open"
                dirs.append(entry)
            elif f.endswith(".ipynb"):
                st = os.stat(absf)
                dt = datetime.utcfromtimestamp(st.st_mtime)
                entry["modtime"] = dt.isoformat() + "Z"
                entry["url"] = url_path_join(self._localfile_path, path, f)
                entry["class"] = "fa fa-book"
                ipynbs.append(entry)

        dirs.sort(key=lambda e: e["name"])
        ipynbs.sort(key=lambda e: e["name"])

        entries.extend(dirs)
        entries.extend(ipynbs)

        html = self.render_dirview_template(
            entries=entries,
            breadcrumbs=self.breadcrumbs(path),
            title=url_path_join(path, "/"),
            **namespace
        )
        return html


def default_handlers(handlers=[], **handler_names):
    """Tornado handlers"""

    local_handler = _load_handler_from_location(handler_names["local_handler"])

    return handlers + [(r"/localfile/?(.*)", local_handler, {})]
