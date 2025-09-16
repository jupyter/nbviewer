# -----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------
import errno
import io
import os
from datetime import datetime
from urllib.parse import urlparse

import boto3
import botocore
from tornado import iostream
from tornado import web

from .. import _load_handler_from_location
from ...utils import url_path_join
from ..base import cached
from ..base import RenderingHandler


class S3Handler(RenderingHandler):
    """Renderer for s3://

    Serving notebooks from S3 buckets
    """

    def initialize(self, **kwargs):
        self.s3_client = boto3.client("s3")
        self._downloadable_data = None
        self._downloaded_path = None
        super().initialize(**kwargs)

    async def download(self, path):
        """Download the notebook"""
        headers = await self.get_notebook_headers(path)
        filename = os.path.basename(path)
        self.set_header("Content-Length", headers["ContentLength"])
        # Escape commas to workaround Chrome issue with commas in download filenames
        self.set_header(
            "Content-Disposition",
            "attachment; filename={};".format(filename.replace(",", "_")),
        )
        if self._downloaded_path == path and self._downloadable_data is not None:
            content = self._downloadable_data
        else:
            content = await self.read_s3_file(path)

        if isinstance(content, bytes):
            content = [content]
        for chunk in content:
            try:
                self.write(chunk)
                await self.flush()
            except iostream.StreamClosedError:
                return

    async def get_notebook_data(self, path):
        """Get additional notebook data"""
        is_download = self.get_query_arguments("download")
        if is_download:
            await self.download(path)
            return

        return path

    async def get_notebook_headers(self, path):
        """Get the size of a notebook file."""
        o = urlparse(path)
        bucket = o.netloc
        key = o.path[1:]
        self.log.debug("Getting headers for %s from %s", key, bucket)
        try:
            head = self.s3_client.head_object(Bucket=bucket, Key=key)
        except botocore.exceptions.ClientError as ex:
            if ex.response["Error"]["Code"] == "404":
                self.log.info("The notebook %s does not exist.", path)
                raise web.HTTPError(404)
            raise ex
        return head

    async def read_s3_file(self, path):
        """Download the notebook file from s3."""
        o = urlparse(path)
        bucket = o.netloc
        key = o.path[1:]
        s3_file = io.BytesIO()
        self.log.debug("Reading %s from %s", key, bucket)
        try:
            self.s3_client.download_fileobj(bucket, key, s3_file)
        except botocore.exceptions.ClientError as ex:
            if ex.response["Error"]["Code"] == "404":
                self.log.info("The notebook %s does not exist.", path)
                raise web.HTTPError(404)
            raise ex
        s3_file.seek(0)
        self.log.debug("Done downloading.")
        self._downloadable_data = s3_file.read().decode("utf-8")
        self._downloaded_path = path
        return self._downloadable_data

    async def deliver_notebook(self, path):
        nbdata = await self.read_s3_file(path)

        # Explanation of some kwargs passed into `finish_notebook`:
        # breadcrumbs: list of dict
        #     Breadcrumb 'name' and 'url' to render as links at the top of the notebook page
        # title: str
        #     Title to use as the HTML page title (i.e., text on the browser tab)
        await self.finish_notebook(
            nbdata,
            download_url="?download",
            msg="file from s3: %s" % path,
            public=False,
            breadcrumbs=[],
            title=os.path.basename(path),
        )

    @cached
    async def get(self, path):
        """Get an s3 notebook

        Parameters
        ==========
        path: str
            s3 uri
        """
        fullpath = await self.get_notebook_data(path)

        # get_notebook_data returns None if a directory is to be shown or a notebook is to be downloaded,
        # i.e. if no notebook is supposed to be rendered, making deliver_notebook inappropriate
        if fullpath is not None:
            await self.deliver_notebook(fullpath)


def default_handlers(handlers=[], **handler_names):
    """Tornado handlers"""

    s3_handler = _load_handler_from_location(handler_names["s3_handler"])

    return handlers + [(r"/(s3%3A//.*)", s3_handler, {})]


def uri_rewrites(rewrites=[]):
    return [
        (r"^(s3://.*)$", "{0}"),
    ]
