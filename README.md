IPython Notebook Viewer
-----------------------

IPython notebook viewer is an [heroku](http://www.heroku.com) application that
given the url of a [IPython](http://www.ipython.org) notebook file (ending in ipynb) show you a static
html version.

Quick Deploy
------------

If will need to have an heroku account, or have acces to one, 
just push the master branch :

```bash
git push heroku master:master
```

The application will be availlable under `yourappname.herokuapp.com`


Modifying the app
-----------------

The app is based on [Twitter Bootstrap](http://twitter.github.com/bootstrap/)
so you will need some dependency like `node`,`uglify-js`.

 * everything in `/static/` is serve statically
 * html files in `/static/` are build from `/template/` by doing `$ make` in the root dirrectory
 * `/template/layout.mustache` contain headers and footers
 * every `*.mustache` file in `template/pages` will create a corresponding html file in `/static/` 
 * any required python package should be availlable via `pip`, and should be added to `requirement.txt`.
   see `pip freeze` to know what to write in the file.
 * local debug mode is activated by creating a `.debug` file in the root directory, `.debug` is excluded in `.gitignore`and `.slugignore`

Testing Locally
---------------

Sql qlchemy need to connect to a database, you should export tthe environement varaible DATABASE_URL
it you don't have any installed DB or just want to try out, you can use in memory sqlite :

$ export DATABASE_URL='sqlite:///:memory:'

## Deploying on heroku

    heroku create [appname]
    heroku git:remote -a [appname] -r [appname]
    heroku addons:add memcachier:dev --app [appname]
    heroku addons:add newrelic:standard --app [appname]

to deploy the new version :

    git push nbviewer2 <local-branch>:master
