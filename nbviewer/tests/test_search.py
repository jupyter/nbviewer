from unittest import SkipTest

from .base import NBViewerTestCase

from nbviewer import search

class ElasticSearchTestCase(NBViewerTestCase):
    def test_finish_notebook(self):
        elasticsearch = search.ElasticSearch(host="127.0.0.1", port=9200)
        nb_contents = {}
        public=False
