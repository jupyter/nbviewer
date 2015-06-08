from unittest import TestCase

from ...utils import transform_ipynb_uri
from .handlers import uri_rewrites

class TestRewrite(TestCase):
    def test_raw1(self):
        uri = 'https://raw.githubusercontent.com/ipython/ipython/3.x/examples/Index.ipynb'
        rewrite = u'/github/ipython/ipython/blob/3.x/examples/Index.ipynb'
        new = transform_ipynb_uri(uri, rewrite_providers=['nbviewer.providers.github'])
        self.assertEqual(new, rewrite)

    def test_raw2(self):
        uri = 'https://github.com/ipython/ipython/blob/3.x/examples/Index.ipynb'
        rewrite = u'/github/ipython/ipython/blob/3.x/examples/Index.ipynb'
        new = transform_ipynb_uri(uri, rewrite_providers=['nbviewer.providers.github'])
        self.assertEqual(new, rewrite)

    def test_raw3(self):
        uri = 'https://github.com/ipython/ipython/raw/3.x/examples/Index.ipynb'
        rewrite = u'/github/ipython/ipython/blob/3.x/examples/Index.ipynb'
        new = transform_ipynb_uri(uri, rewrite_providers=['nbviewer.providers.github'])
        self.assertEqual(new, rewrite)

    def test_raw4(self):
        uri = 'https://raw.github.com/ipython/ipython/3.x/examples/Index.ipynb'
        rewrite = u'/github/ipython/ipython/blob/3.x/examples/Index.ipynb'
        new = transform_ipynb_uri(uri, rewrite_providers=['nbviewer.providers.github'])
        self.assertEqual(new, rewrite)

