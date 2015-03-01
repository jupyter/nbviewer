{% extends "layout.html" %}

{% block body %}

{% filter markdown(extensions=['headerid(level=3)','toc'], extension_configs= {'toc' : [('anchorlink', True)]}) %}

# Frequently Asked Questions

[TOC]

## What is this Notebook Viewer?

IPython Notebook Viewer is a free webservice that allows
you to share **static html** versions of hosted notebook files.  If a
notebook is **publicly** available, by giving its url to the Viewer, you should be
able to view it.

You can also directly browse collections of notebooks in public GitHub repositories,
for example the [IPython examples](/github/ipython/ipython/tree/2.x/examples).

## Bookmarklet and browser extensions

There are extensions and a bookmarklet for Chrome and Firefox   [here](http://jiffyclub.github.io/open-in-nbviewer/).

## I got a 5xx/4xx error on a notebook.

Notebook Viewer tries to get notebooks from the url given. If the remote location
doesn't respond or the file Notebook Viewer receives is not valid, you will get an
error (typically 400). Check that the remote file still exists and that you can convert
it locally with `nbconvert`.

If it's a 5xx error, it's probably a [bug](https://github.com/ipython/nbviewer/issues).


## How do you render notebooks?

The Notebook Viewer uses IPython's `nbconvert` to export `.ipynb` files to HTML.

If you have IPython installed you have access to the same functionality
and many more formats by invoking
`ipython nbconvert` at a command line. Starting in IPython 2.0, you should be
able to export notebooks in other formats using the `file` menu in the IPython
notebook application.

## Where is this Notebook Viewer hosted?

This Notebook Viewer instance is hosted on [Rackspace](https://developer.rackspace.com/?nbviewer=awesome), who kindly provide hosting for the IPython open source project. Thanks to Rackspace, we are able to operate nbconvert as a free service.

## I want to remove/update a notebook from Notebook Viewer.

The Notebook Viewer does not store any notebooks.
You have to find the original place where the notebook is hosted to update/remove it.
Updates occur automatically, but can take some time to appear, as we cache rendered
notebooks for approximately 10 minutes. To force an update, append `?flush_cache=true` 
to the viewer URL.

## I can't share this notebook I'm working on...

You can't directly share the url of a notebook you are working on as the server is
probably running on a local machine (url starts with `127.0.0.1` or `localhost`)
or needs authentication (you have to type a password to access your notebook).
You will have to put the notebook file somewhere with a publicly available url.
We recommend using [GitHub](https://github.com) or [gists](https://gist.github.com).

## Can I share notebooks from a private GitHub repository?

Not yet, but we would like to add this. We'll be happy to have any help you can offer.
In the meantime, you can use a secret gist if you wish. You might be interested in running a Viewer
on your own machine or inside your network.

## Can I run my own Notebook Viewer?

Yes, absolutely.
Please visit the [GitHub repository](https://github.com/ipython/nbviewer) for instructions.

## Can I access Notebook Viewer over https?

You can, but you will probably get a warning that the website does not have a valid
certificate.  We are not sure it is worth paying for an SSL certificate as
the viewer should not expose any sensitive information. If you need to embed an html notebook
on another site, please use local export with `nbconvert`.

## There is a broken link.

Is the broken link on a notebook? If so, we suggest you contact the original author.
Otherwise, please open an issue on [our issue tracker](https://github.com/ipython/nbviewer/issues)
with the link to the broken page, and tell us which link is broken.
We'll do our best to fix it.

## How do you choose the featured notebooks?

Featured notebooks are notebooks we found that we like. If you think some
should be removed, or others that should be added, feel free to contact us.
The best way would be to directly submit a pull request on GitHub.

## How can I contribute?

You can submit a [pull request](https://github.com/ipython/nbviewer),
or [make a donation to IPython](http://ipython.org/donate.html) so that we can work on more awesome features.

## Can I use the Notebook Viewer to convert my notebook to something other than html?

Not yet, but we plan to allow that in the future. You can
already use `ipython nbconvert` locally to export to many formats. You can still help
us by making a donation or contributing with your time.

# I have more questions...

If something was not clear or not present, do not hesitate to reach out to the [IPython mailing list](http://mail.scipy.org/mailman/listinfo/ipython-dev) or [open an issue on GitHub](http://github.com/ipython/nbviewer/issues).

{% endfilter %}
{% endblock %}
