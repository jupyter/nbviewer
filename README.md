**[Quick Run](#quick-run)** |
**[GitHub Enterprise](#github-enterprise)** |
**[Base URL](#base-url)** |
**[Local Development](#local-development)** |
**[Contributing](#contributing)** |
**[Extensions](#extending-the-notebook-viewer)** |
**[Configuration](#config-file-and-command-line-configuration)** |
**[Security](#securing-the-notebook-viewer)**


# Jupyter Notebook Viewer

[![Latest PyPI version](https://img.shields.io/pypi/v/nbviewer?logo=pypi)](https://pypi.python.org/pypi/nbviewer)
[![TravisCI build status](https://img.shields.io/travis/jupyter/nbviewer/master?logo=travis)](https://travis-ci.org/jupyter/nbviewer)
[![GitHub](https://img.shields.io/badge/issue_tracking-github-blue?logo=github)](https://github.com/jupyter/nbviewer/issues)
[![Gitter](https://img.shields.io/badge/social_chat-gitter-blue?logo=gitter)](https://gitter.im/jupyter/nbviewer)

Jupyter NBViewer is the web application behind
[The Jupyter Notebook Viewer](http://nbviewer.org),
which is graciously hosted by [OVHcloud](https://ovhcloud.com) and CDN services
provided by [fastly](https://www.fastly.com/).

Run this locally to get most of the features of nbviewer on your own network.

If you need help using or installing Jupyter Notebook Viewer, please use the [jupyter/help](https://github.com/jupyter/help) issue tracker. If you would like to propose an enhancement to nbviewer or file a bug report, please [open an issue here, in the jupyter/nbviewer project](https://github.com/jupyter/nbviewer).

## Quick Run

If you have `docker` installed, you can pull and run the currently built version of the Docker container by

```shell
docker pull jupyter/nbviewer
docker run -p 8080:8080 jupyter/nbviewer
```

It automatically gets built with each push to `master`, so you'll always be able to get the freshest copy.

For speed and friendliness to GitHub, be sure to set `GITHUB_OAUTH_KEY` and `GITHUB_OAUTH_SECRET`:

```shell
docker run -p 8080:8080 -e 'GITHUB_OAUTH_KEY=YOURKEY' \
                          -e 'GITHUB_OAUTH_SECRET=YOURSECRET' \
                          jupyter/nbviewer
```

Or to use your GitHub personal access token, you can just set `GITHUB_API_TOKEN`.


## S3 buckets
Files in S3 buckets can be access by their s3 uri like `s3://bucket/path/to/key`. This works directly for public buckets. If you want to access private buckets, you need to provide the s3 authentication credentials to the docker container or in your environment. 
For the docker container this can be done by setting the [environment variables](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#environment-variables) with `-e AWS_ACCESS_KEY_ID=my_secret_id -e AWS_SECRET_ACCESS_KEY=my_secret_key`.
Or you can provide the [shared credentials file](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#shared-credentials-file) to the user running the nbviewer (in docker with a volume).

## GitHub Enterprise

To use nbviewer on your own GitHub Enterprise instance you need to set `GITHUB_API_URL`.
The relevant [API endpoints for GitHub Enterprise](https://developer.github.com/v3/enterprise/) are prefixed with `http://hostname/api/v3`.
You must also specify your `OAUTH` or `API_TOKEN` as explained above.  For example:

```shell
docker run -p 8080:8080 -e 'GITHUB_OAUTH_KEY=YOURKEY' \
                          -e 'GITHUB_OAUTH_SECRET=YOURSECRET' \
                          -e 'GITHUB_API_URL=https://ghe.example.com/api/v3/' \
                          jupyter/nbviewer
```

With this configured all GitHub API requests will go to your Enterprise instance so you can view all of your internal notebooks.

## Base URL

If the environment variable `JUPYTERHUB_SERVICE_PREFIX` is specified, then NBViewer _always_ uses the value of this environment variable as the base URL.

In the case that there is no value for `JUPYTERHUB_SERVICE_PREFIX`, then as a backup the value of the `--base-url` flag passed to the `python -m nbviewer` command on the command line will be used as the base URL.

## Local Development

### With Docker

You can build a docker image that uses your local branch.


#### Build

```shell
cd <path to repo>
docker build -t nbviewer .
```


#### Run

```shell
cd <path to repo>
docker run -p 8080:8080 nbviewer
```

### With Docker Compose

The Notebook Viewer uses `memcached` in production. To locally try out this
setup, a [docker-compose](https://docs.docker.com/compose/) configuration is
provided to easily start/stop the `nbviewer` and `memcached` containers
together from your current branch. You will need to install `docker` prior
to this.

#### Run

```shell
cd <path to repo>
pip install docker-compose
docker-compose up
```


### Local Installation

The Notebook Viewer requires several binary packages to be installed on your system. The primary ones are `libmemcached-dev libcurl4-openssl-dev pandoc libevent-dev libgnutls28-dev`. Package names may differ on your system, see [salt-states](https://github.com/rgbkrk/salt-states-nbviewer/blob/master/nbviewer/init.sls) for more details.

If they are installed, you can install the required Python packages via pip.

```shell
$ cd <path to repo>
$ pip install -r requirements.txt
```

#### Static Assets

Static assets are maintained with `bower` and `less` (which require having
`npm` installed), and the `invoke` python module.

```shell
$ cd <path to repo>
$ pip install -r requirements-dev.txt
$ npm install
$ invoke bower
$ invoke less [-d]
```

This will download the relevant assets into `nbviewer/static/components` and create the built assets in `nbviewer/static/build`.

Pass `-d` or `--debug` to `invoke less` to create a CSS sourcemap, useful for debugging.


#### Running Locally

```shell
$ cd <path to repo>
$ python -m nbviewer --debug --no-cache --host=127.0.0.1
```

This will automatically relaunch the server if a change is detected on a python file, and not cache any results. You can then just do the modifications you like to the source code and/or the templates then refresh the pages.


## Contributing

If you would like to contribute to the project, please read the [`CONTRIBUTING.md`](CONTRIBUTING.md). The `CONTRIBUTING.md` file
explains how to set up a development installation and how to run the test suite.


## Extending the Notebook Viewer
### Providers
Providers are sources of notebooks and directories of notebooks and directories.

`nbviewer` ships with several providers
- `url`
- `gist`
- `github`
- `huggingface`
- `local`

#### Writing a new Provider
There are already several providers
[proposed/requested](https://github.com/jupyter/nbviewer/issues?utf8=%E2%9C%93&q=is%3Aissue+is%3Aopen+label%3Atag%3AProvider). Some providers are more involved than others, and some,
such as those which would require user authentication, will take some work to
support properly.

A provider is implemented as a python module, which can expose a few functions:

##### `uri_rewrites`
If you just need to rewrite URLs (or URIs) of another site/namespace, implement
`uri_rewrites`, which will allow the front page to transform an arbitrary string
(usually an URI fragment), escape it correctly, and turn it into a "canonical"
nbviewer URL. See the [dropbox provider](./nbviewer/providers/dropbox/handlers.py)
for a simple example of rewriting URLs without using a custom API client.

##### `default_handlers`
If you need custom logic, such as connecting to an API, implement
`default_handlers`. See the [github provider](./nbviewer/providers/github/handlers.py)
for a complex example of providing multiple handlers.

##### Error Handling
While you _could_ re-implement upstream HTTP error handling, a small
convenience method is provided for intercepting HTTP errors.
On a given URL handler that inherits from `BaseHandler`, overload the
`client_error_message` and re-call it with your message (or `None`). See the
[gist provider](./nbviewer/providers/gist/handlers.py) for an example of customizing the
error message.

### Formats
Formats are ways to present notebooks to the user.

`nbviewer` ships with three providers:
- `html`
- `slides`
- `script`

#### Writing a new Format
If you'd like to write a new format, open a ticket, or speak up on [gitter](https://gitter.im/jupyter/nbviewer)!
We have some work yet to do to support your next big thing in notebook
publishing, and we'd love to hear from you.

## Config File and Command Line Configuration

NBViewer is configurable using a config file, by default called `nbviewer_config.py`. You can modify the name and location of the config file that NBViewer looks for using the `--config-file` command line flag. (The location is always a relative path, i.e. relative to where the command `python -m nbviewer` is run, and never an absolute path.) 

If you don't know which attributes of NBViewer you can configure using the config file, run `python -m nbviewer --generate-config` (or `python -m nbviewer --generate-config --config-file="my_custom_name.py"`) to write a default config file which has all of the configurable options commented out and set to their default values. To change a configurable option to a new value, uncomment the corresponding line and change the default value to the new value.

You can also run `python -m nbviewer --help-all` to see all of the configurable options. This is a more comprehensive version of `python -m nbviewer --help`, which gives a list of the most common ones along with flags and aliases you can use to set their values temporarily via the command line.

The config file uses [the standard configuration syntax for Jupyter projects](https://traitlets.readthedocs.io/en/stable/config.html). For example, to configure the default port used to be 9000, add the line `c.NBViewer.port = 9000` to the config file. If you want to do this just once, you can also run `python -m nbviewer --NBViewer.port=9000` at the command line. (`NBViewer.port` also has the alias `port`, making it also possible to do, in this specific case, `python -m nbviewer --port=9000`. However not all configurable options have shorthand aliases like this; you can check using the outputs of `python -m nbviewer --help` and `python -m nbviewer --help-all` to see which ones do and which ones don't.)

One thing this allows you to do, for example, is to write your custom implementations of any of the standard page rendering [handlers](https://www.tornadoweb.org/en/stable/guide/structure.html#subclassing-requesthandler) included in NBViewer, e.g. by subclassing the original handlers to include custom logic along with custom output possibilities, and then have these custom handlers always loaded by default, by modifying the corresponding lines in the config file. This is effectively another way to extend NBViewer.

## Securing the Notebook Viewer

You can run the viewer as a [JupyterHub 0.7+ service](https://jupyterhub.readthedocs.io/en/latest/reference/services.html). Running the viewer as a service prevents users who have not authenticated with the Hub from accessing the nbviewer instance. This setup can be useful for protecting access to local notebooks rendered with the `--localfiles` option.

Add an entry like the following to your `jupyterhub_config.py` to have it start nbviewer as a managed service:

```python
c.JupyterHub.services = [
    {
        # the /services/<name> path for accessing the notebook viewer
        'name': 'nbviewer',
        # the interface and port nbviewer will use
        'url': 'http://127.0.0.1:9000',
        # the path to nbviewer repo
        'cwd': '<path to repo>',
        # command to start the nbviewer
        'command': ['python', '-m', 'nbviewer']
    }
]
```

The nbviewer instance will automatically read the [various `JUPYTERHUB_*` environment variables](http://jupyterhub.readthedocs.io/en/latest/reference/services.html#launching-a-hub-managed-service) and configure itself accordingly. You can also run the nbviewer instance as an [externally managed JupyterHub service](http://jupyterhub.readthedocs.io/en/latest/reference/services.html#externally-managed-services), but must set the requisite environment variables yourself.
