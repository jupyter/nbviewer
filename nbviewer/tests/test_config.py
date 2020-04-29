import os
from subprocess import Popen

import requests

from .base import NBViewerTestCase

tmpl_fixture = "nbviewer/tests/templates"


class CustomTemplateStub(object):
    def test_used_custom_template(self):
        r = requests.get(self.url("/"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("IT WORKED", r.content)
        self.assertNotIn("html", r.content)


class TemplatePathCLITestCase(NBViewerTestCase, CustomTemplateStub):
    @classmethod
    def get_server_cmd(cls):
        return super().get_server_cmd() + ["--template-path={}".format(tmpl_fixture)]


class TemplatePathEnvTestCase(NBViewerTestCase, CustomTemplateStub):

    environment_variables = {"NBVIEWER_TEMPLATE_PATH": tmpl_fixture}
