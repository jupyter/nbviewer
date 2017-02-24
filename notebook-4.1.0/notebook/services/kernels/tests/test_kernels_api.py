"""Test the kernels service API."""

import json
import requests

from jupyter_client.kernelspec import NATIVE_KERNEL_NAME

from notebook.utils import url_path_join
from notebook.tests.launchnotebook import NotebookTestBase, assert_http_error

class KernelAPI(object):
    """Wrapper for kernel REST API requests"""
    def __init__(self, base_url):
        self.base_url = base_url

    def _req(self, verb, path, body=None):
        response = requests.request(verb,
                url_path_join(self.base_url, 'api/kernels', path), data=body)

        if 400 <= response.status_code < 600:
            try:
                response.reason = response.json()['message']
            except:
                pass
        response.raise_for_status()

        return response

    def list(self):
        return self._req('GET', '')

    def get(self, id):
        return self._req('GET', id)

    def start(self, name=NATIVE_KERNEL_NAME):
        body = json.dumps({'name': name})
        return self._req('POST', '', body)

    def shutdown(self, id):
        return self._req('DELETE', id)

    def interrupt(self, id):
        return self._req('POST', url_path_join(id, 'interrupt'))

    def restart(self, id):
        return self._req('POST', url_path_join(id, 'restart'))

class KernelAPITest(NotebookTestBase):
    """Test the kernels web service API"""
    def setUp(self):
        self.kern_api = KernelAPI(self.base_url())

    def tearDown(self):
        for k in self.kern_api.list().json():
            self.kern_api.shutdown(k['id'])

    def test_no_kernels(self):
        """Make sure there are no kernels running at the start"""
        kernels = self.kern_api.list().json()
        self.assertEqual(kernels, [])

    def test_default_kernel(self):
        # POST request
        r = self.kern_api._req('POST', '')
        kern1 = r.json()
        self.assertEqual(r.headers['location'], url_path_join(self.url_prefix, 'api/kernels', kern1['id']))
        self.assertEqual(r.status_code, 201)
        self.assertIsInstance(kern1, dict)

        report_uri = url_path_join(self.url_prefix, 'api/security/csp-report')
        expected_csp = '; '.join([
            "frame-ancestors 'self'",
            'report-uri ' + report_uri,
            "default-src 'none'"
        ])
        self.assertEqual(r.headers['Content-Security-Policy'], expected_csp)

    def test_main_kernel_handler(self):
        # POST request
        r = self.kern_api.start()
        kern1 = r.json()
        self.assertEqual(r.headers['location'], url_path_join(self.url_prefix, 'api/kernels', kern1['id']))
        self.assertEqual(r.status_code, 201)
        self.assertIsInstance(kern1, dict)

        report_uri = url_path_join(self.url_prefix, 'api/security/csp-report')
        expected_csp = '; '.join([
            "frame-ancestors 'self'",
            'report-uri ' + report_uri,
            "default-src 'none'"
        ])
        self.assertEqual(r.headers['Content-Security-Policy'], expected_csp)

        # GET request
        r = self.kern_api.list()
        self.assertEqual(r.status_code, 200)
        assert isinstance(r.json(), list)
        self.assertEqual(r.json()[0]['id'], kern1['id'])
        self.assertEqual(r.json()[0]['name'], kern1['name'])

        # create another kernel and check that they both are added to the
        # list of kernels from a GET request
        kern2 = self.kern_api.start().json()
        assert isinstance(kern2, dict)
        r = self.kern_api.list()
        kernels = r.json()
        self.assertEqual(r.status_code, 200)
        assert isinstance(kernels, list)
        self.assertEqual(len(kernels), 2)

        # Interrupt a kernel
        r = self.kern_api.interrupt(kern2['id'])
        self.assertEqual(r.status_code, 204)

        # Restart a kernel
        r = self.kern_api.restart(kern2['id'])
        rekern = r.json()
        self.assertEqual(rekern['id'], kern2['id'])
        self.assertEqual(rekern['name'], kern2['name'])

    def test_kernel_handler(self):
        # GET kernel with given id
        kid = self.kern_api.start().json()['id']
        r = self.kern_api.get(kid)
        kern1 = r.json()
        self.assertEqual(r.status_code, 200)
        assert isinstance(kern1, dict)
        self.assertIn('id', kern1)
        self.assertEqual(kern1['id'], kid)

        # Request a bad kernel id and check that a JSON
        # message is returned!
        bad_id = '111-111-111-111-111'
        with assert_http_error(404, 'Kernel does not exist: ' + bad_id):
            self.kern_api.get(bad_id)

        # DELETE kernel with id
        r = self.kern_api.shutdown(kid)
        self.assertEqual(r.status_code, 204)
        kernels = self.kern_api.list().json()
        self.assertEqual(kernels, [])

        # Request to delete a non-existent kernel id
        bad_id = '111-111-111-111-111'
        with assert_http_error(404, 'Kernel does not exist: ' + bad_id):
            self.kern_api.shutdown(bad_id)
