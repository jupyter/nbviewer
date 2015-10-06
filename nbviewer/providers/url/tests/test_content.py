# -*- coding: utf-8 -*-

from ....tests.async_base import AsyncNbviewerTestCase


class ForceUTF8TestCase(AsyncNbviewerTestCase):
    def test_utf8(self):
        """ #507, bitbucket returns no content headers, but _is_ serving utf-8
        """
        response = self.fetch(
            '/urls/bitbucket.org/sandiego206/asdasd/raw/master/Untitled.ipynb'
        )
        self.assertEqual(response.code, 200)
        self.assertIn("ñ", response.body)
