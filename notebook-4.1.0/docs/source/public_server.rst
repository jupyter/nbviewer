.. _working_remotely:

Running a notebook server
=========================


The :doc:`Jupyter notebook <notebook>` web application is based on a
server-client structure.  The notebook server uses a :ref:`two-process kernel
architecture <ipython:ipythonzmq>` based on ZeroMQ_, as well as Tornado_ for
serving HTTP requests.

.. note::
   By default, a notebook server runs locally at 127.0.0.1:8888
   and is accessible only from `localhost`. You may access the
   notebook server from the browser using `http://127.0.0.1:8888`.

This document describes how you can
:ref:`secure a notebook server <notebook_server_security>` and how to
:ref:`run it on a public interface <notebook_public_server>`.

.. _ZeroMQ: http://zeromq.org

.. _Tornado: http://www.tornadoweb.org


.. _notebook_server_security:

Securing a notebook server
--------------------------

You can protect your notebook server with a simple single password by
configuring the :attr:`NotebookApp.password` setting in
:file:`jupyter_notebook_config.py`.

Prerequisite: A notebook configuration file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Check to see if you have a notebook configuration file,
:file:`jupyter_notebook_config.py`. The default location for this file
is your Jupyter folder in your home directory, ``~/.jupyter``.

If you don't already have one, create a config file for the notebook
using the following command::

  $ jupyter notebook --generate-config


Preparing a hashed password
~~~~~~~~~~~~~~~~~~~~~~~~~~~
You can prepare a hashed password using the function
:func:`notebook.auth.security.passwd`:

.. sourcecode:: ipython

    In [1]: from notebook.auth import passwd
    In [2]: passwd()
    Enter password:
    Verify password:
    Out[2]: 'sha1:67c9e60bb8b6:9ffede0825894254b2e042ea597d771089e11aed'

.. caution::

  :func:`~notebook.auth.security.passwd` when called with no arguments
  will prompt you to enter and verify your password such as
  in the above code snippet. Although the function can also
  be passed a string as an argument such as ``passwd('mypassword')``, please
  **do not** pass a string as an argument inside an IPython session, as it
  will be saved in your input history.

Adding hashed password to your notebook configuration file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You can then add the hashed password to your :file:`jupyter_notebook_config.py`.
The default location for this file :file:`jupyter_notebook_config.py` is in
your Jupyter folder in your home directory, ``~/.jupyter``, e.g.::

    c.NotebookApp.password = u'sha1:67c9e60bb8b6:9ffede0825894254b2e042ea597d771089e11aed'

Using SSL for encrypted communication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
When using a password, it is a good idea to also use SSL with a web certificate,
so that your hashed password is not sent unencrypted by your browser.

.. important::
   Web security is rapidly changing and evolving. We provide this document
   as a convenience to the user, and recommend that the user keep current on
   changes that may impact security, such as new releases of OpenSSL.
   The Open Web Application Security Project (`OWASP`_) website is a good resource
   on general security issues and web practices.

You can start the notebook to communicate via a secure protocol mode by setting
the ``certfile`` option to your self-signed certificate, i.e. ``mycert.pem``,
with the command::

    $ jupyter notebook --certfile=mycert.pem --keyfile mykey.key

.. tip::

    A self-signed certificate can be generated with ``openssl``.  For example,
    the following command will create a certificate valid for 365 days with
    both the key and certificate data written to the same file::

        $ openssl req -x509 -nodes -days 365 -newkey rsa:1024 -keyout mykey.key -out mycert.pem

When starting the notebook server, your browser may warn that your self-signed
certificate is insecure or unrecognized.  If you wish to have a fully
compliant self-signed certificate that will not raise warnings, it is possible
(but rather involved) to create one, as explained in detail in `this tutorial`__.

.. __: http://arstechnica.com/security/news/2009/12/how-to-get-set-with-a-secure-sertificate-for-free.ars

.. TODO: Find an additional resource that walks the user through this two-process step by step.

.. _OWASP: https://www.owasp.org


.. _notebook_public_server:

Running a public notebook server
--------------------------------

If you want to access your notebook server remotely via a web browser,
you can do so by running a public notebook server. For optimal security
when running a public notebook server, you should first secure the
server with a password and SSL/HTTPS as described in
:ref:`notebook_server_security`.

Start by creating a certificate file and a hashed password, as explained in
:ref:`notebook_server_security`.

If you don't already have one, create a
config file for the notebook using the following command line::

  $ jupyter notebook --generate-config

In the ``~/.jupyter`` directory, edit the notebook config file,
``jupyter_notebook_config.py``.  By default, the notebook config file has
all fields commented out. The minimum set of configuration options that
you should to uncomment and edit in :file:``jupyter_notebook_config.py`` is the
following::

     # Set options for certfile, ip, password, and toggle off browser auto-opening
     c.NotebookApp.certfile = u'/absolute/path/to/your/certificate/mycert.pem'
     c.NotebookApp.keyfile = u'/absolute/path/to/your/certificate/mykey.key'
     # Set ip to '*' to bind on all interfaces (ips) for the public server
     c.NotebookApp.ip = '*'
     c.NotebookApp.password = u'sha1:bcd259ccf...<your hashed password here>'
     c.NotebookApp.open_browser = False

     # It is a good idea to set a known, fixed port for server access
     c.NotebookApp.port = 9999

You can then start the notebook using the ``jupyter notebook`` command.

.. important::

    **Use 'https'.**
    Keep in mind that when you enable SSL support, you must access the
    notebook server over ``https://``, not over plain ``http://``.  The startup
    message from the server prints a reminder in the console, but *it is easy
    to overlook this detail and think the server is for some reason
    non-responsive*.

    **When using SSL, always access the notebook server with 'https://'.**

You may now access the public server by pointing your browser to
``https://your.host.com:9999`` where ``your.host.com`` is your public server's
domain.

Firewall Setup
~~~~~~~~~~~~~~

To function correctly, the firewall on the computer running the jupyter
notebook server must be configured to allow connections from client
machines on the access port ``c.NotebookApp.port`` set in
:file:``jupyter_notebook_config.py`` port to allow connections to the
web interface.  The firewall must also allow connections from
127.0.0.1 (localhost) on ports from 49152 to 65535.
These ports are used by the server to communicate with the notebook kernels.
The kernel communication ports are chosen randomly by ZeroMQ, and may require
multiple connections per kernel, so a large range of ports must be accessible.

Running the notebook with a customized URL prefix
-------------------------------------------------

The notebook dashboard, which is the landing page with an overview
of the notebooks in your working directory, is typically found and accessed
at the default URL ``http://localhost:8888/``.

If you prefer to customize the URL prefix for the notebook dashboard, you can
do so through modifying ``jupyter_notebook_config.py``. For example, if you
prefer that the notebook dashboard be located with a sub-directory that
contains other ipython files, e.g. ``http://localhost:8888/ipython/``,
you can do so with configuration options like the following (see above for
instructions about modifying ``jupyter_notebook_config.py``)::

    c.NotebookApp.base_url = '/ipython/'
    c.NotebookApp.webapp_settings = {'static_url_prefix':'/ipython/static/'}

Known issues
------------

Proxies
~~~~~~~

When behind a proxy, especially if your system or browser is set to autodetect
the proxy, the notebook web application might fail to connect to the server's
websockets, and present you with a warning at startup. In this case, you need
to configure your system not to use the proxy for the server's address.

For example, in Firefox, go to the Preferences panel, Advanced section,
Network tab, click 'Settings...', and add the address of the notebook server
to the 'No proxy for' field.

Docker CMD
~~~~~~~~~~

Using ``jupyter notebook`` as a
`Docker CMD <https://docs.docker.com/reference/builder/#cmd>`_ results in
kernels repeatedly crashing, likely due to a lack of `PID reaping
<https://blog.phusion.nl/2015/01/20/docker-and-the-pid-1-zombie-reaping-problem/>`_.
To avoid this, use the `tini <https://github.com/krallin/tini>`_ ``init`` as your
Dockerfile `ENTRYPOINT`::

  # Add Tini. Tini operates as a process subreaper for jupyter. This prevents
  # kernel crashes.
  ENV TINI_VERSION v0.6.0
  ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /usr/bin/tini
  RUN chmod +x /usr/bin/tini
  ENTRYPOINT ["/usr/bin/tini", "--"]

  EXPOSE 8888
  CMD ["jupyter", "notebook", "--port=8888", "--no-browser", "--ip=0.0.0.0"]
