import os
from subprocess import Popen
from .base import NBViewerTestCase
import sys
import requests
from tornado.ioloop import IOLoop
from nbviewer.app import main

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


class TemplatePathEnvTestCase(NBViewerTestCase, CustomTemplateStub):

    @classmethod
    def _server_main(cls):
        cls._server_loop = loop = IOLoop()
        loop.make_current()
        cls._server_loop.add_callback(cls._start_evt.set)

        # Set environment variable
        os.environ['NBVIEWER_TEMPLATE_PATH'] = tmpl_fixture

        main(['', '--port=%d' % cls.port] + cls.get_server_args())
        loop.close(all_fds=True)
