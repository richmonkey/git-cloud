#!/usr/bin/env python3
import sys
import os
import time
import json
import subprocess
import webview
from pathlib import Path
from sync import Sync
from sync import set_env_path
from sync import set_sync_interval

import threading, queue

DEBUG = True

sync_q = queue.Queue(maxsize=1000)
event_q = queue.Queue(maxsize=1000)

sync = None

def read_repo_db(workspace):
    path = os.path.join(workspace, ".repos")
    try:
        with open(path, "rb") as f:
            data = f.read()
            if not data:
                return []
            obj = json.loads(data.decode("utf8"))
            return obj
    except FileNotFoundError as e:
        return []

def write_repo_db(workspace, repos):
    path = os.path.join(workspace, ".repos")
    with open(path, "wb") as f:
        data = json.dumps(repos)
        f.write(data.encode("utf8"))


class Api():
    def __init__(self, workspace):
        self.workspace = workspace
        self.dirty = False
        self.lock = threading.Lock()
        self.repos = read_repo_db(self.workspace)
        self.window = None

    def update_last_sync_time(self, repo_name):
        with self.lock:
            for repo in self.repos:
                if repo["name"] == repo_name:
                    repo["lastSyncTime"] = int(time.time())
                    self.dirty = True
                    break

    def get_repos(self):
        print("js api thread id:", threading.get_ident())
        with self.lock:
            return [repo.copy() for repo in self.repos]

    def add_repo(self, name, url):
        with self.lock:
            return self._add_repo(name, url)

    def _add_repo(self, name, url):
        pos = -1
        for index, repo in enumerate(self.repos):
            if repo["name"] == name:
                pos = index
                break
        if pos != -1:
            return False

        repo = {"name":name, "url":url, "disabled":False, "rdonly":False}
        print("add repo:", repo)
        self.repos.append(repo)
        write_repo_db(self.workspace, self.repos)
        self.dirty = False
        sync_q.put(repo)
        return True

    def sync_repo(self, name):
        print("sync repo:", name)
        with self.lock:
            rs = [repo for repo in self.repos if repo["name"] == name]
            if rs:
                repo = rs[0].copy()
                repo["force"] = True
                sync_q.put_nowait(repo)

    def auto_sync_repo(self, name, auto_sync):
        print("auto sync repo:", name, auto_sync)
        with self.lock:
            rs = [repo for repo in self.repos if repo["name"] == name]
            if rs:
                rs[0]["disabled"] = not auto_sync
                sync_q.put_nowait(rs[0])
                print("put sync:", rs[0])

    def get_sync_event(self):
        try:
            item = event_q.get(timeout=60)
            print("sync event:", item)
            event = item["event"]
            if event == "repo_begin":
                self.update_last_sync_time(item["name"])
            if event == "end":
                self.save_dirty_repo_db()

            if event == "repo_begin" or event == "repo_end":
                return item
            return None
        except queue.Empty as e:
            print("queue empty exception")
            return None


    def save_dirty_repo_db(self):
        with self.lock:
            if not self.dirty:
                return
            write_repo_db(self.workspace, self.repos)

    def run(self):
        while True:
            event = self.get_sync_event()
            if not event:
                continue
            name = event["name"]
            rs = [repo for repo in self.repos if repo["name"] == name]
            if not rs:
                continue
            last_sync_time = rs[0]["lastSyncTime"]
            syncing = "true" if event["event"] == "repo_begin" else "false"
            sync_result = "true" if event.get("result", True) else "false"
            self.window.evaluate_js("updateRepoState(\"%s\", %s, %s, %s)"%(event["name"], last_sync_time, syncing, sync_result))

    def start(self):
        thread = threading.Thread(target=self.run, daemon=True, args=())
        thread.start()
    


def main():
    print(sys.argv)
    url = "dist/index.html"
    if len(sys.argv) > 1:
        url = sys.argv[1]
    print("main thread id:", threading.get_ident())
    workspace = os.path.join(Path.home(), "gitCloud")
    if not os.path.exists(workspace):
        os.mkdir(workspace)

    api = Api(workspace)
    repos = [repo.copy() for repo in api.repos]
    sync = Sync(repos, event_q)

    window = webview.create_window('gitCloud', url, width=400, height=680, js_api=api)
    api.window = window

    api.start()
    sync.start(sync_q, workspace)

    webview.start(debug=DEBUG)    


if __name__ == "__main__":
    main()
