{% extends "layout.html" %}

{% block body %}

<style>

.container{
    max-width:700px;
}

p {
    text-align:justify;
}

</style>

{% filter markdown(extensions=['headerid(level=3)','toc'], extension_configs= {'toc' : [('anchorlink', True)]}) %}

This web site does not host notebooks, it only renders notebooks available on other websites.

# Licence

[The code for this site](https://github.com/ipython/nbviewer)
is licensed under [BSD]("https://github.com/ipython/nbviewer/blob/master/LICENSE.txt),
thanks to all our [contributors](href="https://github.com/ipython/nbviewer/contributors).

# Hosting 

We are proudly hosted by <a href="http://www.rackspace.com">Rackspace</a>.

![rack](/static/img/Rackspace-Logo.jpg)


{% endfilter %}
{% endblock %}
