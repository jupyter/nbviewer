#-----------------------------------------------------------------------------
#  Copyright (C) 2014 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

'''
import os
import requests
from elasticsearch import Elasticsearch

elasticsearch_endpoint = os.environ["ES_PORT_9200_TCP_ADDR"]
es = Elasticsearch([{'host':elasticsearch_endpoint, 'port':9200}])

notebook_request = requests.get("http://jakevdp.github.com/downloads/notebooks/XKCD_plots.ipynb")
es.index(index='nbviewer', doc_type='ipynb', body=notebook_request.text)
'''

from tornado.log import app_log

import uuid
from elasticsearch import Elasticsearch

class NoSearch():
  def __init__(self, host=None, port=None):
    pass

  def index_notebook(self, notebook_url, notebook_contents):
    app_log.debug("Totally not indexing \"{}\"".format(notebook_url))
    pass
  
class ElasticSearch():
  def __init__(self, host="127.0.0.1", port=9200):
    self.elasticsearch = Elasticsearch([{'host':host, 'port':port}])
  
  def index_notebook(self, notebook_url, notebook_contents):
    notebook_id = uuid.uuid5(uuid.NAMESPACE_URL, notebook_url)
    resp = self.elasticsearch.index(index='notebooks',
                                    doc_type='ipynb',
                                    body=notebook_contents,
                                    id=notebook_id.hex)
