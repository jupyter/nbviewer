# encoding: utf-8
#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

from nbviewer import utils
import nose.tools as nt

def test_transform_ipynb_uri():
    test_data = (
        # GIST_RGX
        ('1234',
        u'/1234'),
        ('1234/',
        u'/1234'),
        # GIST_URL_RGX
        ('https://gist.github.com/user-name/1234',
        u'/1234'),
        ('https://gist.github.com/user-name/1234/',
        u'/1234'),
        # GITHUB_URL_RGX
        ('https://github.com/user-name_/repo-name_/blob/master/path/file.ipynb',
        u'/github/user-name_/repo-name_/blob/master/path/file.ipynb'),
        ('http://github.com/user-name_/repo-name_/blob/master/path/file.ipynb',
        u'/github/user-name_/repo-name_/blob/master/path/file.ipynb'),
        ('https://github.com/user-name_/repo-name_/tree/master/path/',
        u'/github/user-name_/repo-name_/tree/master/path/'),
        # GITHUB_USER_RGX
        ('ipy-thon',
        u'/github/ipy-thon/'),
        # GITHUB_USER_REPO_RGX
        ('ipy-thon/ipy-thon',
        u'/github/ipy-thon/ipy-thon/tree/master/'),
        #DropBox Urls
        ( u'http://www.dropbox.com/s/bar/baz.qux',
          u'/url/dl.dropbox.com/s/bar/baz.qux'),
        ( u'https://www.dropbox.com/s/zip/baz.qux',
          u'/urls/dl.dropbox.com/s/zip/baz.qux'),
        ( u'https://www.dropbox.com/sh/mhviow274da2wly/CZKwRRcA0k/nested/furthernested/User%2520Interface.ipynb?dl=1',
          u'/urls/dl.dropbox.com/sh/mhviow274da2wly/CZKwRRcA0k/nested/furthernested/User%2520Interface.ipynb'),
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
        output = utils.transform_ipynb_uri(ipynb_uri)
        nt.assert_equal(output, expected_output, "%s => %s != %s" % (
            ipynb_uri, output, expected_output
        ))
    

def test_quote():
    tests = [
        ('hi', u'hi'),
        (u'hi', u'hi'),
        (b'hi', u'hi'),
        (' /#', u'%20/%23'),
        (b' /#', u'%20/%23'),
        (u' /#', u'%20/%23'),
        (u'ü /é#/', u'%C3%BC%20/%C3%A9%23/'),
        (u'ü /é#/'.encode('utf8'), u'%C3%BC%20/%C3%A9%23/'),
        ('ü /é#/', u'%C3%BC%20/%C3%A9%23/'),
    ]
    for s, expected in tests:
        quoted = utils.quote(s)
        assert quoted == expected
        assert type(quoted) == type(expected)
    
