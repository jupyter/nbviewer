# IPython Notebook Viewer

IPython nbviewer is the web application behind [IPython Notebook Viewer](http://nbviewer.ipython.org), which is graciously hosted by [Rackspace](https://developer.rackspace.com/?nbviewer=awesome).

Run this locally to get most of the features of nbviewer on your own network.

## Quick Run

If you have `docker` installed, you can pull and run the currently built version of the Docker container by

```
$ docker pull ipython/nbviewer
$ docker run -p 8080:8080 ipython/nbviewer
```

It automatically gets built with each push to `master`, so you'll always be able to get the freshest copy.

For speed and friendliness to GitHub, be sure to set `GITHUB_OAUTH_KEY` and `GITHUB_OAUTH_SECRET`:

```
$ docker run -p 8080:8080 -e 'GITHUB_OAUTH_KEY=YOURKEY' \
                          -e 'GITHUB_OAUTH_SECRET=YOURSECRET' \
                          ipython/nbviewer 
```

Or to use your GitHub personal access token, you can set just `GITHUB_API_TOKEN`.

## Local Development

### With Docker

You can build a docker image that uses your local branch

#### Build

```
docker build -t nbviewer .
```

#### Run

```
docker run -p 8080:8080 nbviewer
```

### Local Installation

The Notebook Viewer requires several binary packages to be installed on your system. The primary ones are `libmemcached-dev libcurl4-openssl-dev pandoc libevent-dev`. Package names may differ on your system, see [salt-states](https://github.com/rgbkrk/salt-states-nbviewer/blob/master/nbviewer/init.sls) for more details.

If they are installed, you can install the required Python packages via pip.

`pip install -r requirements.txt`

#### Running Locally

```
$ cd <path to repo>
$ python -m nbviewer --debug --no-cache
```

This will automatically relaunch the server if a change is detected on a python file, and not cache any results. You can then just do the modifications you like to the source code and/or the templates then refresh the pages.

