from unittest import skip

from .base import NBViewerTestCase
from nbviewer import index


class ElasticSearchTestCase(NBViewerTestCase):
    @skip("unconditionally skip")
    @classmethod
    def test_finish_notebook(self):
        pass
