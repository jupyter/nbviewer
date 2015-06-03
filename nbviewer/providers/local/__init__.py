import os

from tornado.log import app_log

from ..base import Provider

from . import handlers as local_handlers


class LocalProvider(Provider):
    """A provider for files accessible on the local filesystem

    """
    context = {
        'provider_label': 'Local Files',
    }

    def options(self):
        """For backwards compatibility, adds an un-prefixed `local` option
        """
        options = super(LocalProvider, self).options()

        options.append(dict(
            name="localfiles",
            default="",
            help="Local absolute/relative path from which to serve notebooks. \033[1;31mSecurity risk!\033[1;0m"
        ))

        return options

    def enabled(self, options):
        """For backwards compatibility, `local` can be enabled by just
           specifying the `localfiles` path
        """
        return options["with_{}".format(self.spec_name)] or options.localfiles

    def initialize(self, options):
        options.localfiles = os.path.abspath(options.localfiles)

    def handlers(self, handlers, options):
        """Tornado handlers
        """

        if not options.localfiles or not os.path.exists(options.localfiles):
            raise ValueError(
                "If provider `local` is enabled, `localfiles` must be defined "
                "and be a valid path"
            )

        app_log.warning(
            "Serving local notebooks in %s, this can be a security risk",
            options.localfiles
        )

        return handlers + [
            (r'/localfile/(.*)', local_handlers.LocalFileHandler),
        ]

    handlers.weight = 50
