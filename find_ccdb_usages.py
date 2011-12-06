#! /usr/bin/python

import os
import stat

def walktree (top = ".", depthfirst = True):
    names = os.listdir(top)
    if not depthfirst:
        yield top, names
    for name in names:
        try:
            st = os.lstat(os.path.join(top, name))
        except os.error:
            continue
        if stat.S_ISDIR(st.st_mode):
            for (newtop, children) in walktree (os.path.join(top, name), depthfirst):
                yield newtop, children
    if depthfirst:
        yield top, names

for (basepath, children) in walktree(".",False):
    for child in children:
        print os.path.join(basepath, child)

dirs_to_search = [x[0] for x in os.walk('.') if not ".svn" in x[0]]

    