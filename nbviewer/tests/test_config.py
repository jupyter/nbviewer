import os
from subprocess import Popen
from .base import NBViewerTestCase
import sys

import requests

tmpl_fixture = "nbviewer/tests/templates"


class CustomTemplateStub(object):
    def test_used_custom_template(self):
        r = requests.get(self.url("/"))
        self.assertEqual(r.status_code, 200)
        self.assertIn('IT WORKED', r.content)
        self.assertNotIn('html', r.content)


class TemplatePathCLITestCase(NBViewerTestCase, CustomTemplateStub):
    @classmethod
    def get_server_args(cls):
        return super(TemplatePathCLITestCase, cls).get_server_args() + [
            '--template_path={}'.format(tmpl_fixture),
        ]
