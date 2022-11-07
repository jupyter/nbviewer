from unittest import skip

from .base import NBViewerTestCase


class ElasticSearchTestCase(NBViewerTestCase):
    @skip("unconditionally skip")
    @classmethod
    def test_finish_notebook(self):
        pass
