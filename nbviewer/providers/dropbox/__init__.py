from ..base import Provider


class DropboxProvider(Provider):
    """A simple provider for rewriting public Dropbox URLs
    """
    context = {
        'provider_label': 'Dropbox',
        'provider_icon': 'drobbox'
    }

    def uri_rewrites(self, rewrites, options):
        """rewrite from the dropbox client URLs to the canonical sharing URL
        """
        return rewrites + [
            (r'^http(s?)://www.dropbox.com/(sh?)/(.+)$',
                u'/url{0}/dl.dropbox.com/{1}/{2}'),
        ]

    uri_rewrites.weight = 400
