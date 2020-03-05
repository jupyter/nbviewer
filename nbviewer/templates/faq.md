{% extends "layout.html" %}

{% block body %}

<div class="col-md-10 col-md-offset-1">

{% filter markdown(extensions=['toc'], extension_configs= {'toc' : [('anchorlink', True)]}) %}

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

nbviewer does not execute notebooks. It only renders the inputs and outputs
saved in a notebook document as a web page.

[mybinder.org](https://mybinder.org/) is a separate web service that lets you
open notebooks notebooks in an executable environment, making your code
immediately reproducible by anyone, anywhere. nbviewer shows an *Execute on
Binder* icon in its navbar which

## Why does the Execute on Binder button not appear for a notebook?

nbviewer only supports launching notebooks stored on GitHub or as Gists on
Binder. Binder does support other providers directly on the mybinder.org site.

## Why does the Execute on Binder button lead to a Binder failure?

Binder tries to build a Docker image containing the notebooks and requirements
declared in a git repository. The build will fail if the repository has
a `Dockerfile`, `requirements.txt`, `environment.yaml`, etc. with issues. We
suggest letting the repository owner know about the problem or submitting a
pull request to help fix it.

## Why does a notebook not run correctly after I click the Execute on Binder button?

Binder builds a Docker image containing the notebooks in a git repository.
Those notebooks may have requirements to run correctly such as libraries and
data files. Binder can install these prerequisites as part of its build process,
if the git repository [declares them in a supported manner](https://mybinder.readthedocs.io/en/latest/using.html#preparing-a-repository-for-binder).

If a notebook does not run properly in its Binder environment, we suggest
letting the repository owner know about the problem or submitting a pull request
to help fix it.

## Does JavaScript embedded in notebooks work on nbviewer rendered pages?

Yes. This fact allows plots from plot.ly, Bokeh, and Altair to remain
interactive, for example. It also means arbitrary JavaScript maybe execute when
you visit the page, as it would on any page you visit on the Internet.

## Can I load a private notebook on nbviewer?

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
notebook author gave you the URL, we recommend asking them for an updated link.

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

## Why do I get a 5xx or fastly error when I try to view a notebook?

A 5xx error or an error page from fastly may indicate that the public
nbviewer.jupyter.org site is being redeployed or is down. If the problem
persists for more than a few minutes, please open a bug in the
[nbviewer issue tracker on GitHub](https://github.com/jupyter/nbviewer)
including the URL you are visiting and the error you receive.

## Why is nbviewer showing an outdated version of my notebook?

nbviewer caches rendered notebooks to cut down on rendering time for popular
notebooks. The cache duration on nbviewer.jupyter.org is approximately 10
minutes. To invalidate the cache and force nbviewer to re-render a notebook
page, append `?flush_cache=true` to your URL.

## How do you choose the notebooks featured on the nbviewer.jupyter.org homepage?

We originally selected notebooks that we found and liked. We are currently
soliciting links to refresh the home page using [a Google
Form](https://goo.gl/forms/WayjU9VW7MYvKSb12). You may also open an issue with
your suggestion.

## How can I remove a notebook from nbviewer?

nbviewer does not store any notebooks, it only renders notebooks stored
elsewhere on the web given their URLs. If you've found a notebook that you think
should be removed from the web, you'll need to locate where it is hosted (e.g.,
on GitHub) in order to update or remove it

## Can I use nbviewer to convert my notebook to a format other than HTML?

No. However, you can [install
nbconvert](https://nbconvert.readthedocs.io/en/stable/install.html) locally and
run `jupyter nbconvert` to convert notebook files to a variety of format. See
the [nbconvert documentation](https://nbconvert.readthedocs.io/) for details.

## Where is nbviewer.jupyter.org hosted?

[OVH](https://www.ovh.com) graciously hosts nbviewer.jupyter.org.
Thanks to OVH, we are able to provider a public nbviewer instance as a free service.

nbviewer was generously hosted by Rackspace until March, 2020.

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

Please post your questions about using nbviewer in the [Jupyter Community Forum](https://discourse.jupyter.org/) or in the [Jupyter Google
Group](https://groups.google.com/forum/#!forum/jupyter). If you would like to
propose an enhancement to nbviewer or file a bug report, please open an [issue
in the jupyter/nbviewer project on GitHub](https://github.com/jupyter/nbviewer).

{% endfilter %}

</div>

{% endblock %}
