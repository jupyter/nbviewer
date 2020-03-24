from .base import NBViewerTestCase

from unittest import skip
from nbviewer import index

class ElasticSearchTestCase(NBViewerTestCase):
    @skip
    @classmethod
    def test_finish_notebook(self):
        pass
