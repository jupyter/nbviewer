import os
import json
from unittest import TestCase

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class JSONTestCase(TestCase):
    json = "nbviewer/frontpage.json"

    def test_json(self):
        try:
            json.load(open(os.path.join(ROOT, self.json), "r"))
        except Exception as err:
            self.fail("%s failed to parse:  %s" % (self.json, err))


class BowerJSONTestCase(JSONTestCase):
    json = "nbviewer/static/bower.json"


class BowerRcJSONTestCase(JSONTestCase):
    json = "nbviewer/static/.bowerrc"


class NpmJSONTestCase(JSONTestCase):
    json = "package.json"
