import requests

from ....tests.base import NBViewerTestCase


class BinderRunnerTestCase(NBViewerTestCase):
    def test_tree_has_binder(self):
        url = self.url('github/binder-project/example-requirements')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.text
        self.assertIn(
            'http://mybinder.org/repo/binder-project/example-requirements',
            html,
            "a binder URL appears on the page")

    def test_tree_has_no_binder(self):
        """Assumes binder cannot be build on binder"""
        url = self.url('github/binder-project/binder')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.text
        self.assertNotIn(
            'http://mybinder.org/repo/binder-project/binder',
            html,
            "a binder URL DOES NOT appears on the page")

    def test_notebook_has_binder(self):
        url = self.url('github/binder-project/example-requirements/'
                       'blob/master/index.ipynb')
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        html = r.text
        self.assertIn(
            'http://mybinder.org/repo/binder-project/example-requirements',
            html,
            "a binder URL appears on the page")
