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
    return file(user,repo,'tree',None,None)

@app.route('/<user>/<repo>/<tree>/<branch>/')
def dummy1(user,repo,tree,branch):
    return file(user,repo,tree,branch,None)


@app.route('/<user>/<repo>/<tree>/<branch>/<path:subfile>')
def file(user,repo,tree,branch, subfile):
    #we don't care about tree or branch now...
    base  = "You are trying to access the file : %(file)s, from the %(repo)s repository of %(name)s"
    
    #convert names to objects
    user = github.get_user(user)
    repo = user.get_repo(repo)
    master = branch if branch else repo.master_branch
    branch = [b for b in repo.get_branches() if b.name == master][0]

    if subfile:
        e = rwt(repo, branch.commit.sha, subfile.strip('/').split('/'))
    else :
        e = repo.get_git_tree(branch.commit.sha);

    if hasattr(e,'type') and e.type == 'blob' :
        f = repo.get_git_blob(e.sha)
        return render_content(base64.decodestring(f.content))
    else :
        entries = []
        for en in e.tree:
            var = {}
            var['path'] = en.path
            var['url'] = relative_url_for_tree(en)
            entries.append(var)
        return render_template('treelist.html', entries=entries)

def relative_url_for_tree(obj):
    if hasattr(obj, 'type') and obj.type == 'blob' :
        return obj.path
    else :
        return obj.path+'/'

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
