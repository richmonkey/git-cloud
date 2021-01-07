#!/usr/bin/env python3
import sys
import os
import time
import subprocess
import threading, queue
import socket
import shutil
import datetime

#config item
SYNC_INTERVAL = 10 #6*60


env = None

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
        p = subprocess.Popen(["git", "clone", url, repo_path], env=env, cwd=cwd)
    else:
        p = subprocess.Popen(["git", "clone", "--depth", depth, url, repo_path], env=env, cwd=cwd)
    r = p.wait()
    if r != 0:
        print("clone error:", r)
        return r

    cwd = repo_path
    ignore_file = os.path.join(cwd, ".gitignore")
    ignores = [".DS_Store", "*~", "*.conflict"]
    try:
        with open(ignore_file, "r", encoding="utf8") as f:
            while True:
                line = f.readline()
                if not line:
                    break
                line = line.rstrip()
                ignores = [ignore for ignore in ignores if ignore != line]
    except OSError as e:
        pass

    with open(ignore_file, "ab") as f:
        for ignore in ignores:
            f.write(("\n%s"%ignore).encode("utf8"))
        
    return 0
    
def get_branch(repo_path):
    cwd = repo_path
    p = subprocess.Popen(["git", "symbolic-ref", "--short", "-q", "HEAD"], stdout=subprocess.PIPE, env=env, cwd=cwd, text=True)
    out, _ = p.communicate()
    if p.returncode != 0:
        print("get branch err:", p.returncode)
        return None
    return out.rstrip()

def git_commit(repo_path):
    cwd = repo_path
    p = subprocess.Popen(["git", "status", "-s"], stdout=subprocess.PIPE, env=env, cwd=cwd, text=True)
    out, _ = p.communicate()
    if p.returncode != 0:
        return p.returncode
    if len(out) == 0:
        print("worktree is clean")
        return 0

    p = subprocess.Popen(["git", "add", "."], cwd=cwd)
    r = p.wait()
    if r != 0:
        print("add error:", r)
        return r

    p = subprocess.Popen(["git", "commit", "-m", "git cloud auto commit"], env=env, cwd=cwd)
    r = p.wait()
    if r != 0:
        print("commit error:", r)
    return r

def git_rebase(repo_path, branch):
    cwd = repo_path    
    p = subprocess.Popen(["git", "rebase", "origin/%s"%branch], env=env, cwd=cwd)
    r = p.wait()
    if r != 0:
        print("rebase error:", r)
    return r


def get_conflict_files(repo_path, conflict_files):
    cwd = repo_path    
    p = subprocess.Popen(["git", "ls-files", "-u"], stdout=subprocess.PIPE, env=env, cwd=cwd, text=True)
    out, _ = p.communicate()
    if p.returncode != 0:
        return p.returncode

    lines = out.split("\n")
    d = {}
    #100644 5c65e6d439f561117332e6e04c8fb25ae3b3a116 2	vvv
    for line in lines:
        if not line:
            #last line
            continue
        try:
            s, filename = line.split("\t")
            _, obj_id, stage_number = s.split(" ")
            if filename in d:
                item = d.get(filename)
            else:
                item = {
                    "name":filename, 
                    "our_exists":False, 
                    "their_exists":False, 
                    "ancestor_exists":False
                }
                conflict_files.append(item)
                d[filename] = item
            # stage number 1:O stage ancestor, 2:A stage current, 3:B stage other 
            if stage_number == "2":
                item["our_exists"] = True
                item["our_obj_id"] = obj_id
            elif stage_number == "3":
                item["their_exists"] = True
            elif stage_number == "1":
                item["ancestor_exists"] = True

        except Exception as e:
            print("invalid line format:", line)
            continue
    return 0


class LogSubProcess(object):
    def Popen(self, args, stdout=None, env=None, cwd=None):
        print("subprocess popen args:", args)
        return subprocess.Popen(args, stdout=stdout, env=env, cwd=cwd)

logsubprocess = LogSubProcess()
#merge conflict:theirs
def merge_conflict_theirs(repo_path, conflict_items, conflict_files):
    cwd = repo_path
    for item in conflict_items:
        filename = item["name"]
        if not item["our_exists"] and not item["their_exists"]:
            #git rm
            p = logsubprocess.Popen(["git", "rm", filename], env=env, cwd=cwd)
            r = p.wait()
            if r != 0:
                return r
        elif item["their_exists"] and not item["our_exists"]:
            #git add
            p = logsubprocess.Popen(["git", "add", filename], env=env, cwd=cwd)
            r = p.wait()
            if r != 0:
                return r
        elif item["our_exists"] and not item["their_exists"]:
            #git add
            p = logsubprocess.Popen(["git", "add", filename], env=env, cwd=cwd)
            r = p.wait()
            if r != 0:
                return r
        else:
            #item["our_exists"] and item["their_exists"]
            p = logsubprocess.Popen(["git", "checkout", "--theirs", filename], env=env, cwd=cwd)
            r = p.wait()
            if r != 0:
                return r
            p = logsubprocess.Popen(["git", "add", filename], env=env, cwd=cwd)
            r = p.wait()
            if r != 0:
                return r

            obj_id = item["our_obj_id"]
            cf_file = os.path.join(repo_path, filename + ".conflict")
            with open(cf_file, "wb") as f:
                p = logsubprocess.Popen(["git", "cat-file", "-p", obj_id], stdout=f, env=env, cwd=cwd)
                r = p.wait()
                if r != 0:
                    print("cat file err:", r)
                    return r
                conflict_files.append(filename)
    return 0

def git_merge(repo_path, branch):
    cwd = repo_path    
    p = subprocess.Popen(["git", "merge", "-m", "auto merge", "origin/%s"%branch], env=env, cwd=cwd)
    r = p.wait()
    if r != 0:
        print("merge conflict:", r)
        conflict_items = []
        get_conflict_files(repo_path, conflict_items)
        #filename array
        conflict_files = []
        merge_conflict_theirs(repo_path, conflict_items, conflict_files)
        p = subprocess.Popen(["git", "commit", "-m", "auto merge, use theirs if conflict"], env=env, cwd=cwd)
        r = p.wait()
        if r != 0:
            print("merge with theirs err:", r)
            return r
        
        for c in conflict_files:
            filename = os.path.join(repo_path, c)
            cf_file = filename + ".conflict"
            copy_filename = generate_conflicted_filename(filename)
            shutil.move(cf_file, copy_filename)

    return r

def git_push(repo_path):
    cwd = repo_path    
    p = subprocess.Popen(["git", "push", "origin"], env=env, cwd=cwd)
    r = p.wait()
    if r != 0:
        print("push error:", r)
    return r


def need_push(repo_path, branch):
    cwd = repo_path
    p = subprocess.Popen(["git", "rev-parse", "HEAD", "origin/HEAD"], stdout=subprocess.PIPE, env=env, cwd=cwd, text=True)
    out, _ = p.communicate()
    if p.returncode != 0:
        return True
    a = out.split("\n")
    if len(a) < 2:
        return True
    return not a[0] == a[1]


# branch: current branch
def sync_repo(repo_path, branch):
    print("sync repo:", repo_path, " branch:", branch)
    r = git_fetch(repo_path)
    if r != 0:
        return False
    
    r = git_commit(repo_path)
    if r != 0:
        return False
    
    r = git_merge(repo_path, branch)
    if r != 0:
        return False

    if not need_push(repo_path, branch):
        print("no commit to push")
        return True
    
    r = git_push(repo_path)
    if r != 0:
        return False
    return True


def generate_conflicted_filename(filename):
    name, ext = os.path.splitext(filename)
    today = datetime.date.today()
    index = 0
    while True:
        if index == 0:
            filepath = name + "(%s-conflicted-copy-%s)" % (socket.gethostname(), str(today)) + ext
        else:
            filepath = name + "(%s-conflicted-copy-%s)-(%s)" % (socket.gethostname(), str(today), index)+ ext
        index += 1
        if not os.path.exists(filepath):
            return filepath


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
        self.event_q.put_nowait({"event":"begin"})
        for repo in repos:
            repo_path = os.path.join(workspace, repo["name"])
            if repo["disabled"]:
                continue
            if not os.path.exists(repo_path):
                self.event_q.put_nowait({"event":"repo_begin", "name":repo["name"], "syncing":True})
                r = git_clone(repo_path, repo["url"])
                self.event_q.put_nowait({"event":"repo_end", "name":repo["name"], "syncing":False, "result":r})
                branch = get_branch(repo_path)
                if branch:
                    repo["branch"] = branch
                    print("repo:", repo_path, " branch:", branch)

        for repo in repos:
            repo_path = os.path.join(workspace, repo["name"])
            if repo["disabled"]:
                continue
            if not os.path.exists(repo_path):
                continue
            self.event_q.put_nowait({"event":"repo_begin", "name":repo["name"], "syncing":True})
            if "branch" in repo:
                branch = repo["branch"]
            else:
                branch = get_branch(repo_path)
                print("repo:", repo_path, " branch:", branch)

            if not branch:
                branch = "master"
                #warning
                print("can't get repo branch ", repo_path, " use default master branch")

            r = sync_repo(repo_path, branch)
            self.event_q.put_nowait({"event":"repo_end", "name":repo["name"], "syncing":False, "result":r})

        self.event_q.put_nowait({"event":"end"})

    def handle_item(self, item):
        repos = self.repos
        ret = False
        force = item.get("force", False)
        if item["disabled"] and not force:
            #remove
            self.repos = [repo for repo in repos if repo["name"] != item["name"]]
            print("rm sync repo:", item["name"], self.repos)
            return False
        else:
            #add
            repos = [repo for repo in repos if repo["name"] == item["name"]]
            if not repos :
                assert("url" in item)
                self.repos.append(item.copy())
                print("add sync repo:", item["name"])
            else:
                repos[0]["disabled"] = item["disabled"]
                repos[0]["force"] = force
                print("enable sync repo:", item["name"])
            return True

    def run(self, q, workspace):
        self.sync_repos(self.repos, workspace)
        while True:
            try:
                print("run wait...")
                item = q.get(timeout=SYNC_INTERVAL)
                r = self.handle_item(item)
                if not r:
                    #remove repo or unchanged
                    continue
            except queue.Empty as e:
                pass

            self.sync_repos(self.repos, workspace)
            self.repos = [repo for repo in self.repos if not repo["disabled"] and not repo.get("force")]

    def start(self, q, workspace):
        thread = threading.Thread(target=self.run, daemon=True, args=(q, workspace))
        thread.start()
    

def set_env_path(path):
    global env
    env = os.environ.copy()
    env["PATH"] = path

def set_sync_interval(interval):
    global SYNC_INTERVAL
    SYNC_INTERVAL = interval

if __name__ == "__main__":
    print(sys.argv)
    #print(get_branch("/Users/houxh/gitCloud/test-git-cloud"))
    #git_merge("/Users/houxh/gitCloud/test_git", "master")