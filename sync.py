#!/usr/bin/env python3
import sys
import os
import time
import subprocess
import threading, queue

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



SYNC_INTERVAL = 10 #6*60

class Sync(object):
    def __init__(self, repos, event_q):
        self.last_sync_time = 0
        self.is_syncing = False
        self.repos = repos
        self.event_q = event_q

    def sync_repos(self, repos, workspace):
        if not repos:
            return

        print("sync repos:", repos, workspace)
        self.event_q.put_nowait({"stage":"begin"})
        for repo in repos:
            repo_path = os.path.join(workspace, repo["name"])
            if repo["disabled"]:
                continue
            if not os.path.exists(repo_path):
                self.event_q.put_nowait({"stage":"middle", "name":repo["name"], "syncing":True})
                git_clone(repo_path, repo["url"])
                self.event_q.put_nowait({"stage":"middle", "name":repo["name"], "syncing":False})

        for repo in repos:
            repo_path = os.path.join(workspace, repo["name"])
            if repo["disabled"]:
                continue
            if not os.path.exists(repo_path):
                continue
            self.event_q.put_nowait({"stage":"middle", "name":repo["name"], "syncing":True})
            sync_repo(repo_path, repo["url"])
            self.event_q.put_nowait({"stage":"middle", "name":repo["name"], "syncing":False})

        self.event_q.put_nowait({"stage":"end"})

    def handle_item(self, item):
        repos = self.repos
        ret = False
        if item["disabled"]:
            #remove
            self.repos = [repo for repo in repos if repo["name"] != item["name"]]
            print("rm sync repo:", item["name"])
            return False
        else:
            #add
            repos = [repo for repo in repos if repo["name"] == item["name"]]
            if not repos and "url" in item:
                self.repos.append(item.copy())
                print("add sync repo:", item["name"])
            return True

    def run(self, q, workspace):
        self.sync_repos(self.repos, workspace)
        while True:
            try:
                item = q.get(timeout=SYNC_INTERVAL)
                r = self.handle_item(item)
                if not r:
                    #remove repo or unchanged
                    continue
            except queue.Empty as e:
                pass

            self.sync_repos(self.repos, workspace)

    def start(self, q, workspace):
        thread = threading.Thread(target=self.run, daemon=True, args=(q, workspace))
        thread.start()
    

if __name__ == "__main__":
    print(sys.argv)
