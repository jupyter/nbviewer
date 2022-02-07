# -----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------


def uri_rewrites(rewrites=[]):
    return rewrites + [
        (
            r"^http(s?)://www.dropbox.com/(sh?)/(.+?)(\?dl=.)*$",
            "/url{0}/dl.dropbox.com/{1}/{2}",
        )
    ]
