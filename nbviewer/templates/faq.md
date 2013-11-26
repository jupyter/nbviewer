{% extends "layout.html" %}

{% block body %}
{% filter markdown %}

# Frequently Asked Questions

### What is nbviewer?

IPython Notebook Viewer (or nbviewer in short) is a free webservice that allows you
to see **static html** versions of hosted notebook files.
As long as a notebook is **publicly** available,
by giving its url to nbviewer you should be able to view it.

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
In the meantime, you can use a secret gist if you wish.

### Images do not show in nbviewer!

Did you upload your images next to the ipynb file you are sharing? Perhaps
you used the incorrect absolute `/files/` prefix instead of the relative `files/`?

### There is a broken link.

Is the broken link on a notebook? If so, I suggest you contact the original author.
Otherwise, please open an issue on [our issue tracker](https://github.com/ipython/nbviewer/issues)
with the link to the broken page, and tell us which link is broken.
We'll do our best to fix it.

### How do you choose the featured notebooks?

Featured notebooks are notebooks we found that we like. If you think some
should be removed, or others that should be added, feel free to contact us.
The best way would be to directly submit a pull request on GitHub.

### Can I convert my notebook to something other than HTML?

If you want to convert a notebook file to another format,
you should have a look at [nbconvert](https://github.com/ipython/nbconvert).
It is the notebook conversion library used by nbviewer,
and supports many more customizations and formats than what is used by nbviewer.

## More questions

### Can I run my own nbviewer?

Yes, please visit the [nbviewer github repository](https://github.com/ipython/nbviewer) for instructions.

### How can I contribute?

You can submit pull request to [nbviewer github repository](https://github.com/ipython/nbviewer),
or [make a donation to ipython] so that we can pay for hosting and work on awesome features.

### Are there easter eggs on nbviewer?

Yes, you'll probably need more than your mouse to find them.


{% endfilter %}
{% endblock %}
