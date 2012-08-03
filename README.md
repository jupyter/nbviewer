Quick start
-----------

install heroku toolbelt, 
and follow instruction to set up your environement.


* Modifies template/py files
* $ make 
* test
* commit
* push
* that's it


Detail step
-----------

all files under /static/ are statically served files.
some of them are generate by the `$ make` step.

  * template/layout.mustache contail header and footers
  * template/pages/index.mustache contain body of index.

When pushing, heroku look in `requirements.txt`to know what to install.
shutdown and restart the application 

you can see stdout by doing `heroku logs` for debug
