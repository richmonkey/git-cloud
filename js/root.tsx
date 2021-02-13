import React, { useState, useEffect } from 'react';
import styles from './root.less';
import Modal from 'react-modal';


interface Repository {
    name:string;//名字要唯一,同时也是clone的本地路径名
    url:string;
    disabled:boolean;//不再自动同步
    rdonly:boolean;//本地更新不自动同步到服务器
    lastSyncTime?:number;
    syncing?:boolean;
    syncResult?:boolean;
}


declare global {
    interface Window { pywebview: any; }
}

Modal.setAppElement('#root');


var formatTime = (function() {
 
    function isThisYear(d) {
        var d2 = new Date();
        return d.getFullYear() == d2.getFullYear();
    }
      
    function isSameDay(d1, d2) {
        return (d1.getFullYear() == d2.getFullYear() && d1.getMonth() == d2.getMonth() && d1.getDate() == d2.getDate());
    }
      
    function isToday(d) {
        var now = new Date();
        return isSameDay(d, now);
    }
    function isYestody(d1) {
        var d2 = new Date(Date.now() - 3600*24*1000);
        return isSameDay(d1, d2);
    }
      
    function isInWeek(d) {
        var t = Date.now() - 7*3600*24*1000;
        var d2 = new Date(t);
        return (d.getTime() > t && !isSameDay(d, d2));
    }
      
    function subTime(d) {
        var n = Date.now();
        return (n - d.getTime())/1000;
    }

    return function(ts) {
        var date = new Date(ts);
        var y = date.getFullYear();
        var month = date.getMonth() + 1;
        var d = date.getDate();
        var H = date.getHours();
        var m = date.getMinutes();
        var day = date.getDay();
    
        var diff = subTime(date);

        if (isToday(date)) {
            if (diff < 60) {
                return "刚刚";
            } else if (diff < 60*60) {
                return `${Math.floor(diff/60)}分钟前`;
            } else {
                return `${Math.floor(diff/(60*60))}小时前`;
            }
        } else if (isYestody(date)) {
          return "昨天 " + H + ':' + (m < 10 ? '0' + m : m);
        } else if (diff < 30*24*60*60) {
            return `${Math.floor(diff/(24*60*60))}天前`;
        } else if (isThisYear(date)) {
          return month + '-' + d;
        } else {
          return y + "-" + month + '-' + d;
        }
    };
})();

function DisabledSetting() {
    return (
        <div>
            <div className={styles["setting"]}>设置</div>
        </div>
    );
}
function Setting(props) {
    const [isOpen, setIsOpen] = useState(false);
    const [interval, setInterval] = useState(props.setting.interval);


    var onCancel = function() {
        setIsOpen(false);
    }

    var onOk = function() {
        var setting = Object.assign({}, props.setting, {interval:interval});
        if (isNaN(interval)) {
            return;
        }
        props.onApply(setting)
            .then((r) => {
                if (r) {
                    setIsOpen(false);
                }
            });
    }

    var onChange = function(event) {
        var v = event.currentTarget.value;
        var value = parseInt(v);
        setInterval(value);
    }

    var onSetting = function() {
        setIsOpen(true);
    }

    var changed = (interval!=props.setting.interval);
    return (
        <div>
            <div className={styles["setting"]} onClick={onSetting}>设置</div>
            <Modal
                isOpen={isOpen}>
                <div className={styles["setting-content"]}>
                    <h2>设置</h2>
                    <div className={styles["item"]}>
                        <span className={styles["label"]}>同步间隔, 单位秒</span>
                        <input className={styles["value"]} value={isNaN(interval) ? "" : interval} onChange={onChange} />
                    </div>

                    <div className={styles["item"]}>
                        <span className={styles["label"]}>仓库路径:</span>
                        <div className={styles["value"]}>{props.setting.workspace}</div>
                    </div>
        
                    <div className={styles["bottom"]}>
                        <button onClick={onCancel}>取消</button>
                        <button disabled={!changed} onClick={onOk}>应用</button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}

function Add(props) {
    const [isOpen, setIsOpen] = useState(false);
    const [repoUrl, setRepoUrl] = useState("");
    var onCancel = function() {
        setIsOpen(false);
    }

    var onOk = function() {
        props.onAdd(repoUrl)
            .then((r) => {
                if (r) {
                    setIsOpen(false);
                    setRepoUrl("");
                }
            });
    }

    var onChange = function(event) {
        setRepoUrl(event.currentTarget.value);
    }

    var onAdd = function() {
        setIsOpen(true);
    }
    return (
        <div>
            <div onClick={onAdd}>添加</div>
            <Modal
                isOpen={isOpen}>
                <div className={styles["modal-content"]}>
                    <h2>新仓库</h2>
                    <input value={repoUrl} onChange={onChange} placeholder={"仓库URL"} />
                    <div className={styles["bottom"]}>
                        <button onClick={onCancel}>取消</button>
                        <button onClick={onOk}>确定</button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}

const Checkbox = props => (
    <input type="checkbox" {...props} />
)


interface Props {

}


interface Stat {
    repositories:Repository[];
    setting:any;
}

export class Root extends React.Component<Props, Stat> {
    input:React.RefObject<HTMLInputElement>;
    timer?:number;

    constructor(props) {
        super(props);

        this.input = React.createRef();

        this.state = {
            repositories:[], 
            setting:undefined,
        };

        this.onSync = this.onSync.bind(this);
        this.onDelete = this.onDelete.bind(this);
        this.onCheckboxChange = this.onCheckboxChange.bind(this);

        this.refreshState = this.refreshState.bind(this);
        this.onApiReady = this.onApiReady.bind(this);

        this.onAddRepo = this.onAddRepo.bind(this);
        this.onApplySetting = this.onApplySetting.bind(this);
    }

    componentDidMount() {
        window.addEventListener('pywebviewready', this.onApiReady);
        this.timer = setInterval(this.refreshState, 20*1000);
    }

    componentWillUnmount() {
        window.removeEventListener('pywebviewready',  this.onApiReady);
        clearInterval(this.timer);
    }

    refreshState() {
        //更新同步时间
        this.setState({});
    }

    onApiReady() {
        window.pywebview.api.get_repos()
            .then((repos) => {
                console.log("repos:", repos);
                this.setState({repositories:repos});
            })
        window.pywebview.api.get_setting()
            .then((setting) => {
                console.log("setting:", setting);
                this.setState({setting:setting});
            });
    }

    updateRepoState(repoName, lastSyncTime, syncing, syncResult) {
        var repo = this.state.repositories.find((repo) => {
            return repo.name == repoName;
        });
        if (!repo) {
            console.log("can't find repo:", repoName);
            return;
        }
        console.log("update repo state:", repoName, lastSyncTime, syncing);
        repo.lastSyncTime = lastSyncTime;
        repo.syncResult = syncResult;
        repo.syncing = syncing;
        this.setState({});
    }
 

    onAddRepo(repo_url) {
        var p = Promise.resolve(false);
        if (!repo_url) {
            return p;
        }
        var pos = repo_url.lastIndexOf("/");
        if (pos == -1) {
            return p;
        }
        var filename = repo_url.substring(pos + 1);
        if (!filename) {
            return p;
        }
        var name = filename.split(".")[0];
        if (!name) {
            return p;
        }
        console.log("repo url:", repo_url, " name:", name);
        var r = this.state.repositories.find((repo) => {
            return repo.name == name;
        })
        if (r) {
            alert("仓库名重复");
            return p;
        }

        var repo:Repository = {name:name, url:repo_url, disabled:false, rdonly:false};
        return window.pywebview.api.add_repo(name, repo_url)
            .then((r) => {
                if (r) {
                    this.state.repositories.push(repo);
                    this.setState({});
                } else {
                    console.log("add fail");
                    alert("仓库添加失败");
                }
                return r;
            });
    }

    onApplySetting(setting) {
        if (setting.interval < 10) {
            alert("同步间隔不能小于10秒")
            return Promise.resolve(false);
        }
        return window.pywebview.api.set_interval(setting.interval)
            .then((r) => {
                if (r) {
                    this.setState({ setting: setting });
                } else {
                    console.log("setting fail");
                    alert("设置同步间隔失败");
                }
                return r;
            });
    }


    onCheckboxChange(e) {
        var name = e.target.dataset.name;
        var checked = e.target.checked;
        if (!name) {
            return;
        }
        console.log("auto sync repo:", name, checked);

        window.pywebview.api.auto_sync_repo(name, checked)

        var repos = this.state.repositories;
        var repo = repos.find((repo) => {
            return repo.name == name;
        });
        if (!repo) {
            console.log("can't find repo:", name);
            return;
        }
        repo.disabled = !checked;
        this.setState({});
    }

    onSync(e) {
        var name = e.target.dataset.name;
        console.log("sync repo:", name);
        window.pywebview.api.sync_repo(name);
    }

    onDelete(e) {
        var name = e.target.dataset.name;
        console.log("del repo:", name);
        window.pywebview.api.delete_repo(name);
        var repos = this.state.repositories;
        var index = repos.findIndex((repo) => {
            return repo.name == name;
        });
        if (index == -1) {
            console.log("can't find repo:", name);
            return;
        }
        this.state.repositories.splice(index, 1);
        this.setState({});
    }

    render() {
        var nodes: any[]= [];
        var repos = this.state.repositories;
        repos.forEach((repo) => {
            var status = "";
            if (repo.syncing) {
                status = "正在同步"
            } else if (repo.lastSyncTime) {
                if (repo.syncResult === false) {
                    status = "同步失败";
                } else {
                    status = formatTime(repo.lastSyncTime*1000) + "同步";
                }
            } else {
                status = "";
            }
            nodes.push((
                <div key={repo.name} className={styles["repo"]}>
                    <div className={styles["title"]}>
                        <div className={styles["name"]}>{repo.name}</div>
                        <div>{status}</div>
                    </div>
                    <div className={styles["content"]}>
                        <label>
                            <Checkbox
                                data-name={repo.name}
                                checked={!repo.disabled}
                                onChange={this.onCheckboxChange}
                                />
                          <span>自动同步</span>
                        </label>
                        <div>
                            <button  onClick={this.onSync} data-name={repo.name}>同步仓库</button>
                            <button  onClick={this.onDelete} data-name={repo.name}>移除仓库</button>
                        </div>
                    </div>
                    <div className={styles["line"]}></div>
                </div>
            ));
        });
        return (
            <div>
                <div className={styles["header"]}>
                    <div>我的仓库</div>
                    <div className={styles["menu"]}>
                        <Add onAdd={this.onAddRepo}></Add>
                        {
                            this.state.setting ?
                                <Setting setting={this.state.setting} onApply={this.onApplySetting} /> :
                                <DisabledSetting />
                        }
                    </div>
                </div>
                {nodes}
            </div>
        )
    }
}

