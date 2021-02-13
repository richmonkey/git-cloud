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
from sync import WAKEUP
import appdirs
import threading, queue
import config

APPNAME = "gitcloud"

sync_q = queue.Queue(maxsize=1000)
event_q = queue.Queue(maxsize=1000)

sync = None

def read_json(path, default):
    try:
        with open(path, "rb") as f:
            data = f.read()
            if not data:
                return default
            obj = json.loads(data.decode("utf8"))
            return obj
    except FileNotFoundError as e:
        return default

def read_repo_db(workspace):
    path = os.path.join(workspace, ".repos")
    return read_json(path, [])

def write_repo_db(workspace, repos):
    path = os.path.join(workspace, ".repos")
    with open(path, "wb") as f:
        data = json.dumps(repos)
        f.write(data.encode("utf8"))

def read_setting_db():
    path = os.path.join(appdirs.user_data_dir(APPNAME), "setting.json")
    return read_json(path, {})

def write_setting_db(setting):
    path = os.path.join(appdirs.user_data_dir(APPNAME), "setting.json")
    with open(path, "wb") as f:
        data = json.dumps(setting)
        f.write(data.encode("utf8"))


class Api():
    def __init__(self, setting):
        self.workspace = setting["workspace"]
        self.setting = setting
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
    
    def get_setting(self):
        with self.lock:
            return self.setting.copy()
            return True

    def set_interval(self, interval):
        print("set interval:", interval)
        with self.lock:
            interval = int(interval)
            assert(interval >= 10)
            self.setting["interval"] = interval
            write_setting_db(self.setting)
            sync.set_interval(interval)
            sync_q.put_nowait(WAKEUP)
            return True

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
                write_repo_db(self.workspace, self.repos)
                sync_q.put_nowait(rs[0])
                print("put sync:", rs[0])


    def delete_repo(self, name):
        print("del repo:", name)
        with self.lock:
            rs = next(((index, repo) for index, repo in enumerate(self.repos) if repo["name"] == name), None)
            if rs:
                repo = rs[1].copy()
                self.repos.pop(rs[0])
                repo["disabled"] = True
                write_repo_db(self.workspace, self.repos)
                sync_q.put_nowait(repo)


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
            repo_name = event["name"]
            rs = [repo for repo in self.repos if repo["name"] == repo_name]
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
    global sync
    print(sys.argv)
    url = "index.html"
    if len(sys.argv) > 1:
        url = sys.argv[1]
    print("main thread id:", threading.get_ident())

    data_dir = appdirs.user_data_dir(APPNAME)
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)

    setting = read_setting_db()
    if not setting:
        setting = {
            "workspace":os.path.join(Path.home(), "gitCloud"), 
            "interval":config.SYNC_INTERVAL
        }
    print("setting:", setting)

    workspace = setting["workspace"]
    if not os.path.exists(workspace):
        os.mkdir(workspace)

    if os.path.isabs(config.GIT):
        path = os.path.dirname(config.GIT)
        env_path = os.getenv("PATH")
        if env_path:
            env_path = env_path + ":" + path
        else:
            env_path = path
        set_env_path(env_path)
        
    api = Api(setting)
    repos = [repo.copy() for repo in api.repos]
    sync = Sync(repos, event_q, setting["interval"])

    window = webview.create_window('gitCloud', url, width=400, height=680, js_api=api)
    api.window = window

    api.start()
    sync.start(sync_q, workspace)

    webview.start(debug=config.DEBUG)    


if __name__ == "__main__":
    main()
