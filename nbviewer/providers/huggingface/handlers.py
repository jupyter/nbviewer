# -----------------------------------------------------------------------------
#  Copyright (C) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------


def uri_rewrites(rewrites=[]):
    return rewrites + [
        (
            r"^https://huggingface.co/(.+?)/blob/(.+?)$",
            "/urls/huggingface.co/{0}/resolve/{1}",
        )
    ]
