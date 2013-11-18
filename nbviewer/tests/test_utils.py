#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

from nbviewer.utils import transform_ipynb_uri

def test_transform_ipynb_uri():
    test_data = (
        # GIST_RGX
        ('1234',
        u'/1234'),
        ('1234/',
        u'/1234'),
        # GIST_URL_RGX
        ('https://gist.github.com/username/1234',
        u'/1234'),
        ('https://gist.github.com/username/1234/',
        u'/1234'),
        # GITHUB_URL_RGX
        ('https://github.com/user/repo/blob/master/path/file.ipynb',
        u'/github/user/repo/blob/master/path/file.ipynb'),
        ('http://github.com/user/repo/blob/master/path/file.ipynb',
        u'/github/user/repo/blob/master/path/file.ipynb'),
        # URL
        ('https://example.org/ipynb',
        u'/urls/example.org/ipynb'),
        ('http://example.org/ipynb',
        u'/url/example.org/ipynb'),
        ('example.org/ipynb',
        u'/url/example.org/ipynb'),
        (u'example.org/ipynb',
        u'/url/example.org/ipynb'),
        ('https://gist.github.com/user/1234/raw/a1b2c3/file.ipynb',
        u'/urls/gist.github.com/user/1234/raw/a1b2c3/file.ipynb'),
    )
    for (ipynb_uri, expected_output) in test_data:
        output = transform_ipynb_uri(ipynb_uri)
        assert output == expected_output
    
