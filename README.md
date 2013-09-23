IPython Notebook Viewer
-----------------------

IPython notebook viewer is an [heroku](http://www.heroku.com) application that
given the url of a [IPython](http://www.ipython.org) notebook file (ending in ipynb) shows you a static
html version.

Quick Deploy
------------

If you have an heroku account, or have access to one, 
have a look at heroku-bootstrap.sh that does a quick setup of an heroku account
and set some variables:

```bash
$ ./heroku-bootstrap.sh <an-app-name>
```
```
Creating <an-app-name>... done, stack is cedar
http://<an-app-name>.herokuapp.com/ | git@heroku.com:<an-app-name>.git
Adding memcachier:dev on <an-app-name>... done, v3 (free)
MemCachier is now up and ready to go. Happy bananas!
Use `heroku addons:docs memcachier` to view documentation.
Adding newrelic:standard on <an-app-name>... done, v4 (free)
Use `heroku addons:docs newrelic` to view documentation.
Git remote <an-app-name> added
Setting config vars and restarting <an-app-name>... done, v5
LIBRARY_PATH: /app/.heroku/vendor/lib
Setting config vars and restarting <an-app-name>... done, v6
LD_LIBRARY_PATH: /app/.heroku/vendor/lib
Setting config vars and restarting <an-app-name>... done, v7
PATH: bin:app/.heroku/venv/bin:/bin:/usr/local/bin:/usr/bin
Setting config vars and restarting <an-app-name>... done, v8
BUILDPACK_URL: https://github.com/ddollar/heroku-buildpack-multi.git
```

Push the repo on your new app
```
$ git push <an-app-name> master:master
...
...
```

The application will be available under `yourappname.herokuapp.com`


Modifying the app
-----------------

The app is based on [Twitter Bootstrap](http://twitter.github.com/bootstrap/)
so you will need some dependencies like `node`,`uglify-js`.

 * everything in `/static/` is served statically
 * html files in `/static/` are built from `/template/` by doing `$ make` in the root dirrectory
 * `/template/layout.mustache` contain headers and footers
 * every `*.mustache` file in `template/pages` will create a corresponding html file in `/static/`
 * any required python package should be availlable via `pip`, and should be added to `requirement.txt`.
   see `pip freeze` to know what to write in the file.
 * local debug mode is activated by creating a `.debug` file in the root directory, `.debug` is excluded in `.gitignore`and `.slugignore`

Testing Locally
---------------

Sqlalchemy needs to connect to a database, you should export the environment variable DATABASE_URL.
If you don't have any installed DB or just want to try out, you can use in memory sqlite :

$ export DATABASE_URL='sqlite:///:memory:'

## Deploying on heroku

    heroku create [appname]
    heroku git:remote -a [appname] -r [appname]
    heroku addons:add memcachier:dev --app [appname]
    heroku addons:add newrelic:standard --app [appname]

to deploy the new version :

    git push nbviewer2 <local-branch>:master


You can eventually set the following github key to make authenticated requests to github.
This will increase the maximum number of requests you can do to github /hour.

    GITHUB_OAUTH_KEY:             xxxxxxxxxxxxxxxxxxxx
    GITHUB_OAUTH_SECRET:          xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

you can use `heroku config:set KEY1=VALUE1` to do so.
