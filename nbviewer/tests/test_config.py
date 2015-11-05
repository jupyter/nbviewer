import os
from subprocess import Popen
from .base import NBViewerTestCase

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
    def get_server_cmd(cls):
        return super(TemplatePathCLITestCase, cls).get_server_cmd() + [
            '--template_path={}'.format(tmpl_fixture),
        ]


class TemplatePathEnvTestCase(NBViewerTestCase, CustomTemplateStub):
    @classmethod
    def setup_class(cls):
        server_cmd = cls.get_server_cmd()
        devnull = open(os.devnull, 'w')
        cls.server = Popen(
            server_cmd,
            stdout=devnull,
            stderr=devnull,
            env=dict(os.environ, NBVIEWER_TEMPLATE_PATH=tmpl_fixture)
        )
        cls.wait_until_alive()
