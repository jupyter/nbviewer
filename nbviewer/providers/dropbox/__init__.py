from ..base import Provider


class DropboxProvider(Provider):
    """A simple provider for rewriting public dropbox URLs
    """
    # enable this by default
    default_enabled = True

    def uri_rewrites(self, rewrites, options):
        return rewrites + [
            (r'^http(s?)://www.dropbox.com/(sh?)/(.+)$',
                u'/url{0}/dl.dropbox.com/{1}/{2}'),
        ]

    uri_rewrites.weight = 400
