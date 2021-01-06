import  React from 'react';
import styles from './root.less';
import Modal from 'react-modal';

interface Repository {
    name:string;//名字要唯一,同时也是clone的本地路径名
    url:string;
    disabled:boolean;//不再自动同步
    rdonly:boolean;//本地更新不自动同步到服务器
    lastSyncTime?:number;
    syncing?:boolean;
}

interface Props {

}


interface Stat {
    repositories:Repository[];
    modalIsOpen:boolean;
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



const Checkbox = props => (
    <input type="checkbox" {...props} />
  )

export class Root extends React.Component<Props, Stat> {
    input:React.RefObject<HTMLInputElement>;
    finished:boolean;
    timer?:number;

    constructor(props) {
        super(props);

        this.input = React.createRef();

        this.state = {
            repositories:[], 
            modalIsOpen:false
        };

        this.finished = false;
        this.onSync = this.onSync.bind(this);
        this.onCheckboxChange = this.onCheckboxChange.bind(this);
        this.onAdd = this.onAdd.bind(this);
        this.onApiReady = this.onApiReady.bind(this);
        this.onCloseModal = this.onCloseModal.bind(this);
        this.onOk = this.onOk.bind(this);
        this.refreshState = this.refreshState.bind(this);
    }

    componentDidMount() {
        window.addEventListener('pywebviewready', this.onApiReady);
        this.timer = setInterval(this.refreshState, 20*1000);
    }

    componentWillUnmount() {
        window.removeEventListener('pywebviewready',  this.onApiReady);
        clearInterval(this.timer);
        this.finished = true;
    }
    
    refreshState() {
        this.setState({});
    }

    onApiReady() {
        window.pywebview.api.get_repos()
            .then((repos) => {
                console.log("repos:", repos);
                this.setState({repositories:repos});
            })
    }

    updateRepoState(repoName, lastSyncTime, syncing) {
        var repo = this.state.repositories.find((repo) => {
            return repo.name == repoName;
        });
        if (!repo) {
            console.log("can't find repo:", repoName);
            return;
        }
        console.log("update repo state:", repoName, lastSyncTime, syncing);
        repo.lastSyncTime = lastSyncTime;
        repo.syncing = syncing;
        this.setState({});
    }
  

    onCloseModal() {
        this.setState({modalIsOpen:false});
    }

    onOk() {
        var repo_url = this.input.current?.value;
        if (!repo_url) {
            return;
        }
        var pos = repo_url.lastIndexOf("/");
        if (pos == -1) {
            return;
        }
        var filename = repo_url.substring(pos + 1);
        if (!filename) {
            return;
        }
        var name = filename.split(".")[0];
        if (!name) {
            return;
        }
        console.log("repo url:", repo_url, " name:", name);
        var r = this.state.repositories.find((repo) => {
            return repo.name == name;
        })
        if (r) {
            alert("仓库名重复");
            return;
        }

        var repo:Repository = {name:name, url:repo_url, disabled:false, rdonly:false};
        window.pywebview.api.add_repo(name, repo_url)
            .then((r) => {
                if (r) {
                    this.state.repositories.push(repo);
                    this.setState({modalIsOpen:false});
                } else {
                    console.log("add fail");
                    alert("仓库添加失败");
                }
            });
    }

    onAdd() {
        this.setState({modalIsOpen:true});
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
        window.pywebview.api.sync_repo(name)

    }

    
    render() {
        var nodes: any[]= [];
        var repos = this.state.repositories;
        repos.forEach((repo) => {
            var status = "";
            if (repo.syncing) {
                status = "正在同步"
            } else if (repo.lastSyncTime) {
                status = formatTime(repo.lastSyncTime*1000) + "同步";
            } else {
                status = "";
            }
            nodes.push((
                <div  key={repo.name} className={styles["repo"]}>
                    <div className={styles["title"]}>
                        <div className={styles["name"]}>{repo.name}</div>
                        <button  onClick={this.onSync} data-name={repo.name}>同步仓库</button>
                    </div>
                    <div className={styles["content"]}>
                        <div>{status}</div>
                        <label>
                            <Checkbox
                                data-name={repo.name}
                                checked={!repo.disabled}
                                onChange={this.onCheckboxChange}
                                />
                          <span>自动同步</span>
                        </label>
                    </div>
                    <div className={styles["line"]}></div>
                </div>
            ));
        });
        var modalIsOpen = this.state.modalIsOpen;
        
        return (
            <div>
                <Modal
                    isOpen={modalIsOpen}>
                    <div className={styles["modal-content"]}>
                        <h2>新仓库</h2>
                        <input ref={this.input} placeholder={"仓库URL"}/>
                        <div className={styles["bottom"]}>
                            <button onClick={this.onCloseModal}>取消</button>
                            <button onClick={this.onOk}>确定</button>
                        </div>
                    </div>
                </Modal>

                <div className={styles["header"]}>
                    <div>我的仓库</div>
                    <div onClick={this.onAdd}>添加</div>
                </div>
                {nodes}
            </div>
        )
    }
}

