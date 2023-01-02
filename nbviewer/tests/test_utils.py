# encoding: utf-8
# -----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------
from nbviewer import utils
from nbviewer.providers import default_rewrites
from nbviewer.providers import provider_uri_rewrites


def test_transform_ipynb_uri():
    test_data = (
        # GIST_RGX
        ("1234", "/1234"),
        ("1234/", "/1234"),
        # GIST_URL_RGX
        ("https://gist.github.com/user-name/1234", "/1234"),
        ("https://gist.github.com/user-name/1234/", "/1234"),
        # GITHUB_URL_RGX
        (
            "https://github.com/user-name_/repo-name_/blob/master/path/file.ipynb",
            "/github/user-name_/repo-name_/blob/master/path/file.ipynb",
        ),
        (
            "http://github.com/user-name_/repo-name_/blob/master/path/file.ipynb",
            "/github/user-name_/repo-name_/blob/master/path/file.ipynb",
        ),
        (
            "https://github.com/user-name_/repo-name_/tree/master/path/",
            "/github/user-name_/repo-name_/tree/master/path/",
        ),
        # GITHUB_USER_RGX
        ("ipy-thon", "/github/ipy-thon/"),
        # GITHUB_USER_REPO_RGX
        ("ipy-thon/ipy-thon", "/github/ipy-thon/ipy-thon/tree/master/"),
        # DropBox Urls
        ("http://www.dropbox.com/s/bar/baz.qux", "/url/dl.dropbox.com/s/bar/baz.qux"),
        (
            "https://www.dropbox.com/s/zip/baz.qux",
            "/urls/dl.dropbox.com/s/zip/baz.qux",
        ),
        (
            "https://www.dropbox.com/sh/mhviow274da2wly/CZKwRRcA0k/nested/furthernested/User%2520Interface.ipynb?dl=1",
            "/urls/dl.dropbox.com/sh/mhviow274da2wly/CZKwRRcA0k/nested/furthernested/User%2520Interface.ipynb",
        ),
        # HuggingFace urls
        (
            "https://huggingface.co/pceiyos/fake_news_detection_nlp/blob/main/Fake_News_Classificaton.ipynb",
            "/urls/huggingface.co/pceiyos/fake_news_detection_nlp/resolve/main/Fake_News_Classificaton.ipynb",
        ),
        (
            "https://huggingface.co/spaces/NimaBoscarino/climategan/blob/main/notebooks/plot_metrics.ipynb",
            "/urls/huggingface.co/spaces/NimaBoscarino/climategan/resolve/main/notebooks/plot_metrics.ipynb",
            # This ClimateGAN notebook is served over LFS (as the file is 17.1 MB)
        ),
        (
            "https://huggingface.co/spaces/dalle-mini/dalle-mini/blob/63679e968109278c5f0169100b1755bbda9f4bc6/tools/inference/inference_pipeline.ipynb",
            "/urls/huggingface.co/spaces/dalle-mini/dalle-mini/resolve/63679e968109278c5f0169100b1755bbda9f4bc6/tools/inference/inference_pipeline.ipynb",
            # This Dall-e mini notebook is hosted from a specific revision (= git commit)
        ),
        # URL
        ("https://example.org/ipynb", "/urls/example.org/ipynb"),
        ("http://example.org/ipynb", "/url/example.org/ipynb"),
        ("example.org/ipynb", "/url/example.org/ipynb"),
        ("example.org/ipynb", "/url/example.org/ipynb"),
        (
            "https://gist.github.com/user/1234/raw/a1b2c3/file.ipynb",
            "/urls/gist.github.com/user/1234/raw/a1b2c3/file.ipynb",
        ),
        (
            "https://gist.github.com/user/1234/raw/a1b2c3/file.ipynb?query=string&is=1",
            "/urls/gist.github.com/user/1234/raw/a1b2c3/file.ipynb/%3Fquery%3Dstring%26is%3D1",
        ),
    )
    uri_rewrite_list = provider_uri_rewrites(default_rewrites)
    for ipynb_uri, expected_output in test_data:
        output = utils.transform_ipynb_uri(ipynb_uri, uri_rewrite_list)
        assert output == expected_output, "%s => %s != %s" % (
            ipynb_uri,
            output,
            expected_output,
        )


def test_quote():
    tests = [
        ("hi", "hi"),
        ("hi", "hi"),
        ("hi", "hi"),
        (" /#", "%20/%23"),
        (" /#", "%20/%23"),
        (" /#", "%20/%23"),
        ("ü /é#/", "%C3%BC%20/%C3%A9%23/"),
        ("ü /é#/", "%C3%BC%20/%C3%A9%23/"),
        ("ü /é#/", "%C3%BC%20/%C3%A9%23/"),
    ]
    for s, expected in tests:
        quoted = utils.quote(s)
        assert quoted == expected
        assert type(quoted) == type(expected)
