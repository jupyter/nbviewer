from unittest import SkipTest

from .base import NBViewerTestCase

from nbviewer import search

class ElasticSearchTestCase(NBViewerTestCase):
    def test_index_notebook(self):
        elasticsearch = search.ElasticSearch(host="127.0.0.1", port=9200)
        assert elasticsearch.elasticsearch.host == "127.0.0.1"