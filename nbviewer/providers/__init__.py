def provider_handlers(providers=None):
    """Load tornado URL handlers from a list of dotted-notation modules
       which contain a `default_handlers` function 
       
       `default_handlers` should accept a list of handlers and returns an 
       augmented list of handlers: this allows the addition of, for
       example, custom URLs which should be intercepted before being
       handed to the basic `url` handler
    """

    handlers = []

    if providers is None:
        providers = ['nbviewer.providers.{}'.format(prov)
                     for prov in ['url', 'github', 'gist']]

    for provider in providers:
        try:
            mod = __import__(provider, fromlist=['default_handlers'])
        except:
            continue
        handlers = mod.default_handlers(handlers)

    return handlers


def provider_uri_rewrites(providers=None):
    """Load (regex, template) tuples from a list of dotted-notation modules 
       which contain a `uri_rewrites` function 
       
       `uri_rewrites` should accept a list of rewrites and returns an 
       augmented list of rewrites: this allows the addition of, for
       example, the greedy behavior of the `gist` and `github` providers
    """
    rewrites = []

    if providers is None:
        providers = ['nbviewer.providers.{}'.format(prov)
                     for prov in ['gist', 'github', 'dropbox', 'url']]

    for provider in providers:
        mod = __import__(provider, fromlist=['uri_rewrites'])
        rewrites = mod.uri_rewrites(rewrites)

    return rewrites
    