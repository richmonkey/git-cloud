#!/usr/bin/env python3
import sys
import socket
import datetime
import os
import shutil

def generate_conflicted_filename(filename):
    name, ext = os.path.splitext(filename)
    today = datetime.date.today()
    index = 0
    while True:
        if index == 0:
            filepath = name + "(%s conflicted copy %s)" % (socket.gethostname(), str(today)) + ext
        else:
            filepath = name + "(%s conflicted copy %s) (%s)" % (socket.gethostname(), str(today), index)+ ext
        index += 1
        if not os.path.exists(filepath):
            return filepath
    
if __name__ == "__main__":
    print(sys.argv)
    if len(sys.argv) < 5:
        sys.exit(1)
        
    current_version = sys.argv[1]
    ancestor_version = sys.argv[2]
    other_version = sys.argv[3]
    pathname = sys.argv[4]

    copy_pathname = generate_conflicted_filename(pathname)

    shutil.copy(current_version, copy_pathname)
    shutil.copy(other_version, current_version)
    
    sys.exit(0)
