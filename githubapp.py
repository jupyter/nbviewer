import os
import base64
from flask import Flask , request, render_template
import nbconvert.nbconvert as nbconvert
import requests
from nbformat import current as nbformat
from flask import Flask, redirect, abort
import re
import github as gh
from gist import render_content

app = Flask(__name__)
github = gh.Github()

@app.route('/')
def render_url():
    return 'you are at root'

@app.route('/<user>/')
def user(user):
    return github.get_user(user).name

@app.route('/<user>/<repo>/')
def repo(user,repo):
    return github.get_user(user).get_repo(repo).url


@app.route('/<user>/<repo>/<tree>/<branch>/<path:subfile>')
def file(user,repo,tree,branch, subfile):
    #we don't care about tree or branch now...
    base  = "You are trying to access the file : %(file)s, from the %(repo)s repository of %(name)s"
    user = github.get_user(user)
    repo = user.get_repo(repo)

    master = repo.master_branch
    branch = [b for b in repo.get_branches() if b.name == master][0]

    headtree = repo.get_git_tree(branch.commit.sha)



    formated = base % { 'name':user.name,'repo':repo.url, 'file':subfile}
    e = rwt(repo, branch.commit.sha, subfile.strip('/').split('/'))
    if hasattr(e,'type') and e.type == 'blob' :
        f = repo.get_git_blob(e.sha)
        return render_content(base64.decodestring(f.content))
    else :
        return render_template('treelist.html', entries=[n.path for n in e.tree])
        #return '\n'.join([n.path for n in e.tree])



#recursively walk tree....
def rwt(repo,sha,path):
    tree = repo.get_git_tree(sha)
    if len(path)==0:
        return tree
    subpath = path[1:]
    key = path[0]
    nodes = tree.tree
    for n in nodes :
        if n.path == key:
            if n.type == 'tree':
                return rwt(repo, n.sha, subpath)
            else :
                return n


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    debug = os.path.exists('.debug')
    if debug :
        print 'DEBUG MODE IS ACTIVATED !!!'
    else :
        print 'debug is not activated'
    app.run(host='0.0.0.0', port=port, debug=debug)
