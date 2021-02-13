#!/bin/bash

VERSION="0.2.0"
target=./dist/gitCloud-v$VERSION

if [ -d "$target" ]
then 
while true; do
    read -p "Do you wish to rm $target directory? (y/N)" yn
    case $yn in
        [Yy]* ) rm -rf $target; break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done
fi

mkdir $target

yarn run build
#python3 -m venv $target/python3
#$target/python3/bin/pip install -r requirements.txt
#cp dist/index.html $target
#cp dist/index.bundle.js $target
#cp run.sh $target
#cp config.py $target
#cp sync.py $target
#cp main.py $target
#cp README.md $target
#cd dist && zip gitCloud-v$VERSION.zip -r gitCloud-v$VERSION




pyinstaller --osx-bundle-identifier com.beetle.gitcloud --add-data dist/index.html:.  --add-data dist/index.bundle.js:.  --name "Git Cloud" --exclude-module PyQt5 -w main.py

mv "./dist/Git Cloud.app" $target && cd dist &&  zip gitCloud-v$VERSION.zip -r gitCloud-v$VERSION
