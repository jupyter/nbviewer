{% extends "layout.html" %}

{% block body %}

{% filter markdown(extensions=['headerid(level=3)','toc'], extension_configs= {'toc' : [('anchorlink', True)]}) %}

# Frequently Asked Questions

[TOC]

## What does 3Blades notebook viewer?

3Blades Notebook Viewer is a webservice that allows you to share **static html**
versions of notebook files hosted by 3Blades. This is a free service for 3Blades
users.

## I got a 5xx/4xx error on a notebook.

3Blades Notebook Viewer tries to get notebooks from the share URL given. If the
file does not exist on the system or if the share URL is no longer valid, then
you will get an error (typically 400). Check that the remote file still exists
and that you can convert it locally with `nbconvert`.

## How do you render notebooks?

The 3Blades Notebook Viewer uses IPython's `nbconvert` to export `.ipynb` files
to HTML.

With Jupyter, you should be able to export notebooks in other formats using the
`file` menu in the Jupyter notebook application.

## I want to remove/update a notebook from 3Blades Notebook Viewer.

The 3Blades Notebook Viewer does not store any notebooks.

To update a Notebook, login to [3Blades](https://go.3blades.io) and navigate to your
project page. Launch a new workspace and edit your Jupyter Notebook. Once saved,
your notebook will appear as updated in the 3Blades Notebook viewer.

# I have more questions...

Additional clarifications may be obtained by visiting our [support page](http://support.3blades.io). You may also open a support ticket so that your
request is assigned to someone in our staff.

{% endfilter %}
{% endblock %}
