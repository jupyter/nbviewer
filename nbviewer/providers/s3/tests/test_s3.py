# -----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------
import io
import json
from copy import deepcopy
from unittest.mock import patch

import boto3
import requests

from ....tests.base import FormatHTMLMixin
from ....tests.base import NBViewerTestCase


MOCK_NOTEBOOK = {
    "cells": [
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "b0939771-a810-4ee0-b440-dbbaeb4f1653",
            "metadata": {},
            "outputs": [],
            "source": [],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "cc0d476a-d09c-4919-8dd2-c8d67f7431b3",
            "metadata": {},
            "outputs": [],
            "source": [],
        },
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3 (ipykernel)",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.9.12",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


class MockBoto3:
    def download_fileobj(self, Bucket, Key, fileobj):
        """Mock downloading fileobjects"""
        data = deepcopy(MOCK_NOTEBOOK)
        data["cells"][0]["source"] = [f"print({Bucket})", f"print({Key})"]
        bin_data = json.dumps(data).encode("utf-8")
        fileobj.write(bin_data)

    def head_object(self, Bucket, Key):
        """Mock getting key headers"""
        output_file = io.BytesIO()
        f = self.download_fileobj(Bucket, Key, output_file)
        f.seek(0)
        return {"ContentLength": len(f.read())}


"""
# This test won't work because the server is started through subprocess.POpen, so we can't mock boto3.

class S3TestCase(NBViewerTestCase):

    @patch("boto3.client")
    def test_url(self, mock_boto3_client):
        mockBoto3 = MockBoto3()
        mock_boto3_client.return_value = mockBoto3
        with patch.object(mockBoto3, 'download_fileobj') as mock_download:
            bucket="my_bucket"
            key="my_file.ipynb"
            url = self.url(f"s3%3A//{bucket}/{key}")
            r = requests.get(url)
            self.assertEqual(r.status_code, 200)
            args = mock_download.call_args_list[-1][:2]
            self.assertEqual(args, (bucket, key))


class FormatHTMLLocalFileDefaultTestCase(S3TestCase, FormatHTMLMixin):
    pass
"""
