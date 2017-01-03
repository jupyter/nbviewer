#-----------------------------------------------------------------------------
#  Copyright (C) 2015 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import re
import os

from nbconvert.exporters.export import exporter_map


def default_formats():
    """
    Return the currently-implemented formats.

    These are not classes, but maybe should be: would they survive pickling?

    - exporter:
        an Exporter subclass.
        if not defined, and key is in nbconvert.export.exporter_map, it will be added
        automatically
    - nbconvert_template:
        the name of the nbconvert template to add to config.ExporterClass
    - test:
        a function(notebook_object, notebook_json)
        conditionally offer a format based on content if truthy. see
        `RenderingHandler.filter_exporters`
    - postprocess:
        a function(html, resources)
        perform any modifications to html and resources after nbconvert
    - content_Type:
        a string specifying the Content-Type of the response from this format.
        Defaults to  text/html; charset=UTF-8
    """

    return {
        'html': {
            'nbconvert_template': 'basic',
            'label': 'Notebook',
            'icon': 'book'
        },
        'slides': {
            'nbconvert_template': 'slides_reveal',
            'label': 'Slides',
            'icon': 'gift',
            'test': lambda nb, json: '"slideshow"' in json,
        },
        'script': {
            'label': 'Code',
            'icon': 'code',
            'content_type': 'text/plain; charset=UTF-8'
        }
    }


def configure_formats(options, config, log, formats=None):
    """
    Format-specific configuration.
    """
    if formats is None:
        formats = default_formats()

    # This would be better defined in a class
    config.HTMLExporter.template_file = 'basic'
    config.SlidesExporter.template_file = 'slides_reveal'

    config.TemplateExporter.template_path = [
        os.path.join(os.path.dirname(__file__), "templates", "nbconvert")
    ]

    for key, format in formats.items():
        exporter_cls = format.get("exporter", exporter_map[key])
        if options.processes:
            # can't pickle exporter instances,
            formats[key]["exporter"] = exporter_cls
        else:
            formats[key]["exporter"] = exporter_cls(config=config, log=log)

    return formats
