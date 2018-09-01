{% extends "layout.html" %}

{% block body %}

{% filter markdown(extensions=['headerid(level=2)','toc'], extension_configs= {'toc' : [('anchorlink', True)]}) %}

# Frequently Asked Questions

[TOC]

## What is nbviewer?

[nbviewer](https://github.com/jupyter/nbviewer)
is a web application that lets you enter the URL of a Jupyter Notebook file,
renders that notebook as a static HTML web page, and gives you a stable link to
that page which you can share with others. nbviewer also supports
browsing collections of notebooks (e.g., in a GitHub repository) and
rendering notebooks in other formats (e.g., slides, scripts).

nbviewer is an open source project under the larger [Project
Jupyter](https://jupyter.org) initiative along with other projects like [Jupyter
Notebook](https://github.com/jupyter/notebook),
[JupyterLab](https://github.com/jupyterlab/jupyterlab), and
[JupyterHub](https://github.com/jupyterhub/jupyterhub).

## What is nbviewer.jupyter.org?

Project Jupyter runs a free, public instance of nbviewer at
https://nbviewer.jupyter.org. You can use it to render Jupyter
Notebooks or browse notebook collection on GitHub. In either case, the notebooks
must have **public** web URLs.

The homepage of nbviewer.jupyter.org includes some examples for you to try.

## How does nbviewer render notebooks?

nbviewer is written in Python and JavaScript,
uses [nbconvert](https://github.com/jupyter/nbconvert) to render notebooks, and
uses [Tornado](https://github.com/tornadoweb/tornado) as its web server.

You can [install
nbconvert](https://nbconvert.readthedocs.io/en/stable/install.html) locally and
run `jupyter nbconvert` to get the same functionality (and more). See the
[nbconvert documentation](https://nbconvert.readthedocs.io/) for details.

## Can nbviewer run my Python, Julia, R, Scala, etc. notebooks?

nbviewer does not execute notebooks, It only renders the cell inputs and outputs
saved in a notebook document as a web page.

[mybinder.org] is another Jupyter-sponsored web service for launching full
Jupyter Notebook servers in the cloud, preconfigured

TODO

## Why does the Execute on Binder button not appear for a notebook?

## Why does the Execute on Binder button lead to a Binder failure?

## Why does a notebook not run correctly after I click the Execute on Binder button?

## Do interactive JavaScript widgets work in nbviewer rendered pages?

TODO

## Can I view a private notebook on nbviewer?

nbviewer.jupyter.org can only render notebooks that it can access on the public
Internet. If you are working on a notebook on your local machine, you need to
publish that notebook somewhere with a public URL (e.g., in a [GitHub
repository](https://github.com), as a [gist](https://gist.github.com)) in order
for nbviewer.jupyter.org to render it.

Hosting your own nbviewer server opens additional avenues for rendering private
notebooks. For example, an nbviewer server on your university network can render
notebook files accessible via URLs on that network. Please see the README in the
[nbviewer repository on GitHub](https://github.com/jupyter/nbviewer) for
instructions and options.

## Why do I get a 404: Not Found error from nbviewer?

The URL you are visiting most likely points to a notebook that was moved or
deleted. If you clicked a link on a site that lead to the 404 error page, we
suggest you contact the site auownerthor to report the broken link. If a
notebook author gave you URL to view their work, we recommend asking them for an
updated link.

If you notice one of the links on the nbviewer.jupyter.org, please report it as
a bug in the [nbviewer issue
tracker](https://github.com/jupyter/nbviewer/issues).

## Why do I get a 4xx error when I try to view a notebook?

nbviewer fetches notebooks from upstream providers (e.g., GitHub, GitHub gists,
a public webserver) which host the the notebook files. You will see 4xx errors
if the provider doesn't respond, the file nbviewer receives is invalid, the file
is not publicly accessible, and so on.

If you believe nbviewer is incorrectly showing a 4xx error for an accessible,
valid notebook URL, please file a bug in the [nbviewer issue
tracker](https://github.com/jupyter/nbviewer/issues).

## Why do I get a 5xx error when I try to view a notebook?

TODO

If it's a 5xx error, it's probably a [bug](https://github.com/ipython/nbviewer/issues).

## Why is nbviewer showing an outdated version of my notebook?

nbviewer caches rendered notebooks to cut down on rendering time for popular
notebooks. The cache duration on nbviewer.jupyter.org is approximately 10
minutes. To invalidate the cache and force nbviewer to re-render a notebook
page, append `?flush_cache=true` to your URL.

## How do you choose the notebooks features on the nbviewer.jupyter.org homepage?

TODO

Featured notebooks are notebooks we found that we like. If you think some
should be removed, or others that should be added, feel free to contact us.
The best way would be to directly submit a pull request on GitHub.

## How can I remove a notebook from nbviewer?

TODO:

The Notebook Viewer does not store any notebooks.
You have to find the original place where the notebook is hosted to update/remove it.

## Can I use nbviewer to convert my notebook to a format other than HTML?

TODO

Not yet, but we plan to allow that in the future. You can
already use `ipython nbconvert` locally to export to many formats. You can still help
us by making a donation or contributing with your time.

## Where is nbviewer.jupyter.org hosted?

[Rackspace](https://developer.rackspace.com/?nbviewer=awesome) graciously hosts
nbviewer.jupyter.org. Thanks to Rackspace, we are able to provider a public
nbviewer instance as a free service.

## Can I access nbviewer.jupyter.org over https?

Yes. Please do.

## Can I run my own nbviewer server?

Yes, absolutely. Please see the README in the [nbviewer repository on
GitHub](https://github.com/jupyter/nbviewer) for instructions and options.

## How can I report a bug with nbviewer or suggest a feature?

Please select the appropriate issue template in the [nbviewer issue tracker on GitHub](https://github.com/jupyter/nbviewer).

## Are there useful tools that work with nbviewer?

* [Open in nbviewer](http://jiffyclub.github.io/open-in-nbviewer/) - browser extensions and bookmarklets for opening the current URL in nbviewer
* [gist extension](https://github.com/minrk/ipython_extensions#gist) - publish a notebook as a GitHub Gist and view it on nbviewer

## Where can I ask additional questions?

TODO

{% endfilter %}
{% endblock %}
