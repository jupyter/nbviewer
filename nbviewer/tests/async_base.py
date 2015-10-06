from tornado import testing
from tornado.escape import to_unicode

from .. import app


class AsyncNbviewerTestCase(testing.AsyncHTTPTestCase):
    """ Base case for testing the nbviewer app asynchronously
    """
    def get_app(self):
        """ create an nbviewer tornado app instance for testing
        """
        app.init_options()
        return app.make_app()

    def assertIn(self, observed, expected, *args, **kwargs):
        """ test whether the observed contains the expected, in utf-8
        """
        return super(AsyncNbviewerTestCase, self).assertIn(
            to_unicode(observed),
            to_unicode(expected),
            *args,
            **kwargs
        )

    def assertNotIn(self, observed, expected, *args, **kwargs):
        """ test whether the observed does not contain the expected, in utf-8
        """
        return super(AsyncNbviewerTestCase, self).assertNotIn(
            to_unicode(observed),
            to_unicode(expected),
            *args,
            **kwargs
        )
