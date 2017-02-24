def uri_rewrites(rewrites=[]):
    return rewrites + [
        (r'^(.+?)/(.+?)(\.ipynb)?$',
            u'/shared/{0}/{1}.ipynb'),
    ]
