def provider_handlers(providers=None):
    """Load tornado URL handlers from a list of dotted-notation modules
       which contain a `default_handlers` function 
       
       `default_handlers` should accept a list of handlers and returns an 
       augmented list of handlers: this allows the addition of, for
       example, custom URLs which should be intercepted before being
       handed to the URL handler
    """

    handlers = []

    if providers is None:
        providers = ['nbviewer.providers.{}'.format(prov)
                     for prov in ['url', 'github', 'gist']]

    for provider in providers:
        mod = __import__(provider, fromlist=['default_handlers'])
        handlers = mod.default_handlers(handlers)

    return handlers
