IPython Notebook Viewer
-----------------------

IPython notebook viewer is an [heroku](http://www.heroku.com) application that
given the url of a [IPython](http://www.ipython.org) notebook file (ending in ipynb) shows you a static
html version.

Quick Deploy
------------

If you have an heroku account, or have access to one, 
just push the master branch :

```bash
$ heroku create
Creating something-madeup-123... done, stack is cedar
http://something-madeup-123.herokuapp.com/ | git@heroku.com:something-madeup-123.git
Git remote heroku added
$ git push heroku master:master
...
```

Set PATH environement variable for pandoc
```
$ heroku config:set PATH=bin:app/.heroku/venv/bin:/bin:/usr/local/bin:/usr/bin
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
