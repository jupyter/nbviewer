#-----------------------------------------------------------------------------
#  Copyright (C) 2015 The Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

def uri_rewrites(rewrites=[]):
    return rewrites + [
        (r'^http(s?)://drive\.google\.com/file/d/([^/]*).*$',
            u'/url{0}/googledrive.com/host/{1}'),
        (r'^http(s?)://drive\.google\.com/open\?id=([^&#]*).*$',
            u'/url{0}/googledrive.com/host/{1}')
    ]
