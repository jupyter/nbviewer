{% extends "layout.html" %}

{% block body %}
{% filter markdown %}

#Frequently Asked Questions

### What is NBviewer ?

IPython Notebook Viewer (or NBviewer in short) is a free webservice that allow you
to see **static html** version of hosted notebooks files. As long as a notebook is **publicly** availlabe, by giving its url to nbviewer you should be able to view it.

### I Want to remove/update a notebook on nbviewer.

We do not store any notebook on the nbviewer website, you have to find the origin place where the notebook is hosted to update/remove it. The update can take some time to appear on nbviewer as we cache rendered notebook for efficiency reason. 

### I can't share this notebook I'm working on...

You can't directly share url of notebook you are working on as the server is
probably running on a local machine (url stat with `127.0.0.1` or `localhost`
or needs authentication (you have to type a password to acces your notebook).
You will have to put the notebook file on a publicy availlable url. We
recomment using [github](https://github.com) [gists](https://gist.github.com) that are full
blown [git](http://git-scm.com/) repository.

### Can I share notebook which are on github private repository.

No, you can't, but we are working on it. We'll be happy to have any help you can give us.
In the mean time, you can use secret gist if you wish. 

### Images does not show in nbviewer ! 

Did you uploaded you images next to the ipynb file you are sharing ? Perhaps
you used `/files/` prefix instead of `files/` ? 

### There is a broken link on one page  ?

Is the broken link on one notebook ? If so, I suggest you contact the original
author.  Otherwise, please open an issue on [our issue tracker](https://github.com/ipython/nbviewer/issues) 
with the link to the broken page, and tell us which link is broken, we'll do our best to
fix it.

### How do you choose the feature notebook ?

Featured notebook are some notebook we fond where great. If you think some
should be removed, or others should be added, feel free to contact us, the best
would be to directly submit a pull request on github.

### Can I convert to something else than HTML ? 

If you want to convert a ipynb file to a cleaner html and/or other format, you
should have a look at [nbconvert](https://github.com/ipython/nbconvert). It is
the notebook conversion library nbviewer uses to 

## Advance question

### Can I run my own nbviewer ? 

Yes, please come to [nbviewer github repository](https://github.com/ipython/nbviewer) for instruction. 

### How can I contribute. 

You can submit pull request tp [nbviewer github repository](https://github.com/ipython/nbviewer), or [make a donation to ipython] so that we can pay for hosting and work on awsome feature.

### Is there easter eggs on nbviewer. 

Yes, you'll probably need more than your mouse to find them.









{% endfilter %}
{% endblock %}
