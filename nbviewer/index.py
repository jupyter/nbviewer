#-----------------------------------------------------------------------------
#  Copyright (C) 2014 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

'''
Classes for Indexing Notebooks
'''

from tornado.log import app_log

import uuid
from elasticsearch import Elasticsearch

class Indexer():
    def index_notebook(self, notebook_url, notebook_contents):
        raise NotImplementedException("index_notebook not implemented")


class NoSearch(Indexer):
    def __init__(self):
        pass

    def index_notebook(self, notebook_url, notebook_contents):
        app_log.debug("Totally not indexing \"{}\"".format(notebook_url))
        pass

class ElasticSearch(Indexer):
    def __init__(self, host="127.0.0.1", port=9200):
      self.elasticsearch = Elasticsearch([{'host':host, 'port':port}])

    def index_notebook(self, notebook_url, notebook_contents, public=False):
        notebook_url = notebook_url.encode('utf-8')
        notebook_id = uuid.uuid5(uuid.NAMESPACE_URL, notebook_url)

        # Notebooks API Model
        # https://github.com/ipython/ipython/wiki/IPEP-16%3A-Notebook-multi-directory-dashboard-and-URL-mapping#notebooks-api
        body = {
         "content": notebook_contents,
         "public": public
        }

        resp = self.elasticsearch.index(index='notebooks',
                                        doc_type='ipynb',
                                        body=body,
                                        id=notebook_id.hex)
        if(resp['created']):
            app_log.info("Created new indexed notebook={}, public={}".format(notebook_url, public))
        else:
            app_log.error("Indexing old notebook={}, public={}".format(notebook_url, public, resp))
