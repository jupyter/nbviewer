#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import io
import os
# For use with DynamoDB
import boto3

from tornado import (
    gen,
    web,
)
from tornado.log import app_log

from ..base import (
    cached,
    RenderingHandler,
)

# Get the service resource.
dynamodb = boto3.resource('dynamodb')
# Get environment (dev, staging or production)
dynamodb-table = os.environ.get('DYNAMODB_TABLE', None)

class LocalFileHandler(RenderingHandler):
    """Renderer for /localfile

    Serving notebooks from the local filesystem
    """
    @cached
    @gen.coroutine
    def get(self, path):

        file_name = path.split('/')[-1]
        hash_value = file_name.split('.')[0]
        # path = dynamo_json[hash_value]

        ####
        # BEGIN DYNAMODB
        ####
        table = dynamodb.Table(dynamodb-table)
        response = table.get_item(
            Key={
                'hashId': hash_value
            }
        )
        item = response['Item']
        path = item['path']
        ####
        # END DYNAMODB
        ####

        localfile_path = os.path.abspath(
            self.settings.get('localfile_path', ''))

        abspath = os.path.abspath(os.path.join(
            localfile_path,
            path
        ))

        app_log.info("looking for file: '%s'" % abspath)

        if not abspath.startswith(localfile_path):
            app_log.warn("directory traversal attempt: '%s'" % localfile_path)
            raise web.HTTPError(404)

        if not os.path.exists(abspath):
            raise web.HTTPError(404)

        with io.open(abspath, encoding='utf-8') as f:
            nbdata = f.read()

        yield self.finish_notebook(nbdata, download_url=path,
                                   msg="file from localfile: %s" % path,
                                   public=False,
                                   format=self.format,
                                   request=self.request)
