#-----------------------------------------------------------------------------
#  Copyright (C) 2015 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

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

    def test_slides(nb, json):
        """Determines if at least one cell has a non-blank or "-" as its
        metadata.slideshow.slide_type value.

        Parameters
        ----------
        nb: nbformat.notebooknode.NotebookNode
            Top of the parsed notebook object model
        json: str
            JSON source of the notebook, unused

        Returns
        -------
        bool
        """
        for cell in nb.cells:
            if (
                'metadata' in cell and
                'slideshow' in cell.metadata and
                cell.metadata.slideshow.get('slide_type', '-') != '-'
            ):
                return True
        return False

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
            'test': test_slides,
        },
        'script': {
            'label': 'Code',
            'icon': 'code',
            'content_type': 'text/plain; charset=UTF-8'
        }
    }
