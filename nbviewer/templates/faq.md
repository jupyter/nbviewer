{% extends "layout.html" %}

{% block body %}
{% filter markdown %}

# Frequently Asked Questions

### What is nbviewer?

IPython Notebook Viewer (or nbviewer in short) is a free webservice that allows
you to see **static html** versions of hosted notebook files.  As long as a
notebook is **publicly** available, by giving its url to nbviewer you should be
able to view it.

As we are big fan of [github](http://github.com) and
[gist](http://gist.github.com)s, we make them special, so that you can directly
browse github repository on nbviewer.

### How do you render notebook ? 

Nbviewer is base on `nbconvert` which is the part of IPython library that 
is used to convert `.ipynb` files to increasing number of other format. 
If you have IPython installed you can have access to the same functionality by invoking
`ipython nbconvert` at a command line. Starting to IPython 2.0 you should be able to get
static export of notebook using the `file` menu in the IPython notebook application.

### Where is it hosted ?

Nbviewer is hosted on [Rackspace](http://rackspace.com) that kindly offered us
hosting as we are an open source project. Thanks to them we are able to offer
nbconvert as a service for free. In the current architecture nbviewer is a
python app deployed with salt with 1 master process and 2 minions each get 15GB
Ram, 4vCPUs, and a bandwidht of 1Gbps. Rendered pages are cached using memcached, 
and asynchronous handeling of requests is done through tornado.

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

### Can I share notebooks from a private GitHub repository ?

No, you can't, but we are working on it. We'll be happy to have any help you can give us.
In the meantime, you can use a secret gist if you wish.

### There is a broken link.

Is the broken link on a notebook? If so, I suggest you contact the original author.
Otherwise, please open an issue on [our issue tracker](https://github.com/ipython/nbviewer/issues)
with the link to the broken page, and tell us which link is broken.
We'll do our best to fix it.

### How do you choose the featured notebooks ?

Featured notebooks are notebooks we found that we like. If you think some
should be removed, or others that should be added, feel free to contact us.
The best way would be to directly submit a pull request on GitHub.

### Can I run my own nbviewer ?

We do our best so that you can run it locally or on the cloud.
Please visit the [nbviewer github repository](https://github.com/ipython/nbviewer) for instructions.

### How can I contribute ?

You can submit pull request to [nbviewer github repository](https://github.com/ipython/nbviewer),
or [make a donation to ipython] so that we can and work on more awesome features.

### Can I use nbviewer to convert my notebook to something else than html ?

For the time beeing, no. We woudl like to allow that in a far future, but the
current architecture is already showing its limits with only html. You can 
already use local version of nbconvert to export to most format. You can still help
us by making a donation, or contribute with your time.



{% endfilter %}
{% endblock %}
