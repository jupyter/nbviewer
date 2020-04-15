import json
import os
from unittest import TestCase

from jsonschema import validate


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class JSONTestCase(TestCase):
    json = None
    schema = None

    def test_json(self):
        if not self.json:
            return

        try:
            json.load(open(os.path.join(ROOT, self.json), "r"))
        except Exception as err:
            self.fail("%s failed to parse:  %s" % (self.json, err))

    def test_schema(self):
        if not self.schema:
            return

        try:
            data = json.load(open(os.path.join(ROOT, self.json), "r"))
            schema = json.load(open(os.path.join(ROOT, self.schema), "r"))
            validate(data, schema)
        except Exception as err:
            self.fail(
                "%s failed to validate against %s:  %s" % (self.json, self.schema, err)
            )


class FrontpageJSONTestCase(JSONTestCase):
    json = "nbviewer/frontpage.json"
    schema = "nbviewer/frontpage.schema.json"


class BowerJSONTestCase(JSONTestCase):
    json = "nbviewer/static/bower.json"


class BowerRcJSONTestCase(JSONTestCase):
    json = "nbviewer/static/.bowerrc"


class NpmJSONTestCase(JSONTestCase):
    json = "package.json"
