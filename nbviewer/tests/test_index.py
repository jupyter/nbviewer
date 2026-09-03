import requests

from .base import NBViewerTestCase


class TestNBViewer(NBViewerTestCase):

    def test_get_index(self):
        r = requests.get(self.url())
        r.raise_for_status()

    def test_static_files(self):
        r = requests.get(self.url("/static/img/nav_logo.svg"))
        r.raise_for_status()
        r = requests.get(self.url("/static/build/styles.css"))
        r.raise_for_status()
