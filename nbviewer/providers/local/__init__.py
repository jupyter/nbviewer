import os

from tornado.log import app_log

from ..base import Provider

from . import handlers as local_handlers


class LocalProvider(Provider):
    def options(self, *args):
        options = super(LocalProvider, self).options(*args)

        options.append(dict(
            name="localfiles",
            default="",
            help="Allow to serve local files under /localfile/* this can be a security risk"
        ))

        return options

    def enabled(self, options):
        """For backwards compatibility, `local` can be enabled by just
           specifying the `localfiles` path
        """
        return options["with_{}".format(self.spec_name)] or options.localfiles

    def handlers(self, handlers, options):
        """Tornado handlers"""

        if not options.localfiles or not os.path.exists(options.localfiles):
            raise ValueError(
                "If provider `local` is enabled, `localfiles` must be defined "
                "and be a valid path"
            )

        app_log.warning(
            "Serving local notebooks in %s, this can be a security risk",
            os.path.abspath(options.localfiles)
        )

        return handlers + [
            (r'/localfile/(.*)', local_handlers.LocalFileHandler),
        ]

    handlers.weight = 50
