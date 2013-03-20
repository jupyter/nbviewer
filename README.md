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
git push heroku master:master
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
