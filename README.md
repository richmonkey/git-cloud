#git cloud
基于git的个人网盘

1. 安装git, python3, node, yarn
2. 安装python依赖 pip3 install -r requirements.txt
3. 安装node依赖 yarn install
4. 生成js的bundle yarn run build
5. 启动程序 python3 main.py
6. 在程序中添加需要自动同步的仓库地址，仓库地址要有自动提交的权限, 比如github使用ssh的url地址

#git如何能成为网盘
git默认在处理冲突时，需要人工干预，所以需要定制一个merge driver，保留theirs版本， 同时将ours版本copy到worktree， 类似dropbox冲突处理机制。

#git作为网盘的优势
现有各种git托管系统，都可以成为你的网盘，同时现有的git托管系统都有仓库的共享，协同功能，在一个团队中也可以很好的工作，同时这些组件的质量非常高，应该不用担心数据丢失或者无法回滚的问题。
git托管系统还有各个系统的客户端。

#todo
1. 通过github webhook通知客户端同步新的文件
2. 客户端使用git shadow clone, 同时可以定期清理旧的commit, 来减少客户端占用的磁盘空间。
