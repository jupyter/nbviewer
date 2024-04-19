# -----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------
import errno
import os

import fsspec
from tornado import iostream
from tornado import web

from .. import _load_handler_from_location
from ...utils import url_path_join
from ..base import cached
from ..base import RenderingHandler

IGNORED_PROTOCOLS = {"http", "https"}
ALLOWED_PROTOCOLS = os.environ.get("FSSPEC_ALLOWED", "s3").split(",")
ALLOWED_DIR_LISTING = os.environ.get("FSSPEC_ALLOW_DIR_LISTING", True)


def build_url(protocol, url, *args):
    return url_path_join(f"/fsspec/{protocol}", url, *args)


class FsspecHandler(RenderingHandler):
    """

    Serving notebooks from the fsspec filesystems.
    """

    async def download(self, fs, url):
        """Download the file at the given url

        Parameters
        ==========
        fs: fsspec.AbstractFileSystem
            Filesystem object
        url: str
            URL of the file
        """

        with fs.open(url, "rb") as f:
            info = fs.info(url)
            filename = os.path.basename(url)

            self.set_header("Content-Length", info["size"])
            # Escape commas to workaround Chrome issue with commas in download filenames
            self.set_header(
                "Content-Disposition",
                "attachment; filename={};".format(filename.replace(",", "_")),
            )

            try:
                self.write(f.read())
                await self.flush()
            except iostream.StreamClosedError:
                return

    def can_show(self, protocol, url):
        """
        Generally determine whether the given path is displayable.
        This function is useful for failing fast - further checks may
        be applied at notebook render to confirm a file may be shown.

        """
        if protocol not in ALLOWED_PROTOCOLS:
            return False
        if not url:
            return False
        return True

    async def get_notebook_data(self, fs, protocol, url):

        if not self.can_show(protocol, url):
            self.log.info("Path: '%s' is not visible from within nbviewer", url)
            raise web.HTTPError(404)

        if ALLOWED_DIR_LISTING and fs.isdir(url):
            html = self.show_dir(fs, protocol, url)
            await self.cache_and_finish(html)
            return

        is_download = self.get_query_arguments("download")
        if is_download:
            await self.download(fs, url)
            return

        return url

    async def deliver_notebook(self, fs, protocol, path):
        try:
            with fs.open(path, encoding="utf-8") as f:
                nbdata = f.read()
        except OSError as ex:
            if ex.errno == errno.EACCES:
                # py3: can't read the file, so don't give away it exists
                self.log.info("Path : '%s' is not readable from within nbviewer", path)
                raise web.HTTPError(404)
            raise ex

        # Explanation of some kwargs passed into `finish_notebook`:
        # breadcrumbs: list of dict
        #     Breadcrumb 'name' and 'url' to render as links at the top of the notebook page
        # title: str
        #     Title to use as the HTML page title (i.e., text on the browser tab)
        breadcrumbs = [{"url": build_url(protocol, path, "../"), "name": "Up"}]
        self.log.info("Rendering notebook from path: %s", path)
        await self.finish_notebook(
            nbdata,
            download_url="?download",
            msg="file from location %s" % path,
            public=False,
            breadcrumbs=breadcrumbs,
            title=os.path.basename(path),
        )

    @cached
    async def get(self, protocol, url):
        """Get a directory listing, rendered notebook, or raw file
        at the given path based on the type and URL query parameters.

        If the path points to an accessible directory, render its contents.
        If the path points to an accessible notebook file, render it.
        If the path points to an accessible file and the URL contains a
        'download' query parameter, respond with the file as a download.

        Parameters
        ==========
        protocol: str
            Protocol of the file
        url: str
            URL of the file
        """

        if self.can_show(protocol, url) is False:
            self.log.info("Path: '%s' is not visible from within nbviewer", url)
            raise web.HTTPError(404)

        fs = fsspec.get_filesystem_class(protocol)()

        fullpath = await self.get_notebook_data(fs, protocol, url)

        # get_notebook_data returns None if a directory is to be shown or a notebook is to be downloaded,
        # i.e. if no notebook is supposed to be rendered, making deliver_notebook inappropriate
        if fullpath:
            await self.deliver_notebook(fs, protocol, url)

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
            **namespace,
        )

    def show_dir(self, fs, protocol, url):
        """Render the directory view template for a given filesystem path.

        Parameters
        ==========
        fs: fsspec.AbstractFileSystem
            Filesystem object
        url: str
            URL of the directory

        Returns
        =======
        str
            Rendered HTML
        """
        entries = []
        dirs = []
        ipynbs = []

        try:
            contents = fs.listdir(url)
        except OSError as ex:
            if ex.errno == errno.EACCES:
                # can't access the dir, so don't give away its presence
                self.log.info(
                    "Contents of path: '%s' cannot be listed from within nbviewer",
                    url,
                )
                raise web.HTTPError(404)

        for info in contents:

            entry = {}
            name = os.path.basename(info["name"])
            entry["name"] = name
            entry["url"] = build_url(protocol, url, name)

            # We need to make UTC timestamps conform to true ISO-8601 by
            # appending Z(ulu). Without a timezone, the spec says it should be
            # treated as local time which is not what we want and causes
            # moment.js on the frontend to show times in the past or future
            # depending on the user's timezone.
            # https://en.wikipedia.org/wiki/ISO_8601#Time_zone_designators

            if info["type"] == "directory":
                entry["class"] = "fa fa-folder-open"
                dirs.append(entry)
            elif info["type"] == "file" and name.endswith(".ipynb"):
                entry["class"] = "fa fa-book"
                ipynbs.append(entry)
            else:
                self.log.info(f"Ignored: {info}")

        dirs.sort(key=lambda e: e["name"])
        ipynbs.sort(key=lambda e: e["name"])

        entries.extend(dirs)
        entries.extend(ipynbs)

        breadcrumbs = [{"url": build_url(protocol, url, "../"), "name": "Up"}]
        html = self.render_dirview_template(
            entries=entries,
            breadcrumbs=breadcrumbs,
            title=url_path_join(url, "/"),
        )
        return html


def default_handlers(handlers=[], **handler_names):
    """Tornado handlers"""

    url_handler = _load_handler_from_location(handler_names["fsspec_handler"])
    return handlers + [(r"/fsspec/(?P<protocol>[^/]+)/(?P<url>.*)", url_handler, {})]


def uri_rewrites(rewrites=[]):
    protocols = (i for i in ALLOWED_PROTOCOLS)
    for protocol in protocols:
        rewrites.append((f"^{protocol}://(.*?)$", f"/fsspec/{protocol}" + "/{0}"))

    return rewrites
