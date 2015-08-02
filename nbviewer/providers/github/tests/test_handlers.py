# encoding: utf-8

from unittest import TestCase
from collections import OrderedDict

from ....utils import transform_ipynb_uri
from ..handlers import uri_rewrites

uri_rewrite_dict = OrderedDict()
uri_rewrite_dict.update(uri_rewrites())


class TestRewrite(TestCase):
    def assert_rewrite(self, uri, rewrite):
        new = transform_ipynb_uri(uri, uri_rewrite_dict)
        self.assertEqual(new, rewrite)

    def test_githubusercontent(self):
        uri = u'https://raw.githubusercontent.com/user/reopname/deadbeef/a mřížka.ipynb'
        rewrite = u'/github/user/reopname/blob/deadbeef/a mřížka.ipynb'
        self.assert_rewrite(uri, rewrite)

    def test_blob(self):
        uri = u'https://github.com/user/reopname/blob/deadbeef/a mřížka.ipynb'
        rewrite = u'/github/user/reopname/blob/deadbeef/a mřížka.ipynb'
        self.assert_rewrite(uri, rewrite)

    def test_raw_uri(self):
        uri = u'https://github.com/user/reopname/raw/deadbeef/a mřížka.ipynb'
        rewrite = u'/github/user/reopname/blob/deadbeef/a mřížka.ipynb'
        self.assert_rewrite(uri, rewrite)

    def test_raw_subdomain(self):
        uri = u'https://raw.github.com/user/reopname/deadbeef/a mřížka.ipynb'
        rewrite = u'/github/user/reopname/blob/deadbeef/a mřížka.ipynb'
        self.assert_rewrite(uri, rewrite)

    def test_tree(self):
        uri = u'https://github.com/user/reopname/tree/deadbeef/a mřížka.ipynb'
        rewrite = u'/github/user/reopname/tree/deadbeef/a mřížka.ipynb'
        self.assert_rewrite(uri, rewrite)

    def test_userrepo(self):
        uri = u'username/reponame'
        rewrite = u'/github/username/reponame/tree/master/'
        self.assert_rewrite(uri, rewrite)

    def test_user(self):
        uri = u'username'
        rewrite = u'/github/username/'
        self.assert_rewrite(uri, rewrite)
