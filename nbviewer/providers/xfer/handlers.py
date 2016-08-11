def uri_rewrites(rewrites=[]):
    return rewrites + [
        (r'^(.+?)/(.+?)(\.ipynb)?$',
            u'/shared/notebooks/{0}/{1}.ipynb'),
    ]
