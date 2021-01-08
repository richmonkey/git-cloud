#!/bin/bash
pushd `dirname $0` > /dev/null
BASEDIR=`pwd`
popd > /dev/null

$BASEDIR/python3/bin/python main.py
