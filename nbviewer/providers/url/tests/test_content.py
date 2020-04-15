# -*- coding: utf-8 -*-
import requests

from ....tests.base import NBViewerTestCase


class ForceUTF8TestCase(NBViewerTestCase):
    def test_utf8(self):
        """ #507, bitbucket returns no content headers, but _is_ serving utf-8
        """
        response = requests.get(
            self.url("/urls/bitbucket.org/sandiego206/asdasd/raw/master/Untitled.ipynb")
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("ñ", response.content)
