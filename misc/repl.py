#!/usr/bin/env python3

# M-x run-python (raise window so it doesn't hide)
# ?? python-shell-send-defun
# C-c C-r python-shell-send-region
# shit, it isn't autoscrolling??
#    maybe add hook
#    (setq comint-move-point-for-output t) ;; https://github.com/jorgenschaefer/elpy/issues/1641#issuecomment-528355368
#
import sys
from importlib import reload
from itertools import groupby, islice

from more_itertools import bucket, ilen

# todo function to reload hpi?
todel = [m for m in sys.modules if m.startswith('my.')]
for m in todel:
    del sys.modules[m]

import my
import my.bluemaestro as M
from my.config import bluemaestro as BC

# todo add to doc?
from my.core import get_files

# BC.export_path = get_files(BC.export_path)[:40]

# print(list(M.measurements())[:10])

M.fill_influxdb()

#
# todo ugh. doesn't work??
# from my.core.cachew import disable_cachew
# disable_cachew()
# RC.export_path = get_files(RC.export_path)[-1:]
import my.rescuetime as M
from my.config import rescuetime as RC

# print(len(list(M.entries())))
M.fill_influxdb()

print(M.dataframe())

e = M.entries()
e = list(islice(e, 0, 10))


key = lambda x: 'ERROR' if isinstance(x, Exception) else x.activity

# TODO move to errors module? how to preserve type signature?
# b = bucket(e, key=key)
# for k in b:
#     g = b[k] # meh? should maybe sort
#     print(k, ilen(g))

from collections import Counter

print(Counter(key(x) for x in e))
