import os
import base64
from flask import Flask , request, render_template
import nbconvert.nbconvert as nbconvert
import requests
from nbformat import current as nbformat
from flask import Flask, redirect, abort
from flaskext.cache import Cache
import re
import github as gh
from gist import render_content

app = Flask(__name__)
app.config['CACHE_TYPE'] = 'null'
app.config['CACHE_MEMCACHED_SERVERS'] = os.environ.get('MEMCACHE_SERVERS') or ['127.0.0.1']
    #os.environ.get('MEMCACHE_USERNAME')
    #os.environ.get('MEMCACHE_PASSWORD')
cache = Cache(app)
github = gh.Github()


#@cache.cached(50)
def full_url(user,repo=None, blob=None, branch=None, subpath=None):
    if not subpath and (not branch or branch=='master') :
        return '/%(user)s/%(repo)s/' % {'user':user,\
         'repo':repo}

    string = '/%(user)s/%(repo)s/%(blob)s/%(branch)s/%(subpath)s' % \
        {'user':user,\
         'repo':repo,\
         'blob':blob,\
         'branch':branch,\
         'subpath':subpath}
    sp = string.replace('//','/')

    return sp

@app.route('/')
#@cache.cached(50)
def render_url():
    return 'you are at root'

#@app.route('/<user>/')
#def user(user):
#    return github.get_user(user).name

@app.route('/<user>/<repo>/')
@cache.cached(500)
def repo(user,repo):
    return file(user, repo, 'tree','master', None )
    #return redirect('/%(user)s/%(repo)s/tree/master/'%{'user':user, 'repo':repo})

@app.route('/<user>/<repo>/<tree>/<branch>/')
@cache.cached(500)
def dummy1(user,repo,tree,branch):
    if user == 'static':
        return app.send_static_file('%s/%s/%s'%(repo,tree,branch))
        #return open('static/%s/%s/%s'%(repo,tree,branch)).read()
    return browse_tree_blob(user,repo,tree,branch,None)


#@app.route('/<user>/<repo>/tree/<branch>/<path:subfile>')
def bowse_tree(user,repo,branch,subfile, parent=None):
    pass

#@app.route('/<user>/<repo>/blob/<branch>/<path:subfile>')
def show_blob(user,repo,branch,subfile):
    pass

#@app.route('/<user>/<repo>/branches')
def browse_branches(user,repo):
    pass

@app.route('/<usern>/<repon>/<tree>/<branchn>/<path:subfile>')
@cache.cached(500)
def browse_tree_blob(usern,repon,tree,branchn, subfile):
    if (not subfile) and (branchn == 'master'):
        return redirect('/%s/%s/'%(usern,repon))
    print("================")
    print(usern,repon,tree,branchn, subfile)
    print("================")
    return file(usern,repon,tree,branchn, subfile)

def file(usern,repon,tree,branchn, subfile):
    #we don't care about tree or branch now...
    
    #convert names to objects
    user = github.get_user(usern)
    repo = user.get_repo(repon)
    
    master = branchn if branchn else repo.master_branch

    #if not subfile and branchn == repo.master_branch :
        #return redirect(full_url(usern, repon))

    branch = [b for b in repo.get_branches() if b.name == master][0]

    if subfile:
        atroot = False
        e = rwt(repo, branch.commit.sha, subfile.strip('/').split('/'))
    else :
        atroot = True
        e = repo.get_git_tree(branch.commit.sha);
        subfile = ''

    if hasattr(e,'type') and e.type == 'blob' :
        f = repo.get_git_blob(e.sha)
        return render_content(base64.decodestring(f.content))
    else :
        entries = []
        for en in e.tree:
            var = {}
            var['path'] = en.path
            var['type'] = type_for_tree(en)
            var['class']= class_for_tree(en)
            var['url']  = full_url(usern,repon,var['type'],branchn,subfile+'/'+relative_url_for_tree(en))
            entries.append(var)
        return render_template('treelist.html', entries=entries, atroot=atroot)

def relative_url_for_tree(obj):
    if hasattr(obj, 'type') and obj.type == 'blob' :
        return obj.path
    else :
        return obj.path+'/'

def type_for_tree(obj):
    if hasattr(obj, 'type') and obj.type == 'blob' :
        return 'blob'
    else :
        return 'tree'

def class_for_tree(obj):
    if hasattr(obj, 'type') and obj.type == 'blob' :
        return 'icon-file'
    else :
        return 'icon-folder-open'
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
