#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

from tornado.log import app_log
from IPython.nbformat.current import reads_json

#-----------------------------------------------------------------------------
# 
#-----------------------------------------------------------------------------

class NbFormatError(Exception):
    pass

def render_notebook(exporter, json_notebook, url=None, forced_theme=None):
    app_log.info("rendering %d B notebook from %s", len(json_notebook), url)
    
    try:
        nb = reads_json(json_notebook)
    except ValueError:
        raise NbFormatError('Error reading JSON notebook')


    css_theme = nb.get('metadata', {}).get('_nbviewer', {}).get('css', None)

    if not css_theme or not css_theme.strip():
        # whitespace
        css_theme = None

    if forced_theme:
        css_theme = forced_theme

    # get the notebook title, if any
    try:
        name = nb.metadata.name
    except AttributeError:
        name = ''
    
    if not name and url is not None:
        name = url.rsplit('/')[-1]

    if not name.endswith(".ipynb"):
        name = name + ".ipynb"
    
    html, resources = exporter.from_notebook_node(nb)

    config = {
            'download_name': name,
            'css_theme': css_theme,
            }
    return html, config
