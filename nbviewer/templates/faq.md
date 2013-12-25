{% extends "layout.html" %}

{% block body %}
{% filter markdown %}

# Frequently Asked Questions

### What is nbviewer?

IPython Notebook Viewer (or nbviewer in short) is a free webservice that allows
you to see **static html** versions of hosted notebook files.  As long as a
notebook is **publicly** available, by giving its url to nbviewer you should be
able to view it.

You can also directly browse collections of notebooks through github repositories directly on nbviewer


### I've got a 5xx/4xx error on a notebook.

Nbviewer tries to get notebooks from the url given. If the remote location
doesn't respond or the file nbviewer receives is not valid, you will get an
error (4xx). Check that the remote file still exists and that you can convert
it locally with nbconvert.


### How do you render notebooks?

Nbviewer uses IPython's `nbconvert` to export `.ipynb` to HTML.

If you have IPython installed you can have access to the same functionality
and many more formats by invoking
`ipython nbconvert` at a command line. Starting in IPython 2.0 you should be
able to export notebooks in other formats using the `file` menu in the IPython
notebook application.

### Where is nbviewer hosted?

Nbviewer is hosted on [Rackspace](http://rackspace.com) who kindly gives the IPython open source
project hosting. Thanks to them we are able to offer nbconvert as a service for free.

### I want to remove/update a notebook on nbviewer.

We do not store any notebooks on the nbviewer website.
You have to find the original place where the notebook is hosted to update/remove it.
The update can take some time to appear on nbviewer as we cache rendered
notebooks for a short period.

### I can't share this notebook I'm working on...

You can't directly share the url of a notebook you are working on as the server is
probably running on a local machine (url starts with `127.0.0.1` or `localhost`)
or needs authentication (you have to type a password to access your notebook).
You will have to put the notebook file on a publicly available url.
We recommend using [github](https://github.com) [gists](https://gist.github.com),
which are full blown [git](http://git-scm.com/) repositories.

### Can I share notebooks from a private GitHub repository?

No, you can't, but we are working on it. We'll be happy to have any help you can give us.
In the meantime, you can use a secret gist if you wish. You might be interested in running nbviewer
on your own machine or inside your network.

### Can I run my own nbviewer?

We do our best so that you can run it locally or on the cloud.
Please visit the [nbviewer github repository](https://github.com/ipython/nbviewer) for instructions.

### Can I access nbviewer over https?

You can, but you will probably get a warning that the website does not have a valid
certificate.  We are not sure it is worth paying for an SSL certificate as
nbviewer should not expose any sensitive information. If you need to embed an html notebook
on another site, please use local export with nbconvert.

### There is a broken link.

Is the broken link on a notebook? If so, we suggest you contact the original author.
Otherwise, please open an issue on [our issue tracker](https://github.com/ipython/nbviewer/issues)
with the link to the broken page, and tell us which link is broken.
We'll do our best to fix it.

### How do you choose the featured notebooks?

Featured notebooks are notebooks we found that we like. If you think some
should be removed, or others that should be added, feel free to contact us.
The best way would be to directly submit a pull request on GitHub.

### How can I contribute?

You can submit a pull request to [the nbviewer github repository](https://github.com/ipython/nbviewer),
or [make a donation to ipython](http://ipython.org/donate.html) so that we can work on more awesome features.

### Can I use nbviewer to convert my notebook to something else than html?

For the time being, no. We would like to allow that in the future. You can
already use a `ipython nbconvert` to export to most formats. You can still help
us by making a donation or contributing with your time.

## I have more questions...

If something was not clear or not present, do not hesitate to reach out to the [IPython mailing list](http://mail.scipy.org/mailman/listinfo/ipython-dev) or [make an issue on github](http://github.com/ipython/nbviewer/issues).

{% endfilter %}
{% endblock %}
