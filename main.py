#!/usr/bin/env python3
import sys
import os
import time
import subprocess

merge_driver = "git-cloud-merge.py"
def git_fetch(repo_path):
    cwd = repo_path        
    p = subprocess.Popen(["git", "fetch"], cwd=cwd)
    r = p.wait()
    if r != 0:
        print("fetch error:", r)
    return r


#todo run long time, wait in thread
def git_clone(repo_path, url, depth=None):
    cwd = os.path.dirname(repo_path)
    if depth is None:
        p = subprocess.Popen(["git", "clone", url, repo_path], cwd=cwd)
    else:
        p = subprocess.Popen(["git", "clone", "--depth", depth, url, repo_path], cwd=cwd)
    r = p.wait()
    if r != 0:
        print("clone error:", r)

    cwd = repo_path
    driver_path = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), merge_driver))
    p = subprocess.Popen(["git", "config", "merge.cloud.name", "custom merge driver for gitCloud"], cwd=cwd)
    r = p.wait()
    if r != 0:
        print("config error:", r)
        
    p = subprocess.Popen(["git", "config", "merge.cloud.driver", "python3 " + driver_path +  " %A %O %B %P"], cwd=cwd)
    r = p.wait()
    if r != 0:
        print("config error:", r)

    attr_file = os.path.join(cwd, ".gitattributes")
    with open(attr_file, "wb") as f:
        f.write("* merge=cloud".encode("utf8"))
    ignore_file = os.path.join(cwd, ".gitignore")
    ignores = [".DS_Store", "*~"]
    with open(ignore_file, "ab") as f:
        for ignore in ignores:
            f.write(("\n%s"%ignore).encode("utf8"))
        
    return r
    

def git_commit(repo_path):
    cwd = repo_path
    p = subprocess.Popen(["git", "status", "-s"], stdout=subprocess.PIPE, cwd=cwd, text=True)
    out, _ = p.communicate()
    if p.returncode != 0:
        return p.returncode
    if len(out) == 0:
        print("clean worktree")
        return 0
        

    p = subprocess.Popen(["git", "add", "."], cwd=cwd)
    r = p.wait()
    if r != 0:
        print("add error:", r)
        return r


    
    p = subprocess.Popen(["git", "commit", "-m", "git cloud auto commit"], cwd=cwd)
    r = p.wait()
    if r != 0:
        print("commit error:", r)
    return r

def git_rebase(repo_path):
    cwd = repo_path    
    p = subprocess.Popen(["git", "rebase", "origin/master"], cwd=cwd)
    r = p.wait()
    if r != 0:
        print("rebase error:", r)
    return r

def git_push(repo_path):
    cwd = repo_path    
    p = subprocess.Popen(["git", "push", "origin", "master"], cwd=cwd)
    r = p.wait()
    if r != 0:
        print("push error:", r)
    return r
    
def need_push(repo_path):
    cwd = repo_path
    f1 = os.path.join(repo_path, ".git/refs/heads/master")
    f2 = os.path.join(repo_path, ".git/refs/remotes/origin/master")
    p = subprocess.Popen(["diff", "-q", f1, f2], cwd=cwd)
    r = p.wait()
    return r != 0
    
repos = [
    {
        "url":"file:///tmp/test_git",
        "path":"/tmp/seafile4"
    }
]

def sync_repo(repo_path, url):
    print("sync repo:", repo_path)
    r = git_fetch(repo_path)
    if r != 0:
        return
    
    git_commit(repo_path)
    if r != 0:
        return
    
    git_rebase(repo_path)
    if r != 0:
        return

    if not need_push(repo_path):
        print("no commit to push")
        return
    
    git_push(repo_path)
    if r != 0:
        return

def main():
    for repo in repos:
        if not os.path.exists(repo["path"]):
            git_clone(repo["path"], repo["url"])

    time.sleep(10)
    
    while True:
        for repo in repos:
            if not os.path.exists(repo["path"]):
                git_clone(repo["path"], repo["url"])
            if not os.path.exists(repo["path"]):
                continue
            
            sync_repo(repo["path"], repo["url"])
        time.sleep(10)
        
if __name__ == "__main__":
    print(sys.argv)
    main()
