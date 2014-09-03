from unittest import SkipTest

from .base import NBViewerTestCase

from nbviewer import index

class ElasticSearchTestCase(NBViewerTestCase):
    def test_finish_notebook(self):
        elasticsearch = index.ElasticSearch(host="127.0.0.1", port=9200)
        nb_contents = {}
        public=False